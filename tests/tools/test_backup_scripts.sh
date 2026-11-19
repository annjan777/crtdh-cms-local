#!/usr/bin/env bash
# Exercises deploy/backup/{crtdh-backup.sh,crtdh-restore-check.sh} end to end against a disposable source
# (the scripts/preprod.sh PostgreSQL and media folder) and a throwaway restore target. Never touches Docker,
# staging or production. Usage: tests/tools/test_backup_scripts.sh   (after scripts/preprod.sh up)
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PGBIN=${PGBIN:-$(ls -d /usr/lib/postgresql/*/bin | sort -V | tail -1)}
ST="$REPO/.preprod"
[ -S "$ST/pg/.s.PGSQL.5432" ] || { echo "start scripts/preprod.sh up first (needs its PostgreSQL)"; exit 2; }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; failn=0
ok() { echo "PASS $*"; pass=$((pass+1)); }
no() { echo "FAIL $*"; failn=$((failn+1)); }

mkdir -p "$T/media/hero" "$T/backups" "$T/nas" "$T/deploy"
printf 'img' > "$T/media/hero/a.jpg"; printf 'img2' > "$T/media/b.png"
printf 'SECRET_KEY=not-a-real-secret\n' > "$T/deploy/.env"
head -c 32 /dev/urandom | base64 > "$T/pass"; chmod 600 "$T/pass"
export CRTDH_DEPLOY_DIR="$T/deploy" CRTDH_BACKUP_DIR="$T/backups" CRTDH_BACKUP_PASSFILE="$T/pass" \
       CRTDH_OFFHOST_DIR="$T/nas" CRTDH_RESTORE_MODE=local PGBIN
export CRTDH_BACKUP_DB_CMD="'$PGBIN/pg_dump' -Fc -h '$ST/pg' -U crtdh -d crtdh"
export CRTDH_BACKUP_MEDIA_CMD="tar czf - -C '$T/media' ."
export CRTDH_BACKUP_LIST_CMD="cat > '$T/list.dump' && '$PGBIN/pg_restore' --list '$T/list.dump'; rc=\$?; rm -f '$T/list.dump'; exit \$rc"
B="$REPO/deploy/backup/crtdh-backup.sh"; R="$REPO/deploy/backup/crtdh-restore-check.sh"

"$B" --dry-run > "$T/dry.log" 2>&1 && [ -z "$(ls -A "$T/backups")" ] && ok "dry run writes nothing" || no "dry run"
"$B" > "$T/b1.log" 2>&1 && ok "backup set written" || { no "backup"; cat "$T/b1.log"; }
SET=$(ls -1d "$T/backups"/crtdh-*Z | tail -1)
[ -f "$SET/db.dump.gpg" ] && [ -f "$SET/media.tar.gz.gpg" ] && [ -f "$SET/env.gpg" ] && [ -f "$SET/SHA256SUMS" ] && ok "set has db, media, env, checksums" || no "set contents"
! grep -q "not-a-real-secret" -r "$SET" && ok "env is encrypted (no plaintext in the set)" || no "plaintext env in set"
[ "$(stat -c %a "$SET/db.dump.gpg")" = 600 ] && ok "backup files are mode 600" || no "file mode"
[ -d "$T/nas/$(basename "$SET")" ] && (cd "$T/nas/$(basename "$SET")" && sha256sum --quiet -c SHA256SUMS) && ok "off-host copy matches checksums" || no "off-host copy"
"$R" "$SET" > "$T/r1.log" 2>&1 && grep -q "PASS" "$T/r1.log" && ok "restore into a throwaway database: $(grep -o 'users=.*' "$T/r1.log")" || { no "restore-check"; tail -5 "$T/r1.log"; }

chmod 644 "$T/pass"; "$B" > "$T/b2.log" 2>&1 && no "accepted a world-readable passphrase file" || ok "refuses a passphrase file that is not mode 600"; chmod 600 "$T/pass"
cp -R "$SET" "$T/tampered"; printf 'x' >> "$T/tampered/media.tar.gz.gpg"
"$R" "$T/tampered" > "$T/r2.log" 2>&1 && no "restore-check accepted a tampered set" || ok "restore-check rejects a tampered set"
head -c 32 /dev/urandom | base64 > "$T/wrong"; chmod 600 "$T/wrong"
CRTDH_BACKUP_PASSFILE="$T/wrong" "$R" "$SET" > "$T/r3.log" 2>&1 && no "decrypted with the wrong passphrase" || ok "wrong passphrase cannot restore"
CRTDH_BACKUP_DB_CMD="false" "$B" > "$T/b3.log" 2>&1 && no "a failed dump still produced a set" || ok "a failed dump fails the run"
[ -z "$(ls -d "$T/backups"/*.partial 2>/dev/null)" ] && ok "a failed run leaves no partial set" || no "partial set left behind"
old="$T/backups/crtdh-20200101T000000Z"; mkdir "$old"; touch -d '30 days ago' "$old"
keep="$T/backups/unrelated-folder"; mkdir "$keep"; touch -d '30 days ago' "$keep"
"$B" > "$T/b4.log" 2>&1
[ ! -d "$old" ] && [ -d "$keep" ] && [ -d "$SET" ] && ok "retention prunes only old backup sets" || no "retention"
echo "backup scripts: $pass passed, $failn failed"
[ $failn = 0 ]
