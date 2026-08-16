# Results

Every number here is produced by a script in this repository against data that
is either shipped (`labels/`, `validation/data/substrate/`) or fetched from the
public bucket. The claim → script → artifact map is
[`docs/CLAIMS.md`](docs/CLAIMS.md).

All sections are closed; follow-ups the results name but do not claim are marked
**not run**. **R9 is the controlled experiment** that explains the rest — with
everything but the label held fixed, letter form is learnable from human labels
and not from model-generated ones — and **R11 is the error bar** that every
number measured against a single generator's label, including R4's and R7's,
turns out to carry.

---

## R1 — Renderer fidelity

`python scripts/render_surface.py validate --sample PHerc0343P --segment 20250902170441--4_b2 ...`

| metric | value |
|---|---|
| median per-layer correlation vs official render | **1.00000** |
| median MAD | 0.0014 |
| median frac(\|Δ\| ≤ 1) | 1.000 |
| optimal z-shift | 0 |
| comparable pixels / layers | 125 016 / 31 |

Earlier runs on two other segments: 0.9999995, 0.9999992, shift 0.

## R2 — Exact chunk shell vs naive bounding box

`python scripts/render_surface.py plan --recipe ...`

| object | volume | strategy | chunks | GB | % of volume |
|---|---|---|---|---|---|
| PHerc0009B `20250919123506` | 589 GB | **exact shell** | **3 180** | **6.67** | 1.13 % |
| " | " | per-tile bbox | 4 426 | 9.28 | 1.57 % |
| PHerc1203 `auto_grown_…830031` | 889 GB | shared-cache bbox | 2 378 | 4.98 | 0.56 % |

Over-fetch factor of the naive strategy: **1.392×**. Realised PHerc0009B
render: 3 165 chunks / 6.375 GB / 4.0 min.

**Lock parity**: 384 × 384 window, rendered with and without the chunk
restriction → **0 differing pixels**, 9 chunks blocked.

## R3 — Product: a 29 mm surface from a prize scroll

| | |
|---|---|
| largest full-resolution rectangle | **29.21 × 29.58 mm** |
| valid area / fraction | 1 483 mm² / 0.680 |
| connected components / internal holes | **1 / 0** |
| canvas | 31 × 4640 × 5360 = 43.44 × 50.18 mm |

PHerc0009B, effective mask: 22.75 cm², largest rectangle 44.41 × 30.84 mm
(mesh-only mask would inflate this to 24.47 cm² / 38.53 × 42.68 mm).

## R4 — Ceiling of public checkpoints at 116 keV

`python scripts/ceiling_table.py`

| reader | kind | AUC (7 seg) | ±sd | holdout AUC |
|---|---|---|---|---|
| `champion_54keV` | out-of-domain ref | 0.5874 | .0184 | 0.5923 |
| `s42_040k` | public checkpoint | 0.5835 | .0373 | 0.6624 |
| `ens6` | public checkpoint | 0.5814 | .0445 | 0.7198 |
| **`mean_z`** | **substrate baseline** | **0.5774** | .0607 | 0.6029 |
| `s42_060k_tta8` | public checkpoint | 0.5714 | .0490 | **0.7288** |
| `s42_075k` | public checkpoint | 0.5695 | .0289 | 0.6674 |
| `s42_060k` | public checkpoint | 0.5614 | .0346 | 0.6928 |
| `s43_040k` | public checkpoint | 0.5609 | .0341 | 0.7106 |
| `s43_060k` | public checkpoint | 0.5608 | .0418 | 0.7032 |
| `s43_075k` | public checkpoint | 0.5527 | .0375 | 0.6536 |
| `amplitude` | substrate baseline | 0.4913 | .0463 | 0.6737 |
| `sd_z` | substrate baseline | 0.4829 | .0457 | 0.6554 |

Largest margin of any checkpoint over the substrate floor: **+0.0061**, against
a between-segment sd of **0.0607**. Ceiling off-holdout: **AUC 0.57 ± 0.04**.
On the single clean-text segment: **0.7288**.

