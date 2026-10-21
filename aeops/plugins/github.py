"""GitHub plugin: finds failing tests in a repo, proposes a patch, waits for
approval, applies it, verifies and can revert."""
import os
import subprocess
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ..llm import ask_json, have_key
from ..state import EngineState
from .registry import Plugin, register

NAME = "github"


def _repo() -> Path:
    return Path(os.getenv("AEOPS_REPO", "demo_repo")).resolve()


def _run_tests() -> tuple[bool, str]:
    p = subprocess.run(
        ["python", "-m", "pytest", "-x", "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=_repo(), capture_output=True, text=True,
    )
    return p.returncode == 0, (p.stdout + p.stderr)[-3000:]


def _ctx(update: dict) -> dict:
    return {"plugin_context": {NAME: update}}


def diagnose(state: EngineState):
    ok, output = _run_tests()
    if ok:
        return _ctx({"diagnosis": "All tests pass, nothing to fix.", "healthy": True})
    src = {}
    for f in _repo().glob("*.py"):
        if not f.name.startswith("test_"):
            src[f.name] = f.read_text()
    if have_key():
        res = ask_json(
            "You are debugging a Python repo.",
            f"Test output:\n{output}\n\nSource files:\n{src}\n\n"
            'Return {"file": ..., "diagnosis": ...}',
        )
        target, text = res["file"], res["diagnosis"]
    else:
        target = next(iter(src))
        text = "Failing test points at " + target + ":\n" + output.strip().splitlines()[-1]
    return _ctx({"diagnosis": text, "target": target, "test_output": output, "healthy": False})


def after_diagnose(state: EngineState) -> str:
    c = state["plugin_context"][NAME]
    if c.get("healthy"):
        return "done"
    return "propose" if state.get("mode") == "fix" else "await_followup"


def await_followup(state: EngineState):
    reply = interrupt({
        "type": "followup",
        "plugin": NAME,
        "message": state["plugin_context"][NAME]["diagnosis"],
    })
    wants_fix = any(w in str(reply).lower() for w in ("fix", "patch", "apply", "yes"))
    return {"mode": "fix" if wants_fix else "diagnose_only"}


def after_followup(state: EngineState) -> str:
    return "propose" if state.get("mode") == "fix" else "done"


def propose(state: EngineState):
    c = state["plugin_context"][NAME]
    path = _repo() / c["target"]
    original = path.read_text()
    if have_key():
        res = ask_json(
            "You fix bugs with minimal edits.",
            f"Diagnosis: {c['diagnosis']}\nTests:\n{c['test_output']}\n"
            f"File {c['target']}:\n{original}\n"
            'Return {"new_content": <full file>, "explanation": ...}',
        )
        new, why = res["new_content"], res["explanation"]
    else:
        new, why = _mock_fix(original)
    # keep the undo action before anything runs
    return _ctx({"new_content": new, "explanation": why, "revert_content": original})


def _mock_fix(src: str) -> tuple[str, str]:
    fixed = src.replace("len(items) + 1", "len(items)").replace("range(1, n)", "range(n)")
    return fixed, "Corrected an off by one error."


def approval_gate(state: EngineState):
    c = state["plugin_context"][NAME]
    decision = interrupt({
        "type": "approval",
        "plugin": NAME,
        "action": f"Overwrite {c['target']}",
        "explanation": c["explanation"],
        "revertible": True,
    })
    return _ctx({"approved": bool(decision is True or str(decision).lower() in ("approve", "yes", "y"))})


def after_gate(state: EngineState) -> str:
    return "execute" if state["plugin_context"][NAME]["approved"] else "done"


def execute(state: EngineState):
    c = state["plugin_context"][NAME]
    (_repo() / c["target"]).write_text(c["new_content"])
    return _ctx({"executed": True})


def verify(state: EngineState):
    ok, out = _run_tests()
    return _ctx({"verified": ok, "verify_output": out})


def after_verify(state: EngineState) -> str:
    return "done" if state["plugin_context"][NAME]["verified"] else "revert_gate"


def revert_gate(state: EngineState):
    decision = interrupt({
        "type": "approval",
        "plugin": NAME,
        "action": "Revert the change (tests still failing)",
        "revertible": True,
    })
    ok = bool(decision is True or str(decision).lower() in ("approve", "yes", "y"))
    if ok:
        c = state["plugin_context"][NAME]
        (_repo() / c["target"]).write_text(c["revert_content"])
    return _ctx({"reverted": ok})


def build():
    g = StateGraph(EngineState)
    for fn in (diagnose, await_followup, propose, approval_gate, execute, verify, revert_gate):
        g.add_node(fn.__name__, fn)
    g.add_node("done", lambda s: {})
    g.add_edge(START, "diagnose")
    g.add_conditional_edges("diagnose", after_diagnose)
    g.add_conditional_edges("await_followup", after_followup)
    g.add_edge("propose", "approval_gate")
    g.add_conditional_edges("approval_gate", after_gate)
    g.add_edge("execute", "verify")
    g.add_conditional_edges("verify", after_verify)
    g.add_edge("revert_gate", "done")
    g.add_edge("done", END)
    return g.compile()


register(Plugin(
    name=NAME,
    description="Finds and fixes failing code in a repository",
    keywords=["code", "bug", "repo", "github", "test", "error in my code", "commit", "push"],
    build=build,
    required_credentials=["GITHUB_TOKEN"],
    permissions=["repo:read", "repo:write"],
))
