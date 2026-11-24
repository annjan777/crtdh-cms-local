#!/usr/bin/env bash
# CRTDH website + CMS on academicweb.iitkgp.ac.in: no root, no Docker, and this server ignores .htaccess.
# Started by install.sh (which downloads the code to a local disk first), never directly:
#
#   curl -fsSL https://raw.githubusercontent.com/annjan777/crtdh-cms-local/dev/deploy/academicweb/install.sh -o /tmp/crtdh-install.sh && bash /tmp/crtdh-install.sh
#
# In order, stopping at the first problem, before the live site changes:
#   1. checks this server: PHP works (it carries the CMS), private folders are really private
#   2. saves a copy of the current website in ~/.crtdh/backups/
#   3. installs Python and Node packages, builds the CMS screens, sets up the database and content
#   4. starts the CMS; cron restarts it (every 5 minutes, after a reboot) and backs up its data nightly
#   5. asks for the first admin user, then asks "yes" before the new site goes live
#   CRTDH_IMPORT=<address>: take content, photos and users from a staging export instead (deploy/staging/export-for-cic.sh)
# --update: new code, same data.  --repair: rebuild the programs folder, restore data from the nightly backup.
set -euo pipefail

KEEP="${CRTDH_KEEP:-$HOME/.crtdh}"                                  # network drive: settings, backups, scripts
ROOT="${CRTDH_INSTALL:-$(cat "$KEEP/install-dir" 2>/dev/null || true)}"    # local disk: programs, database, photos, logs
APP="$ROOT/app"
HERE="$APP/deploy/academicweb"
WEB_ROOT="$HOME"
SITE="${CRTDH_SITE_URL:-https://crtdh.iitkgp.ac.in}"              # override only for a rehearsal elsewhere
HOSTNAME_SITE="$(printf '%s' "$SITE" | sed 's#^https://##; s#[:/].*##')"
CMS_PATH="/cms/index.php"
FLAG="${1:-}"; UPDATE=0; [ -n "$FLAG" ] && UPDATE=1
CTL="$KEEP/crtdh"

step() { printf '\n== %s\n' "$*"; }
ok() { printf '   ok  %s\n' "$*"; }
die() { printf '\nSTOPPED: %s\nNothing on the live website was changed by this step.\n' "$*" >&2; exit 1; }

trap 'printf "\nSTOPPED unexpectedly (setup.sh line %s). The live website is unchanged unless DONE was printed. Send a photo of this screen.\n" "$LINENO" >&2' ERR
[ -n "$ROOT" ] && [ -d "$APP/backend" ] || die "start with install.sh (the programs folder is not set up)"
[ "$(id -u)" != 0 ] || die "run this as the website user (crtdh), not root"
ulimit -n "$(ulimit -Hn)" 2>/dev/null || ulimit -n 65536 2>/dev/null || true
umask 022
PY=""
for c in python3.12 python3.13 python3.11; do command -v "$c" >/dev/null && { PY="$(command -v "$c")"; break; }; done
[ -n "$PY" ] || die "Python 3.11 or newer is needed (found none)"
for c in curl tar xz sha256sum crontab setsid; do command -v "$c" >/dev/null || die "the command '$c' is missing"; done
mkdir -p "$KEEP/backups" "$ROOT"/{data,logs,run,agent,releases} && chmod 700 "$KEEP" "$ROOT"

# curl to our own public address; if this server can't reach itself by name, go to Apache directly.
CURL_RESOLVE=""
selfcurl() { curl -s -m 20 $CURL_RESOLVE "$@"; }
if ! curl -s -o /dev/null -m 15 "$SITE/"; then
  CURL_RESOLVE="--resolve $HOSTNAME_SITE:443:127.0.0.1"
  selfcurl -o /dev/null "$SITE/" || die "this server cannot open $SITE itself, so the checks cannot run"
fi

# ---- 1. what this server allows (a temporary test folder, removed again) ------------------------------------------
step "Checking this server"
T="$WEB_ROOT/_crtdh_test_$$"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/locked"; chmod 755 "$T"
printf '<?php echo "php:".($_SERVER["PATH_INFO"] ?? "none");' > "$T/p.php"; chmod 644 "$T/p.php"
echo private > "$T/locked/x.txt"; chmod 700 "$T/locked"
base="$SITE/$(basename "$T")"
[ "$(selfcurl "$base/p.php/a/b")" = "php:/a/b" ] || die "PHP does not run here (or not with /path after the file), so the CMS cannot be reached"
ok "PHP works (it carries the CMS)"
code="$(selfcurl -o /dev/null -w '%{http_code}' "$base/locked/x.txt")"
case "$code" in 403|404) ok "private folders are refused by the web server ($code)" ;;
  *) die "a private (700) folder is readable from the web ($code); settings could not be kept safe here" ;; esac
