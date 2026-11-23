#!/usr/bin/env bash
# CRTDH website + CMS on academicweb: download, then install / update / repair.
#
#   curl -fsSL https://raw.githubusercontent.com/annjan777/crtdh-cms-local/dev/deploy/academicweb/install.sh -o /tmp/crtdh-install.sh && bash /tmp/crtdh-install.sh
#
# Why not git clone into the home folder: the home folder is on a shared network drive (/data) that refuses when
# thousands of files are created quickly ("Too many open files"). So the programs (code, Python and Node packages,
# database) go on this server's own disk, chosen and tested below, and only small things stay in ~/.crtdh:
# settings, backups, and copies of this script and the control script (so a wiped program folder can be rebuilt).
#
#   bash ~/.crtdh/install.sh            first install (asks 3 things, then "yes" before going live)
#   bash ~/.crtdh/install.sh --update   newest code, keep everything else  (= ~/.crtdh/crtdh update)
#   bash ~/.crtdh/install.sh --repair   rebuild a missing program folder, restore data from the nightly backup
set -euo pipefail

KEEP="$HOME/.crtdh"
BRANCH="${CRTDH_BRANCH:-dev}"
TARBALL="${CRTDH_TARBALL:-https://codeload.github.com/annjan777/crtdh-cms-local/tar.gz/refs/heads/$BRANCH}"
MODE="${1:-}"
umask 022

die() { printf '\nSTOPPED: %s\nNothing on the live website was changed.\n' "$*" >&2; exit 1; }
[ "$(id -u)" != 0 ] || die "run this as the website user (crtdh), not root"
for c in curl tar gzip df mktemp; do command -v "$c" >/dev/null || die "the command '$c' is missing"; done
mkdir -p "$KEEP/backups" && chmod 700 "$KEEP"

# A failed "git clone" into ~/.crtdh/app (the network drive) is not used any more.
if [ -d "$KEEP/app" ]; then
  printf 'Removing the earlier half-finished download from the network drive...\n'
  rm -rf "$KEEP/app" 2>/dev/null || mv "$KEEP/app" "$KEEP/app.unused.$$" 2>/dev/null || true
fi

# ---- where the programs go: a local disk where we can create many files and run programs -----------------------
works_here() {
  local d="$1" t
  mkdir -p "$d" 2>/dev/null && chmod 700 "$d" 2>/dev/null || return 1
  t="$(mktemp -d "$d/.probe.XXXXXX" 2>/dev/null)" || return 1
  local i ok=1
  for i in $(seq 1 3000); do : > "$t/f$i" 2>/dev/null || { ok=0; break; }; done
  if [ "$ok" = 1 ]; then cp /bin/true "$t/x" 2>/dev/null && "$t/x" 2>/dev/null || ok=0; fi
  rm -rf "$t"
  [ "$ok" = 1 ] || return 1
  [ "$(df -Pk "$d" | awk 'NR==2 {print $4}')" -gt 4000000 ] || return 1   # 4 GB free
}

INST=""
[ -f "$KEEP/install-dir" ] && INST="$(cat "$KEEP/install-dir")"
if [ -z "$INST" ] || ! works_here "$INST"; then
  printf 'Finding a local disk for the programs...\n'
  INST=""
  for cand in "${CRTDH_INSTALL_CANDIDATE:-}" "/var/tmp/crtdh-$(id -un)" "/tmp/crtdh-$(id -un)"; do
    [ -n "$cand" ] || continue
    if works_here "$cand"; then INST="$cand"; break; fi
  done
  [ -n "$INST" ] || die "no local folder where thousands of files can be created and programs run (tried /var/tmp, /tmp)"
  printf '%s\n' "$INST" > "$KEEP/install-dir"
fi
printf 'Programs folder: %s\n' "$INST"

# ---- code: one archive, unpacked next to the old copy, then swapped in ----------------------------------------------
if [ "$MODE" != "--repair" ] || [ ! -d "$INST/app/backend" ]; then
  printf 'Downloading the code...\n'
  rm -rf "$INST/app.new" "$INST/app.old"; mkdir -p "$INST/app.new"
  curl -fsSL -m 300 "$TARBALL" | tar -xz -C "$INST/app.new" --strip-components=1 || die "downloading the code failed"
  [ -f "$INST/app.new/deploy/academicweb/setup.sh" ] || die "the download is incomplete"
  [ -d "$INST/app" ] && mv "$INST/app" "$INST/app.old"
  mv "$INST/app.new" "$INST/app"
  rm -rf "$INST/app.old"
fi

# Small copies on the persistent drive: they rebuild everything if the programs folder is ever wiped.
cp "$INST/app/deploy/academicweb/install.sh" "$KEEP/install.sh"
cp "$INST/app/deploy/academicweb/crtdh" "$KEEP/crtdh"
chmod 700 "$KEEP/install.sh" "$KEEP/crtdh"

export CRTDH_KEEP="$KEEP" CRTDH_INSTALL="$INST"
exec bash "$INST/app/deploy/academicweb/setup.sh" "$MODE"
