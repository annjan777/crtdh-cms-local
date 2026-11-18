"""E2E fixtures (Playwright, Python). Run from the repo root:

    /home/claude/venv/bin/python -m pytest tests/e2e                    # harness checks only
    /home/claude/venv/bin/python -m pytest tests/e2e --integration      # everything (wave 2)

Options / env:
  --backend-port 8600 --admin-port 3600 --site-port 3601   (QA lane ports)
  --site-dir   built public site   (default frontend/build/client; env E2E_SITE_DIR)
  --admin-dir  built admin          (default admin/dist; env E2E_ADMIN_DIR)
  --external   don't start anything; use already-running servers on those ports (preprod.sh, staging)
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
    return args


@pytest.fixture(scope="session")
def stack(request, tmp_path_factory):
    o = request.config.getoption
    s = Stack(backend_port=o("--backend-port"), admin_port=o("--admin-port"), site_port=o("--site-port"),
              workdir=tmp_path_factory.mktemp("stack"), site_dir=Path(o("--site-dir")), admin_dir=Path(o("--admin-dir")))
    if o("--external"):
        s.password = os.environ.get("CRTDH_TEST_PASSWORD", "")
        yield s
        return
    s.start_backend()
    s.start_static()
    yield s
    s.stop()


@pytest.fixture(scope="session")
def site(stack):
    if not (stack.site_dir / "index.html").is_file() and not os.environ.get("E2E_SITE_URL"):
        pytest.skip(f"public site not built at {stack.site_dir} (run scripts/e2e-build.sh)")
    return os.environ.get("E2E_SITE_URL", stack.site)


@pytest.fixture(scope="session")
def cms(stack):
    if not (stack.admin_dir / "index.html").is_file() and not os.environ.get("E2E_ADMIN_URL"):
        pytest.skip(f"admin not built at {stack.admin_dir} (run scripts/e2e-build.sh)")
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
    return context.browser.new_context().new_page()
