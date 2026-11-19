"""SFTP connection and small, safe file helpers on the web server."""
from __future__ import annotations

import errno
import getpass
import json
import os
import posixpath
import shlex
import socket
import stat
import uuid

import paramiko

from .config import Config
from .logutil import LOG, register_secret

KEYRING_SERVICE = "crtdh-publish-agent"

# The only shell commands the agent ever runs on the server. Arguments are filled in quoted, never raw;
# scripts are sent on stdin, not on the command line.
SHELL_COMMANDS = {
    "probe": "echo crtdh-shell-ok",
    "discover": "WEB_ROOT={web_root} sh -s",
}


def shell_command(name: str, **args: str) -> str:
    template = SHELL_COMMANDS[name]
    return template.format(**{k: shlex.quote(str(v)) for k, v in args.items()})


class RemoteError(Exception):
    """Connection or file operation on the server failed."""


class _TrustOnFirstUse(paramiko.MissingHostKeyPolicy):
    """Only used by `check --trust-host-key`: saves the key after showing its fingerprint."""

    def __init__(self, path: str):
        self.path = path

    def missing_host_key(self, client, hostname, key):
        fp = key.fingerprint if hasattr(key, "fingerprint") else key.get_base64()[:32]
        LOG.warning("trusting NEW host key for %s: %s %s (saved to %s)", hostname, key.get_name(), fp, self.path)
        client.get_host_keys().add(hostname, key.get_name(), key)
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        client.save_host_keys(self.path)


def keyring_password(cfg: Config) -> str | None:
    try:
        import keyring  # optional dependency
    except ImportError:
        return None
    try:
        return keyring.get_password(KEYRING_SERVICE, f"{cfg.sftp_user}@{cfg.sftp_host}")
    except Exception:  # noqa: BLE001 - a broken keyring backend must not crash the agent
        return None


def store_keyring_password(cfg: Config, password: str) -> None:
    try:
        import keyring
    except ImportError:
        raise RemoteError("the 'keyring' package is not installed: pip install keyring") from None
    keyring.set_password(KEYRING_SERVICE, f"{cfg.sftp_user}@{cfg.sftp_host}", password)


