"""Main Engine: routes a request to plugins, plans their order and runs them."""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .plugins import REGISTRY
from .plugins import github, stubs  # noqa: F401  (registers plugins)
from .state import EngineState

# order to use when several plugins are needed and the planner is unsure
KNOWN_ORDERINGS = ["github", "aws", "database"]


def detect_mode(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("fix", "solve", "repair", "patch")):
        return "fix"
    return "diagnose_only"


def select_plugins(text: str) -> list[str]:
    t = text.lower()
    hits = [n for n, p in REGISTRY.items() if any(k in t for k in p.keywords)]
    return sorted(hits, key=KNOWN_ORDERINGS.index)


def make_engine(enabled: set[str], checkpointer=None):
    def route(state: EngineState):
        wanted = select_plugins(state["user_input"])
        missing = [p for p in wanted if p not in enabled]
        if not wanted:
            return {"queue": [], "replies": ["I could not match this to any plugin."]}
        if missing:
            return {"queue": [], "replies": [f"Enable the '{m}' plugin to ask about this." for m in missing]}
        # sequential by default: one stage per plugin, in the known order
        return {
            "plan": [[p] for p in wanted],
            "queue": wanted,
            "mode": detect_mode(state["user_input"]),
            "replies": [],
        }

    def dispatch(state: EngineState):
        q = list(state.get("queue", []))
        return {"current": q.pop(0) if q else "", "queue": q}

    def pick(state: EngineState) -> str:
        return state["current"] or "respond"

    def respond(state: EngineState):
        lines = list(state.get("replies", []))
        for name, c in state.get("plugin_context", {}).items():
            if "diagnosis" in c:
                lines.append(f"[{name}] {c['diagnosis']}")
            if c.get("verified"):
                lines.append(f"[{name}] fix applied and verified")
            if c.get("reverted"):
                lines.append(f"[{name}] change reverted")
        return {"final": "\n".join(lines)}

    g = StateGraph(EngineState)
    g.add_node("route", route)
    g.add_node("dispatch", dispatch)
    g.add_node("respond", respond)
    g.add_edge(START, "route")
    g.add_edge("route", "dispatch")
    for name in enabled:
        g.add_node(name, REGISTRY[name].build())
        g.add_edge(name, "dispatch")
    g.add_conditional_edges("dispatch", pick, [*enabled, "respond"])
    g.add_edge("respond", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())
