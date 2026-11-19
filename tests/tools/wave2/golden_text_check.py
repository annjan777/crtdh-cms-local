"""CRITICAL regression triage: for every golden item/image-alt the exact-match comparison reports as lost,
is its text still on the built page (any markup)? Separates real content loss from redesign markup changes.
    python tests/tools/wave2/golden_text_check.py --site https://localhost:3602 --current /tmp/cur.json"""
import argparse
import html
import json
import re
import ssl
import urllib.request
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--site", required=True)
ap.add_argument("--current", required=True)
ap.add_argument("--ca", default=".preprod/tls/cert.pem")
a = ap.parse_args()
g = json.loads(Path("tests/e2e/golden/public_content.json").read_text())
c = json.loads(Path(a.current).read_text())
ctx = ssl.create_default_context(cafile=a.ca)


def page_text(r):
    h = urllib.request.urlopen(a.site + r, context=ctx).read().decode()
    alts = " ".join(re.findall(r'alt="([^"]*)"', h))
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)) + " " + alts).lower()


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


total = 0
for r in g:
    t = page_text(r)
    lost = sorted(set(g[r]["items"]) - set(c[r]["items"]))
    # an item is "present" if its first 30 normalised chars appear on the page
    gone = [x for x in lost if norm(x)[:30] and norm(x)[:30] not in t]
    alts = sorted({i["alt"] for i in g[r]["images"] if i["alt"]} - {i["alt"] for i in c[r]["images"]})
    gone_alts = [x for x in alts if norm(x) not in t]
    total += len(gone) + len(gone_alts)
    print(f"{r:15} exact-lost {len(lost):3}  text-missing {len(gone):3} {[x[:60] for x in gone[:4]]}  "
          f"alts-missing {len(gone_alts)} {[x[:40] for x in gone_alts[:4]]}")
print(f"\nTOTAL golden items/alts whose text is not on the page: {total}")
