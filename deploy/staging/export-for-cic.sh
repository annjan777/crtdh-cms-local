#!/usr/bin/env bash
# Run ON THE HOMELAB. Packs the staging CMS (content, drafts, history, photos, user accounts with their passwords)
# into one encrypted file and puts it at a random address on crtdh.annjan.in, so the CIC server can download it.
#
#   curl -fsSL https://raw.githubusercontent.com/annjan777/crtdh-cms-local/dev/deploy/staging/export-for-cic.sh | bash
#   ... | bash -s -- --cleanup        afterwards: delete the file from the web and from this machine
#   ... | bash -s -- --github         also put the newest packed file on a temporary GitHub release
#   ... | bash -s -- --github-cleanup delete that release
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
  local rel ref sub found
  # 1. the agent's .htaccess says where /_media/ points
  rel="$("$DC" exec -T sftp sh -c "cat $WWW/.htaccess 2>/dev/null" </dev/null 2>/dev/null \
        | awk '$1 == "RewriteRule" && $2 == "^_media/(.+)$" { sub("/_media/[$]1$", "", $3); print $3; exit }')"
  if [ -n "$rel" ]; then printf '%s/%s/_media' "$WWW" "$rel"; return 0; fi
  # 2. otherwise: take one photo address from the live home page and find that file on the web server
  ref="$(curl -s -m 30 "$PUBLIC/" | grep -o '/_media/[A-Za-z0-9._/-]*' | head -1)"
  [ -n "$ref" ] || return 1
  sub="${ref#/_media/}"
  found="$("$DC" exec -T sftp find /home/crtdh -type f -path "*/_media/$sub" </dev/null 2>/dev/null | head -1)"
  [ -n "$found" ] || return 1
  printf '%s' "${found%/$sub}"
}

diagnose() {
  echo "--- what the web server holds" >&2
  "$DC" exec -T sftp sh -c 'ls -la /home/crtdh/www /home/crtdh/www/public_html 2>&1 | head -40; echo; head -30 /home/crtdh/www/public_html/.htaccess 2>&1' </dev/null >&2 || true
  echo "--- photo addresses on the home page:" >&2
  curl -s -m 30 "$PUBLIC/" | grep -o '/_media/[A-Za-z0-9._/-]*' | head -3 >&2 || true
}

