# Specification: Fix Noisy Wave Normals in the Unified Export

## Status (updated 2026-09-06)

**Option A is confirmed and measured on real data.** It is implemented not inside
`sample_unified_grid()` as originally proposed, but as a **separate post-pass**,
`derive_wave_normals.py`, over the exported per-frame JSON — matching the architecture already
used for seam blending (kept separate so it can be re-run without a multi-hour re-export).

Measured on `medium_wave_left`, 20 frames, via `analyze_wave_normal_noise.py --compare`:

| metric | before (ray_cast) | after (Option A) | change |
|---|---|---|---|
| slope, same point next frame (AC2, headline) | 0.0155 | 0.0053 | **−66%** |
| slope, adjacent in X (AC1) | 0.0209 | 0.0091 | −56% |
| slope, adjacent in Y | 0.0299 | 0.0166 | −44% |
| height (AC4 control) | — | unchanged | ✓ |
| stored-vs-implied normal, max | **179.99°** | 88.55° (edges only) | flips gone |

Diagnosis (measured, and note the correction — do **not** chase the flips):

- The dominant cause is the **re-triangulation jitter of flat face normals** (the FLIP surface
  re-meshes every frame, so a fixed point lands on a differently-tilted triangle). This is the
  spec's original point #1 and it drives ~97% of the noise.
- The `nz<0` "flipped" normals (winding inside/outside inconsistency) are real but only **0.43%**
  of cells. Fixing them — e.g. Blender `normals_make_consistent(inside=False)` / "recompute
  outside" — does **nothing** for the in-game signal: slope is `sqrt(1−nz²)`, sign-invariant, so
  forcing normals up leaves temporal `|Δslope|` unchanged (0.0299 → 0.0299). Even normal *direction*
  jitter barely improves (3.75° → 3.10°), because it too is re-mesh tilt, not flips. Proof: slope
  jitter among never-flipping cells is 0.0297, ≈ the all-cells 0.0299.
- Option A moots the flips anyway: `n = (−dz/dx, −dz/dy, 1)` always has `nz>0`, so it is flip-free
  by construction *and* kills the tilt jitter (temporal `|Δslope|` → 0.0099, direction → 0.84°).

**Tiling axis is X (grid columns), confirmed rotation-proof** by `detect_tiling_axis.py` (crest
runs along X; cross-shore/steep face is Y). The Blender→Unreal export rotates axes, so this was
measured in grid space, not inferred from labels. See the corrected Open Question below.

**Correctness (Tier 2 / AC2b) — passed.** `test_derive_wave_normals.py` runs the derivation on
synthetic grids with analytic normals: tilted plane (max error 0.00° — sign/axis/scale correct),
cross-shore sine (slope amplitude ratio 0.991 = expected `sinc(k·step)`, not over-flattened),
tile-periodic sine (seam-edge error 0.040° with the wrap vs 0.124° without). This is the gate that
Tier 1 smoothness cannot provide, since all-normals-up passes Tier 1 and is wrong.

**Seam handling (done, measured).** Each exported frame is *already* one self-contained tile of
period `tiling_x` — `create_joined_blended_mesh` blends frame N with frame N−`frame_offset` while
building it. So the game tiles by **repeating a frame periodically**, and the seam pad is a
**within-frame periodic wrap** (`tiling_deriv_x`), not a neighbour frame. Verified from data: the
N±`frame_offset` frame is the *worst* spatial match at the seam (mean Δ ~2.0 vs ~1.1 for the self
wrap). On the breaking frames the seam jump between tiled copies drops from **0.137→0.047 mean,
0.392→0.102 p95** with the wrap on; a one-sided fallback leaves it at 0.101 (≈ unchanged). The
period is fractional (`tiling_x/step ≈ 40.9`, not 41), so the wrapped column is interpolated.

## Problem Statement

The `nx/ny/nz` arrays in `wave_unified_data` are **noisy in space and, much worse, in time**. The
heights in the same export are clean. Consumers in the game read the normal to derive wave slope,
and that slope signal jitters far beyond anything the wave shape can justify.

