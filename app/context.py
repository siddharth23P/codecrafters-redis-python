"""Shared services handed to commands by the loader, so no command module keeps global state."""
from dataclasses import dataclass, field


@dataclass
class ServerContext:
    registry: dict = field(default_factory=dict)  # command name -> callable(args) -> reply
    store: dict = field(default_factory=dict)     # key -> value, for SET/GET and friends
