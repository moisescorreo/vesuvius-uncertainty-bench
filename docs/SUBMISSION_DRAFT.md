# Submission draft — copy/paste into the form

Not submitted. Fill the placeholders marked `<<< >>>` and delete this line.

---

## Title

**Vesuvius Uncertainty Bench: a validated laptop-scale surface renderer, a
labelled benchmark, and a provenance audit for ink detection above 100 keV**

*(shorter alternative if the field is tight)*
**Vesuvius Uncertainty Bench: rendering, benchmarking and not hallucinating
above 100 keV**

---

## Summary (200 words)

The Challenge's 2026 open problems state that "label quality is now one of the
main unwrapping bottlenecks" and that "better diagnostics matter just as much as
better models". This package is exactly that: diagnostics, shipped labels, and
every claim backed by a runnable script.

**Controlled experiment.** Holding architecture, loss and schedule fixed and
varying only the label: training on 113/116 keV model-generated labels leaves
letter form absent (median z per letter 0.58 → −0.03…−0.22, contrast 2.96 →
0.42), while the identical recipe on human 54 keV labels installs it (z −0.04 →
1.66, AUC 0.61 → 0.83). The bottleneck is the labels.

**Error bar.** Two generators agree at AUC 0.860 ± 0.047; swapping the label
source moves a published AUC by 0.036 and contrast by 0.40 — six times the
margin separating top checkpoints.

**Benchmark.** 38 derived labels at 116/113 keV, shipped. Ceiling of eleven
public checkpoints: AUC 0.57 ± 0.04, none separating from a substrate baseline.

**Validation.** The usual permutation null reaches z = 17.4 on blank substrate;
a mosaic null holds, catching a real false positive.

**Renderer.** Correlation 1.00000 with official renders, fetching 6.4 GB of a
589 GB volume; renders a 29 mm PHerc1203 surface on a laptop. All open source
and runnable today.

*(≈200 words. Both quotations verified verbatim against
scrollprize.org/2026_open_problems.)*

---

## Contribution bullets

- **A controlled experiment isolating the supervision bottleneck.** With
  architecture, loss, schedule, augmentation and evaluation harness held fixed
  and **only the label varied**: training against the published 113/116 keV
  model-generated labels leaves letter form absent — median z per letter falls
  from the frozen checkpoint's 0.576 to −0.03…−0.22 across three arms, zero
  letters ever reach z ≥ 3, and contrast collapses from 2.96 to 0.39–0.49. The
  mechanism is measured: ink/background separation barely moves (0.085 → 0.034)
  while background robust sd inflates **×2.4–3.0** — the fine-tune adds
  substrate noise, not letter sharpness. The **identical recipe on human 54 keV
  labels** installs form: median z −0.044 → **1.664** (against an achievable
  ceiling of 3.245 on the same letters), cell AUC 0.608 → **0.827**, contrast
  1.32 → **2.15**, with 54 keV retention *improving* (0.619 → 0.73–0.77) rather
  than collapsing as it had previously. Corpus size is ruled out: `gold113` was
  first expanded to 38 segments, 183.17 cm², 1015 plausible letters.
  **Conclusion: the >100 keV bottleneck is the labels, not the model** — which
  is the case for building an independent benchmark rather than training harder
  against the existing corpus.

- **The inter-generator agreement band, and the error bar every single-label
  evaluation inherits.** Two ink generators now coexist in the public catalogue
  over **114 dual segments**. Measured on the same segments and the same grid,
  they agree at **AUC 0.860 ± 0.047** (Dice 0.547 ± 0.093), and the agreement is
  stroke-level rather than envelope-level — high-pass filtering costs 0.036 of
  correlation while a 12-cell displacement collapses AUC from 0.878 to 0.585.
  This *refutes* the convenient hypothesis: the generators agree better than any
  reader agrees with either, so generator noise does **not** explain the ceiling
  away. What it does establish is precision — **swapping which generator supplies
  the label moves a published AUC by 0.036 and reader contrast `c` by 0.40**, with
  the reader, map, masks and metric held fixed. That is ~6× the +0.0061 margin
  separating the top public checkpoints. The audit also caught an error in our
  own shipping (`gold113` is 36 labels from one generator and 2 from the other,
  settled bit-exactly by re-derivation) and is corrected in place rather than
  quietly.

