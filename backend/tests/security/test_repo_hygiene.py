"""No default credentials or dev seeding in what ships."""
import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.security
ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"


def test_seed_fixture_has_no_users_or_credentials():
    data = json.loads((BACKEND / "apps/core/fixtures/local_seed.json").read_text())
    models = {o["model"] for o in data}
    assert not {m for m in models if m.startswith(("auth.", "accounts.", "sessions.", "admin.", "contact."))}
    assert "pbkdf2_sha256$" not in (BACKEND / "apps/core/fixtures/local_seed.json").read_text()


def test_production_compose_has_no_seeding_or_default_secrets():
    text = (ROOT / "deploy/docker-compose.yml").read_text()
    assert "bootstrap_local" not in text and "create_dev_users" not in text and "createsuperuser" not in text
    assert ":-" not in text, "no ${VAR:-default} fallbacks for secrets or flags in production compose"
    compose = yaml.safe_load(text)
    for name, svc in compose["services"].items():
        assert "ports" not in svc, f"{name} publishes a host port; everything goes through cloudflared"
        env = svc.get("environment", {})
        if isinstance(env, dict):
            assert str(env.get("DEBUG", "False")).lower() in ("false", "0"), name
            assert str(env.get("CORS_ALLOW_ALL_ORIGINS", "False")).lower() in ("false", "0"), name


def test_env_file_is_example_only_and_ignored():
    assert not (ROOT / "deploy/.env").exists() or ".env" in (ROOT / ".gitignore").read_text()
    assert "deploy/.env" in (ROOT / ".gitignore").read_text()
    example = (ROOT / "deploy/.env.example").read_text()
    for line in example.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            if any(w in key for w in ("PASSWORD", "SECRET", "KEY", "DATABASE_URL", "EMAIL_URL", "TOKEN")):
                assert value.startswith("<") and value.endswith(">"), f"{key} must be a <placeholder>"


def test_local_compose_has_no_fixed_admin_password():
    text = (ROOT / "docker-compose.local.yml").read_text()
    assert "adminpassword" not in text and "DJANGO_SUPERUSER_PASSWORD" not in text


def test_tunnel_routes_only_mcp_paths_to_mcp_host():
    import re

    import yaml

    conf = yaml.safe_load((ROOT / "deploy/cloudflared/config.yml.template").read_text())
    mcp_rules = [r for r in conf["ingress"] if r.get("hostname") == "mcp.<domain>"]
    routed = [r for r in mcp_rules if "path" in r]
    assert len(routed) == 1 and routed[0]["service"] == "http://mcp:8400"
    assert mcp_rules[-1]["service"] == "http_status:404"  # everything else on the MCP host
    rx = re.compile(routed[0]["path"])
    for ok in ["/mcp", "/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp",
               "/.well-known/oauth-authorization-server", "/oauth/token/", "/oauth/revoke_token/"]:
        assert rx.search(ok), ok
    for no in ["/oauth/authorize/", "/oauth/authorize/?x=1", "/api/v1/auth/login/", "/admin/", "/cms/login",
               "/mcpx", "/oauth/register/", "/oauth/applications/"]:
        assert not rx.search(no), no
    assert conf["ingress"][-1]["service"] == "http_status:404"


def _compose():
    return yaml.safe_load((ROOT / "deploy/docker-compose.yml").read_text())


def _nets(svc):
    n = svc.get("networks", [])
    return set(n) if isinstance(n, list) else set(n)


def test_only_gateway_and_cloudflared_are_trusted_proxies():
    c = _compose()
    gw = c["services"]["gateway"]["networks"]["internal"]["ipv4_address"]
    cf = c["services"]["cloudflared"]["networks"]["internal"]["ipv4_address"]
    subnet = c["networks"]["internal"]["ipam"]["config"][0]["subnet"]
    import ipaddress
    assert ipaddress.ip_address(gw) in ipaddress.ip_network(subnet) and c["networks"]["internal"]["internal"] is True
    for name in ("cms", "mcp", "worker", "housekeeping", "migrate"):
        env = c["services"][name]["environment"]
        assert env["TRUSTED_PROXY_IPS"].split(",") == [gw, cf], name
        assert env["REQUIRE_TRUSTED_PROXY"] == "True", name
    mcp_cmd = c["services"]["mcp"]["command"]
    assert "--no-proxy-headers" in mcp_cmd and '"*"' not in mcp_cmd and "--proxy-headers " not in mcp_cmd


