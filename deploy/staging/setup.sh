#!/usr/bin/env bash
# CRTDH staging on a homelab (macOS or Linux): one command, safe to run again.
#
#   deploy/staging/setup.sh               set up / update and start everything
#   deploy/staging/setup.sh --dry-run     write the env, keys and agent config into a temporary folder,
#                                         validate them and print what would run; touches nothing else
#   deploy/staging/setup.sh --new-token   ask for the Cloudflare tunnel token again
#   deploy/staging/setup.sh --with-access the CMS host is behind Cloudflare Access: ask for the agent's service token
#
# Hostnames (override with environment variables): SITE_HOST=crtdh.annjan.in CMS_HOST=cms-crtdh.annjan.in
# MCP_HOST=mcp-crtdh.annjan.in CONTACT_HOST=contact-crtdh.annjan.in
#
# Secrets are written only to deploy/staging/.env.staging and deploy/staging/secrets/ (both git-ignored, 0600/0700).
# The script prints a secret only where it must be copied once: the Claude OAuth client (printed by the CMS
# command itself). It never asks for, prints or stores the admin password: you type it into the CMS prompt.
set -euo pipefail
umask 077

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DEPLOY=$(dirname "$HERE")
REPO=$(dirname "$DEPLOY")

SITE_HOST=${SITE_HOST:-crtdh.annjan.in}
CMS_HOST=${CMS_HOST:-cms-crtdh.annjan.in}
MCP_HOST=${MCP_HOST:-mcp-crtdh.annjan.in}
CONTACT_HOST=${CONTACT_HOST:-contact-crtdh.annjan.in}
MIN_COMPOSE=2.24.4

DRY_RUN=0
NEW_TOKEN=0
WITH_ACCESS=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --new-token) NEW_TOKEN=1 ;;
        --with-access) WITH_ACCESS=1 ;;
        -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $arg (try --help)" >&2; exit 2 ;;
    esac
done

if [ "$DRY_RUN" = 1 ]; then
    OUT=$(mktemp -d "${TMPDIR:-/tmp}/crtdh-staging-dryrun.XXXXXX")
else
    OUT=$HERE
fi
ENV_FILE=$OUT/.env.staging
SECRETS=$OUT/secrets
OS=$(uname -s)
ARCH=$(uname -m)

