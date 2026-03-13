# Wave Velocity Export — Investigation & Fix Summary

## Problem

Wave velocity data (vx, vy, vz) was either missing or incorrect in unified export JSON files.

---

## Bug 1: Empty velocity arrays

**Symptom:** All vx, vy, vz arrays were empty in the exported JSON files.

**Root cause:** Wrong filename format for FLIP Fluids `.bobj` cache files.
The export script used `f"{frame}.bobj"` (e.g. `886.bobj`), but FLIP Fluids uses 6-digit zero-padded names (`000886.bobj`).

**Fix:** Changed format strings to `f"{frame:06d}.bobj"` and `f"blur{frame:06d}.bobj"`.

---

## Bug 2: `ModuleNotFoundError: No module named 'scipy'`

**Symptom:** Script crashed when trying to import `scipy.spatial.KDTree`.

**Root cause:** Blender's embedded Python does not include scipy.

**Fix:** Replaced with `mathutils.kdtree.KDTree`, which is built into Blender. The API differs — requires `insert()`, `balance()`, and `find()` instead of the scipy constructor + `query()`.

---

## Bug 3: Velocity repeating across Y dimension

**Symptom (reported from Unreal Engine logs):**
```
[Velocity Sample 0] gridPos=(0,280) idx=11480, waveHeight=17.17, dataVel=(-0.012265,-0.001519,-0.050902)
[Velocity Sample 3] gridPos=(0,284) idx=11644, waveHeight=18.35, dataVel=(-0.012265,-0.001519,-0.050902)  // IDENTICAL
[Velocity Sample 6] gridPos=(0,288) idx=11808, waveHeight=18.15, dataVel=(-0.012265,-0.001519,-0.050902)  // IDENTICAL
```
Different grid indices, different wave heights, but identical velocity values.

**Root cause:** Grid Y range extended far beyond the FLIP particle domain. The KDTree nearest-neighbor lookup returned the same edge particle for all grid positions outside the simulation, resulting in identical velocity values across large portions of the grid.

**Data (at frame 886):**
| | Y min | Y max |
|---|---|---|
| FLIP particles | -277.69 | +184.48 |
| Sampling grid | -337.15 | +528.85 |

The grid extended ~59 units below and ~344 units above the particle domain.

**Fix:** Added a distance threshold in `sample_velocity_grid()`. Grid points farther than `step * 2.0` from any particle are left at zero velocity instead of being assigned the nearest edge particle's velocity.

```python
max_dist = step * 2.0
_co, idx, _dist = tree.find((x_pos, y_pos, 0.0))
if _dist <= max_dist:
    vx[i] = float(velocities[idx][0])
    vy[i] = float(velocities[idx][1])
    vz[i] = float(velocities[idx][2])
# else: leave as 0.0 (grid point is outside the fluid domain)
```

---

## Known Limitation: h/v mismatch at grid edges

The sampling grid is sized to match the joined blended wave mesh. The wave mesh covers the full grid, so h (height) values are non-zero across the entire grid from ray-casting. However, the FLIP particles only span a subset of that range.

**At frame 886:**
| Grid region | Rows | % of grid | h | velocity |
|---|---|---|---|---|
| Bottom (Y < -278) | ~29 | 6.7% | non-zero | 0 |
| Middle (in domain) | ~233 | 53.7% | non-zero | non-zero |
| Top (Y > +184) | ~172 | 39.6% | non-zero | 0 |

The top ~172 rows in particular have wave surface height data but zero velocity. This is accepted for now — if it causes visual artifacts in Unreal Engine (e.g. wave shape without matching motion cues), options include:
- Cropping the grid to the particle domain
- Zeroing out h/normals where velocity is also zero

---

## Files Modified

- [export_waves_display.py](export_waves_display.py) — `sample_velocity_grid()` function (fixes 1, 2, 3)
