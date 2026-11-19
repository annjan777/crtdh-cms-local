#!/usr/bin/env bash
# CRTDH staging smoke test. Run from ANY machine with bash and curl (no repo checkout or Docker needed):
#
#   deploy/staging/smoke.sh
#   SITE_HOST=... CMS_HOST=... MCP_HOST=... CONTACT_HOST=... deploy/staging/smoke.sh
#
# Prints PASS / FAIL / SKIP per check and exits 1 if anything FAILed.
# Before the first publish the public-site checks that need the built site are SKIPped (the placeholder is live).
# If the WAF rule restricting the MCP host to Anthropic's ranges is on (TUNNEL.md section 4), the MCP checks expect
# 403 from your IP instead; run them from a machine in those ranges, or turn the rule off, to test the app.
set -uo pipefail

SITE=https://${SITE_HOST:-crtdh.annjan.in}
CMS=https://${CMS_HOST:-cms-crtdh.annjan.in}
MCP=https://${MCP_HOST:-mcp-crtdh.annjan.in}
CONTACT=https://${CONTACT_HOST:-contact-crtdh.annjan.in}

command -v curl >/dev/null 2>&1 || { echo "smoke.sh needs curl" >&2; exit 2; }
TMP=$(mktemp -d "${TMPDIR:-/tmp}/crtdh-smoke.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
NPASS=0; NFAIL=0; NSKIP=0
UA="crtdh-staging-smoke/1"

pass() { NPASS=$((NPASS + 1)); printf 'PASS  %s\n' "$1"; }
fail() { NFAIL=$((NFAIL + 1)); printf 'FAIL  %s  -- %s\n' "$1" "$2"; }
skip() { NSKIP=$((NSKIP + 1)); printf 'SKIP  %s  -- %s\n' "$1" "$2"; }
section() { printf '\n== %s\n' "$1"; }

# req METHOD URL [curl args...]: sets CODE, and leaves headers in $TMP/h and body in $TMP/b. Never follows redirects.
req() {
    local method=$1 url=$2; shift 2
    CODE=$(curl -sS -m 20 -A "$UA" -X "$method" -D "$TMP/h" -o "$TMP/b" -w '%{http_code}' "$@" "$url" 2>"$TMP/e") || CODE=000
    tr -d '\r' < "$TMP/h" > "$TMP/h2" 2>/dev/null; mv "$TMP/h2" "$TMP/h" 2>/dev/null || true
}
hdr() { grep -i "^$1:" "$TMP/h" | tail -n 1 | cut -d: -f2- | sed 's/^ *//'; }
body_has() { grep -q -- "$1" "$TMP/b"; }

# check_code NAME METHOD URL WANT... [-- curl args]
check_code() {
    local name=$1 method=$2 url=$3; shift 3
    local want=() a
    while [ $# -gt 0 ] && [ "$1" != -- ]; do want+=("$1"); shift; done
    [ "${1:-}" = -- ] && shift
    req "$method" "$url" "$@"
    for a in "${want[@]}"; do [ "$CODE" = "$a" ] && { pass "$name ($CODE)"; return 0; }; done
    fail "$name" "got $CODE, want ${want[*]}$( [ "$CODE" = 000 ] && printf ' (%s)' "$(head -c 200 "$TMP/e")")"
    return 1
}

# check_header NAME HEADER EXPECTED-SUBSTRING (on the last response)
check_header() {
    local v; v=$(hdr "$2")
    if [ -z "$v" ]; then fail "$1" "no $2 header"
    elif [ -n "$3" ] && ! printf '%s' "$v" | grep -qi -- "$3"; then fail "$1" "$2: $v"
    else pass "$1"; fi
}

security_headers() { # $1 = label; the response must already be in $TMP/h
    check_header "$1: Content-Security-Policy" Content-Security-Policy "default-src 'self'"
    check_header "$1: CSP frame-ancestors none" Content-Security-Policy "frame-ancestors 'none'"
    check_header "$1: Strict-Transport-Security" Strict-Transport-Security "max-age=31536000"
    check_header "$1: X-Content-Type-Options" X-Content-Type-Options nosniff
    check_header "$1: X-Frame-Options" X-Frame-Options DENY
    check_header "$1: Referrer-Policy" Referrer-Policy ""
    check_header "$1: Permissions-Policy" Permissions-Policy "camera=()"
    check_header "$1: Cross-Origin-Opener-Policy" Cross-Origin-Opener-Policy same-origin
}

echo "CRTDH staging smoke: site $SITE | cms $CMS | mcp $MCP | contact $CONTACT"

# ------------------------------------------------------------------------------------------------ public site
section "Public site ($SITE)"
if check_code "GET /" GET "$SITE/" 200; then
    if body_has 'crtdh-staging-placeholder'; then
        PUBLISHED=0
        skip "built site checks" "the placeholder is live: publish once from the CMS, then run this again"
    else
        PUBLISHED=1
        build=$(grep -o '<meta name="crtdh-build" content="[^"]*"' "$TMP/b" | head -n 1 | sed 's/.*content="//; s/"$//')
        if [ -n "$build" ]; then pass "crtdh-build meta present ($build)"; else fail "crtdh-build meta" "not in the home page"; fi
        security_headers "site /"
        check_header "site /: HTML not cached" Cache-Control no-cache
    fi
else
    PUBLISHED=0
fi

if [ "$PUBLISHED" = 1 ]; then
    if check_code "GET /about (no slash) redirects" GET "$SITE/about" 301; then
        loc=$(hdr Location)
        case "$loc" in
            "$SITE/about/"|/about/) pass "/about -> $loc" ;;
            *) fail "/about redirect target" "Location: $loc (want $SITE/about/)" ;;
        esac
    fi
    check_code "GET /about/" GET "$SITE/about/" 200
    if check_code "unknown page is 404" GET "$SITE/no-such-page-$$/" 404; then
        if body_has '<html'; then pass "404 serves the designed 404.html"; else fail "404 body" "not the site's 404 page"; fi
        check_header "404 page: Content-Security-Policy" Content-Security-Policy "default-src 'self'"
    fi
    if check_code "GET /sitemap.xml" GET "$SITE/sitemap.xml" 200; then
        n=$(grep -c '<loc>' "$TMP/b" || true)
        if [ "${n:-0}" -ge 1 ]; then pass "sitemap lists $n URLs"; else fail "sitemap" "no <loc> entries"; fi
    fi
    if check_code "GET /robots.txt" GET "$SITE/robots.txt" 200; then
        if body_has 'Sitemap:'; then pass "robots.txt names the sitemap"; else fail "robots.txt" "no Sitemap: line"; fi
    fi
    req GET "$SITE/assets/"
    if body_has 'Index of'; then fail "/assets/ listing" "directory listing is on"; else pass "/assets/ is not a listing ($CODE)"; fi
    req GET "$SITE/_media/"
    if body_has 'Index of'; then fail "/_media/ listing" "directory listing is on"; else pass "/_media/ is not a listing ($CODE)"; fi
    req GET "$SITE/"; js=$(grep -o '/assets/[^"]*\.js' "$TMP/b" | head -n 1)
    if [ -n "$js" ]; then
        check_code "hashed asset $js" GET "$SITE$js" 200 && check_header "asset cached for a year" Cache-Control immutable
    else
        skip "hashed asset cache" "no /assets/*.js reference found in the home page"
    fi
