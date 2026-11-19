"""Start/stop the local stack for E2E: backend (prod-like settings), admin (CMS origin), public site.

All on the QA lane ports by default (contract §6): backend 8600, admin 3600, public site 3601.
Everything is served over HTTPS on localhost with a throwaway self-signed cert (tests/tools/devcert.py),
because production settings refuse http origins. urllib trusts it via a global opener + E2E_CA_FILE;
Playwright contexts use ignore_https_errors (conftest.browser_context_args).
"""
import json
import os
import secrets
import ssl
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
PY = os.environ.get("E2E_PYTHON", "/home/claude/venv/bin/python" if Path("/home/claude/venv/bin/python").exists() else sys.executable)
sys.path.insert(0, str(REPO / "tests"))
from tools.devcert import make as make_cert  # noqa: E402
from tools.static_server import serve  # noqa: E402


def wait_http(url, timeout=60, ok=(200, 204, 301, 302, 400, 401, 403, 404, 405)):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status in ok:
                    return
        except urllib.error.HTTPError as e:
            if e.code in ok:
                return
            last = e
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(0.5)
    raise RuntimeError(f"{url} not up after {timeout}s: {last}")


@dataclass
class Stack:
    backend_port: int = 8600
    admin_port: int = 3600
    site_port: int = 3601
    workdir: Path = None
    settings_module: str = os.environ.get("E2E_DJANGO_SETTINGS", "config.settings")
    site_dir: Path = None
    admin_dir: Path = None
    password: str = field(default_factory=lambda: secrets.token_urlsafe(18), repr=False)
    users: dict = field(default_factory=dict, repr=False)  # holds TOTP secrets: never in tracebacks
    _procs: list = field(default_factory=list)
    _servers: list = field(default_factory=list)

    @property
    def api(self):
        return f"https://localhost:{self.backend_port}"

    @property
    def admin(self):
        return f"https://localhost:{self.admin_port}"

    @property
    def site(self):
        return f"https://localhost:{self.site_port}"

    def env(self):
        e = dict(os.environ)
        origins = f"{self.admin},{self.site}"
        e.update({
            "DJANGO_SETTINGS_MODULE": self.settings_module,
            "CRTDH_ENV": os.environ.get("E2E_CRTDH_ENV", "production"),
            "DEBUG": "False",
            "SECRET_KEY": "e2e-" + secrets.token_urlsafe(48),
            "ALLOWED_HOSTS": "localhost,127.0.0.1",
            "CORS_ALLOW_ALL_ORIGINS": "False",
            "CORS_ALLOWED_ORIGINS": origins,
            "CSRF_TRUSTED_ORIGINS": origins,
            "DATABASE_URL": os.environ.get("E2E_DATABASE_URL", f"sqlite:///{self.workdir / 'e2e.sqlite3'}"),
            "ALLOW_SQLITE": "1",
            "MEDIA_ROOT": str(self.workdir / "media"),
            "EMAIL_BACKEND": "django.core.mail.backends.filebased.EmailBackend",
            "EMAIL_FILE_PATH": str(self.workdir / "mail"),
            "PUBLISH_WORK_DIR": str(self.workdir / "publish"),
            "PUBLIC_SITE_URL": self.site,
            "CMS_PUBLIC_URL": self.admin,
            "TURNSTILE_SECRET": "1x0000000000000000000000000000000AA",  # Cloudflare's always-pass test key
            "CRTDH_SKIP_DOTENV": "1",
            "CRTDH_ALLOW_TEST_SEED": "1",
            "MFA_ENABLED": os.environ.get("E2E_MFA_ENABLED", "True"),  # the E2E flows cover two-step sign-in
            "CRTDH_TEST_PASSWORD": self.password,
            "PYTHONPATH": str(BACKEND),
        })
        return e

    def trust_cert(self):
        """Self-signed cert for this run; make every urllib call in the test process trust it."""
        self.cert, self.key = make_cert(self.workdir / "tls")
        os.environ["E2E_CA_FILE"] = str(self.cert)
        ctx = ssl.create_default_context(cafile=str(self.cert))
        urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)))

    def manage(self, *args, check=True):
        r = subprocess.run([PY, "manage.py", *args], cwd=BACKEND, env=self.env(), capture_output=True, text=True)
        if check and r.returncode:
            raise RuntimeError(f"manage.py {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
        return r

    def start_backend(self):
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.trust_cert()
        self.manage("migrate", "--noinput", "-v0")
        seed = os.environ.get("E2E_SEED", "sample")  # sample | full | none | /path/to/snapshot.json
        if seed != "none":
            path = {"sample": "SAMPLE_SNAPSHOT_PATH", "full": "FULL_SNAPSHOT_PATH"}.get(seed, repr(seed))
            self.manage("shell", "-c", "from tests.support.content import *; load_snapshot_into_db(%s)" % path)
        out = self.manage("seed_test_users", "--rehearsal").stdout.strip().splitlines()[-1]
        self.users = json.loads(out)
        log = open(self.workdir / "backend.log", "w")
        p = subprocess.Popen(
            [PY, "-m", "gunicorn", "config.wsgi:application", "-b", f"127.0.0.1:{self.backend_port}",
             "-w", "2", "--threads", "4", "--timeout", "60",
             "--certfile", str(self.cert), "--keyfile", str(self.key)],
            cwd=BACKEND, env=self.env(), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        self._procs.append(p)
        wait_http(f"{self.api}/api/v1/auth/me/")

    def start_static(self):
        for directory, port, mode, proxy in [
            (self.site_dir, self.site_port, "static", None),
            (self.admin_dir, self.admin_port, "spa", self.api),
        ]:
            if directory and Path(directory).is_dir():
                srv = serve(directory, port, mode, proxy, cert=str(self.cert), key=str(self.key))
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                self._servers.append(srv)

    def stop(self):
        for s in self._servers:
            s.shutdown()
        for p in self._procs:
            try:
                os.killpg(p.pid, signal.SIGTERM)
                p.wait(10)
            except Exception:  # noqa: BLE001
                pass

    def mail(self):
        """Emails written by the filebased backend, newest last, as raw text."""
        d = Path(os.environ["E2E_MAIL_DIR"]) if os.environ.get("E2E_MAIL_DIR") else self.workdir / "mail"
        return [f.read_text(errors="replace") for f in sorted(d.glob("*.log"), key=lambda f: f.stat().st_mtime)] if d.exists() else []