# ----------------------------------------------------------------------------------------------------- helpers
bold() { if [ -t 1 ]; then printf '\033[1m%s\033[0m\n' "$*"; else printf '%s\n' "$*"; fi; }
step() { echo; bold "== $*"; }
info() { printf '   %s\n' "$*"; }
ok()   { printf '   ok    %s\n' "$*"; }
warn() { printf '   WARN  %s\n' "$*" >&2; }
die()  { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

dc() {
    docker compose --env-file "$ENV_FILE" -f "$DEPLOY/docker-compose.yml" -f "$HERE/docker-compose.staging.yml" "$@"
}

# Run "python manage.py shell -c CODE" in the running cms container; prints the last stdout line.
django() {
    dc exec -T cms python manage.py shell -c "$1" 2>/dev/null | tr -d '\r' | tail -n 1
}

# 64 random letters/digits from the kernel CSPRNG (no python/openssl needed; works with macOS's bash 3.2).
gen_secret() {
    local s
    s=$(head -c 4096 /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9' | cut -c1-64)
    [ "${#s}" -eq 64 ] || die "could not generate a random secret"
    printf '%s' "$s"
}

# Value of KEY in an env file ("" if absent), exactly as written (quotes included).
env_get() {
    [ -f "$1" ] || return 0
    { grep -m1 "^$2=" "$1" || true; } | cut -d= -f2-
}

mask() { local v=$1; if [ "${#v}" -gt 8 ]; then printf '%s…(%d chars)' "${v:0:4}" "${#v}"; else printf '***'; fi; }

version_ge() { # version_ge 2.29.1 2.24.4
    local IFS=.
    # shellcheck disable=SC2206
    local va=($1) vb=($2) i x y
    for i in 0 1 2; do
        x=${va[$i]:-0}; x=${x%%[!0-9]*}; x=${x:-0}
        y=${vb[$i]:-0}
        [ "$x" -gt "$y" ] && return 0
        [ "$x" -lt "$y" ] && return 1
    done
    return 0
}

print_docker_install() {
    echo
    bold "How to install Docker on this machine ($OS $ARCH)"
    case "$OS" in
        Darwin)
            local macos; macos=$(sw_vers -productVersion 2>/dev/null || echo unknown)
            local chip="Intel chip"; [ "$ARCH" = arm64 ] && chip="Apple silicon"
            cat <<EOF
   macOS $macos on $chip. Pick ONE of these:

   A) Docker Desktop (GUI; free for personal use):
      https://docs.docker.com/desktop/setup/install/mac-install/  -> "Docker Desktop for Mac with $chip"
      Docker Desktop supports only the current and the two previous major macOS releases; if macOS $macos is
      older, use B, or install Ubuntu Server on this Mac instead.
      For a home server: Settings -> General -> "Start Docker Desktop when you sign in", Resources -> Memory >= 6 GB,
      and stop the Mac sleeping (System Settings -> Energy / Battery -> prevent automatic sleeping).

   B) Colima (no GUI; needs Homebrew from https://brew.sh):
      brew install colima docker docker-compose docker-buildx
      mkdir -p ~/.docker/cli-plugins
      ln -sfn "\$(brew --prefix)/opt/docker-compose/bin/docker-compose" ~/.docker/cli-plugins/docker-compose
      ln -sfn "\$(brew --prefix)/opt/docker-buildx/bin/docker-buildx" ~/.docker/cli-plugins/docker-buildx
      colima start --cpu 2 --memory 6 --disk 40
      brew services start colima        # start it again after a reboot

   (OrbStack also works: brew install --cask orbstack.)
   Then run this script again.
EOF
            ;;
        Linux)
            local id="" like="" codename=""
            if [ -r /etc/os-release ]; then
                # shellcheck disable=SC1091
                id=$(. /etc/os-release && echo "${ID:-}")
                # shellcheck disable=SC1091
                like=$(. /etc/os-release && echo "${ID_LIKE:-}")
                # shellcheck disable=SC1091
                codename=$(. /etc/os-release && echo "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}")
            fi
            local repo=""
            case "$id" in
                ubuntu) repo=ubuntu ;;
                debian|raspbian) repo=debian ;;
            esac
            if [ -n "$repo" ] && [ -n "$codename" ]; then
                cat <<EOF
   $id ($codename): Docker Engine from Docker's apt repository (docs.docker.com/engine/install/$repo/):

      sudo apt-get update
      sudo apt-get install -y ca-certificates curl
      sudo install -m 0755 -d /etc/apt/keyrings
      sudo curl -fsSL https://download.docker.com/linux/$repo/gpg -o /etc/apt/keyrings/docker.asc
      sudo chmod a+r /etc/apt/keyrings/docker.asc
      echo "deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$repo $codename stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
      sudo apt-get update
      sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
      sudo usermod -aG docker "\$USER"     # then sign out and back in
      docker run --rm hello-world

   Then run this script again (as your normal user, not with sudo).
EOF
            else
                cat <<EOF
   Linux distribution "${id:-unknown}" (like: ${like:-?}). Follow the page for it, using the package-repository
   method (not the convenience script): https://docs.docker.com/engine/install/
   Install docker-ce, docker-buildx-plugin and docker-compose-plugin, add yourself to the docker group,
   then run this script again.
EOF
            fi
            ;;
        *)
            echo "   Unsupported OS $OS: this kit supports macOS and Linux." ;;
    esac
}

