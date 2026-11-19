"""Cancel a stuck publish (if any), start a new one as the publisher, report state timings.
    set -a; . .preprod/env; set +a; python tests/tools/wave2/publish_cycle.py [--timeout 900]"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "e2e"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preprod_smoke import S, _trust  # noqa: E402
from helpers import api_session  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--timeout", type=int, default=900)
a = ap.parse_args()
st = Path(".preprod")
_trust(st)
call = api_session(S(st), "priya")
s, body = call("POST", "/api/v1/cms/publish/", {})
if s == 409 and isinstance(body, dict) and body.get("publish_id"):
    s2, b2 = call("POST", f"/api/v1/cms/publish/{body['publish_id']}/cancel/", {})
    print("cancel stuck", body["publish_id"], s2, json.dumps(b2)[:200])
    s, body = call("POST", "/api/v1/cms/publish/", {})
print("publish", s, json.dumps(body)[:300])
pid = (body or {}).get("id") or (body or {}).get("publish_id")
t0, seen, end = time.time(), [], time.time() + a.timeout
while pid and time.time() < end:
    _, stt = call("GET", f"/api/v1/cms/publish/{pid}/")
    key = (stt.get("status"), stt.get("step"))
    if not seen or seen[-1][1:] != key:
        seen.append((round(time.time() - t0, 1), *key, stt.get("message", "")[:120]))
        print(*seen[-1], flush=True)
    if stt.get("status") in ("live", "failed", "cancelled"):
        break
    time.sleep(2)
