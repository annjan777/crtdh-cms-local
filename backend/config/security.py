"""Fail-closed checks for production settings (WS0.2).

`production_problems()` is a pure function so the settings matrix can be unit
tested; `config/settings.py` calls it and refuses to start if it returns
anything. "Production" means DEBUG is false, or CRTDH_ENV=production.
"""

KNOWN_DEFAULT_SECRETS = {
    "django-insecure-dev-key-change-me-in-production",
    "change-me-to-a-long-random-string",
    "local-secret-key-123",
    "local-insecure-secret-key",
}
MIN_SECRET_LENGTH = 50


def secret_key_problem(key):
    if not key:
        return "SECRET_KEY is not set"
    if key in KNOWN_DEFAULT_SECRETS or key.startswith("django-insecure") or "change-me" in key:
        return "SECRET_KEY is a known default value"
    if len(key) < MIN_SECRET_LENGTH or len(set(key)) < 5:
        return f"SECRET_KEY is too short or too simple (need >= {MIN_SECRET_LENGTH} random characters)"
    return None


def production_problems(*, debug, env_name, secret_key, allowed_hosts, cors_allow_all,
                        cors_origins, csrf_trusted_origins, database_engine, allow_sqlite,
                        django_admin_enabled, trust_cf_connecting_ip=False, trusted_proxy_ips=(),
                        require_trusted_proxy=False):
    problems = []
    if debug and env_name == "production":
        problems.append("DEBUG is true while CRTDH_ENV=production")
    if debug and env_name != "production":
        return problems  # local development

    msg = secret_key_problem(secret_key)
    if msg:
        problems.append(msg)
    if not allowed_hosts:
        problems.append("ALLOWED_HOSTS is empty")
    if any(h.strip() in ("*", ".*") or h.strip().startswith("*") for h in allowed_hosts):
        problems.append("ALLOWED_HOSTS contains a wildcard")
    if cors_allow_all:
        problems.append("CORS_ALLOW_ALL_ORIGINS is true")
    for origin in list(cors_origins) + list(csrf_trusted_origins):
        if origin.strip() == "*" or "*" in origin:
            problems.append(f"wildcard origin {origin!r} in CORS/CSRF origins")
        elif not origin.startswith("https://"):
            problems.append(f"origin {origin!r} is not https")
    if "sqlite" in database_engine and not allow_sqlite:
        problems.append("DATABASE_URL is sqlite (set ALLOW_SQLITE=1 only for tests)")
    import ipaddress

    for spec in trusted_proxy_ips:
        try:
            net = ipaddress.ip_network(spec.strip(), strict=False)
        except ValueError:
            problems.append(f"TRUSTED_PROXY_IPS entry {spec!r} is not an IP or CIDR")
            continue
        if net.prefixlen < (24 if net.version == 4 else 64):
            problems.append(f"TRUSTED_PROXY_IPS entry {spec!r} is wider than one compose network")
    if (trust_cf_connecting_ip or require_trusted_proxy) and not trusted_proxy_ips:
        problems.append("TRUST_CF_CONNECTING_IP/REQUIRE_TRUSTED_PROXY need TRUSTED_PROXY_IPS (gateway + cloudflared)")
    if django_admin_enabled:
        problems.append("DJANGO_ADMIN_ENABLED is set; the Django admin bypasses MFA and must stay off in production")
    return problems
