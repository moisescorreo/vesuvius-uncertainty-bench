# How not to hallucinate above 100 keV

The field's failure mode number one is not missing text. It is **finding text
that is not there** — and then building on it. Papyrus substrate has structure
at exactly the spatial scale of writing, so a statistic that asks *"is there a
periodic line rhythm here?"* will happily answer yes on blank material unless
its null model is chosen with care.

This directory contains the two judges we calibrated, the null-model comparison
that shows the standard null is unsafe, the power curves that bound what those
judges can detect, and the record of a real false positive that this machinery
caught before it became a claim.

**Reproduce the headline finding** (bundled real substrate, a few minutes):

```bash
python scripts/null_comparison.py --windows 8 --n-mos 199
python scripts/null_comparison.py --report      # published campaign numbers
```

---

## 1. The permutation null is not safe

The natural null for a surface volume is to **permute the z-order** before
projecting: it destroys any depth-coherent ink signature while preserving the
marginal distribution. It is used widely, we used it, and above 100 keV it is
wrong — because permuting z leaves the *xy* structure of the substrate
completely intact. A line-periodicity statistic computed against it treats
papyrus texture as signal.

Measured on **bare, text-free substrate**, 29 mm windows, no model involved:

| Substrate | Energy | max `z_perm` | max `z_mos` (block mosaic) | windows clearing Z=4 by permutation |
|---|---|---|---|---|
| PHerc1203 | 113 keV | **12.24** | 2.50 | **30.9 %** |
| PHerc0009B | 116 keV | **16.84** | 3.52 | — |

Nearly a third of blank windows would be reported as a discovery. The mosaic
null — rebuild the map from randomly sized patches copied from random positions
of itself, which destroys long-range rhythm while keeping local texture —
holds on both substrates.

**Rule adopted, in advance**: the mosaic decides, the permutation informs. On
these substrates `z_perm` is a useful *diagnostic of how much substrate
structure is present*, and nothing more.

## 2. Synthetic canvases fabricate the thing you are testing for

Real substrate large enough to host a 29 mm window is scarce — in all of
PHerc1203 exactly **one** non-overlapping window exists. The obvious workaround
is to manufacture nulls by mosaicking real patches (14–24 mm) into a bigger
canvas with feathered seams.

It does not work. Those canvases produce line periodicity by themselves:

- `z_mos` up to **7.61**, with p at the 1/200 floor
- `z_perm` up to **22.23**
- 3.6–5.5 % of canvases exceed the inherited claim threshold

The seams *are* a periodic structure at the patch scale. We excluded canvas
nulls from every threshold derivation and flag our own earlier use of them as a
mistake. A control rules out the obvious rebuttal: canvases whose patches are
14–24 mm (seams **outside** the search band) are the *hardest* null, not the
softest — so the tail is intrinsic to the construction, not a seam artifact of
one patch size.

**Where this still bites us**: for the wide band (2.4–8.0 mm), real substrate
cannot sustain 3.5 periods, so 154 of 159 `ruler` nulls are canvas. The
`ruler`'s wide-band FPR is therefore, by construction, an FPR measured mostly
on canvas — stated in the caveats, not buried. The `incoherence` judge has a
null that is one-third real substrate and needs half the threshold; for wide
bands, prefer it.

## 3. This blocked a real false positive

The strongest evidence that the pre-registration was worth its cost.

On the sealed reader map of PHerc1203 (maps computed, hashed and never
inspected before the protocol was signed):

| statistic | value | would it have been a claim? |
|---|---|---|
| `z_perm` (permutation null) | **6.14**, p at the 0.005 floor | **yes** — over Z=4 and p<0.01 |
| `z_mos` (mosaic null, pre-registered) | **0.502**, p = 0.295 | no, by a factor of 18 in p |

The controls confirm it was an artifact: the same judge on bare `mean_z` gives
`z_perm` 3.72, and on the paired permutation-null map 2.56, while all three
mosaic values sit between −0.53 and −0.70. Across five seeds `z_perm` persists
at 5.22–6.70 — it is structural, not noise.

The rule that the mosaic decides was fixed **before** the map was opened, on
the basis of a substrate H0 measured in an earlier round. It was paid for in
advance and it paid off.

## 4. Thresholds with a stated false-positive bound

Both judges use the same pre-registered rule:

```
z* = max(previously calibrated z*, ceil(max z_mos under a REAL-substrate null) + 1)
claim = z_mos >= z*  AND  p_mos <= 0.01  AND  band_complete  AND  period in band
```

Observed FPR is 0 by construction — the threshold is set above the observed
maximum — so the number to quote is the **rule-of-three upper bound `3/n`**:

| judge | band | n nulls | z* | observed FPR | 95 % upper bound |
|---|---|---|---|---|---|
| `ruler` | 2.4–6.5 mm | 204 (real substrate) | 4.0 | 0.000 | **1.5 %** |
| `ruler` | 2.4–8.0 mm | 159 (154 canvas) | 8.0 | 0.000 | 1.9 % |
| `incoherence` | 2.4–8.0 mm | 170 (1/3 real) | 4.0 | 0.000 | **1.8 %** |
| `ruler` | 2.4–6.5 mm | 55 (PHerc1203) | 4.0 | 0.000 | 5.5 % |
| `incoherence` | 2.4–7.0 mm | 55 (PHerc1203) | 3.0 | 0.000 | 5.5 % |

