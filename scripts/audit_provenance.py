#!/usr/bin/env python3
"""Verify the circularity audit against the Vesuvius Challenge public catalogue.

    python scripts/audit_provenance.py              # use the bundled snapshot
    python scripts/audit_provenance.py --fetch      # fetch the live catalogue
    python scripts/audit_provenance.py --fetch --out audit/data/provenance.json

Claims checked (see audit/REPORT.md):

  C-A1  a single model generated the published ink labels for the >100 keV
        evaluation corpus;
  C-A2  those labels were computed on fine-resolution volumes, never on the
        113/116 keV volumes they are evaluated against;
  C-A3  the 116 keV "holdout" sample is listed in the generator's own
        compatible_samples.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit.provenance import audit, load_catalogue  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(HERE, "audit", "data", "catalogue_snapshot.json")

# The generator this repository's benchmark labels descend from.
EXPECTED_GENERATOR = "20260417190342"
FOCUS = ("PHerc0343P", "PHerc0500P2", "PHerc0139", "PHerc0009B")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true",
                    help="fetch the live catalogue instead of the bundled snapshot")
    ap.add_argument("--catalogue", default=None,
                    help="path to a local metadata.json (gzipped or plain)")
    ap.add_argument("--out", default=None, help="write the full audit JSON here")
    a = ap.parse_args()

    if a.catalogue:
        src, cat = a.catalogue, load_catalogue(a.catalogue)
    elif a.fetch:
        src, cat = "live: s3://vesuvius-challenge-open-data/metadata.json", load_catalogue()
    elif os.path.exists(SNAPSHOT):
        src, cat = SNAPSHOT, load_catalogue(SNAPSHOT)
    else:
        print("no bundled snapshot; re-run with --fetch", file=sys.stderr)
        return 2

    rep = audit(cat, focus_samples=FOCUS)
    t, models = rep["totals"], rep["models"]

    print(f"source: {src}")
    print(f"catalogue: {rep['catalogue']['n_samples']} samples, "
          f"{rep['catalogue']['n_models']} models")
    print(f"published ink-detection artifacts: {t['n_ink_artifacts']} "
          f"from {t['n_distinct_generators']} distinct generator(s)\n")

    print(f"{'model':<16} {'artifacts':>9}  {'target um':<12} architecture")
    print("-" * 74)
    for mid, m in list(models.items())[:12]:
        tr = m["target_resolution_um"]
        tr_s = f"{tr[0]}-{tr[1]}" if tr and tr[0] is not None else "-"
        print(f"{mid:<16} {m['n_artifacts']:>9}  {tr_s:<12} {m['architecture'] or '-'}")

    print("\nfocus corpus (the samples an evaluator at 113/116 keV will use)")
    print("-" * 74)
    ok = True
    for s in FOCUS:
        c = rep["focus_corpus"][s]
        gens = ",".join(c["generator_model_ids"]) or "(none)"
        comp = ",".join(c["in_compatible_samples_of"]) or "-"
        print(f"  {s}")
        print(f"    ink artifacts .............. {c['n_ink_artifacts']}")
        print(f"    distinct generators ........ {c['n_distinct_generators']}  [{gens}]")
        print(f"    labels COMPUTED on ......... "
              f"{', '.join(f'{u} um / {k} keV' for u, k in c['label_computed_on']) or '-'}")
        print(f"    surface volumes EXIST at ... "
              f"{', '.join(f'{u} um / {k} keV' for u, k in c['surface_volume_grids']) or '-'}")
        print(f"    in compatible_samples of ... {comp}")

    print("\nchecks")
    print("-" * 74)

    labelled = [s for s in FOCUS if rep["focus_corpus"][s]["n_ink_artifacts"] > 0]

    # C-A1 is a claim about the 116 keV corpus specifically -- the only sample
    # with surface volumes at 8.640 um / 116 keV, i.e. the stand-in for the
    # prize scrolls. That is where "no second opinion exists" bites.
    kev116 = "PHerc0343P"
    g116 = rep["focus_corpus"][kev116]["generator_model_ids"]
    c1 = g116 == [EXPECTED_GENERATOR]
    ok &= c1
    print(f"  [{'PASS' if c1 else 'FAIL'}] C-A1  exactly ONE generator for the "
          f"116 keV corpus ({kev116})  -> {g116}")

    # Not a pass/fail: an observation about the rest of the corpus, which moves.
    others = sorted({g for s in labelled if s != kev116
                     for g in rep["focus_corpus"][s]["generator_model_ids"]})
    extra = [g for g in others if g != EXPECTED_GENERATOR]
    print(f"  [note] generators elsewhere in the focus corpus: {others}")
    if extra:
        print(f"         a SECOND generator exists at 113 keV: {extra}")
        for s in labelled:
            c = rep["focus_corpus"][s]
            if len(c["generator_model_ids"]) > 1:
                print(f"           {s}: {c['n_distinct_generators']} generators "
                      f"-> per-segment agreement is now MEASURABLE here, and "
                      f"nobody has measured it")

    computed = sorted({k for s in labelled
                       for _, k in rep["focus_corpus"][s]["label_computed_on"]})
    c2 = all(k < 113.0 for k in computed) if computed else False
    ok &= c2
    print(f"  [{'PASS' if c2 else 'FAIL'}] C-A2  no label was computed at 113/116 keV"
          f"      -> computed at {computed} keV")

    holdout = "PHerc0343P"
    c3 = EXPECTED_GENERATOR in rep["focus_corpus"][holdout]["in_compatible_samples_of"]
    ok &= c3
    print(f"  [{'PASS' if c3 else 'FAIL'}] C-A3  {holdout} is in the generator's "
          f"compatible_samples")

    gen = models.get(EXPECTED_GENERATOR)
    if gen:
        print(f"\n  generator {EXPECTED_GENERATOR}: {gen['long_id']}")
        print(f"    architecture ........ {gen['architecture']}")
        print(f"    target resolution ... {gen['target_resolution_um']} um")
        print(f"    compatible_samples .. {gen['compatible_samples']}")

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as fh:
            json.dump(rep, fh, indent=1, default=str)
        print(f"\nwrote {a.out}")

    print(f"\n{'ALL CHECKS PASS' if ok else 'SOME CHECKS FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
