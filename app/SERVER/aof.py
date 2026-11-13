import os


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
