# Vesuvius Uncertainty Bench

**Tools, a benchmark, and an audit for ink detection above 100 keV.**

Every published ink label above 100 keV that we could find in the Vesuvius
Challenge open data comes from **one model checkpoint**, run **outside its
calibration regime**. This repository provides the tooling to work with that
material honestly: a validated surface renderer that fits on a laptop, a
labelled benchmark with a measured ceiling, and a set of statistical judges
whose false-positive rate is bounded on *real substrate* rather than on
synthetic canvases.

The unifying question is the field's failure mode number one:
**how do you avoid hallucinating text that is not there?**

Everything here is measured, not asserted. Every headline number below names
the script that reproduces it and the file that stores it
([`docs/CLAIMS.md`](docs/CLAIMS.md) is the full claim → script → checksum map).

---

## What is in here

| Directory | What it gives you | Runs on |
|---|---|---|
| [`rendering/`](rendering/) | Surface renderer from `tifxyz` + OME-Zarr, validated to median per-layer correlation **1.00000** against official renders. Downloads only the **exact** chunk set the interpolation touches — a **3–7 GB shell out of 589–889 GB volumes**. | Laptop, CPU, no GPU |
| [`benchmark/`](benchmark/) | `gold116` and `gold113`: 18 segments of derived, curated ink labels at 8.640 µm/116 keV and 9.362 µm/113 keV, **shipped in this repo** (42 MB), plus an evaluation harness and the measured **ceiling of 11 public readers**. | Laptop, CPU |
| [`validation/`](validation/) | Two line-periodicity judges with **FPR bounded on real substrate**, the null-model comparison that shows the usual permutation null is unsafe, and power-by-injection curves. | Laptop, CPU |
| [`audit/`](audit/) | Reproducible provenance audit of the >100 keV label corpus, verified from the Challenge's own public `metadata.json`. | Laptop, network |

No GPU is required for anything in this repository. No scroll volume is
redistributed — the renderer derives what it needs from the public bucket.

---

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 1. See the ceiling of public checkpoints at 116 keV (no download, instant)
python scripts/ceiling_table.py

# 2. Verify the provenance audit against the live public catalogue
python scripts/audit_provenance.py --fetch

# 3. Reproduce the mosaic-vs-permutation finding (bundled data, ~1 min)
python scripts/null_comparison.py

# 4. Price a render before paying for it (no volume data is fetched)
python scripts/render_surface.py plan   --recipe rendering/recipes/PHerc1203_29mm.json