Measured in the game (`GoneSurfingUE5`, shortboard on the `surfing-down-the-line` autopilot, fixed
60 fps — see `GoneSurfing/specs/flat-water-propulsion-audit.md`):

| measurement | value |
|---|---|
| slope change between **adjacent grid points** in the exported data | mean 0.0368, max 0.3612 |
| adjacent pairs differing by more than 0.05 | 12.5% |
| slope change per game tick, board moving ~12 cm (~0.2 of a grid cell) | **0.0992** |
| …on ticks where the sampled animation frame advanced | **0.1012** |
| …on ticks where it did not | **0.0311** |
| slope change 12 cm of movement should produce, from the data's own gradient | ~0.008 |

Two conclusions:

1. **The dominant term is temporal.** Slope moves ~3x more when the animation frame advances than
   when it does not. The wave surface at a *fixed point* changes far more between consecutive frames
   than the water itself plausibly does at 24 fps.
2. The spatial term is real too — the exported grid's own adjacent-point differences are large
   enough to matter at 56 cm spacing.

### Why this surfaced now

The game used to have a propulsion term that did not depend on wave slope at all, which swamped the
noise. That term was recently gated to the wave face (correctly — it was driving the board on flat
water and behind the crest), so **every remaining propulsion force is now slope-proportional** and
follows this signal directly. The result is a board that surges and brakes several times a second
instead of gliding. The consumer change was right; it exposed a pre-existing data problem.

The fix belongs here, not in the consumer. Smoothing the slope signal in the game would hide a
faceting artefact behind a filter and leave the data wrong for every other reader.

## Root Cause

`export_waves_display.py`, `sample_unified_grid()`:

```python
hit, location, normal, face_idx = mesh_obj.ray_cast(ray_origin_local, ray_dir)

i = y_idx * width + x_idx
if hit:
    h[i] = float(location.z)      # continuous across the surface
    normal.normalize()
    nx[i] = float(normal.x)       # FLAT FACE NORMAL of the triangle that was hit
    ny[i] = float(normal.y)
    nz[i] = float(normal.z)
```

`Object.ray_cast()` returns the **face normal of the hit polygon**, not an interpolated smooth
normal. That produces exactly the two symptoms measured:

- **Spatially:** the FLIP surface is an irregular triangle mesh. Grid samples 56 cm apart routinely
  land on different triangles, and a face normal is piecewise-constant, discontinuous at every
  triangle edge. Neighbouring samples therefore disagree by however much the local triangulation
  happens to vary.
- **Temporally:** FLIP re-meshes every frame. The triangulation at a fixed world point is completely
  different from one frame to the next, so the face normal jumps even when the true surface barely
  moved. This is why the temporal term dominates.

It also explains the asymmetry: `location.z` is a ray-plane intersection, which is continuous across
a triangulated surface, so **heights are clean while normals are not**.

Nothing downstream repairs this — `merge_unified_wave_data.py` passes `nx/ny/nz` through verbatim
into the UE datatable.

## Goal

Exported normals that vary smoothly in space and in time, so that a consumer reading wave slope at a
moving point sees the wave's shape rather than the mesh's triangulation. No change to the export
format, the grid, or any consumer.

## Proposed Solution

### Option A — derive normals from the sampled height grid (recommended, IMPLEMENTED)

