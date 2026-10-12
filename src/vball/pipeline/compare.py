"""Compare two folders of pipeline results (change adopt-engineering-practices, design D2).

A refactor must not change what the stages produce. Run the pipeline on the same videos before and after, then

  .venv/bin/python scripts/compare_stage_outputs.py outputs/golden/before outputs/golden/after

Each video folder is compared file by file: JSON by value (numbers within --tol), CSV / CSV.GZ cell by cell, NPZ
array by array, anything else byte for byte. Exit status 1 when anything differs or a file exists on one side only.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def json_diff(a, b, tol: float, path: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out = [f"{path}/{k}: only in {'first' if k in a else 'second'}" for k in sorted(set(a) ^ set(b))]
        for k in sorted(set(a) & set(b)):
            out += json_diff(a[k], b[k], tol, f"{path}/{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in json_diff(x, y, tol, f"{path}[{i}]")]
    numbers = (int, float)
    if isinstance(a, numbers) and isinstance(b, numbers) and not isinstance(a, bool) and not isinstance(b, bool):
        same = math.isclose(a, b, rel_tol=0, abs_tol=tol) or (math.isnan(a) and math.isnan(b))
        return [] if same else [f"{path}: {a!r} != {b!r}"]
    return [] if a == b and type(a) is type(b) else [f"{path}: {a!r} != {b!r}"]


def table_diff(a: pd.DataFrame, b: pd.DataFrame, tol: float) -> list[str]:
    if list(a.columns) != list(b.columns):
        return [f"columns {list(a.columns)} != {list(b.columns)}"]
    if len(a) != len(b):
        return [f"rows {len(a)} != {len(b)}"]
    out = []
    for c in a.columns:
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            bad = ~np.isclose(x, y, rtol=0, atol=tol, equal_nan=True)
        else:
            bad = ~((x == y) | (x.isna() & y.isna())).to_numpy()
        if bad.any():
            out.append(f"column {c}: {int(bad.sum())} cells differ (first at row {int(np.argmax(bad))})")
    return out


def file_diff(a: Path, b: Path, tol: float) -> list[str]:
    name = a.name
    if name.endswith(".json"):
        return json_diff(json.loads(a.read_text()), json.loads(b.read_text()), tol)
    if name.endswith((".csv", ".csv.gz")):
        return table_diff(pd.read_csv(a), pd.read_csv(b), tol)
    if name.endswith(".npz"):
        x, y = np.load(a), np.load(b)
        if sorted(x.files) != sorted(y.files):
            return [f"arrays {sorted(x.files)} != {sorted(y.files)}"]
        return [f"array {k} differs" for k in x.files if x[k].shape != y[k].shape or not np.allclose(x[k], y[k], atol=tol, equal_nan=True)]
    return [] if a.read_bytes() == b.read_bytes() else ["bytes differ"]


def compare(first: Path, second: Path, tol: float = 1e-9) -> dict[str, list[str]]:
    """{relative file: [differences]} for every file that differs or exists on one side only."""
    fa = {p.relative_to(first) for p in first.rglob("*") if p.is_file()}
    fb = {p.relative_to(second) for p in second.rglob("*") if p.is_file()}
    out = {str(p): ["only in first"] for p in fa - fb} | {str(p): ["only in second"] for p in fb - fa}
    for p in sorted(fa & fb):
        d = file_diff(first / p, second / p, tol)
        if d:
            out[str(p)] = d
    return out
