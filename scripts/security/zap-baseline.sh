#!/usr/bin/env bash
# OWASP ZAP baseline (passive) scan of a running stack. Needs Docker with network access to the target.
#   scripts/security/zap-baseline.sh https://localhost:3601            # public site (preprod)
#   scripts/security/zap-baseline.sh https://localhost:8600/api/v1/auth/csrf/   # CMS API surface
# Passive only: spiders and reads responses, sends no attacks, so it is safe against staging. Never point
# it at the production CIC host without the institute's permission. Report: test-results/zap-<host>.html
# Rule tuning: tests/security/zap-rules.tsv (WARN/IGNORE/FAIL per ZAP rule id, each with a reason).
# Manual fallback when Docker is unavailable (e.g. this sandbox): install ZAP desktop, Quick Start ->
# Automated Scan against the same URL with "Use traditional spider" only, then save the HTML report under
# test-results/ and file every Medium/High alert against the lane that owns the response.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../.." && pwd)
TARGET=${1:?usage: zap-baseline.sh <url>}
IMAGE=${ZAP_IMAGE:-ghcr.io/zaproxy/zaproxy:stable}
command -v docker >/dev/null && docker info >/dev/null 2>&1 || { echo "docker not available: use the manual fallback in this script's header"; exit 2; }
mkdir -p "$REPO/test-results"
NAME=$(echo "$TARGET" | sed -E 's#https?://##; s#[^A-Za-z0-9]+#-#g; s#-$##')
# --network host so the container reaches localhost services; -I: warnings do not fail, FAIL rules do.
docker run --rm --network host -v "$REPO/test-results:/zap/wrk:rw" -v "$REPO/tests/security:/zap/rules:ro" \
  "$IMAGE" zap-baseline.py -t "$TARGET" -c /zap/rules/zap-rules.tsv -r "zap-$NAME.html" -J "zap-$NAME.json" -I -m 3