> **As built (`derive_wave_normals.py`).** Runs as a post-pass over the exported per-frame JSON,
> not inside `sample_unified_grid()`. Two corrections the original pseudocode below omits, both
> required by this pipeline and both found the hard way:
>
> 1. **Invalid/dead cells must not be differenced across.** A missed ray leaves the exporter's
>    init (`nx=ny=0, nz=1, h=0`); the large `offset_y` trim border on the **Y axis** is all such
>    cells. `masked_deriv()` uses a central difference only where both neighbours are valid, a
>    one-sided difference at the valid edge, and leaves dead cells as flat up-normal. Blindly
>    indexing `h` (as below) produces a huge false slope at the valid boundary — exactly where the
>    rideable face is.
> 2. **The tiling seam (X axis) needs a periodic wrap.** The seam blend is C0 (position only —
>    `create_joined_blended_mesh` / `apply_seamless_blending` both `smoothstep`-lerp positions,
>    never tangents), so a naive one-sided difference at the X-edge does **not** match the next
>    tile's slope → a coherent slope discontinuity repeating at every tile boundary. Because each
>    frame is one full period and the game repeats it, `tiling_deriv_x` pads the X-edges with the
>    frame's *own* opposite side one period back (fractional column, `tiling_x/step ≈ 40.9`), so
>    the tiled copies join smoothly. Do **not** pad with frame `N ± frame_offset` — measurement
>    shows that is the worst match; that offset is already consumed building the frame's tile.
>
> The verification tooling is `detect_tiling_axis.py` (which axis tiles) and
> `analyze_wave_normal_noise.py` (before/after metrics + a seam-column check).

Original pseudocode (correct in spirit, seam- and mask-naive):

After the ray-cast pass fills `h`, compute normals by central differences on that grid instead of
taking them from `ray_cast`:

```python
# after the sampling loop, h[] is populated
for y_idx in range(height):
    for x_idx in range(width):
        i = y_idx * width + x_idx
        xm = h[y_idx * width + max(x_idx - 1, 0)]
        xp = h[y_idx * width + min(x_idx + 1, width - 1)]
        ym = h[max(y_idx - 1, 0) * width + x_idx]
        yp = h[min(y_idx + 1, height - 1) * width + x_idx]
        # divisor is 2*step for interior points, step at a clamped edge
        dzdx = (xp - xm) / (step * (2 if 0 < x_idx < width - 1 else 1))
        dzdy = (yp - ym) / (step * (2 if 0 < y_idx < height - 1 else 1))
        n = Vector((-dzdx, -dzdy, 1.0)).normalized()
        nx[i], ny[i], nz[i] = n.x, n.y, n.z
```

Why this is the right shape for this pipeline:

- The game **bilinearly interpolates `h`** and reads slope from the normal. Deriving the normal as
  the gradient of that same field makes the two **self-consistent** — the normal is the true normal
  of the surface the game actually reconstructs, which is not true today.
- It is **independent of triangulation**, so both the spatial faceting and the frame-to-frame
  re-meshing jitter disappear together.
- It **cannot lose detail the game could have used**: the consumer never sees finer than the 56 cm
  grid, so a normal describing that grid is all the information there is to carry.

Trade-off: genuinely sharp features smaller than the grid (the lip of a breaking wave) get averaged
into the cell rather than reported from one triangle. That is a faithful representation of the
resolution actually being exported, not a loss.

### Option B — interpolate the mesh's smooth normal at the hit point

Barycentrically blend the hit triangle's vertex normals using `location` within
`mesh.loops[...].normal`. Faithful to the source mesh and keeps sub-cell detail, but:

- it still inherits frame-to-frame re-triangulation, so it reduces the temporal term rather than
  removing it — and the temporal term is the dominant one;
- it requires valid vertex normals (smooth shading) on the blended mesh;
- it leaves normals and heights describing subtly different surfaces.

Worth doing only if measurement shows Option A has lost something that matters.

## Verification

Verify in **this** repo, on the exported JSON, before anything reaches Unreal. A round-trip through
the game to find out whether an export improved is far too slow a loop, and the in-game slope signal
mixes in tiling and interpolation that obscure what the data actually contains.

### Tier 1 - measure the exported data (no Blender, no Unreal)

`analyze_wave_normal_noise.py` reads `wave_data_frame_*.json` and reports the metrics this spec is
written against:

```
python analyze_wave_normal_noise.py <unified_dir>
python analyze_wave_normal_noise.py <old_unified_dir> --compare <new_unified_dir>
```

- **spatial** - |slope change| between adjacent grid points, along X and Y
- **temporal** - |slope change| at the *same* grid point between consecutive frames (the headline)
- **height** - the same two, as a control: heights must not move
- **consistency** - angle between the stored normal and the normal implied by central differences on
  the stored heights

Two frames are enough for every metric, so this runs on a short export.

