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

Above 100 keV — the regime of most Grand Prize scrolls — the only available ink
supervision is model output, and we show it descends from a single checkpoint
run outside its calibration regime. This package makes that situation workable
rather than merely lamentable.

**Tool.** A surface renderer validated to median per-layer correlation 1.00000
against official renders, which downloads only the exact chunk shell that
trilinear interpolation touches: 6.4 GB out of a 589 GB volume, 1.392× less
than the naive bounding box, bit-identical output verified at 0 differing
pixels. It renders a 29.21 × 29.58 mm contiguous surface of PHerc1203 — one
component, zero holes — on a laptop.

**Benchmark.** `gold116` and `gold113`: 18 curated derived label sets at
8.640 µm/116 keV and 9.362 µm/113 keV, shipped here, with an evaluation
harness. Measured ceiling of eleven public checkpoints: **AUC 0.57 ± 0.04**,
none separating from a trivial substrate baseline; 0.73 on the one clean-text
segment.

**Validation.** The standard z-permutation null is unsafe here: on text-free
substrate it reaches z = 17.4 and would call 30.9 % of blank windows a
discovery. A block-mosaic null holds. This caught a real false positive
(z_perm 6.14 vs z_mos 0.502) before it became a claim.

*(word count: 199)*

---

## Contribution bullets

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
- `RESULTS.md` contains **open** sections (R9–R11) explicitly marked as
  pending. Either fill them before submitting or leave them marked — they are
  written to be honest as placeholders.
- If a demo is wanted, `python scripts/null_comparison.py --windows 8` runs on
  bundled data in a few minutes and reproduces the headline finding on a
  laptop with no downloads.
