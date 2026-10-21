"""AWS and Database plugins. Only the manifests exist for now."""
from langgraph.graph import END, START, StateGraph

from ..state import EngineState
from .registry import Plugin, register


def _stub(name):
    def build():
        def run(state: EngineState):
            return {"plugin_context": {name: {"diagnosis": f"{name} plugin is not implemented yet"}}}
        g = StateGraph(EngineState)
        g.add_node("run", run)
        g.add_edge(START, "run")
        g.add_edge("run", END)
        return g.compile()
    return build


register(Plugin("aws", "Diagnoses and fixes cloud infrastructure issues",
                ["ec2", "aws", "instance", "infrastructure", "s3", "cloud"], _stub("aws"),
                ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"], ["ec2:Describe*"]))
register(Plugin("database", "Diagnoses and fixes database issues",
                ["database", "sql", "query", "db", "slow query", "postgres"], _stub("database"),
                ["DATABASE_URL"], ["db:read"]))