> **Precision caveat (from R11).** These AUCs are measured against one
> generator's label. Where a second generator exists, swapping which one
> supplies the label moves AUC by **0.036** and `c` by **0.40** with the reader
> and metric held fixed — **about six times** the +0.0061 margin that separates
> the top checkpoints here, and more than half the between-segment sd. **The
> ranking in this table is not robust to a label choice that was never
> presented as a choice.** The ceiling itself survives (the two generators agree
> at 0.860, above this ceiling, so the shortfall is real); its *precision* does
> not. See R11.

## R5 — The permutation null is not safe (reproduced live)

`python scripts/null_comparison.py --windows 8 --n-perm 99 --n-mos 99`
(seed 1903, 8 dispersed 29 mm windows per substrate, **no text present**)

| substrate | judge | n | max `z_perm` | max `z_mos` | FPR perm @Z=4 | FPR mos @Z=4 |
|---|---|---|---|---|---|---|
| PHerc1203 @113 keV | `ruler` | 8 | **17.437** | 2.696 | **37.5 %** | **0.0 %** |
| PHerc1203 @113 keV | `incoherence` | 8 | 6.376 | 0.610 | **25.0 %** | **0.0 %** |
| PHerc0009B @116 keV | `ruler` | 8 | 5.144 | −0.093 | **37.5 %** | **0.0 %** |
| PHerc0009B @116 keV | `incoherence` | 8 | 2.226 | 0.493 | 0.0 % | **0.0 %** |

Published campaign at full strength (n = 55 windows, n_mos = 199):
PHerc1203 max `z_perm` 12.24 vs `z_mos` 2.50, **30.9 %** of text-free windows
clearing Z = 4 by permutation; PHerc0009B max `z_perm` 16.84 vs `z_mos` 3.52.

Canvas nulls fabricate line rhythm: `z_mos` to **7.61**, `z_perm` to **22.23**,
p at the 1/200 floor.

## R6 — A blocked false positive

Sealed reader map of PHerc1203, window W1 (29.21 × 29.51 mm):

| statistic | value | would have been a claim? |
|---|---|---|
| `z_perm` | **6.14**, p at the 0.005 floor | **yes** |
| `z_mos` (pre-registered) | **0.502**, p = 0.295 | no, by 18× in p |

Controls: same judge on bare `mean_z` → `z_perm` 3.72; on the paired
permutation-null map → 2.56; all three mosaic values −0.53 to −0.70. Across
five seeds `z_perm` persists at 5.22–6.70.

## R7 — Measured walls

| substrate | energy | window | reader `c` | X₈₀ | power at top of grid |
|---|---|---|---|---|---|
| PHerc1203 | 113 keV | 29.21 × 29.51 mm | 2.59 | **> 7.15** | 0.208 @ c = 7.15 |
| PHerc0009B | 116 keV | 29.03 mm square | 2.59–2.96 | **not reached ≤ 4.0** | 0.375 @ c = 4.0 |

Clean-signal arm (optimistic bound) also fails: 0.333 / 0.25 at c = 4.0.
Realised contrast tracks nominal: 1.52 / 2.00 / 2.61 / 3.03 / 3.97.

> **Sensitivity of the 113 keV input (from R11).** The reader contrast that
> parameterises this wall is pooled over two segments, and one of them
> (`20250628074500`) turns out to carry a label from the *second* generator.
> Published pooled `c` = **2.5902** (gen2 label on that segment); recomputed
> with gen1's label it is **2.2976**, a shift of **−0.29**. This feeds X₈₀
> directly. The verdict does not change sign — the lower value moves *further*
> from the threshold, making the wall harder, not easier — but the input was
> never a single well-defined number, and both figures are stated here.

## R8 — Threshold calibration and FPR bounds

| judge | band | n nulls | z\* | observed FPR | 95 % upper bound |
|---|---|---|---|---|---|
| `ruler` | 2.4–6.5 mm | 204 real | 4.0 | 0.000 | 1.5 % |
| `ruler` | 2.4–8.0 mm | 159 (154 canvas) | 8.0 | 0.000 | 1.9 % |
| `incoherence` | 2.4–8.0 mm | 170 (⅓ real) | 4.0 | 0.000 | 1.8 % |

