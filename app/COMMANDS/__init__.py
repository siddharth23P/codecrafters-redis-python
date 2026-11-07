import importlib
import pkgutil


def load(ctx):
    """Import every module in this package and register its command in ctx.registry.

    A module provides either:
      create(ctx) -> callable(args) -> reply   when it needs shared state (e.g. ctx.store)
      run(args) -> reply                       when it is stateless
    `args` is a list of bytes (the command name is not included).
    The module name, lowercase, is the command name.
    """
    for mod in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f".{mod.name}", __name__)
        if hasattr(module, "create"):
            command = module.create(ctx)
        elif hasattr(module, "run"):
            command = module.run
        else:
            raise TypeError(f"command module {mod.name!r} must define create(ctx) or run(args)")
        ctx.registry[mod.name.lower()] = command
    return ctx.registry
