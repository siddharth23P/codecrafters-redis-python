"""Connection and server commands: PING, ECHO, INFO, REPLCONF, PSYNC."""
from ..PROTOCOL.encoder import encode
from ..PROTOCOL.resp_types import BulkString, Raw, SimpleString, ToMaster
from . import check_arity, register, registered_commands

# Snapshot sent to a new replica on full resync: an RDB file with no keys.
EMPTY_RDB = bytes.fromhex(
    "524544495330303131fa0972656469732d76657205372e322e30"
    "fa0a72656469732d62697473c040fa056374696d65c26d08bc65"
    "fa08757365642d6d656dc2b0c41000fa08616f662d62617365c000"
    "fff06e3bfec0ff5aa2"
)


def create(ctx):
    return registered_commands(ConnectionCommands(ctx))


class ConnectionCommands:
    def __init__(self, ctx):
        self._ctx = ctx

    @register
    def ping(self, args):
        """PING -> +PONG.  PING message -> message as a bulk string."""
        check_arity("ping", len(args) <= 1)
        return args[0] if args else SimpleString("PONG")

    @register
    def echo(self, args):
        """ECHO message -> message as a bulk string."""
        check_arity("echo", len(args) == 1)
        return args[0]

    @register
    def info(self, args):
        """INFO [replication] -> "field:value" lines as one bulk string."""
        ctx = self._ctx
        fields = {"role": ctx.role}
        if b"replication" in (a.lower() for a in args):
            fields.update(ctx.replication)
        else:
            fields.update(version=ctx.version,
                          connected_clients=ctx.connected_clients,
                          used_memory=ctx.used_memory)
        return BulkString("\r\n".join(f"{k}:{v}" for k, v in fields.items()).encode())

    @register
    def replconf(self, args):
        """REPLCONF GETACK * -> REPLCONF ACK <offset> (sent even on the master link); else +OK."""
        check_arity("replconf", len(args) >= 1)
        if args[0].lower() == b"getack":
            offset = self._ctx.replication.get("master_repl_offset", 0)
            return ToMaster([b"REPLCONF", b"ACK", str(offset).encode()])
        return SimpleString("OK")

    @register
    def psync(self, args):
        """PSYNC replid offset -> +FULLRESYNC <replid> <offset>, then the RDB snapshot."""
        check_arity("psync", len(args) == 2)
        repl = self._ctx.replication
        header = SimpleString(f"FULLRESYNC {repl['master_replid']} {repl['master_repl_offset']}")
        return Raw(encode(header) + _rdb_payload(EMPTY_RDB))


def _rdb_payload(rdb):
    """RDB file framed as $<len>\\r\\n<bytes>: like a bulk string, but with no trailing CRLF."""
    return b"$%d\r\n" % len(rdb) + rdb
