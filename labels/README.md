# Derived ink labels

**Licence: CC BY-NC 4.0 — see [`LICENSE-DATA`](LICENSE-DATA).** Different from
the repository's code licence, and additionally subject to the Vesuvius
Challenge data terms. Read it before redistributing.

## Contents

```
gold116/   8 x .npz   PHerc0343P   8.640 um / 116 keV   9.2 MB
gold113/  10 x .npz   PHerc0500P2  9.362 um / 113 keV    34 MB
```

Each `.npz` holds one array named after its set:

| | |
|---|---|
| key | `label116` or `label113` |
| dtype | `uint8` |
| shape | the exact `(H, W)` of that segment's coarse surface-volume grid |
| meaning | ink probability, 0–255, as produced by the Challenge's ink model on the FINE scan and transferred to this grid |
| filename | the segment id, matching the Challenge's own ids |

```python
import numpy as np
lab = np.load("labels/gold116/20250511003658.npz")["label116"]   # (3440, 2060)
```

## Read this before using them

**They are not binary.** Ink fraction changes by more than 2× between
thresholds 64 and 192. Pick one and you are reporting your threshold. The
curation in `../benchmark/data/curation_gold116.json` gives a measured
three-way split (positive / negative / **ignore**) per segment and per tier.

**They are model output, not ground truth.** See
[`../audit/README.md`](../audit/README.md) — including the measurement that
fine-tuning against them collapses 54 keV performance against *human* labels to
chance.

**`gold113` is a MIXTURE of two generators — corrected.** An earlier version of
this repository declared a single generator for all 38 labels. That was wrong:

| generator | segments |
|---|---|
| `20260417190342` (`new_canon_autoresearch_recipe`, 2.0–3.0 µm) | **36** |
| `20260709123958` (`mrg20736_1um_s1z2`, 1.0–1.5 µm) | **2** — `20250628074500`, `20250919184428` |

The two exceptions are precisely the segments the catalogue covers with *both*
generators; the survey that produced the download paths took the **first**
`ink-detection` entry per segment, which on a dual segment is the second
generator. Attribution was settled by re-derivation: rebuilding from the source
TIFs reproduces the stored arrays **bit for bit for gen2** (max |Δ| = 0 on both)
and not for gen1 (MAD 9.5 and 20.1).

This matters for anything you compute from `gold113`. The two generators agree
with each other at AUC 0.860 ± 0.047, but swapping which one supplies the label
moves a reader's AUC by **0.036** and its contrast `c` by **0.40** — see
[`../RESULTS.md` §R11](../RESULTS.md). `20250628074500` in particular supplies
half of the pooled 113 keV reader contrast quoted in §R7 (2.5902 as published
with gen2, 2.2976 with gen1).

`gold116` is unaffected: PHerc0343P has exactly one generator.

**gold113 has dropped inference tiles.** 25–104 square holes of ~47 × 47 px per
segment, inside valid material, from the generator's own `tile256/stride128`
pass. They are missing data. Training them as negatives is a hard lie; the
curation marks them ignore.

**`20250511003658` is the holdout.** It is the only clean-text segment at
116 keV and every aggregate in this repository excludes it. If you train on
gold116, keep it out.

## Provenance chain

```
EduceLab-Scrolls CT (arXiv:2304.02084)
  -> Vesuvius Challenge surface tracing            -> tifxyz mesh
  -> mesh transformed onto BOTH volumes            -> shared (u,v)
  -> Challenge ink model on the fine scan (2.215 um / 111 keV)
       gold116: 20260417190342 on all 8
       gold113: 20260417190342 on 36, 20260709123958 on 2 (the dual segments)
  -> published ink-detection TIF on the fine grid
  -> [this repo] INTER_AREA resize onto the exact coarse grid shape
  -> labels/gold*/<segment>.npz
```

Only the last step is ours. It is reproducible with
`python scripts/build_labels.py --verify`, which re-derives the arrays from the
public bucket and checks them against `manifest.sha256`.

## Checksums

`manifest.sha256` covers every shipped array.

```bash
cd labels && shasum -a 256 -c manifest.sha256
```