rm -rf "$T"; trap - EXIT

# A free local port for the CMS (other sites' programs may run on this machine too).
PORT="$(sed -n 's/^CRTDH_PORT=//p' "$KEEP/env" 2>/dev/null || true)"
if [ -z "$PORT" ]; then
  PORT="$("$PY" - <<'PYEOF'
import socket
for port in range(8650, 8700):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        print(port)
        break
    except OSError:
        pass
    finally:
        s.close()
PYEOF
)"
  [ -n "$PORT" ] || die "no free local port between 8650 and 8699"
fi
ok "CMS will listen on 127.0.0.1:$PORT (this machine only)"
MCP_PORT="$(sed -n 's/^CRTDH_MCP_PORT=//p' "$KEEP/env" 2>/dev/null || true)"
if [ -z "$MCP_PORT" ]; then
  MCP_PORT="$("$PY" - "$PORT" <<'PYEOF'
import socket, sys
for port in range(8700, 8750):
    if str(port) == sys.argv[1]:
        continue
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        print(port)
        break
    except OSError:
        pass
    finally:
        s.close()
PYEOF
)"
  [ -n "$MCP_PORT" ] || die "no free local port between 8700 and 8749 for the Claude connector"
fi

# ---- 2. copy of the current site (one file) ---------------------------------------------------------------------
if ! ls "$KEEP"/backups/old-site-*.tar.gz >/dev/null 2>&1; then
  step "Saving a copy of the current website"
  B="$KEEP/backups/old-site-$(date +%Y%m%d-%H%M%S).tar.gz"
  tar -czf "$B" -C "$WEB_ROOT" --exclude=./.crtdh --exclude=./cms --exclude=./_media --exclude=./.cache \
      --exclude=./.mozilla --exclude=./.bash_history --exclude=./.lesshst --exclude=./.npm . || die "could not save the copy"
  chmod 600 "$B"
  ok "saved: $B ($(du -h "$B" | cut -f1))"
fi

# ---- 3. install ---------------------------------------------------------------------------------------------
step "Installing Python packages (a few minutes the first time)"
[ -x "$ROOT/venv/bin/python" ] || "$PY" -m venv "$ROOT/venv"
export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_CACHE_DIR="$ROOT/cache/pip"
"$ROOT/venv/bin/python" -m pip install -q --require-hashes -r "$APP/backend/requirements.txt" || die "installing the CMS packages failed"
"$ROOT/venv/bin/python" -m pip install -q --require-hashes -r "$APP/publish_agent/requirements.txt" || die "installing the publish agent packages failed"
ok "Python $("$ROOT/venv/bin/python" -V 2>&1 | cut -d' ' -f2)"

if ! "$ROOT/node/bin/node" -v 2>/dev/null | grep -q '^v22\.'; then
  step "Downloading Node.js 22"
  D="$(mktemp -d "$ROOT/.node.XXXXXX")"; NODE_URL="https://nodejs.org/dist/latest-v22.x"
  curl -fsS -m 60 "$NODE_URL/SHASUMS256.txt" -o "$D/SHASUMS256.txt" || die "could not reach nodejs.org"
  F="$(grep -o 'node-v22\.[0-9.]*-linux-x64\.tar\.xz' "$D/SHASUMS256.txt" | head -1)"
  [ -n "$F" ] || die "no Node 22 build listed"
  curl -fsS -m 300 "$NODE_URL/$F" -o "$D/$F" || die "Node download failed"
  (cd "$D" && grep " $F\$" SHASUMS256.txt | sha256sum -c --status) || die "Node download is corrupt (checksum)"
  rm -rf "$ROOT/node"; mkdir -p "$ROOT/node"; tar -xJf "$D/$F" -C "$ROOT/node" --strip-components=1; rm -rf "$D"
fi
export PATH="$ROOT/node/bin:$ROOT/venv/bin:$PATH"
ok "Node $(node -v)"

