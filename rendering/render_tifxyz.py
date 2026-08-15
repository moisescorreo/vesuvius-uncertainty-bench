"""Surface-volume renderer from `tifxyz` meshes, with an exact chunk planner.

A faithful NumPy port of `vc_render_tifxyz` as the Vesuvius Challenge pipeline
invokes it for published surface volumes:

    scale=1  group-idx=0  num-slices=31  slice-step=1  rotate=0
    flip=-1  flip-normals=true  composite=false  accum-type=max

Validated against the official renders at **median per-layer correlation
1.00000** (MAD 0.0014, optimal z-shift 0, frac |delta| <= 1 equal to 1.000) on
PHerc0343P/20250902170441--4_b2, 125 016 px, 31 layers.

Why this exists
---------------
Rendering a flattened surface normally means having the volume, and the volumes
are 589-889 GB. But trilinear interpolation over a thin surface touches only a
computable *shell* of the chunk grid, and that shell can be enumerated exactly
-- `floor(p)` and `floor(p)+1` on each axis, for every layer, for every sample
-- **before opening a single connection**. Everything outside the shell is
served as absent, so the output is bit-identical to the unrestricted renderer.

Measured on PHerc0009B (9598 x 7837 x 7837 uint8 = 589 GB):

    exact chunk set   3 180 chunks   6.67 GB
    per-tile bbox     4 426 chunks   9.28 GB    over-fetch 1.392x

Parity was verified, not assumed: a 384 x 384 window rendered with the chunk
lock and without it differs in **0 pixels** while 9 chunks are blocked.

Coordinate conventions (easy to get wrong)
------------------------------------------
* `tifxyz` points are stored in (x, y, z) order; zarr indexing is (z, y, x).
* The sentinel for an invalid grid point is **-1.0**, not 0 and not NaN.
* `dimension_separator` in `.zarray` varies per sample ('.' vs '/'). Hardcoding
  it yields a silent 100 % miss rate, i.e. a blank render.
* Validity and normals are sampled NEAREST with no clamping (out of range means
  invalid); coordinates are sampled BILINEAR with replicate clamping. Using one
  sampler for both changes the mask at the surface border.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
import time

import numpy as np
from scipy import ndimage

S3 = "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/"

NUM_SLICES = 31
SLICE_STEP = 1.0
FLIP_NORMALS = True
CHUNK = 128
GB = 1024.0 ** 3


# --------------------------------------------------------------------- net
def http_get(url, retries=5, timeout=180):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "vesuvius-uncertainty-bench"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            last = e
        except Exception as e:                                  # noqa: BLE001
            last = e
        time.sleep(min(2 ** i, 8))
    raise last


# ------------------------------------------------------------------ tifxyz
def load_tifxyz(prefix, cache_dir=None):
    """Download (and cache) x/y/z.tif + meta.json. Returns (points, meta).

    `points` is (rows, cols, 3) in (x, y, z) order, with the -1.0 sentinel
    already mapped to NaN -- exactly what vc_render_tifxyz does right after
    loading the surface.
    """
    import tifffile

    base = S3 + prefix.rstrip("/") + "/"
    meta = json.loads(http_get(base + "meta.json"))
    planes = []
    for axis in ("x", "y", "z"):
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            p = os.path.join(cache_dir, f"{axis}.tif")
            if not os.path.exists(p):
                with open(p, "wb") as fh:
                    fh.write(http_get(base + f"{axis}.tif"))
            planes.append(tifffile.imread(p).astype(np.float32))
        else:
            import io
            planes.append(tifffile.imread(
                io.BytesIO(http_get(base + f"{axis}.tif"))).astype(np.float32))
    pts = np.stack(planes, -1)
    pts[pts[..., 0] == -1.0] = np.nan          # sentinel -> NaN
    return pts, meta


def grid_normals(pts):
    """Central differences ON THE GRID, cross product, normalised.

    NaN on the first/last row and column and wherever a neighbour is invalid,
    which is what makes the surface border fall out of the mask cleanly.
    """
    out = np.full_like(pts, np.nan)
    xl, xr = pts[1:-1, :-2], pts[1:-1, 2:]
    yu, yd = pts[:-2, 1:-1], pts[2:, 1:-1]
    n = np.cross(xr - xl, yd - yu)
    ln = np.linalg.norm(n, axis=-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[1:-1, 1:-1] = n / ln
    return out


def output_geometry(pts, meta, render_scale=1.0):
    """Destination -> source mapping. Returns (W, H, sx, sy, ul_x, ul_y)."""
    rows, cols = pts.shape[:2]
    sxg, syg = float(meta["scale"][0]), float(meta["scale"][1])
    W = max(1, int(round(cols * (render_scale / sxg))))
    H = max(1, int(round(rows * (render_scale / syg))))
    cx, cy = cols / 2.0 / sxg, rows / 2.0 / syg
    u0, v0 = -0.5 * (W - 1.0), -0.5 * (H - 1.0)
    ul_x = (u0 / render_scale + cx) * sxg
    ul_y = (v0 / render_scale + cy) * syg
    return W, H, sxg / render_scale, syg / render_scale, ul_x, ul_y


def coords_and_dirs(pts, nrm, meta, y0, y1, x0, x1, render_scale=1.0):
    """Volume coordinates and unit normals for one output tile.

    Two different samplers, deliberately:
      * validity and normals -- NEAREST, no clamp (out of range => invalid)
      * coordinates          -- BILINEAR, replicate clamp
    """
    rows, cols = pts.shape[:2]
    _, _, sx, sy, ul_x, ul_y = output_geometry(pts, meta, render_scale)
    fx = np.float32(ul_x) + np.arange(x0, x1, dtype=np.float32) * np.float32(sx)
    fy = np.float32(ul_y) + np.arange(y0, y1, dtype=np.float32) * np.float32(sy)

    ix_n = np.floor(fx + 0.5).astype(np.int64)
    iy_n = np.floor(fy + 0.5).astype(np.int64)
    inb = ((ix_n >= 0) & (ix_n < cols))[None, :] & ((iy_n >= 0) & (iy_n < rows))[:, None]
    ixc = np.clip(ix_n, 0, cols - 1)
    iyc = np.clip(iy_n, 0, rows - 1)
    dirs = nrm[np.ix_(iyc, ixc)]
    valid = inb & np.isfinite(dirs).all(-1) & np.isfinite(pts[np.ix_(iyc, ixc)]).all(-1)

    x0i = np.clip(np.floor(fx).astype(np.int64), 0, cols - 1)
    y0i = np.clip(np.floor(fy).astype(np.int64), 0, rows - 1)
    x1i, y1i = np.minimum(x0i + 1, cols - 1), np.minimum(y0i + 1, rows - 1)
    wx = np.clip(fx - np.floor(fx), 0, 1)[None, :, None]
    wy = np.clip(fy - np.floor(fy), 0, 1)[:, None, None]
    p00, p01 = pts[np.ix_(y0i, x0i)], pts[np.ix_(y0i, x1i)]
    p10, p11 = pts[np.ix_(y1i, x0i)], pts[np.ix_(y1i, x1i)]
    coords = (p00 * (1 - wx) + p01 * wx) * (1 - wy) + (p10 * (1 - wx) + p11 * wx) * wy

    coords = coords.copy()
    dirs = dirs.copy()
    coords[~valid] = np.nan
    dirs[~valid] = np.nan
    if FLIP_NORMALS:
        dirs = -dirs
    ln = np.linalg.norm(dirs, axis=-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        dirs = dirs / ln
    return coords, dirs, valid


def layer_offsets(n=NUM_SLICES, step=SLICE_STEP):
    """buildOffsetList: n layers centred on the surface, `step` voxels apart."""
    return ((np.arange(n) - (n - 1) / 2.0) * step).astype(np.float32)


# ------------------------------------------------------- the chunk planner
def chunk_keys(vz, vy, vx, shape, chunk=CHUNK):
    """Linear keys of every chunk the trilinear interpolation can touch.

    THE TRICK. For each sample the interpolator reads the eight corners
    floor(p) and floor(p)+1 on each axis; that is the whole footprint, and it
    is computable offline from the mesh alone. Union it over all layers and all
    tiles and you have the exact shell -- typically 1 % of the volume.

    Returns sorted unique keys `k = (iz*Ny + iy)*Nx + ix`.
    """
    fin = (np.isfinite(vz) & np.isfinite(vy) & np.isfinite(vx)
           & (vz >= 0) & (vy >= 0) & (vx >= 0)
           & (vz < shape[0]) & (vy < shape[1]) & (vx < shape[2]))
    if not fin.any():
        return np.zeros(0, np.int64)
    iz = vz[fin].astype(np.int64)
    iy = vy[fin].astype(np.int64)
    ix = vx[fin].astype(np.int64)
    Ny = (shape[1] + chunk - 1) // chunk
    Nx = (shape[2] + chunk - 1) // chunk
    out = []
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                a = np.minimum(iz + dz, shape[0] - 1) // chunk
                b = np.minimum(iy + dy, shape[1] - 1) // chunk
                c = np.minimum(ix + dx, shape[2] - 1) // chunk
                out.append(np.unique((a * Ny + b) * Nx + c))
    return np.unique(np.concatenate(out))


def bbox_chunk_keys(coords, dirs, valid, offs, shape, margin=2, chunk=CHUNK):
    """Keys the NAIVE per-tile bounding-box strategy would request.

    Kept so the planner can report the over-fetch factor honestly rather than
    quoting a saving against an imagined baseline.
    """
    if not valid.any():
        return np.zeros(0, np.int64)
    lo = coords + dirs * offs.min()
    hi = coords + dirs * offs.max()
    todo = np.concatenate([lo[valid], hi[valid]], 0)
    if todo.size == 0 or not np.isfinite(todo).any():
        return np.zeros(0, np.int64)
    mn, mx = np.nanmin(todo, 0), np.nanmax(todo, 0)   # (x, y, z)
    Ny = (shape[1] + chunk - 1) // chunk
    Nx = (shape[2] + chunk - 1) // chunk
    rng = []
    for ax, lim in ((2, shape[0]), (1, shape[1]), (0, shape[2])):
        a0 = max(0, int(np.floor(mn[ax])) - margin)
        a1 = min(lim, int(np.ceil(mx[ax])) + margin + 1)
        if a1 <= a0:
            return np.zeros(0, np.int64)
        rng.append(np.arange(a0 // chunk, (a1 - 1) // chunk + 1))
    A, B, C = np.meshgrid(rng[0], rng[1], rng[2], indexing="ij")
    return np.unique(((A * Ny + B) * Nx + C).ravel())


# ------------------------------------------------------------------ volume
class RawVolume:
    """Level 0 of a zarr v2 uint8 volume, with an on-disk chunk cache.

    `allowed` restricts fetches to a precomputed key set; blocked chunks are
    served as fill, which is exactly what the volume itself returns for absent
    chunks -- hence bit-identical output when the set is the exact shell.
    """

    def __init__(self, prefix, cache_dir, threads=16, allowed=None):
        self.base = S3 + prefix.rstrip("/") + "/0/"
        za = json.loads(http_get(S3 + prefix.rstrip("/") + "/0/.zarray"))
        self.shape = tuple(za["shape"])
        self.chunks = tuple(za["chunks"])
        self.dtype = np.dtype(za["dtype"])
        self.sep = za.get("dimension_separator", ".")   # varies per sample!
        self.fill = za.get("fill_value", 0) or 0
        codec = za.get("compressor")
        if codec:
            import numcodecs
            self.codec = numcodecs.get_codec(codec)
        else:
            self.codec = None
        self.dir = cache_dir
        os.makedirs(self.dir, exist_ok=True)
        self.threads = threads
        self._lock = threading.Lock()
        self.n_fetched = self.n_cached = self.n_blocked = self.n_absent = 0
        self.allowed = None if allowed is None else set(int(k) for k in allowed)
        self._Ny = (self.shape[1] + self.chunks[1] - 1) // self.chunks[1]
        self._Nx = (self.shape[2] + self.chunks[2] - 1) // self.chunks[2]

    def key(self, iz, iy, ix):
        return (iz * self._Ny + iy) * self._Nx + ix

    def _path(self, iz, iy, ix):
        return os.path.join(self.dir, f"{iz}_{iy}_{ix}.bin")

    def _chunk(self, t):
        iz, iy, ix = t
        if self.allowed is not None and self.key(iz, iy, ix) not in self.allowed:
            with self._lock:
                self.n_blocked += 1
            return None
        p = self._path(iz, iy, ix)
        if os.path.exists(p):
            with self._lock:
                self.n_cached += 1
            b = np.fromfile(p, dtype=self.dtype)
            return None if b.size == 0 else b.reshape(self.chunks)
        url = f"{self.base}{self.sep.join(map(str, (iz, iy, ix)))}"
        try:
            raw = http_get(url, retries=3)
        except Exception:                                       # noqa: BLE001
            open(p, "wb").close()          # memoise absence as a 0-byte file
            with self._lock:
                self.n_absent += 1
            return None
        if self.codec:
            raw = self.codec.decode(raw)
        with open(p + ".tmp", "wb") as fh:
            fh.write(raw)
        os.replace(p + ".tmp", p)
        with self._lock:
            self.n_fetched += 1
        return np.frombuffer(raw, dtype=self.dtype).reshape(self.chunks)

    def block(self, z0, z1, y0, y1, x0, x1):
        """Dense sub-volume [z0:z1, y0:y1, x0:x1], clipped to the volume."""
        from concurrent.futures import ThreadPoolExecutor
        z0, y0, x0 = max(0, z0), max(0, y0), max(0, x0)
        z1 = min(z1, self.shape[0])
        y1 = min(y1, self.shape[1])
        x1 = min(x1, self.shape[2])
        if z1 <= z0 or y1 <= y0 or x1 <= x0:
            return np.zeros((0, 0, 0), self.dtype), (z0, y0, x0)
        cz, cy, cx = self.chunks
        out = np.full((z1 - z0, y1 - y0, x1 - x0), self.fill, self.dtype)
        tasks = [(iz, iy, ix)
                 for iz in range(z0 // cz, (z1 - 1) // cz + 1)
                 for iy in range(y0 // cy, (y1 - 1) // cy + 1)
                 for ix in range(x0 // cx, (x1 - 1) // cx + 1)]
        with ThreadPoolExecutor(self.threads) as ex:
            for t, blk in zip(tasks, ex.map(self._chunk, tasks)):
                if blk is None:
                    continue
                iz, iy, ix = t
                az0, ay0, ax0 = iz * cz, iy * cy, ix * cx
                sz0, sy0, sx0 = max(z0, az0), max(y0, ay0), max(x0, ax0)
                sz1 = min(z1, az0 + cz)
                sy1 = min(y1, ay0 + cy)
                sx1 = min(x1, ax0 + cx)
                out[sz0 - z0:sz1 - z0, sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = \
                    blk[sz0 - az0:sz1 - az0, sy0 - ay0:sy1 - ay0, sx0 - ax0:sx1 - ax0]
        return out, (z0, y0, x0)


def trilinear(blk, org, vz, vy, vx, shape_vol):
    """Trilinear sample. uint8 TRUNCATES, matching the C++ (no rounding)."""
    if blk.size == 0:
        return np.zeros(vz.shape, np.float32)
    oz, oy, ox = org
    fz, fy, fx = vz - oz, vy - oy, vx - ox
    ok = (np.isfinite(fz) & np.isfinite(fy) & np.isfinite(fx)
          & (vz >= 0) & (vy >= 0) & (vx >= 0)
          & (vz < shape_vol[0] - 1) & (vy < shape_vol[1] - 1) & (vx < shape_vol[2] - 1))
    out = np.zeros(vz.shape, np.float32)
    if not ok.any():
        return out
    z, y, x = fz[ok], fy[ok], fx[ok]
    i0, j0, k0 = np.floor(z).astype(np.int64), np.floor(y).astype(np.int64), np.floor(x).astype(np.int64)
    inb = ((i0 >= 0) & (i0 < blk.shape[0] - 1) & (j0 >= 0) & (j0 < blk.shape[1] - 1)
           & (k0 >= 0) & (k0 < blk.shape[2] - 1))
    if not inb.any():
        return out
    i0, j0, k0 = i0[inb], j0[inb], k0[inb]
    dz, dy, dx = (z[inb] - i0)[:, None], (y[inb] - j0)[:, None], (x[inb] - k0)[:, None]
    b = blk.astype(np.float32)
    c00 = b[i0, j0, k0] * (1 - dx[:, 0]) + b[i0, j0, k0 + 1] * dx[:, 0]
    c01 = b[i0, j0 + 1, k0] * (1 - dx[:, 0]) + b[i0, j0 + 1, k0 + 1] * dx[:, 0]
    c10 = b[i0 + 1, j0, k0] * (1 - dx[:, 0]) + b[i0 + 1, j0, k0 + 1] * dx[:, 0]
    c11 = b[i0 + 1, j0 + 1, k0] * (1 - dx[:, 0]) + b[i0 + 1, j0 + 1, k0 + 1] * dx[:, 0]
    c0 = c00 * (1 - dy[:, 0]) + c01 * dy[:, 0]
    c1 = c10 * (1 - dy[:, 0]) + c11 * dy[:, 0]
    v = c0 * (1 - dz[:, 0]) + c1 * dz[:, 0]
    idx = np.where(ok.ravel())[0][inb]
    out.ravel()[idx] = v
    return out


def render_tile(pts, nrm, meta, vol, y0, y1, x0, x1, offs, margin=2):
    """(n_layers, h, w) uint8 plus a validity mask for one output rectangle."""
    coords, dirs, valid = coords_and_dirs(pts, nrm, meta, y0, y1, x0, x1)
    nz, h, w = len(offs), y1 - y0, x1 - x0
    out = np.zeros((nz, h, w), np.uint8)
    if not valid.any():
        return out, valid
    lo, hi = coords + dirs * offs.min(), coords + dirs * offs.max()
    todo = np.concatenate([lo[valid], hi[valid]], 0)
    if todo.size == 0 or not np.isfinite(todo).any():
        return out, valid
    mn, mx = np.nanmin(todo, 0), np.nanmax(todo, 0)     # (x, y, z)
    bx0, bx1 = int(np.floor(mn[0])) - margin, int(np.ceil(mx[0])) + margin + 1
    by0, by1 = int(np.floor(mn[1])) - margin, int(np.ceil(mx[1])) + margin + 1
    bz0, bz1 = int(np.floor(mn[2])) - margin, int(np.ceil(mx[2])) + margin + 1
    blk, org = vol.block(bz0, bz1, by0, by1, bx0, bx1)
    for i, off in enumerate(offs):
        p = coords + dirs * off
        v = trilinear(blk, org, p[..., 2], p[..., 1], p[..., 0], vol.shape)
        out[i] = np.clip(v, 0, 255).astype(np.uint8)     # truncation, not round
    return out, valid


def plan_chunks(pts, nrm, meta, shape, tile=256, n_slices=NUM_SLICES,
                chunk=CHUNK, progress=None):
    """Enumerate the exact chunk shell offline. Returns (exact_keys, bbox_keys).

    Touches the network zero times. On PHerc0009B this takes ~1.2 minutes and
    decides whether the render fits the disk budget at all.
    """
    W, H, *_ = output_geometry(pts, meta)
    offs = layer_offsets(n_slices)
    exact, box = set(), set()
    ntiles = ((H + tile - 1) // tile) * ((W + tile - 1) // tile)
    done = 0
    for y0 in range(0, H, tile):
        for x0 in range(0, W, tile):
            y1, x1 = min(y0 + tile, H), min(x0 + tile, W)
            coords, dirs, valid = coords_and_dirs(pts, nrm, meta, y0, y1, x0, x1)
            if valid.any():
                for off in offs:
                    p = coords + dirs * off
                    exact.update(chunk_keys(p[..., 2], p[..., 1], p[..., 0],
                                            shape, chunk).tolist())
                box.update(bbox_chunk_keys(coords, dirs, valid, offs, shape,
                                           chunk=chunk).tolist())
            done += 1
            if progress and done % max(1, ntiles // 20) == 0:
                progress(done, ntiles, len(exact), len(box))
    return np.array(sorted(exact), np.int64), np.array(sorted(box), np.int64)


def chunk_bytes(n, chunk=CHUNK, itemsize=1):
    return n * (chunk ** 3) * itemsize
