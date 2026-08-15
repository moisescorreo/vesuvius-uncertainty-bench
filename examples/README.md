# Examples

Four things you can do with this repository, shortest first. The first three
need **no network and no GPU**; only the fourth downloads anything.

---

## 1. See what the public state of the art actually achieves at 116 keV

```bash
python scripts/ceiling_table.py
python scripts/ceiling_table.py --per-segment      # reader x segment
python scripts/ceiling_table.py --format md        # for pasting
```

Instant, reads a shipped JSON. The line to look at is the last one:

```
substrate floor (mean_z, no model at all) : AUC 0.5774
largest margin over the floor             : +0.0061  (vs sd 0.0607)
```

A reader that does not beat `mean_z` — a statistic with no model in it — by
more than the segment-to-segment scatter is not demonstrably reading.

## 2. Reproduce the null-model finding on real substrate

```bash
python scripts/null_comparison.py --windows 8 --n-perm 99 --n-mos 99
```

A few minutes on one core, using the substrate cell grids shipped in
`validation/data/substrate/`. These windows contain **no text**, so every
non-zero `z` is a false positive by construction. Expected shape of the result:

```
substrate            judge           n  max z_perm  max z_mos  FPR perm  FPR mos
PHerc1203_113keV     ruler           8      17.437      2.696     37.5%     0.0%
PHerc1203_113keV     incoherence     8       6.376      0.610     25.0%     0.0%
PHerc0009B_116keV    ruler           8       5.144     -0.093     37.5%     0.0%
```

`--report` prints the full published campaign (n = 55 windows, n_mos = 199)
without running anything.

## 3. Audit the provenance of any label you are about to trust

```bash
python scripts/audit_provenance.py --fetch
```

Fetches the Challenge's live `metadata.json` and joins every published
`ink-detection` artifact against the model registry. It prints, per sample:
how many distinct generators produced its labels, at what energy those labels
were **computed** (as opposed to the grid they are displayed on), and whether
the sample sits in the generator's own `compatible_samples`.

A `FAIL` on check C-A1 is not a bug — it means a second generator has appeared
since we last looked, and the table says exactly where. That is the point of
running it live.

## 4. Render a surface from a Grand Prize scroll on a laptop

**Always plan first.** Planning touches zero bytes of volume data and tells you
the price before you pay it:

```bash
python scripts/render_surface.py plan \
    --recipe rendering/recipes/PHerc1203_29mm.json --budget-gb 8
```

```
strategy                 chunks       GB  % of volume
exact shell                3180     6.67        1.13%
per-tile bbox (naive)      4426     9.28        1.57%
over-fetch factor of the naive strategy: 1.392x
```

Then render (~5 GB, ~10 minutes on a good connection):

```bash
python scripts/render_surface.py render \
    --recipe rendering/recipes/PHerc1203_29mm.json --out work/
```

And prove the chunk restriction cost you nothing:

```bash
python scripts/render_surface.py verify-lock \
    --recipe rendering/recipes/PHerc1203_29mm.json --window 384
# -> differing pixels: 0
```

### Rendering something else

Copy `rendering/recipes/PHerc1203_29mm.json`, change `mesh_prefix` and
`volume_prefix` to any pair from the public catalogue, drop the `expected`
block, and plan. Predicting the patch size from the `tifxyz` grid alone is
accurate to **0.2 mm**, so you can reject meshes that will not clear your size
bar without rendering them.

---

## Checking everything still matches

```bash
python scripts/verify_checksums.py
python scripts/build_labels.py --verify
```
