"""The agent's file operations on the machine it runs on: transport = local in config.ini.

For a CMS that runs on the web server itself (deploy/academicweb). Same interface as the SFTP Remote, so every
publish step (upload to a new folder, switch, verify, keep releases, roll back) works unchanged.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess  # nosec B404: runs only the fixed SHELL_COMMANDS templates, arguments shlex-quoted
from types import SimpleNamespace

from .remote import Remote, shell_command


class _File:
    """A local file with paramiko.SFTPFile's prefetch() (a no-op here)."""

    def __init__(self, fh):
        self._fh = fh

    def prefetch(self, *_a):
        pass

    def __getattr__(self, name):
        return getattr(self._fh, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._fh.close()


class _Channel:
    def get_transport(self):
        return self

    def is_active(self):
        return True


class _LocalFiles:
    """The small part of paramiko.SFTPClient the agent uses, on the local filesystem."""

    def normalize(self, path):
        return os.path.realpath(os.path.expanduser("~") if path in (".", "") else os.path.expanduser(path))

    def lstat(self, path):
        return os.lstat(path)

    def stat(self, path):
        return os.stat(path)

    def listdir(self, path):
        return os.listdir(path)

    def listdir_attr(self, path):
        out = []
        for name in os.listdir(path):
            st = os.lstat(os.path.join(path, name))
            out.append(SimpleNamespace(filename=name, st_mode=st.st_mode, st_size=st.st_size, st_mtime=st.st_mtime))
        return out

    def chmod(self, path, mode):
        os.chmod(path, mode)

    def mkdir(self, path):
        os.mkdir(path)

    def rmdir(self, path):
        os.rmdir(path)

    def remove(self, path):
        os.remove(path)

    def rename(self, src, dst):
        if os.path.lexists(dst):
            raise OSError(f"{dst} exists")
        os.rename(src, dst)

    def posix_rename(self, src, dst):
        os.replace(src, dst)

    def symlink(self, target, link):
        os.symlink(target, link)

    def put(self, local, remote, confirm=True):
        shutil.copyfile(local, remote)

    def get(self, remote, local):
        shutil.copyfile(remote, local)

    def readlink(self, path):
        return os.readlink(path)

    def get_channel(self):
        return _Channel()  # nothing to drop: the "connection" is always up

    def open(self, path, mode="rb"):
        return _File(open(path, mode))  # noqa: SIM115

    def close(self):
        pass


class LocalRemote(Remote):
    def __init__(self):
        super().__init__(_LocalFiles(), None)

    def isdir(self, path: str) -> bool:
        try:
            return stat.S_ISDIR(os.stat(path).st_mode)
        except OSError:
            return False

    def exec(self, name: str, stdin: bytes = b"", timeout: int = 30, **args: str):
        try:
            res = subprocess.run(["/bin/sh", "-c", shell_command(name, **args)], input=stdin,  # nosec B603
                                 capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return res.returncode, (res.stdout + res.stderr).decode("utf-8", "replace")