- **Positioning, stated plainly.** villa PR #1457 (August 2026) now ships
  `tifxyz_label_transfer`, which performs the same label-transfer operation
  used to build these labels — via 3D geometry and nearest-neighbour sampling,
  where ours uses the shared-mesh `(u,v)` and area-averaging appropriate to a
  4.23× reduction of a continuous probability map. For the general case their
  tool is better, and `benchmark/README.md` says so and tabulates the
  differences, including their caveat about uncorrectable 2D canvas offsets —
  which is the most likely place our transfer is wrong. **The contribution here
  is not the transfer.** It is what the transfer was for: the benchmark, the
  measured ceiling against it, the provenance audit, and the inter-generator
  error bar.

- **`gold116` / `gold113` benchmark, shipped.** 18 segments, 119.92 cm² valid,
  1163.9 mm² of ink, on the two grids covering all thirteen prize scrolls.
  Duality verified four ways per segment (shape ratio, grid landing, output
  grid, silhouette IoU and mean-z correlation aligned vs displaced). Measured
  ink-quality caveats included rather than hidden: blob merging in `gold113`
  (median 0.161 of ink in >3 mm² components vs 0.0 for `gold116`), and 25–104
  dropped inference tiles per segment that must be ignored, never trained as
  negatives.

- **The measured ceiling of the public state of the art at 116 keV.** Eleven
  checkpoints plus three substrate baselines: **AUC 0.57 ± 0.04** off-holdout,
  largest margin over a trivial `mean_z` baseline **+0.006** against a
  between-segment sd of **0.061**. On the single clean-text segment, 0.73, and
  there the signal survives residualisation against substrate statistics — real
  and localised, but small and rare.

- **A reproducible provenance audit.** Verified live from the Challenge's own
  `metadata.json`: one generator (`20260417190342`) produced every published
  ink label on the only 8.640 µm/116 keV sample; the labels were never computed
  at 113/116 keV (which makes them independent of that signal — a widely
  repeated claim to the contrary is false); the "holdout" sample sits in the
  generator's `compatible_samples`. Measured consequence: fine-tuning against
  these labels raises validation AUC while dropping holdout AUC below its own
  initialisation and collapsing 54 keV performance against *human* labels to
  chance (0.50).

- **Null models that do not hallucinate, with bounded FPR.** Two line-rhythm
  judges calibrated on **real substrate**. The usual z-permutation null is
  unsafe above 100 keV — it leaves xy substrate structure intact — reaching
  z = 17.4 on blank material and calling 30.9 % of text-free windows a
  discovery. A block-mosaic null holds (max 2.50 / 3.52). Synthetic mosaicked
  canvases **fabricate** line rhythm (z_mos to 7.61) and must not be used for
  calibration. Threshold rule pre-registered; FPR 0 observed with 95 % upper
  bounds of 1.5–1.9 %.

- **Evidence the discipline pays.** On a sealed reader map of PHerc1203 the
  permutation statistic returned a clean positive (z_perm 6.14, p at the floor).
  The pre-registered mosaic statistic returned 0.502 (p 0.295). The rule was
  fixed before the map was opened.

- **Power curves that bound what can be claimed.** Injecting real human text at
  measured contrast into real substrate: no judge reaches power 0.50 anywhere on
  the grid. X₈₀ > 7.15 at 113 keV on a 29.21 mm window; not reached up to
  c = 4.0 at 116 keV on 29.03 mm. Two substrates, two energies, same wall — and
  the binding constraint is **window extent, not reader contrast**, so no reader
  improvement rescues a negative on windows this size.

