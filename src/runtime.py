"""SUMO discovery, experiment identity and crash-safe JSON persistence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import xml.etree.ElementTree as ET

SCHEMA_VERSION = 2
FEATURE_SCHEMA = "movement-queue-vehicle-wait-competition-active-major-clock-v2"
FEATURE_DIM = 7
REWARD_SCHEMA = "discounted-normalized-queue-integral-v2"
CONNECTION_LOCK = threading.Lock()

if os.environ.get("SUMO_HOME"):
    sys.path.append(str(Path(os.environ["SUMO_HOME"]) / "tools"))


def sumo_binary(name="sumo"):
    suffix = ".exe" if os.name == "nt" else ""
    if os.environ.get("SUMO_HOME"):
        candidate = Path(os.environ["SUMO_HOME"]) / "bin" / (name + suffix)
        if candidate.is_file():
            return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f"{name} bulunamadi; SUMO_HOME veya PATH ayarlayin")


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, allow_nan=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def scenario_identity(config):
    config = Path(config).resolve()
    root = ET.parse(config).getroot()
    files = [config]
    for key in ("net-file", "route-files", "additional-files"):
        entry = root.find(f"input/{key}")
        if entry is not None:
            files.extend(config.parent / name.strip() for name in entry.attrib["value"].split(","))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return {
        "scenario_sha256": digest.hexdigest(),
        "feature_schema": FEATURE_SCHEMA,
        "reward_schema": REWARD_SCHEMA,
    }
