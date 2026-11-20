#!/usr/bin/env bash
# Serve build/client with Apache 2.4 under "AllowOverride FileInfo" only (the most a shared host may allow)
# and check that the generated .htaccess does not 500: every sitemap URL returns 200, "/about" 301s to
# "/about/", the old site's /about.html etc. 301 to the new pages, an unknown path gets 404, and the security headers are present.
# Usage: scripts/apache-check.sh [AllowOverride value, default FileInfo]   (needs apache2 and curl; run as root
# or a user that may bind 127.0.0.1:8089)
set -euo pipefail
OVR="${1:-FileInfo}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="${BUILD_DIR:-$HERE/build/client}"
WORK="$(mktemp -d /tmp/crtdh-apache.XXXXXX)"
PORT="${APACHE_PORT:-8089}"
trap 'apache2 -f "$WORK/httpd.conf" -k stop >/dev/null 2>&1 || true; sleep 0.3; rm -rf "$WORK"' EXIT
chmod 755 "$WORK"
cp -r "$BUILD" "$WORK/www"
chmod -R a+rX "$WORK/www"
RUNAS="$(id -un)"; [ "$(id -u)" = 0 ] && RUNAS=www-data
cat > "$WORK/httpd.conf" <<EOF
ServerRoot /etc/apache2
Listen 127.0.0.1:$PORT
PidFile $WORK/httpd.pid
ErrorLog $WORK/error.log
LogLevel warn
Include /etc/apache2/mods-enabled/*.load
Include /etc/apache2/mods-enabled/mime.conf
Include /etc/apache2/mods-enabled/dir.conf
TypesConfig /etc/mime.types
User $RUNAS
Group $RUNAS
ServerName localhost
DocumentRoot $WORK/www
<Directory $WORK/www>
  Options Indexes FollowSymLinks
  AllowOverride $OVR
  Require all granted
</Directory>
EOF
apache2 -f "$WORK/httpd.conf" -k start
for _ in 1 2 3 4 5 6 7 8 9 10; do curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.2; done

fail=0
check() { # url expected-status [expected-redirect]
  local got
  got="$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' "http://127.0.0.1:$PORT$1")"
  if [ "${got%% *}" != "$2" ] || { [ -n "${3:-}" ] && [ "${got#* }" != "$3" ]; }; then
    echo "FAIL $1 -> $got (expected $2 ${3:-})"; fail=1
  else
    echo "ok   $1 -> $got"
  fi
}
site="$(grep -o '<loc>[^<]*' "$BUILD/sitemap.xml" | head -1 | sed 's#<loc>##; s#/$##')"
for loc in $(grep -o '<loc>[^<]*' "$BUILD/sitemap.xml" | sed 's#<loc>##'); do check "${loc#$site}" 200; done
check /about 301 "http://127.0.0.1:$PORT/about/"
check /assets/ 200
# Old hand-written site URLs move to the new pages; /index.html still serves the home page.
for old in about team innovations facilities services product enterprises social-impact media contact; do
  check "/$old.html" 301 "http://127.0.0.1:$PORT/$old/"
done
check /index.html 200
check /About.html 404
check /no-such-page/ 404
check /sitemap.xml 200
headers="$(curl -sI "http://127.0.0.1:$PORT/about/")"
for h in Content-Security-Policy X-Content-Type-Options X-Frame-Options; do
  grep -qi "^$h:" <<<"$headers" && echo "ok   header $h" || { echo "FAIL header $h missing"; fail=1; }
done
if [ "$fail" != 0 ]; then echo "--- error.log"; tail -20 "$WORK/error.log"; exit 1; fi
echo "apache-check: AllowOverride $OVR — all pages 200"
