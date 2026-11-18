"""Stand-in for `npm run build` in tests: renders one HTML file per page from $SNAPSHOT_PATH into $BUILD_OUTPUT_DIR.
Exit code / behaviour can be forced with FAKE_BUILD_FAIL=1."""
import json
import os
import sys
from pathlib import Path

if os.environ.get("FAKE_BUILD_FAIL"):
    print("vite: something broke", file=sys.stderr)
    sys.exit(3)
snap = json.loads(Path(os.environ["SNAPSHOT_PATH"]).read_text())
out = Path(os.environ["BUILD_OUTPUT_DIR"])
out.mkdir(parents=True, exist_ok=True)
for page in snap["registry"]["pages"]:
    target = out / ("index.html" if page["path"] == "/" else page["path"].strip("/") + "/index.html")
    target.parent.mkdir(parents=True, exist_ok=True)
    titles = [r.get("heading") or "" for r in snap["collections"]["hero-slides"]] if page["id"] == "home" else []
    target.write_text(f"<!doctype html><title>{page['title']}</title><p>{snap['snapshot_id']}</p><p>{'|'.join(titles)}</p>\n")
(out / "assets").mkdir(exist_ok=True)
(out / "assets" / "app.js").write_text("console.log('ok')\n")
