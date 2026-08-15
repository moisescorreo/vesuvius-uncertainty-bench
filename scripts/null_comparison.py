#!/usr/bin/env python3
"""Reproduce the headline validation finding: the permutation null is not safe.

On text-free substrate the two judges are run against both nulls. The
permutation null routinely clears any sane claim threshold; the block-mosaic
null does not. Every "positive" a line judge reports against a permutation null
above 100 keV should be assumed to be substrate until proven otherwise.

    python scripts/null_comparison.py                       # both substrates
    python scripts/null_comparison.py --substrate PHerc1203_113keV
    python scripts/null_comparison.py --windows 8 --n-mos 199   # full strength

Runtime with the defaults (n=99 draws, 4 windows, 2 judges, 2 substrates) is a
few minutes on a laptop core. The published campaign used n=199 and 55 windows
per substrate; `validation/data/*.json` holds those results and
`--report` prints them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation import incoherence, ruler  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBSTRATE_DIR = os.path.join(HERE, "validation", "data", "substrate")

# Windows are ~29 mm on a side: the largest square that fits in the material,
# and the size at which the published power curves were measured.
WINDOW_MM = 29.0
COVERAGE_MIN = 0.9


def load_substrate(name):
    d = np.load(os.path.join(SUBSTRATE_DIR, name + ".npz"))
    return (d["mean_z"], d["sd_z"], d["coverage"] >= COVERAGE_MIN,
            float(d["mm_per_cell"]))


def window_pool(valid, side):
    """All top-left corners whose window is >= 99 % covered (summed-area table)."""
    v = valid.astype(np.int32)
    ii = np.pad(np.cumsum(np.cumsum(v, 0), 1), ((1, 0), (1, 0)))
    ys = np.arange(0, v.shape[0] - side + 1)
    xs = np.arange(0, v.shape[1] - side + 1)
    if ys.size == 0 or xs.size == 0:
        return np.zeros((0, 2), int)
    S = (ii[np.ix_(ys + side, xs + side)] - ii[np.ix_(ys, xs + side)]
         - ii[np.ix_(ys + side, xs)] + ii[np.ix_(ys, xs)])
    pos = np.argwhere(S / float(side * side) >= 0.99)
    return np.stack([ys[pos[:, 0]], xs[pos[:, 1]]], 1)


def disperse(pos, n, seed=19):
    """Farthest-point selection: the least-overlapping windows the material allows.

    It does NOT make them independent -- on PHerc1203 only ONE 29 mm window is
    fully disjoint in the entire scroll. Overlap is reported, never hidden.
    """
    rng = np.random.default_rng(seed)
    P = pos.astype(np.float64)
    idx = [int(rng.integers(len(P)))]
    d = np.linalg.norm(P - P[idx[0]], axis=1)
    while len(idx) < min(n, len(P)):
        k = int(np.argmax(d))
        idx.append(k)
        d = np.minimum(d, np.linalg.norm(P - P[k], axis=1))
    return pos[np.array(idx)]


def run(name, n_windows, n_perm, n_mos, seed):
    mean_z, sd_z, valid, mm = load_substrate(name)
    side = int(round(WINDOW_MM / mm))
    pool = window_pool(valid, side)
    if len(pool) == 0:
        print(f"  {name}: no {WINDOW_MM} mm window fits; skipping")
        return []
    picks = disperse(pool, n_windows, seed=19)
    print(f"  {name}: cell {mm:.6f} mm, window {side} cells = {side*mm:.2f} mm, "
          f"pool {len(pool)}, using {len(picks)}")

    rows = []
    for i, (y, x) in enumerate(picks):
        field = (mean_z if i % 2 == 0 else sd_z)[y:y + side, x:x + side].copy()
        m = valid[y:y + side, x:x + side].copy()
        stat_name = "mean_z" if i % 2 == 0 else "sd_z"
        for judge, mod, band, minper in (
                ("ruler", ruler, (2.4, 6.5), 3.5),
                ("incoherence", incoherence, (2.4, 7.0), 3.0)):
            r = mod.evaluate(field, m, mm_per_cell=mm, band_mm=band,
                             min_periods=minper, n_perm=n_perm, n_mos=n_mos,
                             seed=seed + i * 17 + (0 if judge == "ruler" else 7))
            rows.append({"substrate": name, "window": i, "field": stat_name,
                         "judge": judge, "y": int(y), "x": int(x),
                         "z_perm": r["z_perm"], "p_perm": r["p_perm"],
                         "z_mos": r["z_mos"], "p_mos": r["p_mos"],
                         "band_complete": r["band_complete"],
                         "period_mm": r["period_mm"]})
            print(f"    w{i:02d} {stat_name:<7} {judge:<12} "
                  f"z_perm {r['z_perm']:>8.3f}   z_mos {r['z_mos']:>7.3f}"
                  f"   band_complete={r['band_complete']}")
    return rows


def summarise(rows, z_claim=4.0):
    print("\n" + "=" * 74)
    print("SUMMARY -- these windows contain NO text. Every z is a false positive.")
    print("=" * 74)
    print(f"{'substrate':<20} {'judge':<13} {'n':>3} {'max z_perm':>11} "
          f"{'max z_mos':>10} {'FPR perm':>9} {'FPR mos':>8}")
    print("-" * 74)
    bad = 0
    for sub in sorted({r["substrate"] for r in rows}):
        for judge in ("ruler", "incoherence"):
            g = [r for r in rows if r["substrate"] == sub and r["judge"] == judge]
            if not g:
                continue
            zp = np.array([r["z_perm"] for r in g])
            zm = np.array([r["z_mos"] for r in g])
            fp, fm = float((zp >= z_claim).mean()), float((zm >= z_claim).mean())
            bad += int((zp >= z_claim).sum())
            print(f"{sub:<20} {judge:<13} {len(g):>3} {zp.max():>11.3f} "
                  f"{zm.max():>10.3f} {fp:>9.1%} {fm:>8.1%}")
    print("-" * 74)
    print(f"windows with NO text that the permutation null would call a claim "
          f"at z >= {z_claim}: {bad}")
    print("\nThe mosaic null is what must decide. The permutation null is a\n"
          "diagnostic: it tells you how much substrate structure is present.")


def print_report():
    """Print the published campaign numbers (larger n than the live demo)."""
    print("\nPUBLISHED CAMPAIGN (validation/data/*.json)")
    print("=" * 74)
    for f, label in (("power_1203_113kev.json", "PHerc1203 @113 keV, 29.21 x 29.51 mm, n=55"),
                     ("power_0009b_116kev.json", "PHerc0009B @116 keV, 29.03 mm square, n=48/24")):
        p = os.path.join(HERE, "validation", "data", f)
        if os.path.exists(p):
            print(f"  {label}\n    -> {p}")
    print("""
  PHerc1203  @113 keV : max z_perm 12.24, max z_mos 2.50
                        30.9 % of text-free windows clear Z=4 by permutation
  PHerc0009B @116 keV : max z_perm 16.84, max z_mos 3.52
  canvas nulls        : mosaicked substrate patches FABRICATE line rhythm,
                        z_mos up to 7.61 with p at the 1/200 floor -- never
                        calibrate a line judge on synthetic canvases
  false positive blocked: on the sealed PHerc1203 reader map the permutation
                        statistic gave z_perm 6.14, p at the floor (a clean
                        "positive"); the pre-registered mosaic gave 0.502,
                        p 0.295.""")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--substrate", default=None,
                    help="PHerc1203_113keV or PHerc0009B_116keV (default: both)")
    ap.add_argument("--windows", type=int, default=4)
    ap.add_argument("--n-perm", type=int, default=99)
    ap.add_argument("--n-mos", type=int, default=99)
    ap.add_argument("--seed", type=int, default=1903)
    ap.add_argument("--z-claim", type=float, default=4.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", action="store_true",
                    help="only print the published campaign numbers")
    a = ap.parse_args()

    if a.report:
        print_report()
        return 0

    names = ([a.substrate] if a.substrate
             else sorted(f[:-4] for f in os.listdir(SUBSTRATE_DIR)
                         if f.endswith(".npz")))
    print(f"seed={a.seed}  n_perm={a.n_perm}  n_mos={a.n_mos}  "
          f"p floor = 1/{a.n_mos + 1} = {1.0 / (a.n_mos + 1):.4f}")
    if 1.0 / (a.n_mos + 1) > 0.01:
        print("  NOTE: with this n_mos the empirical p cannot reach 0.01. "
              "Use --n-mos 199 for claim-grade runs.")
    print()

    rows = []
    for n in names:
        rows += run(n, a.windows, a.n_perm, a.n_mos, a.seed)
    summarise(rows, a.z_claim)
    print_report()

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as fh:
            json.dump({"config": vars(a), "rows": rows}, fh, indent=1)
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
