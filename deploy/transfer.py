#!/usr/bin/env python3
"""Move a whole CRTDH CMS (content, drafts, history, photos, user accounts) from one install to another.

    export:  python transfer.py export > crtdh-transfer.dat        (prints a one-time pass phrase on stderr)
    import:  python transfer.py import <file or https address> [--check] [--yes]

Run from the backend folder (where manage.py is), with the CMS's settings in the environment.
The file is encrypted (scrypt + AES-256-GCM in authenticated chunks), so it can travel through a public address;
the pass phrase is shown once on export and typed on import. Not carried: sessions, sign-in throttles, publish
jobs and agent state (each install has its own), contact-form messages, and OAuth/Claude-connector data.
Import replaces the target's CMS data in one database transaction; nothing changes if any check fails.
"""
import getpass
import hashlib
import io
import json
import os
import secrets
import shutil
import struct
import sys
import tarfile
import tempfile
import time
import urllib.request

MAGIC = b"CRTDHX1\n"
CHUNK = 1 << 20
FORMAT = 1
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"

# What travels. Whole apps of content, plus these models from the system apps.
CONTENT_APPS = ["common", "core", "carousel", "team", "facilities", "services", "innovations", "products",
                "enterprises", "media_gallery"]
EXTRA_MODELS = ["auth.Group", "auth.User", "accounts.UserSecurity", "accounts.RecoveryCode",
                "publishing.Snapshot", "publishing.AuditEntry", "publishing.ReviewRequest", "publishing.MediaAsset"]


def fail(msg):
    print(f"\nSTOPPED: {msg}\nNothing was changed.", file=sys.stderr)
    sys.exit(1)


# ---- crypto ------------------------------------------------------------------------------------------------
def _key(passphrase, salt):
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    return Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(passphrase.strip().lower().encode())


class EncWriter(io.RawIOBase):
    """File-like: plaintext in, MAGIC|salt|prefix then [flag(1) len(4) ciphertext] chunks out; flag 1 = last."""

    def __init__(self, out, passphrase):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        self.out, self.buf, self.n = out, bytearray(), 0
        salt, self.prefix = secrets.token_bytes(16), secrets.token_bytes(8)
        self.header = MAGIC + salt + self.prefix
        self.aes = AESGCM(_key(passphrase, salt))
        out.write(self.header)

    def writable(self):
        return True

    def _emit(self, data, last):
        flag = b"\x01" if last else b"\x00"
        ct = self.aes.encrypt(self.prefix + struct.pack(">I", self.n), bytes(data), self.header + flag)
        self.out.write(flag + struct.pack(">I", len(ct)) + ct)
        self.n += 1

    def write(self, b):
        self.buf += b
        while len(self.buf) > CHUNK:
            self._emit(self.buf[:CHUNK], False)
            del self.buf[:CHUNK]
        return len(b)

    def close(self):
        if not self.closed:
            self._emit(self.buf, True)
            self.out.flush()
        super().close()


class DecReader(io.RawIOBase):
    def __init__(self, src, passphrase):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        self.src, self.buf, self.n, self.done = src, b"", 0, False
        head = src.read(len(MAGIC) + 24)
        if not head.startswith(MAGIC):
            fail("this is not a CRTDH transfer file (or the download was cut short)")
        self.header, self.prefix = head, head[len(MAGIC) + 16:]
        self.aes = AESGCM(_key(passphrase, head[len(MAGIC):len(MAGIC) + 16]))

    def readable(self):
        return True

    def _next(self):
        from cryptography.exceptions import InvalidTag
        meta = self.src.read(5)
        if len(meta) != 5:
            fail("the transfer file is incomplete (download cut short?)")
        flag, size = meta[:1], struct.unpack(">I", meta[1:])[0]
        if size > CHUNK + 64:
            fail("the transfer file is damaged")
        ct = self.src.read(size)
        try:
            pt = self.aes.decrypt(self.prefix + struct.pack(">I", self.n), ct, self.header + flag)
        except InvalidTag:
            fail("wrong pass phrase, or the file was changed" if self.n == 0 else "the transfer file is damaged")
        self.n += 1
        if flag == b"\x01":
            self.done = True
            if self.src.read(1):
                fail("the transfer file has extra data after its end")
        return pt

    def readinto(self, b):
        while not self.buf and not self.done:
            self.buf = self._next()
        k = min(len(b), len(self.buf))
        b[:k] = self.buf[:k]
        self.buf = self.buf[k:]
        return k


