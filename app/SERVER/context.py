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
    replication:dict = {
        "connected_slave": 0,
        "master_replid":None,
        "master_repl_offset":0,
        "second_repl_offset":0,
        "repl_backlog_active":0,
        "repl_backlog_size":0,
        "repl_backlog_first_byte_offset":0,
        "repl_backlog_histlen": 0,
    }

    def __post_init__(self):
        self.blocking = BlockingRegistry(self.store)