def test_fixed_addresses_are_outside_the_dynamic_range():
    """A container started first (reboot order, `docker compose run`) must never be given .10/.11."""
    import ipaddress
    c = _compose()
    for net_name, net in c["networks"].items():
        fixed = [s["networks"][net_name]["ipv4_address"] for s in c["services"].values()
                 if isinstance(s.get("networks"), dict) and isinstance(s["networks"].get(net_name), dict)
                 and s["networks"][net_name].get("ipv4_address")]
        if not fixed:
            continue
        cfg = net["ipam"]["config"][0]
        assert "ip_range" in cfg, f"network {net_name} has fixed addresses but no ip_range"
        subnet, pool = ipaddress.ip_network(cfg["subnet"]), ipaddress.ip_network(cfg["ip_range"])
        assert pool.subnet_of(subnet)
        for ip in fixed:
            addr = ipaddress.ip_address(ip)
            assert addr in subnet and addr not in pool, (net_name, ip)


def test_internet_egress_is_minimal():
    c = _compose()
    on_egress = {n for n, s in c["services"].items() if "egress" in _nets(s)}
    assert on_egress == {"cms", "mcp", "worker", "cloudflared"}
    assert "egress" not in _nets(c["services"]["db"])


def test_gateway_container_is_hardened_and_serves_static():
    c = _compose()
    gw = c["services"]["gateway"]
    assert gw["read_only"] is True and gw["cap_drop"] == ["ALL"]
    assert set(gw["cap_add"]) <= {"CHOWN", "SETUID", "SETGID", "NET_BIND_SERVICE"}
    assert any(t.startswith("/etc/nginx/conf.d") for t in gw["tmpfs"])
    assert "static_data:/srv/static:ro" in gw["volumes"]
    assert "collectstatic" in c["services"]["migrate"]["command"]
    conf = (ROOT / "deploy/nginx/templates/gateway.conf.template").read_text()
    assert "location /static/" in conf and "alias /srv/static/;" in conf


# ---- gateway framing (QA wave 2 D3): the page editor frames its own /preview.html --------------------------------
def _gateway_cms_locations():
    import re

    conf = (ROOT / "deploy/nginx/templates/gateway.conf.template").read_text()
    cms = conf[conf.index("server_name ${CMS_HOST};"):conf.index("server_name ${CONTACT_HOST};")]
    variables = dict(re.findall(r'set \$(\w+) "([^"]*)";', cms))
    locations = {}
    for m in re.finditer(r"location ([^{]+?) \{(.*?)\n    \}", cms, re.S):
        headers = {}
        for name, value in re.findall(r'add_header ([\w-]+) (\$\w+|"[^"]*") always;', m.group(2)):
            headers[name] = variables[value[1:]] if value.startswith("$") else value.strip('"')
        locations[m.group(1).strip()] = headers
    return locations


def _csp(header):
    return {d.split()[0]: d.split()[1:] for d in (x.strip() for x in header.split(";")) if d}


def test_admin_spa_may_frame_its_preview_but_is_never_framed():
    spa = _gateway_cms_locations()["/"]
    csp = _csp(spa["Content-Security-Policy"])
    assert "'self'" in csp["frame-src"], "the editor canvas is <iframe src=/preview.html> on the same origin"
    assert csp["frame-ancestors"] == ["'none'"] and spa["X-Frame-Options"] == "DENY"


def test_preview_document_is_framed_same_origin_only():
    canvas = (ROOT / "admin/src/editor/Canvas.jsx").read_text()
    assert 'src="/preview.html"' in canvas  # what the location below is for
    preview = _gateway_cms_locations()["= /preview.html"]
    csp = _csp(preview["Content-Security-Policy"])
    assert csp["frame-ancestors"] == ["'self'"] and preview["X-Frame-Options"] == "SAMEORIGIN"
    # the public site's own embeds (Blocks.jsx: map, youtube-nocookie player) and nothing broader
    assert set(csp["frame-src"]) == {"https://www.youtube-nocookie.com", "https://www.google.com"}
    for directive in ("script-src", "object-src", "base-uri"):
        assert directive in csp
    assert "'unsafe-inline'" not in preview["Content-Security-Policy"]
    assert {"X-Content-Type-Options", "Strict-Transport-Security", "Referrer-Policy"} <= set(preview)


