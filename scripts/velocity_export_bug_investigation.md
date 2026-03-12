# Velocity Export Bug Investigation Summary

## Problem
Wave velocity data exported from Blender FLIP Fluids simulation is repeating across the Y dimension. All grid positions with the same X coordinate have identical velocity values, regardless of their Y position.

**Evidence from Unreal Engine logs:**
```
[Velocity Sample 0] gridPos=(0,280) idx=11480, waveHeight=17.1654, dataVel=(-0.012265,-0.001519,-0.050902)
[Velocity Sample 3] gridPos=(0,284) idx=11644, waveHeight=18.3494, dataVel=(-0.012265,-0.001519,-0.050902)  // IDENTICAL
[Velocity Sample 6] gridPos=(0,288) idx=11808, waveHeight=18.1455, dataVel=(-0.012265,-0.001519,-0.050902)  // IDENTICAL
```

Different grid positions (different indices, different wave heights) but **exact same velocity data**. This proves the bug is in the export script, not in Unreal Engine.

## Export Script Location
**File:** `E:\windowsgrejor\git\GoneSurfingSimulation\scripts\export_waves_display.py`

**Function:** `sample_velocity_grid()` (lines 615-691)

## How Velocity Export Works

1. **Input data:** Reads two `.bobj` files per frame:
   - `{frame}.bobj` - contains particle positions (x, y, z)
   - `blur{frame}.bobj` - contains particle velocities (vx, vy, vz)

2. **KDTree nearest-neighbor lookup:**
   ```python
   positions_2d = [(p[0], p[1]) for p in positions]  # Extract (x,y) only
   tree = KDTree(positions_2d)
   ```

3. **Grid sampling loop:**
   ```python
   for y_idx in range(height):
       for x_idx in range(width):
           x_pos = start_x + step * x_idx
           y_pos = start_y + step * y_idx
           dist, idx = tree.query([x_pos, y_pos])  # Find nearest particle
           i = y_idx * width + x_idx
           vx[i] = float(velocities[idx][0])
           vy[i] = float(velocities[idx][1])
           vz[i] = float(velocities[idx][2])
   ```

## The Code Looks Correct

The sampling loop properly:
- Iterates over both X and Y dimensions
- Calculates world positions for each grid point
- Queries KDTree for nearest neighbor
- Stores velocity at correct array index `i = y_idx * width + x_idx`

## Hypothesis

The bug is likely that **the KDTree is returning the same particle index for all Y positions at a given X**. This could happen if:

1. **Sparse particle distribution:** FLIP particles only vary in X dimension, not Y
2. **Particles clustered in lines:** Particles form vertical lines, so all Y queries at same X find the same particle
3. **Query distance too large:** All grid points finding the same far-away particle
4. **Grid/particle coordinate mismatch:** Sampling grid is in different coordinate space than particles

## Debug Logging Added

I added debug output to the export script to diagnose this:

```python
# Lines 648-655: Show data ranges
print(f"    KDTree X range: [{min(x_coords):.2f}, {max(x_coords):.2f}]")
print(f"    KDTree Y range: [{min(y_coords):.2f}, {max(y_coords):.2f}]")
print(f"    Sampling grid X range: [{start_x:.2f}, {start_x + step * (width-1):.2f}]")
print(f"    Sampling grid Y range: [{start_y:.2f}, {start_y + step * (height-1):.2f}]")

# Lines 672-686: Show sample queries at X=0
if x_idx == 0 and y_idx % 4 == 0 and len(debug_samples) < 5:
    debug_samples.append({
        'grid': (x_idx, y_idx),
        'pos': (x_pos, y_pos),
        'kdtree_idx': idx,
        'dist': dist,
        'vel': velocities[idx]
    })
```

## What to Look For in Export Output

When the export script runs with the debug logging, check:

1. **Range comparison:**
   - Do KDTree and sampling grid ranges overlap?
   - Is Y range in KDTree very small or zero?

2. **Sample queries:**
   ```
   Debug: Velocity sampling at X=0 for different Y values:
     Grid(0,0) pos=(..,..) -> KDTree idx=123 dist=0.05 vel=(...)
     Grid(0,4) pos=(..,..) -> KDTree idx=456 dist=0.05 vel=(...)  // Should be DIFFERENT idx
   ```
   - Are KDTree indices different for different Y positions?
   - Are distances reasonable (< 1.0 units)?
   - Are velocities different?

## Expected Fix

Once we identify the root cause from debug output:

- **If particles lack Y variation:** May need to use 3D KDTree or sample velocity differently
- **If coordinate mismatch:** Need to transform coordinates before KDTree query
- **If distance too large:** May need to handle "no nearby particle" case differently

## Files Modified

- `E:\windowsgrejor\git\GoneSurfingSimulation\scripts\export_waves_display.py` - Added debug logging at lines 648-655 and 672-686

## Next Steps

1. Run the export script on another machine
2. Look for debug output lines in console
3. Share the debug output showing:
   - KDTree X/Y ranges
   - Sampling grid X/Y ranges
   - Sample queries at X=0 with their KDTree indices and distances
4. Based on output, identify why KDTree returns same index for different Y positions
5. Fix the velocity sampling logic