---

# The controlled experiment

<!-- R21 --> <!-- CLOSED -->
## R9 — Is letter form learnable from these labels? A controlled negative

**Closed.** Pre-registered success metric: **median z per letter ≥ 3** on
untouched holdouts, scored with a glyph-template bank built from *Scroll 1
human* ink labels and used as a fixed library, without recalibration. Metric
**not reached at 113/116 keV**, reached in neither direction by accident: the
same training reached it at 54 keV. That contrast is the result.

The design is a controlled experiment, not a leaderboard entry. **Architecture,
loss, schedule, augmentation, replay and evaluation harness are held fixed.
The only variable is the label.**

### Instrument validated first

Epoch 0 reproduces the frozen checkpoint bit for bit — H116 z 0.866, c 2.9639,
AUC 0.7106 — so any movement below is training, not harness drift.

### The corpus was multiplied before training

28 further labels transferred by the same INTER_AREA procedure (V2 and V4 true
on all, V1 max deviation 2.58 %), taking `gold113` from 10 to **38 segments**:

| | r18 | r21 |
|---|---|---|
| segments | 10 | **38** |
| valid area | 87.89 cm² | **183.17 cm²** |
| ink @thr128 | 1023.4 mm² | **1630.2 mm²** |
| plausible letters | 608 | **1015** |

11.25 GB of surface volumes, 0 errors. So the negative below is not a
small-data result.

### Arm 1 — model-generated labels at 113/116 keV: NEGATIVE

External null, identical to the frozen-reader protocol (230 boxes at 116 keV,
239 at 113 keV):

| model | H116 z_ext | H113 z_ext | c H116 | AUC H116 | frac z≥3 (H116) |
|---|---|---|---|---|---|
| **frozen `s43_040k`** | **0.576** | −1.698 | **2.964** | **0.7106** | 0.00 |
| A2 head-only, lr 3e-5, ep8 | **−0.218** | −0.679 | 0.417 | 0.5931 | 0.00 |
| B full, lr 1e-5, ep3 | **−0.030** | −0.391 | 0.487 | 0.6055 | 0.00 |
| C thr128, lr 3e-5, ep6 | **−0.130** | −0.888 | 0.388 | 0.5904 | 0.00 |

All three arms finish **below the frozen checkpoint** at 116 keV; 113 keV never
leaves negative in any arm or any epoch; `frac z ≥ 3` is **0.00 everywhere**.
`c` collapses from 2.96 to 0.39–0.49. Arm B stopped itself under the
pre-registered rule (validation worsening three epochs); an lr 3e-4 arm aborted
at epoch 1.

**Mechanism, measured.** Ink/background separation barely moves
(0.085 → 0.034), while the **robust background sd inflates ×2.4–3.0**
(0.038 → 0.112). Fine-tuning against a model-generated label adds **substrate
noise, not letter sharpness** — which is precisely why AUC can drift while `c`
falls off a cliff.

### Arm 2 — human labels at 54 keV: POSITIVE CONTROL

Same architecture, same loss, same schedule. Scored on a `gold48` holdout whose
segment was excluded from the replay set:

| | frozen | after training | Δ |
|---|---|---|---|
| median z per letter | **−0.044** | **+1.664** | **+1.708** |
| frac z ≥ 3 | 0.00 | 0.20 | +0.20 |
| cell AUC | 0.6077 | **0.827** | +0.219 |
| `c` | 1.324 | **2.152** | +0.828 |

For scale, the bank's upper bound on that same holdout — clean label plus noise
at the reader's own contrast — is median z **3.245**. Training moved the reader
from *nothing* to roughly **half way to the achievable ceiling**, on the same
letters, with the same judge.

**And retention improved rather than degraded.** The r18 fine-tune had collapsed
54 keV performance against human labels from 0.72–0.76 to chance (0.50–0.53).
Here the replay overshot in the good direction: `gold48` intra-AUC
**0.6189 → 0.7289 / 0.7206 / 0.7326** across the three arms. The hard gate in
the pre-registered reading is not merely passed, it moves the wrong way for the
pessimistic hypothesis.

