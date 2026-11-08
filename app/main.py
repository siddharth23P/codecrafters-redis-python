from .COMMANDS import load as load_commands
from .SERVER.context import ServerContext
from .SERVER.dispatcher import CommandDispatcher
from .SERVER.expiry import ActiveExpirer
from .SERVER.server import RedisServer


def main():
    print("Running Redis Server")
    ctx = ServerContext()
    load_commands(ctx)  # fills ctx.registry
    server = RedisServer(
        ("localhost", 6379),
        dispatcher=CommandDispatcher(ctx.registry),
        blocking=ctx.blocking,
        tickers=[ActiveExpirer(ctx.store)],
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
