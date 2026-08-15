#!/usr/bin/env python3
"""Render a flattened surface volume from a public tifxyz mesh + CT volume.

    # 1. plan first -- costs nothing, decides whether it fits your disk
    python scripts/render_surface.py plan   --recipe rendering/recipes/PHerc1203_29mm.json
    # 2. render
    python scripts/render_surface.py render --recipe rendering/recipes/PHerc1203_29mm.json \
                                            --out work/PHerc1203
    # 3. prove the chunk restriction changed nothing
    python scripts/render_surface.py verify-lock --recipe ... --window 384

    # validate against an official Challenge render (the correctness gate)
    python scripts/render_surface.py validate --sample PHerc0343P \
        --segment 20250902170441--4_b2 --vol-id 20250521134555 --um 8.64 \
        --suffix 1.2m-116keV --side 384

`plan` NEVER touches the volume data: it enumerates the exact chunk shell from
the mesh alone and reports it against the naive bounding-box strategy, so you
learn the cost before paying it.

Nothing is redistributed. Everything is fetched from
s3://vesuvius-challenge-open-data at run time, subject to the Vesuvius
Challenge data terms you accepted to obtain access.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rendering.render_tifxyz import (  # noqa: E402
    CHUNK, GB, RawVolume, chunk_bytes, coords_and_dirs, grid_normals,
    http_get, layer_offsets, load_tifxyz, output_geometry, plan_chunks,
    render_tile, S3)


def load_recipe(path):
    with open(path) as fh:
        return json.load(fh)


def volume_shape(prefix):
    za = json.loads(http_get(S3 + prefix.rstrip("/") + "/0/.zarray"))
    return tuple(za["shape"]), np.dtype(za["dtype"]).itemsize


def _mesh(rec, work):
    pts, meta = load_tifxyz(rec["mesh_prefix"], os.path.join(work, "mesh"))
    return pts, meta, grid_normals(pts)


def cmd_plan(a):
    rec = load_recipe(a.recipe)
    work = a.work or os.path.join("work", rec["name"])
    os.makedirs(work, exist_ok=True)
    t0 = time.time()
    pts, meta, nrm = _mesh(rec, work)
    shape, itemsize = volume_shape(rec["volume_prefix"])
    W, H, *_ = output_geometry(pts, meta, rec.get("render_scale", 1.0))
    print(f"mesh   : {pts.shape[0]} x {pts.shape[1]}  scale={meta['scale']}")
    print(f"canvas : {rec.get('num_slices', 31)} x {H} x {W}")
    print(f"volume : {shape}  = {np.prod(shape) * itemsize / GB:.1f} GB")
    print("planning the exact chunk shell (no volume data is fetched)...")

    def prog(done, tot, ne, nb):
        print(f"  tiles {done}/{tot}   exact {ne}   bbox {nb}", flush=True)

    exact, box = plan_chunks(pts, nrm, meta, shape,
                             tile=rec.get("tile", 256),
                             n_slices=rec.get("num_slices", 31),
                             progress=prog if a.verbose else None)
    ge = chunk_bytes(len(exact), CHUNK, itemsize) / GB
    gb = chunk_bytes(len(box), CHUNK, itemsize) / GB
    vol_gb = np.prod(shape) * itemsize / GB
    print()
    print(f"{'strategy':<22} {'chunks':>8} {'GB':>8} {'% of volume':>12}")
    print("-" * 54)
    print(f"{'exact shell':<22} {len(exact):>8} {ge:>8.2f} {100*ge/vol_gb:>11.2f}%")
    print(f"{'per-tile bbox (naive)':<22} {len(box):>8} {gb:>8.2f} {100*gb/vol_gb:>11.2f}%")
    print("-" * 54)
    print(f"over-fetch factor of the naive strategy: {gb / max(ge, 1e-9):.3f}x")
    if a.budget_gb:
        print(f"budget {a.budget_gb} GB -> exact fits: {ge <= a.budget_gb}; "
              f"bbox fits: {gb <= a.budget_gb}")
    out = {"recipe": rec["name"], "volume_shape": list(shape),
           "volume_GB": round(vol_gb, 1), "canvas": [rec.get("num_slices", 31), H, W],
           "chunks_exact": len(exact), "GB_exact": round(ge, 3),
           "chunks_bbox": len(box), "GB_bbox": round(gb, 3),
           "overfetch_x": round(gb / max(ge, 1e-9), 3),
           "plan_minutes": round((time.time() - t0) / 60, 2)}
    p = os.path.join(work, "plan_chunks.json")
    with open(p, "w") as fh:
        json.dump(out, fh, indent=1)
    np.save(os.path.join(work, "chunks_allowed.npy"), exact)
    print(f"\nwrote {p} and chunks_allowed.npy ({len(exact)} keys)")
    return 0


def cmd_render(a):
    rec = load_recipe(a.recipe)
    work = a.work or os.path.join("work", rec["name"])
    out_dir = a.out or work
    os.makedirs(out_dir, exist_ok=True)
    pts, meta, nrm = _mesh(rec, work)
    shape, itemsize = volume_shape(rec["volume_prefix"])
    nz = rec.get("num_slices", 31)
    W, H, *_ = output_geometry(pts, meta, rec.get("render_scale", 1.0))

    allowed = None
    ap = os.path.join(work, "chunks_allowed.npy")
    if a.lock and os.path.exists(ap):
        allowed = np.load(ap)
        print(f"chunk lock active: {len(allowed)} keys from {ap}")
    elif a.lock:
        print("no chunks_allowed.npy; run `plan` first for the exact shell",
              file=sys.stderr)

    vol = RawVolume(rec["volume_prefix"], os.path.join(work, "chunks"),
                    threads=rec.get("threads", 16), allowed=allowed)
    offs = layer_offsets(nz, rec.get("slice_step", 1.0))
    name = rec["name"]
    sv = np.lib.format.open_memmap(os.path.join(out_dir, f"sv_{name}.npy"),
                                   mode="w+", dtype=np.uint8, shape=(nz, H, W))
    mask = np.zeros((H, W), np.uint8)
    tile = rec.get("tile", 256)
    t0 = time.time()
    ntiles = ((H + tile - 1) // tile) * ((W + tile - 1) // tile)
    done = 0
    for y0 in range(0, H, tile):
        for x0 in range(0, W, tile):
            y1, x1 = min(y0 + tile, H), min(x0 + tile, W)
            blk, valid = render_tile(pts, nrm, meta, vol, y0, y1, x0, x1, offs)
            sv[:, y0:y1, x0:x1] = blk
            mask[y0:y1, x0:x1] = valid.astype(np.uint8) * 255
            done += 1
            if done % 25 == 0 or done == ntiles:
                print(f"  tile {done}/{ntiles}  fetched {vol.n_fetched} "
                      f"({chunk_bytes(vol.n_fetched, CHUNK, itemsize)/GB:.2f} GB) "
                      f"cached {vol.n_cached} blocked {vol.n_blocked} "
                      f"absent {vol.n_absent}  {(time.time()-t0)/60:.1f} min",
                      flush=True)
    sv.flush()
    np.save(os.path.join(out_dir, f"mask_{name}.npy"), mask)
    meta_out = {
        "name": name, "mesh": rec["mesh_prefix"], "volume": rec["volume_prefix"],
        "shape": [nz, H, W], "num_slices": nz,
        "slice_step": rec.get("slice_step", 1.0), "flip_normals": True,
        "render_scale": rec.get("render_scale", 1.0),
        "frac_valid": round(float((mask > 0).mean()), 4),
        "chunks_fetched": vol.n_fetched, "chunks_cached": vol.n_cached,
        "chunks_blocked": vol.n_blocked, "chunks_absent": vol.n_absent,
        "download_GB": round(chunk_bytes(vol.n_fetched, CHUNK, itemsize) / GB, 3),
        "minutes": round((time.time() - t0) / 60, 2),
    }
    with open(os.path.join(out_dir, f"meta_{name}.json"), "w") as fh:
        json.dump(meta_out, fh, indent=1)
    print("\n" + json.dumps(meta_out, indent=1))
    exp = rec.get("expected", {})
    if exp:
        print("\nvs recipe expectation:")
        for k, got in (("frac_valid", meta_out["frac_valid"]),
                       ("chunks_fetched", meta_out["chunks_fetched"]),
                       ("download_GB", meta_out["download_GB"])):
            if k in exp:
                print(f"  {k:<16} expected {exp[k]}   got {got}")
    return 0


def cmd_verify_lock(a):
    """Render one window twice -- with and without the chunk lock -- and diff.

    This is the claim that the saving is free. It must be exercised, not
    asserted: a chunk set that is one voxel too small produces a render that
    looks fine and is wrong.
    """
    rec = load_recipe(a.recipe)
    work = a.work or os.path.join("work", rec["name"])
    pts, meta, nrm = _mesh(rec, work)
    shape, itemsize = volume_shape(rec["volume_prefix"])
    nz = rec.get("num_slices", 31)
    W, H, *_ = output_geometry(pts, meta, rec.get("render_scale", 1.0))
    allowed = np.load(os.path.join(work, "chunks_allowed.npy"))
    offs = layer_offsets(nz, rec.get("slice_step", 1.0))
    side = a.window
    y0 = a.y0 if a.y0 is not None else (H - side) // 2
    x0 = a.x0 if a.x0 is not None else (W - side) // 2

    free = RawVolume(rec["volume_prefix"], os.path.join(work, "chunks"),
                     threads=rec.get("threads", 16))
    lock = RawVolume(rec["volume_prefix"], os.path.join(work, "chunks"),
                     threads=rec.get("threads", 16), allowed=allowed)
    a1, _ = render_tile(pts, nrm, meta, free, y0, y0 + side, x0, x0 + side, offs)
    a2, _ = render_tile(pts, nrm, meta, lock, y0, y0 + side, x0, x0 + side, offs)
    diff = int((a1 != a2).sum())
    print(f"window [{y0}:{y0+side}, {x0}:{x0+side}]  layers {nz}")
    print(f"chunks blocked by the lock : {lock.n_blocked}")
    print(f"differing pixels           : {diff}")
    print(f"IDENTICAL: {diff == 0}")
    return 0 if diff == 0 else 1


def cmd_validate(a):
    """Compare our render against the official Challenge surface volume.

    Gate: median per-layer correlation >= 0.95. Measured on
    PHerc0343P/20250902170441--4_b2: 1.00000.
    """
    import zarr
    seg_base = a.segment.split("-")[0]
    mesh = (f"{a.sample}/segments/{a.segment}/mesh/"
            f"{seg_base}-on-{a.vol_id}-{a.um}.tifxyz")
    official = (f"{a.sample}/segments/{a.segment}/surface-volumes/"
                f"{a.um}-{a.suffix}-volume-{a.vol_id}.zarr")
    vol_pref = a.volume or f"{a.sample}/volumes/{a.vol_id}-{a.um:.3f}um-{a.suffix}-masked.zarr"
    work = a.work or os.path.join("work", "validate", a.segment)
    os.makedirs(work, exist_ok=True)

    pts, meta = load_tifxyz(mesh, os.path.join(work, "mesh"))
    nrm = grid_normals(pts)
    W, H, *_ = output_geometry(pts, meta)
    z = zarr.open(S3 + official, mode="r")
    arr = z["0"] if hasattr(z, "keys") and "0" in z else z
    nz = arr.shape[0]

    side = a.side
    y0 = a.y0 if a.y0 is not None else (H - side) // 2
    x0 = a.x0 if a.x0 is not None else (W - side) // 2
    vol = RawVolume(vol_pref, os.path.join(work, "chunks"), threads=16)
    offs = layer_offsets(nz)
    mine, valid = render_tile(pts, nrm, meta, vol, y0, y0 + side, x0, x0 + side, offs)
    theirs = np.asarray(arr[:, y0:y0 + side, x0:x0 + side])

    m = valid & (theirs.max(0) > 0)
    print(f"canvas {nz}x{H}x{W}  window [{y0}:{y0+side},{x0}:{x0+side}]  "
          f"comparable px {int(m.sum())}")
    corrs, mads, d1 = [], [], []
    for i in range(nz):
        u, v = mine[i][m].astype(np.float64), theirs[i][m].astype(np.float64)
        if u.std() < 1e-9 or v.std() < 1e-9:
            continue
        corrs.append(float(np.corrcoef(u, v)[0, 1]))
        mads.append(float(np.abs(u - v).mean()))
        d1.append(float((np.abs(u - v) <= 1).mean()))
    res = {"mesh": mesh, "official": official, "window": [y0, y0 + side, x0, x0 + side],
           "comparable_px": int(m.sum()), "layers": len(corrs),
           "corr_median": round(float(np.median(corrs)), 7),
           "mad_median": round(float(np.median(mads)), 5),
           "frac_within_1_median": round(float(np.median(d1)), 5)}
    print(json.dumps(res, indent=1))
    gate = res["corr_median"] >= 0.95
    print(f"\nGATE (corr_median >= 0.95): {'PASS' if gate else 'FAIL'}")
    with open(os.path.join(work, "validate.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    return 0 if gate else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("plan", "render", "verify-lock"):
        p = sub.add_parser(name)
        p.add_argument("--recipe", required=True)
        p.add_argument("--work", default=None)
        p.add_argument("--verbose", action="store_true")
        if name == "plan":
            p.add_argument("--budget-gb", type=float, default=None)
        if name == "render":
            p.add_argument("--out", default=None)
            p.add_argument("--lock", action="store_true", default=True)
            p.add_argument("--no-lock", dest="lock", action="store_false")
        if name == "verify-lock":
            p.add_argument("--window", type=int, default=384)
            p.add_argument("--y0", type=int, default=None)
            p.add_argument("--x0", type=int, default=None)

    p = sub.add_parser("validate")
    p.add_argument("--sample", required=True)
    p.add_argument("--segment", required=True)
    p.add_argument("--vol-id", required=True)
    p.add_argument("--um", type=float, required=True)
    p.add_argument("--suffix", required=True, help="e.g. 1.2m-116keV")
    p.add_argument("--volume", default=None)
    p.add_argument("--side", type=int, default=384)
    p.add_argument("--y0", type=int, default=None)
    p.add_argument("--x0", type=int, default=None)
    p.add_argument("--work", default=None)

    a = ap.parse_args()
    return {"plan": cmd_plan, "render": cmd_render,
            "verify-lock": cmd_verify_lock, "validate": cmd_validate}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