# ---- Django ------------------------------------------------------------------------------------------------
def django_up():
    sys.path.insert(0, os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()


def labels():
    from django.apps import apps
    out = [a.label for a in apps.get_app_configs() if a.label in CONTENT_APPS]
    for m in EXTRA_MODELS:
        app, model = m.split(".")
        try:
            apps.get_model(app, model)
            out.append(m)
        except LookupError:
            pass
    return out


def applied_migrations():
    from django.db.migrations.recorder import MigrationRecorder
    return sorted([a, n] for a, n in MigrationRecorder.Migration.objects.values_list("app", "name"))


def media_files(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if not os.path.islink(os.path.join(d, x)))
        for f in sorted(files):
            p = os.path.join(d, f)
            if os.path.isfile(p) and not os.path.islink(p):
                yield p, os.path.relpath(p, root)


def _add_bytes(tar, name, data):
    ti = tarfile.TarInfo(name)
    ti.size, ti.mtime, ti.mode = len(data), int(time.time()), 0o600
    tar.addfile(ti, io.BytesIO(data))


# ---- export ------------------------------------------------------------------------------------------------
def export():
    if sys.stdout.isatty():
        fail("send the output to a file: python transfer.py export > crtdh-transfer.dat")
    django_up()
    from django.conf import settings
    from django.core.management import call_command
    from django.apps import apps

    buf = io.StringIO()
    call_command("dumpdata", *labels(), natural_foreign=True, natural_primary=True, indent=None, stdout=buf)
    data = buf.getvalue().encode()
    rows = json.loads(data)
    counts = {}
    for r in rows:
        counts[r["model"]] = counts.get(r["model"], 0) + 1
    users = [{"username": r["fields"]["username"], "admin": r["fields"]["is_superuser"],
              "active": r["fields"]["is_active"]} for r in rows if r["model"] == "auth.user"]
    files = list(media_files(settings.MEDIA_ROOT)) if os.path.isdir(settings.MEDIA_ROOT) else []
    manifest = {"format": FORMAT, "created": time.strftime("%Y-%m-%d %H:%M:%S %z"),
                "django": __import__("django").get_version(), "migrations": applied_migrations(),
                "counts": counts, "users": users, "data_sha256": hashlib.sha256(data).hexdigest(),
                "media_files": len(files), "media_bytes": sum(os.path.getsize(p) for p, _ in files)}

    words = "".join(secrets.choice(ALPHABET) for _ in range(20))
    passphrase = "-".join(words[i:i + 4] for i in range(0, 20, 4))
    out = EncWriter(sys.stdout.buffer, passphrase)
    with tarfile.open(fileobj=out, mode="w|") as tar:
        _add_bytes(tar, "manifest.json", json.dumps(manifest, indent=1).encode())
        _add_bytes(tar, "data.json", data)
        for p, rel in files:
            tar.add(p, arcname="media/" + rel, recursive=False)
    out.close()
    print(f"\nPacked {len(rows)} records, {len(users)} user(s) "
          f"({', '.join(u['username'] for u in users)}), {len(files)} photos/files "
          f"({manifest['media_bytes'] // 1048576} MB).", file=sys.stderr)
    print(f"PASSPHRASE {passphrase}", file=sys.stderr)


# ---- import ------------------------------------------------------------------------------------------------
def _open_source(src, work):
    if src.startswith("https://"):
        path = os.path.join(work, "download.dat")
        req = urllib.request.Request(src, headers={"User-Agent": "crtdh-transfer/1"})
        print("Downloading...", file=sys.stderr)
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
        except Exception as e:  # noqa: BLE001 - shown to the person, who can retry
            fail(f"could not download {src} ({e})")
        return open(path, "rb")
    if src.startswith("http://"):
        fail("use the https:// address")
    if not os.path.isfile(src):
        fail(f"no file at {src}")
    return open(src, "rb")


def _safe_extract(reader, dest):
    os.makedirs(os.path.join(dest, "media"))
    with tarfile.open(fileobj=reader, mode="r|") as tar:
        for m in tar:
            name = m.name
            parts = name.split("/")
            ok = (m.isfile() and not name.startswith("/") and ".." not in parts and "" not in parts
                  and (name in ("manifest.json", "data.json") or (parts[0] == "media" and len(parts) > 1)))
            if not ok:
                fail(f"the transfer file contains an unexpected entry ({name!r})")
            target = os.path.join(dest, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with tar.extractfile(m) as f, open(target, "wb") as g:
                shutil.copyfileobj(f, g, 1 << 20)


def do_import(src, check, yes):
    django_up()
    from django.conf import settings
    from django.core.cache import cache
    from django.core.management import call_command
    from django.db import transaction

    passphrase = os.environ.get("CRTDH_TRANSFER_KEY") or getpass.getpass("Pass phrase from the export (hidden): ")
    if not passphrase.strip():
        fail("no pass phrase given")
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    parent = os.path.dirname(media_root)
    os.makedirs(parent, exist_ok=True)
    work = tempfile.mkdtemp(prefix=".crtdh-import-", dir=parent)   # same disk as the photos: swap by rename
    try:
        with _open_source(src, work) as f:
            _safe_extract(DecReader(f, passphrase), os.path.join(work, "x"))
        x = os.path.join(work, "x")
        try:
            manifest = json.load(open(os.path.join(x, "manifest.json")))
            data_path = os.path.join(x, "data.json")
        except (OSError, ValueError):
            fail("the transfer file has no manifest")
        if manifest.get("format") != FORMAT:
            fail("this transfer file was made by a different version of the tool")
        if hashlib.sha256(open(data_path, "rb").read()).hexdigest() != manifest["data_sha256"]:
            fail("the content inside the transfer file does not match its checksum")

        from django.apps import apps
        here = {a.label for a in apps.get_app_configs()}
        mine = {tuple(m) for m in applied_migrations()}
        newer = sorted(f"{a}.{n}" for a, n in manifest["migrations"] if a in here and (a, n) not in mine)
        if newer:
            fail("the export comes from newer CMS code than this server has ("
                 + ", ".join(newer[:5]) + "). Update this server first: ~/.crtdh/crtdh update")

        users = manifest["users"]
        print(f"\nTransfer made {manifest['created']}:", file=sys.stderr)
        print(f"  {sum(manifest['counts'].values())} records, {manifest['media_files']} photos/files "
              f"({manifest['media_bytes'] // 1048576} MB)", file=sys.stderr)
        print("  users: " + ", ".join(f"{u['username']}{' (admin)' if u['admin'] else ''}"
                                       f"{'' if u['active'] else ' (inactive)'}" for u in users), file=sys.stderr)
        if not any(u["admin"] and u["active"] for u in users):
            fail("the export has no active admin user, so nobody could sign in after the import")
        if check:
            print("Check passed. Nothing was changed.", file=sys.stderr)
            return
        if not yes:
            ans = input("Type yes to replace this CMS's content, photos and users with these: ")
            if ans.strip() != "yes":
                fail("not confirmed")

        with transaction.atomic():
            call_command("flush", interactive=False, verbosity=0)
            call_command("loaddata", data_path, verbosity=0)
        old = media_root + ".before-import"
        shutil.rmtree(old, ignore_errors=True)
        if os.path.isdir(media_root):
            os.rename(media_root, old)
        os.rename(os.path.join(x, "media"), media_root)
        shutil.rmtree(old, ignore_errors=True)
        try:
            cache.clear()
        except Exception:  # noqa: BLE001 - a cold cache is fine
            pass
        print(f"Imported: content, {manifest['media_files']} photos/files and {len(users)} user(s). "
              "Sign in with the same usernames and passwords as on staging.", file=sys.stderr)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv):
    if len(argv) >= 1 and argv[0] == "export":
        return export()
    if len(argv) >= 2 and argv[0] == "import":
        return do_import(argv[1], "--check" in argv[2:], "--yes" in argv[2:])
    print(__doc__, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
