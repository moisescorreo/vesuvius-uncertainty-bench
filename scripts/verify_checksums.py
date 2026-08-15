#!/usr/bin/env python3
"""Verify every shipped artifact against its recorded SHA-256.

    python scripts/verify_checksums.py            # check
    python scripts/verify_checksums.py --update   # regenerate the manifests

Two manifests:
  labels/manifest.sha256   the 18 derived label arrays
  docs/artifacts.sha256    shipped JSON results and substrate cell grids

Exit code is 0 only if everything matches.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFESTS = {
    os.path.join(HERE, "labels", "manifest.sha256"): os.path.join(HERE, "labels"),
    os.path.join(HERE, "docs", "artifacts.sha256"): HERE,
}
PATTERNS = {
    os.path.join(HERE, "labels", "manifest.sha256"): ["gold116", "gold113"],
    os.path.join(HERE, "docs", "artifacts.sha256"): [
        "validation/data/substrate", "validation/data", "benchmark/data",
        "audit/data", "rendering/recipes"],
}


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def collect(root, subdirs):
    out = []
    for sd in subdirs:
        d = os.path.join(root, sd)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if os.path.isfile(p) and name.split(".")[-1] in ("npz", "json"):
                out.append(os.path.relpath(p, root))
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true")
    a = ap.parse_args()

    rc = 0
    for manifest, root in MANIFESTS.items():
        rel = os.path.relpath(manifest, HERE)
        if a.update:
            files = collect(root, PATTERNS[manifest])
            with open(manifest, "w") as fh:
                for f in files:
                    fh.write(f"{sha256(os.path.join(root, f))}  {f}\n")
            print(f"{rel}: wrote {len(files)} entries")
            continue

        if not os.path.exists(manifest):
            print(f"{rel}: MISSING", file=sys.stderr)
            rc = 1
            continue
        ok = bad = missing = 0
        with open(manifest) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                want, _, name = line.partition("  ")
                p = os.path.join(root, name.strip())
                if not os.path.exists(p):
                    print(f"  MISSING  {name}")
                    missing += 1
                elif sha256(p) == want:
                    ok += 1
                else:
                    print(f"  MISMATCH {name}")
                    bad += 1
        status = "OK" if (bad == 0 and missing == 0) else "FAILED"
        print(f"{rel}: {ok} ok, {bad} mismatched, {missing} missing  [{status}]")
        if bad or missing:
            rc = 1

    if not a.update:
        print("\nALL ARTIFACTS VERIFIED" if rc == 0 else "\nVERIFICATION FAILED")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
