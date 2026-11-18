"""MCP tool schema snapshot (CI drift check). Lists the tools the CMS MCP server exposes — name, description,
input schema, annotations — as stable JSON, so any change to what Claude sees is a reviewed diff.

    python tests/tools/mcp_schema.py --write          # refresh tests/golden/mcp_tools.json (commit it)
    python tests/tools/mcp_schema.py --check          # CI: exit 1 + unified diff if the tools changed
Run from the repo root with the backend venv; uses config.settings_test (no network, no DB writes).
"""
import argparse
import asyncio
import difflib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "golden" / "mcp_tools.json"


def _dump(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", by_alias=True, exclude_none=True)
    return obj


def current(backend=REPO / "backend"):
    sys.path.insert(0, str(backend))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")
    import django
    django.setup()
    from mcp_server.tools import build_server
    tools = asyncio.run(build_server().list_tools())
    out = []
    for t in sorted(tools, key=lambda t: t.name):
        d = _dump(t)
        out.append({k: d.get(k) for k in ("name", "title", "description", "inputSchema", "input_schema",
                                         "annotations") if d.get(k) is not None})
    return json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--golden", default=str(GOLDEN))
    ap.add_argument("--backend", default=str(REPO / "backend"), help="backend dir (default: this repo)")
    a = ap.parse_args()
    now, golden = current(a.backend), Path(a.golden)
    if a.write:
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(now)
        print(f"wrote {golden} ({len(json.loads(now))} tools)")
        return 0
    if not golden.exists():
        print(f"no golden at {golden}; run --write and commit it")
        return 1
    old = golden.read_text()
    if old == now:
        print(f"MCP tool schemas unchanged ({len(json.loads(now))} tools)")
        return 0
    sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), now.splitlines(True), "golden", "current"))
    print("\nMCP tool schemas changed. If intended, run: python tests/tools/mcp_schema.py --write and commit.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