step "Building the CMS screens"
export NPM_CONFIG_UPDATE_NOTIFIER=false NPM_CONFIG_FUND=false NPM_CONFIG_AUDIT=false NPM_CONFIG_CACHE="$ROOT/cache/npm"
(cd "$APP/frontend" && npm ci --no-fund --no-audit --loglevel=error) || die "npm install (site) failed"
(cd "$APP/admin" && npm ci --no-fund --no-audit --loglevel=error) || die "npm install (CMS) failed"
(cd "$APP/admin" && VITE_BASE="$CMS_PATH/" VITE_API_BASE_URL="$CMS_PATH/api/v1" VITE_PUBLIC_SITE_URL="$SITE" \
   npx vite build --logLevel error) || die "building the CMS screens failed"
ok "CMS screens built"

# ---- settings: secrets made here, never typed or shown; kept private on the persistent drive ---------------------
if [ ! -f "$KEEP/env" ]; then
  step "Settings"
  gen() { "$ROOT/venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(48))'; }
  printf 'Optional: Cloudflare Turnstile keys for the contact form (press Enter to skip; until they are added to ~/.crtdh/env the form refuses messages).\n'
  read -r -p '  Turnstile site key: ' TS_SITE || TS_SITE=""
  TS_SECRET=""
  [ -n "$TS_SITE" ] && { read -r -s -p '  Turnstile secret key (hidden): ' TS_SECRET || true; echo; }
  umask 077
  cat > "$KEEP/env" <<EOF
# CRTDH CMS settings on academicweb. Private: never share or commit this file.
DEBUG=False
CRTDH_ENV=production
CRTDH_SKIP_DOTENV=True
SECRET_KEY=$(gen)
AGENT_HMAC_SECRET=$(gen)
ALLOWED_HOSTS=$HOSTNAME_SITE,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=$SITE
CMS_PUBLIC_URL=$SITE$CMS_PATH/
MEDIA_URL=$CMS_PATH/api/v1/media/
ALLOW_SQLITE=True
TRUSTED_PROXY_IPS=127.0.0.1
REQUIRE_TRUSTED_PROXY=True
TRUST_X_FORWARDED_FOR=True
USE_X_FORWARDED_HOST=True
FORWARDED_PROTO_DEFAULT=https
SECURE_SSL_REDIRECT=False
MFA_ENABLED=False
SITE_URL=$SITE
CONTACT_API_URL=$SITE$CMS_PATH/api/v1/contact/
CSP_IN_PAGES=1
LEGACY_PAGES_AS_FILES=1
TURNSTILE_SITE_KEY=$TS_SITE
TURNSTILE_SECRET=$TS_SECRET
CRTDH_PORT=$PORT
CRTDH_MCP_PORT=$MCP_PORT
CRTDH_CURL_RESOLVE='$CURL_RESOLVE'
EOF
  umask 022
  chmod 600 "$KEEP/env"
  ok "settings written to ~/.crtdh/env (readable only by you)"
fi
grep -q '^CRTDH_MCP_PORT=' "$KEEP/env" || printf 'CRTDH_MCP_PORT=%s\n' "$MCP_PORT" >> "$KEEP/env"
# Where things are on the programs disk: rewritten every run, so a moved or rebuilt folder just works.
cat > "$ROOT/paths.env" <<EOF
DATABASE_URL=sqlite:///$ROOT/data/cms.sqlite3
STATIC_ROOT=$ROOT/data/static
MEDIA_ROOT=$ROOT/data/media
PUBLISH_ROOT=$ROOT/data/publish
ADMIN_DIST_DIR=$APP/admin/dist
FRONTEND_BUILD_CMD='npm --prefix $APP/frontend run build'
FRONTEND_BUILD_OUTPUT=$APP/frontend/build/client
MCP_PUBLIC_URL=$SITE/mcp/index.php
MCP_OAUTH_ISSUER=$SITE
EOF
set -a; . "$KEEP/env"; . "$ROOT/paths.env"; set +a

# ---- database and content ---------------------------------------------------------------------------------------
step "Database"
mkdir -p "$ROOT/data/media" "$ROOT/data/static" "$ROOT/data/publish"
if [ ! -f "$ROOT/data/cms.sqlite3" ]; then
  SNAP="$(ls -1 "$KEEP"/backups/data-*.tar.gz 2>/dev/null | tail -1 || true)"
  if [ -n "$SNAP" ]; then
    tar -xzf "$SNAP" -C "$ROOT/data" || die "restoring the nightly backup $SNAP failed"
    ok "restored the CMS data from $(basename "$SNAP")"
  fi
fi
FRESH=0; [ -f "$ROOT/data/cms.sqlite3" ] || FRESH=1
(cd "$APP/backend" && python manage.py migrate --noinput -v 0 && python manage.py createcachetable) || die "database setup failed"
chmod 600 "$ROOT/data/cms.sqlite3"
if [ -n "${CRTDH_IMPORT:-}" ]; then
  step "Copying the content, photos and users from staging"
  (cd "$APP/backend" && python ../deploy/transfer.py import "$CRTDH_IMPORT" --yes) \
    || die "copying from staging failed (the message above says why)"
  FRESH=0
fi
if [ "$FRESH" = 1 ]; then
  (cd "$APP/backend" && CRTDH_ALLOW_SEED=1 python manage.py bootstrap_local && python manage.py create_baseline_snapshot) \
    || die "loading the website content failed"
  ok "website content loaded (the pages as they are today)"
fi
if ! (cd "$APP/backend" && python manage.py shell -c \
      'from django.contrib.auth import get_user_model as g; import sys; sys.exit(0 if g().objects.filter(is_superuser=True).exists() else 1)'); then
  printf '\nCreate your CMS admin login (use your own name, not "admin"; the password is never shown):\n'
  NOINPUT=""; [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && NOINPUT="--noinput"   # rehearsal only
  (cd "$APP/backend" && python manage.py createsuperuser $NOINPUT) || die "creating the admin user failed"
fi
ok "database ready"

# ---- publish agent: copies each release into the website folder ----------------------------------------------------
umask 077
printf '%s\n' "$AGENT_HMAC_SECRET" > "$ROOT/agent/agent-secret.txt"
VERIFY="$SITE/"; [ -n "$CURL_RESOLVE" ] && VERIFY=""   # the agent can't reach the site by name from here
cat > "$ROOT/agent/config.ini" <<EOF
[cms]
url = http://127.0.0.1:$PORT
secret_file = agent-secret.txt

[sftp]
transport = local

[site]
web_root = $WEB_ROOT
strategy = copy
base_dir = $ROOT/releases
keep_releases = 3
verify_url = $VERIFY

[agent]
state_dir = state
EOF
umask 022

# ---- 4. the CMS address, processes, cron ---------------------------------------------------------------------------
step "Starting the CMS"
ACCESS="$(sed -n 's/^access=//p' "$KEEP/host.conf" 2>/dev/null || true)"; ACCESS="${ACCESS:-campus}"
mkdir -p "$WEB_ROOT/cms"; chmod 755 "$WEB_ROOT/cms"
sed -e "s/^\$CMS_PORT = [0-9]*;/\$CMS_PORT = $PORT;/" -e "s/^\$ACCESS = '[a-z]*';/\$ACCESS = '$ACCESS';/" \
    "$HERE/cms-bridge.php" > "$WEB_ROOT/cms/index.php"
printf '<!doctype html><meta charset="utf-8"><title>CRTDH CMS</title><meta http-equiv="refresh" content="0; url=%s/"><a href="%s/">Open the CMS</a>\n' \
    "$CMS_PATH" "$CMS_PATH" > "$WEB_ROOT/cms/index.html"
printf 'upload_max_filesize = 1100M\npost_max_size = 1100M\nmax_execution_time = 330\n' > "$WEB_ROOT/cms/.user.ini"
# The Claude connector's address: the same bridge in "mcp" mode, in front of the MCP server.
MCP_ACCESS="$(sed -n 's/^claude=//p' "$KEEP/host.conf" 2>/dev/null || true)"; MCP_ACCESS="${MCP_ACCESS:-campus}"
mkdir -p "$WEB_ROOT/mcp"; chmod 755 "$WEB_ROOT/mcp"
sed -e "s/^\$CMS_PORT = [0-9]*;/\$CMS_PORT = $MCP_PORT;/" -e "s/^\$ACCESS = '[a-z]*';/\$ACCESS = '$MCP_ACCESS';/" \
    -e "s/^\$MODE = '[a-z]*';/\$MODE = 'mcp';/" "$HERE/cms-bridge.php" > "$WEB_ROOT/mcp/index.php"
printf 'max_execution_time = 330\n' > "$WEB_ROOT/mcp/.user.ini"
chmod 644 "$WEB_ROOT/mcp/index.php" "$WEB_ROOT/mcp/.user.ini"
# The connector's consent page asks for its stylesheet at /static/oauth/ (Apache serves it as a plain file).
mkdir -p "$WEB_ROOT/static/oauth" && cp "$APP/backend/apps/oauth/static/oauth/consent.css" "$WEB_ROOT/static/oauth/" \
  && chmod 755 "$WEB_ROOT/static" "$WEB_ROOT/static/oauth" && chmod 644 "$WEB_ROOT/static/oauth/consent.css"
chmod 644 "$WEB_ROOT/cms/index.php" "$WEB_ROOT/cms/index.html" "$WEB_ROOT/cms/.user.ini"
printf 'access=%s\nclaude=%s\n' "$ACCESS" "$MCP_ACCESS" > "$KEEP/host.conf"

export CRTDH_KEEP="$KEEP" CRTDH_INSTALL="$ROOT"
bash "$CTL" stop >/dev/null 2>&1 || true
bash "$CTL" start || die "the CMS did not start; see: ~/.crtdh/crtdh logs web"

CRON_MARK="# crtdh-cms"
( crontab -l 2>/dev/null | grep -v "$CRON_MARK" || true
  echo "*/5 * * * * bash $CTL watchdog >/dev/null 2>&1 $CRON_MARK"
  echo "@reboot bash $CTL watchdog >/dev/null 2>&1 $CRON_MARK"
  echo "23 3 * * * bash $CTL nightly >>$KEEP/nightly.log 2>&1 $CRON_MARK"
) | crontab - || die "could not set cron"
ok "running; restarts by itself and backs up its data every night (cron)"

for p in /.crtdh/env /.crtdh/; do
  code="$(selfcurl -o /dev/null -w '%{http_code}' "$SITE$p")"
  case "$code" in 403|404) ;; *) bash "$CTL" stop; die "$SITE$p answered $code; it must be 403 or 404. Stopped the CMS to be safe." ;; esac
