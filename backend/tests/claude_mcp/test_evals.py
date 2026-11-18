"""The eval spec stays in step with the tool set; the runner reports not-run without a key."""

import asyncio
import json

import pytest

from mcp_server.evals import run

pytestmark = [pytest.mark.django_db]


def test_spec_has_ten_prompts_naming_real_tools():
    from mcp_server.tools import build_server

    names = {t.name for t in asyncio.run(build_server().list_tools())}
    prompts = run.SPEC["prompts"]
    assert len(prompts) == 10 and len({p["id"] for p in prompts}) == 10
    for p in prompts:
        for want in p["expect"]:
            assert want["tool"] in names, (p["id"], want["tool"])
        for bad in p["forbid"] + p.get("allow_writes", []):
            assert bad in names, (p["id"], bad)


def test_checks_logic():
    spec = {"expect": [{"tool": "update_team_member", "args": {"fields": "Head"}}], "forbid": ["hide_team_member"]}
    good = [{"name": "find_content", "args": {}, "is_error": False},
            {"name": "update_team_member", "args": {"fields": {"designation": "Professor and Head"}}, "is_error": False}]
    assert run.checks(spec, good) == []
    assert run.checks(spec, good + [{"name": "hide_team_member", "args": {}, "is_error": False}])
    assert run.checks(spec, [{**good[1], "is_error": True}])
    assert run.checks({"expect": [], "forbid": [], "read_only": True}, [{"name": "reorder", "args": {}, "is_error": False}])


def test_not_run_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(run, "RESULTS", tmp_path / "results.json")
    assert asyncio.run(run.main_async(None)) == 0
    data = json.loads((tmp_path / "results.json").read_text())
    assert data["status"] == "not-run" and len(data["results"]) == 10