# 5. Render a 29 mm surface of PHerc1203 from the public bucket (~5 GB, ~10 min)
python scripts/render_surface.py render --recipe rendering/recipes/PHerc1203_29mm.json
```

Every script writes JSON and prints a table. Seeds are fixed and printed.

---

## The four claims

### 1. A validated renderer that fits a 889 GB volume into a 5 GB download

Rendering a flattened surface from a `tifxyz` mesh normally means having the
volume. The trick here is that trilinear interpolation over a surface touches
a **thin, computable shell** of the chunk grid, and you can enumerate it
exactly — `floor(p)` and `floor(p)+1` per layer, per sample — *before opening
the network*.

| Object | Volume | Chunks fetched | Downloaded | Fraction of volume |
|---|---|---|---|---|
| PHerc1203 `auto_grown_20251005230830031` | 18977×6844×6844 (889 GB) | 2 378 | **4.98 GB** | 0.56 % |
| PHerc0009B `20250919123506` | 9598×7837×7837 (589 GB) | 3 165 | **6.38 GB** | 1.08 % |

The naive per-tile bounding-box approach asks for **4 426 chunks / 9.28 GB**
on the same PHerc0009B surface, against **3 180 chunks / 6.67 GB** for the
exact set computed offline — an over-fetch factor of **1.392×**, which is the
difference between fitting in an 8 GB budget and not. (PHerc1203's 4.98 GB was
achieved with the simpler shared-cache bbox path; the exact-set planner is what
made PHerc0009B feasible at all.)

Correctness is not approximated. Against the official Challenge renders on a
fresh segment (`PHerc0343P/20250902170441--4_b2`, 125 016 px, 31 layers) the
renderer reaches **median per-layer correlation 1.00000**, MAD 0.0014, optimal
z-shift 0, `frac(|Δ| ≤ 1) = 1.000`. And the chunk restriction itself is
**bit-exact**: rendering a 384² window with the restricted chunk set and with
the unrestricted renderer gives **0 differing pixels** while 9 chunks are
blocked.

Product: **29.21 × 29.58 mm of contiguous PHerc1203 surface, one connected
component, zero holes** — reproducible from
[`rendering/recipes/PHerc1203_29mm.json`](rendering/recipes/PHerc1203_29mm.json)
and checksum-verifiable. → [`rendering/README.md`](rendering/README.md)

### 2. A benchmark, and the ceiling it measures

`gold116` (8 segments of PHerc0343P, 8.640 µm/116 keV, 32.03 cm² valid,
140.5 mm² ink) and `gold113` (10 segments of PHerc0500P2, 9.362 µm/113 keV,
87.89 cm² valid, 1023.4 mm² ink) are derived by transferring the Challenge's
own published ink predictions from the fine scan onto the coarse grid — both
surface volumes come from the **same mesh**, so they share `(u,v)` and the
transfer is a 2D resize to the exact target shape, with no 12-DOF registration.
Duality is verified four ways per segment (shape ratio, grid landing, output
grid, silhouette IoU and mean-z correlation aligned vs displaced).

Evaluated against that label, **eleven public readers plus three substrate
baselines** give, outside the one clean-text segment:

| Reader | AUC (7 seg) | ±sd | holdout AUC |
|---|---|---|---|
| `s42_040k` | 0.5835 | .0373 | 0.6624 |
| `ens6` | 0.5814 | .0445 | 0.7198 |
| `s42_060k_tta8` | 0.5714 | .0490 | **0.7288** |
| **`media_z` (substrate baseline)** | **0.5774** | .0607 | 0.6029 |
| `s43_040k` | 0.5609 | .0341 | 0.7106 |
| `sd_z` (baseline) | 0.4829 | .0457 | 0.6554 |

*(full 11-reader table: `python scripts/ceiling_table.py`)*

**Read the ranking with its error bar.** Where a second generator's label
exists, swapping which one supplies it moves AUC by **0.036** and `c` by
**0.40** with the reader and metric fixed — six times the +0.006 margin between
the top rows. The ceiling survives (the two generators agree at 0.860, above
it); its precision does not. → [`RESULTS.md` §R11](RESULTS.md)

**The ceiling of public checkpoints at 116 keV against an independent label is
AUC 0.57 ± 0.04, and no checkpoint separates from the trivial `media_z`
substrate baseline.** On the single segment with clean text it rises to 0.73
and there it does beat every substrate baseline (0.60–0.67), and residualising
against `{media_z, sd_z, amplitude}` barely dents it (0.7288 → 0.7078) — so
the signal is real and localised, just small and rare.

### 3. The circularity audit

Provenance is not folklore; it is in the Challenge's own catalogue.
`scripts/audit_provenance.py --fetch` pulls
`s3://vesuvius-challenge-open-data/metadata.json` (1.18 MB, gzipped without a
`Content-Encoding` header — a gotcha the script handles) and verifies:

- **A single model, `20260417190342`** (`new_canon_autoresearch_recipe`,
  ResNet3D-152 + 3D decoder, `target_resolution_um = [2.0, 3.0]`), produced
  **every** published ink label on PHerc0343P — the only sample with surface
  volumes at exactly 8.640 µm/116 keV, and therefore the stand-in for the prize
  scrolls. Eight of eight segments, same checkpoint, same tiling parameters:
  one batch run, and **no second opinion exists to check it against**. (At
  113 keV a second generator, `20260709123958`, has recently appeared on 2 of
  our 10 `gold113` segments and on 37 of 38 PHerc0139 segments. The audit script
  reports this as it finds it — the catalogue is a moving target, and measuring
  where the two generators disagree is the cheapest useful experiment we can
  name.)
- It was **never run on 113/116 keV data**. On PHerc0343P and PHerc0500P2 it
  ran on the 2.215 µm/111 keV volume; the labels are transferred downstream.
  This cuts both ways and we say so: it means the labels are *independent of
  the 113/116 keV signal*, which is exactly the condition a cross-energy test
  needs — but it also means they were produced out of regime.
