"""Compare two folders of pipeline results (change adopt-engineering-practices, design D2).

A refactor must not change what the stages produce. Run the pipeline on the same videos before and after, then

  .venv/bin/python scripts/compare_stage_outputs.py outputs/golden/before outputs/golden/after

Each video folder is compared file by file: JSON by value (numbers within --tol), CSV / CSV.GZ cell by cell, NPZ
array by array, anything else byte for byte. Exit status 1 when anything differs or a file exists on one side only.
"""

import argparse
import sys
from pathlib import Path

from vball.pipeline.compare import compare


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("first", type=Path)
    ap.add_argument("second", type=Path)
    ap.add_argument("--tol", type=float, default=1e-9, help="absolute tolerance for numbers")
    args = ap.parse_args()
    diffs = compare(args.first, args.second, args.tol)
    for f, ds in sorted(diffs.items()):
        print(f"{f}:")
        for d in ds[:10]:
            print(f"  {d}")
        if len(ds) > 10:
            print(f"  ... {len(ds) - 10} more")
    n = sum(1 for p in args.first.rglob("*") if p.is_file())
    print("identical" if not diffs else f"{len(diffs)} of {n} files differ")
    sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