done
ok "settings and backups are not reachable from the web"

# Claude connector discovery: clients read the OAuth metadata at the site root, so keep a static copy there.
mkdir -p "$WEB_ROOT/.well-known"; chmod 755 "$WEB_ROOT/.well-known"
WK_OK=1
for doc in oauth-authorization-server oauth-protected-resource/mcp; do
  out="$WEB_ROOT/.well-known/${doc%/mcp}"
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    curl -sf -m 10 -H "Host: $HOSTNAME_SITE" "http://127.0.0.1:$MCP_PORT/.well-known/$doc" -o "$out.part" && break
    sleep 2
  done
  if [ -s "$out.part" ]; then mv -f "$out.part" "$out"; chmod 644 "$out"; else rm -f "$out.part"; WK_OK=0; fi
done
code="$(selfcurl -o /dev/null -w '%{http_code}' "$SITE/.well-known/oauth-authorization-server")"
if [ "$WK_OK" = 1 ] && [ "$code" = 200 ]; then
  ok "Claude connector: $SITE/mcp/index.php/mcp (campus + Anthropic's servers)"
else
  printf '   note the Claude connector is not ready (metadata %s, web %s); the website and CMS are not affected\n' "$WK_OK" "$code"
fi
code="$(selfcurl -o /dev/null -w '%{http_code}' "$SITE$CMS_PATH/")"
case "$code" in 200) ok "CMS opens at $SITE/cms/" ;;
  403) ok "CMS answers at $SITE/cms/ (this server's own address is not on campus, so it got the campus-only page)" ;;
  *) printf '   note CMS at %s/cms/ answered %s from this server\n' "$SITE" "$code" ;; esac

