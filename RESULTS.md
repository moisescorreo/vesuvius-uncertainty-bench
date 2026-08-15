# Results

Every number here is produced by a script in this repository against data that
is either shipped (`labels/`, `validation/data/substrate/`) or fetched from the
public bucket. The claim → script → artifact map is
[`docs/CLAIMS.md`](docs/CLAIMS.md).

Sections marked **[open]** are results in flight; they are placeholders, not
findings, and they say so.

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

# Open results

<!-- R21 -->
## R9 — Trained-vs-frozen comparison at 116 keV **[open]**

A training run is in flight. When it lands, this section reports it against
exactly the same harness as R4 — same eight segments, same cells, same holdout,
same geometry — so the comparison is like-for-like rather than a new pipeline
scored against an old table.

| reader | AUC (7 seg) | ±sd | holdout AUC | holdout c | holdout c_loc | 54 keV human-label intra-AUC |
|---|---|---|---|---|---|---|
| best frozen public (`s42_060k_tta8`) | 0.5714 | .0490 | 0.7288 | +1.543 | +1.394 | 0.72–0.76 |
| *trained — pending* | — | — | — | — | — | — |

Pre-registered reading, fixed before the numbers arrive:

- **The holdout, not validation, decides.** Both earlier fine-tunes gained on
  validation (+0.083, +0.027) and *lost* on the holdout against their own
  initialisation. A validation gain alone is not evidence.
- **54 keV retention is a hard gate.** Any run whose gold48 intra-AUC against
  *human* labels falls below ~0.65 has traded reading for label agreement,
  regardless of what the 116 keV number does.
- **`c`, not AUC, determines downstream usability**, because the judges' power
  curves are in units of `c`. A run that raises AUC and lowers `c` is not an
  improvement for any claim.
- To move R7's wall, a reader would need `c` ≳ 7 at 29 mm. Nothing in R4
  suggests that is within reach, and R7 says even reaching it leaves power near
  0.21 — so we do not expect this run to change the extent conclusion, and we
  will say so plainly if it does not.

<!-- R21 -->
## R10 — Line-rhythm and letter-scale curves for the trained reader **[open]**

If R9 produces a checkpoint with materially better `c`, re-running the R7 power
grid on the same substrates gives an updated X₈₀. Slot reserved; the substrates,
windows, seeds and null configuration are already fixed in
`validation/data/*.json` so the comparison is paired.

| arm | judge | X₈₀ (frozen) | X₈₀ (trained) |
|---|---|---|---|
| PHerc1203 @113 keV, 29.21 mm | `ruler` | > 7.15 | — |
| PHerc1203 @113 keV, 29.21 mm | `incoherence` | > 7.15 | — |
| PHerc0009B @116 keV, 29.03 mm | `ruler` | not reached ≤ 4.0 | — |
| PHerc0009B @116 keV, 29.03 mm | `incoherence` | not reached ≤ 4.0 | — |

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
