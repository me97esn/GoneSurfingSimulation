"""
Tier 2 (AC2b) correctness test for derive_wave_normals.py -- no Blender, no export.

Tier 1 (analyze_wave_normal_noise.py) only proves the normals are SMOOTH, which is gameable:
all-normals-up scores perfectly and is wrong. This proves they are CORRECT by running the
derivation on synthetic height grids whose true normal is known analytically:

  plane   constant, exactly known normal -> catches sign errors, X/Y axis swaps, step/scale bugs
  sine-Y  varying normal on the cross-shore axis -> catches over-flattening (slope amplitude)
  sine-X  a genuinely tile-periodic ridge -> proves the seam wrap keeps the normal continuous
          across the tile boundary (and that a no-seam diff does NOT)

Run:  python test_derive_wave_normals.py
"""
import numpy as np
import derive_wave_normals as D

STEP = 2.0
TILING_X = 81.79325866699219          # medium_wave_left, from wave_unified_metadata.json
PERIOD_COLS = TILING_X / STEP


def ang_err(n, ntrue):
    d = (n * ntrue).sum(-1) / (np.linalg.norm(n, axis=-1) * np.linalg.norm(ntrue, axis=-1))
    return np.degrees(np.arccos(np.clip(d, -1, 1)))


def test_plane():
    W, H, a, b = 41, 60, 0.30, -0.15
    X = np.arange(W) * STEP
    Y = np.arange(H) * STEP
    h = a * X[None, :] + b * Y[:, None]
    nx, ny, nz = D.derive(h, np.ones((H, W), bool), STEP, None)   # plane isn't periodic -> no seam wrap
    n = np.stack([nx, ny, nz], -1)
    v = np.array([-a, -b, 1.0]); ntrue = np.broadcast_to(v / np.linalg.norm(v), (H, W, 3))
    err = ang_err(n, ntrue).max()
    print(f"  plane  (a={a}, b={b}): max angle error {err:.2e} deg")
    assert err < 1e-6, f"plane normal wrong by {err} deg -- sign/axis/scale bug"
    return err


def test_sine_crossshore():
    W, H, A, L = 41, 400, 3.0, 120.0
    Y = np.arange(H) * STEP
    h = np.broadcast_to((A * np.sin(2 * np.pi * Y / L))[:, None], (H, W)).copy()
    nx, ny, nz = D.derive(h, np.ones((H, W), bool), STEP, None)
    dzdy = A * (2 * np.pi / L) * np.cos(2 * np.pi * Y / L)
    nt = np.stack([np.zeros(H), -dzdy, np.ones(H)], -1); nt /= np.linalg.norm(nt, axis=-1, keepdims=True)
    nt = np.broadcast_to(nt[:, None, :], (H, W, 3))
    err = ang_err(np.stack([nx, ny, nz], -1), nt)
    slope_got = np.sqrt(np.clip(1 - nz * nz, 0, 1))
    slope_true = np.abs(dzdy)[:, None] * np.ones_like(slope_got)
    steep = slope_true > 0.3 * slope_true.max()          # ignore near-zero-slope points (ratio ill-defined)
    ratio = (slope_got[steep] / slope_true[steep]).mean()  # central diff scales slope by sinc(k*step) ~ 0.998
    print(f"  sine-Y (L={L}, {L/STEP:.0f} pts/wave): interior max err {err[1:-1].max():.3f} deg, "
          f"slope amplitude ratio {ratio:.4f} (central-diff sinc ~0.998, not over-flattened)")
    assert err[1:-1].max() < 0.5, "over-flattening / distortion on the cross-shore axis"
    assert 0.99 < ratio < 1.01, "slope amplitude not preserved"


def test_sine_seam():
    W, H, A = 41, 40, 2.0
    X = np.arange(W) * STEP
    h = np.broadcast_to((A * np.sin(2 * np.pi * X / TILING_X))[None, :], (H, W)).copy()
    dzdx = A * (2 * np.pi / TILING_X) * np.cos(2 * np.pi * X / TILING_X)
    nt = np.stack([-dzdx, np.zeros(W), np.ones(W)], -1); nt /= np.linalg.norm(nt, axis=-1, keepdims=True)
    nt = np.broadcast_to(nt[None, :, :], (H, W, 3))
    valid = np.ones((H, W), bool)
    on = ang_err(np.stack(D.derive(h, valid, STEP, PERIOD_COLS), -1), nt)
    off = ang_err(np.stack(D.derive(h, valid, STEP, None), -1), nt)
    edge = [0, W - 1]
    print(f"  sine-X seam: edge-column err  wrap ON {on[:, edge].max():.3f} deg  vs  no-seam {off[:, edge].max():.3f} deg")
    assert on[:, edge].max() < 0.5, "seam wrap did not reproduce the analytic normal at the tile edge"
    assert off[:, edge].max() > on[:, edge].max() * 3, "expected no-seam to be clearly worse at the seam"


if __name__ == "__main__":
    print("Tier 2 correctness (analytic ground truth):")
    test_plane()
    test_sine_crossshore()
    test_sine_seam()
    print("ALL PASSED -- derivation is correct (right sign/axis/scale), not merely smooth.")