- **Out of calibration on PHerc0343P**: the generator's own regime is
  2.4 µm/78 keV; on 0343P (2.215 µm/111 keV) it marks **2.51× less ink** than
  on PHerc0139, and optimal label alignment sits at (−1, −1) cells ≈ **138 µm**
  off.
- **PHerc0343P is in the generator's `compatible_samples`** — the holdout is
  not virgin at the object level.

Two consequences we measured rather than argued:

- "AUC against the 116 keV label" scores **agreement with that one generator**,
  not reading.
- **Fine-tuning against it destroys the reader.** Validation AUC rises
  (0.6534 → 0.6804) while holdout AUC falls below its own initialisation
  (0.7288 frozen → 0.6198 fine-tuned), and 54 keV performance against *human*
  labels collapses from intra-AUC 0.72–0.76 to **0.50–0.53, i.e. chance**.

→ [`audit/README.md`](audit/README.md)

### 3b. The controlled experiment: it is the labels, not the model

Everything above is provenance and correlation. This is the causal test.
Architecture, loss, schedule, augmentation, replay and evaluation harness held
**fixed**; the **only** variable is which label supervises.

| | supervision | median z per letter | cell AUC | contrast `c` |
|---|---|---|---|---|
| frozen checkpoint | — | 0.576 (116 keV) | 0.7106 | 2.964 |
| trained, 3 arms | **model-generated**, 113/116 keV | **−0.03 … −0.22** | 0.590–0.606 | 0.39–0.49 |
| frozen checkpoint | — | −0.044 (54 keV) | 0.6077 | 1.324 |
| trained, same recipe | **human**, 54 keV | **+1.664** | **0.827** | **2.152** |

Against the model-generated labels every arm finishes **below the frozen
checkpoint**, no letter ever reaches z ≥ 3, and contrast collapses. The
mechanism is measured: ink/background separation barely moves (0.085 → 0.034)
while the background's robust sd inflates **×2.4–3.0** — the fine-tune adds
*substrate noise*, not letter sharpness. Against human labels the identical
recipe moves the reader roughly **half way to the achievable ceiling** (3.245
on those same letters), and 54 keV retention *improves* (0.619 → 0.73–0.77)
instead of collapsing.

Corpus size is ruled out: `gold113` was first expanded from 10 to **38
segments, 183.17 cm², 1015 plausible letters** before training.

> **With everything but the label held fixed, letter form is learnable from
> human labels and not from model-generated labels.** The supervision
> bottleneck above 100 keV is the labels — which is the argument for an
> independent benchmark rather than more training against the existing corpus.

→ [`RESULTS.md` §R9](RESULTS.md)

### 4. How not to hallucinate: null models, bounded FPR, and measured walls

This is the part we would most like other teams to take.

**The permutation null is not safe above 100 keV.** Permuting the z-order of a
surface volume leaves the xy structure of the substrate intact, so a periodicity
statistic computed against it sees the substrate as signal. On *bare substrate
with no text*:

| Substrate | Energy | max `z_perm` | max `z_mos` (mosaic null) |
|---|---|---|---|
| PHerc1203 | 113 keV | **12.24** | 2.50 |
| PHerc0009B | 116 keV | **16.84** | 3.52 |

**30.9 %** of text-free 29 mm windows of PHerc1203 would clear a `Z = 4` claim
threshold by permutation alone. The block-mosaic null holds in both.

**Synthetic canvases fabricate the very structure you are testing for.**
Mosaicking real substrate patches into a larger canvas — a standard way to
manufacture nulls when real substrate is scarce — produces line periodicity
at **z_mos up to 7.61** with p at the 1/200 floor. Canvas nulls must not be
used to calibrate a line judge; we exclude them and flag our own earlier use
of them.

**This blocked a real false positive.** On the sealed reader map of PHerc1203,
the default permutation statistic gave **z_perm = 6.14 with p at the floor** —
a clean positive over any threshold we had. The pre-registered mosaic statistic
gave **0.502, p = 0.295**. The controls confirm it was an artifact (the same
judge on bare `media_z` gives z_perm 3.72, on the paired null map 2.56, while
all three mosaic values sit at −0.5 to −0.7). The decision to let the mosaic
decide was registered *before* the map was opened.

