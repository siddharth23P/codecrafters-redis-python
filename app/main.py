import argparse
from .COMMANDS import load as load_commands
from .SERVER.context import ServerContext
from .SERVER.dispatcher import CommandDispatcher
from .SERVER.expiry import ActiveExpirer
from .SERVER.server import RedisServer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=6379)
    args = parser.parse_args()
    
    print(f"Running Redis Server on port {args.port}")
    ctx = ServerContext()
    load_commands(ctx)  # fills ctx.registry
    server = RedisServer(
        ("localhost", args.port),
        dispatcher=CommandDispatcher(ctx.registry),
        blocking=ctx.blocking,
        tickers=[ActiveExpirer(ctx.store)],
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
