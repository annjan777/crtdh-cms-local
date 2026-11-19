#!/usr/bin/env bash
# docker compose for the staging stack: base file + staging override + staging env, from any folder.
#   deploy/staging/dc.sh ps
#   deploy/staging/dc.sh logs -f worker publish-agent
#   deploy/staging/dc.sh exec cms python manage.py check --deploy
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DEPLOY=$(dirname "$HERE")
if [ ! -f "$HERE/.env.staging" ]; then
    echo "dc.sh: $HERE/.env.staging is missing; run deploy/staging/setup.sh first" >&2
    exit 1
fi
exec docker compose --env-file "$HERE/.env.staging" \
    -f "$DEPLOY/docker-compose.yml" -f "$HERE/docker-compose.staging.yml" "$@"
