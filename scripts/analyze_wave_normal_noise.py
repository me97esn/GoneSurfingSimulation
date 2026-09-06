"""
Measure noise in exported wave normals, straight from the unified frame JSON.

This is the verification tool for SPEC_wave_normal_noise.md. It needs no Blender and no Unreal --
it reads what the exporter wrote, so a fix can be judged on a handful of frames instead of a full
export plus an import round-trip.

Reports four things:

  spatial     |slope change| between ADJACENT grid points, along X and along Y.
  temporal    |slope change| at the SAME grid point between CONSECUTIVE frames. This is the
              headline number: in-game measurements showed the temporal term dominating (0.1012 on
              ticks where the animation frame advanced vs 0.0311 where it did not).
  height      the same two metrics for the height channel, as a control. Heights come from
              ray-plane intersection and are already clean; they should not move when normals are
              fixed. If they do, something else changed.
  consistency angle between the STORED normal and the normal implied by central differences on the
              stored heights. The game bilinearly interpolates h and reads slope from the normal, so
              these describing different surfaces is itself a defect. Near zero after Option A.

Usage:
    python analyze_wave_normal_noise.py <dir-or-frame.json> [...]
    python analyze_wave_normal_noise.py <before_dir> --compare <after_dir>

Examples:
    python analyze_wave_normal_noise.py /hdd/gone_surfing_exports/medium_wave_left/unified
    python analyze_wave_normal_noise.py old/unified --compare new/unified
"""
import json
import os
import re
import sys

import numpy as np


def load_frames(path, limit=None):
    """Return [(frame_number, grid_dict, arrays_dict), ...] sorted by frame number."""
    if os.path.isfile(path):
        paths = [path]
    else:
        paths = [
            os.path.join(path, f)
            for f in os.listdir(path)
            if re.match(r"wave_data_frame_-?\d+\.json$", f)
        ]
    frames = []
    for p in paths:
        with open(p) as fh:
            d = json.load(fh)
        frames.append((int(d["frame"]), d["grid"], d["data"]))
    frames.sort(key=lambda t: t[0])
    if limit:
        frames = frames[:limit]
    return frames


def as_grids(grid, data):
    """Reshape the flat arrays into (height, width) grids. Returns (h, slope)."""
    w, hgt = grid["width"], grid["height"]
    h = np.asarray(data["h"], dtype=float).reshape(hgt, w)
    nz = np.asarray(data["nz"], dtype=float).reshape(hgt, w)
    # Same definition the game uses: slopeSin = sqrt(1 - nz^2).
    slope = np.sqrt(np.clip(1.0 - nz * nz, 0.0, 1.0))
    return h, slope


def stats(diffs):
    a = np.abs(diffs)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return dict(mean=float("nan"), p95=float("nan"), mx=float("nan"), frac=float("nan"))
    return dict(mean=a.mean(), p95=np.percentile(a, 95), mx=a.max(), frac=100.0 * (a > 0.05).mean())


def normal_from_heights(h, step):
    """Central-difference normal of the height grid -- what Option A would export."""
    dzdy, dzdx = np.gradient(h, step, step)      # np.gradient returns (d/drow, d/dcol)
    n = np.stack([-dzdx, -dzdy, np.ones_like(h)], axis=-1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def analyse(path, label, limit=None):
    frames = load_frames(path, limit)
    if not frames:
        print(f"  {label}: no wave_data_frame_*.json found at {path}")
        return None
    step = frames[0][1]["step"]
    w, hgt = frames[0][1]["width"], frames[0][1]["height"]

    sx, sy, hx, cons = [], [], [], []
    slope_prev = h_prev = None
    st, ht = [], []

    for _, grid, data in frames:
        h, slope = as_grids(grid, data)

        sx.append(np.diff(slope, axis=1).ravel())        # adjacent along X
        sy.append(np.diff(slope, axis=0).ravel())        # adjacent along Y
        hx.append(np.diff(h, axis=1).ravel())

        nz_stored = np.asarray(data["nz"], dtype=float).reshape(hgt, w)
        nx_stored = np.asarray(data["nx"], dtype=float).reshape(hgt, w)
        ny_stored = np.asarray(data["ny"], dtype=float).reshape(hgt, w)
        stored = np.stack([nx_stored, ny_stored, nz_stored], axis=-1)
        norm = np.linalg.norm(stored, axis=-1, keepdims=True)
        stored = np.divide(stored, norm, out=np.zeros_like(stored), where=norm > 1e-9)
        implied = normal_from_heights(h, step)
        dot = np.clip((stored * implied).sum(axis=-1), -1.0, 1.0)
        cons.append(np.degrees(np.arccos(dot)).ravel())

        if slope_prev is not None:
            st.append((slope - slope_prev).ravel())
            ht.append((h - h_prev).ravel())
        slope_prev, h_prev = slope, h

    print(f"\n  {label}  ({len(frames)} frames, grid {w}x{hgt}, step {step})")
    print(f"    {'metric':<34}{'mean':>10}{'p95':>10}{'max':>10}{'>0.05':>9}")
    for name, d in (
        ("slope, adjacent in X", stats(np.concatenate(sx))),
        ("slope, adjacent in Y", stats(np.concatenate(sy))),
        ("slope, SAME POINT next frame", stats(np.concatenate(st)) if st else None),
        ("height, adjacent in X (control)", stats(np.concatenate(hx))),
        ("height, same point next frame", stats(np.concatenate(ht)) if ht else None),
    ):
        if d is None:
            print(f"    {name:<34}{'(needs 2+ frames)':>39}")
            continue
        print(f"    {name:<34}{d['mean']:>10.4f}{d['p95']:>10.4f}{d['mx']:>10.4f}{d['frac']:>8.1f}%")

    c = np.concatenate(cons)
    print(f"    {'stored vs height-implied normal':<34}{c.mean():>9.2f}°{np.percentile(c,95):>9.2f}°{c.max():>9.2f}°")
    return True


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        sys.exit(1)
    limit = None
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i : i + 2]

    if "--compare" in args:
        i = args.index("--compare")
        before, after = args[:i], args[i + 1 :]
        print("=== BEFORE ===")
        for p in before:
            analyse(p, os.path.basename(p.rstrip("/\\")) or p, limit)
        print("\n=== AFTER ===")
        for p in after:
            analyse(p, os.path.basename(p.rstrip("/\\")) or p, limit)
        print("\n  AC1: 'slope, adjacent in X' mean should fall well below the before value.")
        print("  AC2: 'slope, SAME POINT next frame' is the headline -- it should fall the most.")
        print("  AC4: the two height rows must be unchanged.")
    else:
        for p in args:
            analyse(p, os.path.basename(p.rstrip("/\\")) or p, limit)


if __name__ == "__main__":
    main()