# ---- publish worker (GO-LIVE blocker 1): it must be able to build the site in production -------------------------
def test_worker_has_node_frontend_and_a_publish_volume():
    c = _compose()
    worker, cms = c["services"]["worker"], c["services"]["cms"]
    assert worker["build"] == {"context": "..", "dockerfile": "deploy/worker/Dockerfile"}
    dockerfile = (ROOT / "deploy/worker/Dockerfile").read_text()
    assert "FROM node:22" in dockerfile and "COPY --from=frontend /usr/local/bin/node" in dockerfile
    assert "npm ci" in dockerfile and "--omit=dev" not in dockerfile  # vite/@react-router/dev are devDependencies
    assert "COPY --from=frontend /srv/frontend /srv/frontend" in dockerfile
    assert "\nUSER app\n" in dockerfile and "useradd --system --no-create-home --uid 10001 app" in dockerfile
    assert worker["read_only"] is True and worker["cap_drop"] == ["ALL"]
    assert "publish_data:/data/publish" in worker["volumes"] and "publish_data" in c["volumes"]
    assert "publish_data:/data/publish:ro" in cms["volumes"]  # the cms serves the tarballs to the agent
    assert any(t.startswith("/tmp") for t in worker["tmpfs"])
    env = worker["environment"]
    assert env["PUBLISH_ROOT"] == "/data/publish"
    assert env["FRONTEND_BUILD_CMD"] == "/usr/local/bin/crtdh-build-site"
    assert env["FRONTEND_BUILD_OUTPUT"].startswith("/tmp/") and env["FRONTEND_BUILD_OUTPUT"].endswith("/client")
    assert env["DEBUG"] == "False" and env["REQUIRE_TRUSTED_PROXY"] == "True"  # shared backend env kept
    script = (ROOT / "deploy/worker/build-site.sh").read_text()
    assert "BUILD_OUTPUT_DIR" in script and "SNAPSHOT_PATH" in script and "npm --prefix" in script
    ignore = (ROOT / "deploy/worker/Dockerfile.dockerignore").read_text().splitlines()
    assert "*" in ignore and "!backend" in ignore and "!frontend" in ignore
    assert {"backend/.env", "frontend/node_modules", "backend/media"} <= set(ignore)
    # the backend image creates /data/publish too, so the named volume is owned by app whichever container mounts it first
    assert "/data/publish" in (ROOT / "backend/Dockerfile").read_text()


# ---- Anthropic outbound ranges for the mcp. WAF rule (platform.claude.com/docs/en/api/ip-addresses, 19 Nov 2026) ---
ANTHROPIC_OUTBOUND = ("160.79.104.0/21", "153.61.208.0/20")
WAF_EXPRESSION = "not ip.src in {160.79.104.0/21 153.61.208.0/20}"


def test_every_place_that_names_the_anthropic_ranges_names_both():
    import re

    # the phased-out single addresses must not come back
    phased_out = ("34.162.46.92", "34.162.102.82", "34.162.136.91", "34.162.142.92", "34.162.183.95")
    for rel in ("deploy/cloudflared/config.yml.template", "docs/mcp.md", "docs/GO-LIVE.md", "deploy/README.md"):
        text = (ROOT / rel).read_text()
        for cidr in ANTHROPIC_OUTBOUND:
            assert cidr in text, f"{rel} does not name {cidr}"
        assert not any(ip in text for ip in phased_out), rel
        for expr in re.findall(r"not ip\.src in \{[^}]*\}", text):
            assert expr == WAF_EXPRESSION, f"{rel}: {expr}"
    assert WAF_EXPRESSION in (ROOT / "deploy/cloudflared/config.yml.template").read_text()
    assert WAF_EXPRESSION in (ROOT / "docs/GO-LIVE.md").read_text()


def test_housekeeping_runs_every_daily_cleanup():
    import re

    cmd = " ".join(_compose()["services"]["housekeeping"]["command"].split())
    jobs = re.findall(r"python manage\.py (\w+)", cmd)
    assert jobs == ["purge_contact_messages", "clearsessions", "clear_auth_throttles", "cleartokens"]
    assert "sleep 86400" in cmd and " && " in cmd
    from django.core.management import get_commands

    assert set(jobs) <= set(get_commands())  # each one exists in this codebase
