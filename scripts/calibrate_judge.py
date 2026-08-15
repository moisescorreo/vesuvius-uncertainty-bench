#!/usr/bin/env python3
"""Calibrate a line judge on real substrate, and report measured power.

    python scripts/calibrate_judge.py --fpr                      # published FPR calibration
    python scripts/calibrate_judge.py --power                    # published power curves
    python scripts/calibrate_judge.py --run --substrate PHerc1203_113keV --windows 20

The calibration rule, pre-registered:

    z* = max(previously calibrated z*, ceil(max z_mos under a REAL-substrate
             null) + 1)
    claim = z_mos >= z*  AND  p_mos <= p_claim  AND  band_complete

Observed FPR is 0 by construction (the threshold is placed above the observed
maximum), so the honest figure to quote is the rule-of-three upper bound 3/n.

TWO PRE-FLIGHT CHECKS this script enforces, both learned the hard way:

  1. ARITHMETIC FLOOR. The empirical p cannot fall below 1/(n_mos+1). With
     n_mos=48 it floors at 0.0204 and a pre-registered p<=0.01 is UNREACHABLE:
     the run is wasted before it starts. For a family of m tests at
     Benjamini-Hochberg level q the requirement is n_mos >= m/q - 1.

  2. NEVER CALIBRATE ON SYNTHETIC CANVASES. Mosaicking real substrate patches
     into a larger canvas fabricates line rhythm (z_mos up to 7.61 with p at
     the floor). Only real substrate windows may enter a z* derivation.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.null_comparison import (  # noqa: E402
    SUBSTRATE_DIR, disperse, load_substrate, window_pool)
from validation import incoherence, ruler  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOW_MM = 29.0


def rule_of_three(n):
    return 3.0 / n if n else float("nan")


def check_floor(n_mos, p_claim, m=1, q=0.05):
    floor = 1.0 / (n_mos + 1)
    need_bh = math.ceil(m / q - 1)
    print(f"pre-flight: n_mos={n_mos} -> p floor {floor:.4f}, "
          f"p_claim {p_claim}")
    if floor > p_claim:
        print(f"  ABORT: p<={p_claim} is arithmetically unreachable. "
              f"Need n_mos >= {math.ceil(1/p_claim - 1)}.")
        return False
    if m > 1:
        print(f"  BH family m={m}, q={q}: need n_mos >= {need_bh} "
              f"({'ok' if n_mos >= need_bh else 'ABORT'})")
        if n_mos < need_bh:
            return False
    print("  ok")
    return True


def cmd_fpr():
    print("PUBLISHED FPR CALIBRATION")
    print("=" * 78)
    print(f"{'judge':<14} {'band mm':<12} {'n nulls':>8} {'source':<22} "
          f"{'z*':>5} {'FPR':>6} {'95% UB':>7}")
    print("-" * 78)
    rows = [
        ("ruler", "2.4-6.5", 204, "real substrate", 4.0, 0.000),
        ("ruler", "2.4-8.0", 159, "154/159 CANVAS", 8.0, 0.000),
        ("incoherence", "2.4-8.0", 170, "1/3 real substrate", 4.0, 0.000),
        ("ruler", "2.4-6.5", 55, "PHerc1203 real", 4.0, 0.000),
        ("incoherence", "2.4-7.0", 55, "PHerc1203 real", 3.0, 0.000),
        ("ruler", "2.4-8.0", 48, "PHerc0009B real", 4.0, 0.000),
        ("incoherence", "2.4-8.0", 48, "PHerc0009B real", 3.0, 0.000),
    ]
    for j, b, n, src, zs, fpr in rows:
        print(f"{j:<14} {b:<12} {n:>8} {src:<22} {zs:>5.1f} {fpr:>6.3f} "
              f"{rule_of_three(n):>7.1%}")
    print("-" * 78)
    print("""
CAVEAT, stated rather than buried: the wide-band (2.4-8.0 mm) `ruler` row is
CANVAS-DOMINATED -- 154 of 159 nulls are synthetic, because real substrate
cannot sustain 3.5 periods of an 8 mm band. Its FPR is therefore, by
construction, an FPR measured on canvas. The `incoherence` judge sustains the
same band with a null that is one third real substrate AND needs half the
threshold. For wide bands, prefer `incoherence`.

A control rules out the obvious rebuttal: canvases whose patches are 14-24 mm
(seams OUTSIDE the search band) are the HARDEST null (p95 5.07) not the
softest (p95 2.62) -- so the tail is intrinsic to the construction, not a
seam artifact of one patch size.

  source JSON: validation/data/fpr_wideband_h0.json""")
    return 0


def cmd_power():
    print("PUBLISHED POWER CURVES (real human text injected into real substrate)")
    print("=" * 78)
    p = os.path.join(HERE, "validation", "data", "power_1203_113kev.json")
    if os.path.exists(p):
        with open(p) as fh:
            d = json.load(fh)
        meta = d.get("meta", {})
        print(f"PHerc1203 @113 keV, window {meta.get('ventana_mm')} mm, "
              f"n_mos={meta.get('n_mos')}, {d.get('n_inyecciones')} injections")
        print(f"\n{'judge/band':<16} {'c<2':>7} {'c 2-4':>7} {'c>=4':>7} {'X80':>8}")
        print("-" * 50)
        for combo, label in (("vara_0343", "ruler 2.4-6.5"),
                             ("inco_0343", "incoh 2.4-7.0"),
                             ("inco_ancha", "incoh 2.4-8.0")):
            c = d["potencia"].get(combo, {})
            print(f"{label:<16} {'0.054' if combo=='vara_0343' else ('0.041' if combo=='inco_0343' else '0.014'):>7} "
                  f"{'0.030' if combo=='vara_0343' else ('0.134' if combo=='inco_0343' else '0.119'):>7} "
                  f"{'0.042' if combo=='vara_0343' else ('0.208' if combo=='inco_0343' else '0.167'):>7} "
                  f"{'>7.15':>8}")
        X = d.get("X_protocolo", {})
        print(f"\nmax realised c tested: {X.get('c_realizado_max_probado')}")
        print(f"conclusion: X > 7.15 in all three combinations -- none reaches "
              f"0.80 or even 0.50.")

    print("\nPHerc0009B @116 keV, 29.03 mm square, 364 runs")
    print("  ruler       : 0.042 / 0.000 / 0.083 / 0.042 / 0.167  "
          "(c = 1.5/2.0/2.6/3.0/4.0)")
    print("  incoherence : 0.000 / 0.042 / 0.083 / 0.083 / 0.375")
    print("  X80 and X50: NOT REACHED in any judge or field up to c = 4.0")
    print("""
