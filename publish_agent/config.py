"""Config file (INI, stdlib only). See config.example.ini for every option."""
from __future__ import annotations

import configparser
import os
import urllib.parse
from dataclasses import dataclass, field

STRATEGIES = ("symlink", "htaccess", "swap", "copy")


class ConfigError(Exception):
    pass


@dataclass
class Config:
    cms_url: str
    secret_env: str = "CRTDH_AGENT_SECRET"
    secret_file: str = ""
    poll_seconds: int = 30
    max_backoff_seconds: int = 600
    http_timeout: int = 60
    max_download_errors: int = 5  # consecutive failed downloads of one build before reporting it failed
    # Cloudflare Access service token (cms.<domain> is behind Access). The id is not secret; the secret is read
    # like the agent secret: from access_secret_file, else the access_secret_env variable. Empty id = not sent.
    access_client_id: str = ""
    access_secret_env: str = "CRTDH_CF_ACCESS_SECRET"
    access_secret_file: str = ""

    transport: str = "sftp"  # sftp | local (the agent runs on the web server itself, e.g. academicweb)
    sftp_host: str = ""
    sftp_port: int = 22
    sftp_user: str = ""
    key_file: str = ""
    password_source: str = "keyring"  # keyring | prompt (only used without key_file)
    known_hosts: str = ""

    web_root: str = "~/public_html"
    base_dir: str = ""  # empty: chosen per strategy
    strategy: str = "auto"
    keep_releases: int = 3
    verify_url: str = ""
    verify_marker: str = "crtdh-build"
    verify_attempts: int = 5
    verify_delay: float = 3.0

    state_dir: str = "state"
    log_file: str = ""
    config_path: str = ""
    extra: dict = field(default_factory=dict)

    # ---- derived -----------------------------------------------------------
    @property
    def work_dir(self) -> str:
        return os.path.join(self.state_dir, "work")

    @property
    def backup_dir(self) -> str:
        return os.path.join(self.state_dir, "backups")

    @property
    def local_state_file(self) -> str:
        return os.path.join(self.state_dir, "agent-state.json")

    def secret(self) -> str:
        """The shared HMAC secret. Read on demand, never stored in the config file itself."""
        value = ""
        if self.secret_file:
            try:
                with open(self.secret_file, encoding="utf-8") as fh:
                    value = fh.read().strip()
            except OSError as exc:
                raise ConfigError(f"cannot read secret_file {self.secret_file}: {exc.strerror}") from None
        if not value and self.secret_env:
            value = os.environ.get(self.secret_env, "").strip()
        if not value:
            raise ConfigError(
                f"agent secret missing: set environment variable {self.secret_env} "
                "or put it in the file named by secret_file")
        return value


    def access_headers(self) -> dict:
        """CF-Access-Client-Id / CF-Access-Client-Secret for every CMS request, or {} when no token is set up."""
        if not self.access_client_id:
            return {}
        value = ""
        if self.access_secret_file:
            try:
                with open(self.access_secret_file, encoding="utf-8") as fh:
                    value = fh.read().strip()
            except OSError as exc:
                raise ConfigError(f"cannot read access_secret_file {self.access_secret_file}: {exc.strerror}") from None
        if not value and self.access_secret_env:
            value = os.environ.get(self.access_secret_env, "").strip()
        if not value:
            raise ConfigError(
                f"access_client_id is set but the Cloudflare Access client secret is missing: set environment "
                f"variable {self.access_secret_env} or put it in the file named by access_secret_file")
        return {"CF-Access-Client-Id": self.access_client_id, "CF-Access-Client-Secret": value}


def _resolve(base: str, path: str) -> str:
    if not path:
        return path
    path = os.path.expanduser(path)
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(base, path))


