import argparse
from .COMMANDS import load as load_commands
from .SERVER.context import ServerContext
from .SERVER.dispatcher import CommandDispatcher
from .SERVER.expiry import ActiveExpirer
from .SERVER.server import RedisServer
from .SERVER.replication import connect_to_master

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--replicaof", type=str, default=None)
    parser.add_argument("--dir", type=str, default=None)
    parser.add_argument("--dbfilename", type=str, default=None)
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
    config["dir"] = args.dir if args.dir else "."
    config["dbfilename"] = args.dbfilename if args.dbfilename else "dump.rdb"
        
    ctx = ServerContext(role=role,replication=replication,config=config)
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
