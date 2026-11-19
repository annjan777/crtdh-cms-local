"""Minimal SMTP sink for the preprod rehearsal: accepts every message, writes it to <dir>/<n>.eml.
Production uses SMTP (EMAIL_URL=smtp+tls://…); settings support no file backend path, so the rehearsal
points EMAIL_URL at this sink instead.  Usage: python smtp_sink.py --dir .preprod/mail --port 2525"""
import argparse
import itertools
import socketserver
import time
from pathlib import Path

COUNTER = itertools.count()


class H(socketserver.StreamRequestHandler):
    out = None

    def reply(self, line):
        self.wfile.write((line + "\r\n").encode())

    def handle(self):
        self.reply("220 crtdh-rehearsal-sink")
        rcpt, data = [], None
        while True:
            line = self.rfile.readline()
            if not line:
                return
            cmd = line.decode(errors="replace").strip()
            up = cmd.upper()
            if up.startswith(("EHLO", "HELO")):
                self.reply("250 ok")
            elif up.startswith("MAIL FROM"):
                rcpt = []
                self.reply("250 ok")
            elif up.startswith("RCPT TO"):
                rcpt.append(cmd.split(":", 1)[1].strip())
                self.reply("250 ok")
            elif up == "DATA":
                self.reply("354 end with .")
                buf = []
                for raw in iter(self.rfile.readline, b""):
                    if raw in (b".\r\n", b".\n"):
                        break
                    buf.append(raw[1:] if raw.startswith(b"..") else raw)
                data = b"".join(buf)
                f = Path(self.out) / f"{int(time.time())}-{next(COUNTER)}.log"
                f.write_bytes(b"X-Rcpt-To: " + ", ".join(rcpt).encode() + b"\r\n" + data)
                self.reply("250 queued")
            elif up in ("RSET", "NOOP"):
                self.reply("250 ok")
            elif up == "QUIT":
                self.reply("221 bye")
                return
            else:
                self.reply("502 not implemented")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--port", type=int, default=2525)
    a = ap.parse_args()
    Path(a.dir).mkdir(parents=True, exist_ok=True)
    H.out = a.dir
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer(("127.0.0.1", a.port), H).serve_forever()
