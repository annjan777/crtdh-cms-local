# CMS backups (R-3 / F-03)

What is backed up, every night: the PostgreSQL database (`pg_dump -Fc`), the uploaded media (`media_data`
volume, read through the `cms` container) and `deploy/.env`. Each set is encrypted (GPG, AES-256), checksummed,
**verified** (it decrypts, the dump is a valid archive with table data, the media archive lists), copied to an
off-server folder and re-checked there. Sets older than 14 days (60 off-host) are pruned, and only sets written
by this script. The scripts only *read* from the running stack: no stop, restart, restore or write.

The public website itself is not in these sets: CIC serves the published copy, the publish agent keeps the
previous releases there, and a fresh publish rebuilds it from the CMS.

## Set up once (lab server)

1. Passphrase file: `head -c 32 /dev/urandom | base64 > ~/.crtdh-backup-pass && chmod 600 ~/.crtdh-backup-pass`.
   Put the same text in the password manager now. Without it, no backup can ever be restored.
2. `cp deploy/backup/backup.conf.example deploy/backup/backup.conf` and set the folders. Mount the off-host
   folder (lab NAS or a USB drive) first; the script refuses to run if it is configured but not mounted.
3. Try it: `deploy/backup/crtdh-backup.sh --dry-run`, then `deploy/backup/crtdh-backup.sh`.
4. Prove a restore: `deploy/backup/crtdh-restore-check.sh latest`. It restores into a throwaway PostgreSQL
   container (no network, removed afterwards) and prints user, version and media counts. Expect `PASS`.
5. Cron (`crontab -e`), 01:30 every night:
   `30 1 * * * /srv/crtdh/app/deploy/backup/crtdh-backup.sh >> /srv/crtdh/backups/backup.log 2>&1`
6. Run `crtdh-restore-check.sh latest` once a term and after every upgrade; note the result in the handover log.

A failed run exits non-zero and prints `FAILED: <reason>`; nothing half-written is left behind. Watch for the
`WARNING: CRTDH_OFFHOST_DIR is not set` line: a backup on the same disk does not survive that disk.

## Full restore after a loss (needs the owner's go-ahead; it replaces live data)

Not yet rehearsed against a real stack (only `crtdh-restore-check.sh` is tested). Rehearse it once on staging
before relying on it.

1. Stop writes: `docker compose stop cms mcp worker housekeeping` (keep `db` running).
2. Database: decrypt the dump and restore into the live database with `--clean --if-exists`:
   `gpg -d db.dump.gpg | docker compose exec -T db sh -c 'cat > /tmp/r.dump && pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/r.dump; rm /tmp/r.dump'`
3. Media: `gpg -d media.tar.gz.gpg | docker compose run --rm --no-deps -T cms tar xzf - -C /data/media`
4. `docker compose up -d`, sign in, check the latest pages and photos, then publish once.

Tested by `tests/tools/test_backup_scripts.sh` (13 checks: encryption, permissions, verification, off-host
copy, tamper and wrong-passphrase rejection, failure cleanup, retention, and a real restore).