if [ "$UPDATE" = 1 ]; then
  bash "$CTL" nightly >/dev/null 2>&1 || true   # a fresh data backup after every update or repair
  printf '\nDone (%s). The live site is unchanged; publish from the CMS to rebuild it.\n' "${FLAG#--}"
  exit 0
fi

# ---- 5. go live ---------------------------------------------------------------------------------------------------
bash "$CTL" nightly >/dev/null 2>&1 || true
cat <<EOF

The CMS is ready: $SITE/cms/  (opens from the campus network)
The old website is still live and was saved in ~/.crtdh/backups/.

EOF
read -r -p 'Type yes to put the new website live now (anything else: later, with ~/.crtdh/crtdh go-live): ' ANSWER || ANSWER=""
if [ "$ANSWER" = yes ]; then
  bash "$CTL" go-live || { printf '\nThe publish did not finish. The old site stays live. Logs: ~/.crtdh/crtdh logs worker\n'; exit 1; }
  cat <<EOF

DONE. The new website is live: $SITE
  Edit it:            $SITE/cms/  (Review & publish puts changes live in 1-3 minutes)
  Old site back:      ~/.crtdh/crtdh old-site      New site again: ~/.crtdh/crtdh new-site
  Is it all running:  ~/.crtdh/crtdh status
  CMS from home too:  ~/.crtdh/crtdh access anywhere   (default: campus network only)
EOF
else
  printf '\nNot published. When ready: ~/.crtdh/crtdh go-live\n'
fi