# ----------------------------------------------------------------------------------------------------- 1. checks
preflight() {
    step "1/9 Checking this machine"
    info "OS $OS, CPU $ARCH, repo $REPO"
    case "$ARCH" in
        x86_64|amd64|arm64|aarch64) ok "CPU architecture $ARCH has images for every service" ;;
        *) warn "CPU architecture $ARCH: postgres, python, node, nginx, httpd or cloudflared may have no image for it" ;;
    esac
    [ "$(id -u)" = 0 ] && warn "running as root: run it as your normal user (in the docker group) so the files it makes are yours"
    command -v ssh-keygen >/dev/null 2>&1 || {
        [ "$OS" = Linux ] && info "Debian/Ubuntu: sudo apt-get install -y openssh-client"
        die "ssh-keygen not found (needed for the SFTP keys)"; }
    ok "ssh-keygen"
    command -v curl >/dev/null 2>&1 || die "curl not found (needed to wait for the tunnel)"

    local missing=0
    if ! command -v docker >/dev/null 2>&1; then
        warn "docker is not installed"; missing=1
    elif ! docker compose version >/dev/null 2>&1; then
        warn "the Docker Compose v2 plugin (\"docker compose\") is not installed"; missing=1
    fi
    if [ "$missing" = 1 ]; then
        print_docker_install
        [ "$DRY_RUN" = 1 ] && { warn "dry run: carrying on without Docker"; return 0; }
        exit 1
    fi
    local cv; cv=$(docker compose version --short 2>/dev/null | sed 's/^v//')
    if version_ge "$cv" "$MIN_COMPOSE"; then ok "Docker Compose $cv"
    else
        [ "$DRY_RUN" = 1 ] || die "Docker Compose $cv is too old: need $MIN_COMPOSE or newer (update Docker Desktop / the docker-compose-plugin package)"
        warn "Docker Compose $cv is older than $MIN_COMPOSE"
    fi
    if docker buildx version >/dev/null 2>&1; then ok "docker buildx"
    else warn "docker buildx missing: the builds need BuildKit (install docker-buildx-plugin / docker-buildx)"; fi
    if ! docker info >/dev/null 2>&1; then
        case "$OS" in
            Darwin) info "Start Docker Desktop (or: colima start / open -a OrbStack), wait until it is running, then retry." ;;
            Linux)  info "Start it: sudo systemctl enable --now docker. If that is not it: add yourself to the docker group (sudo usermod -aG docker \$USER) and sign in again." ;;
        esac
        [ "$DRY_RUN" = 1 ] && { warn "dry run: Docker daemon not reachable; carrying on"; return 0; }
        die "cannot talk to the Docker daemon"
    fi
    local mem; mem=$(docker info --format '{{.MemTotal}}' 2>/dev/null || echo 0)
    if [ "${mem:-0}" -lt 3800000000 ] 2>/dev/null; then
        warn "Docker has $((mem / 1048576)) MB of memory; the site build in the worker needs about 4 GB (raise it in Docker Desktop / colima start --memory 6)"
    else
        ok "Docker memory $((mem / 1048576)) MB"
    fi
    if [ "$OS" = Darwin ]; then
        case "$REPO" in
            /Users/*) ;;
            *) warn "the repo is outside /Users: Docker Desktop shares only /Users (and /tmp, /Volumes, /private) by default; bind mounts of deploy/staging may fail" ;;
        esac
    fi
    if [ "$DRY_RUN" = 0 ] && command -v git >/dev/null 2>&1; then
        { git -C "$REPO" check-ignore -q deploy/staging/.env.staging \
            && git -C "$REPO" check-ignore -q deploy/staging/secrets/x; } \
            || die ".gitignore does not cover deploy/staging/.env.staging and deploy/staging/secrets/; refusing to write secrets"
        ok ".env.staging and secrets/ are git-ignored"
    fi
}

# ----------------------------------------------------------------------------------------------------- 2. env
write_env() {
    step "2/9 Environment file ($ENV_FILE)"
    local old=$ENV_FILE
    [ "$DRY_RUN" = 1 ] && old=$HERE/.env.staging-does-not-exist   # dry run never reads the real file
    local secret_key pg_pw hmac internal image
    secret_key=$(env_get "$old" SECRET_KEY);         [ -n "$secret_key" ] || secret_key=$(gen_secret)
    pg_pw=$(env_get "$old" POSTGRES_PASSWORD);       [ -n "$pg_pw" ]      || pg_pw=$(gen_secret)
    hmac=$(env_get "$old" AGENT_HMAC_SECRET);        [ -n "$hmac" ]       || hmac=$(gen_secret)
    internal=$(env_get "$old" CMS_INTERNAL_SECRET);  [ -n "$internal" ]   || internal=$(gen_secret)
    [ -f "$old" ] && ok "kept the existing secrets (the database already uses that password)"

    image=$(env_get "$old" CLOUDFLARED_IMAGE)
    case "$image" in
        *@sha256:*) ok "cloudflared image stays pinned: $image" ;;
        *)
            if [ "$DRY_RUN" = 1 ]; then
                image="cloudflare/cloudflared:latest"
                info "dry run: CLOUDFLARED_IMAGE left unpinned ($image); a real run pins it by digest"
            else
                local tag=${CLOUDFLARED_TAG:-latest}
                info "pulling cloudflare/cloudflared:$tag to pin it by digest"
                docker pull -q "cloudflare/cloudflared:$tag" >/dev/null
                image=$(docker image inspect --format '{{index .RepoDigests 0}}' "cloudflare/cloudflared:$tag")
                case "$image" in *@sha256:*) ok "pinned $image" ;; *) die "could not read the cloudflared image digest" ;; esac
            fi ;;
    esac
    local access_id=${STAGING_ACCESS_CLIENT_ID:-$(env_get "$old" STAGING_ACCESS_CLIENT_ID)}
    # Kept from an earlier run if you changed them; otherwise the staging defaults.
    local ts_secret ts_site email_url notify from
    ts_secret=$(env_get "$old" TURNSTILE_SECRET);  ts_secret=${ts_secret:-1x0000000000000000000000000000000AA}
    ts_site=$(env_get "$old" TURNSTILE_SITE_KEY);  ts_site=${ts_site:-1x00000000000000000000AA}
    email_url=$(env_get "$old" EMAIL_URL);         email_url=${email_url:-consolemail://}
    notify=$(env_get "$old" CONTACT_NOTIFY_EMAIL); notify=${notify:-staging-inbox@example.invalid}
    from=$(env_get "$old" DEFAULT_FROM_EMAIL);     from=${from:-\"CRTDH staging <no-reply@example.invalid>\"}
    [ "$ts_site" = 1x00000000000000000000AA ] && info "Turnstile: Cloudflare TEST keys (always pass; staging only)"
    [ "$email_url" = consolemail:// ] && info "email: printed to the logs (no SMTP)"

    local tmp; tmp=$(mktemp "$OUT/.env.staging.XXXXXX")
    cat > "$tmp" <<EOF
# CRTDH STAGING (homelab). Generated by deploy/staging/setup.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ). Git-ignored; 0600.
# Re-running setup.sh keeps the secrets below and rewrites everything else. Never copy this file to production.

# --- Hostnames (Cloudflare tunnel public hostnames; see deploy/staging/TUNNEL.md)
SITE_HOST=$SITE_HOST
CMS_HOST=$CMS_HOST
CONTACT_HOST=$CONTACT_HOST
PUBLIC_SITE_URL=https://$SITE_HOST

# --- Postgres
POSTGRES_DB=crtdh
POSTGRES_USER=crtdh
POSTGRES_PASSWORD=$pg_pw

# --- Django
SECRET_KEY=$secret_key
ALLOWED_HOSTS=$CMS_HOST,$CONTACT_HOST,$MCP_HOST
CSRF_TRUSTED_ORIGINS=https://$CMS_HOST
DATABASE_URL=postgres://crtdh:$pg_pw@db:5432/crtdh
CORS_ALLOWED_ORIGINS=https://$SITE_HOST

# --- Contact relay
# Default: Cloudflare's documented Turnstile TEST keys (developers.cloudflare.com/turnstile/troubleshooting/testing/):
# the site key always passes (visible widget) and the secret accepts its dummy token. NOT a real bot check.
# To use a real widget, put its keys here and run setup.sh again (it keeps what you set; then publish once).
TURNSTILE_SECRET=$ts_secret
TURNSTILE_SITE_KEY=$ts_site
# Default: no SMTP (consolemail://). Every email (contact alerts, review requests) is printed in the cms/worker
# logs instead. setup.sh keeps any value you set here.
EMAIL_URL=$email_url
CONTACT_NOTIFY_EMAIL=$notify
DEFAULT_FROM_EMAIL=$from
CONTACT_RETENTION_DAYS=365

# --- Publishing (the staging publish agent reads the same value from secrets/agent/agent-secret.txt)
CMS_PUBLIC_URL=https://$CMS_HOST
AGENT_HMAC_SECRET=$hmac
CMS_INTERNAL_SECRET=$internal
SITE_URL=https://$SITE_HOST
CONTACT_API_URL=https://$CONTACT_HOST/api/v1/contact/

# --- Claude connector
MCP_PUBLIC_URL=https://$MCP_HOST

# --- Cloudflare tunnel (token mode; the token itself is in secrets/tunnel.env, read only by cloudflared)
CLOUDFLARED_IMAGE=$image

# --- Staging kit only (docker-compose.staging.yml)
STAGING_UID=$(id -u)
STAGING_GID=$(id -g)
STAGING_ACCESS_CLIENT_ID=$access_id
EOF
    # Every variable deploy/.env.example requires must have a value here.
    local k missing=""
    while IFS= read -r k; do
        grep -q "^$k=." "$tmp" || missing="$missing $k"
    done < <(grep -E '^[A-Z][A-Z0-9_]*=' "$DEPLOY/.env.example" | cut -d= -f1)
    if [ -n "$missing" ]; then
        rm -f "$tmp"
        die "deploy/.env.example requires$missing, which setup.sh does not set yet. Add a staging value for it in write_env()."
    fi
    chmod 600 "$tmp"
    mv "$tmp" "$ENV_FILE"
    ok "every variable required by deploy/.env.example is set ($(grep -cE '^[A-Z][A-Z0-9_]*=' "$DEPLOY/.env.example") checked)"
    ok "wrote $ENV_FILE (0600)"
}

# ----------------------------------------------------------------------------------------------------- 3. token
write_tunnel_token() {
    step "3/9 Cloudflare tunnel token"
    local file=$SECRETS/tunnel.env tok=""
    mkdir -p "$SECRETS"; chmod 700 "$SECRETS"
    if [ "$DRY_RUN" = 1 ]; then
        printf 'TUNNEL_TOKEN=%s\n' "dry-run-placeholder-not-a-token" > "$file"
        info "dry run: not asking; wrote a placeholder to $file"
        return
    fi
    if [ "$NEW_TOKEN" = 0 ] && [ -n "$(env_get "$file" TUNNEL_TOKEN)" ]; then
        ok "keeping the saved token ($file); use --new-token to replace it"
        return
    fi
    [ -t 0 ] || die "no saved tunnel token and no terminal to ask for one; run setup.sh in a terminal"
    info "Cloudflare dashboard -> Networks -> Tunnels -> your tunnel -> install command: copy the long"
    info "token after \"--token\" (starts with eyJ). Steps: deploy/staging/TUNNEL.md section 1."
    while [ -z "$tok" ]; do
        printf '   Paste the tunnel token (input hidden), then Enter: '
        IFS= read -r -s tok; echo
        tok=$(printf '%s' "$tok" | tr -d '[:space:]')
        case "$tok" in
            *--token*|*cloudflared*) warn "paste only the token, not the whole command"; tok="" ;;
            eyJ*) [ "${#tok}" -ge 80 ] || { warn "that is too short for a tunnel token"; tok=""; } ;;
            "") ;;
            *) warn "a tunnel token starts with eyJ"; tok="" ;;
        esac
    done
    printf 'TUNNEL_TOKEN=%s\n' "$tok" > "$file"
    chmod 600 "$file"
    ok "saved to $file (0600); it is not printed"
}

# ----------------------------------------------------------------------------------------------------- 4. keys
write_keys_and_agent() {
    step "4/9 SFTP keys, agent secret and agent config"
    local ad=$SECRETS/agent sd=$SECRETS/sftp
    mkdir -p "$ad/keys" "$ad/state" "$sd"
    chmod 700 "$SECRETS" "$ad" "$ad/keys" "$ad/state" "$sd"

    if [ ! -f "$ad/keys/crtdh_publish_ed25519" ]; then
        ssh-keygen -q -t ed25519 -N '' -C crtdh-publish-agent -f "$ad/keys/crtdh_publish_ed25519"
        ok "agent SSH key: $ad/keys/crtdh_publish_ed25519"
    else ok "agent SSH key exists"; fi
    if [ ! -f "$sd/ssh_host_ed25519_key" ]; then
        ssh-keygen -q -t ed25519 -N '' -C crtdh-staging-sftp -f "$sd/ssh_host_ed25519_key"
        ok "SFTP host key: $sd/ssh_host_ed25519_key"
    else ok "SFTP host key exists"; fi
    chmod 600 "$ad/keys/crtdh_publish_ed25519" "$sd/ssh_host_ed25519_key"
    cp "$ad/keys/crtdh_publish_ed25519.pub" "$sd/authorized_key.pub"
    chmod 644 "$sd/authorized_key.pub" "$ad/keys/crtdh_publish_ed25519.pub" "$sd/ssh_host_ed25519_key.pub"

    # Trust the SFTP host key by pinning the key we just made (no trust-on-first-use needed).
    printf 'sftp %s\n' "$(cut -d' ' -f1,2 "$sd/ssh_host_ed25519_key.pub")" > "$ad/state/known_hosts"
    chmod 600 "$ad/state/known_hosts"
    ok "agent trusts the SFTP host key $(ssh-keygen -l -f "$sd/ssh_host_ed25519_key.pub" | cut -d' ' -f2)"

    env_get "$ENV_FILE" AGENT_HMAC_SECRET > "$ad/agent-secret.txt"
    chmod 600 "$ad/agent-secret.txt"
    ok "agent-secret.txt = AGENT_HMAC_SECRET (0600)"

    local access_id; access_id=$(env_get "$ENV_FILE" STAGING_ACCESS_CLIENT_ID)
    if [ "$WITH_ACCESS" = 1 ] && [ "$DRY_RUN" = 0 ]; then
        [ -t 0 ] || die "--with-access needs a terminal"
        info "Cloudflare Access service token for the agent (TUNNEL.md section 5, option B)."
        printf '   Client ID (ends in .access): '; IFS= read -r access_id
        local sec=""
        printf '   Client Secret (input hidden): '; IFS= read -r -s sec; echo
        [ -n "$access_id" ] && [ -n "$sec" ] || die "both the Client ID and the Client Secret are needed"
        printf '%s\n' "$sec" > "$ad/access-secret.txt"; chmod 600 "$ad/access-secret.txt"
        local tmp; tmp=$(mktemp "$OUT/.env.staging.XXXXXX")
        grep -v '^STAGING_ACCESS_CLIENT_ID=' "$ENV_FILE" > "$tmp"
        printf 'STAGING_ACCESS_CLIENT_ID=%s\n' "$access_id" >> "$tmp"
        chmod 600 "$tmp"; mv "$tmp" "$ENV_FILE"
        ok "access-secret.txt saved (0600)"
    fi
    local access_lines=""
    if [ -n "$access_id" ] && [ -s "$ad/access-secret.txt" ]; then
        access_lines="access_client_id = $access_id
access_secret_file = access-secret.txt"
    fi

    cat > "$ad/config.ini" <<EOF
; CRTDH publish agent: STAGING config, generated by deploy/staging/setup.sh. Paths are relative to this file
; (mounted at /agent in the publish-agent container). No secrets in here: the agent refuses them.
[cms]
url = https://$CMS_HOST
secret_file = agent-secret.txt
poll_seconds = 15
max_download_errors = 5
$access_lines

[sftp]
; the sftp stand-in container (docker-compose.staging.yml); chrooted, the account's home is /www
host = sftp
port = 22
user = crtdh
key_file = keys/crtdh_publish_ed25519
known_hosts = state/known_hosts

[site]
web_root = /www/public_html
strategy = auto
keep_releases = 3
verify_url = https://$SITE_HOST/
verify_marker = crtdh-build

[agent]
state_dir = state
EOF
    chmod 600 "$ad/config.ini"
    ok "agent config: $ad/config.ini"

    # Validate with the agent's own loader (stdlib only), on the host if python3 is there.
    if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
        PYTHONPATH=$REPO python3 -I - "$ad/config.ini" <<'PY' || die "the agent rejected its config (see above)"
import sys
sys.path.insert(0, __import__("os").environ.get("PYTHONPATH", ""))
from publish_agent.config import ConfigError, load
try:
    c = load(sys.argv[1])
    c.secret()
    c.access_headers()
except ConfigError as exc:
    print("   agent config error:", exc)
    raise SystemExit(1)
print(f"   ok    agent config loads: cms={c.cms_url} sftp={c.sftp_user}@{c.sftp_host}:{c.sftp_port} "
      f"web_root={c.web_root} verify={c.verify_url} access_token={'yes' if c.access_client_id else 'no'}")
PY
    else
        info "python3 not found on this machine: the config is validated inside the agent container in step 6"
    fi
}

# ----------------------------------------------------------------------------------------------------- dry run
dry_run_report() {
    step "Dry run result"
    info "Everything was written under $OUT (delete it when done: rm -rf '$OUT')"
    echo
    info "Generated $ENV_FILE (secrets masked):"
    local line k v
    while IFS= read -r line; do
        case "$line" in
            ""|\#*) continue ;;
        esac
        k=${line%%=*}; v=${line#*=}
        case "$k" in
            SECRET_KEY|POSTGRES_PASSWORD|AGENT_HMAC_SECRET|CMS_INTERNAL_SECRET) v=$(mask "$v") ;;
            DATABASE_URL) v="postgres://crtdh:$(mask "${v#postgres://crtdh:}")" ;;
        esac
        printf '     %s=%s\n' "$k" "$v"
    done < "$ENV_FILE"
    echo
    info "Files and permissions:"
    # shellcheck disable=SC2012
    (cd "$OUT" && find . -type f | sort | while IFS= read -r f; do
        printf '     %s %s\n' "$(ls -l "$f" | cut -c1-10)" "$f"; done)
    echo
    info "A real run would then do:"
    info "  docker compose --env-file deploy/staging/.env.staging -f deploy/docker-compose.yml -f deploy/staging/docker-compose.staging.yml build"
    info "  ... up -d   (migrate runs migrate + createcachetable + collectstatic first)"
    info "  ... exec -e CRTDH_ALLOW_SEED=1 cms python manage.py bootstrap_local   (only into an empty database)"
    info "  ... exec cms python manage.py create_baseline_snapshot"
    info "  ... exec cms python manage.py createsuperuser                          (you type the password)"
    info "  ... exec cms python manage.py create_claude_client                     (prints id + secret once)"
    info "  ... run --rm --no-deps publish-agent check                             (pinned host key, discovery)"
}

# ----------------------------------------------------------------------------------------------------- 5-9 docker
build_and_start() {
    step "5/9 Building images (first time: 10-20 minutes)"
    dc build
    step "6/9 Starting the stack"
    # depends_on makes `up` wait for the one-shot `migrate` service: migrate, createcachetable, collectstatic.
    dc up -d --remove-orphans || die "docker compose up failed. Look at: deploy/staging/dc.sh ps -a; deploy/staging/dc.sh logs migrate cms"
    local cid code
    cid=$(dc ps -a -q migrate)
    code=$(docker inspect --format '{{.State.ExitCode}}' "$cid")
    [ "$code" = 0 ] || die "migrate exited with $code: deploy/staging/dc.sh logs migrate"
    ok "migrations, cache table and collectstatic done (migrate exited 0)"
    # nginx looks up "cms" and "mcp" once, when it starts. When `up` recreates those containers (new image) but
    # not the gateway, the gateway keeps their old addresses and every API call fails with 502. Restart it.
    dc restart gateway >/dev/null || die "gateway restart failed: deploy/staging/dc.sh logs gateway"
    ok "gateway restarted (picks up the new cms and mcp containers)"
    local i
    for i in $(seq 1 30); do
        [ "$(django 'print("ready")')" = ready ] && break
        sleep 2
    done
    [ "$(django 'print("ready")')" = ready ] || die "the cms container is not answering: deploy/staging/dc.sh logs cms"
    ok "cms is running"
    dc run --rm --no-deps --entrypoint python publish-agent -c \
        'from publish_agent.config import load; c = load("/agent/config.ini"); c.secret(); c.access_headers(); print("   ok    agent config loads in its container")' \
        || die "the agent rejected its config"
    dc ps
}

load_content() {
    step "7/9 Content (the bundled fixture; no users)"
    local snaps navs
    snaps=$(django 'from apps.publishing.models import Snapshot; print(Snapshot.objects.count())')
    navs=$(django 'from apps.core.models import NavItem; print(NavItem.objects.count())')
    if [ "${navs:-0}" = 0 ] && [ "${snaps:-0}" = 0 ]; then
        info "empty database: importing the bundled content and seed media"
        dc exec -T -e CRTDH_ALLOW_SEED=1 cms python manage.py bootstrap_local
    else
        ok "content already present ($navs nav items); not importing again (it would overwrite edits)"
    fi
    if [ "${snaps:-0}" = 0 ]; then
        dc exec -T cms python manage.py create_baseline_snapshot
    else
        ok "baseline snapshot exists"
    fi
}

first_admin() {
    step "8/9 First admin and the Claude connector client"
    local n; n=$(django 'from django.contrib.auth import get_user_model as g; print(g().objects.filter(is_superuser=True).count())')
    if [ "${n:-0}" != 0 ]; then
        ok "an admin account already exists"
    elif [ -t 0 ]; then
        info "Create YOUR admin account now. Use your own name, not \"admin\". Type the password at the prompt:"
        info "this script does not see, print or store it."
        dc exec cms python manage.py createsuperuser || die "createsuperuser failed; run: deploy/staging/dc.sh exec cms python manage.py createsuperuser"
    else
        warn "no terminal: create the admin later with: deploy/staging/dc.sh exec cms python manage.py createsuperuser"
    fi

    local c; c=$(django 'from oauth2_provider.models import get_application_model as g; print(g().objects.filter(name="Claude", user__isnull=True).count())')
    if [ "${c:-0}" != 0 ]; then
        ok "the Claude OAuth client exists (new secret: deploy/staging/dc.sh exec cms python manage.py create_claude_client --rotate)"
    else
        echo
        bold "   Claude connector OAuth client: copy the id and secret into your password manager NOW."
        bold "   They are shown once and are not saved anywhere by this script. Clear the terminal afterwards."
        dc exec -T cms python manage.py create_claude_client
        echo
    fi
}

agent_check() {
    step "9/9 Tunnel and publish agent"
    local i code=""
    info "waiting for https://$CMS_HOST/ through the tunnel (up to 2 minutes)"
    for i in $(seq 1 24); do
        code=$(curl -s -o /dev/null -m 10 -w '%{http_code}' "https://$CMS_HOST/" || true)
        [ "$code" = 200 ] && break
        sleep 5
    done
    if [ "$code" != 200 ]; then
        warn "https://$CMS_HOST/ answers ${code:-nothing} (want 200). Check: deploy/staging/dc.sh logs cloudflared,"
        warn "and the public hostnames in TUNNEL.md section 2. Then run setup.sh again (it is safe) or:"
        warn "  deploy/staging/dc.sh run --rm --no-deps publish-agent check"
        return 0
    fi
    ok "tunnel up: https://$CMS_HOST/ -> 200"
    info "publish agent discovery against the SFTP stand-in (host key pinned, no --trust-host-key):"
    dc run --rm --no-deps publish-agent check \
        || warn "the agent check reported a problem (above). The agent keeps retrying; see: deploy/staging/dc.sh logs publish-agent"
    dc restart publish-agent >/dev/null
    ok "publish-agent restarted with the discovery result"
}

checklist() {
    echo
    bold "Done. Checklist:"
    cat <<EOF
   [ ] https://$CMS_HOST  sign in -> "Set up two-step sign-in": scan the QR code with an authenticator app,
       enter the 6-digit code, save the 10 recovery codes (shown once) in your password manager.
   [ ] First publish: change one small thing (e.g. a news item), Review & publish -> Publish. Watch it go
       queued -> building -> uploading -> Live (deploy/staging/dc.sh logs -f worker publish-agent).
   [ ] https://$SITE_HOST shows the site (view source: <meta name="crtdh-build" ...>).
   [ ] From any machine: deploy/staging/smoke.sh   (all PASS after the first publish)
   [ ] Claude connector (optional): claude.ai -> Customize -> Connectors -> Add custom connector,
       URL https://$MCP_HOST/mcp, Advanced settings -> the client id + secret printed above.
       Needs the WAF rule open to Anthropic's ranges only (TUNNEL.md section 4).
   [ ] Emails are not sent in staging: they appear in deploy/staging/dc.sh logs cms worker.
   [ ] Contact form uses Cloudflare's TEST Turnstile keys (always passes). Not a real bot check.
   Stop:  deploy/staging/teardown.sh        Wipe everything:  deploy/staging/teardown.sh -v
EOF
}

# ----------------------------------------------------------------------------------------------------- main
bold "CRTDH staging setup$([ "$DRY_RUN" = 1 ] && echo ' (DRY RUN)')"
info "site https://$SITE_HOST | cms https://$CMS_HOST | mcp https://$MCP_HOST | contact https://$CONTACT_HOST"
preflight
mkdir -p "$OUT"
write_env
write_tunnel_token
write_keys_and_agent
if [ "$DRY_RUN" = 1 ]; then
    dry_run_report
    exit 0
fi
build_and_start
load_content
first_admin
agent_check
checklist