fi
check_code ".htaccess is not served" GET "$SITE/.htaccess" 403 404
check_code "no CMS API on the public host" GET "$SITE/api/v1/" 404

# ------------------------------------------------------------------------------------------------ CMS
section "CMS ($CMS)"
ACCESS=0
if check_code "admin app (sign-in page) GET /" GET "$CMS/" 200 302; then
    if [ "$CODE" = 302 ]; then
        case "$(hdr Location)" in
            *cloudflareaccess.com*) ACCESS=1
                skip "admin app content and headers" "Cloudflare Access is in front of the CMS (TUNNEL.md section 5)" ;;
            *) fail "admin app" "302 to $(hdr Location), not the admin app" ;;
        esac
    else
        if body_has 'id="root"'; then pass "admin SPA index.html served"; else fail "admin SPA" "no #root element in /"; fi
        security_headers "cms /"
    fi
fi
if [ "$ACCESS" = 1 ]; then
    # Behind Access every path answers with Access's redirect or block before the CMS sees it.
    check_code "API behind Access: GET /api/v1/hero-slides/" GET "$CMS/api/v1/hero-slides/" 302 401 403
    check_code "agent API behind Access (service token only)" GET "$CMS/api/v1/agent/next/" 302 401 403
else
    check_code "SPA route /login" GET "$CMS/login" 200
    check_code "API needs a session: GET /api/v1/hero-slides/" GET "$CMS/api/v1/hero-slides/" 401 403
    check_code "API root needs a session: GET /api/v1/" GET "$CMS/api/v1/" 401 403
    check_code "agent API refuses unsigned calls" GET "$CMS/api/v1/agent/next/" 401 403
    check_code "Django admin is not exposed" GET "$CMS/admin/" 404
    check_code "OAuth sign-in entry /cms/login redirects to the SPA" GET "$CMS/cms/login" 302
