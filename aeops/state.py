from typing import Annotated, Any, TypedDict


def merge_ctx(old: dict | None, new: dict | None) -> dict:
    """Merge per-plugin context dicts so plugins never overwrite each other."""
    out = dict(old or {})
    for key, val in (new or {}).items():
        out[key] = {**out.get(key, {}), **val}
    return out


class EngineState(TypedDict, total=False):
    user_input: str
    mode: str                      # "diagnose_only" or "fix"
    plan: list[list[str]]          # stages, each a list of plugin names
    queue: list[str]               # plugins still to run
    current: str
    plugin_context: Annotated[dict[str, dict[str, Any]], merge_ctx]
    replies: list[str]
    final: str
