"""Where things live on the server for each switch strategy, and the remote state file.

    symlink   web_root -> <base>/releases/<id>        media: <base>/_media  (release/_media -> ../../_media)
    htaccess  web_root/.htaccess rewrites to <web_root>/_crtdh/releases/<id>   media: <web_root>/_crtdh/_media
    swap      web_root IS the live release dir; others in <base>/releases/   media: <web_root>/_media (moves with the live dir)
    copy      files copied into web_root; releases kept in <base>/releases/   media: <web_root>/_media

Release metadata: <base>/meta/<id>.json (never inside a served folder); state: <base>/state.json.
Media is served at /_media/ (contract addendum A13); /media/ is the Media & Gallery page and is ordinary site content.
"""
from __future__ import annotations

import posixpath
from dataclasses import dataclass

from .bundle import MEDIA_NAME, MEDIA_PREFIX
from .config import Config
from .remote import Remote

STAGING_MARKER = ".crtdh-staging.json"  # only inside <id>.partial folders, which are never served
STATE_FILE = "state.json"
META_DIR = "meta"  # <base>/meta/<release id>.json: what each release holds (never inside a served folder)
OUR_MEDIA = MEDIA_NAME  # media GC only ever touches names like this


@dataclass
class Layout:
    strategy: str
    web_root: str
    base: str
    media_dir: str

    @property
    def releases(self) -> str:
        return posixpath.join(self.base, "releases")

    @property
    def state_file(self) -> str:
        return posixpath.join(self.base, STATE_FILE)

    @property
    def meta_dir(self) -> str:
        return posixpath.join(self.base, META_DIR)

    def meta_file(self, rid: str) -> str:
        return posixpath.join(self.meta_dir, rid + ".json")

    def staging(self, rid: str) -> str:
        return posixpath.join(self.releases, rid + ".partial")

    def stored(self, rid: str) -> str:
        return posixpath.join(self.releases, rid)

    def live_path(self, state: dict, rid: str) -> str:
        """Directory currently holding release rid on the server."""
        if self.strategy == "swap" and state.get("current") == rid:
            return self.web_root
        return self.stored(rid)


def make_layout(cfg: Config, remote: Remote, strategy: str) -> Layout:
    web_root = remote.abspath(cfg.web_root)
    if strategy == "htaccess":
        base = remote.abspath(cfg.base_dir) if cfg.base_dir else posixpath.join(web_root, "_crtdh")
        if not (base + "/").startswith(web_root.rstrip("/") + "/"):
            raise ValueError("htaccess strategy needs base_dir inside web_root")
        media = posixpath.join(base, MEDIA_PREFIX)
    else:
        default = posixpath.join(posixpath.dirname(web_root), "crtdh-releases")
        base = remote.abspath(cfg.base_dir) if cfg.base_dir else default
        if (base + "/").startswith(web_root.rstrip("/") + "/"):
            raise ValueError(f"{strategy} strategy needs base_dir outside web_root")
        media = posixpath.join(base if strategy == "symlink" else web_root, MEDIA_PREFIX)
    return Layout(strategy, web_root, base, media)


def empty_state(strategy: str) -> dict:
    return {"version": 1, "strategy": strategy, "current": None, "history": [], "kinds": {}}


def read_meta(remote: Remote, layout: Layout, rid: str) -> dict | None:
    """Release metadata (files, media, index folders, build id). Kept beside releases/, not in the release folder,
    so the web server never serves it: <base> is outside the web root, or (htaccess strategy) inside _crtdh/,
    which the agent's rules refuse to serve directly."""
    meta = remote.read_json(layout.meta_file(rid))
    return meta if isinstance(meta, dict) else None


def write_meta(remote: Remote, layout: Layout, rid: str, meta: dict) -> None:
    remote.makedirs(layout.meta_dir)
    remote.write_json(layout.meta_file(rid), meta)


def drop_meta(remote: Remote, layout: Layout, rid: str) -> None:
    if remote.exists(layout.meta_file(rid)):
        remote.sftp.remove(layout.meta_file(rid))


def load_state(remote: Remote, layout: Layout) -> dict:
    state = remote.read_json(layout.state_file)
    if not isinstance(state, dict) or "history" not in state:
        return empty_state(layout.strategy)
    state.setdefault("kinds", {})
    return state


def save_state(remote: Remote, layout: Layout, state: dict) -> None:
    remote.makedirs(layout.base)
    remote.write_json(layout.state_file, state)
