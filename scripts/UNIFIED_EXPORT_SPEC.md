# Unified Wave Export System - Specification

## Overview

This specification defines a unified export system that generates all wave-related data (meshes, height samples, and velocities) in a single coordinated pipeline, ensuring perfect alignment and tiling consistency.

## Problem Statement

The current system has three separate export processes:
1. **Mesh export** (`export_waves_display.py`) - GridLODActor OBJ files with seamless blending
2. **Height export** (`export_fluid_surface_to_3d_samples.py`) - Ray-cast height samples to JSON
3. **Velocity export** (`create_water_velocity_datatable.js`) - Particle velocities from FLIP cache

**Critical Issues:**
- Each uses different coordinate systems and bounds
- Height data uses mesh bounds (61.16 × 230.98) instead of tiling dimensions (123.45 × 59.65)
- No guarantee that height/velocity data aligns with mesh tiling
- Velocity data is from particle positions, not mesh-aligned
- Three separate scripts = three potential sources of misalignment

## Solution: Unified Export

### Design Goals

1. **Single source of truth**: All data derived from the same blended mesh
2. **Guaranteed tiling**: Height and velocity use identical tiling parameters as meshes
3. **Efficient**: Process each frame's mesh once, sample multiple data types
4. **Maintainable**: One script, one coordinate system, one set of parameters
5. **Small files**: Compact JSON format optimized for compression
6. **Fast lookup**: Grid-based sampling for O(1) position queries

### Architecture

```
For each frame:
  1. Create joined+blended mesh (current approach, working correctly)
     ├─ Load current frame fluid surface
     ├─ Load adjacent frame fluid surface
     ├─ Position adjacent at reference_offset
     ├─ Blend overlap region
     └─ Join meshes

  2. Export mesh chunks as OBJ (current approach, unchanged)
     ├─ Apply decimate modifier for each quality level
     ├─ Trim to seam boundaries + margin
     ├─ Split into chunks
     └─ Export OBJ files

  3. Sample unified data grid from blended mesh (NEW)
     ├─ Create regular grid covering tiling region
     ├─ For each grid point:
     │  ├─ Ray-cast or nearest-vertex lookup for height + normal
     │  └─ Lookup velocity from particle cache (spatial query)
     └─ Export to unified JSON format
```

## File Format Specification

### Metadata File (One-time, shared)

**File**: `wave_unified_metadata.json`

```json
{
  "version": "1.0",
  "export_date": "2024-01-15T10:30:00Z",
  "blender_file": "breaking_waves_beach_break_2.blend",

  "tiling": {
    "tiling_x": 123.4486,
    "tiling_y": 59.6493,
    "comment": "Dimensions for infinite tiling, from reference mesh offset"
  },

  "grid": {
    "step_size": 2.0,
    "grid_start_x": 5.0,
    "grid_start_y": -277.0,
    "grid_width": 60,
    "grid_height": 116,
    "comment": "Grid covers one tiling tile: tiling_x × tiling_y"
  },

  "seam_boundaries": {
    "min": 5.0,
    "max": 128.4486,
    "axis": "x",
    "comment": "Seam boundaries used for mesh trimming"
  },

  "frames": {
    "start_frame": 752,
    "end_frame": 868,
    "frame_offset": -95,
    "comment": "frame_offset is the offset to adjacent frame for blending"
  },

  "reference_mesh": {
    "name": "1_0_mesh_903_reference",
    "offset_x": 123.4486,
    "offset_y": -59.6493,
    "offset_z": 0.0
  }
}
```

### Per-Frame Data Files

**File pattern**: `wave_data_frame_{frame}.json`

**Format Option A: Compact Arrays** (Recommended)
```json
{
  "frame": 752,
  "grid": {
    "width": 60,
    "height": 116,
    "step": 2.0,
    "start_x": 5.0,
    "start_y": -277.0
  },
  "data": {
    "h": [/* height values, width*height floats */],
    "nx": [/* normal X, width*height floats */],
    "ny": [/* normal Y, width*height floats */],
    "nz": [/* normal Z, width*height floats */],
    "vx": [/* velocity X, width*height floats */],
    "vy": [/* velocity Y, width*height floats */],
    "vz": [/* velocity Z, width*height floats */]
  }
}
```

**Array indexing**: `index = y * width + x`
- Where `x = floor((world_x - grid_start_x) / step_size)`
- And `y = floor((world_y - grid_start_y) / step_size)`

**Format Option B: Split Files** (If size is concern)
```
wave_height_frame_752.json      # Just height + normals
wave_velocity_frame_752.json    # Just velocities
```

### File Size Estimates

For grid 60×116 = 6,960 samples:
- 7 arrays × 6,960 floats × 4 bytes = ~194 KB per frame (uncompressed)
- With gzip compression: ~20-40 KB per frame (estimated)
- For 117 frames: ~2.3-4.7 MB total (compressed)

