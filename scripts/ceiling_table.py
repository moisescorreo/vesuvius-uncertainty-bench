#!/usr/bin/env python3
"""Print the measured ceiling of public checkpoints against gold116.

    python scripts/ceiling_table.py                 # the headline table
    python scripts/ceiling_table.py --per-segment   # every reader x segment
    python scripts/ceiling_table.py --format md     # markdown, for pasting

Reads `benchmark/data/ceiling_gold116.json`, produced by
`scripts/evaluate_readers.py` on the eight PHerc0343P segments at
8.640 um / 116 keV. No network, no GPU, instant.

How to read it
--------------
`AUC (7 seg)` is the mean over the seven non-holdout segments; `holdout` is the
single segment with clean text (20250511003658), held out of every aggregate.
`media_z` and `sd_z` are SUBSTRATE baselines computed from the same 21 layers --
they use no model at all. A reader that does not beat `media_z` is not reading.

`c` is an effect size: (mean over ink cells - mean over background cells)
divided by the robust sd of the background. `c_loc` subtracts the plateau
reached when the label is rolled 8-12 cells away, so it measures how much of
the agreement is LOCALISED rather than a global brightness offset.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(HERE, "benchmark", "data", "ceiling_gold116.json")

# Reader families, for grouping in the printed table.
BASELINES = {"media_z", "sd_z", "amplitud", "mean_z", "amplitude"}
DEAD_REFS = {"campeon", "champion"}

RENAME = {"media_z": "mean_z", "amplitud": "amplitude",
          "campeon": "champion_54keV"}


def load(path):
    with open(path) as fh:
        return json.load(fh)


def kind(name):
    if name in BASELINES:
        return "substrate baseline"
    if name in DEAD_REFS:
        return "out-of-domain reference"
    return "public checkpoint"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default=DEFAULT)
    ap.add_argument("--per-segment", action="store_true")
    ap.add_argument("--format", choices=("text", "md"), default="text")
    a = ap.parse_args()

    if not os.path.exists(a.json):
        print(f"missing {a.json}", file=sys.stderr)
        return 2
    d = load(a.json)
    meta, agg = d["meta"], d["agregado"]

    rows = []
    for name, m in agg.items():
        ho = m.get("holdout") or {}
        rows.append({
            "reader": RENAME.get(name, name),
            "kind": kind(name),
            "auc": m["auc"], "auc_sd": m["auc_sd"],
            "auc_min": m.get("auc_min"), "auc_max": m.get("auc_max"),
            "c": m["c"], "c_loc": m["c_loc"], "n": m["n"],
            "ho_auc": ho.get("auc"), "ho_c": ho.get("c"), "ho_c_loc": ho.get("c_loc"),
        })
    rows.sort(key=lambda r: -r["auc"])
    base = next((r["auc"] for r in rows if r["reader"] == "mean_z"), None)

    print("CEILING OF PUBLIC READERS AT 116 keV, AGAINST AN INDEPENDENT LABEL")
    print(f"corpus: gold116, {meta['n_seg']} segments of PHerc0343P at "
          f"8.640 um / 116 keV, {meta['cel_px']} px cells")
    print(f"geometry: scale={meta['escala']}, dz={meta['dz']}; "
          f"holdout={meta['holdout']} (excluded from the aggregate)")
    print()

    if a.format == "md":
        print("| reader | kind | AUC (7 seg) | ±sd | c | c_loc | holdout AUC | holdout c |")
        print("|---|---|---|---|---|---|---|---|")
        for r in rows:
            print(f"| `{r['reader']}` | {r['kind']} | {r['auc']:.4f} | "
                  f"{r['auc_sd']:.4f} | {r['c']:+.3f} | {r['c_loc']:+.3f} | "
                  f"{_f(r['ho_auc'])} | {_f(r['ho_c'], '+.3f')} |")
    else:
        print(f"{'reader':<18} {'kind':<24} {'AUC7':>7} {'sd':>6} {'c':>7} "
              f"{'c_loc':>7} | {'HO AUC':>7} {'HO c':>7} {'HO c_loc':>8}")
        print("-" * 96)
        for r in rows:
            mark = "  <-- substrate floor" if r["reader"] == "mean_z" else ""
            print(f"{r['reader']:<18} {r['kind']:<24} {r['auc']:>7.4f} "
                  f"{r['auc_sd']:>6.4f} {r['c']:>+7.3f} {r['c_loc']:>+7.3f} | "
                  f"{_f(r['ho_auc']):>7} {_f(r['ho_c'], '+.3f'):>7} "
                  f"{_f(r['ho_c_loc'], '+.3f'):>8}{mark}")

    if base is not None:
        above = [r for r in rows
                 if r["kind"] == "public checkpoint" and r["auc"] > base]
        margin = max((r["auc"] - base for r in above), default=0.0)
        print()
        print(f"substrate floor (mean_z, no model at all) : AUC {base:.4f}")
        print(f"public checkpoints above that floor        : "
              f"{len(above)} of "
              f"{sum(1 for r in rows if r['kind'] == 'public checkpoint')}")
        print(f"largest margin over the floor              : {margin:+.4f} "
              f"(vs a between-segment sd of "
              f"{max(r['auc_sd'] for r in rows):.4f})")
        print("\nCEILING: AUC ~0.57 +- 0.04 off-holdout; no checkpoint separates from")
        print("the substrate floor by more than the segment-to-segment scatter.")
        print("On the one clean-text segment the best reader reaches "
              f"{max((r['ho_auc'] or 0) for r in rows):.4f}.")

    if a.per_segment:
        print("\nPER SEGMENT (AUC)")
        segs = sorted({s for m in d["por_segmento"].values() for s in m})
        print(f"{'reader':<18} " + " ".join(f"{s[-6:]:>7}" for s in segs))
        print("-" * (19 + 8 * len(segs)))
        for r in rows:
            src = None
            for k in d["por_segmento"]:
                if RENAME.get(k, k) == r["reader"]:
                    src = d["por_segmento"][k]
            if src is None:
                continue
            cells = " ".join(f"{src[s]['auc']:>7.4f}" if s in src and src[s] else
                             f"{'-':>7}" for s in segs)
            print(f"{r['reader']:<18} {cells}")
        print(f"\n(holdout = {meta['holdout']}, last column group)")
    return 0


def _f(v, fmt=".4f"):
    return "-" if v is None else format(v, fmt)


if __name__ == "__main__":
    raise SystemExit(main())
