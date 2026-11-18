#!/usr/bin/env sh
# Supply-chain and static security checks for the backend. Exit non-zero on any finding.
set -eu
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"
echo "== pip-audit (hash-pinned runtime deps)"
"$PY" -m pip_audit -r requirements.txt --require-hashes --progress-spinner off
echo "== bandit"
"$PY" -m bandit -q -c bandit.yaml -r apps config -ll
echo "== lock is current"
"$PY" -m piptools compile -q --generate-hashes --allow-unsafe --strip-extras -o /tmp/requirements.check.txt requirements.in
grep -E '^[a-z0-9].*==' requirements.txt > /tmp/req.current
grep -E '^[a-z0-9].*==' /tmp/requirements.check.txt > /tmp/req.fresh
cmp -s /tmp/req.current /tmp/req.fresh || { echo "requirements.txt is stale: re-run pip-compile"; exit 1; }
echo "OK"
