"""Shared services handed to commands by the loader, so no command module keeps global state."""
from dataclasses import dataclass, field

from .blocking import BlockingRegistry


@dataclass
class ServerContext:
    registry: dict = field(default_factory=dict)  # command name -> callable(args) -> reply
    store: dict = field(default_factory=dict)     # key -> (value, expires_at) or [deque, expires_at]
    blocking: BlockingRegistry = field(init=False)  # clients parked by BLPOP
    role: str = "master"
    version: str="0.0.0"
    connected_clients: int = 0
    used_memory: int = 0
    replication:dict = field(default_factory=dict)

    def __post_init__(self):
        self.blocking = BlockingRegistry(self.store)
