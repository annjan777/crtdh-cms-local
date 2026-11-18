#!/usr/bin/env bash
# Capture the CRITICAL regression golden from the pre-v3 runtime SPA (frontend/ at the baseline commit)
# with the full seed. QA lane ports. Usage: scripts/capture-baseline-golden.sh [baseline-ref]
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd); PY=${PY:-/home/claude/venv/bin/python}
REF=${1:-834f59a}; WORK=$(mktemp -d); API=8600; SITE=3601
trap 'kill $(jobs -p) 2>/dev/null || true; pkill -f "runserver 127.0.0.1:$API" 2>/dev/null || true' EXIT
git -C "$REPO" archive "$REF" frontend backend | tar -x -C "$WORK"
cp -r "$REPO/backend/tests" "$WORK/backend/"   # seed loader only
export DATABASE_URL="sqlite:///$WORK/db.sqlite3" SECRET_KEY="golden-$RANDOM$RANDOM" DEBUG=True \
       ALLOWED_HOSTS=localhost,127.0.0.1 CORS_ALLOW_ALL_ORIGINS=True
(cd "$WORK/backend" && $PY manage.py migrate -v0 && \
  $PY manage.py shell -c "from tests.support.content import *; load_snapshot_into_db(FULL_SNAPSHOT_PATH)" && \
  setsid nohup $PY manage.py runserver 127.0.0.1:$API --noreload >"$WORK/backend.log" 2>&1 &)
(cd "$WORK/frontend" && cp -r "$REPO/frontend/node_modules" . && VITE_API_BASE_URL="http://localhost:$API/api/v1" npx vite build >/dev/null)
$PY "$REPO/tests/tools/static_server.py" --dir "$WORK/frontend/dist" --port $SITE --mode spa &
sleep 3
$PY "$REPO/tests/tools/capture_golden.py" --site "http://localhost:$SITE" --out "$REPO/tests/e2e/golden/public_content.json"
echo "golden written from $REF (work dir $WORK)"
