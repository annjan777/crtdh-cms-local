"""Self-signed TLS cert for localhost/127.0.0.1 (preprod rehearsal and E2E run over HTTPS because
production settings refuse non-https origins). Usage: python devcert.py <dir>  -> dir/cert.pem, dir/key.pem"""
import subprocess
import sys
from pathlib import Path


def make(directory):
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    cert, key = d / "cert.pem", d / "key.pem"
    if not cert.exists():
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30",
                        "-keyout", str(key), "-out", str(cert), "-subj", "/CN=localhost",
                        "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
                       check=True, capture_output=True)
        key.chmod(0o600)
    return cert, key


if __name__ == "__main__":
    print(*make(sys.argv[1]))
