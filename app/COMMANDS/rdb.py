"""Stream commands."""
from . import check_arity, register, registered_commands, to_int
from ..PROTOCOL.resp_types import Array, BulkString, CommandError, Integer, SimpleString, WrongTypeError
from ..SERVER.blocking import Blocked
from collections import deque, OrderedDict
import time

def create(ctx):
    return registered_commands(RDBCommands(ctx.config))


class RDBCommands:
    def __init__(self, config):
        self._config = config

    @register
    def config(self, args):
        check_arity(args, "config", len(args) >= 1)
        sub_cmd = args[0]
        if sub_cmd.lower() == b"get":
            return self._config_get([arg.lower() for arg in args[1:]])
        # if sub_cmd.lower() == b"set":
        #     return self._config_set(args[1:])
        raise CommandError(f"Unknown CONFIG subcommand '{sub_cmd.decode()}'")
    
    def _config_get(self, args):
        check_arity(args, "config get", len(args) >= 1)
        params = args
        reply = []
        
        if b'dir' in params:
            reply.append(BulkString(b'dir'))
            reply.append(BulkString(self._config['dir'].encode()))
        if b'dbfilename' in params:
            reply.append(BulkString(b'dbfilename'))
            reply.append(BulkString(self._config['dbfilename'].encode()))
        if b'appendonly' in params:
            reply.append(BulkString(b'appendonly'))
            reply.append(BulkString(self._config['appendonly'].encode()))
        if b'appenddirname' in params:
            reply.append(BulkString(b'appenddirname'))
            reply.append(BulkString(self._config['appenddirname'].encode()))
        if b'appendfilename' in params:
            reply.append(BulkString(b'appendfilename'))
            reply.append(BulkString(self._config['appendfilename'].encode()))
        if b'appendfsync' in params:
            reply.append(BulkString(b'appendfsync'))
            reply.append(BulkString(self._config['appendfsync'].encode()))
        
        return BulkString([r for r in reply]) if reply else BulkString([])
            