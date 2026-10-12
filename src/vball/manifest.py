"""models/manifest.json: every weight file the code loads, with its checksum, where it comes from and where it was
measured.

    problems = check()          # {file: "missing" | "changed"} for the files listed in the manifest
    usable(path)                # the file exists and, when it is in models/ and listed, matches its checksum

Weights are not in git (models/ is ignored except for the manifest), so a checkout can hold a stale or partial copy;
this makes that visible instead of letting a stage run on the wrong file. `scripts/fetch_models.py` gets what can be
fetched and rewrites the checksums of the files present (`--write`).

Each entry: {"sha256", "bytes", "source": where it comes from, "measured_in": the docs/results file with its numbers}
and, when it can be fetched, "external": a path under external/ to copy from, or "ultralytics": true for weights the
ultralytics package downloads by name.
"""

import hashlib
import json
import shutil
from pathlib import Path

from .paths import EXTERNAL, MODELS

MANIFEST = MODELS / "manifest.json"
_hashes: dict[tuple[str, int, int], str] = {}  # (path, size, mtime) -> sha256, so a file is read once per version


def sha256(path: Path) -> str:
    st = path.stat()
    key = (str(path.resolve()), st.st_size, st.st_mtime_ns)
    if key not in _hashes:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        _hashes[key] = h.hexdigest()
    return _hashes[key]


def load(manifest: Path = MANIFEST) -> dict[str, dict]:
    """file name -> entry; empty when there is no manifest."""
    return json.loads(manifest.read_text()) if manifest.exists() else {}


def check(models: Path = MODELS, manifest: Path = MANIFEST) -> dict[str, str]:
    """Listed files that are missing from `models` or differ from their checksum."""
    out = {}
    for name, entry in load(manifest).items():
        path = models / name
        if not path.exists():
            out[name] = "missing"
        elif sha256(path) != entry["sha256"]:
            out[name] = "changed"
    return out


def usable(path: Path, models: Path = MODELS, manifest: Path = MANIFEST) -> bool:
    """The file exists and, when it lies in `models` and is listed, matches its checksum (other files, such as a
    test's fake weights, only need to exist)."""
    path = Path(path)
    if not path.exists():
        return False
    if path.resolve().parent != models.resolve():
        return True
    entry = load(manifest).get(path.name)
    return entry is None or sha256(path) == entry["sha256"]


def external_source(entry: dict) -> Path | None:
    """The upstream copy of a file kept under external/, if the entry names one."""
    return EXTERNAL / entry["external"] if entry.get("external") else None


def write(models: Path = MODELS, manifest: Path = MANIFEST) -> dict[str, dict]:
    """Rewrite checksums and sizes of the listed files that are present; metadata (source, measured_in) is kept."""
    entries = load(manifest)
    for name, entry in entries.items():
        path = models / name
        if path.exists():
            entry.update(sha256=sha256(path), bytes=path.stat().st_size)
    manifest.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n")
    return entries


def fetch(name: str, entry: dict, models: Path = MODELS) -> str:
    """Get one missing file if the manifest says how (a copy under external/, or an ultralytics download), check it
    against its checksum, and say what happened."""
    dest = models / name
    src = external_source(entry)
    if src is not None and src.exists():
        shutil.copy2(src, dest)
    elif entry.get("ultralytics"):
        _ultralytics_download(name, dest)
    else:
        return f"not fetchable: {entry['source']}"
    if sha256(dest) != entry["sha256"]:
        dest.unlink()
        return "fetched, but the checksum differs: removed"
    return "fetched"


def _ultralytics_download(name: str, dest: Path) -> None:  # pragma: no cover - needs the network and ultralytics
    """Ultralytics downloads its released weights by file name into the working directory."""
    import os
    import tempfile

    from ultralytics import YOLO

    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            YOLO(name)
            shutil.move(Path(tmp) / name, dest)
        finally:
            os.chdir(cwd)