# --github: put the newest packed file on a temporary GitHub release (for networks that block crtdh.annjan.in).
# The file stays encrypted; the pass phrase from the export is the same. --github-cleanup deletes the release.
REPO="${CRTDH_REPO_SLUG:-annjan777/crtdh-cms-local}"
if [ "${1:-}" = --github ] || [ "${1:-}" = --github-cleanup ]; then
  GH="$(command -v gh || true)"
  [ -n "$GH" ] || GH="$(ls "$HOME"/.crtdh-gh/*/bin/gh 2>/dev/null | head -1 || true)"
  if [ -z "$GH" ]; then
    # No install needed: GitHub's own command-line tool, unpacked into ~/.crtdh-gh
    echo "Getting the GitHub tool (about 15 MB, no install)..."
    case "$(uname -m)" in arm64|aarch64) A=arm64 ;; *) A=amd64 ;; esac
    case "$(uname -s)" in Darwin) PAT="macOS_${A}\.(zip|tar\.gz)" ;; *) PAT="linux_${A}\.tar\.gz" ;; esac
    U="$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest | grep -oE "https://[^\"]*_${PAT}" | head -1)"
    [ -n "$U" ] || die "could not find the GitHub tool to download"
    rm -rf "$HOME/.crtdh-gh" && mkdir -p "$HOME/.crtdh-gh" && curl -fsSL "$U" -o "$HOME/.crtdh-gh/gh.pkg" || die "downloading the GitHub tool failed"
    case "$U" in
      *.zip) (cd "$HOME/.crtdh-gh" && unzip -q gh.pkg) ;;
      *) tar -xzf "$HOME/.crtdh-gh/gh.pkg" -C "$HOME/.crtdh-gh" ;;
    esac || die "unpacking the GitHub tool failed"
    GH="$(ls "$HOME"/.crtdh-gh/*/bin/gh 2>/dev/null | head -1 || true)"
    [ -n "$GH" ] || die "the GitHub tool did not unpack as expected"
  fi
  gh() { "$GH" "$@"; }
  if ! gh auth status >/dev/null 2>&1; then
    echo "Sign in to GitHub: it shows a one-time code; open https://github.com/login/device on any phone or computer and enter it."
    gh auth login --hostname github.com --git-protocol https --web </dev/tty || die "GitHub sign-in did not finish"
  fi
  if [ "$1" = --github-cleanup ]; then
    for t in $(gh release list --repo "$REPO" --limit 50 </dev/null | awk -F'\t' '{print $3}' | grep '^crtdh-transfer-' || true); do
      gh release delete "$t" --repo "$REPO" --yes --cleanup-tag </dev/null && echo "deleted release $t"
    done
    exit 0
  fi
  F="$(ls -1t "$HOME"/crtdh-transfer-*.dat 2>/dev/null | head -1)"
  [ -n "$F" ] || die "no packed file in $HOME; run this script without --github first"
  TAG="crtdh-transfer-$(head -c 6 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  cp "$F" "/tmp/$TAG.dat"
  echo "Uploading $(du -h "$F" | cut -f1) to GitHub (a few minutes)..."
  gh release create "$TAG" "/tmp/$TAG.dat" --repo "$REPO" --prerelease --target dev --title "temporary transfer file" \
     --notes "Encrypted CMS transfer for the CIC server. Deleted after use." </dev/null >/dev/null || { rm -f "/tmp/$TAG.dat"; die "upload failed"; }
  rm -f "/tmp/$TAG.dat"
  URL="https://github.com/$REPO/releases/download/$TAG/$TAG.dat"
  GOT="$(curl -sL -r 0-7 "$URL" | head -c 7)"
  [ "$GOT" = CRTDHX1 ] || die "uploaded, but $URL does not download yet; wait a minute and test it in a browser"
  cat <<EOF2

Uploaded ($(basename "$F")). On the CIC server, use this address in place of the crtdh.annjan.in one:

  $URL

The pass phrase is the one printed when that file was packed.
Afterwards delete it:  curl -fsSL $RAW/deploy/staging/export-for-cic.sh | bash -s -- --github-cleanup
EOF2
  exit 0
fi

if [ "${1:-}" = --cleanup ]; then
  M="$(media_dir)" || { diagnose; die "could not find the web folder"; }
  "$DC" exec -T sftp sh -c "rm -f $M/_transfer-*.dat" </dev/null && rm -f "$HOME"/crtdh-transfer-*.dat
  echo "Removed the transfer file from $PUBLIC and from this machine."
  exit 0
fi

echo "Finding the web folder for the download..."
M="$(media_dir)" || { diagnose; die "could not find the live site's photo folder. Send a photo of this screen."; }
echo "  $M"
TOOL="$(mktemp)"; trap 'rm -f "$TOOL"' EXIT
curl -fsSL "$RAW/deploy/transfer.py" -o "$TOOL" || die "could not download the transfer tool from GitHub"
OUT="$HOME/crtdh-transfer-$(date +%Y%m%d-%H%M).dat"
umask 077
echo "Packing the staging CMS (a minute or two)..."
"$DC" exec -T cms python - export < "$TOOL" > "$OUT" 2> "$OUT.log" || { cat "$OUT.log" >&2; rm -f "$OUT"; die "packing failed"; }
PASS="$(sed -n 's/^PASSPHRASE //p' "$OUT.log")"; grep -v '^PASSPHRASE ' "$OUT.log"; rm -f "$OUT.log"
[ -n "$PASS" ] && [ -s "$OUT" ] || die "packing produced no file"

ID="$(head -c 18 /dev/urandom | od -An -tx1 | tr -d ' \n')"
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