## Export Script API

### Command Line Interface

```bash
blender simulation.blend --background --python export_waves_unified.py -- \
  --start-frame 752 \
  --end-frame 868 \
  --output-dir /hdd/exports/medium_wave_left \
  --quality-levels 0.03,0.005 \
  --step-size 2.0 \
  --frame-offset -95 \
  --reference-mesh 1_0_mesh_903_reference \
  --velocity-cache /ssd3/flip_fluid_cache/flip_fluid_cache_6 \
  --skip-existing
```

### Python Function Signatures

```python
def export_unified_frame(
    fluid_surface: bpy.types.Object,
    frame: int,
    output_dir: str,
    quality_levels: List[float],
    blend_config: Dict,
    grid_config: Dict,
    velocity_cache_path: str,
    skip_existing: bool = True
) -> None:
    """
    Export all data for a single frame.

    Args:
        fluid_surface: Blender fluid surface object
        frame: Frame number to export
        output_dir: Base output directory
        quality_levels: List of decimate ratios for mesh export
        blend_config: Seamless blending configuration
        grid_config: Grid sampling configuration
        velocity_cache_path: Path to FLIP fluid cache
        skip_existing: Skip if files already exist
    """
    pass

def sample_mesh_grid(
    mesh_obj: bpy.types.Object,
    grid_config: Dict,
    velocity_data: Optional[Dict] = None
) -> Dict:
    """
    Sample height, normals, and velocities on a regular grid.

    Args:
        mesh_obj: The joined+blended mesh object
        grid_config: Grid parameters (start, size, step)
        velocity_data: Optional velocity particle data

    Returns:
        Dict with arrays: h, nx, ny, nz, vx, vy, vz
    """
    pass

def load_velocity_frame(
    cache_path: str,
    frame: int
) -> Dict:
    """
    Load velocity particles from FLIP cache for a frame.

    Args:
        cache_path: Path to flip_fluid_cache folder
        frame: Frame number

    Returns:
        Dict with particle positions and velocities
    """
    pass

def map_velocities_to_grid(
    velocity_data: Dict,
    grid_config: Dict
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Map particle velocities to regular grid using spatial queries.

    Uses inverse distance weighting to interpolate velocities
    from nearby particles to grid points.

    Args:
        velocity_data: Particle positions and velocities
        grid_config: Grid parameters

    Returns:
        Tuple of (vx, vy, vz) arrays
    """
    pass
```

## Grid Calculation Details

### Grid Coverage

The grid must cover exactly one tiling tile to ensure seamless wrapping:
- **Grid X extent**: `tiling_x` (e.g., 123.4486 units)
- **Grid Y extent**: `tiling_y` (e.g., 59.6493 units)
- **Grid start**: Aligned with seam boundaries
  - `grid_start_x = seam_min = 5.0`
  - `grid_start_y` = mesh Y min at start frame
- **Grid dimensions**:
  - `grid_width = ceil(tiling_x / step_size)`
  - `grid_height = ceil(tiling_y / step_size)`

### Sampling Methods

**Height Sampling** (choose one):

1. **Ray-casting** (current method):
   - Cast ray from (x, y, +100) to (x, y, -100)
   - Find intersection with mesh
   - Extract height (Z) and normal

2. **Nearest vertex** (faster):
   - Build KD-tree of mesh vertices
   - For each grid point, find nearest vertex
   - Use vertex Z position and normal
   - Faster but less accurate between vertices

3. **Interpolated** (most accurate):
   - Find face containing (x, y) point
   - Barycentric interpolation of face vertices
   - Most accurate but slowest

**Velocity Sampling**:

1. Load particle data from `.bobj` file (use existing parser)
2. Build KD-tree of particle positions (X, Y only, ignore Z)
3. For each grid point:
   - Find K nearest particles (e.g., K=4)
   - Inverse distance weighted average of velocities
   - Fallback to zero if no particles within threshold

## Unreal Engine Integration

### Data Loading

**C++ Structure**:
```cpp
struct FWaveUnifiedMetadata
{
    float TilingX;
    float TilingY;
    float GridStartX;
    float GridStartY;
    float StepSize;
    int32 GridWidth;
    int32 GridHeight;
    int32 StartFrame;
    int32 EndFrame;
};

struct FWaveFrameData
{
    int32 Frame;
    TArray<float> Heights;
    TArray<FVector> Normals;   // Or separate nx, ny, nz arrays
    TArray<FVector> Velocities; // Or separate vx, vy, vz arrays
};
```

### Tiling Implementation