- **Surface renderer with an offline chunk planner.** Enumerates the exact set
  of zarr chunks a surface render can touch — `floor(p)` and `floor(p)+1` per
  axis per layer — before opening a connection, then fetches only those.
  6.67 GB against 9.28 GB for the naive per-tile bounding box (1.392×
  over-fetch) on a 589 GB volume. Parity with the unrestricted renderer
  verified at **0 differing pixels**; fidelity against the Challenge's own
  published renders at **median correlation 1.00000** (MAD 0.0014, 125 016 px,
  31 layers). Puts surface rendering of prize scrolls on consumer hardware.

- **A 29 mm contiguous surface from a Grand Prize scroll.** PHerc1203
  `auto_grown_20251005230830031`: 29.21 × 29.58 mm, one connected component,
  zero internal holes, 4.98 GB downloaded. Reproducible from a checksummed
  recipe; no data redistributed.

---

## Links

| | |
|---|---|
| Repository | `<<< URL >>>` |
| Licence | MIT (code) / CC BY-NC 4.0 (derived labels) |
| Results table | `RESULTS.md` |
| Claim → script map | `docs/CLAIMS.md` |
| Renderer | `rendering/README.md` |
| Benchmark | `benchmark/README.md` |
| Provenance audit | `audit/README.md` |
| Validation methodology | `validation/README.md` |
| Rendered PHerc1203 surface (optional host) | `<<< URL or omit >>>` |

---

## Fit against the published criteria

Verified quotations, for the submitter's confidence — do not paraphrase these
as if they were ours.

| published criterion | how this package meets it |
|---|---|
| *"label quality is now one of the main unwrapping bottlenecks"* (2026 open problems, §2) | R9 measures that bottleneck causally — same recipe, only the label varied — and R11 puts a ±0.036 AUC / ±0.40 `c` error bar on it. |
| *"better diagnostics matter just as much as better models"* (2026 open problems, §3) | The whole package is diagnostics: a benchmark, a provenance audit, and judges with a bounded false-positive rate. We ship no new reader. |
| *"released or open-sourced early"* (Progress Prizes) | MIT code, CC BY-NC labels, complete on submission — not a promise of a later release. |
| *"Actually get used"* + *"well documented"* (Progress Prizes) | Four worked examples, three of which need no network and no GPU; every claim maps to a command in `docs/CLAIMS.md`; labels ship in-repo so the benchmark runs on a clone. |
| *"real data"* (Progress Prizes) | Every number is measured on published Challenge scans and labels. No synthetic benchmark anywhere. |

## Suggested category

Open source tooling / data + methodology. The package is a tool first
(renderer + benchmark that others can run today), with the audit and the
validation methodology as the findings it enables.

---

## Notes for the submitter

- Nothing in this repository has been published, pushed or shared. The
  repository is local only.
- No scroll data is redistributed. The 42 MB of shipped labels are derived
  arrays under CC BY-NC 4.0 with the EduceLab-Scrolls citation
  (arXiv:2304.02084) and the Challenge data terms attached.
- `RESULTS.md` R9, R10 and R11 are all **CLOSED**; there are no open sections.
  R9 is the controlled label experiment (the package's differentiator); R10 is
  closed by its own pre-registered gate (the trained reader's contrast fell, so
  the power grid was not re-run — stated rather than quietly skipped); R11 is
  the inter-generator agreement band, which came back *against* the hypothesis
  it was posed to test and is reported that way.
- **R11 forced a correction to shipped data** (`gold113` is a two-generator
  mixture). It is corrected in `labels/README.md`, `benchmark/README.md` and the
  shipped `transfer_gold113.json`, with the superseded declaration retained in
  the record. Reviewers may reasonably see the self-correction as a feature; do
  not remove it.
- Follow-ups the package names and does **not** claim: distilling against the
  second generator, and full-resolution agreement on PHerc1667/PHerc0814.
- If a demo is wanted, `python scripts/null_comparison.py --windows 8` runs on
  bundled data in a few minutes and reproduces the headline finding on a
  laptop with no downloads.