fi

# ------------------------------------------------------------------------------------------------ contact
section "Contact relay ($CONTACT)"
check_code "GET on the contact endpoint refused" GET "$CONTACT/api/v1/contact/" 403 405
check_code "anything else on the contact host is 404" GET "$CONTACT/anything-$$" 404
check_code "POST without Turnstile is rejected" POST "$CONTACT/api/v1/contact/" 400 -- \
    -H 'Content-Type: application/json' -H "Origin: $SITE" --data '{}'
if check_code "CORS preflight from the site" OPTIONS "$CONTACT/api/v1/contact/" 200 204 -- \
    -H "Origin: $SITE" -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type'; then
    check_header "CORS allows only the site" Access-Control-Allow-Origin "$SITE"
fi
if check_code "CORS preflight from another origin" OPTIONS "$CONTACT/api/v1/contact/" 200 204 403 -- \
    -H 'Origin: https://evil.example' -H 'Access-Control-Request-Method: POST'; then
    if [ -n "$(hdr Access-Control-Allow-Origin)" ]; then fail "CORS other origin" "Access-Control-Allow-Origin: $(hdr Access-Control-Allow-Origin)"
    else pass "no CORS grant for another origin"; fi
fi

# ------------------------------------------------------------------------------------------------ MCP
section "Claude MCP ($MCP)"
req GET "$MCP/.well-known/oauth-protected-resource/mcp"
if [ "$CODE" = 403 ]; then
    skip "MCP app checks" "403: the WAF rule blocks your IP (expected when it is on; only Anthropic's ranges get through)"
    pass "MCP host is closed to non-Anthropic IPs (403)"
    check_code "WAF also covers /mcp" POST "$MCP/mcp" 403
else
    if [ "$CODE" = 200 ]; then
        pass "GET /.well-known/oauth-protected-resource/mcp (200)"
        if body_has '"resource"'; then pass "protected-resource metadata names the resource"; else fail "PRM body" 'no "resource" field'; fi
    else
        fail "GET /.well-known/oauth-protected-resource/mcp" "got $CODE, want 200"
    fi
    check_code "GET /.well-known/oauth-protected-resource" GET "$MCP/.well-known/oauth-protected-resource" 200
    if check_code "GET /.well-known/oauth-authorization-server" GET "$MCP/.well-known/oauth-authorization-server" 200; then
        if grep -q "\"authorization_endpoint\": *\"$CMS/oauth/authorize/\"" "$TMP/b"; then pass "authorize endpoint is on the CMS host"
        else fail "authorization_endpoint" "$(grep -o '"authorization_endpoint": *"[^"]*"' "$TMP/b")"; fi
        if grep -q "\"token_endpoint\": *\"$MCP/oauth/token/\"" "$TMP/b"; then pass "token endpoint is on the MCP host"
        else fail "token_endpoint" "$(grep -o '"token_endpoint": *"[^"]*"' "$TMP/b")"; fi
    fi
    if check_code "POST /mcp without a token" POST "$MCP/mcp" 401 -- \
        -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
        --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'; then
        check_header "401 points at the resource metadata" WWW-Authenticate "resource_metadata="
    fi
    check_code "POST /oauth/token/ reaches the OAuth server" POST "$MCP/oauth/token/" 400 401 -- \
        -H 'Content-Type: application/x-www-form-urlencoded' --data 'grant_type=authorization_code'
    for p in / /oauth/authorize/ /api/v1/ /admin/ /mcp/extra /.well-known/openid-configuration /cms/login; do
        check_code "MCP host: $p is 404" GET "$MCP$p" 404
    done
fi

# ------------------------------------------------------------------------------------------------ summary
printf '\n%d passed, %d failed, %d skipped\n' "$NPASS" "$NFAIL" "$NSKIP"
[ "$NFAIL" = 0 ]
