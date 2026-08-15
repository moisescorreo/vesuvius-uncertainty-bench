# Rendering surfaces without the volume

**Reproduce**:

```bash
python scripts/render_surface.py plan   --recipe recipes/PHerc1203_29mm.json --budget-gb 8
python scripts/render_surface.py render --recipe recipes/PHerc1203_29mm.json --out work/
python scripts/render_surface.py verify-lock --recipe recipes/PHerc1203_29mm.json
```

---

## The problem

Most of the Grand Prize scrolls have no published surface volumes. Of thirteen,
only PHerc1447 has any, and its largest rendered patch is 13.1 mm — below the
25 mm that a meaningful reading claim needs. Nine of the thirteen are at
9.362 µm/113 keV and have **zero** rendered surface between them.

Meshes, however, do exist. PHerc1203 has 22 `tifxyz` grids and no renders. The
gap between "a mesh exists" and "a flattened surface exists" is a render, and a
render conventionally means having the volume — which is **889 GB** for
PHerc1203 and **589 GB** for PHerc0009B. On a laptop that is the end of the
conversation.

## The trick

It is not the end. A surface is a two-dimensional sheet through a
three-dimensional array, and trilinear interpolation over it reads only a thin
**shell** of the chunk grid. That shell is not merely *small* — it is *exactly
computable offline*, because the interpolator's footprint per sample is known:
`floor(p)` and `floor(p)+1` on each axis, for each of the 31 layers.

```python
for dz in (0, 1):
    for dy in (0, 1):
        for dx in (0, 1):
            keys.add(((z+dz)//128 * Ny + (y+dy)//128) * Nx + (x+dx)//128)
```

Union that over every layer and every output tile and you have the complete set
of chunks the render can possibly touch — computed from the mesh alone, with
the network untouched. Everything outside it is served as absent, exactly as
the store itself serves genuinely absent chunks.

### Measured

PHerc0009B `20250919123506` over `20250521125136-8.640um-1.2m-116keV-masked.zarr`
(9598 × 7837 × 7837 uint8 = 589 GB), canvas 31 × 7440 × 6120, tile 256:

| strategy | chunks | GB | % of volume |
|---|---|---|---|
| **exact shell** | **3 180** | **6.67** | 1.13 % |
| per-tile bounding box | 4 426 | 9.28 | 1.57 % |

Over-fetch factor **1.392×**. With a 7.5 GB budget the exact set fits and the
bbox set does not — the difference between rendering the segment and not. The
actual render fetched 3 165 chunks / 6.375 GB in 4.0 minutes (2.7 min prefetch
at 24 threads, 1.3 min tiles); the small shortfall against the plan is chunks
that are genuinely absent from the masked volume.

Planning costs **1.2 minutes and zero bytes of volume data**. Always plan first.

PHerc1203 `auto_grown_20251005230830031` over the 889 GB volume, using the
simpler shared-cache bbox path: 2 378 chunks, **4.98 GB**, 8.4 minutes, 0.56 %
of the volume. (Tiles overlap heavily in chunk space, so a shared cache already
recovers most of the saving; the exact planner is what rescues the cases where
that is not enough.)

## Correctness is verified, not assumed

Two separate gates, because they can fail independently.

**1. The renderer matches the official pipeline.** Against the Challenge's own
published surface volume on a fresh segment
(`PHerc0343P/20250902170441--4_b2`, 125 016 comparable px, 31 layers):

| metric | value |
|---|---|
| median per-layer correlation | **1.00000** |
| median MAD | 0.0014 |
| median frac(\|Δ\| ≤ 1) | 1.000 |
| optimal z-shift | 0 |

Earlier runs on other segments: 0.9999995 and 0.9999992, shift 0.

**2. The chunk restriction changes nothing.** A 384 × 384 window rendered with
the lock and without it: **0 differing pixels**, with 9 chunks blocked. This
matters more than it looks — a chunk set one voxel too small yields a render
that looks perfectly plausible and is wrong at the tile seams.

```
python scripts/render_surface.py verify-lock --recipe ... --window 384
```

## The product

`recipes/PHerc1203_29mm.json` reproduces the largest contiguous flattened
surface we could derive from a prize scroll:

- **29.21 × 29.58 mm** largest full-resolution rectangle
- valid area 1 483 mm², fraction valid 0.680
- **1 connected component, 0 internal holes, 0 dropped tiles**
- canvas 31 × 4640 × 5360 = 43.44 × 50.18 mm, 771 MB output

A collateral finding worth having: the patch size predicted from the `tifxyz`
grid alone was accurate to **0.2 mm**, not the ~1 mm we had assumed. That
accuracy let us decline to render meshes #2 and #3 (predicted 24.0 and 23.4 mm,
i.e. under the 25 mm bar) without paying for them. **Predict from the mesh
before you render.**

## Reading the output honestly — two masks, not one

The mask the renderer writes is **mesh validity**, not material presence. On
PHerc0009B, 7.04 % of nominally valid pixels (2.31 Mpx, 173 mm², dominated by a
single 170 mm² hole) have all 31 layers at zero: the masked volume has no
material there because the auto-grown mesh wandered off the sheet.

Quoting mesh validity gives 24.47 cm² and a 38.53 × 42.68 mm rectangle. The
honest figure uses the **effective mask** (validity AND `mean_z > 0`):

| | mesh mask | effective mask |
|---|---|---|
| area | 24.47 cm² | **22.75 cm²** |
| largest rectangle | 38.53 × 42.68 mm | **44.41 × 30.84 mm** |

The difference is not cosmetic. Calibrating a null on the inflated mask shifts
`z_mos` from 3.52 to 2.67–3.19 — the data hole biases the null. **Always
calibrate on the effective mask.**

## Gotchas that cost us time

- `dimension_separator` in `.zarray` is `'.'` on some samples and `'/'` on
  others. Hardcoding it gives a 100 % chunk miss and a silently blank render.
- The `tifxyz` invalid sentinel is **−1.0**, not 0 and not NaN.
- Points are stored **(x, y, z)**; zarr indexes **(z, y, x)**.
- Validity/normals sample NEAREST **without clamping** (out of range means
  invalid); coordinates sample BILINEAR **with** replicate clamping. Using one
  sampler for both changes the border mask.
- uint8 output **truncates**, it does not round.
- The z-profile argmax sits off centre. That is the physics of a 31-layer
  stack — it reproduces on the official PHerc0343P renders too — not a
  registration failure.
- Segments share chunks: the union of the top 8 PHerc0009B meshes is 26.89 GB
  against a naive sum of 55.81 GB. Plan the set you want *jointly*.

## What this does not solve

Rendering the **fine** scans is still out of reach: PHerc0009B at 2.401 µm
would be 705 GB of shell out of a 23.2 TB volume. The cheap-shell trick scales
with surface area over voxel size squared, and at 2.4 µm that ratio stops being
kind. Fine-resolution ink detection remains something only the Challenge's
infrastructure can do.