**In WaveHeight.cpp**:
```cpp
FVector AWaveHeight::GetHeightAndVelocity(FVector WorldPos, int32 Frame)
{
    // Convert world position to grid indices with tiling
    float localX = WorldPos.X - ActorLocation.X;
    float localY = WorldPos.Y - ActorLocation.Y;

    // Apply modulo wrapping using tiling dimensions
    localX = fmod(localX - GridStartX, TilingX);
    if (localX < 0) localX += TilingX;
    localX += GridStartX;

    localY = fmod(localY - GridStartY, TilingY);
    if (localY < 0) localY += TilingY;
    localY += GridStartY;

    // Convert to grid indices
    int32 gridX = FMath::FloorToInt((localX - GridStartX) / StepSize);
    int32 gridY = FMath::FloorToInt((localY - GridStartY) / StepSize);

    // Clamp to grid bounds
    gridX = FMath::Clamp(gridX, 0, GridWidth - 1);
    gridY = FMath::Clamp(gridY, 0, GridHeight - 1);

    // Lookup in array
    int32 index = gridY * GridWidth + gridX;
    float height = FrameData->Heights[index];
    FVector velocity = FrameData->Velocities[index];

    return FVector(localX, localY, height); // + velocity elsewhere
}
```

## Implementation Phases

### Phase 1: Extend Mesh Export (Minimal Change)
- Modify `export_waves_display.py` to also output metadata JSON
- Include tiling parameters in metadata
- No changes to mesh export logic
- **Deliverable**: `wave_unified_metadata.json` with correct tiling params

### Phase 2: Unified Height Sampling
- Add grid sampling to `export_waves_display.py`
- Sample from the same blended mesh used for OBJ export
- Export per-frame height + normal data
- **Deliverable**: `wave_data_frame_*.json` with h, nx, ny, nz

### Phase 3: Velocity Integration
- Add FLIP cache parsing (port from JS to Python)
- Map velocities to grid using spatial queries
- Include in per-frame JSON
- **Deliverable**: Complete unified export with velocities

### Phase 4: Unreal Engine Updates
- Update WaveHeight to load unified format
- Implement tiling using metadata tiling dimensions
- Update velocity lookup to use same grid
- **Deliverable**: Working tiling in Unreal

## Testing & Validation

### Export Validation

1. **Metadata correctness**:
   - Verify `tiling_x` = `abs(reference_offset.x)`
   - Verify `grid_width * step_size ≈ tiling_x`
   - Verify seam boundaries match mesh export

2. **Grid coverage**:
   - Sample point at (grid_start_x, grid_start_y) should exist
   - Sample point at (grid_start_x + tiling_x - step, grid_start_y + tiling_y - step) should exist
   - All samples should have valid height values

3. **Tiling validation**:
   - Height at (x, y) should ≈ height at (x + tiling_x, y)
   - Height at (x, y) should ≈ height at (x, y + tiling_y)
   - Velocity should also tile (within particle noise tolerance)

### Runtime Validation

1. **Alignment test**:
   - Load WaveHeight and GridLODActor in Unreal
   - Enable debug visualization
   - Move surfboard across seams
   - Verify height matches mesh visually

2. **Tiling test**:
   - Move camera far from origin (e.g., +500 units in X)
   - Verify no drift or discontinuities
   - Wave should look identical to origin

## Performance Considerations

### Export Performance

- **Current**: ~5-10 min per frame for all quality levels
- **With unified sampling**: +30-60 sec per frame (estimated)
- **Optimization**: Can parallelize across frames
- **Velocity parsing**: First-time cost to port FLIP reader to Python

### Runtime Performance

- **Memory**: ~200 KB per frame (compressed), 117 frames = ~24 MB total
- **Lookup**: O(1) grid lookup, 2-3 arithmetic operations
- **Loading**: Parse JSON once at startup, minimal overhead

## Migration Path

### For Existing Projects

1. **Re-export data**: Run unified export on existing simulation
2. **Update metadata**: Create `wave_unified_metadata.json` with current tiling params
3. **Update Unreal**: Modify WaveHeight to use new tiling dimensions
4. **Verify**: Test alignment and tiling
5. **Cleanup**: Remove old height sample files

### Backward Compatibility

- Old height sample format can coexist temporarily
- Add feature flag in Unreal to select data format
- Gradual migration per-simulation

## Open Questions

1. **Velocity cache format**: Confirm `.bobj` format is consistent across simulations
2. **Grid resolution**: Is step_size=2.0 optimal, or should it be configurable per-simulation?
3. **Normal storage**: Store as Vector3 or separate arrays? (Separate = better compression)
4. **Velocity fallback**: What value when no particles nearby? (Zero, or nearest particle?)
5. **Multi-axis tiling**: Current spec assumes X-axis tiling only. Support Y-axis in future?

## References

- Current mesh export: `export_waves_display.py`
- Current height export: `export_fluid_surface_to_3d_samples.py`
- Current velocity export: `create_water_velocity_datatable.js`
- GridLODActor tiling: `InfiniteWaveManager.cpp` lines 354-362
- WaveHeight tiling (broken): `WaveHeight.cpp` lines 547-551
