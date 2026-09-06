"""
Identify which grid axis the wave tiles along, straight from the exported frame JSON.

The Blender->Unreal export may rotate axes, so we must NOT trust Blender's blend-axis or
any metadata default. Instead we identify the tiling axis in the SAME grid space the game
and the normal-derivation operate in -- the reshaped h array -- which makes the result
independent of whatever rotation the export applied.

The tiling axis is the axis the wave CREST runs along. Two independent signatures, from the
user's description ("the crest spans a tile side to side and continues into the next tile"):

  1. anisotropy   The crest is a ridge: height changes most steeply PERPENDICULAR to it
                  (cross-shore trough->crest->back) and least ALONG it. So the tiling axis is
                  the axis with the SMALLER mean |dh|.
  2. continuity   The crest exits and re-enters at the seam, so along the tiling axis the crest
                  stays high at BOTH end edges. Along the cross-shore axis the profile is a
                  single interior peak that falls off at the edges.

If the two signatures agree, trust it. If they disagree, the grid is not a clean crest-aligned
tile and someone should look at the height field by eye before deriving normals.

Usage:
    python detect_tiling_axis.py <dir-or-frame.json> [--limit N]
"""
import json
import os
import re
import sys

import numpy as np

AXIS_NAME = {0: "Y / rows (the 'height'/start_y index)",
             1: "X / cols (the 'width'/start_x index)"}


def load_frames(path, limit=None):
    if os.path.isfile(path):
        paths = [path]
    else:
        paths = [os.path.join(path, f) for f in os.listdir(path)
                 if re.match(r"wave_data_frame_-?\d+\.json$", f)]
    frames = []
    for p in paths:
        with open(p) as fh:
            d = json.load(fh)
        frames.append((int(d["frame"]), d["grid"], d["data"]))
    frames.sort(key=lambda t: t[0])
    return frames[:limit] if limit else frames


def valid_mask(data, w, hgt):
    """Cells where a ray hit. A miss leaves the exporter's init: nx=ny=0, nz=1, h=0."""
    nx = np.asarray(data["nx"], float).reshape(hgt, w)
    ny = np.asarray(data["ny"], float).reshape(hgt, w)
    nz = np.asarray(data["nz"], float).reshape(hgt, w)
    miss = (nx == 0.0) & (ny == 0.0) & (nz == 1.0)
    return ~miss


def masked_grad_mean(h, valid, axis):
    """Mean |dh| between adjacent cells along `axis`, counting only pairs where both are valid."""
    dh = np.abs(np.diff(h, axis=axis))
    n = h.shape[axis]
    va = np.take(valid, range(0, n - 1), axis=axis)   # first endpoint of each adjacent pair
    vb = np.take(valid, range(1, n), axis=axis)        # second endpoint
    vals = dh[va & vb]
    return float(vals.mean()) if vals.size else float("nan")


def crest_edge_continuity(h, valid, tiling_axis):
    """
    If `tiling_axis` is the true tiling axis, the crest exits at both its ends. Measure how high
    the surface still is at the two extreme lines along that axis, relative to that line's own
    trough-to-crest range. ~1.0 means 'crest present at the edge'; ~0.0 means 'edge is at trough'.
    Returns (edge_lo_score, edge_hi_score).
    """
    hm = np.where(valid, h, np.nan)

    def line(idx):
        return np.take(hm, idx, axis=tiling_axis)

    def score(edge_line):
        # the perpendicular profile at this edge: is its max near the global crest height?
        finite = edge_line[np.isfinite(edge_line)]
        if finite.size < 2:
            return float("nan")
        lo, hi = np.nanmin(hm), np.nanmax(hm)
        rng = hi - lo
        return float((np.nanmax(edge_line) - lo) / rng) if rng > 0 else float("nan")

    n = h.shape[tiling_axis]
    return score(line(0)), score(line(n - 1))


def main():
    args = sys.argv[1:]
    limit = None
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        print(__doc__)
        sys.exit(1)

    frames = load_frames(args[0], limit)
    if not frames:
        print(f"No wave_data_frame_*.json found at {args[0]}")
        sys.exit(1)

    grad = {0: [], 1: []}
    cont = {0: [], 1: []}
    for _, grid, data in frames:
        w, hgt = grid["width"], grid["height"]
        h = np.asarray(data["h"], float).reshape(hgt, w)
        valid = valid_mask(data, w, hgt)
        for ax in (0, 1):
            grad[ax].append(masked_grad_mean(h, valid, ax))
            cont[ax].append(crest_edge_continuity(h, valid, ax))

    g0, g1 = np.nanmean(grad[0]), np.nanmean(grad[1])
    tiling_by_grad = 0 if g0 < g1 else 1          # smaller gradient = along-crest = tiling axis
    ratio = max(g0, g1) / min(g0, g1) if min(g0, g1) > 0 else float("inf")

    c0 = np.nanmean(cont[0], axis=0)              # (lo, hi) continuity if axis 0 were tiling
    c1 = np.nanmean(cont[1], axis=0)
    tiling_by_cont = 0 if np.nanmin(c0) > np.nanmin(c1) else 1

    print(f"\n  frames analysed: {len(frames)}   grid {w}x{hgt} (cols x rows)\n")
    print("  (1) gradient anisotropy  -- tiling axis has the SMALLER mean |dh|")
    print(f"      mean |dh| along {AXIS_NAME[0]:<40} = {g0:.4f}")
    print(f"      mean |dh| along {AXIS_NAME[1]:<40} = {g1:.4f}")
    print(f"      -> tiling axis = {AXIS_NAME[tiling_by_grad]}   (anisotropy ratio {ratio:.1f}x)\n")
    print("  (2) crest continuity at seam -- tiling axis keeps the crest high at BOTH end edges")
    print(f"      axis 0 as tiling: edge scores lo={c0[0]:.2f} hi={c0[1]:.2f}  (min {np.nanmin(c0):.2f})")
    print(f"      axis 1 as tiling: edge scores lo={c1[0]:.2f} hi={c1[1]:.2f}  (min {np.nanmin(c1):.2f})")
    print(f"      -> tiling axis = {AXIS_NAME[tiling_by_cont]}\n")

    if tiling_by_grad == tiling_by_cont:
        print(f"  VERDICT: both signatures agree -> tile along {AXIS_NAME[tiling_by_grad]}")
    else:
        print("  VERDICT: signatures DISAGREE -- the grid is not a clean crest-aligned tile.")
        print("           Inspect the height field by eye before deriving normals.")


if __name__ == "__main__":
    main()
