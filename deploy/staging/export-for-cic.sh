#!/usr/bin/env bash
# Run ON THE HOMELAB. Packs the staging CMS (content, drafts, history, photos, user accounts with their passwords)
# into one encrypted file and puts it at a random address on crtdh.annjan.in, so the CIC server can download it.
#
#   curl -fsSL https://raw.githubusercontent.com/annjan777/crtdh-cms-local/dev/deploy/staging/export-for-cic.sh | bash
#   ... | bash -s -- --cleanup        afterwards: delete the file from the web and from this machine
#
# The staging checkout is ~/crtdh-cms-v3 (set CRTDH_STAGING_DIR to use another). Nothing on staging is changed.
# Everything is inside main(), so bash reads the whole script before running any of it: with "curl | bash" a
# command that reads its input (docker compose exec) would otherwise swallow the rest of the script.
main() {
set -euo pipefail
echo "CRTDH staging export"
DIR="${CRTDH_STAGING_DIR:-$HOME/crtdh-cms-v3}"
DC="$DIR/deploy/staging/dc.sh"
PUBLIC="${CRTDH_STAGING_PUBLIC:-https://crtdh.annjan.in}"
RAW="${CRTDH_RAW:-https://raw.githubusercontent.com/annjan777/crtdh-cms-local/dev}"
WWW=/home/crtdh/www/public_html

die() { printf '\nSTOPPED: %s\n' "$*" >&2; exit 1; }
[ -x "$DC" ] || die "no staging checkout at $DIR (set CRTDH_STAGING_DIR=/path/to/it)"
"$DC" exec -T cms true </dev/null >/dev/null 2>&1 || die "the staging CMS is not running (start it: $DC up -d)"

# Where the live release keeps its photos: the "_media" line of the agent's .htaccess, inside the sftp container.
media_dir() {
  local rel
  rel="$("$DC" exec -T sftp cat "$WWW/.htaccess" </dev/null 2>/dev/null \
        | awk '$1 == "RewriteRule" && $2 == "^_media/(.+)$" { sub("/_media/[$]1$", "", $3); print $3; exit }')"
  [ -n "$rel" ] || return 1
  printf '%s/%s/_media' "$WWW" "$rel"
}

if [ "${1:-}" = --cleanup ]; then
  M="$(media_dir)" || die "could not find the web folder"
  "$DC" exec -T sftp sh -c "rm -f $M/_transfer-*.dat" </dev/null && rm -f "$HOME"/crtdh-transfer-*.dat
  echo "Removed the transfer file from $PUBLIC and from this machine."
  exit 0
fi

TOOL="$(mktemp)"; trap 'rm -f "$TOOL"' EXIT
curl -fsSL "$RAW/deploy/transfer.py" -o "$TOOL" || die "could not download the transfer tool from GitHub"
OUT="$HOME/crtdh-transfer-$(date +%Y%m%d-%H%M).dat"
umask 077
echo "Packing the staging CMS (a minute or two)..."
"$DC" exec -T cms python - export < "$TOOL" > "$OUT" 2> "$OUT.log" || { cat "$OUT.log" >&2; rm -f "$OUT"; die "packing failed"; }
PASS="$(sed -n 's/^PASSPHRASE //p' "$OUT.log")"; grep -v '^PASSPHRASE ' "$OUT.log"; rm -f "$OUT.log"
[ -n "$PASS" ] && [ -s "$OUT" ] || die "packing produced no file"

ID="$(head -c 18 /dev/urandom | od -An -tx1 | tr -d ' \n')"
M="$(media_dir)" || die "could not find the live release's photo folder (publish once on staging, then retry)"
"$DC" exec -T sftp sh -c "cat > $M/_transfer-$ID.dat && chmod 644 $M/_transfer-$ID.dat" < "$OUT" \
  || die "could not place the file in the web folder"
URL="$PUBLIC/_media/_transfer-$ID.dat"
SIZE="$(wc -c < "$OUT" | tr -d ' ')"
GOT="$(curl -s -o /dev/null -w '%{http_code} %{size_download}' "$URL")"
[ "$GOT" = "200 $SIZE" ] || die "the file is not downloadable at $URL (got: $GOT; expected 200 $SIZE). It is saved here: $OUT"

cat <<EOF

Ready. On the CIC server (logged in as crtdh), paste ONE of these:

  If the new site is NOT installed there yet:
    curl -fsSL $RAW/deploy/academicweb/install.sh -o /tmp/crtdh-install.sh && CRTDH_IMPORT=$URL bash /tmp/crtdh-install.sh

  If it is already installed:
    curl -fsSL $RAW/deploy/academicweb/install.sh -o /tmp/crtdh-install.sh && bash /tmp/crtdh-install.sh --update && ~/.crtdh/crtdh import $URL

When it asks for the pass phrase, type:   $PASS
(it is shown only here; anyone with both the address and this phrase can read the file)

Afterwards, delete the file:  curl -fsSL $RAW/deploy/staging/export-for-cic.sh | bash -s -- --cleanup
EOF
}
main "$@"
