"""Coherent line-spacing judge ("ruler").

Asks one question of a 2-D map: *does it contain a periodic line rhythm at a
physically plausible spacing?* The statistic is the peak of the unbiased 1-D
autocorrelation of the row projection, inside a physical lag band, maximised
over 180 degrees of rotation, and standardised against two independent nulls.

Why two nulls, and why the second one decides
---------------------------------------------
The obvious null for a surface volume is to permute the z-order before
projecting. It is not safe: permuting z leaves the *xy* structure of the
papyrus substrate completely intact, so a periodicity statistic computed
against it treats substrate texture as signal. Measured on bare, text-free
substrate this null reaches z = 12.24 (PHerc1203, 113 keV) and z = 16.84
(PHerc0009B, 116 keV) -- far above any sane claim threshold.

The second null is an *aperiodic block mosaic*: the map is rebuilt from
randomly sized patches copied from random positions of itself. That destroys
long-range rhythm while preserving local texture, and it holds on the same
substrates (max 2.50 and 3.52).

``evaluate`` reports both and takes the conservative merge
``z = min(z_perm, z_mos)``. Any *claim* must be decided on ``z_mos`` alone --
see ``validation/REPORT.md``.

Thresholds
----------
``Z_CLAIM`` here is a placeholder. The real threshold is calibrated per
substrate by ``scripts/calibrate_judge.py`` under the pre-registered rule

    z* = max(previously calibrated z*, ceil(max z_mos under a REAL-substrate
             null) + 1)

which puts the observed false-positive rate at 0 by construction; the honest
figure to quote is the rule-of-three upper bound ``3 / n_null``.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

# --- physical defaults (116 keV / 8.64 um scan, 16 px cells) ---------------
UM_PER_VOXEL = 8.64
CELL_PX = 16
MM_PER_CELL = UM_PER_VOXEL * CELL_PX / 1000.0        # 0.13824 mm
BAND_MM = (2.4, 6.5)          # plausible Herculaneum line spacing
ANG_STEP = (1.0, 3.0)         # min/max angular step, degrees
SMEAR = 0.15                  # tolerated end-to-end drift, in periods
MAX_ANGLES = 120              # cost cap
MIN_PERIODS = 3.5             # periods that must fit inside the window
COVERAGE = 0.35               # row kept if covered >= this fraction of max
MOSAIC_MM = 1.2               # mosaic patch side
MM_WORKING = MM_PER_CELL
Z_CLAIM = 4.0                 # PLACEHOLDER -- calibrate per substrate
P_CLAIM = 0.01


# --------------------------------------------------------------- primitives
def robust_stats(x):
    """Median and MAD-derived sigma. Falls back to std if the MAD vanishes."""
    med = float(np.median(x))
    sd = 1.4826 * float(np.median(np.abs(x - med)))
    if sd <= 1e-9:
        sd = float(np.std(x)) or 1.0
    return med, sd


def _normalise(field, mask=None):
    """Robust z-normalisation inside the mask; 0 outside."""
    a = np.asarray(field, np.float32)
    val = np.isfinite(a)
    if mask is not None:
        val &= np.asarray(mask, bool)
    if val.sum() < 8:
        return np.zeros_like(a), val, 0.0, 1.0
    med, sd = robust_stats(a[val])
    b = np.zeros_like(a)
    b[val] = (a[val] - med) / sd
    return b, val, med, sd


def _rescale(b, val, mm_in, mm_out):
    """Downsample to the working cell size. No-op unless the input is finer."""
    f = mm_in / mm_out
    if f > 0.85:
        return b, val, mm_in
    v = val.astype(np.float32)
    num = ndimage.zoom(b * v, f, order=1)
    den = ndimage.zoom(v, f, order=1)
    keep = den > 0.75
    out = np.zeros_like(num)
    out[keep] = num[keep] / den[keep]
    return out, keep, mm_out


def angle_grid(width_mm, min_period_mm, step=ANG_STEP, smear=SMEAR,
               max_angles=MAX_ANGLES):
    """Angles to sweep, spaced so end-to-end smear stays under `smear` periods.

    A line rhythm misjudged by dtheta smears the projection by
    width * tan(dtheta); requiring that to stay below `smear * period` gives
    the step below. Wider windows therefore need *finer* angular sampling.
    """
    d = np.rad2deg(2.0 * np.arctan(smear * min_period_mm / max(width_mm, 1e-6)))
    d = float(np.clip(d, step[0], step[1]))
    n = min(int(np.ceil(180.0 / d)), max_angles)
    return tuple(np.round(-90.0 + 180.0 * np.arange(n) / n, 3))


def _rotate(bv, v, ang):
    return (ndimage.rotate(bv, ang, order=1, reshape=True, cval=0.0),
            ndimage.rotate(v, ang, order=1, reshape=True, cval=0.0))


def _span(den, coverage=COVERAGE):
    """First and last row with enough valid mass. None if too few."""
    if den.size == 0 or den.max() <= 0:
        return None
    ok = den >= max(4.0, coverage * den.max())
    if ok.sum() < 8:
        return None
    y0 = int(np.argmax(ok))
    return y0, len(ok) - int(np.argmax(ok[::-1]))


def detrend(profile, sigma, degree=3):
    """Remove a cubic trend and everything slower than the band ceiling."""
    p = np.asarray(profile, np.float64)
    n = p.size
    if n > 4 * (degree + 1):
        x = np.linspace(-1.0, 1.0, n)
        p = p - np.polyval(np.polyfit(x, p, degree), x)
    if sigma >= 1:
        p = p - ndimage.gaussian_filter1d(p, sigma=float(sigma), mode="nearest")
    return p - p.mean()


def autocorr(profile, lag_max):
    """Unbiased normalised autocorrelation, ac[0] == 1."""
    x = np.asarray(profile, np.float64)
    n = x.size
    den = float((x * x).sum())
    if den < 1e-12 or n < 8:
        return None
    raw = np.correlate(x, x, mode="full")[n - 1:n + lag_max + 1]
    k = np.arange(raw.size)
    return raw * n / (den * np.maximum(n - k, 1))


def local_peak(ac, lag_lo, lag_hi):
    """Greatest STRICT local maximum in [lag_lo, lag_hi].

    Strictness matters: a monotone shoulder is not a rhythm, and taking a plain
    argmax over the band would score one.
    """
    if ac is None:
        return 0.0, 0, 0.0
    hi = int(min(lag_hi, ac.size - 2))
    if hi <= lag_lo:
        return 0.0, 0, 0.0
    c = ac[:hi + 2]
    loc = np.where((c[1:-1] > c[:-2]) & (c[1:-1] >= c[2:]))[0] + 1
    loc = loc[(loc >= lag_lo) & (loc <= hi)]
    if loc.size == 0:
        return 0.0, 0, 0.0
    i = int(loc[np.argmax(ac[loc])])
    harm = float(ac[2 * i]) if 2 * i < ac.size else 0.0
    return float(ac[i]), i, harm


def _stat(num, den, lag_lo, lag_hi_req, min_periods):
    """Statistic of one already-rotated frame -> (peak, lag, harm, lag_hi, rows)."""
    sp = _span(den)
    if sp is None:
        return 0.0, 0, 0.0, 0, 0
    y0, y1 = sp
    n = y1 - y0
    lag_hi = int(min(lag_hi_req, n // min_periods))
    if lag_hi <= lag_lo:
        return 0.0, 0, 0.0, lag_hi, n
    prof = detrend(num[y0:y1] / np.maximum(den[y0:y1], 1e-6), lag_hi)
    peak, lag, harm = local_peak(autocorr(prof, lag_hi + 2), lag_lo, lag_hi)
    return peak, lag, harm, lag_hi, n


def _sweep(b, val, angles, lag_lo, lag_hi, min_periods, cache=None):
    v = val.astype(np.float32)
    bv = b * v
    peaks = np.zeros(len(angles))
    lags = np.zeros(len(angles), int)
    harms = np.zeros(len(angles))
    hi = np.zeros(len(angles), int)
    rows = np.zeros(len(angles), int)
    for k, a in enumerate(angles):
        rb, rv = _rotate(bv, v, a)
        if cache is not None:
            cache.append((rb, rv))
        peaks[k], lags[k], harms[k], hi[k], rows[k] = _stat(
            rb.sum(1), rv.sum(1), lag_lo, lag_hi, min_periods)
    return peaks, lags, harms, hi, rows


# ------------------------------------------------------------------- nulls
def _perm_matrix(cache, lag_lo, lag_hi, min_periods, n, seed):
    """Null 1: permute rows within each column, IN THE ROTATED FRAME.

    Preserves every column's marginal and the mask exactly; destroys vertical
    ordering. This is the z-permutation analogue in projection space -- and the
    one that is NOT safe on real substrate (see module docstring).
    """
    rng = np.random.default_rng(seed)
    prep = []
    for (rb, rv) in cache:
        sp = _span(rv.sum(1))
        if sp is None:
            prep.append(None)
            continue
        y0, y1 = sp
        prep.append((np.ascontiguousarray(rb[y0:y1]),
                     np.ascontiguousarray(rv[y0:y1]),
                     np.tile(np.arange(y1 - y0)[:, None], (1, rb.shape[1]))))
    X = np.zeros((n, len(cache)))
    for i in range(n):                      # draw-major: preserves RNG stream
        for k, p in enumerate(prep):
            if p is None:
                continue
            bb, vv, base = p
            idx = rng.permuted(base, axis=0)
            X[i, k] = _stat(np.take_along_axis(bb, idx, axis=0).sum(1),
                            np.take_along_axis(vv, idx, axis=0).sum(1),
                            lag_lo, lag_hi, min_periods)[0]
    return X


def mosaic(b, val, h0, w0, rng):
    """Rebuild the map from randomly sized patches copied from random places.

    Destroys long-range rhythm, keeps local texture. Patch sides are drawn in
    [0.6*side, 1.4*side] (inclusive high). If six attempts fail to find a
    well-covered source patch the destination block keeps its original content
    rather than being filled with garbage.
    """
    H, W = b.shape
    out = b.copy()
    y = 0
    while y < H:
        hh = min(int(rng.integers(max(3, int(0.6 * h0)), max(4, int(1.4 * h0)) + 1)),
                 H - y)
        x = 0
        while x < W:
            wd = min(int(rng.integers(max(3, int(0.6 * w0)), max(4, int(1.4 * w0)) + 1)),
                     W - x)
            for _ in range(6):
                sy = int(rng.integers(0, H - hh + 1))
                sx = int(rng.integers(0, W - wd + 1))
                if val[sy:sy + hh, sx:sx + wd].mean() > 0.95:
                    out[y:y + hh, x:x + wd] = b[sy:sy + hh, sx:sx + wd]
                    break
            x += wd
        y += hh
    return out


def _mosaic_matrix(b, val, angles, lag_lo, lag_hi, min_periods, side, n, seed):
    """Null 2 (decisive): aperiodic block mosaic, swept over all angles."""
    rng = np.random.default_rng(seed + 31_337)
    v = val.astype(np.float32)
    X = np.zeros((n, len(angles)))
    for i in range(n):
        m = mosaic(b, val, side, side, rng) * val
        for k, a in enumerate(angles):
            rb, rv = _rotate(m, v, a)
            X[i, k] = _stat(rb.sum(1), rv.sum(1), lag_lo, lag_hi, min_periods)[0]
    return X


def combine(peaks, X):
    """Standardise each angle against its own null, take the max over angles.

    The observation is a max over ~120 correlated angles, so it cannot be
    compared to a per-angle null. We build the null distribution OF THAT SAME
    MAX, standardising each null draw leave-one-out so no draw is ever
    standardised against itself (which would shrink the tail and inflate z).

    Returns (T_obs, best_angle_index, z, p, T_null).
    """
    n = X.shape[0]
    mu, sd = X.mean(0), X.std(0, ddof=1)
    ok = sd > 1e-9
    t_obs = np.zeros_like(peaks)
    t_obs[ok] = (peaks[ok] - mu[ok]) / sd[ok]
    k = int(np.argmax(t_obs))
    T_obs = float(t_obs[k])
    if n < 4:
        return T_obs, k, 0.0, 1.0, np.zeros(1)
    mu_i = (n * mu - X) / (n - 1)
    var = X.var(0, ddof=1)
    sd_i = np.sqrt(np.maximum((n - 1) * var - (X - mu) ** 2 * n / (n - 1), 0.0)
                   / max(n - 2, 1))
    T = np.where(sd_i > 1e-9, (X - mu_i) / np.maximum(sd_i, 1e-9), 0.0).max(1)
    z = (T_obs - T.mean()) / T.std(ddof=1) if T.std(ddof=1) > 1e-9 else 0.0
    p = (1.0 + float((T >= T_obs).sum())) / (n + 1.0)
    return T_obs, k, float(z), float(p), T


def _thirds(rot, lag, lag_hi):
    """Autocorrelation at the winning lag, per third of the window width.

    A real rhythm survives in all three; an artifact from one seam does not.
    """
    rb, rv = rot
    W = rb.shape[1]
    out = []
    for j in range(3):
        x0, x1 = j * W // 3, (j + 1) * W // 3
        num, den = rb[:, x0:x1].sum(1), rv[:, x0:x1].sum(1)
        sp = _span(den)
        if sp is None:
            out.append(0.0)
            continue
        y0, y1 = sp
        ac = autocorr(detrend(num[y0:y1] / np.maximum(den[y0:y1], 1e-6), lag_hi),
                      lag_hi + 2)
        out.append(float(ac[lag]) if ac is not None and lag < ac.size else 0.0)
    return out


# ---------------------------------------------------------------- main API
def evaluate(field, mask=None, mm_per_cell=MM_PER_CELL, *,
             band_mm=BAND_MM, angles=None, n_perm=48, n_mos=96,
             seed=0, mm_working=MM_WORKING, min_periods=MIN_PERIODS,
             mosaic_mm=MOSAIC_MM, stride_cells=None,
             z_claim=Z_CLAIM, p_claim=P_CLAIM, detail=False):
    """Judge one map. Returns a dict; see `verdict` for the decision rule.

    Parameters
    ----------
    field : 2-D array. NaN marks invalid.
    mask : optional bool array of valid cells.
    mm_per_cell : physical size of one cell.
    band_mm : (lo, hi) plausible line spacing in mm.
    n_perm, n_mos : null draws. NOTE the arithmetic floor: the empirical p
        cannot go below 1/(n+1), so p <= 0.01 is UNREACHABLE unless n >= 99.
        Use n_mos = 199 for any run that must support a claim at p <= 0.01.
    stride_cells : if given, a winning lag that is an exact multiple of it is
        flagged as `grid` -- the reader's own tiling masquerading as text.
    """
    b, val, med, sd = _normalise(field, mask)
    if val.sum() < 64:
        return _empty(mm_per_cell, band_mm)
    b, val, mm = _rescale(b, val, mm_per_cell, mm_working)

    lag_lo = max(3, int(round(band_mm[0] / mm)))
    lag_hi = int(round(band_mm[1] / mm))
    side = max(3, int(round(mosaic_mm / mm)))
    if b.shape[0] < 3 * lag_lo:
        return _empty(mm_per_cell, band_mm)

    if angles is None:
        angles = angle_grid(min(b.shape) * mm, band_mm[0])

    cache = []
    peaks, lags, harms, his, rows = _sweep(b, val, angles, lag_lo, lag_hi,
                                           min_periods, cache)
    reach_mm = float(his.max() * mm) if len(his) else 0.0
    band_complete = bool(his.max() >= lag_hi) if len(his) else False

    Xp = _perm_matrix(cache, lag_lo, lag_hi, min_periods, n_perm, seed)
    Xm = _mosaic_matrix(b, val, angles, lag_lo, lag_hi, min_periods, side,
                        n_mos, seed)
    _, kp, zp, pp, _ = combine(peaks, Xp)
    _, km, zm, pm, _ = combine(peaks, Xm)
    k = km if zm <= zp else kp

    lag = int(lags[k])
    z, p = min(zp, zm), max(pp, pm)
    out = {
        "instrument": "ruler",
        "cells": [int(b.shape[0]), int(b.shape[1])],
        "mm_per_cell": round(float(mm), 6),
        "extent_mm": [round(b.shape[0] * mm, 2), round(b.shape[1] * mm, 2)],
        "frac_valid": round(float(val.mean()), 4),
        "band_mm": list(band_mm),
        "lag_band": [lag_lo, lag_hi],
        "mosaic_cells": side,
        "n_perm": n_perm, "n_mos": n_mos,
        "n_angles": len(angles),
        "angular_step_deg": round(180.0 / len(angles), 3),
        "median": round(float(med), 5), "robust_sd": round(float(sd), 5),
        "reach_mm": round(reach_mm, 3),
        "band_complete": band_complete,
        "peak": round(float(peaks[k]), 5),
        "lag": lag,
        "period_mm": round(lag * mm, 4),
        "angle_deg": float(angles[k]),
        "harmonic": round(float(harms[k]), 5),
        "rows": int(rows[k]),
        "z_perm": round(zp, 4), "p_perm": round(pp, 5),
        "z_mos": round(zm, 4), "p_mos": round(pm, 5),
        "z": round(z, 4), "p": round(p, 5),
        "grid": bool(stride_cells and lag and lag % int(stride_cells) == 0),
        "ac_thirds": [round(v, 4) for v in _thirds(cache[k], lag, int(his[k]))]
        if lag else [0.0, 0.0, 0.0],
        "seed": seed,
    }
    out["verdict"] = verdict(out, z_claim, p_claim)
    if detail:
        out["per_angle"] = [[float(a), float(peaks[i]), int(lags[i]),
                             int(his[i]), int(rows[i])]
                            for i, a in enumerate(angles)]
        out["null_perm"] = Xp.max(1).tolist()
        out["null_mos"] = Xm.max(1).tolist()
    return out


def _empty(mm, band_mm):
    return {"instrument": "ruler", "band_complete": False, "z": 0.0, "p": 1.0,
            "z_perm": 0.0, "p_perm": 1.0, "z_mos": 0.0, "p_mos": 1.0,
            "peak": 0.0, "lag": 0, "period_mm": 0.0, "mm_per_cell": mm,
            "band_mm": list(band_mm), "verdict": "no_data"}


def verdict(r, z_claim=Z_CLAIM, p_claim=P_CLAIM):
    """Decision rule.

    `inconclusive_extent` is a first-class outcome, not a failure: if the
    window is too small to fit `min_periods` of the band ceiling, a null result
    carries no information and must not be reported as absence of text.
    """
    if not r.get("band_complete"):
        return "inconclusive_extent"
    if r["z"] >= z_claim and r["p"] <= p_claim:
        return "grid_artifact" if r.get("grid") else "LINES"
    if r["z"] >= 0.7 * z_claim:
        return "marginal"
    return "negative"
