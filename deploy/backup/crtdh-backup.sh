#!/usr/bin/env bash
# CRTDH CMS backup (R-3 / F-03): database + uploaded media + deploy/.env, encrypted, checksummed, verified,
# copied off the server, old sets pruned. Read-only against the running stack: it only runs pg_dump and tar
# inside the existing containers (`docker compose exec`), never stops, restarts or writes to them.
#
#   deploy/backup/crtdh-backup.sh              one backup set now (cron: see deploy/backup/README.md)
#   deploy/backup/crtdh-backup.sh --dry-run    print what it would do, touch nothing
#
# Settings come from deploy/backup/backup.conf (copy backup.conf.example) or the environment:
#   CRTDH_DEPLOY_DIR     the compose folder (default: this repo's deploy/)
#   CRTDH_BACKUP_DIR     where sets are written (default /srv/crtdh/backups); keep it off the Docker disk if you can
#   CRTDH_BACKUP_PASSFILE  gpg passphrase file, mode 600 (default ~/.crtdh-backup-pass). Keep a copy in the
#                        password manager: without it no backup can be restored.
#   CRTDH_BACKUP_KEEP_DAYS  local retention (default 14)
#   CRTDH_OFFHOST_DIR    a mounted off-server folder (lab NAS, external drive); each set is copied there and
#                        re-checked. Empty = no off-host copy (the script warns every run).
#   CRTDH_OFFHOST_KEEP_DAYS retention on the off-host copy (default 60)
# Test hooks (used by tests/tools/test_backup_scripts.sh; leave unset in production):
#   CRTDH_BACKUP_DB_CMD / CRTDH_BACKUP_MEDIA_CMD  replace the two `docker compose exec` producers.
#   CRTDH_BACKUP_LIST_CMD  lists a pg_dump archive read from stdin (default: a throwaway postgres:16 container with
#                          no network, so the host needs no PostgreSQL tools and the live db is never touched).
set -euo pipefail
umask 077

HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/backup.conf" ] && . "$HERE/backup.conf"
DEPLOY_DIR=${CRTDH_DEPLOY_DIR:-$(cd "$HERE/.." && pwd)}
BACKUP_DIR=${CRTDH_BACKUP_DIR:-/srv/crtdh/backups}
PASSFILE=${CRTDH_BACKUP_PASSFILE:-$HOME/.crtdh-backup-pass}
KEEP_DAYS=${CRTDH_BACKUP_KEEP_DAYS:-14}
OFFHOST_DIR=${CRTDH_OFFHOST_DIR:-}
OFFHOST_KEEP_DAYS=${CRTDH_OFFHOST_KEEP_DAYS:-60}
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1

DB_CMD=${CRTDH_BACKUP_DB_CMD:-"docker compose -f '$DEPLOY_DIR/docker-compose.yml' exec -T db sh -c 'pg_dump -Fc -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\"'"}
LIST_CMD=${CRTDH_BACKUP_LIST_CMD:-"docker run --rm -i --network none postgres:16-alpine sh -c 'cat > /tmp/d && pg_restore --list /tmp/d'"}
MEDIA_CMD=${CRTDH_BACKUP_MEDIA_CMD:-"docker compose -f '$DEPLOY_DIR/docker-compose.yml' exec -T cms tar czf - -C /data/media ."}

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SET="$BACKUP_DIR/crtdh-$STAMP"
log() { printf '%s backup: %s\n' "$(date -u +%FT%TZ)" "$*"; }
fail() { log "FAILED: $*"; [ -d "$SET.partial" ] && rm -rf "$SET.partial"; exit 1; }

[ -s "$PASSFILE" ] || fail "passphrase file $PASSFILE is missing or empty"
perm=$(stat -c %a "$PASSFILE" 2>/dev/null || stat -f %Lp "$PASSFILE")
[ "$perm" = 600 ] || [ "$perm" = 400 ] || fail "passphrase file $PASSFILE must be mode 600 (is $perm)"
command -v gpg >/dev/null || fail "gpg is not installed"
[ -z "$OFFHOST_DIR" ] && log "WARNING: CRTDH_OFFHOST_DIR is not set; this set stays on this server only"

