#!/usr/bin/env bash
# CRTDH website + CMS on academicweb.iitkgp.ac.in (no root, no Docker), in one run:
#
#   git clone -b dev https://github.com/annjan777/crtdh-cms-local.git ~/.crtdh/app && bash ~/.crtdh/app/deploy/academicweb/setup.sh
#
# What it does, in order (it stops at the first problem, before changing the live site):
#   1. checks this server can do it: .htaccess rules, and a way to reach the CMS (Apache proxy, else PHP)
#   2. saves a copy of the current website in ~/.crtdh/backups/
#   3. installs everything under ~/.crtdh (hidden, never served): Python packages, Node, the CMS, its database
#   4. starts the CMS and sets cron so it restarts by itself (every 5 minutes, and after a reboot)
#   5. asks you for the first admin user, then asks "yes" before the new site goes live
# Run it again any time: finished steps are skipped and your data is kept.
#   bash ~/.crtdh/app/deploy/academicweb/setup.sh --update   (what "crtdh update" runs after git pull)
set -euo pipefail

ROOT="$HOME/.crtdh"
APP="$ROOT/app"
WEB_ROOT="$HOME"
PORT=8650
SITE="${CRTDH_SITE_URL:-https://crtdh.iitkgp.ac.in}"          # overrides only for a rehearsal elsewhere
HOSTNAME_SITE="$(printf '%s' "$SITE" | sed 's#^https://##; s#[:/].*##')"
REPO="${CRTDH_REPO:-https://github.com/annjan777/crtdh-cms-local.git}"
BRANCH="${CRTDH_BRANCH:-dev}"
UPDATE=0; [ "${1:-}" = "--update" ] && UPDATE=1
HERE="$(cd "$(dirname "$0")" && pwd)"

step() { printf '\n== %s\n' "$*"; }
ok() { printf '   ok  %s\n' "$*"; }
die() { printf '\nSTOPPED: %s\nNothing on the live website was changed by this step.\n' "$*" >&2; exit 1; }

[ "$(id -u)" != 0 ] || die "run this as the website user (crtdh), not root"
ulimit -n "$(ulimit -Hn)" 2>/dev/null || ulimit -n 65536 2>/dev/null || true   # git/npm open many files
umask 022
PY=""
for c in python3.12 python3.13 python3.11; do command -v "$c" >/dev/null && { PY="$(command -v "$c")"; break; }; done
[ -n "$PY" ] || die "Python 3.11 or newer is needed (found none)"
for c in git curl tar xz sha256sum crontab setsid; do command -v "$c" >/dev/null || die "the command '$c' is missing"; done
mkdir -p "$ROOT"/{backups,data,logs,run,agent} && chmod 700 "$ROOT"

# ---- 0. code ---------------------------------------------------------------------------------------------
if [ ! -d "$APP/.git" ]; then
  step "Downloading the code"
  git -c core.checkoutWorkers=1 clone --depth 50 -b "$BRANCH" "$REPO" "$APP" || die "git clone failed"
fi
[ "$HERE" = "$APP/deploy/academicweb" ] || HERE="$APP/deploy/academicweb"
ln -sfn "$HERE/crtdh" "$ROOT/crtdh"
chmod 755 "$HERE/crtdh"

# curl to our own public address; if this server can't reach itself by name, go to Apache directly.
CURL_RESOLVE=""
selfcurl() { curl -s -m 20 $CURL_RESOLVE "$@"; }
if ! curl -s -o /dev/null -m 15 "$SITE/"; then
  CURL_RESOLVE="--resolve $HOSTNAME_SITE:443:127.0.0.1"
  selfcurl -o /dev/null "$SITE/" || die "this server cannot open $SITE itself, so the checks cannot run"
fi

