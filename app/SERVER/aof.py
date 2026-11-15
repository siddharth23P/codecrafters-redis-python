"""Append-only file: log write commands, and replay them at startup.

Layout (Redis 7 multi-part AOF):
    <dir>/<appenddirname>/<appendfilename>.1.incr.aof
    <dir>/<appenddirname>/<appendfilename>.manifest
"""
import os

from ..PROTOCOL.encoder import encode
from ..PROTOCOL.parser import Incomplete, parse
from ..PROTOCOL.resp_types import CommandError


def enabled(config):
    return config.get("appendonly", "no").lower() == "yes"


def _aof_dir(config):
    return os.path.join(config.get("dir", "."), config.get("appenddirname", "appendonlydir"))


def _base(config):
    return config.get("appendfilename", "appendonly.aof")


def incr_path(config):
    return os.path.join(_aof_dir(config), f"{_base(config)}.1.incr.aof")


def manifest_path(config):
    return os.path.join(_aof_dir(config), f"{_base(config)}.manifest")


def init(config):
    """Create the AOF directory, incremental file and manifest when appendonly is yes.

    Existing files are left untouched. Returns the incremental file's path, or None if AOF is off.
    """
    if not enabled(config):
        return None
    os.makedirs(_aof_dir(config), exist_ok=True)
    path = incr_path(config)
    if not os.path.exists(path):
        open(path, "wb").close()
    if not os.path.exists(manifest_path(config)):
        with open(manifest_path(config), "w") as f:
            f.write(f"file {os.path.basename(path)} seq 1 type i\n")
    return path


class Appender:
    """Appends each write command to the incremental AOF file. Does nothing when appendonly is no."""

    def __init__(self, config):
        self._path = incr_path(config) if enabled(config) else None
        self._fsync_always = config.get("appendfsync", "everysec").lower() == "always"

    def append(self, request):
        if self._path is None:
            return
        with open(self._path, "ab") as f:
            f.write(encode(request))
            f.flush()
            if self._fsync_always:
                os.fsync(f.fileno())


def replay(config, registry):
    """Re-run every command in the manifest's incremental AOF files to rebuild the store.

    Commands go straight to the registry, so they are not re-appended or propagated.
    A truncated tail (crash mid-write) is ignored. Returns the number of commands replayed.
    """
    if not enabled(config) or not os.path.exists(manifest_path(config)):
        return 0
    count = 0
    for name in _incr_files(manifest_path(config)):
        path = os.path.join(_aof_dir(config), name)
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            buf = f.read()
        pos = 0
        while pos < len(buf):
            try:
                request, pos = parse(buf, pos)
            except Incomplete:
                break  # partial last command
            if not isinstance(request, list) or not request:
                continue
            command = registry.get(request[0].decode(errors="replace").lower())
            if command is None:
                continue
            try:
                command(request[1:])
            except CommandError:
                pass
            count += 1
    return count


def _incr_files(path):
    """Incremental file names from the manifest, ordered by seq."""
    entries = []
    with open(path) as f:
        for line in f:
            parts = line.split()
            fields = dict(zip(parts[::2], parts[1::2]))
            if fields.get("type") == "i" and "file" in fields:
                entries.append((int(fields.get("seq", 0)), fields["file"]))
    return [name for _, name in sorted(entries)]
