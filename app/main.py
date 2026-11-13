import argparse
import os
from .COMMANDS import load as load_commands
from .SERVER.context import ServerContext
from .SERVER.dispatcher import CommandDispatcher
from .SERVER.expiry import ActiveExpirer
from .SERVER.server import RedisServer
from .SERVER.replication import connect_to_master
from .SERVER import rdb_loader

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--replicaof", type=str, default=None)
    parser.add_argument("--dir", type=str, default=None)
    parser.add_argument("--dbfilename", type=str, default=None)
    parser.add_argument("--appendonly", type=str, default=None)
    parser.add_argument("--appenddirname", type=str, default=None)
    parser.add_argument("--appendfilename", type=str, default=None)
    parser.add_argument("--appendfsync", type=str, default=None)
    args = parser.parse_args()
    
    print(f"Running Redis Server on port {args.port}")
    replication = {}
    master = None
    
    if args.replicaof:
        role = "slave"
        master, leftover = connect_to_master(args.replicaof,args.port,replication)
    else:
        role = "master"
        replication["master_replid"] = "8371b4fb1155b71f4a04d3e1bc3e18c4a990aeeb"
        replication["master_repl_offset"] = 0
    
    config = {}
    config["dir"] = os.path.abspath(args.dir or ".")  # Redis reports dir as an absolute path; default is cwd
    config["dbfilename"] = args.dbfilename if args.dbfilename else "dump.rdb"
    config["appendonly"] = args.appendonly if args.appendonly else "no"
    config["appenddirname"] = args.appenddirname if args.appenddirname else "appendonlydir"
    config["appendfilename"] = args.appendfilename if args.appendfilename else "appendonly.aof"
    config["appendfsync"] = args.appendfsync if args.appendfsync else "everysec"
        
    ctx = ServerContext(role=role,replication=replication,config=config)
    rdb_loader.load(ctx.config, ctx.store)  # restore keys from dir/dbfilename, if present
    load_commands(ctx)  # fills ctx.registry
    server = RedisServer(
        ("localhost", args.port),
        dispatcher=CommandDispatcher(ctx.registry, ctx.blocking),
        blocking=ctx.blocking,
        tickers=[ActiveExpirer(ctx.store)],
    )
    
    if master:
        server.attach_master(master,leftover, ctx.replication)
    server.serve_forever()


if __name__ == "__main__":
    main()