if [ $DRY = 1 ]; then
  log "dry run: would write $SET/{db.dump.gpg,media.tar.gz.gpg,env.gpg,SHA256SUMS,MANIFEST}"
  log "dry run: db via: $DB_CMD"
  log "dry run: media via: $MEDIA_CMD"
  log "dry run: keep $KEEP_DAYS days in $BACKUP_DIR${OFFHOST_DIR:+, copy to $OFFHOST_DIR (keep $OFFHOST_KEEP_DAYS days)}"
  exit 0
fi

mkdir -p "$BACKUP_DIR"
mkdir "$SET.partial"
enc() { gpg --batch --yes --quiet --pinentry-mode loopback --passphrase-file "$PASSFILE" \
          --symmetric --cipher-algo AES256 -o "$1"; }
dec() { gpg --batch --quiet --pinentry-mode loopback --passphrase-file "$PASSFILE" --decrypt "$1"; }

# 1. Database: custom format (compressed; pg_restore can list and restore it selectively).
log "dumping database"
eval "$DB_CMD" | enc "$SET.partial/db.dump.gpg" || fail "pg_dump"
# 2. Uploaded media (the cms container's /data/media = the media_data volume).
log "archiving media"
eval "$MEDIA_CMD" | enc "$SET.partial/media.tar.gz.gpg" || fail "media archive"
# 3. deploy/.env: secrets needed to bring the stack back (encrypted like the rest).
if [ -f "$DEPLOY_DIR/.env" ]; then enc "$SET.partial/env.gpg" < "$DEPLOY_DIR/.env" || fail "env"; fi

# 4. Verify before calling it a backup: every file decrypts, the dump is a readable archive, the tar lists.
log "verifying"
listing=$(dec "$SET.partial/db.dump.gpg" | eval "$LIST_CMD" 2>/dev/null) \
  || fail "the database dump does not decrypt or is not a valid pg_dump archive"
tables=$(printf '%s\n' "$listing" | grep -c ' TABLE DATA ' || true)
[ "$tables" -gt 0 ] || fail "the database dump holds no table data"
files=$(dec "$SET.partial/media.tar.gz.gpg" | tar tzf - | grep -vc '/$' || true)
[ -f "$SET.partial/env.gpg" ] && { dec "$SET.partial/env.gpg" >/dev/null || fail "env.gpg does not decrypt"; }

(cd "$SET.partial" && sha256sum -- *.gpg > SHA256SUMS)
cat > "$SET.partial/MANIFEST" <<EOF
crtdh backup $STAMP
host: $(hostname)
tables_with_data: $tables
media_files: $files
env_included: $([ -f "$SET.partial/env.gpg" ] && echo yes || echo no)
EOF
mv "$SET.partial" "$SET"
log "set $SET: $tables tables with data, $files media files"

# 5. Off-host copy, re-checked against the checksums.
if [ -n "$OFFHOST_DIR" ]; then
  [ -d "$OFFHOST_DIR" ] || fail "off-host folder $OFFHOST_DIR is not mounted"
  cp -R "$SET" "$OFFHOST_DIR/" || fail "copy to $OFFHOST_DIR"
  (cd "$OFFHOST_DIR/$(basename "$SET")" && sha256sum --quiet -c SHA256SUMS) || fail "off-host copy does not match its checksums"
  log "copied to $OFFHOST_DIR"
  find "$OFFHOST_DIR" -maxdepth 1 -type d -name 'crtdh-*Z' -mtime +"$OFFHOST_KEEP_DAYS" -exec rm -rf {} +
fi

# 6. Retention: only this script's own sets, only after today's set is safely written.
find "$BACKUP_DIR" -maxdepth 1 -type d -name 'crtdh-*Z' -mtime +"$KEEP_DAYS" -exec rm -rf {} +
find "$BACKUP_DIR" -maxdepth 1 -type d -name 'crtdh-*.partial' -mtime +1 -exec rm -rf {} +
log "done"
