import argparse
import os

from .COMMANDS import load as load_commands
from .SERVER import aof, rdb_loader
from .SERVER.context import ServerContext
from .SERVER.dispatcher import CommandDispatcher
from .SERVER.expiry import ActiveExpirer
from .SERVER.replication import Replicas, connect_to_master
from .SERVER.pubsub import PUBSUB
from .SERVER.server import RedisServer

MASTER_REPLID = "8371b4fb1155b71f4a04d3e1bc3e18c4a990aeeb"

# Startup parameters readable with CONFIG GET, with their defaults.
CONFIG_DEFAULTS = {
    "dir": ".",
    "dbfilename": "dump.rdb",
    "appendonly": "no",
    "appenddirname": "appendonlydir",
    "appendfilename": "appendonly.aof",
    "appendfsync": "everysec",
}


def parse_args():
    parser = argparse.ArgumentParser(description="A small Redis-compatible server.")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--replicaof", help='run as a replica of "<host> <port>"')
    for name in CONFIG_DEFAULTS:
        parser.add_argument(f"--{name}")
    return parser.parse_args()


def main():
    args = parse_args()
    print(f"Running Redis Server on port {args.port}")

    config = {name: getattr(args, name) or default for name, default in CONFIG_DEFAULTS.items()}
    config["dir"] = os.path.abspath(config["dir"])

    master, leftover = None, b""
    if args.replicaof:
        role, replication = "slave", {}
        master, leftover = connect_to_master(args.replicaof, args.port)
    else:
        role, replication = "master", {"master_replid": MASTER_REPLID, "master_repl_offset": 0}

    ctx = ServerContext(role=role, replication=replication, config=config)
    rdb_loader.load(ctx.config, ctx.store)  # restore keys from dir/dbfilename, if present
    aof.init(ctx.config)                    # create AOF dir + files when appendonly is yes
    load_commands(ctx)                      # fills ctx.registry
    aof.replay(ctx.config, ctx.registry)    # rebuild store from AOF commands

    server = RedisServer(
        ("localhost", args.port),
        dispatcher=CommandDispatcher(ctx.registry,
                                     Replicas(ctx.blocking),
                                     aof.Appender(ctx.config),
                                     PUBSUB()
                                     ),
        blocking=ctx.blocking,
        replication=ctx.replication,
        tickers=[ActiveExpirer(ctx.store)],
    )
    if master:
        server.attach_master(master, leftover)
    server.serve_forever()


if __name__ == "__main__":
    main()
