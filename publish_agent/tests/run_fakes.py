"""Manual end-to-end sandbox: fake CMS on 127.0.0.1:8500 and fake SFTP host on 127.0.0.1:2222.

    python -m publish_agent.tests.run_fakes /tmp/crtdh-e2e
Writes /tmp/crtdh-e2e/config.ini, queues two builds, and serves until Ctrl+C. Then, in another shell:
    CRTDH_AGENT_SECRET=local-test-agent-secret-0123456789 python -m publish_agent -c /tmp/crtdh-e2e/config.ini check --no-http
    CRTDH_AGENT_SECRET=... python -m publish_agent -c /tmp/crtdh-e2e/config.ini run --once
Local test values only.
"""
import os
import sys
import time

import paramiko

from .conftest import SECRET
from .fakes import S1, S2, FakeCMS, FakeSFTPServer, make_build, media_name


def main(base: str) -> None:
    os.makedirs(base, exist_ok=True)
    key = paramiko.RSAKey.generate(2048)
    key_path = os.path.join(base, "id_rsa")
    key.write_private_key_file(key_path)
    srv = FakeSFTPServer(os.path.join(base, "server"), key, port=2222)
    os.makedirs(srv.home_path("public_html"), exist_ok=True)
    with open(srv.home_path("public_html", "index.html"), "w") as fh:
        fh.write("old site")
    cms = FakeCMS(SECRET, port=8500)
    img = b"demo-image" * 100
    cms.queue(S1, "pub-1", make_build(S1, "pub-1", media={media_name(img): img}))
    cms.queue(S2, "pub-2", make_build(S2, "pub-2", media_all=[media_name(img)]))
    with open(os.path.join(base, "known_hosts"), "w") as fh:
        fh.write(srv.known_hosts_line())
    with open(os.path.join(base, "config.ini"), "w") as fh:
        fh.write(f"""[cms]
url = http://127.0.0.1:8500
secret_env = CRTDH_AGENT_SECRET
poll_seconds = 5
[sftp]
host = 127.0.0.1
port = 2222
user = u
key_file = {key_path}
known_hosts = {os.path.join(base, 'known_hosts')}
[site]
web_root = ~/public_html
strategy = auto
keep_releases = 2
[agent]
state_dir = {os.path.join(base, 'state')}
""")
    print(f"fake CMS on :8500, fake SFTP on :2222, config {base}/config.ini; Ctrl+C to stop", flush=True)
    try:
        while True:
            time.sleep(1)
            for s in cms.statuses:
                if not s.get("_shown"):
                    print("status:", {k: v for k, v in s.items() if k != "_shown"}, flush=True)
                    s["_shown"] = True
    except KeyboardInterrupt:
        pass
    finally:
        cms.close()
        srv.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/crtdh-e2e")