### Tier 2 - prove correctness, not just smoothness

Smoothness alone is trivially gamed: setting every normal to straight up scores perfectly on Tier 1
and is completely wrong. So test the sampler against surfaces whose normals are known analytically -
a **tilted plane** (constant, exactly known normal) and a **sine wave** (known varying normal):

- build the test mesh in Blender, run `sample_unified_grid()` on it, compare exported normals to the
  analytic normal per grid point;
- a plane catches sign errors, axis swaps and step/scale mistakes - the failure modes most likely in
  a gradient implementation;
- a sine wave catches over-flattening: the exported slope amplitude should match the analytic one to
  within what the grid resolution justifies, and no worse.

Follow the existing `test_*.py` convention (`blender <file> --background --python test_...py`).

### Tier 3 - a cheap guard inside the export run

Compute the Tier 1 spatial metric per frame during export and print it, warning past a threshold. An
export takes hours; this catches a regression at frame 3 instead of at import time.

### Test on the right frames

Include a **steep or breaking section**, not just open face. Faceting is worst where the surface
curves hardest, so an export that looks clean on gentle water can still be broken where the game
actually spends its time.

## Acceptance Criteria

- **AC1** (Tier 1) `|slope change|` between adjacent grid points falls well below today's
  mean 0.0368 / max 0.3612.
- **AC2** (Tier 1) `|slope change|` at a fixed grid point between consecutive frames falls
  substantially. **This is the headline** - it is the term that dominates the in-game jitter.
- **AC2b** (Tier 2) Exported normals match the analytic normal of a tilted plane to within a small
  tolerance, and a sine wave's slope amplitude is not flattened beyond what the grid justifies.
  Without this, AC1 and AC2 can both be passed by a wrong-but-smooth implementation.
- **AC3** (game, last) Per-tick `|slope change|` while riding approaches what the grid gradient
  predicts (~0.008 for 12 cm of movement), against 0.0992 today. Check this only once Tier 1 and
  Tier 2 pass - it is confirmation, not the development loop. Game-side diagnostics:
  `surf.debug.flags wavedump` and the `tileFrame` field on the CROSSING line.
- **AC4** Heights are unchanged — this touches only `nx/ny/nz`.
- **AC5** The rendered wave looks the same. Normals here feed physics sampling; confirm the display
  meshes are unaffected (they carry their own normals from the OBJ export).

## Validation Cost

A full export takes many hours (see `SPEC_seamless_mesh_blending.md`). Validate on a **short frame
range first** — a few consecutive frames is enough to measure AC1 and AC2, since both are local
comparisons. Only run a full export once the numbers move.

## Open Questions

- **Is `CoordinateScale` non-uniform in the game, and if so are normals being transformed wrongly?**
  The exported normal is in Blender/data space; `AWaveHeight` reads it and uses it directly as a
  world-space normal. If the Blender→world mapping scales X and Y differently (the debug code in
  `WaveHeight.cpp` references factors of 28.0 and 20.1), then a normal needs the inverse-transpose
  of that scale, not a straight copy, and every slope the game computes is distorted by a fixed
  factor. This is **independent of the noise** and would not be fixed by this spec. Check the live
  `CoordinateScale` on the `AWaveHeight` instance in the level before assuming either way.
- **Is cross-shore resolution enough? (axis label corrected.)** The grid is 41 (X) x 434 (Y) at
  `step_size` 2.0. This spec originally called **X** the cross-shore/rideable axis and asked for a
  finer grid *in X* — that is **wrong**: `detect_tiling_axis.py` shows **X is the along-crest
  tiling axis** (41 pts) and **Y is the steep cross-shore face** (434 pts). So the cross-shore
  face is already the *well*-resolved axis. If the rideable core is only ~5 samples wide in game,
  the shortfall is either along-crest (X, genuinely coarse at 41) or an in-game tiling/interp
  effect — re-measure against the corrected axes before adding resolution anywhere.
- Should normals be **temporally smoothed** across frames as well? Option A should remove most of
  the frame-to-frame jitter by construction. Measure first; only add temporal filtering if AC2 is
  still missed.
