#!/usr/bin/env bash
# Prove a backup set can be restored (R-3 / F-03), without touching the live stack: restores the database into a
# throwaway PostgreSQL 16 (its own container, no network, removed afterwards) and unpacks the media into a temp
# folder, then reports row counts. Run it after the first backup, once a term, and after upgrades.
#
#   deploy/backup/crtdh-restore-check.sh /srv/crtdh/backups/crtdh-20261201T013000Z
#   deploy/backup/crtdh-restore-check.sh latest          (newest set in CRTDH_BACKUP_DIR)
#
# Uses the same backup.conf / environment as crtdh-backup.sh (CRTDH_BACKUP_DIR, CRTDH_BACKUP_PASSFILE).
# CRTDH_RESTORE_MODE=local uses PostgreSQL binaries on this machine (PGBIN) instead of Docker (used by the tests).
set -euo pipefail
umask 077

HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/backup.conf" ] && . "$HERE/backup.conf"
BACKUP_DIR=${CRTDH_BACKUP_DIR:-/srv/crtdh/backups}
PASSFILE=${CRTDH_BACKUP_PASSFILE:-$HOME/.crtdh-backup-pass}
MODE=${CRTDH_RESTORE_MODE:-docker}
SET=${1:?usage: crtdh-restore-check.sh <backup set folder | latest>}
[ "$SET" = latest ] && SET=$(ls -1d "$BACKUP_DIR"/crtdh-*Z 2>/dev/null | sort | tail -1)
[ -d "$SET" ] || { echo "restore-check: no backup set at '$SET'" >&2; exit 1; }

log() { printf '%s restore-check: %s\n' "$(date -u +%FT%TZ)" "$*"; }
dec() { gpg --batch --quiet --pinentry-mode loopback --passphrase-file "$PASSFILE" --decrypt "$1"; }
WORK=$(mktemp -d)
NAME="crtdh-restore-check-$$"
AS=()
cleanup() {
  if [ "$MODE" = docker ]; then docker rm -f "$NAME" >/dev/null 2>&1 || true
  elif [ -n "${PGDATA_DIR:-}" ]; then "${AS[@]}" "$PGBIN/pg_ctl" -D "$PGDATA_DIR" -m immediate stop >/dev/null 2>&1 || true; fi
  rm -rf "$WORK"
}
trap cleanup EXIT

log "checking checksums of $SET"
(cd "$SET" && sha256sum --quiet -c SHA256SUMS)

log "restoring the database into a throwaway PostgreSQL ($MODE)"
dec "$SET/db.dump.gpg" > "$WORK/db.dump"
if [ "$MODE" = docker ]; then
  docker run -d --name "$NAME" --network none -e POSTGRES_USER=crtdh -e POSTGRES_PASSWORD=restore-check \
    -e POSTGRES_DB=crtdh postgres:16-alpine >/dev/null
  for _ in $(seq 60); do docker exec "$NAME" pg_isready -U crtdh -d crtdh >/dev/null 2>&1 && break; sleep 1; done
  docker exec -i "$NAME" pg_restore --no-owner --no-acl -U crtdh -d crtdh < "$WORK/db.dump"
  q() { docker exec "$NAME" psql -U crtdh -d crtdh -tAc "$1"; }
else
  PGBIN=${PGBIN:-$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)}
  PGDATA_DIR="$WORK/pg"; SOCK="$WORK"
  AS=(); if [ "$(id -u)" = 0 ]; then AS=(runuser -u postgres --); chmod 755 "$WORK"; chown postgres "$WORK"; fi  # initdb refuses root
  "${AS[@]}" "$PGBIN/initdb" -D "$PGDATA_DIR" -U crtdh -A trust >/dev/null
  "${AS[@]}" "$PGBIN/pg_ctl" -D "$PGDATA_DIR" -o "-c listen_addresses='' -k $SOCK" -w start >/dev/null
  "$PGBIN/createdb" -h "$SOCK" -U crtdh crtdh
  "$PGBIN/pg_restore" --no-owner --no-acl -h "$SOCK" -U crtdh -d crtdh "$WORK/db.dump"
  q() { "$PGBIN/psql" -h "$SOCK" -U crtdh -d crtdh -tAc "$1"; }
fi

users=$(q "select count(*) from auth_user")
snaps=$(q "select count(*) from publishing_snapshot where published_at is not null")
last=$(q "select coalesce(max(published_at)::text, 'never') from publishing_snapshot")
migrations=$(q "select count(*) from django_migrations")
[ "$migrations" -gt 0 ] || { log "FAILED: restored database has no migrations table rows"; exit 1; }

log "unpacking media"
mkdir "$WORK/media"
dec "$SET/media.tar.gz.gpg" | tar xzf - -C "$WORK/media"
media=$(find "$WORK/media" -type f | wc -l | tr -d ' ')
expected=$(awk -F': ' '/^media_files:/{print $2}' "$SET/MANIFEST")
[ "$media" = "$expected" ] || { log "FAILED: media has $media files, manifest says $expected"; exit 1; }

log "PASS $(basename "$SET"): users=$users published_versions=$snaps last_publish=$last migrations=$migrations media_files=$media"
