# Publish worker image: the backend (Django, run_publish_worker) plus Node and frontend/ with the dependencies its
# `npm run build` needs, so the worker can snapshot -> build the static site -> pack the tarball (docs/GO-LIVE.md).
# Build context: the repository root (deploy/docker-compose.yml: context .., dockerfile deploy/worker/Dockerfile);
# deploy/worker/Dockerfile.dockerignore keeps it to backend/, frontend/ and this folder.
#
# Runs as uid 10001 with a read-only root file system. Writable at run time:
#   /data/publish  (named volume publish_data: snapshots, content-hashed media, tarballs; the cms reads tarballs)
#   /tmp           (tmpfs: the site build output /tmp/site/build/client, Vite/React Router temp files, npm cache)
# frontend/ itself stays read-only: its temp folders are symlinks into /tmp, made by crtdh-build-site.

# ---- frontend: dependencies for `npm run build` (vite and @react-router/dev are devDependencies) --------------------
FROM node:22-bookworm-slim AS frontend
WORKDIR /srv/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY frontend/ ./
RUN rm -rf build dist .react-router node_modules/.vite node_modules/.vite-temp snapshot.json \
    && ln -s /tmp/frontend/vite-temp node_modules/.vite-temp \
    && ln -s /tmp/frontend/vite-cache node_modules/.vite \
    && ln -s /tmp/frontend/react-router .react-router

# ---- worker: backend image + node + frontend -----------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
# Hash-pinned (pip-compile --generate-hashes); any unpinned or altered package fails the build.
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Node (same binary as the frontend stage; needs only glibc and libgcc_s) and npm, for `npm run build`.
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && node --version && npm --version

COPY --from=frontend /srv/frontend /srv/frontend
COPY deploy/worker/build-site.sh /usr/local/bin/crtdh-build-site
COPY backend/ ./
RUN chmod 755 /usr/local/bin/crtdh-build-site \
    && rm -f .env && useradd --system --no-create-home --uid 10001 app \
    && mkdir -p /data/media /data/static /data/publish && chown app:app /data/media /data/static /data/publish

# run_frontend_build() runs FRONTEND_BUILD_CMD with SNAPSHOT_PATH (this publish's snapshot.json) and
# BUILD_OUTPUT_DIR (= FRONTEND_BUILD_OUTPUT, read back for the tarball) in its environment.
ENV PUBLISH_ROOT=/data/publish \
    FRONTEND_BUILD_CMD=/usr/local/bin/crtdh-build-site \
    FRONTEND_BUILD_OUTPUT=/tmp/site/build/client \
    HOME=/tmp \
    NPM_CONFIG_CACHE=/tmp/npm-cache \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false

USER app
CMD ["python", "manage.py", "run_publish_worker"]
