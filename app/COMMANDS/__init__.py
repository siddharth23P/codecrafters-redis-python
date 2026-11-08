import importlib
import pkgutil

from ..PROTOCOL.resp_types import CommandError


def check_arity(args, name, ok):
    """Raise the standard error when `ok` (an argument-count check) is False."""
    if not ok:
        raise CommandError(f"wrong number of arguments for '{name}' command")


def to_int(arg):
    try:
        return int(arg)
    except ValueError:
        raise CommandError("value is not an integer or out of range")


def register(name_or_fn=None):
    """Mark a method as a command. Use as @register (name = method name) or @register("name")."""
    def mark(fn, name=None):
        fn.command_name = (name or fn.__name__).lower()
        return fn
    if callable(name_or_fn):
        return mark(name_or_fn)
    return lambda fn: mark(fn, name_or_fn)


def registered_commands(obj):
    """{name: bound method} for every @register method on obj."""
    methods = (getattr(obj, attr) for attr in dir(obj) if not attr.startswith("__"))
    return {m.command_name: m for m in methods if hasattr(m, "command_name")}


def load(ctx):
    """Import every module in this package and register its commands in ctx.registry.

    A module provides one of:
      create(ctx) -> callable(args) -> reply   one command that needs shared state (e.g. ctx.store)
      create(ctx) -> {name: callable(args)}    a group of commands (e.g. registered_commands(obj))
      run(args) -> reply                       one stateless command
    `args` is a list of bytes (the command name is not included).
    For a single command, the module name, lowercase, is the command name.
    """
    for mod in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f".{mod.name}", __name__)
        if hasattr(module, "create"):
            command = module.create(ctx)
        elif hasattr(module, "run"):
            command = module.run
        else:
            raise TypeError(f"command module {mod.name!r} must define create(ctx) or run(args)")
        if isinstance(command, dict):
            ctx.registry.update(command)
        else:
            ctx.registry[mod.name.lower()] = command
    return ctx.registry