### Two controls that make the negative interpretable

1. **Not a registration bug.** Localised excess at d = 0 is −0.0452 across the
   28 new labels versus −0.0454 across the 10 independently verified in r18;
   32 of 35 localise. The new corpus is aligned exactly as well as the verified
   one.
2. **Not the judge, and not the energy.** At 54 keV with a *human* label, the
   frozen reader scores z −0.044 (5.3 % of letters at z ≥ 3) while the label
   itself at the **same contrast** scores 4.70 (68.4 %). The judge has ample
   power; the shape deficit belongs to this family of readers.

### Conclusion

> With architecture, loss and schedule held fixed, **letter form is learnable
> from human labels (54 keV) and not from model-generated labels
> (113/116 keV)** — direct causal evidence that the supervision bottleneck
> above 100 keV is the *labels*, not the architecture, the optimiser or the
> corpus size. This strengthens the case for an independent benchmark rather
> than more training against the existing corpus.

This is the result that ties the package together: the audit (R-A) shows the
>100 keV labels descend from one out-of-regime generator; the ceiling (R4)
shows no public reader separates from a substrate baseline against them; and
R9 now shows *why* — training against them cannot install letter form, while
the identical recipe on human labels can.

### Caveats

- The internal null at 113 keV rests on only **38 boxes** and is unstable (it
  reached −36 in one epoch). The **external** null (239 boxes) governs, and is
  what the table reports.
- τ = 3.5584 was calibrated on the **frozen** reader's maps, so `frac_detecta`
  is not comparable across models. **`z` is** the comparable quantity — it is
  standardised against each model's own null — and it is what we report.
- The 113/116 keV labels are output of `ink_canonical_2um` on the fine volume:
  **independent of the 113/116 keV data, but not human truth**. The 54 keV
  labels *are* human. That asymmetry is the experiment's whole point, and also
  its main limitation: "human" and "54 keV" are not fully separable here.
- No glyph template in the bank comes from `gold48`, `gold113` or `gold116`.
- The 113 keV training corpus contains almost no clean text; the two best clean
  segments are reserved as holdout and validation.
- z = 1.664 at 54 keV is a large, controlled *improvement* but still below the
  pre-registered z ≥ 3. We call the 54 keV arm a positive **control**, not a
  solved reading problem.
- **The negative arm used the less letter-shaped of the two available model
  labels (from R11).** The second generator's blobs score median z 3.16 per
  letter against gen1's 0.76, winning on 12 of 12 paired segments. R9's
  conclusion — human versus model supervision — is unaffected, because gen2 is
  still a model. But a distillation target with substantially more letter form
  now demonstrably exists, and **re-running this training arm against gen2 is
  the obvious follow-up. It is not run here.**

<!-- R21 --> <!-- CLOSED -->
## R10 — Power curves for the trained reader: gate not met, not run

**Closed by its own pre-registered gate.** R10 was conditional on R9 producing
a checkpoint with materially better `c`. R9 produced the opposite at
113/116 keV — `c` fell from 2.964 to 0.39–0.49 — so re-running the R7 power
grid would measure a *worse* reader and could only move X₈₀ in the wrong
direction. The grid was not run.

| arm | judge | X₈₀ (frozen) | X₈₀ (trained) |
|---|---|---|---|
| PHerc1203 @113 keV, 29.21 mm | `ruler` | > 7.15 | not run — `c` fell |
| PHerc1203 @113 keV, 29.21 mm | `incoherence` | > 7.15 | not run — `c` fell |
| PHerc0009B @116 keV, 29.03 mm | `ruler` | not reached ≤ 4.0 | not run — `c` fell |
| PHerc0009B @116 keV, 29.03 mm | `incoherence` | not reached ≤ 4.0 | not run — `c` fell |

R7's conclusion therefore stands unchanged and, if anything, hardened: the
binding constraint on a ~29 mm window is **extent**, and the one training route
we could take against the available supervision moves contrast **away** from
the threshold rather than towards it.

A related exploratory pass on PHerc1203 was also gated on R9 reaching z ≥ 3 and
was **not executed**; the sealed reader maps from the R6 judgement remain
untouched.

