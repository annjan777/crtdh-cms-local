"""Local SFTP server standing in for the CIC host (academicweb) in the preprod rehearsal.

Wraps publish_agent.tests.fakes.FakeSFTPServer (paramiko, SFTP-only, no exec, fault injection).
  python tests/tools/sftp_host.py --root .preprod/sftp --port 2223 --client-key .preprod/agent_key --known-hosts .preprod/known_hosts
Faults (env): SFTP_QUOTA_BYTES, SFTP_DROP_AFTER_FILES, SFTP_NO_SYMLINK=1, SFTP_NO_POSIX_RENAME=1
Web root as the agent sees it: ~/public_html  ==  <root>/home/u/public_html on disk.
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    import paramiko

    from publish_agent.tests.fakes import FakeSFTPServer

    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--port", type=int, default=2223)
    ap.add_argument("--client-key", required=True, help="private key file; created if missing")
    ap.add_argument("--known-hosts", required=True)
    a = ap.parse_args()
    kp = Path(a.client_key)
    if not kp.exists():
        paramiko.RSAKey.generate(2048).write_private_key_file(str(kp))
        os.chmod(kp, 0o600)
    key = paramiko.RSAKey.from_private_key_file(str(kp))
    hk = Path(a.root).parent / "sftp_host_key"
    if hk.exists():
        FakeSFTPServer.host_key = paramiko.RSAKey.from_private_key_file(str(hk))
    else:
        FakeSFTPServer.host_key = paramiko.RSAKey.generate(2048)
        FakeSFTPServer.host_key.write_private_key_file(str(hk))
    srv = FakeSFTPServer(a.root, key, port=a.port)
    f = srv.faults
    f.quota_bytes = int(os.environ["SFTP_QUOTA_BYTES"]) if os.environ.get("SFTP_QUOTA_BYTES") else None
    f.drop_after_files = int(os.environ["SFTP_DROP_AFTER_FILES"]) if os.environ.get("SFTP_DROP_AFTER_FILES") else None
    f.no_symlink = os.environ.get("SFTP_NO_SYMLINK") == "1"
    f.no_posix_rename = os.environ.get("SFTP_NO_POSIX_RENAME") == "1"
    web = Path(srv.home_path("public_html"))
    web.mkdir(parents=True, exist_ok=True)
    if not any(web.iterdir()):
        (web / "index.html").write_text("<!doctype html><title>CRTDH (before first publish)</title><h1>old site</h1>")
    Path(a.known_hosts).write_text(srv.known_hosts_line())
    print(f"sftp host on 127.0.0.1:{srv.port} web root {web}", flush=True)
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
