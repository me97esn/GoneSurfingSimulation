# Specification: Include Wave Velocity in Unified Export

## Problem Statement

Wave velocity data is currently exported via a separate Node.js pipeline that reads FLIP Fluids `.bobj`/`blur*.bobj` cache files and outputs scattered (non-grid) vertex data. The unified export already samples wave height and normals on a regular grid via ray-casting. Having velocity on a different coordinate system requires extra mapping logic in Unreal.

## Goal

Add wave velocity (vx, vy, vz) to the unified export so that height, normals, and velocity all share the same regular grid. One grid lookup in Unreal gives all data for a position.

## Current State

### Unified export (height + normals)
- Runs inside Blender (`export_waves_display.py`)
- Samples on a regular grid via ray-casting downward onto the blended mesh
- Outputs per-frame JSON with `h`, `nx`, `ny`, `nz` arrays (flat, indexed as `y * width + x`)
- Grid config defined by seam boundaries (X) and mesh extent (Y)

### Velocity export (separate pipeline)
- Runs outside Blender (`create_water_velocity_datatable.js` + worker)
- Reads binary `.bobj` files for vertex positions (x, y, z)
- Reads `blur*.bobj` files for velocity at same vertices (dx, dy, dz)
- Outputs per-frame JSON with scattered coordinates + velocity arrays
- Source: FLIP Fluids simulation cache at `/ssd3/flip_fluid_cache/flip_fluid_cache_6/bakefiles/`

## Proposed Solution

Read the `.bobj` and `blur*.bobj` files for each frame inside the unified export script, interpolate the scattered velocity data onto the same regular grid, and populate the `vx`, `vy`, `vz` arrays.

### Approach

1. For each frame, after sampling height/normals from the mesh:
   - Read the `.bobj` file to get scattered vertex positions
   - Read the corresponding `blur*.bobj` file to get velocities at those positions
   - Build a spatial lookup (KDTree) from the scattered (x, y) positions
   - For each grid point, find the nearest scattered vertex and use its velocity
2. Write the velocity data into the same per-frame JSON (filling the currently-empty `vx`, `vy`, `vz` arrays)

### Binary File Format (from existing worker code)

The `.bobj` files use little-endian format:
- First 4 bytes: `uint32` number of vertices
- Then for each vertex: 3 x `float32` (x, y, z) = 12 bytes per vertex
- Total vertex data size: `4 + (num_vertices * 12)` bytes

The `blur*.bobj` files have the same layout - velocity (dx, dy, dz) at the same vertex indices.

**Note**: The existing worker reads offset starting at 4 (skipping the vertex count), then increments by 4 bytes per float. The first float read is at offset 4 (x), then 8 (y), then 12 (z), etc.

### Interpolation Method

**Nearest-neighbor** using a KDTree on the (x, y) coordinates of the scattered vertices:
- Fast to build and query
- Sufficient for velocity data (doesn't need sub-vertex precision)
- Blender's `mathutils.kdtree` or Python's `scipy.spatial.KDTree` can be used

Alternative: linear interpolation via `scipy.griddata` for smoother results, at the cost of speed.

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `flip_fluid_cache_folder` | `/ssd3/flip_fluid_cache/` | Path to FLIP Fluids cache |
| `cache_subfolder` | `flip_fluid_cache_6` | Name of the cache subfolder |
| `velocity_interpolation` | `nearest` | Interpolation method: `nearest` or `linear` |

These should be added as command-line arguments to `export_waves_display.py`.

## Implementation Notes

### Reading .bobj in Python (inside Blender)

```python
import struct

def read_bobj(filepath):
    with open(filepath, 'rb') as f:
        num_vertices = struct.unpack('<I', f.read(4))[0]
        data = struct.unpack(f'<{num_vertices * 3}f', f.read(num_vertices * 12))
        vertices = [(data[i*3], data[i*3+1], data[i*3+2]) for i in range(num_vertices)]
    return vertices
```

### Grid Sampling with KDTree

```python
from scipy.spatial import KDTree

# Build tree from scattered (x, y) positions
positions_2d = [(v[0], v[1]) for v in bobj_vertices]
tree = KDTree(positions_2d)

# For each grid point, find nearest vertex
for y_idx in range(grid_height):
    for x_idx in range(grid_width):
        x_pos = start_x + step * x_idx
        y_pos = start_y + step * y_idx
        dist, idx = tree.query([x_pos, y_pos])
        i = y_idx * grid_width + x_idx
        vx[i] = blur_vertices[idx][0]
        vy[i] = blur_vertices[idx][1]
        vz[i] = blur_vertices[idx][2]
```

### File Naming

The `.bobj` files are named by frame number: `{frame}.bobj`
The blur files are: `blur{frame}.bobj`

Both are in `{flip_fluid_cache_folder}/{cache_subfolder}/bakefiles/`

### Integration Point

In `export_chunks_for_frame()`, after calling `sample_unified_grid()` for height/normals:
1. Read `.bobj` + `blur*.bobj` for the current frame
2. Interpolate velocities onto the grid
3. Add `vx`, `vy`, `vz` to the samples dict before calling `write_unified_frame_data()`

## Workflow

No change to the user workflow - velocity is automatically included when running the unified export, provided the FLIP Fluids cache path is configured.

## Output

The per-frame JSON files will now include populated velocity arrays:

```json
{
  "frame": 886,
  "grid": { "width": 40, "height": 230, "step": 2.0, ... },
  "data": {
    "h": [...],
    "nx": [...], "ny": [...], "nz": [...],
    "vx": [...], "vy": [...], "vz": [...]
  }
}
```

The merged UE datatable (`wave_unified_data.json`) will also include `vx`, `vy`, `vz` arrays per row.

## Success Criteria

- Velocity arrays are populated in the unified JSON output
- Velocity values visually make sense when plotted (e.g., quiver plot on the grid)
- Grid positions match between height and velocity data
- No significant increase in export time (KDTree build + query should be fast)
- Existing height/normal export is unaffected
