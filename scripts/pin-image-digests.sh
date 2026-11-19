#!/usr/bin/env bash
# Pin every Dockerfile base image to the digest its tag points at today (R-11 / F-11).
#   scripts/pin-image-digests.sh          show what would change (no edits)
#   scripts/pin-image-digests.sh --write  rewrite the FROM lines in place, then review with `git diff`
# Needs Docker with buildx (uses `docker buildx imagetools inspect`, read-only; pulls nothing). Run it on a machine
# that can reach Docker Hub, rebuild and test, then commit. Re-run it when you want newer base images.
set -euo pipefail
cd "$(dirname "$0")/.."
write=${1:-}
files=$(git ls-files '*Dockerfile' 'Dockerfile*' | grep -v dockerignore)
for f in $files; do
  grep -nE '^FROM [^ ]+' "$f" | while IFS=: read -r line rest; do
    ref=$(echo "$rest" | awk '{print $2}')
    case "$ref" in *@sha256:*|scratch) continue ;; esac
    digest=$(docker buildx imagetools inspect "$ref" --format '{{json .Manifest}}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["digest"])')
    echo "$f:$line  $ref  ->  $ref@$digest"
    if [ "$write" = "--write" ]; then
      python3 - "$f" "$line" "$ref" "$digest" <<'PY'
import sys
path, line, ref, digest = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
lines = open(path).read().split("\n")
lines[line - 1] = lines[line - 1].replace(ref, f"{ref}@{digest}", 1)
open(path, "w").write("\n".join(lines))
PY
    fi
  done
done
