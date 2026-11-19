#!/bin/sh
# FRONTEND_BUILD_CMD of the worker image (deploy/worker/Dockerfile). frontend/ is read-only, so the build writes
# only under /tmp (tmpfs): Vite/React Router temp folders (symlinked from frontend/) and the site itself
# (BUILD_OUTPUT_DIR, e.g. /tmp/site/build/client). React Router's prerender imports <build>/server/index.js,
# which must find frontend's packages: a node_modules link next to the build folder provides them.
set -eu
FRONTEND=${FRONTEND_DIR:-/srv/frontend}
: "${BUILD_OUTPUT_DIR:?set by the publish worker}"
: "${SNAPSHOT_PATH:?set by the publish worker}"
site_root=$(dirname "$(dirname "$BUILD_OUTPUT_DIR")")   # /tmp/site for /tmp/site/build/client
mkdir -p /tmp/frontend/vite-temp /tmp/frontend/vite-cache /tmp/frontend/react-router "$site_root"
ln -sfn "$FRONTEND/node_modules" "$site_root/node_modules"
exec npm --prefix "$FRONTEND" run build
