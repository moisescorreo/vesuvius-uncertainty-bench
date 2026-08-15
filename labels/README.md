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

**They are model output, not ground truth.** Every one descends from a single
checkpoint (`20260417190342`) run outside its calibration regime. See
[`../audit/README.md`](../audit/README.md) — including the measurement that
fine-tuning against them collapses 54 keV performance against *human* labels to
chance.

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
  -> Challenge ink model 20260417190342 on the fine scan (2.215 um / 111 keV)
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
