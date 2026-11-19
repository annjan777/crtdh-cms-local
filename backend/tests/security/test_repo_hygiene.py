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