**The arithmetic floor is a pre-flight check, not an afterthought.** The
empirical p cannot go below `1/(n+1)`. With 48 draws it floors at 0.0204, so a
pre-registered `p ≤ 0.01` is *unreachable* and every run is wasted. Both
judges default to `n = 199` (floor 0.005), and the power driver asserts
`1/(n_mos+1) ≤ p_claim` and aborts before spending compute. For a family of `m`
tests at Benjamini–Hochberg level `q` the requirement generalises to
`n_mos ≥ m/q − 1`.

## 5. What the judges can actually detect — the measured wall

Thresholds bound false positives. They say nothing about power, and a negative
from an underpowered test is not evidence of absence. So we injected **real
human text** (Scroll 1 human ink labels, rescaled to preserve physical letter
size, woven at the measured line pitch, with curvature) into **real substrate**
at a controlled contrast `c`, measured in robust sd units of that substrate,
and reported the **realised** `c`, not the nominal one.

| Substrate | Energy | Window | Reader `c` | X₈₀ | power at top of grid |
|---|---|---|---|---|---|
| PHerc1203 | 113 keV | 29.21 × 29.51 mm | 2.59 | **> 7.15** | 0.208 at c = 7.15 |
| PHerc0009B | 116 keV | 29.03 mm square | 2.59–2.96 | **not reached ≤ 4.0** | 0.375 at c = 4.0 |

**Neither judge reaches power 0.50 anywhere on the grid**, let alone 0.80.
Three checks that this is not an artifact of the injection:

1. the **clean-signal arm** — noiseless text, an optimistic upper bound — also
   fails to reach it (0.333 `ruler` / 0.25 `incoherence` at c = 4.0);
2. **realised contrast tracks nominal** (1.52 / 2.00 / 2.61 / 3.03 / 3.97), so
   the axis is honest;
3. **two substrates at two energies reproduce each other.**

The mechanism differs between the judges and both are informative:
`incoherence` *does* localise the injected period (61–69 % of the time; 94–100 %
within its detections) — its limit is the magnitude of `z_mos`, not masking.
The `ruler` is simply blind at 29 mm: 39 % period accuracy, and 33 % of the
time it locks onto the substrate's own 5.54 mm rhythm.

**The consequence, stated as a rule**: with `c_reader ≈ 2.6` and `X > 7.15`,
*any* negative from a line judge on a ~29 mm window is **inconclusive by
construction** — and at a realised `c` of 7.15, nearly 3× what the best public
reader delivers, power is still ~0.21, so **no improvement to the reader alone
rescues it**. The binding constraint is window extent, not contrast.

This is why we did not run the reader on PHerc0009B: a pre-registered power
gate (`judge only if X₈₀ ≤ 2.6`) returned NO-GO, and the honest move was to
stop, not to look anyway.

---

## Files

| Path | What |
|---|---|
| `ruler.py` | Coherent judge: rotate, project rows, autocorrelate, peak in band. 120 angles. |
| `incoherence.py` | Tiled judge: 5 mm strips × 35 mm blocks, per-tile autocorrelation, mass-weighted average. Phase-invariant, so curved baselines add instead of cancelling. 30 angles. |
| `data/substrate/*.npz` | Real substrate cell grids (mean-z, sd-z, coverage) for PHerc1203 @113 keV and PHerc0009B @116 keV. **Pure CT statistics — no model output.** These make section 1 reproducible offline. |
| `data/power_1203_113kev.json` | Full 278-run campaign: H0, canvas stress test, z_perm diagnostics, power by contrast and by injected period. |
| `data/power_0009b_116kev.json` | 364-run gate on PHerc0009B, including the clean-signal and untrimmed-texture arms. |
| `data/fpr_wideband_h0.json` | 448 wide-band nulls behind the `z* = 8.0` derivation. |
| `data/verdict_1203.json` | The 12-test judgement, its controls, and the blocked false positive. |

## Caveats

1. **Window overlap.** Only one 29 mm window in PHerc1203 is fully disjoint;
   the 55-window null uses farthest-point dispersal with mean IoU 0.796. The
   effective n is smaller than 55 and we do not know by how much. The
   rule-of-three bounds above inherit that.
2. **Wide-band `ruler` FPR is canvas-dominated** (154/159). See §2.
3. **The injected text is Scroll 1 human ink at 54 keV**, rescaled, not text
   observed at 113/116 keV. It is the best real-text donor available; it is not
   the same object.
4. **`c` is measured on cell grids**, matching the reader-contrast definition
   used throughout, not on raw pixels.
5. These judges detect **line rhythm**, not letters. A separate glyph-matching
   judge was built and killed: with clean label plus noise at the reader's
   measured contrast it fires (z/letter 6.75, 93 % of letters at z ≥ 3), and on
   the *real* reader map at the same contrast it does not (0.87, 0 %) — at cell
   sizes 4, 8 and 16 px alike. The frozen public reader delivers **contrast,
   not letter shape**. That result is not packaged here beyond this note, but
   it is why we make no claims about glyph-level readability.
