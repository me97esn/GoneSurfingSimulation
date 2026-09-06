"""
Re-derive wave normals (nx/ny/nz) from the sampled height grid, as a post-pass over exported
per-frame JSON. Implements SPEC_wave_normal_noise Option A, correctly for THIS pipeline:

  - normals = central differences of h  (triangulation-independent -> kills the temporal jitter
    that ray_cast face-normals produce when FLIP re-meshes every frame)
  - trim axis (Y / rows here): dead 'no-hit' cells (nx=ny=0, nz=1, h=0) are never differenced
    across; the valid-edge cell uses a one-sided difference; dead cells stay up-normal
  - tiling axis (X / cols here): at the seam we currently fall back to a one-sided difference.
    A fully seamless version pads with the neighbour frame (frame_offset) -- see --neighbour-dir;
    without it, only the 1-2 seam columns are approximate, the interior (the headline fix) is exact.

Writes new wave_data_frame_*.json with h and velocity untouched and only nx/ny/nz replaced.

Usage:
    python derive_wave_normals.py <in_dir> <out_dir> [--limit N] [--tiling-axis x|y]

Validate:
    python analyze_wave_normal_noise.py <in_dir> --compare <out_dir>
"""
import json
import os
import re
import sys

import numpy as np


def load_frames(path, limit=None):
    paths = [os.path.join(path, f) for f in os.listdir(path)
             if re.match(r"wave_data_frame_-?\d+\.json$", f)]
    paths.sort(key=lambda p: int(re.search(r"(-?\d+)\.json$", p).group(1)))
    return paths[:limit] if limit else paths


def valid_mask(data, w, hgt):
    nx = np.asarray(data["nx"], float).reshape(hgt, w)
    ny = np.asarray(data["ny"], float).reshape(hgt, w)
    nz = np.asarray(data["nz"], float).reshape(hgt, w)
    return ~((nx == 0.0) & (ny == 0.0) & (nz == 1.0))


def masked_deriv(h, valid, step, axis):
    """
    Central difference along `axis`, but never crossing an invalid cell.
    Both neighbours valid -> central; one valid -> one-sided; neither -> nan.
    This handles both the dead trim border and (as a fallback) the tiling seam.
    """
    hh = np.where(valid, h, np.nan)
    fwd = np.full_like(h, np.nan)   # h[i+1] - h[i]
    bwd = np.full_like(h, np.nan)   # h[i]   - h[i-1]
    if axis == 0:
        fwd[:-1, :] = hh[1:, :] - hh[:-1, :]
        bwd[1:, :] = hh[1:, :] - hh[:-1, :]
    else:
        fwd[:, :-1] = hh[:, 1:] - hh[:, :-1]
        bwd[:, 1:] = hh[:, 1:] - hh[:, :-1]
    fwd_s, bwd_s = fwd / step, bwd / step
    both = ~np.isnan(fwd_s) & ~np.isnan(bwd_s)
    return np.where(both, (fwd_s + bwd_s) / 2.0,
                    np.where(~np.isnan(fwd_s), fwd_s,
                             np.where(~np.isnan(bwd_s), bwd_s, np.nan)))


def tiling_deriv_x(h, valid, step, period_cols):
    """
    d/dx on the tiling axis (X = columns), made seamless by a WITHIN-FRAME periodic wrap.
    Each exported frame is one self-contained tile of period `tiling_x`; the game repeats it, so
    the sample just past the +X edge is the frame's own -X side, one period back. period_cols is
    tiling_x/step and is fractional (~40.9 for a 41-wide grid), so the wrapped column is
    interpolated. Where a wrapped/neighbour cell is invalid, falls back to a one-sided difference.
    """
    H, W = h.shape

    def col_at(f):
        f = f % period_cols
        lo = max(0, min(W - 2, int(np.floor(f))))
        fr = f - lo
        return h[:, lo] * (1 - fr) + h[:, lo + 1] * fr, valid[:, lo] & valid[:, lo + 1]

    pad_l, vl = col_at(-1.0 + period_cols)   # periodic image of column -1
    pad_r, vr = col_at(float(W) - period_cols)  # periodic image of column W
    ha = np.concatenate([pad_l[:, None], h, pad_r[:, None]], axis=1)
    va = np.concatenate([vl[:, None], valid, vr[:, None]], axis=1)
    return masked_deriv(ha, va, step, axis=1)[:, 1:-1]


def derive(h, valid, step, period_cols=None):
    if period_cols is not None:
        dzdx = tiling_deriv_x(h, valid, step, period_cols)
    else:
        dzdx = masked_deriv(h, valid, step, axis=1)
    dzdy = masked_deriv(h, valid, step, axis=0)
    n = np.stack([-dzdx, -dzdy, np.ones_like(h)], axis=-1)
    norm = np.linalg.norm(n, axis=-1, keepdims=True)
    n = np.divide(n, norm, out=np.zeros_like(n), where=norm > 0)
    # dead cells (nan gradient) -> flat up-normal, matching the exporter's miss default
    dead = np.isnan(dzdx) | np.isnan(dzdy)
    nx = np.where(dead, 0.0, n[..., 0])
    ny = np.where(dead, 0.0, n[..., 1])
    nz = np.where(dead, 1.0, n[..., 2])
    return nx, ny, nz


def main():
    args = sys.argv[1:]
    limit = None
    if "--limit" in args:
        i = args.index("--limit"); limit = int(args[i + 1]); del args[i:i + 2]
    if "--tiling-axis" in args:  # accepted for forward-compat; masked_deriv is axis-symmetric
        i = args.index("--tiling-axis"); del args[i:i + 2]
    seam = "--no-seam" not in args
    if not seam:
        args.remove("--no-seam")
    if len(args) < 2:
        print(__doc__); sys.exit(1)
    in_dir, out_dir = args[0], args[1]
    os.makedirs(out_dir, exist_ok=True)

    # tiling_x / step -> fractional tile period in columns, for the seamless X wrap
    period_cols = None
    meta_path = os.path.join(in_dir, "wave_unified_metadata.json")
    if seam and os.path.isfile(meta_path):
        meta = json.load(open(meta_path))
        m = meta[0] if isinstance(meta, list) else meta
        period_cols = float(m["tiling_x"]) / float(m["step_size"])
        print(f"Seamless X wrap ON: period_cols = {period_cols:.3f}")
    elif seam:
        print("Seamless X wrap ON but no metadata found; using integer grid-width wrap")

    paths = load_frames(in_dir, limit)
    if not paths:
        print(f"No wave_data_frame_*.json in {in_dir}"); sys.exit(1)

    for p in paths:
        with open(p) as fh:
            d = json.load(fh)
        w, hgt = d["grid"]["width"], d["grid"]["height"]
        step = d["grid"]["step"]
        h = np.asarray(d["data"]["h"], float).reshape(hgt, w)
        valid = valid_mask(d["data"], w, hgt)
        pc = period_cols if period_cols is not None else (float(w) if seam else None)
        nx, ny, nz = derive(h, valid, step, pc)
        d["data"]["nx"] = nx.reshape(-1).tolist()
        d["data"]["ny"] = ny.reshape(-1).tolist()
        d["data"]["nz"] = nz.reshape(-1).tolist()
        with open(os.path.join(out_dir, os.path.basename(p)), "w") as fh:
            json.dump(d, fh)
    print(f"Wrote {len(paths)} frames with re-derived normals to {out_dir}")


if __name__ == "__main__":
    main()
