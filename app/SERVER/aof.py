import os
from ..PROTOCOL.parser import Incomplete, _parse_at
from ..PROTOCOL.resp_types import CommandError


def init(config):
    """Create the AOF directory, incremental file, and manifest when appendonly is yes.

    Layout (Redis 7 multi-part AOF):
        <dir>/<appenddirname>/<appendfilename>.1.incr.aof
        <dir>/<appenddirname>/<appendfilename>.manifest
    Existing files are left untouched.
    """
    if config.get("appendonly", "no").lower() != "yes":
        return None

    aof_dir = os.path.join(config["dir"], config["appenddirname"])
    os.makedirs(aof_dir, exist_ok=True)

    base = config["appendfilename"]
    incr_name = f"{base}.1.incr.aof"
    incr_path = os.path.join(aof_dir, incr_name)
    manifest_path = os.path.join(aof_dir, f"{base}.manifest")

    if not os.path.exists(incr_path):
        open(incr_path, "wb").close()

    if not os.path.exists(manifest_path):
        with open(manifest_path, "w") as f:
            f.write(f"file {incr_name} seq 1 type i\n")

    return incr_path


def replay(config, registry):
    """Re-run every command in the manifest's incremental AOF files to rebuild the store.

    Commands go straight to the registry, so they are not re-appended or propagated.
    A truncated tail (crash mid-write) is ignored. Returns the number of commands replayed.
    """
    if config.get("appendonly", "no").lower() != "yes":
        return 0

    aof_dir = os.path.join(config["dir"], config["appenddirname"])
    manifest_path = os.path.join(aof_dir, f"{config['appendfilename']}.manifest")
    if not os.path.exists(manifest_path):
        return 0

    count = 0
    for name in _incr_files(manifest_path):
        path = os.path.join(aof_dir, name)
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            buf = f.read()
        pos = 0
        while pos < len(buf):
            try:
                request, pos = _parse_at(buf, pos)
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


def _incr_files(manifest_path):
    """Incremental file names from the manifest, ordered by seq."""
    entries = []
    with open(manifest_path) as f:
        for line in f:
            parts = line.split()
            fields = dict(zip(parts[::2], parts[1::2]))
            if fields.get("type") == "i" and "file" in fields:
                entries.append((int(fields.get("seq", 0)), fields["file"]))
    return [name for _, name in sorted(entries)]