**And the wall is extent, not contrast.** Injecting real human text at measured
contrast into real substrate, no judge reaches power 0.50 — let alone 0.80 —
anywhere on the grid:

| Substrate | Energy | Window | Reader contrast `c` | X₈₀ | Power at top of grid |
|---|---|---|---|---|---|
| PHerc1203 | 113 keV | 29.21 × 29.51 mm | 2.59 | **> 7.15** | 0.208 at c = 7.15 |
| PHerc0009B | 116 keV | 29.03 mm square | 2.59–2.96 | **not reached ≤ 4.0** | 0.375 at c = 4.0 |

Two substrates, two energies, same wall. Three checks that this is not an
injection artifact: the *clean-signal* arm (an optimistic upper bound) also
fails to reach it (0.333/0.25 at c = 4.0); the realised contrast tracks nominal
(1.52/2.00/2.61/3.03/3.97), so the axis is honest; and the two substrates
reproduce each other. **Any negative result from a line judge on a ~29 mm
window is inconclusive by construction, and no improvement to the reader alone
rescues it.**

→ [`validation/README.md`](validation/README.md)

---

## Caveats, stated up front

We would rather you find these here than in a footnote.

1. **The labels in `labels/` are model output, not human ground truth.** They
   are the best independent supervision available above 100 keV, and they are
   not truth. `gold48`-style human labels exist only for Scroll 1 at 54 keV.
2. **PHerc0343P and PHerc0500P2 are in the generator's `compatible_samples`.**
   The 116 keV holdout is a *scan* holdout, not an *object* holdout.
3. **`gold113` is not equal in quality to `gold116`.** Ink merges into blobs
   (ink fraction in components > 3 mm²: median 0.161 vs 0.0), stroke width
   486 µm vs 354 µm, and each segment has 25–104 dropped ~47×47 px inference
   tiles inside the valid domain. Those tiles are **ignore**, never negatives —
   the shipped masks encode this. Only 2 of 10 segments are clean text.
4. **The wide-band FPR of the `ruler` judge is measured mostly on canvas**
   (154 of 159 nulls), because real substrate cannot sustain an 8 mm band over
   3.5 periods. The `incoherence` judge is calibrated on one-third real
   substrate and needs half the threshold; prefer it for wide bands.
5. **Small n where it matters.** One clean-text segment at 116 keV, two at
   113 keV; the reader and z-window were selected on those same segments, so
   the reported contrast is slightly optimistic.
6. **The ceiling table is for frozen public checkpoints.** It is a statement
   about what is publicly available today, not a claim that 116 keV ink
   detection is impossible.

---

## Reproducibility

- Python **3.11+** (developed on 3.14), dependencies pinned in
  [`requirements.txt`](requirements.txt).
- All seeds are fixed in code and echoed into every output JSON.
- Every claim maps to a script, a seed and an expected checksum in
  [`docs/CLAIMS.md`](docs/CLAIMS.md); `python scripts/verify_checksums.py`
  checks the shipped artifacts.
- **No Docker image.** The dependency set is four pure wheels
  (`numpy`, `scipy`, `zarr`, `requests`) plus optional `tifffile`/`matplotlib`;
  a pinned `requirements.txt` reproduces it in under a minute, and containerising
  it would add more surface than it removes. Stated explicitly so the omission
  is a decision, not an oversight.
- Hardware used: a consumer laptop (Apple M-series, 10 cores, no discrete GPU).
  The renderer is network-bound, the judges are CPU-bound; nothing needs CUDA.

## Licence

- **Code**: MIT ([`LICENSE`](LICENSE)).
- **Derived labels in `labels/`**: CC BY-NC 4.0
  ([`labels/LICENSE-DATA`](labels/LICENSE-DATA)), because they are derivative
  works of EduceLab-Scrolls data and of Vesuvius Challenge model outputs, and
  inherit those terms. See the data licence for attribution and the required
  citation of arXiv:2304.02084.

## Citing

If this is useful, cite the EduceLab-Scrolls dataset (arXiv:2304.02084) and the
Vesuvius Challenge. See [`CITATION.cff`](CITATION.cff).
