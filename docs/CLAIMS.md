# Claim → script → artifact

Every headline number in `README.md` and `RESULTS.md`, with the command that
produces it, the seed it uses, and where the evidence lives.

`shipped` = the artifact is in this repository and needs no network.
`derived` = the script fetches from the public bucket and regenerates it.

| # | Claim | Command | Seed | Artifact |
|---|---|---|---|---|
| **C-R1** | Renderer matches official renders at median per-layer correlation 1.00000 (MAD 0.0014, 125 016 px, 31 layers) | `scripts/render_surface.py validate --sample PHerc0343P --segment 20250902170441--4_b2 --vol-id 20250521134555 --um 8.64 --suffix 1.2m-116keV` | n/a (deterministic) | derived → `work/validate/…/validate.json` |
| **C-R2** | Exact chunk shell = 3 180 chunks / 6.67 GB vs 4 426 / 9.28 GB naive; over-fetch 1.392× | `scripts/render_surface.py plan --recipe rendering/recipes/PHerc0009B_seg.json` | n/a | derived → `work/…/plan_chunks.json` |
| **C-R3** | Chunk restriction is bit-exact: 0 differing pixels, 9 chunks blocked | `scripts/render_surface.py verify-lock --recipe … --window 384` | n/a | stdout, exit 0 |
| **C-R4** | PHerc1203 surface: 29.21 × 29.58 mm, 1 component, 0 holes, 4.98 GB | `scripts/render_surface.py render --recipe rendering/recipes/PHerc1203_29mm.json` | n/a | shipped recipe + expectations: `rendering/recipes/PHerc1203_29mm.json` |
| **C-B1** | gold116/gold113 duality verified 4 ways per segment (corr 0.63–0.66 aligned vs 0.13–0.20 displaced) | `scripts/build_labels.py --verify` | n/a | shipped → `benchmark/data/transfer_gold113.json` |
| **C-B2** | Ceiling at 116 keV = AUC 0.57 ± 0.04; no checkpoint separates from `mean_z` (0.5774) by more than the between-segment sd | `scripts/ceiling_table.py` | n/a | shipped → `benchmark/data/ceiling_gold116.json` |
| **C-B3** | Best reader on the clean-text holdout = 0.7288; survives residualisation (→ 0.7078) | `scripts/ceiling_table.py --per-segment` | n/a | shipped → same |
| **C-B4** | Label quality caveats: gold113 blobs (0.161 vs 0.0 in >3 mm² components), 25–104 dropped tiles/segment | `scripts/build_labels.py --report` | n/a | shipped → `benchmark/data/curation_gold113.json` |
| **C-A1** | One generator (`20260417190342`) for every published ink label on the only 8.640 µm/116 keV sample |  `scripts/audit_provenance.py --fetch` | n/a | shipped snapshot → `audit/data/catalogue_snapshot.json` |
| **C-A2** | No >100 keV label was ever computed at 113/116 keV |  `scripts/audit_provenance.py --fetch` | n/a | same |
| **C-A3** | The 116 keV "holdout" sample is in the generator's `compatible_samples` |  `scripts/audit_provenance.py --fetch` | n/a | same |
| **C-A4** | Fine-tuning against the label: val ↑ (0.6534→0.6804), holdout ↓ (0.7288→0.6187), 54 keV human-label AUC → 0.50 | (reported, not re-runnable here — needs GPU training) | — | `audit/README.md` §2 |
| **C-A5** | Controlled label experiment: model-generated labels → z 0.576 → −0.03…−0.22, c 2.96 → 0.39–0.49; human labels, same recipe → z −0.044 → 1.664, AUC 0.608 → 0.827, c 1.32 → 2.15 | (reported, not re-runnable here — needs GPU training) | pre-registered z ≥ 3 | `RESULTS.md` §R9 |
| **C-A6** | Mechanism: separation 0.085 → 0.034 while background robust sd inflates ×2.4–3.0 (0.038 → 0.112) | (reported with C-A5) | — | `RESULTS.md` §R9 |
| **C-V1** | Permutation null unsafe: max z_perm 17.4 on text-free substrate, 37.5 % FPR at Z=4; mosaic null 0.0 % | `scripts/null_comparison.py --windows 8 --n-perm 99 --n-mos 99` | 1903 | shipped substrate → `validation/data/substrate/*.npz` |
| **C-V2** | Full campaign: PHerc1203 max z_perm 12.24 vs z_mos 2.50, 30.9 % FPR; PHerc0009B 16.84 vs 3.52 | `scripts/null_comparison.py --report` | 1717 / 1203 | shipped → `validation/data/power_1203_113kev.json`, `power_0009b_116kev.json` |
| **C-V3** | Canvas nulls fabricate rhythm: z_mos to 7.61, z_perm to 22.23, p at the 1/200 floor | `scripts/null_comparison.py --report` | 1203 | shipped → `validation/data/power_1203_113kev.json` (`prueba_esfuerzo_lienzo`) |
| **C-V4** | Blocked false positive: z_perm 6.14 (p at floor) vs z_mos 0.502 (p 0.295) | — (sealed-map judgement, reported) | 5 seeds | shipped → `validation/data/verdict_1203.json` |
| **C-V5** | X₈₀ > 7.15 at 113 keV / 29.21 mm; not reached ≤ 4.0 at 116 keV / 29.03 mm | `scripts/calibrate_judge.py --power` | 1203 / 9000 | shipped → `validation/data/power_*.json` |
| **C-V6** | FPR 0 observed, 95 % upper bounds 1.5–1.9 % | `scripts/calibrate_judge.py --fpr` | 1717 | shipped → `validation/data/fpr_wideband_h0.json` |

## Checksums

```bash
python scripts/verify_checksums.py          # all shipped artifacts
cd labels && shasum -a 256 -c manifest.sha256
```

`labels/manifest.sha256` covers the 18 label arrays; `docs/artifacts.sha256`
covers the shipped JSON and substrate arrays.

## Determinism

- Every stochastic script takes `--seed` and echoes it into its output JSON.
- Null draws use `numpy.random.default_rng(seed)`; the permutation null draws
  **draw-major** and the mosaic null uses `seed + 31337`, so the two streams
  never interleave and a rerun reproduces exactly.
- Floating-point reductions are order-stable at the array level; the judges
  round reported statistics to 4 decimals, which is well above the platform
  noise we observed between macOS and Linux.

## What is *not* reproducible from this repository

Stated so nobody wastes time looking:

- **C-A4/C-A5/C-A6** (the fine-tuning collapse and the controlled label
  experiment) required GPU training runs. The numbers are reported with their
  full configuration, holdouts, pre-registered metric and caveats; the training
  code is not packaged. The 54 keV positive control used **human** ink labels
  from Scroll 1, which this repository does not redistribute.
- **C-V4** (blocked false positive) depends on a sealed reader map produced by
  a checkpoint we do not redistribute. The verdict JSON, its controls and the
  five-seed stability check are shipped.
- The **glyph-matching judge** result mentioned in `validation/README.md` §5 is
  reported as a caveat only; it is not packaged.
