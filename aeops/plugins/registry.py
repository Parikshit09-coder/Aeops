from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Plugin:
    name: str
    description: str
    keywords: list[str]
    build: Callable            # returns a compiled subgraph
    required_credentials: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


REGISTRY: dict[str, Plugin] = {}


def register(plugin: Plugin) -> None:
    REGISTRY[plugin.name] = plugin