---

<!-- R22 --> <!-- CLOSED -->
## R11 — Two-generator agreement: an error bar for every single-label AUC

**Closed.** The audit (C-A1) found a second ink generator. It is now measured.
Two models from the public catalogue, run on the *same* segment, agree with each
other at **AUC 0.860 ± 0.047** and **Dice 0.547 ± 0.093**. Swapping which of the
two supplies the label moves a published AUC by **0.036** and the reader
contrast `c` by **0.40** — with the reader, the map, the masks and the metric
held fixed. That is the error bar every 113/116 keV number in this repository,
including R4's and R7's, has been carrying without stating it. And two of the 38
`gold113` labels shipped here turn out to come from the second generator, not
the first as the transfer record declared — corrected below and in
`labels/README.md`.

Shipped evidence: `audit/data/generator_agreement.json`,
`generator_agreement_per_segment.json`, `label_swap.json`.

### Scope: the second generator is larger than the audit reported

| | `20260417190342` (gen1) | `20260709123958` (gen2) |
|---|---|---|
| identifier | `new_canon_autoresearch_recipe` | `mrg20736_1um_s1z2` |
| architecture | resnet3d-152-3d-decoder | resnet3d-152 |
| target resolution | 2.0–3.0 µm | 1.0–1.5 µm, render level 1 |
| segments in catalogue | 202 | **114** |

Segments carrying **both**: **114**, not 39 — PHercParis4 37, PHerc0139 37,
PHerc1667 19, PHerc0814 19, PHerc0500P2 2. gen2 never appears alone: every
segment it covers is also covered by gen1, so the dual corpus is its whole
extent.

### Method

Both maps are renders of the same mesh into different volumes, so they share the
(u, v) parametrisation and differ only in pixel scale. They are brought to one
grid by a single INTER_AREA resize onto the **exact** target shape — never by a
factor — the same procedure used to build `gold113`. On PHerc0500P2 both
generators ran on the *same* volume (2.215 µm), so that pair needs **no resize at
all** and is compared pixel for pixel.

| check | result |
|---|---|
| V1 shape ratio vs resolution ratio | max deviation **0.13 %** (14/14) |
| V2 each TIF lands on its surface-volume grid | **28/28 exact**, Δ = 0 px |
| V4 common grid identical for both | 14/14 |
| best global shift, ±12 cells, high-pass corr | **(0, 0) in 13/13** |

The shift control replaces a frame check and is stronger: if the two maps did not
share a frame, correlation would not peak at zero offset.

### Agreement, 14 segments (2 PHerc0500P2 + 12 PHerc0139)

The 12 PHerc0139 segments were drawn by area into 6 strata, 2 at random per
stratum (seed 22). Area is independent of agreement, so the mean is not selected
on the outcome.

| statistic | mean ± sd | range |
|---|---|---|
| AUC — gen1 as score, gen2 as label @128 | **0.866 ± 0.047** | 0.783 – 0.950 |
| AUC — gen2 as score, gen1 as label @128 | **0.853 ± 0.047** | 0.770 – 0.921 |
| AUC, both directions pooled (n = 28) | **0.860 ± 0.047** | 0.770 – 0.950 |
| Dice @128 | **0.547 ± 0.093** | 0.347 – 0.662 |
| IoU @128 | 0.381 ± 0.085 | 0.210 – 0.495 |
| Pearson r, pixel | 0.592 ± 0.093 | 0.430 – 0.749 |
| Pearson r, 0.1498 mm cell | 0.614 ± 0.097 | 0.452 – 0.772 |
| Pearson r, cell, **high-pass** σ = 1.2 mm | **0.578 ± 0.099** | 0.415 – 0.723 |
| localised excess AUC(0) − mean AUC(8, 12 cells) | 0.277 ± 0.036 | 0.218 – 0.335 |

Dice is flat in the threshold (0.557 at 96, 0.533 at 160), so the disagreement is
not a calibration offset.

**The agreement is stroke-level, not envelope-level.** Removing everything
coarser than 1.2 mm costs only 0.036 of correlation (0.614 → 0.578); and
displacing one map against the other collapses it:

