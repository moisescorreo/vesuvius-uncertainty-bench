# The benchmark: gold116 and gold113

**Reproduce**:

```bash
python scripts/ceiling_table.py                  # the measured ceiling, instant
python scripts/ceiling_table.py --per-segment    # every reader x segment
python scripts/build_labels.py --verify          # re-derive and check the labels
```

The labels themselves are **in this repository** (`labels/`, 42 MB), so the
ceiling table needs no download at all.

---

## What the label sets are

| set | sample | grid | segments | valid area | ink @thr128 | quality |
|---|---|---|---|---|---|---|
| `gold116` | PHerc0343P | 8.640 µm / **116 keV** | 8 | 32.03 cm² | 140.5 mm² | 1 clean text, 3 partial, 3 speckled, 1 empty |
| `gold113` | PHerc0500P2 | 9.362 µm / **113 keV** | 10 | 87.89 cm² | 1023.4 mm² | 2 clean text, 5 partial, 3 blotchy |

Together: **119.92 cm²** usable, **115.97 cm²** trainable excluding the holdout,
**1163.9 mm²** of ink, on the two grids that cover all thirteen prize scrolls
(8.640 µm/116 keV covers PHerc1447/0268/0800/1218; 9.362 µm/113 keV covers the
other nine).

## How they are derived

The Challenge publishes ink predictions computed on the **fine** scan
(2.215 µm/111 keV). We need them on the **coarse** grid (116/113 keV), which is
where the prize scrolls live.

The registration problem does not exist, because the Challenge already solved
it upstream: the segment is traced once, and the *same mesh* is published
transformed onto both volumes (`…-on-<volume>-2.215um.tifxyz` and
`…-on-<volume>-9.362um.tifxyz`). Both surface volumes therefore share the same
`(u, v)` parameterisation, and the transfer is a **2-D resize onto the exact
target shape** — `INTER_AREA`, correct for a 4.23× reduction where bilinear
aliases. No 12-DOF registration, no PPM, no landmark fitting.

Resizing to the *exact target shape* rather than by a scalar factor matters:
each grid is padded to a chunk multiple, so the measured ratio lands at
4.19–4.22 against a theoretical 4.2266 (max deviation 0.83 %). Scaling by
4.2266 would leave a systematic sub-pixel drift across the segment.

### Duality is verified per segment, four ways

| check | what | result |
|---|---|---|
| V1 | measured shape ratio vs theoretical 4.2266 | 4.19–4.22, max deviation 0.83 % |
| V2 | the ink TIF lands exactly on the fine grid | true, 10/10, delta [0, 0] px |
| V3 | same `(u,v)` frame: silhouette IoU and mean-z correlation, aligned vs displaced | IoU 0.928–0.949 vs 0.881–0.893; corr **0.63–0.66** vs **0.13–0.20** |
| V4 | output lands exactly on the 113 keV grid | true, 10/10 |

V3 is the load-bearing one and it is deliberately resolution-independent. A
high-pass correlation was computed and **not** used for the verdict: at 9.362 µm
the 5–37 µm texture the readers rely on is not resolved, so a near-zero
high-pass correlation there is physics, not misalignment. Saying so is cheaper
than being caught by it later.

## Curation: the label is not binary

Ink fraction moves by **more than a factor of 2** across thresholds 64 → 192.
Any evaluation that picks one threshold and calls it ground truth is reporting
its own threshold choice. The curation therefore produces, per segment, a tier
and an explicit three-way mask.

**Ignore-mask recipe** (measured, not invented):

| tier | thr_pos | thr_neg | border dilation | use as | weight |
|---|---|---|---|---|---|
| clean text | 160 | 96 | 3 px | train (holdout if `20250511003658`) | 1.0 |
| partial text | 176 | 80 | 4 px | train | 0.7 |
| speckled | 192 | 64 | 5 px | negatives only | 0.3 |
| empty | — | 64 | 5 px | negatives only | 0.2 |

