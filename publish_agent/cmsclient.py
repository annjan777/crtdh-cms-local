"""Talks to the private CMS: poll for the next build, download it, report status.

Every request is signed:
  X-Agent-Timestamp: unix seconds
  X-Agent-Signature: hex HMAC-SHA256(secret, METHOD\\nPATH\\nTIMESTAMP\\nhex SHA256(body))
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from . import __version__
from .logutil import LOG, register_secret

MAX_TARBALL_BYTES = 2 * 1024 ** 3


class CMSError(Exception):
    """CMS unreachable or returned an unexpected answer. Retryable."""


class BuildRejected(Exception):
    """The build offered by the CMS failed verification. Not retryable for this publish."""


@dataclass
class Job:
    publish_id: str
    snapshot_id: str
    tarball_url: str
    sha256: str
    signature: str


def sign_request(secret: str, method: str, path: str, body: bytes, ts: int | None = None) -> dict:
    ts = int(time.time()) if ts is None else ts
    msg = f"{method.upper()}\n{path}\n{ts}\n{hashlib.sha256(body).hexdigest()}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return {"X-Agent-Timestamp": str(ts), "X-Agent-Signature": sig}


def build_signature(secret: str, publish_id: str, snapshot_id: str, sha256: str) -> str:
    msg = f"crtdh-build-v1\n{publish_id}\n{snapshot_id}\n{sha256}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify_job(secret: str, job: Job) -> None:
    expected = build_signature(secret, job.publish_id, job.snapshot_id, job.sha256)
    if not hmac.compare_digest(expected, job.signature or ""):
        raise BuildRejected("build signature does not match (wrong secret or tampered build)")


class CMSClient:
    def __init__(self, base_url: str, secret: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.timeout = timeout
        register_secret(secret)
        self._origin = urllib.parse.urlsplit(self.base_url)[:2]
        self._last_signed = None

    # ---- low level ---------------------------------------------------------
    def _url(self, path_or_url: str) -> str:
        url = urllib.parse.urljoin(self.base_url + "/", path_or_url)
        if urllib.parse.urlsplit(url)[:2] != self._origin:
            raise BuildRejected("CMS pointed the agent at another host; refusing to follow it")
        return url

    def _request(self, method: str, path_or_url: str, body: bytes = b"", content_type: str | None = None):
        url = self._url(path_or_url)
        path = urllib.parse.urlsplit(url).path
        # The CMS accepts each (timestamp, signature) pair once, so never send an identical request twice in a second.
        ts = int(time.time())
        key = (ts, method, path, hashlib.sha256(body).hexdigest())
        if key == self._last_signed:
            time.sleep(1.05)
            ts = int(time.time())
            key = (ts,) + key[1:]
        self._last_signed = key
        headers = sign_request(self.secret, method, path, body, ts)
        headers["User-Agent"] = f"crtdh-publish-agent/{__version__}"
        if content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(url, data=body if method != "GET" else None, method=method, headers=headers)
        try:
            return urllib.request.urlopen(req, timeout=self.timeout)  # noqa: S310 - URL is checked above
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = json.loads(exc.read().decode("utf-8", "replace")).get("message", "")
            except Exception:  # noqa: BLE001
                pass
            if exc.code in (401, 403):
                raise CMSError(f"CMS refused the agent ({exc.code}); check the agent secret and the PC clock. {detail}") from None
            raise CMSError(f"CMS returned HTTP {exc.code} for {path}. {detail}".strip()) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise CMSError(f"cannot reach the CMS: {reason}") from None

    # ---- endpoints ---------------------------------------------------------
    def next_job(self) -> Job | None:
        with self._request("GET", "/api/v1/agent/next/") as resp:
            if resp.status == 204:
                return None
            raw = resp.read()
        try:
            data = json.loads(raw)
            job = Job(str(data["publish_id"]), str(data.get("snapshot_id") or ""),
                      str(data["tarball_url"]), str(data["sha256"]).lower(), str(data.get("signature") or ""))
        except (ValueError, KeyError, TypeError):
            raise CMSError("CMS sent an unreadable /agent/next/ answer") from None
        return job  # the build signature is checked by the caller so a bad one can be reported as failed

    def download(self, job: Job, dest: str) -> None:
        """Stream the tarball to dest, checking size and sha256 on the way."""
        h = hashlib.sha256()
        total = 0
        tmp = dest + ".download"
        with self._request("GET", job.tarball_url) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_TARBALL_BYTES:
                    raise BuildRejected("build tarball is larger than 2 GB; refusing it")
                h.update(chunk)
                out.write(chunk)
        if not hmac.compare_digest(h.hexdigest(), job.sha256):
            os.remove(tmp)
            raise BuildRejected("downloaded build does not match its sha256 (corrupt or tampered)")
        os.replace(tmp, dest)

    def report(self, publish_id: str, status: str, step: str, message: str) -> bool:
        body = json.dumps({"publish_id": publish_id, "status": status, "step": step,
                           "message": message[:1000]}).encode()
        try:
            with self._request("POST", "/api/v1/agent/status/", body, "application/json"):
                pass
            return True
        except (CMSError, BuildRejected) as exc:
            LOG.warning("could not report status %s/%s to the CMS: %s", status, step, exc)
            return False