| offset (cells of 0.1498 mm) | 0 | 2 | 4 | 8 | 12 |
|---|---|---|---|---|---|
| AUC | **0.878** | 0.813 | 0.701 | 0.618 | 0.585 |

The two models are agreeing about *where* the ink is, not about a shared
low-frequency picture of damage and fibre.

### They do not label the same surface

| | gen1 | gen2 |
|---|---|---|
| footprint, fraction of canvas | 0.816 ± 0.116 | **0.374 ± 0.094** |
| ink fraction @128 (on the overlap) | 0.166 ± 0.146 | 0.122 ± 0.088 |

Footprint IoU is **0.484 ± 0.223** — and exactly **1.000** on the two PHerc0500P2
segments, where both ran on the same volume. On PHerc0139 the 1.129 µm volume
simply sees less of the segment, so gen2 covers roughly half of what gen1 covers.
All agreement above is measured on the intersection (14.6 ± 5.2 cm² per segment,
≈ 205 cm² in total). gen2 is therefore not a drop-in replacement label: it is a
different, smaller field of view.

### Corpus-wide context (downsampled previews, all 114)

Orientative only — ds8 previews are JPEG and 8× coarser — but they show the fine
sample is not a lucky draw, and that agreement is strongly sample-dependent:

| sample | n | Dice @128 | AUC (gen1 → gen2) |
|---|---|---|---|
| PHerc0500P2 | 1 | 0.580 | 0.897 |
| PHercParis4 | 37 | 0.522 ± 0.237 | 0.878 ± 0.063 |
| PHerc0139 | 37 | 0.516 ± 0.114 | 0.869 ± 0.047 |
| PHerc0814 | 18 | 0.348 ± 0.216 | 0.695 ± 0.101 |
| PHerc1667 | 19 | 0.302 ± 0.097 | 0.731 ± 0.061 |

### What it costs a published number

PHerc0500P2 `20250628074500` is one of the two segments with both generators, so
the evaluation can be repeated changing **only** the label. Reader map, volume,
coverage masks, cell grid and metric are byte-identical to R9's; the gen2 context
reproduces R9's cell count (47 707) exactly.

| reader | AUC vs gen2 | AUC vs gen1 | Δ | `c` vs gen2 | `c` vs gen1 |
|---|---|---|---|---|---|
| `s43_040k` (frozen) | **0.7295** | 0.6953 | −0.0342 | 2.836 | 2.251 |
| `ens2_mix` | 0.7455 | 0.7033 | −0.0422 | 2.049 | 1.564 |
| `ens6` | 0.7400 | 0.6976 | −0.0424 | 1.882 | 1.433 |
| `s42_060k` | 0.7152 | 0.6705 | −0.0447 | 2.071 | 1.520 |
| `mean_z` (substrate) | 0.5273 | 0.5472 | +0.0199 | 0.090 | 0.181 |

Across 10 readers: **Δ AUC = −0.032 ± 0.020**, mean |Δ| = **0.036**; **Δ c =
−0.40 ± 0.23**. The sign is not uniform — the substrate baseline moves the other
way — so this is a re-ranking effect, not a constant offset.

Put against R4: the largest margin any public checkpoint holds over the substrate
floor is **+0.0061**. Changing which generator wrote the label moves the same
kind of number by **0.036 — about six times that margin**, and by more than half
the between-segment sd of 0.0607. The R4 ordering is not robust to a choice that
was never presented as a choice.

**What this does and does not license.** The result is not the one the slot was
reserved to find. We expected the two generators to agree at roughly the level of
a good reader (~0.7–0.8), which would have placed every reported AUC inside
generator noise. They agree at **0.860** — better than any reader agrees with
either of them. So generator disagreement does **not** explain the ceiling away:
R4's 0.57 off-holdout and 0.73 on clean text remain genuine shortfalls. What it
does establish is the *precision* of those shortfalls. A single-generator AUC is
a measurement with a ±0.036 label-choice term and a ±0.40 term in `c`, neither of
which was previously stated, and both of which exceed the differences the
comparison tables are being asked to resolve.

### Bookkeeping correction to `gold113`