class Remote:
    def __init__(self, sftp: paramiko.SFTPClient, client: paramiko.SSHClient | None = None):
        self.sftp = sftp
        self.client = client
        self.home = sftp.normalize(".")

    # ---- connection --------------------------------------------------------
    @classmethod
    def connect(cls, cfg: Config, trust_new_host_key: bool = False, interactive: bool = False) -> "Remote":
        client = paramiko.SSHClient()
        if os.path.exists(cfg.known_hosts):
            client.load_host_keys(cfg.known_hosts)
        if trust_new_host_key:
            client.set_missing_host_key_policy(_TrustOnFirstUse(cfg.known_hosts))
        else:
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        kwargs = dict(hostname=cfg.sftp_host, port=cfg.sftp_port, username=cfg.sftp_user,
                      timeout=30, banner_timeout=30, auth_timeout=30,
                      allow_agent=False, look_for_keys=False)
        if cfg.key_file:
            kwargs["key_filename"] = cfg.key_file
            passphrase = keyring_password(cfg)  # only needed for an encrypted key
            if passphrase:
                register_secret(passphrase)
                kwargs["passphrase"] = passphrase
        else:
            password = keyring_password(cfg) if cfg.password_source == "keyring" else None
            if not password:
                if not interactive:
                    raise RemoteError(
                        "no SSH key configured and no password in the system keyring. "
                        "Set key_file (recommended) or run: python -m publish_agent set-password")
                password = getpass.getpass(f"SFTP password for {cfg.sftp_user}@{cfg.sftp_host}: ")
            register_secret(password)
            kwargs["password"] = password
        try:
            client.connect(**kwargs)
        except paramiko.BadHostKeyException:
            raise RemoteError(
                "the server's host key CHANGED since it was trusted. Stop and check with the server owner "
                "before doing anything (possible interception).") from None
        except paramiko.SSHException as exc:
            if "not found in known_hosts" in str(exc) or "Server" in str(exc) and "not found" in str(exc):
                raise RemoteError(
                    "server host key not trusted yet. Run once: python -m publish_agent check --trust-host-key") from None
            raise RemoteError(f"SSH login failed: {exc}") from None
        except (socket.error, OSError) as exc:
            raise RemoteError(f"cannot reach {cfg.sftp_host}:{cfg.sftp_port}: {exc}") from None
        transport = client.get_transport()
        if transport is not None:
            transport.set_keepalive(30)
        return cls(client.open_sftp(), client)

    def close(self) -> None:
        try:
            self.sftp.close()
        finally:
            if self.client:
                self.client.close()

    def exec(self, name: str, stdin: bytes = b"", timeout: int = 30, **args: str) -> tuple[int, str] | None:
        """Run one of the fixed SHELL_COMMANDS if the account allows a shell; None if shell access is disabled."""
        if not self.client:
            return None
        command = shell_command(name, **args)
        try:
            # nosec B601: the command is a fixed template from SHELL_COMMANDS and every argument is shlex.quote'd
            _in, out, err = self.client.exec_command(command, timeout=timeout)  # nosec B601
            if stdin:
                _in.write(stdin)
            _in.channel.shutdown_write()
            text = out.read().decode("utf-8", "replace") + err.read().decode("utf-8", "replace")
            return out.channel.recv_exit_status(), text
        except (paramiko.SSHException, OSError, socket.timeout):
            return None

    # ---- paths -------------------------------------------------------------
    def abspath(self, path: str) -> str:
        if path == "~":
            return self.home
        if path.startswith("~/"):
            path = posixpath.join(self.home, path[2:])
        elif not path.startswith("/"):
            path = posixpath.join(self.home, path)
        return posixpath.normpath(path)

    # ---- queries -----------------------------------------------------------
    def lstat(self, path: str):
        try:
            return self.sftp.lstat(path)
        except FileNotFoundError:
            return None
        except IOError as exc:
            if getattr(exc, "errno", None) == errno.ENOENT:
                return None
            raise

    def exists(self, path: str) -> bool:
        return self.lstat(path) is not None

    def isdir(self, path: str) -> bool:
        try:
            return stat.S_ISDIR(self.sftp.stat(path).st_mode)
        except IOError:
            return False

    def islink(self, path: str) -> bool:
        st = self.lstat(path)
        return bool(st and stat.S_ISLNK(st.st_mode))

    def listdir(self, path: str) -> list[str]:
        try:
            return sorted(self.sftp.listdir(path))
        except IOError:
            return []

    # ---- changes -----------------------------------------------------------
    def makedirs(self, path: str) -> None:
        if self.isdir(path):
            return
        parent = posixpath.dirname(path)
        if parent and parent != path:
            self.makedirs(parent)
        try:
            self.sftp.mkdir(path)
        except IOError:
            if not self.isdir(path):
                raise

    def replace(self, src: str, dst: str) -> None:
        """Rename src over dst (atomic where the server supports posix-rename)."""
        try:
            self.sftp.posix_rename(src, dst)
            return
        except IOError as exc:
            if not self.exists(dst):
                self.sftp.rename(src, dst)
                return
            LOG.debug("posix-rename unavailable (%s); falling back to remove + rename", exc)
        st = self.lstat(dst)
        if st and stat.S_ISDIR(st.st_mode):
            raise RemoteError(f"cannot atomically replace directory {dst}")
        self.sftp.remove(dst)
        self.sftp.rename(src, dst)

    def put_file(self, local: str, remote: str) -> None:
        """Upload via a temp name, then rename, so a dropped connection never leaves a half file under the real name."""
        tmp = f"{remote}.part-{uuid.uuid4().hex[:8]}"
        try:
            self.sftp.put(local, tmp, confirm=True)
        except BaseException:
            try:
                self.sftp.remove(tmp)
            except Exception:  # noqa: BLE001
                pass
            raise
        self.replace(tmp, remote)

    def write_bytes(self, remote: str, data: bytes) -> None:
        tmp = f"{remote}.part-{uuid.uuid4().hex[:8]}"
        with self.sftp.open(tmp, "wb") as fh:
            fh.write(data)
        self.replace(tmp, remote)

    def read_bytes(self, remote: str) -> bytes | None:
        try:
            with self.sftp.open(remote, "rb") as fh:
                return fh.read()
        except IOError:
            return None

    def read_json(self, remote: str):
        raw = self.read_bytes(remote)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return None

    def write_json(self, remote: str, data) -> None:
        self.write_bytes(remote, json.dumps(data, indent=2, sort_keys=True).encode())

    def symlink(self, target: str, link: str) -> None:
        self.sftp.symlink(target, link)

    def rmtree(self, path: str) -> None:
        """Delete a file, symlink or directory tree. Never follows symlinks."""
        st = self.lstat(path)
        if st is None:
            return
        if not stat.S_ISDIR(st.st_mode):
            self.sftp.remove(path)
            return
        for attr in self.sftp.listdir_attr(path):
            child = posixpath.join(path, attr.filename)
            if stat.S_ISDIR(attr.st_mode):
                self.rmtree(child)
            else:
                self.sftp.remove(child)
        self.sftp.rmdir(path)

    def walk_files(self, path: str, prefix: str = ""):
        """Yield (relpath, attr) for every regular file under path (symlinks are not followed)."""
        for attr in self.sftp.listdir_attr(path):
            rel = f"{prefix}{attr.filename}"
            if stat.S_ISDIR(attr.st_mode):
                yield from self.walk_files(posixpath.join(path, attr.filename), rel + "/")
            elif stat.S_ISREG(attr.st_mode):
                yield rel, attr
