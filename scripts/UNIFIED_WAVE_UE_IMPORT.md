# Importing Unified Wave Data into Unreal Engine

## Files

The unified export produces two files:

- `wave_unified_metadata.json` - Grid and tiling configuration (import manually or parse at startup)
- `wave_unified_data.json` - UE datatable with one row per frame

## Step 1: Create the UE Struct

Create a new struct (e.g., `FWaveUnifiedFrameData`) that matches the datatable row format:

| Field | Type | Description |
|-------|------|-------------|
| `h` | `TArray<float>` | Height values (grid_width * grid_height floats) |
| `nx` | `TArray<float>` | Normal X components |
| `ny` | `TArray<float>` | Normal Y components |
| `nz` | `TArray<float>` | Normal Z components |

In Blueprint, create a **Structure** asset with four `Array of Float` fields named `h`, `nx`, `ny`, `nz`.

## Step 2: Import the Datatable

1. In the Content Browser, right-click and select **Import**
2. Select `wave_unified_data.json`
3. When prompted, choose **DataTable** and select your `FWaveUnifiedFrameData` struct as the row type
4. The datatable will have one row per frame, named `Frame_886`, `Frame_887`, etc.

## Step 3: Load the Metadata

The metadata file contains the grid configuration needed to look up values. Parse it at startup or store the values as properties:

| Metadata Field | Example Value | Description |
|----------------|---------------|-------------|
| `grid.step_size` | `2.0` | Distance between grid samples |
| `grid.grid_start_x` | `5.0` | World X of first grid sample |
| `grid.grid_start_y` | `-277.72` | World Y of first grid sample |
| `grid.grid_width` | `40` | Number of samples in X |
| `grid.grid_height` | `230` | Number of samples in Y |
| `tiling.tiling_x` | `81.79` | Tiling period in X (from reference mesh offset) |
| `tiling.tiling_y` | `404.43` | Tiling period in Y |
| `seam_boundaries.min` | `5.0` | X start of valid tiling region |
| `seam_boundaries.max` | `86.79` | X end of valid tiling region |

## Step 4: Look Up Height at a World Position

### Array Indexing

The arrays use flat indexing: `index = y_idx * grid_width + x_idx`

### World Position to Grid Index

```cpp
// Convert world position to grid indices
int32 x_idx = FMath::FloorToInt((WorldPos.X - GridStartX) / StepSize);
int32 y_idx = FMath::FloorToInt((WorldPos.Y - GridStartY) / StepSize);

// Clamp to grid bounds
x_idx = FMath::Clamp(x_idx, 0, GridWidth - 1);
y_idx = FMath::Clamp(y_idx, 0, GridHeight - 1);

// Look up in flat array
int32 index = y_idx * GridWidth + x_idx;
float Height = FrameData->h[index];
FVector Normal(FrameData->nx[index], FrameData->ny[index], FrameData->nz[index]);
```

### With Tiling (Infinite Wrapping in X)

```cpp
// Apply modulo wrapping for infinite tiling
float LocalX = WorldPos.X - ActorLocation.X;
LocalX = FMath::Fmod(LocalX - GridStartX, TilingX);
if (LocalX < 0) LocalX += TilingX;
LocalX += GridStartX;

// Then convert to grid index as above
int32 x_idx = FMath::FloorToInt((LocalX - GridStartX) / StepSize);
```

## Notes

- The height values are in Blender world-space units (not scaled). Apply a multiplier if your UE project uses a different scale.
- The grid is sampled from the seamlessly blended mesh (before decimation), so height data aligns exactly with the tiled stop-motion meshes.
- Velocity arrays (`vx`, `vy`, `vz`) are not yet included. They will be added in a future export phase.
