# Results

Every number here is produced by a script in this repository against data that
is either shipped (`labels/`, `validation/data/substrate/`) or fetched from the
public bucket. The claim → script → artifact map is
[`docs/CLAIMS.md`](docs/CLAIMS.md).

Sections marked **[open]** are results in flight; they are placeholders, not
findings, and they say so. **R9 is the controlled experiment** that explains
the rest: with everything but the label held fixed, letter form is learnable
from human labels and not from model-generated ones.

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

# Open results

<!-- R21 -->
## R11 — Two-generator agreement on PHerc0139 **[open]**

The audit (C-A1) found a second ink generator, `20260709123958`, now covering
37 of 38 PHerc0139 segments and 2 of the 10 `gold113` segments. Per-segment
agreement between the two has not been measured by anyone we know of. It is the
cheapest experiment that would put an honest error bar on every 116 keV AUC
ever reported, including R4's. Slot reserved; **not run**.

| segments with both generators | mean per-segment agreement | disagreement area |
|---|---|---|
| 37 (PHerc0139), 2 (PHerc0500P2) | — | — |
