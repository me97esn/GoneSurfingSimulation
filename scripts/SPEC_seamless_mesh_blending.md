# Specification: Seamless Mesh Blending for Infinite Wave Animation

## Problem Statement

When placing exported wave meshes side by side in Unreal Engine to create an infinite sideways scrollable wave:
- Mesh at frame 0 is placed at position A
- Mesh at frame 85 (configurable offset) is placed adjacent to it
- The meshes don't merge perfectly - there are small differences between the left edge of mesh 0 and the right edge of mesh 85
- This creates visible seams that break the illusion of a continuous wave when viewed from a near distance

## Goal

Create perfectly seamless transitions between adjacent meshes so the wave appears infinite when scrolling sideways, with no visible edges or seams. Must support an infinite number of meshes placed side by side.

## Proposed Solution

Add a **transition/blend zone** (approximately 5% of mesh width) on one edge of each mesh that smoothly interpolates vertices to match the adjacent mesh's edge.

### Approach

**Separate post-processing step** (not integrated into export pipeline):

The seamless blending is implemented as a separate script that runs on already-exported OBJ files. This is preferable to integrating into the export pipeline because:
- The export takes many hours to complete
- Iteration on the seamless algorithm can be done quickly without re-exporting
- Easier to debug and tune blending parameters
- Can re-run blending with different settings without touching the original exports

**Problem with exported meshes:**
The decimation/compression during export causes the mesh edges to curve outward. When two meshes are placed side by side, both edges curve away from each other, creating a visible gap that simple vertex interpolation cannot fix.

**Solution - Cut and blend both edges:**
1. **Cut away the distorted edges** (~3% of mesh width) from **both** the left and right sides
2. **Use original simulation data** (not exported OBJ) for the blend target positions
3. **Blend vertices in both cut zones**:
   - Right edge: blend toward frame N-95 (the mesh placed to the right)
   - Left edge: blend toward frame N+95 (the mesh placed to the left)

This removes the curved/distorted edges on both sides and creates smooth transitions using accurate source data.

**Workflow:**

1. **First**: Export all meshes using the existing `export_waves_display.sh` script (unchanged)
2. **Second**: Run the seamless blending script which:
   - Loads the exported OBJ files
   - Loads the original Blender simulation file to access undistorted vertex positions
   - Cuts away ~3% from the blend edge
   - Blends remaining edge vertices toward the original simulation data from frame N-offset
   - Writes the modified meshes to output folder

**Seamless blending script** (`apply_seamless_blending.py`):
   - Takes the exported OBJ folder as input
   - Takes the Blender simulation file to read original vertex positions
   - Takes the frame offset as a configurable parameter (default: 95, negative = earlier frame)
   - For each frame N:
     1. Load the exported OBJ mesh
     2. Cut away ~3% from the blend edge (removes distorted vertices)
     3. Load original simulation vertex positions from frame N-offset
     4. Blend the edge vertices toward the original simulation positions
   - Writes to output folder (default: /tmp/seamless_blended_meshes)

### Why One Edge is Sufficient

Since meshes are placed in sequence (0, 85, 170, 255, ...), blending only the "right" edge of each mesh is sufficient:
- Mesh 0's right edge blends toward mesh 85
- Mesh 85's right edge blends toward mesh 170
- And so on...

This creates seamless transitions for infinite side-by-side placement.

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `input_folder` | (required) | Path to folder containing exported OBJ files |
| `output_folder` | /tmp/seamless_blended_meshes | Path to output folder |
| `blend_file` | (required) | Path to Blender simulation file (for reading original vertex positions AND reference mesh position) |
| `reference_mesh` | (required) | **CRITICAL**: Name of reference mesh in Blender file that defines the position offset for adjacent meshes |
| `frame_offset` | -95 | Frame offset to adjacent mesh (negative = earlier frame) |
| `cut_width_percent` | 3.0 | Width of edge to cut away as percentage of mesh width |
| `blend_width_percent` | 3.0 | Width of the blend zone as percentage of mesh width (same as cut width) |
| `blend_axis` | "x" | Axis along which meshes are placed side by side ("x", "y", or "z") |
| `blend_direction` | "positive" | Which edge to blend ("positive" or "negative" end of the axis) |

