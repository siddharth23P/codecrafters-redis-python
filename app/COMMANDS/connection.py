"""Connection commands: PING, ECHO."""
from . import check_arity, register, registered_commands
from ..PROTOCOL.encoder import encode
from ..PROTOCOL.resp_types import SimpleString, BulkString, Raw

EMPTY_RDB = bytes.fromhex(
    "524544495330303131fa0972656469732d76657205372e322e30"
    "fa0a72656469732d62697473c040fa056374696d65c26d08bc65"
    "fa08757365642d6d656dc2b0c41000fa08616f662d62617365c000"
    "fff06e3bfec0ff5aa2"
)

def create(ctx):
    return registered_commands(ConnectionCommands(ctx))


class ConnectionCommands:
    def __init__(self,ctx):
        self.__version = ctx.version
        self.__connected_clients = ctx.connected_clients
        self.__used_memory = ctx.used_memory
        self.__role = ctx.role
        self.__replication = ctx.replication
        
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
    
    @register
    def replconf(self, args):
        if args[0] == "listening_port":
            slave_port = int(args[1])
        if args[0] == "capa":
            capabilities = args[1]
        return SimpleString("OK")
    
    @register
    def psync(self,args):
        check_arity(args, "psync", len(args) == 2)
        repl_id = self.__replication["master_replid"]
        offset = self.__replication["master_repl_offset"]
        header = encode(SimpleString(f"FULLRESYNC {repl_id} {offset}"))
        rdb = b"$%d\r\n" % len(EMPTY_RDB) + EMPTY_RDB
        return Raw(header + rdb)
            

        