`ignore` = off-surface ∪ border margin ∪ the threshold band ∪ **holes**. The
3 px ring is justified rather than guessed: the soft ramp from 96 to 160 next
to a confident core measures p50 = 5 px (43 µm) and the real stroke is 324 µm
wide (p90), so the threshold band already covers the ramp and the geometric
ring only needs to cover the ~1 px residual of the 3.9007× resize plus surface
placement slack.

## gold113 is not as good as gold116, and here is the number

Both are shipped; they are not interchangeable.

| | gold116 | gold113 |
|---|---|---|
| ink in components > 3 mm² (median) | **0.0** | **0.161** (max 0.442) |
| largest component | 3.2 mm² | **14.7 mm²** |
| stroke width | 354 µm | 486 µm |
| clean-text segments | 1 of 8 | 2 of 10 |

A letter fits in ~2 mm². Components of 14.7 mm² are blotches, not letters, and
the "608 plausible letters" a naive count reports on gold113 is **inflated** —
it counts blob fragments of letter-like size. Do not read gold113 as a promise
of legible text.

**Dropped inference tiles.** Every gold113 segment has 25–104 square holes of
~47 × 47 px (440 µm), 0.2–2.5 % of the valid domain, sitting *inside* valid
material. They are lost tiles from the generator's own `tile256/stride128`
inference, not clean papyrus. **Training them as negatives is a hard lie**, and
the shipped masks mark them ignore. gold116 does not have them — its few holes
are irregular, i.e. real mesh gaps.

## The ceiling

Eleven public readers plus three substrate baselines, evaluated at cell
resolution (16 px cells) on all eight gold116 segments, geometry chosen by a
sweep on a **non-holdout** segment (`xyz`, dz = −2):

Run `python scripts/ceiling_table.py` for the live table. The summary:

- **Off the holdout, the ceiling is AUC 0.57 ± 0.04.** No checkpoint separates
  from the trivial `mean_z` substrate baseline (0.5774) by more than the
  segment-to-segment scatter: the largest margin over the floor is **+0.006**
  against a between-segment sd of **0.061**.
- **On the one clean-text segment it rises to 0.73**, and there it does beat
  every substrate baseline (0.60–0.67).
- **The signal is real, not a brightness artifact.** Residualising the best
  reader against `{mean_z, sd_z, amplitude}` costs almost nothing
  (0.7288 → 0.7078; ρ with amplitude ≈ 0.03), and the reader's agreement is
  *localised* — its shift-test plateau is ≈0 where `amplitude`'s is 0.31.
- Only one checkpoint (`s43_040k`) reaches the contrast a line judge needs
  (c ≈ 2.8): c = +2.964, c_loc = +2.777 on the holdout. The same checkpoint
  wins independently at 113 keV on gold113 (c = +2.590), which is a genuine
  cross-energy, cross-corpus replication.

### Metrics, and why these

- **AUC** — exact rank statistic on cells, robust to the label's non-binary
  intensities.
- **c** — effect size, (mean over ink − mean over background) / robust sd of
  the background. This is the unit the line judges' power curves are in, so it
  is the number that determines whether a downstream claim is possible at all.
  **AUC and c can disagree, and when they do, c decides.** TTA×8 raises AUC
  from 0.7170 to 0.7474 while *dropping* c from 2.590 to 1.971: averaging eight
  orientations smooths the field and dilutes an oriented response. Every
  ensemble we tried does the same. The best AUC is not the best reader.
- **c_loc** — c minus the plateau reached when the label is rolled 8–12 cells
  away. Separates localised agreement from a global offset.

## Caveats

1. The labels are **model output**, not human ground truth. See
   [`../audit/README.md`](../audit/README.md).
2. Both source samples are in the generator's `compatible_samples`.
3. **n = 1** clean-text segment at 116 keV, **n = 2** at 113 keV. The reader and
   the z-window were selected on those same segments, so the reported contrast
   is slightly optimistic.
4. Label resolution was **never** the bottleneck: AUC with a full-resolution
   label is 0.5608 against 0.5609 with an 8× downsampled one. We checked
   because we assumed otherwise.
5. The `champion` row is an out-of-domain reference (a 54 keV model asked to
   work at 116 keV with a stretched z-stack). It is reported for completeness,
   not as a fair comparison.
