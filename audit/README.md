# Provenance audit: the >100 keV ink-label corpus

**Reproduce**: `python scripts/audit_provenance.py --fetch`

Everything below is read out of the Vesuvius Challenge's own public catalogue,
`s3://vesuvius-challenge-open-data/metadata.json`. No inference, no scraping,
no private data. The script prints PASS/FAIL per claim and writes the full
join to JSON.

---

## Why this matters

If you evaluate an ink detector at 113 or 116 keV, the only supervision
available is the Challenge's published `ink-detection` output. It is easy —
and wrong — to read *"AUC 0.61 against the 116 keV label"* as *the model reads
ink*. What it actually measures is **agreement with whatever produced that
label**. So the first question is not *how good is my model* but *what is the
label, and how many independent opinions does the corpus contain?*

For the corpus that matters here, the answer is: **one**.

---

## C-A1 — one generator for the 116 keV evaluation corpus

`PHerc0343P` is the only sample with surface volumes at exactly
**8.640 µm / 116 keV** — the voxel and energy of PHerc1447, 0268, 0800 and
1218, i.e. Grand Prize scrolls. All eight of its published ink artifacts come
from a single model:

| | |
|---|---|
| model id | `20260417190342` |
| long id | `20260417190342-new_canon_autoresearch_recipe` |
| architecture | `resnet3d-152-3d-decoder` |
| target resolution | 2.0 – 3.0 µm |
| `compatible_samples` | PHerc0139, **PHerc0343P**, **PHerc0500P2**, PHerc0814, PHerc1667, PHercParis4 |
| distinct generators on PHerc0343P | **1 of 1** |

Every one of the 8 segments carries the same `model_id` and the same tiling
parameters (`tile256-stride128`): one batch run, one opinion.

**And the catalogue moves.** As of the bundled snapshot a *second* ink
generator exists, `20260709123958` (`resnet3d-152`, target 1.0–1.5 µm) — but
its coverage is uneven, and it does not touch the 116 keV corpus at all:

| sample | segments with ink | `20260417190342` | `20260709123958` | segments with both |
|---|---|---|---|---|
| PHerc0343P (116 keV grid) | 8 | 8 | **0** | 0 |
| PHerc0500P2 (113 keV grid) | 38 | 38 | 2 | **2** |
| PHerc0139 (113 keV grid) | 38 | 38 | 37 | **37** |
| PHerc0009B | **0** | — | — | — |

So the honest claim is narrower than "one model labelled everything", and we
prefer the narrow one:

> **For the 116 keV corpus — the one that stands in for the prize scrolls —
> exactly one model has ever produced a published ink label, and there is no
> second opinion to cross-check it against.** At 113 keV a second generator has
> begun to appear: on 2 of the 10 segments in `gold113`, and on 37 of 38
> segments of PHerc0139.

`PHerc0009B` has both scans (8.640 µm/116 keV and 2.401 µm/77 keV) and 18
traced meshes, and **zero** published ink. It is the natural second independent
fragment at exactly the prize voxel — and it is *not* in the generator's
`compatible_samples`, which would make it more independent than anything in
`gold116` or `gold113`.

## C-A2 — the labels were never computed at 113/116 keV

| sample | label COMPUTED on | surface volumes EXIST at |
|---|---|---|
| PHerc0343P | 2.215 µm / **111 keV** | 2.215 µm/111 keV, **8.64 µm/116 keV** |
| PHerc0500P2 | 2.215 µm / **111 keV** | 2.215, 4.317 µm/111 keV, **9.362 µm/113 keV** |
| PHerc0139 | 2.399 µm/78 keV and 1.129 µm/59 keV | …, 9.362 µm/113 keV |

This cuts **both ways**, and both directions matter:

- **In favour.** The label is genuinely *independent of the 113/116 keV
  signal*: it never saw that data. That is precisely the condition a
  cross-energy evaluation needs, and it is why `gold116`/`gold113` are worth
  building at all. The widely repeated shorthand — "the 113/116 keV labels are
  pseudo-labels computed on 113/116 keV data" — is false, and the catalogue
  says so. We believed it ourselves until we checked.
- **Against.** The generator's declared regime is 2.0–3.0 µm, and the field's
  own physics work puts the ink-visible optimum near 2.4 µm / 77–78 keV. On
  PHerc0343P it ran at 2.215 µm / **111 keV**, off that optimum.

## C-A3 — the "holdout" is in the generator's compatible_samples

