#!/usr/bin/env python3
"""Build, verify and describe the derived label sets.

    python scripts/build_labels.py --report            # quality table, no network
    python scripts/build_labels.py --verify            # shapes + checksums
    python scripts/build_labels.py --rebuild 20250511003658 --set gold116

The transfer is a 2-D resize and nothing more, because the Challenge already
solved the hard part upstream: a segment is traced once and the SAME mesh is
published transformed onto both the fine and the coarse volume, so both surface
volumes share the (u, v) parameterisation.

    fine ink TIF  --INTER_AREA resize to the EXACT coarse shape-->  label

Resizing to the exact target shape rather than by a scalar factor matters: each
grid is padded to a chunk multiple, so the measured ratio lands at 4.19-4.22
against a theoretical 4.2266. Scaling by the theoretical factor leaves a
systematic sub-pixel drift across the segment.

INTER_AREA, not bilinear: this is a 4.23x reduction, where bilinear aliases.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETS = {
    "gold116": {"sample": "PHerc0343P", "dir": "labels/gold116", "key": "label116",
                "um": 8.640, "keV": 116, "curation": "benchmark/data/curation_gold116.json"},
    "gold113": {"sample": "PHerc0500P2", "dir": "labels/gold113", "key": "label113",
                "um": 9.362, "keV": 113, "curation": "benchmark/data/curation_gold113.json"},
}
HOLDOUT = "20250511003658"


def load_json(rel):
    p = os.path.join(HERE, rel)
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        return json.load(fh)


def cmd_report():
    inv = load_json("benchmark/data/inventory.json")
    print("DERIVED LABEL SETS")
    print("=" * 78)
    for name, s in SETS.items():
        d = os.path.join(HERE, s["dir"])
        files = sorted(f for f in os.listdir(d) if f.endswith(".npz"))
        tot = sum(os.path.getsize(os.path.join(d, f)) for f in files)
        print(f"\n{name}: {s['sample']} at {s['um']} um / {s['keV']} keV")
        print(f"  {len(files)} segments, {tot/1e6:.1f} MB, key '{s['key']}'")
        print(f"  {'segment':<18} {'shape':>16} {'mean':>7} {'>128':>8}  note")
        print("  " + "-" * 66)
        for f in files:
            seg = f[:-4]
            a = np.load(os.path.join(d, f))[s["key"]]
            frac = float((a > 128).mean())
            note = "HOLDOUT (clean text)" if seg == HOLDOUT else ""
            print(f"  {seg:<18} {str(a.shape):>16} {a.mean():>7.2f} "
                  f"{frac:>8.4f}  {note}")

    print("\n" + "=" * 78)
    print("QUALITY CAVEATS (measured, see benchmark/README.md)")
    print("=" * 78)
    print("""
  gold113 is NOT equal in quality to gold116:
    ink in components > 3 mm^2 : median 0.161 (max 0.442)  vs  0.0 (max 0.155)
    largest component          : 14.7 mm^2                 vs  3.2 mm^2
    stroke width               : 486 um                    vs  354 um
    clean-text segments        : 2 of 10                   vs  1 of 8
  A letter fits in ~2 mm^2. Components of 14.7 mm^2 are blotches, not letters.

  gold113 DROPPED INFERENCE TILES:
    25-104 square holes of ~47x47 px (440 um) per segment, 0.2-2.5 % of the
    valid domain, INSIDE valid material. They are lost tiles from the
    generator's own tile256/stride128 pass -- missing data, not blank papyrus.
    Training them as negatives is a hard lie. The curation marks them IGNORE.

  THE LABEL IS NOT BINARY:
    ink fraction moves by more than 2x between thresholds 64 and 192. Pick one
    and you are reporting your threshold choice. Use the three-way masks.""")
    if inv:
        print(f"\n  inventory JSON: benchmark/data/inventory.json")
    return 0


def cmd_verify():
    ok = True
    print("shape and dtype")
    print("-" * 60)
    for name, s in SETS.items():
        d = os.path.join(HERE, s["dir"])
        for f in sorted(os.listdir(d)):
            if not f.endswith(".npz"):
                continue
            z = np.load(os.path.join(d, f))
            if s["key"] not in z.files:
                print(f"  FAIL {name}/{f}: missing key '{s['key']}'")
                ok = False
                continue
            a = z[s["key"]]
            good = a.dtype == np.uint8 and a.ndim == 2 and a.size > 0
            ok &= good
            print(f"  {'ok ' if good else 'FAIL'} {name}/{f[:-4]:<18} "
                  f"{str(a.shape):>16} {a.dtype}")
    print("\nchecksums")
    print("-" * 60)
    import subprocess
    r = subprocess.run([sys.executable,
                        os.path.join(HERE, "scripts", "verify_checksums.py")],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    ok &= (r.returncode == 0)

    tr = load_json("benchmark/data/transfer_gold113.json")
    if tr:
        print("\nduality verification (shipped, from the build run)")
        print("-" * 60)
        print("  V1 measured shape ratio vs theoretical 4.2266 : 4.19-4.22 "
              "(max deviation 0.83 %)")
        print("  V2 ink TIF lands exactly on the fine grid     : true, 10/10")
        print("  V3 silhouette IoU aligned vs displaced        : "
              "0.928-0.949 vs 0.881-0.893")
        print("     mean-z correlation aligned vs displaced    : "
              "0.63-0.66 vs 0.13-0.20")
        print("  V4 output lands exactly on the 113 keV grid   : true, 10/10")
        print("  full record: benchmark/data/transfer_gold113.json")
    print("\n" + ("ALL CHECKS PASS" if ok else "SOME CHECKS FAILED"))
    return 0 if ok else 1


def cmd_rebuild(seg, setname):
    """Re-derive one label from the public bucket."""
    try:
        import cv2
    except ImportError:
        print("rebuild needs opencv (INTER_AREA); "
              "pip install opencv-python-headless", file=sys.stderr)
        return 2
    import tifffile
    from audit.provenance import load_catalogue
    from rendering.render_tifxyz import S3, http_get

    s = SETS[setname]
    cat = load_catalogue(os.path.join(HERE, "audit", "data",
                                      "catalogue_snapshot.json"))
    sample = cat["samples"][s["sample"]]
    if seg not in sample["segments"]:
        print(f"segment {seg} not in {s['sample']}", file=sys.stderr)
        return 2
    entry = sample["segments"][seg]

    ink_path = coarse = None
    for e in entry["data"]:
        if e.get("type") == "ink-detection":
            ink_path = e["origins"][0]["path"]
        if e.get("type") == "layers-zarr":
            p = e["origins"][0]["path"]
            if f"{s['um']:.3f}um" in p or f"{s['um']}um" in p:
                coarse = p
    if not ink_path or not coarse:
        print(f"missing ink ({bool(ink_path)}) or coarse zarr ({bool(coarse)})",
              file=sys.stderr)
        return 2

    print(f"ink   : {ink_path}")
    print(f"coarse: {coarse}")
    za = json.loads(http_get(S3 + coarse.rstrip('/') + "/0/.zarray"))
    target = (za["shape"][1], za["shape"][2])            # (H, W) on the coarse grid
    print(f"target shape: {target}")

    import io
    fine = tifffile.imread(io.BytesIO(http_get(S3 + ink_path)))
    print(f"fine label  : {fine.shape} {fine.dtype}  "
          f"ratio {fine.shape[0]/target[0]:.4f} x {fine.shape[1]/target[1]:.4f}")
    out = cv2.resize(fine.astype(np.uint8), (target[1], target[0]),
                     interpolation=cv2.INTER_AREA)

    have = os.path.join(HERE, s["dir"], f"{seg}.npz")
    if os.path.exists(have):
        ref = np.load(have)[s["key"]]
        same = ref.shape == out.shape
        print(f"\nvs shipped: shape {'MATCH' if same else 'DIFFER'}  "
              f"{ref.shape} vs {out.shape}")
        if same:
            d = np.abs(ref.astype(int) - out.astype(int))
            print(f"            identical px {float((d == 0).mean()):.6f}, "
                  f"max |delta| {int(d.max())}, mean |delta| {d.mean():.4f}")
    dst = os.path.join(HERE, "work", f"{seg}_rebuilt.npz")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    np.savez_compressed(dst, **{s["key"]: out})
    print(f"\nwrote {dst}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--rebuild", metavar="SEGMENT", default=None)
    ap.add_argument("--set", choices=list(SETS), default="gold116")
    a = ap.parse_args()
    if a.rebuild:
        return cmd_rebuild(a.rebuild, a.set)
    if a.verify:
        return cmd_verify()
    return cmd_report()


if __name__ == "__main__":
    raise SystemExit(main())
