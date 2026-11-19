"""E2E fixtures (Playwright, Python). Run from the repo root:

    /home/claude/venv/bin/python -m pytest tests/e2e                    # harness checks only
    /home/claude/venv/bin/python -m pytest tests/e2e --integration      # everything (wave 2)

Options / env:
  --backend-port 8600 --admin-port 3600 --site-port 3601   (QA lane ports)
  --site-dir   built public site   (default frontend/build/client; env E2E_SITE_DIR)
  --admin-dir  built admin          (default admin/dist; env E2E_ADMIN_DIR)
  --external   don't start anything; use already-running servers on those ports (preprod.sh, staging)
               with E2E_CA_FILE=.preprod/tls/cert.pem E2E_USERS_FILE=.preprod/users.json CRTDH_TEST_PASSWORD=...
               E2E_SITE_URL / E2E_ADMIN_URL / E2E_MCP_URL, and E2E_PUBLISH_STACK=1 for the publish flow
  E2E_DJANGO_SETTINGS  production settings module (default config.settings + CRTDH_ENV=production)
  CHROME_BIN           used when Playwright's bundled Chromium is not installed (sandbox)
"""
import os
from pathlib import Path

import pytest

from stack import REPO, Stack

ROUTES = ["/", "/about", "/team", "/innovations", "/facilities", "/services", "/product", "/enterprises",
          "/social-impact", "/covid-19", "/media", "/contact"]
VIEWPORTS = {"phone": (375, 812), "tablet": (768, 1024), "desktop": (1280, 900)}


def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true", default=False)
    parser.addoption("--backend-port", type=int, default=8600)
    parser.addoption("--admin-port", type=int, default=3600)
    parser.addoption("--site-port", type=int, default=3601)
    parser.addoption("--site-dir", default=os.environ.get("E2E_SITE_DIR", str(REPO / "frontend/build/client")))
    parser.addoption("--admin-dir", default=os.environ.get("E2E_ADMIN_DIR", str(REPO / "admin/dist")))
    parser.addoption("--external", action="store_true", default=False)


def pytest_collection_modifyitems(config, items):
    # The golden regression compares against the seed content, so it runs before the specs that change content
    # on purpose (the editor spec empties Media coverage; the publish specs publish that). Stable sort: harness first.
    items.sort(key=lambda i: {"test_00_harness.py": 0, "test_golden_regression.py": 1}.get(i.path.name, 2))
    if config.getoption("--integration") or os.environ.get("RUN_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="needs_integration: run with --integration once lanes are merged")
    for item in items:
        if "needs_integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Fall back to system Chrome when Playwright's own browser isn't downloadable (sandbox CDN blocked)."""
    from playwright.sync_api import sync_playwright
    args = dict(browser_type_launch_args)
    with sync_playwright() as p:
        bundled = Path(p.chromium.executable_path)
    chrome = os.environ.get("CHROME_BIN")
    if not bundled.exists() and chrome and Path(chrome).exists():
        args["executable_path"] = chrome
    # The browser may only talk to the local stack: OAuth redirects to claude.ai (auth codes!), fonts, analytics
    # and anything else external go to a dead proxy. Playwright's route() does not see redirect hops.
    args["args"] = [*args.get("args", []), "--proxy-server=http://127.0.0.1:9",
                    "--proxy-bypass-list=localhost;127.0.0.1;[::1]"]
    return args


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """The stack serves HTTPS with a throwaway self-signed cert (stack.py)."""
    return {**browser_context_args, "ignore_https_errors": True}


@pytest.fixture(scope="session")
def stack(request, tmp_path_factory):
    o = request.config.getoption
    s = Stack(backend_port=o("--backend-port"), admin_port=o("--admin-port"), site_port=o("--site-port"),
              workdir=tmp_path_factory.mktemp("stack"), site_dir=Path(o("--site-dir")), admin_dir=Path(o("--admin-dir")))
    if o("--external"):  # e.g. preprod.sh: trust its cert via E2E_CA_FILE=.preprod/tls/cert.pem
        s.password = os.environ.get("CRTDH_TEST_PASSWORD", "")
        if os.environ.get("E2E_USERS_FILE"):  # .preprod/users.json from seed_test_users --rehearsal
            import json
            s.users = json.loads(Path(os.environ["E2E_USERS_FILE"]).read_text())
        if os.environ.get("E2E_CA_FILE"):
            import ssl
            import urllib.request
            ctx = ssl.create_default_context(cafile=os.environ["E2E_CA_FILE"])
            urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)))
        yield s
        return
    s.start_backend()
    s.start_static()
    yield s
    s.stop()


@pytest.fixture(scope="session")
def site(stack):
    if not (stack.site_dir / "index.html").is_file() and not os.environ.get("E2E_SITE_URL"):
        pytest.skip(f"public site not built at {stack.site_dir} (build it, or run against preprod: scripts/preprod.sh e2e)")
    return os.environ.get("E2E_SITE_URL", stack.site)


@pytest.fixture(scope="session")
def cms(stack):
    if not (stack.admin_dir / "index.html").is_file() and not os.environ.get("E2E_ADMIN_URL"):
        pytest.skip(f"admin not built at {stack.admin_dir} (build it, or run against preprod: scripts/preprod.sh e2e)")
    return os.environ.get("E2E_ADMIN_URL", stack.admin)


@pytest.fixture
def login(page, cms, stack):
    """login("priya") signs in through the real UI (password + TOTP when enrolled). Returns the page."""
    from helpers import ui_login

    def _login(username, p=None):
        return ui_login(p or page, cms, username, stack.password, stack.users.get(username, {}).get("totp_secret"))

    return _login


@pytest.fixture
def second_page(context):
    return context.browser.new_context(ignore_https_errors=True).new_page()