## Reference Mesh Setup (CRITICAL - Required One-Time Setup)

**The reference mesh is REQUIRED** to determine the exact position offset where adjacent meshes are placed. Without this, the blending cannot know where the adjacent mesh will be positioned in Unreal.

### Setup Steps:
1. Open the simulation Blender file
2. Import a reference mesh (e.g., an OBJ from the frame that will be placed adjacent - typically frame N-95)
3. Position it exactly where it would be placed adjacent to frame 0 in Unreal (edge-to-edge)
4. Name the imported mesh (e.g., "frame_857_reference" if using frame 857 as reference)
5. Save the Blender file

The script reads this reference mesh's position to calculate the exact offset needed for blending.

## Workflow

1. **Export meshes** (no changes to existing workflow):
   - Run `./export_waves_display.sh` as usual
   - This exports all frames and quality levels to OBJ files
   - Takes many hours but only needs to be done once

2. **One-time setup: Position reference mesh in Blender** (see above)

3. **Apply seamless blending** (new post-processing step):
   - Run the seamless blending script
   - The script reads the reference mesh position AND original simulation vertex data from Blender
   - Example: `python apply_seamless_blending.py --blend-file ../3dmodels/breaking_waves_beach_break_2.blend --reference-mesh "frame_857_reference" --input /hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_05 --frame-offset -95`
   - Outputs to `/tmp/seamless_blended_meshes` by default
   - Fast to run, can iterate multiple times with different parameters

4. **Import to Unreal** (unchanged):
   - Import the blended OBJ files as before

## Technical Considerations

- The blend needs to work for all frames in the animation
- Each frame N should blend seamlessly with frame N-offset (earlier frame, since meshes scroll forward)
- For frames near the start of the animation where N-offset is negative, wrap around (modulo)
- The chunk splitting (3x1 grid) needs consideration - only edge chunks along the blend axis need blending
- Vertex interpolation should use smooth falloff (e.g., ease-in-out) to avoid harsh transitions
- Script must parse OBJ files, modify vertex positions, and write back valid OBJ files
- Script must load Blender file in background mode to access original simulation vertex positions
- Should process all quality level folders if specified, or a single folder
- Cutting edges will remove some geometry - faces referencing removed vertices must be handled
- The cut removes the distorted edge caused by decimation/export compression

## Implementation Notes

### Cut and Blend Algorithm

1. **Load exported OBJ mesh** for frame N
2. **Calculate cut boundary**: mesh_max - (mesh_width * cut_width_percent / 100)
3. **Remove vertices beyond cut boundary** (the distorted edge)
4. **Load original simulation** at frame N-offset from Blender file
5. **For vertices in the blend zone** (between cut_boundary and blend_start):
   - Determine blend factor based on position (0.0 at inner edge, 1.0 at outer edge)
   - Apply smooth falloff: `smoothstep(blend_factor)`
   - Find corresponding vertex position in the original simulation mesh
   - Interpolate: `final_pos = lerp(exported_pos, simulation_pos, smooth_blend_factor)`
6. **Rebuild faces** that reference removed vertices (or remove faces with missing vertices)

### Chunk Handling

Since meshes are split into 3x1 chunks:
- Only chunks on the blend edge need modification
- For X-axis blending with positive direction: chunks at x=2 (rightmost column)
- Other chunks export unchanged

## Success Criteria

- Adjacent meshes appear seamless when viewed in Unreal Engine
- No visible seam or discontinuity at any viewing distance
- Works for infinite side-by-side mesh placement
- Animation still loops correctly
- Performance impact is negligible (same polygon count)
- Configurable axis allows adjustment if X is not correct