# ---- 1. what this server allows ------------------------------------------------------------------------------
if [ "$UPDATE" = 0 ] || [ ! -f "$ROOT/host.conf" ]; then
  step "Checking what this server allows (a temporary test folder, removed again)"
  T="$WEB_ROOT/_crtdh_test_$$"; mkdir -p "$T"; trap 'rm -rf "$T"; kill $TP 2>/dev/null || true' EXIT; TP=""
  echo ok-file > "$T/hello.txt"
  printf '<?php echo "ok-php";' > "$T/p.php"
  printf 'RewriteEngine On\nRewriteRule ^rw$ hello.txt [L]\nRewriteRule ^px/(.*)$ http://127.0.0.1:8659/$1 [P,L]\n' > "$T/.htaccess"
  chmod 644 "$T"/* "$T/.htaccess"; chmod 755 "$T"
  (cd "$T" && exec "$PY" -m http.server 8659 --bind 127.0.0.1 >/dev/null 2>&1) & TP=$!
  sleep 2
  base="$SITE/$(basename "$T")"
  [ "$(selfcurl "$base/rw")" = ok-file ] || die ".htaccess rewrite rules are not allowed here (needs AllowOverride FileInfo); ask CIC"
  ok ".htaccess rules work"
  if [ "$(selfcurl "$base/px/hello.txt")" = ok-file ]; then MODE=proxy; ok "Apache can pass /cms/ to the CMS directly"
  elif [ "$(selfcurl "$base/p.php")" = ok-php ]; then MODE=php; ok "no Apache proxy here; using the PHP bridge instead"
  else die "neither Apache proxying nor PHP works here, so the CMS cannot be reached from a browser"; fi
  kill "$TP" 2>/dev/null || true; rm -rf "$T"; trap - EXIT
  # From here on: hidden files and the install are refused, and the CMS paths are campus-only.
  CRTDH_PORT=$PORT "$ROOT/crtdh" _host "$MODE" campus
  ok "web rules in place (.htaccess)"
else
  MODE="$(sed -n 's/^mode=//p' "$ROOT/host.conf")"
fi

# ---- 2. copy of the current site -----------------------------------------------------------------------------
if ! ls "$ROOT"/backups/old-site-*.tar.gz >/dev/null 2>&1; then
  step "Saving a copy of the current website"
  B="$ROOT/backups/old-site-$(date +%Y%m%d-%H%M%S).tar.gz"
  tar -czf "$B" -C "$WEB_ROOT" --exclude=./.crtdh --exclude=./_crtdh --exclude=./.cache --exclude=./.mozilla \
      --exclude=./.bash_history --exclude=./.lesshst . || die "could not save the copy"
  ok "saved: $B ($(du -h "$B" | cut -f1))"
fi


# ---- 3. install ---------------------------------------------------------------------------------------------
step "Installing Python packages (a few minutes the first time)"
[ -x "$ROOT/venv/bin/python" ] || "$PY" -m venv "$ROOT/venv"
"$ROOT/venv/bin/python" -m pip install -q --disable-pip-version-check --require-hashes -r "$APP/backend/requirements.txt" \
  || die "installing the CMS packages failed"
"$ROOT/venv/bin/python" -m pip install -q --disable-pip-version-check --require-hashes -r "$APP/publish_agent/requirements.txt" \
  || die "installing the publish agent packages failed"
ok "Python $("$ROOT/venv/bin/python" -V 2>&1 | cut -d' ' -f2)"

if ! "$ROOT/node/bin/node" -v 2>/dev/null | grep -q '^v22\.'; then
  step "Downloading Node.js 22"
  D="$(mktemp -d)"; NODE_URL="https://nodejs.org/dist/latest-v22.x"
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
export NPM_CONFIG_UPDATE_NOTIFIER=false NPM_CONFIG_FUND=false NPM_CONFIG_AUDIT=false
(cd "$APP/frontend" && npm ci --no-fund --no-audit --loglevel=error) || die "npm install (site) failed"
(cd "$APP/admin" && npm ci --no-fund --no-audit --loglevel=error) || die "npm install (CMS) failed"
(cd "$APP/admin" && VITE_BASE=/cms/ VITE_API_BASE_URL=/api/v1 VITE_PUBLIC_SITE_URL="$SITE" npx vite build --logLevel error) \
  || die "building the CMS screens failed"
ok "CMS screens built"

# ---- settings (secrets made here, never typed or shown) ---------------------------------------------------------
if [ ! -f "$ROOT/env" ]; then
  step "Settings"
  gen() { "$ROOT/venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(48))'; }
  printf 'Optional: Cloudflare Turnstile keys for the contact form (press Enter to skip; the form then refuses messages until you add them in ~/.crtdh/env).\n'
  read -r -p '  Turnstile site key: ' TS_SITE || TS_SITE=""
  TS_SECRET=""
  [ -n "$TS_SITE" ] && { read -r -s -p '  Turnstile secret key (hidden): ' TS_SECRET || true; echo; }
  umask 077
  cat > "$ROOT/env" <<EOF
# CRTDH CMS settings on academicweb. Private: never share or commit this file.
DEBUG=False
CRTDH_ENV=production
CRTDH_SKIP_DOTENV=True
SECRET_KEY=$(gen)
AGENT_HMAC_SECRET=$(gen)
ALLOWED_HOSTS=$HOSTNAME_SITE,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=$SITE
CMS_PUBLIC_URL=$SITE/cms/
DATABASE_URL=sqlite:///$ROOT/data/cms.sqlite3
ALLOW_SQLITE=True
TRUSTED_PROXY_IPS=127.0.0.1
REQUIRE_TRUSTED_PROXY=True
TRUST_X_FORWARDED_FOR=True
USE_X_FORWARDED_HOST=True
FORWARDED_PROTO_DEFAULT=https
SECURE_SSL_REDIRECT=False
MFA_ENABLED=False
STATIC_ROOT=$ROOT/data/static
MEDIA_ROOT=$ROOT/data/media
PUBLISH_ROOT=$ROOT/data/publish
ADMIN_DIST_DIR=$APP/admin/dist
FRONTEND_BUILD_CMD='npm --prefix $APP/frontend run build'
FRONTEND_BUILD_OUTPUT=$APP/frontend/build/client
SITE_URL=$SITE
CONTACT_API_URL=$SITE/api/v1/contact/
TURNSTILE_SITE_KEY=$TS_SITE
TURNSTILE_SECRET=$TS_SECRET
CRTDH_PORT=$PORT
CRTDH_CURL_RESOLVE='$CURL_RESOLVE'
EOF
  umask 022
  chmod 600 "$ROOT/env"
  ok "settings written to ~/.crtdh/env (readable only by you)"
fi
set -a; . "$ROOT/env"; set +a

# ---- database and content ---------------------------------------------------------------------------------------
step "Database"
mkdir -p "$ROOT/data/media" "$ROOT/data/static" "$ROOT/data/publish"
FRESH=0; [ -f "$ROOT/data/cms.sqlite3" ] || FRESH=1
(cd "$APP/backend" && python manage.py migrate --noinput -v 0 && python manage.py createcachetable) || die "database setup failed"
chmod 600 "$ROOT/data/cms.sqlite3"
if [ "$FRESH" = 1 ]; then
  (cd "$APP/backend" && CRTDH_ALLOW_SEED=1 MEDIA_ROOT="$ROOT/data/media" python manage.py bootstrap_local \
     && python manage.py create_baseline_snapshot) || die "loading the website content failed"
  ok "website content loaded (the pages as they are today)"
fi
if ! (cd "$APP/backend" && python manage.py shell -c \
      'from django.contrib.auth import get_user_model as g; import sys; sys.exit(0 if g().objects.filter(is_superuser=True).exists() else 1)'); then
  printf '\nCreate your CMS admin login (use your own name, not "admin"; the password is never shown):\n'
  NOINPUT=""; [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && NOINPUT="--noinput"   # rehearsal only
  (cd "$APP/backend" && python manage.py createsuperuser $NOINPUT) || die "creating the admin user failed"
fi
ok "database ready"

# ---- publish agent (local) --------------------------------------------------------------------------------------
if [ ! -f "$ROOT/agent/config.ini" ]; then
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
strategy = htaccess
keep_releases = 3
verify_url = $VERIFY

[agent]
state_dir = state
EOF
  umask 022
fi

# ---- 4. routing, processes, cron -----------------------------------------------------------------------------------
step "Starting the CMS"
if [ "$MODE" = php ]; then
  sed "s/^\$CMS_PORT = [0-9]*;/\$CMS_PORT = $PORT;/" "$HERE/cms-bridge.php" > "$WEB_ROOT/_crtdh_cms.php"
  chmod 644 "$WEB_ROOT/_crtdh_cms.php"
  printf 'upload_max_filesize = 1100M\npost_max_size = 1100M\nmax_execution_time = 330\n' > "$WEB_ROOT/.user.ini"
fi
ACCESS="$(sed -n 's/^access=//p' "$ROOT/host.conf" 2>/dev/null)"; ACCESS="${ACCESS:-campus}"
"$ROOT/crtdh" stop >/dev/null 2>&1 || true
CRTDH_PORT=$PORT "$ROOT/crtdh" _host "$MODE" "$ACCESS"
"$ROOT/crtdh" start || die "the CMS did not start; see: ~/.crtdh/crtdh logs web"

CRON_MARK="# crtdh-cms"
( crontab -l 2>/dev/null | grep -v "$CRON_MARK" || true
  echo "*/5 * * * * $ROOT/crtdh watchdog >/dev/null 2>&1 $CRON_MARK"
  echo "@reboot $ROOT/crtdh watchdog >/dev/null 2>&1 $CRON_MARK"
  echo "23 3 * * * $ROOT/crtdh housekeeping >>$ROOT/logs/housekeeping.log 2>&1 $CRON_MARK"
) | crontab - || die "could not set cron"
ok "running; restarts by itself (cron)"

