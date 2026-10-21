import shutil
from pathlib import Path

import pytest
from langgraph.types import Command

from aeops.engine import make_engine, select_plugins


@pytest.fixture
def repo(tmp_path, monkeypatch):
    dst = tmp_path / "repo"
    shutil.copytree(Path(__file__).parent.parent / "demo_repo", dst)
    monkeypatch.setenv("AEOPS_REPO", str(dst))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return dst


def cfg(i):
    return {"configurable": {"thread_id": i}}


def test_routing():
    assert select_plugins("there is a bug in my code") == ["github"]
    assert select_plugins("ec2 instance is down") == ["aws"]


def test_plugin_not_enabled(repo):
    eng = make_engine({"github"})
    out = eng.invoke({"user_input": "my ec2 instance is down"}, cfg("a"))
    assert "Enable the 'aws' plugin" in out["final"]


def test_diagnose_then_fix_with_approval(repo):
    eng = make_engine({"github"})
    out = eng.invoke({"user_input": "there is an error in my code"}, cfg("b"))
    assert out["__interrupt__"][0].value["type"] == "followup"
    assert "len(items) + 1" in (repo / "stats.py").read_text()   # nothing changed yet
    out = eng.invoke(Command(resume="ok fix it"), cfg("b"))
    assert out["__interrupt__"][0].value["type"] == "approval"
    assert "len(items) + 1" in (repo / "stats.py").read_text()   # still unchanged
    out = eng.invoke(Command(resume="y"), cfg("b"))
    assert "fix applied and verified" in out["final"]
    assert "+ 1" not in (repo / "stats.py").read_text()


def test_reject_leaves_code_untouched(repo):
    eng = make_engine({"github"})
    eng.invoke({"user_input": "fix the bug in my code"}, cfg("c"))
    out = eng.invoke(Command(resume="n"), cfg("c"))
    assert "__interrupt__" not in out
    assert "len(items) + 1" in (repo / "stats.py").read_text()
