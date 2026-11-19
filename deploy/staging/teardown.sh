#!/usr/bin/env bash
# Stop the CRTDH staging stack.
#
#   deploy/staging/teardown.sh        stop and remove the containers; keep the data (database, media, site files)
#   deploy/staging/teardown.sh -v     ALSO delete the data volumes (database, media, published site) and the
#                                     agent's local state; asks you to type DELETE first (-y skips the question)
#
# Never deletes .env.staging, the tunnel token or the keys in secrets/, so setup.sh can start again with the same
# secrets. To forget those too, delete deploy/staging/.env.staging and deploy/staging/secrets/ yourself.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

WIPE=0; YES=0
for arg in "$@"; do
    case "$arg" in
        -v|--volumes) WIPE=1 ;;
        -y|--yes) YES=1 ;;
        -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $arg (try --help)" >&2; exit 2 ;;
    esac
done

if [ "$WIPE" = 0 ]; then
    "$HERE/dc.sh" down --remove-orphans
    echo "Stopped. Data kept. Start again: deploy/staging/setup.sh (or deploy/staging/dc.sh up -d)"
    exit 0
fi

echo "This deletes the staging database, media, published site and agent state (volumes of project crtdh-staging)."
if [ "$YES" = 0 ]; then
    [ -t 0 ] || { echo "no terminal to confirm; use -v -y" >&2; exit 1; }
    printf 'Type DELETE to continue: '
    read -r answer
    [ "$answer" = DELETE ] || { echo "Nothing deleted."; exit 1; }
fi
"$HERE/dc.sh" down -v --remove-orphans
# The agent's local state describes the server it published to, which is gone now. Keep known_hosts (the SFTP
# host key in secrets/sftp is reused).
STATE=$HERE/secrets/agent/state
if [ -d "$STATE" ]; then
    find "$STATE" -mindepth 1 -maxdepth 1 ! -name known_hosts -exec rm -rf -- {} +
fi
echo "Deleted. Next deploy/staging/setup.sh starts from an empty database (you create the admin again)."
