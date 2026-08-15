"""Incoherent line-spacing judge.

Same question as `ruler`, different projection. The ruler sums whole rows,
which assumes the lines are straight across the entire window: on a real
unwrapped surface they are not, and a few millimetres of sag cancels the very
rhythm it is looking for.

This judge tiles the rotated frame into strips (~5 mm wide) and blocks
(~35 mm tall), autocorrelates each tile *independently*, and averages the
autocorrelations weighted by valid mass. Autocorrelation discards phase, so
curved baselines add instead of cancelling.

Measured consequence (wide band 2.4-8.0 mm on real PHerc0343P substrate):
the ruler yields a usable statistic on 4.8 % of windows and needs z* = 8.0;
this judge yields one on 55.8 % and needs z* = 4.0. For wide bands, prefer
this instrument.

Nulls, thresholds and the claim rule are identical to `ruler` -- the mosaic
decides, the permutation informs.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from .ruler import (MM_PER_CELL, MOSAIC_MM, COVERAGE, P_CLAIM, Z_CLAIM,
                    _normalise, _rescale, _rotate, _span, combine, local_peak,
                    mosaic, verdict)

BAND_MM = (2.4, 7.0)
STRIP_MM = 5.0
BLOCK_MM = 35.0
ANG_STEP = (1.5, 6.0)
SMEAR = 0.15
MIN_PERIODS = 3.0     # 3.5 would put the band ceiling out of reach at 29 mm
N_PERM = N_MOS = 199  # p floor = 1/200 = 0.005 <= P_CLAIM. See note below.

_VANDER = {}


def angle_grid(strip_mm=STRIP_MM, min_period_mm=BAND_MM[0], step=ANG_STEP,
               smear=SMEAR):
    """Angles to sweep.

    Note the argument: smear is bounded by the STRIP width, not the window
    width, because each strip is autocorrelated on its own. That is why this
    judge needs 30 angles where the ruler needs 120 -- an eightfold saving that
    pays for the tiling.
    """
    d = np.rad2deg(2.0 * np.arctan(smear * min_period_mm / max(strip_mm, 1e-6)))
    d = float(np.clip(d, step[0], step[1]))
    n = int(np.ceil(180.0 / d))
    return tuple(np.round(-90.0 + 180.0 * np.arange(n) / n, 3))


def _vander(n, degree):
    key = (n, degree)
    if key not in _VANDER:
        _VANDER[key] = np.vander(np.linspace(-1.0, 1.0, n), degree + 1)
    return _VANDER[key]


class _Geom:
    """Tile geometry for one rotation angle.

    Denominators are precomputed because neither null changes the mask: the
    mosaic copies data, the permutation moves map and mask with the same index.
    Reusing them is what makes 199 x 30 null draws affordable on a laptop.
    """

    __slots__ = ("y", "x0", "x1", "xb", "idx", "den", "weight", "lag_hi", "ok",
                 "n_strips", "n_blocks", "rows", "shape")

    def __init__(self, rv, lag_lo, lag_hi_band, min_periods, strip, block):
        self.ok = False
        self.shape = rv.shape
        self.lag_hi = 0
        self.n_strips = self.n_blocks = self.rows = 0
        sp = _span(rv.sum(1))
        if sp is None:
            return
        y0, y1 = sp
        n = y1 - y0
        self.rows = n
        col = rv[y0:y1].sum(0)
        xs = np.where(col > 0.5)[0]
        if xs.size < 4:
            return
        x0, x1 = int(xs[0]), int(xs[-1]) + 1
        W = x1 - x0
        h_min = int(np.ceil(min_periods * lag_hi_band))
        nb = max(1, min(max(1, n // max(h_min, 1)),
                        max(1, int(round(n / max(block, 1))))))
        self.lag_hi = int(min(lag_hi_band, (n // nb) // min_periods))
        if self.lag_hi <= lag_lo:
            return
        nt = max(1, min(int(round(W / max(strip, 1))), W // 2))
        yb = np.linspace(y0, y1, nb + 1).astype(int)
        xb = np.linspace(x0, x1, nt + 1).astype(int)
        self.y, self.x0, self.x1, self.xb = yb, x0, x1, xb
        self.n_blocks, self.n_strips = nb, nt
        self.idx = xb[:-1] - x0
        self.den, self.weight = [], []
        for j in range(nb):
            D = np.add.reduceat(rv[yb[j]:yb[j + 1], x0:x1], self.idx, axis=1)
            rows_ok = (D > 0.5).sum(0)
            # A tile earns a vote only if it can actually resolve the band AND
            # carries enough mass for the autocorrelation to mean anything.
            use = (rows_ok >= min_periods * self.lag_hi) & (D.sum(0) >= 16 * self.lag_hi)
            self.den.append(np.maximum(D, 1e-6))
            self.weight.append(np.where(use, D.sum(0), 0.0))
        self.ok = any(float(w.sum()) > 0 for w in self.weight)

    def num(self, rb):
        return [np.add.reduceat(rb[self.y[j]:self.y[j + 1], self.x0:self.x1],
                                self.idx, axis=1)
                for j in range(self.n_blocks)]


def _detrend_multi(P, W, sigma, degree=3):
    """Weighted cubic detrend + weight-normalised high-pass, batched over tiles."""
    n = P.shape[0]
    if n > 4 * (degree + 1):
        V = _vander(n, degree)
        A = np.einsum("ni,nj,nt->tij", V, V, W, optimize=True)
        b = np.einsum("ni,nt->ti", V, P * W, optimize=True)
        A[:, np.arange(degree + 1), np.arange(degree + 1)] += 1e-9 * (
            np.trace(A, axis1=1, axis2=2)[:, None] + 1e-12)
        P = P - (V @ np.linalg.solve(A, b[:, :, None])[:, :, 0].T)
    if sigma >= 1:
        sw = ndimage.gaussian_filter1d(W, sigma=float(sigma), axis=0, mode="nearest")
        sp = ndimage.gaussian_filter1d(P * W, sigma=float(sigma), axis=0, mode="nearest")
        P = P - sp / np.maximum(sw, 1e-9)
    return P - (P * W).sum(0, keepdims=True) / np.maximum(W.sum(0, keepdims=True), 1e-9)


def _ac_multi(P, W, lag_max, guard=0.15):
    """Gap-aware autocorrelation via FFT, batched over tiles.

        ac_k = [sum_i p_i p_{i+k} w_i w_{i+k} / sum_i w_i w_{i+k}] / (same at k=0)

    The `guard` zeroes lags whose weight overlap falls below 15 % of lag 0 --
    without it, long lags across a mask gap divide by almost nothing and
    manufacture spectacular spurious peaks.
    """
    n = P.shape[0]
    nf = 1 << int(np.ceil(np.log2(2 * n)))
    X = P * W
    Fx = np.fft.rfft(X, n=nf, axis=0)
    Fw = np.fft.rfft(W, n=nf, axis=0)
    num = np.fft.irfft(Fx * np.conj(Fx), n=nf, axis=0)[:lag_max + 1]
    den = np.fft.irfft(Fw * np.conj(Fw), n=nf, axis=0)[:lag_max + 1]
    ok = den > guard * np.maximum(den[0:1], 1e-12)
    R = np.where(ok, num / np.where(ok, den, 1.0), 0.0)
    e0 = R[0:1].copy()
    R = np.where(e0 > 1e-12, R / np.maximum(e0, 1e-12), 0.0)
    return R, e0[0]


def _accumulate(Ns, Ds, g, lag_lo, detail=False):
    acc, wtot, keep = None, 0.0, []
    for j in range(g.n_blocks):
        w = g.weight[j]
        sel = np.where(w > 0)[0]
        if sel.size == 0:
            continue
        D = Ds[j][:, sel]
        Wt = np.where(D > 0.5, D, 0.0)
        P = _detrend_multi(Ns[j][:, sel] / np.maximum(D, 1e-6), Wt, g.lag_hi)
        R, den = _ac_multi(P, Wt, g.lag_hi + 2)
        R[:, den <= 1e-12] = 0.0
        ww = w[sel]
        acc = R @ ww if acc is None else acc + R @ ww
        wtot += float(ww.sum())
        if detail:
            keep.append((sel, R))
    if acc is None or wtot <= 0:
        return 0.0, 0, 0.0, None, None
    m = acc / wtot
    peak, lag, harm = local_peak(m, lag_lo, g.lag_hi)
    return peak, lag, harm, m, (keep if detail else None)


def _stat(rb, g, lag_lo, detail=False):
    if not g.ok:
        return 0.0, 0, 0.0, None, None
    return _accumulate(g.num(rb), g.den, g, lag_lo, detail)


def _stat_perm(rb, rv, g, lag_lo, rng):
    """Null 1: permute rows within each column and within each block."""
    Ns, Ds = [], []
    for j in range(g.n_blocks):
        y0, y1 = g.y[j], g.y[j + 1]
        blk = rb[y0:y1, g.x0:g.x1]
        vlk = rv[y0:y1, g.x0:g.x1]
        base = np.tile(np.arange(blk.shape[0])[:, None], (1, blk.shape[1]))
        idx = rng.permuted(base, axis=0)
        Ns.append(np.add.reduceat(np.take_along_axis(blk, idx, axis=0), g.idx, axis=1))
        Ds.append(np.maximum(np.add.reduceat(np.take_along_axis(vlk, idx, axis=0),
                                             g.idx, axis=1), 1e-6))
    return _accumulate(Ns, Ds, g, lag_lo)[0]


def _coherence(g, lag, per_tile):
    """Fraction of tiles independently peaking at the winning lag (+-1).

    Reported, never part of the claim unless calibration says so: it is a
    description of HOW the evidence is distributed, and distributions are easy
    to over-read.
    """
    if per_tile is None or not lag:
        return None
    hit = tot = 0
    for sel, R in per_tile:
        for t in range(R.shape[1]):
            ac = R[:, t]
            loc = np.where((ac[1:-1] > ac[:-2]) & (ac[1:-1] >= ac[2:]))[0] + 1
            tot += 1
            if loc.size and np.min(np.abs(loc - lag)) <= 1 and ac[lag] > 0:
                hit += 1
    return round(hit / tot, 4) if tot else None


def evaluate(field, mask=None, mm_per_cell=MM_PER_CELL, *,
             band_mm=BAND_MM, angles=None, n_perm=N_PERM, n_mos=N_MOS,
             seed=0, strip_mm=STRIP_MM, block_mm=BLOCK_MM,
             min_periods=MIN_PERIODS, mosaic_mm=MOSAIC_MM,
             mm_working=MM_PER_CELL, stride_cells=None,
             z_claim=Z_CLAIM, p_claim=P_CLAIM, detail=False):
    """Judge one map. Same contract as `ruler.evaluate`.

    n_perm = n_mos = 199 is deliberate, not arbitrary: the empirical p floor is
    1/(n+1), so with 48 draws p floors at 0.0204 and the pre-registered
    `p <= 0.01` is ARITHMETICALLY UNREACHABLE. Check the floor before running,
    not after.
    """
    b, val, med, sd = _normalise(field, mask)
    if val.sum() < 64:
        return {"instrument": "incoherence", "band_complete": False, "z": 0.0,
                "p": 1.0, "z_mos": 0.0, "p_mos": 1.0, "z_perm": 0.0,
                "p_perm": 1.0, "lag": 0, "period_mm": 0.0, "verdict": "no_data"}
    b, val, mm = _rescale(b, val, mm_per_cell, mm_working)

    lag_lo = max(3, int(round(band_mm[0] / mm)))
    lag_hi = int(round(band_mm[1] / mm))
    strip = max(4, int(round(strip_mm / mm)))
    block = max(4, int(round(block_mm / mm)))
    side = max(3, int(round(mosaic_mm / mm)))
    if b.shape[0] < 3 * lag_lo:
        return {"instrument": "incoherence", "band_complete": False, "z": 0.0,
                "p": 1.0, "z_mos": 0.0, "p_mos": 1.0, "z_perm": 0.0,
                "p_perm": 1.0, "lag": 0, "period_mm": 0.0, "verdict": "no_data"}

    if angles is None:
        angles = angle_grid(strip_mm, band_mm[0])

    v = val.astype(np.float32)
    bv = b * v
    rots, geoms = [], []
    peaks = np.zeros(len(angles))
    lags = np.zeros(len(angles), int)
    harms = np.zeros(len(angles))
    details = [None] * len(angles)
    for k, a in enumerate(angles):
        rb, rv = _rotate(bv, v, a)
        g = _Geom(rv, lag_lo, lag_hi, min_periods, strip, block)
        rots.append((rb, rv))
        geoms.append(g)
        peaks[k], lags[k], harms[k], _, details[k] = _stat(rb, g, lag_lo, detail=True)

    reach = max((g.lag_hi for g in geoms), default=0)
    reach_mm = float(reach * mm)
    band_complete = bool(reach >= lag_hi)

    rng = np.random.default_rng(seed)
    Xp = np.zeros((n_perm, len(angles)))
    for k, (rb, rv) in enumerate(rots):          # angle-major: preserves stream
        if not geoms[k].ok:
            continue
        for i in range(n_perm):
            Xp[i, k] = _stat_perm(rb, rv, geoms[k], lag_lo, rng)

    rmos = np.random.default_rng(seed + 31_337)
    Xm = np.zeros((n_mos, len(angles)))
    for i in range(n_mos):
        m = mosaic(b, val, side, side, rmos) * val
        for k, a in enumerate(angles):
            if not geoms[k].ok:
                continue
            rb, _ = _rotate(m, v, a)
            Xm[i, k] = _accumulate(geoms[k].num(rb), geoms[k].den, geoms[k], lag_lo)[0]

    _, kp, zp, pp, _ = combine(peaks, Xp)
    _, km, zm, pm, _ = combine(peaks, Xm)
    k = km if zm <= zp else kp
    lag = int(lags[k])
    g = geoms[k]
    z, p = min(zp, zm), max(pp, pm)

    out = {
        "instrument": "incoherence",
        "cells": [int(b.shape[0]), int(b.shape[1])],
        "mm_per_cell": round(float(mm), 6),
        "extent_mm": [round(b.shape[0] * mm, 2), round(b.shape[1] * mm, 2)],
        "frac_valid": round(float(val.mean()), 4),
        "band_mm": list(band_mm), "lag_band": [lag_lo, lag_hi],
        "strip_mm": strip_mm, "block_mm": block_mm,
        "n_strips": int(g.n_strips), "n_blocks": int(g.n_blocks),
        "mosaic_cells": side, "n_perm": n_perm, "n_mos": n_mos,
        "n_angles": len(angles), "angular_step_deg": round(180.0 / len(angles), 3),
        "median": round(float(med), 5), "robust_sd": round(float(sd), 5),
        "reach_mm": round(reach_mm, 3), "band_complete": band_complete,
        "peak": round(float(peaks[k]), 5), "lag": lag,
        "period_mm": round(lag * mm, 4), "angle_deg": float(angles[k]),
        "harmonic": round(float(harms[k]), 5), "rows": int(g.rows),
        "z_perm": round(zp, 4), "p_perm": round(pp, 5),
        "z_mos": round(zm, 4), "p_mos": round(pm, 5),
        "z": round(z, 4), "p": round(p, 5),
        "grid": bool(stride_cells and lag and lag % int(stride_cells) == 0),
        "frac_strips": _coherence(g, lag, details[k]),
        "seed": seed,
    }
    out["verdict"] = verdict(out, z_claim, p_claim)
    if detail:
        out["null_perm"] = Xp.max(1).tolist()
        out["null_mos"] = Xm.max(1).tolist()
    return out
