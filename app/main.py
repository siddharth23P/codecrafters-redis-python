from .COMMANDS import load as load_commands
from .context import ServerContext
from .dispatcher import CommandDispatcher
from .encoder import RespEncoder
from .expiry import ActiveExpirer
from .parser import RespParser
from .server import RedisServer


def build_server():
    """Composition root: the only place concrete objects are created and wired together."""
    ctx = ServerContext()
    load_commands(ctx)  # fills ctx.registry
    return RedisServer(
        ("localhost", 6379),
        parser=RespParser(),
        dispatcher=CommandDispatcher(ctx.registry),
        encoder=RespEncoder(),
        tickers=[ActiveExpirer(ctx.store)],
    )


def main():
    print("Running Redis Server")
    build_server().serve_forever()


if __name__ == "__main__":
    main()
