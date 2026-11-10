"""Connection commands: PING, ECHO."""
from . import check_arity, register, registered_commands
from ..PROTOCOL.resp_types import SimpleString, BulkString


def create(ctx):
    return registered_commands(ConnectionCommands())


class ConnectionCommands:
    def __init__(self):
        self.__version = "0.0.0"
        self.__connected_clients = 0
        self.__used_memory = 0
        self.__role = "master"
        self.__replication = {
            "connected_slave":0,
            "master_replid":None,
            "master_repl_offset":0,
            "second_repl_offset":0,
            "repl_backlog_active":0,
            "repl_backlog_size":0,
            "repl_backlog_first_byte_offset":0,
            "repl_backlog_histlen": 0,
        }
    @register
    def ping(self, args):
        """PING -> +PONG.  PING message -> message as a bulk string."""
        check_arity(args, "ping", len(args) <= 1)
        return args[0] if args else SimpleString("PONG")

    @register
    def echo(self, args):
        """ECHO message -> message as a bulk string."""
        check_arity(args, "echo", len(args) == 1)
        return args[0]

    @register
    def info(self, args):
        info_dump = {}
        info_dump = {"role": self.__role}
        if b"replication" in (a.lower() for a in args):
            info_dump.update(self.__replication)
        else:
            info_dump.update(version=self.__version,
                             connected_clients=self.__connected_clients,
                             used_memory=self.__used_memory)
        text = "\r\n".join(f"{k}:{v}" for k, v in info_dump.items())
        return BulkString(text.encode())

        