The provenance of the 38 `gold113` labels was re-read from the catalogue:
**36 come from gen1 and 2 from gen2** — precisely the two dual segments. The
transfer record declared a single generator for all 38. The cause is mechanical:
the segment survey took the *first* `ink-detection` entry per segment, which for
a dual segment is gen2.

Re-deriving both labels from the TIFs reproduces the stored arrays **bit for bit
for gen2** (max |Δ| = 0 on both segments) and not for gen1 (MAD 9.5 and 20.1),
which settles the attribution.

This is not a bookkeeping detail confined to the lab. `benchmark/data/
transfer_gold113.json` ships in this repository, and one of the two mislabelled
segments, `20250628074500`, supplies half of R7's 113 keV reader contrast:

| | `20250628074500` | `20250716055229` | pooled `c_reader_113keV` |
|---|---|---|---|
| as published (gen2 label) | 2.8363 | 2.3441 | **2.5902** |
| with gen1's label instead | 2.2510 | 2.3441 | **2.2976** |

R7's walls are computed from that pooled contrast. Choosing the other generator
moves it by **−0.29**, in the direction that makes X₈₀ worse. The R7 verdict
(X₈₀ > 7.15, wall not cleared) is unaffected in sign — it moves further from the
threshold, not towards it — but the input was never a single well-defined number.

### Does gen2 carry more letter form?

Same question as R9, same instrument: the Scroll-1 human glyph bank used as a
fixed library, no recalibration; the field is each generator's own label plus
Gaussian noise at the standard contrast, which leaves shape as the only free
variable. Letters are taken from each generator's own components, so each model
competes with its best material. Comparison is paired by segment.

| | gen1 | gen2 |
|---|---|---|
| median z per letter | 0.76 ± 1.93 | **3.16 ± 1.64** |
| fraction of letters with z ≥ 3 | 0.279 ± 0.168 | **0.487 ± 0.137** |
| letter candidates per segment | 116 ± 56 | 53 ± 28 |
| mean of the per-segment median letter height | 1.50 mm | 1.49 mm |

Paired difference **+2.19 ± 1.15, favouring gen2 in 12 of 12 segments.** Frozen
reference points, unchanged: a *human* label at the same contrast scores 4.70,
the bank's ceiling is 6.75, a real reader map scores 0.87.

So gen2's blobs are shaped substantially more like letters than gen1's — while
producing about half as many candidates over a third as much surface. This is
precision, not coverage. It does not overturn R9, whose conclusion was about
human versus model labels; it does say R9's negative arm was trained against the
*less* letter-shaped of the two available model labels, and that a distillation
target with more form now exists. **Re-running the R9 training arm against gen2
is the obvious follow-up; it is not run here.**

### Caveats

- **Agreement is not accuracy.** No human ground truth enters anywhere in R11.
  Two models can agree and both be wrong; 0.860 is an upper bound on how much of
  the residual is reader error, not a measurement of correctness.
- The two generators are not independent in the statistical sense — same
  organisation, same pipeline, overlapping training material. Agreement between
  them is therefore an *optimistic* bound on label reproducibility.
- The fine sample is 14 segments from 2 of the 5 dual samples. PHerc1667 and
  PHerc0814 show markedly lower agreement in the ds8 sweep (Dice 0.30–0.35) and
  were not measured at full resolution.
- The shape comparison uses a validity mask derived from the label footprint
  rather than the surface volume, which is unavailable at 9.362 µm for
  PHerc0139. It is applied identically to both generators, so the paired
  direction is safe; the absolute level is not. On the one segment where the
  exact mask exists, it *widens* the gap (1.36 vs 3.39) rather than creating it.
- Two of 14 segments dropped out of the shape arm (one too small to yield five
  letter candidates, one with fewer than 20 clean negative boxes).
- `20250628074500` is a validation segment in R9, not a holdout. It is used here
  only for a label-swap comparison in which the reader is frozen and never
  trained.

---

# Open results

*(none — R9, R10 and R11 are all closed. The follow-ups they name — distilling
against gen2, and measuring agreement on PHerc1667/PHerc0814 at full resolution
— are stated as not run.)*
