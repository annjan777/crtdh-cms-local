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
