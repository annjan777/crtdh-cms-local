"""Command line: python -m publish_agent <command> [-c config.ini]

  check [--trust-host-key]   connect, run server discovery, print what was found and the recommended strategy
  backup                     download the current live site into state/backups/ (also done before the first publish)
  run [--once]               poll the CMS and publish new builds (loop with backoff, or a single pass)
  rollback [--to ID]         make the previous (or a named) release live again
  status                     show what is live, kept releases and the last result
  set-password               store the SFTP password in the system keyring (only if you cannot use an SSH key)
Global: --dry-run (change nothing on the server, report nothing), --verbose
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import random
import sys
import time

from . import __version__
from .cmsclient import CMSClient, CMSError
from .config import Config, ConfigError, load
from .deploy import PublishFailed, Publisher
from .logutil import LOG, setup_logging
from .remote import Remote, RemoteError, store_keyring_password

DEFAULT_CONFIG = "config.ini"


class SingleInstance:
    """Stops two copies (e.g. two scheduled-task starts) publishing at the same time."""

    def __init__(self, path: str):
        self.path = path
        self.fh = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.fh = open(self.path, "a+")
        try:
            if os.name == "nt":
                import msvcrt
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.fh.close()
            raise SystemExit("another copy of the publish agent is already running; exiting")
        return self

    def __exit__(self, *exc):
        if self.fh:
            self.fh.close()


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m publish_agent", description="CRTDH publish agent")
    p.add_argument("-c", "--config", default=os.environ.get("CRTDH_AGENT_CONFIG", DEFAULT_CONFIG))
    p.add_argument("--dry-run", action="store_true", help="change nothing on the server and report nothing")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="connect and run server discovery")
    c.add_argument("--trust-host-key", action="store_true",
                   help="first time only: trust and save the server's host key (compare the printed fingerprint)")
    c.add_argument("--no-http", action="store_true", help="skip the HTTP probes")
    c.add_argument("--password", action="store_true", help="prompt for the SFTP password instead of using the key")
    sub.add_parser("backup", help="download the current live site to a local .tar.gz")
    r = sub.add_parser("run", help="poll the CMS and publish")
    r.add_argument("--once", action="store_true", help="one pass, then exit (for schedulers)")
    rb = sub.add_parser("rollback", help="make the previous release live again")
    rb.add_argument("--to", help="release id to make live (see `status`)")
    sub.add_parser("status", help="show what is live")
    sub.add_parser("set-password", help="store the SFTP password in the system keyring")
    return p


def _connector(cfg: Config, interactive: bool = False, trust: bool = False):
    return lambda: Remote.connect(cfg, trust_new_host_key=trust, interactive=interactive)


def cmd_check(cfg: Config, args) -> int:
    from .discover import discover, format_report
    if args.password:
        cfg.key_file = ""
        cfg.password_source = "prompt"
    remote = Remote.connect(cfg, trust_new_host_key=args.trust_host_key, interactive=True)
    try:
        LOG.info("connected to %s@%s:%s", cfg.sftp_user, cfg.sftp_host, cfg.sftp_port)
        pub = Publisher(cfg, connect=lambda: remote)
        report = discover(cfg, remote, http_get=pub.http_get, probe_http=not args.no_http)
        pub.save_local_state(discovery=report)
        print(format_report(report))
        if report.get("discover_sh"):
            LOG.debug("discover.sh output:\n%s", report["discover_sh"])
        if cfg.cms_url:
            try:
                CMSClient(cfg.cms_url, cfg.secret(), cfg.http_timeout).next_job()
                print("CMS connection         : ok (agent secret accepted)")
            except (CMSError, ConfigError, Exception) as exc:  # noqa: BLE001
                print(f"CMS connection         : FAILED - {exc}")
        return 0 if report.get("recommended") else 1
    finally:
        remote.close()


def cmd_backup(cfg: Config, args) -> int:
    from .discover import backup_live_site
    remote = Remote.connect(cfg, interactive=True)
    try:
        path = backup_live_site(cfg, remote, remote.abspath(cfg.web_root))
        print(f"backup saved: {path}")
        Publisher(cfg, connect=lambda: remote).save_local_state(backup=path)
        return 0
    finally:
        remote.close()


def cmd_run(cfg: Config, args) -> int:
    cms = CMSClient(cfg.cms_url, cfg.secret(), cfg.http_timeout)
    pub = Publisher(cfg, cms=cms, connect=_connector(cfg), dry_run=args.dry_run)
    if args.once:
        try:
            result = pub.run_once()
        except CMSError as exc:
            LOG.error("%s", exc)
            return 2
        return 1 if result == "failed" else 0
    LOG.info("publish agent %s polling %s every %ss", __version__, cfg.cms_url, cfg.poll_seconds)
    pub.idle_cleanup()
    delay = cfg.poll_seconds
    while True:
        try:
            result = pub.run_once()
            delay = cfg.poll_seconds
            if result == "live":
                delay = 1  # check straight away for another queued publish
        except (CMSError, RemoteError) as exc:
            delay = min(cfg.max_backoff_seconds, max(cfg.poll_seconds, delay * 2))
            LOG.warning("%s; retrying in %ss", exc, delay)
        except KeyboardInterrupt:
            LOG.info("stopped")
            return 0
        except Exception:  # noqa: BLE001 - keep the loop alive, but log the bug
            delay = min(cfg.max_backoff_seconds, max(cfg.poll_seconds, delay * 2))
            LOG.exception("unexpected error; retrying in %ss", delay)
        try:
            time.sleep(delay + random.uniform(0, min(5, delay / 5)))
        except KeyboardInterrupt:
            LOG.info("stopped")
            return 0


def cmd_rollback(cfg: Config, args) -> int:
    pub = Publisher(cfg, connect=_connector(cfg, interactive=True), dry_run=args.dry_run)
    target = pub.rollback(args.to)
    print(f"live release is now: {target}")
    return 0


def cmd_status(cfg: Config, args) -> int:
    pub = Publisher(cfg, connect=_connector(cfg, interactive=True))
    info = pub.status()
    local = info.pop("local", {})
    local.pop("discovery", None)
    print(json.dumps({"server": info, "this_pc": local}, indent=2, sort_keys=True))
    return 0


def cmd_set_password(cfg: Config, args) -> int:
    pw = getpass.getpass(f"SFTP password for {cfg.sftp_user}@{cfg.sftp_host} (not shown): ")
    if not pw:
        print("nothing stored")
        return 1
    store_keyring_password(cfg, pw)
    print("stored in the system keyring")
    return 0


COMMANDS = {"check": cmd_check, "backup": cmd_backup, "run": cmd_run, "rollback": cmd_rollback,
            "status": cmd_status, "set-password": cmd_set_password}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        cfg = load(args.config)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    setup_logging(cfg.log_file, args.verbose)
    try:
        if args.cmd in ("run", "rollback", "backup"):
            with SingleInstance(os.path.join(cfg.state_dir, "agent.lock")):
                return COMMANDS[args.cmd](cfg, args)
        return COMMANDS[args.cmd](cfg, args)
    except (ConfigError, RemoteError, PublishFailed) as exc:
        LOG.error("%s", getattr(exc, "message", None) or exc)
        return 2
