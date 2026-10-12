"""Check the model weights against models/manifest.json and fetch what can be fetched.

  .venv/bin/python scripts/fetch_models.py            # status of every listed file; fetch the missing ones
  .venv/bin/python scripts/fetch_models.py --write    # after training a new version: record the files' checksums

Files copied from external/ (VballNet) or downloaded by ultralytics (COCO YOLO) are fetched; trained weights say
where they come from (a notebook or a script) and have to be trained or copied by hand.
"""

import argparse

from vball import manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="rewrite the checksums of the files present")
    args = ap.parse_args()
    if args.write:
        entries = manifest.write()
        print(f"{manifest.MANIFEST}: {len(entries)} files")
        return
    problems = manifest.check()
    for name, entry in sorted(manifest.load().items()):
        state = problems.get(name, "ok")
        if state == "missing":
            state = manifest.fetch(name, entry)
        print(f"{name:32s} {state}")


if __name__ == "__main__":
    main()