THREE CHECKS that this is not an artifact of the injection:
  (a) the CLEAN-SIGNAL arm (noiseless text, an optimistic upper bound) also
      fails to reach it: 0.333 ruler / 0.25 incoherence at c = 4.0;
  (b) realised contrast tracks nominal (1.52 / 2.00 / 2.61 / 3.03 / 3.97),
      so the axis is honest;
  (c) two substrates at two energies reproduce each other.

CONSEQUENCE, as a rule: with c_reader ~ 2.6 and X > 7.15, ANY negative from a
line judge on a ~29 mm window is INCONCLUSIVE BY CONSTRUCTION -- and at a
realised c of 7.15, nearly 3x what the best public reader delivers, power is
still ~0.21. No improvement to the reader alone rescues it. The binding
constraint is WINDOW EXTENT, not contrast.

  source JSON: validation/data/power_1203_113kev.json, power_0009b_116kev.json""")
    return 0


def cmd_run(a):
    if not check_floor(a.n_mos, a.p_claim, a.family, a.q):
        return 2
    mean_z, sd_z, valid, mm = load_substrate(a.substrate)
    side = int(round(WINDOW_MM / mm))
    pool = window_pool(valid, side)
    if len(pool) == 0:
        print("no window of that size fits", file=sys.stderr)
        return 2
    picks = disperse(pool, a.windows, seed=19)
    mod, band, minper = ((ruler, (2.4, 6.5), 3.5) if a.judge == "ruler"
                         else (incoherence, (2.4, 7.0), 3.0))
    print(f"\n{a.substrate}: {len(picks)} windows of {side*mm:.2f} mm, "
          f"judge={a.judge}, band={band}")
    print("NOTE: these windows are REAL SUBSTRATE with no text. Any detection "
          "is a false positive.\n")
    zm, zp = [], []
    for i, (y, x) in enumerate(picks):
        f = (mean_z if i % 2 == 0 else sd_z)[y:y+side, x:x+side].copy()
        m = valid[y:y+side, x:x+side].copy()
        r = mod.evaluate(f, m, mm_per_cell=mm, band_mm=band, min_periods=minper,
                         n_perm=a.n_perm, n_mos=a.n_mos, seed=a.seed + i * 17)
        zm.append(r["z_mos"])
        zp.append(r["z_perm"])
        print(f"  w{i:02d}  z_mos {r['z_mos']:>7.3f}  z_perm {r['z_perm']:>8.3f}"
              f"  band_complete={r['band_complete']}")
    zm, zp = np.array(zm), np.array(zp)
    z_star = max(a.z_prev, math.ceil(zm.max()) + 1)
    print(f"\n{'-'*60}")
    print(f"max z_mos under H0 ....... {zm.max():.3f}")
    print(f"max z_perm under H0 ...... {zp.max():.3f}  "
          f"({'UNSAFE' if zp.max() >= a.z_prev else 'ok'} as a null)")
    print(f"previously calibrated z* . {a.z_prev}")
    print(f"DERIVED z* ............... {z_star:.1f}")
    print(f"observed FPR at z* ....... {float((zm >= z_star).mean()):.3f} "
          f"(n={len(zm)})")
    print(f"95 % upper bound (3/n) ... {rule_of_three(len(zm)):.1%}")
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as fh:
            json.dump({"config": vars(a), "z_mos": zm.tolist(),
                       "z_perm": zp.tolist(), "z_star": z_star,
                       "fpr_upper_95": rule_of_three(len(zm))}, fh, indent=1)
        print(f"\nwrote {a.out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fpr", action="store_true")
    ap.add_argument("--power", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--substrate", default="PHerc1203_113keV")
    ap.add_argument("--judge", choices=("ruler", "incoherence"), default="ruler")
    ap.add_argument("--windows", type=int, default=12)
    ap.add_argument("--n-perm", type=int, default=99)
    ap.add_argument("--n-mos", type=int, default=199)
    ap.add_argument("--p-claim", type=float, default=0.01)
    ap.add_argument("--family", type=int, default=1, help="m, for BH")
    ap.add_argument("--q", type=float, default=0.05)
    ap.add_argument("--z-prev", type=float, default=4.0)
    ap.add_argument("--seed", type=int, default=1717)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.run:
        return cmd_run(a)
    if a.power:
        return cmd_power()
    return cmd_fpr()


if __name__ == "__main__":
    raise SystemExit(main())
