#!/usr/bin/env bash
# Static security scan (semgrep). Exit 1 on any ERROR finding.
#   scripts/security/semgrep.sh            project rules + registry packs (needs network for the packs)
#   SEMGREP_OFFLINE=1 scripts/security/semgrep.sh   project rules only (tests/security/semgrep-crtdh.yml)
# Install: pip install semgrep (kept out of requirements: dev/CI tool only). Report: test-results/semgrep.{json,txt}
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../.." && pwd); cd "$REPO"
SEMGREP=${SEMGREP:-semgrep}
command -v "$SEMGREP" >/dev/null || { echo "semgrep not installed (pip install semgrep)"; exit 2; }
mkdir -p test-results
CONFIGS=(--config tests/security/semgrep-crtdh.yml)
if [ "${SEMGREP_OFFLINE:-0}" != 1 ]; then
  CONFIGS+=(--config p/python --config p/django --config p/javascript --config p/react --config p/secrets)
fi
TARGETS=(backend publish_agent frontend/app frontend/src frontend/scripts admin/src)
EXISTING=(); for t in "${TARGETS[@]}"; do [ -e "$t" ] && EXISTING+=("$t"); done
"$SEMGREP" scan "${CONFIGS[@]}" --metrics=off --severity ERROR --severity WARNING \
  --exclude node_modules --exclude build --exclude dist --exclude migrations --exclude '*.min.js' \
  --json-output test-results/semgrep.json "${EXISTING[@]}" | tee test-results/semgrep.txt
# Gate: ERROR findings fail; WARNINGs are listed for triage but do not fail the build.
python3 - <<'PY'
import json, sys
r = json.load(open("test-results/semgrep.json"))
errs = [x for x in r.get("results", []) if x["extra"].get("severity") == "ERROR"]
warns = [x for x in r.get("results", []) if x["extra"].get("severity") == "WARNING"]
for x in errs + warns:
    print(f'{x["extra"]["severity"]:7} {x["path"]}:{x["start"]["line"]} {x["check_id"]}')
print(f"semgrep: {len(errs)} error(s), {len(warns)} warning(s), {len(r.get('errors', []))} scan error(s)")
sys.exit(1 if errs else 0)
PY
