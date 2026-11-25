"""deploy/.env.example documents every environment variable the code reads (placeholders only)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PY_READ = re.compile(r'(?:(?<![\w.])_?env(?:\.\w+)?|os\.environ(?:\.get)?|os\.getenv|monkeypatch\.\w+env)\(\s*"([A-Z][A-Z0-9_]+)"'
                     r'|os\.environ\[\s*"([A-Z][A-Z0-9_]+)"')
JS_READ = re.compile(r"(?:process\.env|import\.meta\.env)\.([A-Z][A-Z0-9_]+)")


def _reads():
    names = set()
    for base in ("backend/config", "backend/apps", "publish_agent"):
        for path in (ROOT / base).rglob("*.py"):
            if "tests" in path.parts or "migrations" in path.parts:
                continue
            for m in PY_READ.finditer(path.read_text(encoding="utf-8")):
                names.add(m.group(1) or m.group(2))
    for base in ("frontend/scripts", "frontend/src", "admin/src"):
        for path in (ROOT / base).rglob("*"):
            if path.suffix in (".js", ".mjs", ".jsx", ".ts") and "__tests__" not in path.parts:
                names |= set(JS_READ.findall(path.read_text(encoding="utf-8")))
    for name in ("vite.config.js",):
        names |= set(JS_READ.findall((ROOT / "admin" / name).read_text(encoding="utf-8")))
    return names


def test_every_env_read_is_documented():
    example = (ROOT / "deploy/.env.example").read_text()
    documented = set(re.findall(r"\b([A-Z][A-Z0-9_]{2,})\b", example))
    missing = sorted(_reads() - documented)
    assert not missing, f"add to deploy/.env.example: {missing}"


def test_found_the_known_reads():
    """Guard the scanner itself: these are read by the code today."""
    assert {"SECRET_KEY", "AGENT_HMAC_SECRET", "PUBLISH_ROOT", "CMS_PUBLIC_URL", "TRUSTED_PROXY_IPS",
            "CONTACT_API_URL", "TURNSTILE_SITE_KEY"} <= _reads()