`PHerc0343P` is listed in `compatible_samples` for `20260417190342`. The
segment held out (`20250511003658`) is therefore a *scan* holdout, not an
*object* holdout: the same physical fragment participated in the generator's
development set. Any claim of the form "0343P is a virgin holdout" needs this
caveat attached. This repository attaches it everywhere.

---

## Two measured consequences

Not deductions from provenance — numbers.

### 1. Out of calibration on PHerc0343P

- The generator marks **2.51× less ink** on PHerc0343P than on PHerc0139.
- Optimal alignment between the label and reader response sits at
  **(−1, −1) cells ≈ 138 µm**, not at (0, 0). On PHerc0139 the optimum is
  exactly (0, 0).

A systematic ~138 µm offset is small absolutely and large relative to a stroke:
the measured stroke width on `gold116` is **324 µm** (p90). Enough to degrade
per-pixel metrics while leaving aggregate ones apparently intact.

### 2. Fine-tuning against this label destroys the reader

Two fine-tune runs from the two best public initialisations, ignore-masks
handling the label's ambiguous band, trained on 6 segments, validated on a 7th,
holdout never touched:

| | val AUC (init → final) | holdout AUC | 54 keV human-label intra-AUC |
|---|---|---|---|
| best frozen checkpoint | — | **0.7288** | 0.72–0.76 |
| fine-tune v1 (from `s42_060k`) | 0.5910 → **0.6744** | 0.6198 | **0.4972** |
| fine-tune v2 (from `s42_040k`) | 0.6534 → **0.6804** | 0.6187 | **0.5301** |

Validation goes up. The holdout goes *down*, below each run's own
initialisation. And performance against genuine **human** labels at 54 keV
collapses to chance (0.50). The model learned the label's segment-specific
structure, which on speckled and partial segments is the generator's noise.

**Operational rule**: above 100 keV, treat the published label as a *benchmark
of agreement*, not as supervision. Report against it; do not train against it
without an independent check.

---

## What would change the conclusion

Stated in advance, so it can be checked rather than argued:

1. **An independent label at 113 or 116 keV** on any sample — human annotation,
   an IR-imaged fragment, or a model from a genuinely different family.
2. **A published ink detection for PHerc0009B**, which is not in
   `compatible_samples` and already has both scans and 18 meshes.
3. ~~**Two-generator agreement measured per segment**~~ — **DONE. See
   [`../RESULTS.md` §R11](../RESULTS.md).**

### Result of item 3

The dual corpus is larger than the check above reports: **114 segments**, not
39 (PHercParis4 37, PHerc0139 37, PHerc1667 19, PHerc0814 19, PHerc0500P2 2).
gen2 never runs alone.

The two generators **agree at AUC 0.860 ± 0.047** (Dice 0.547 ± 0.093), and the
agreement is stroke-level: high-pass filtering costs only 0.036 of correlation,
while displacing one map against the other collapses AUC from 0.878 to 0.585.

That answer runs **against** the hypothesis this item was posed to test. We
expected agreement around a good reader's level (~0.7–0.8), which would have
placed every reported AUC inside generator noise. At 0.860 the generators agree
*better than any reader agrees with either of them*, so **generator
disagreement does not explain the ceiling away** — the shortfalls in the
benchmark are real.

What it does establish is **precision**. Swapping which generator supplies the
label, with the reader and metric held fixed, moves AUC by **0.036** and
contrast `c` by **0.40** — roughly six times the +0.0061 margin that separates
the top public checkpoints. Every single-generator evaluation, including ours,
carries that term.

It also surfaced an error in our own shipping: `gold113` is a **mixture** —
36 labels from gen1, 2 from gen2 — corrected in
[`../labels/README.md`](../labels/README.md) and in the shipped transfer record.

And a lead: gen2's labels are substantially more letter-shaped than gen1's
(median z per letter 3.16 vs 0.76, winning 12 of 12 paired segments), which
reopens distillation against gen2 as a training target. Not run.

---

## Reproducing

```bash
python scripts/audit_provenance.py --fetch --out audit/data/provenance_live.json
```

C-A1/C-A2/C-A3 print PASS or FAIL against the live catalogue. C-A1 is scoped to
the **116 keV corpus** (`PHerc0343P`), which is where "no second opinion exists"
actually bites; generators appearing elsewhere are printed as a `[note]`, not a
failure, together with the samples where two-generator agreement has become
measurable. **A FAIL on C-A1 would be excellent news** — it would mean a second
opinion now exists at 116 keV, and the printed table would say whose.

Gotcha handled in `audit/provenance.py`: `metadata.json` is gzip-compressed but
served without a `Content-Encoding` header, so `requests.get(...).json()`
fails. We sniff the magic bytes instead.