def load(path: str) -> Config:
    if not os.path.exists(path):
        raise ConfigError(f"config file not found: {path} (copy config.example.ini to start)")
    cp = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(";", "#"))
    cp.read(path, encoding="utf-8")
    base = os.path.dirname(os.path.abspath(path))

    def get(section, key, default=""):
        return cp.get(section, key, fallback=default).strip()

    def getint(section, key, default):
        try:
            return cp.getint(section, key, fallback=default)
        except ValueError:
            raise ConfigError(f"[{section}] {key} must be a whole number") from None

    for key in ("password", "pass", "secret", "access_client_secret", "access_secret", "client_secret"):
        for section in cp.sections():
            if cp.has_option(section, key) and cp.get(section, key).strip():
                raise ConfigError(
                    f"[{section}] {key}= found in the config file. Do not store passwords or secrets in it; "
                    "use an SSH key, the system keyring, or the secret env var / secret_file.")

    cfg = Config(
        cms_url=get("cms", "url").rstrip("/"),
        secret_env=get("cms", "secret_env", "CRTDH_AGENT_SECRET"),
        secret_file=_resolve(base, get("cms", "secret_file")),
        poll_seconds=getint("cms", "poll_seconds", 30),
        max_backoff_seconds=getint("cms", "max_backoff_seconds", 600),
        http_timeout=getint("cms", "http_timeout", 60),
        max_download_errors=getint("cms", "max_download_errors", 5),
        access_client_id=get("cms", "access_client_id"),
        access_secret_env=get("cms", "access_secret_env", "CRTDH_CF_ACCESS_SECRET"),
        access_secret_file=_resolve(base, get("cms", "access_secret_file")),
        transport=get("sftp", "transport", "sftp") or "sftp",
        sftp_host=get("sftp", "host"),
        sftp_port=getint("sftp", "port", 22),
        sftp_user=get("sftp", "user"),
        key_file=_resolve(base, get("sftp", "key_file")),
        password_source=get("sftp", "password_source", "keyring") or "keyring",
        web_root=get("site", "web_root", "~/public_html"),
        base_dir=get("site", "base_dir"),
        strategy=get("site", "strategy", "auto") or "auto",
        keep_releases=getint("site", "keep_releases", 3),
        verify_url=get("site", "verify_url"),
        verify_marker=get("site", "verify_marker", "crtdh-build") or "crtdh-build",
        verify_attempts=getint("site", "verify_attempts", 5),
        state_dir=_resolve(base, get("agent", "state_dir", "state") or "state"),
        config_path=os.path.abspath(path),
    )
    cfg.known_hosts = _resolve(base, get("sftp", "known_hosts")) or os.path.join(cfg.state_dir, "known_hosts")
    cfg.log_file = _resolve(base, get("agent", "log_file")) or os.path.join(cfg.state_dir, "logs", "agent.log")
    try:
        cfg.verify_delay = float(get("site", "verify_delay", "3") or 3)
    except ValueError:
        raise ConfigError("[site] verify_delay must be a number") from None
    validate(cfg)
    return cfg


def validate(cfg: Config) -> None:
    parts = urllib.parse.urlsplit(cfg.cms_url)
    local = parts.hostname in ("localhost", "127.0.0.1", "::1")
    if not (parts.scheme == "https" or (parts.scheme == "http" and local)) or not parts.hostname:
        raise ConfigError("[cms] url must start with https:// (plain http is only allowed for localhost testing)")
    if cfg.verify_url:
        vparts = urllib.parse.urlsplit(cfg.verify_url)
        if vparts.scheme not in ("http", "https") or not vparts.hostname:
            raise ConfigError("[site] verify_url must be an http:// or https:// address of the public site")
    if cfg.transport not in ("sftp", "local"):
        raise ConfigError("[sftp] transport must be sftp or local")
    if cfg.transport == "sftp" and (not cfg.sftp_host or not cfg.sftp_user):
        raise ConfigError("[sftp] host and user are required")
    if cfg.strategy not in ("auto",) + STRATEGIES:
        raise ConfigError(f"[site] strategy must be auto or one of {', '.join(STRATEGIES)}")
    if cfg.keep_releases < 1:
        raise ConfigError("[site] keep_releases must be at least 1")
    if cfg.password_source not in ("keyring", "prompt"):
        raise ConfigError("[sftp] password_source must be keyring or prompt")
    if cfg.key_file and not os.path.exists(cfg.key_file):
        raise ConfigError(f"[sftp] key_file not found: {cfg.key_file}")