code="$(selfcurl -o /dev/null -w '%{http_code}' "$SITE/.crtdh/env")"
case "$code" in 403|404) ok "the install is hidden from the web ($code)" ;;
  *) "$ROOT/crtdh" stop; die "$SITE/.crtdh/env answered $code; it must be 403 or 404. Stopped the CMS to be safe." ;; esac
code="$(selfcurl -o /dev/null -w '%{http_code}' "$SITE/cms/")"
[ "$code" = 200 ] && ok "CMS opens at $SITE/cms/" || printf '   note CMS at %s/cms/ answered %s from this server\n' "$SITE" "$code"

if [ "$UPDATE" = 1 ]; then
  printf '\nUpdated and restarted. The live site is unchanged; publish from the CMS to rebuild it.\n'
  exit 0
fi

# ---- 5. go live ---------------------------------------------------------------------------------------------------
cat <<EOF

The CMS is ready: $SITE/cms/  (opens from the campus network)
The old website is still live and was saved in ~/.crtdh/backups/.

EOF
read -r -p 'Type yes to put the new website live now (anything else: later, with ~/.crtdh/crtdh go-live): ' ANSWER || ANSWER=""
if [ "$ANSWER" = yes ]; then
  "$ROOT/crtdh" go-live || { printf '\nThe publish did not finish. The old site stays live. Logs: ~/.crtdh/crtdh logs worker\n'; exit 1; }
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
