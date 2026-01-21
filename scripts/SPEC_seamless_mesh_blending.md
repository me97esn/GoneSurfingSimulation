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

**Workflow:**

1. **First**: Export all meshes using the existing `export_waves_display.sh` script (unchanged)
2. **Second**: Run the seamless blending script on the exported OBJ files

**Seamless blending script** (`apply_seamless_blending.py` or similar):
   - Takes the exported OBJ folder as input
   - Takes the frame offset as a configurable parameter (default: 85)
   - For each frame N, loads both frame N and frame N+offset OBJ files
   - Creates a transition zone on one edge (~5% of mesh width)
   - Interpolates vertex positions in the transition zone to match frame N+offset's corresponding edge
   - Overwrites the original OBJ file (or writes to a new folder)

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
| `output_folder` | (same as input) | Path to output folder (if not specified, overwrites input files) |
| `frame_offset` | 85 | Number of frames between adjacent meshes |
| `reference_mesh_name` | (required) | Name of the imported reference mesh in the Blender file (used to read position offset) |
| `blend_width_percent` | 5.0 | Width of the transition zone as percentage of mesh width |
| `blend_axis` | "x" | Axis along which meshes are placed side by side ("x", "y", or "z") |
| `blend_direction` | "positive" | Which edge to blend ("positive" or "negative" end of the axis) |

## Workflow

1. **One-time setup** (in Blender):
   - Open Blender with the original simulation file
   - Import a reference mesh (e.g., frame 85 OBJ)
   - Position it exactly where it would be placed in the game relative to frame 0
   - Save the Blender file (the reference mesh position is now stored)

2. **Export meshes** (no changes to existing workflow):
   - Run `./export_waves_display.sh` as usual
   - This exports all frames and quality levels to OBJ files
   - Takes many hours but only needs to be done once

3. **Apply seamless blending** (new post-processing step):
   - Run the seamless blending script
   - The script reads the Blender file to get the reference mesh position automatically
   - Example: `python apply_seamless_blending.py --blend-file ../3dmodels/breaking_waves_beach_break_2.blend --reference-mesh "frame_85_reference" --input /hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_05 --frame-offset 85`
   - This modifies the OBJ files in place (or outputs to a separate folder)
   - Fast to run, can iterate multiple times with different parameters

4. **Import to Unreal** (unchanged):
   - Import the blended OBJ files as before

## Technical Considerations

- The blend needs to work for all frames in the animation
- Each frame N should blend seamlessly with frame N+offset
- For frames near the end of the animation where N+offset exceeds total frames, wrap around (modulo)
- The chunk splitting (3x1 grid) needs consideration - only edge chunks along the blend axis need blending
- Vertex interpolation should use smooth falloff (e.g., ease-in-out) to avoid harsh transitions
- Script must parse OBJ files, modify vertex positions, and write back valid OBJ files
- Should process all quality level folders if specified, or a single folder

## Implementation Notes

### Blending Algorithm

For vertices in the transition zone:
1. Determine blend factor based on position (0.0 at inner edge, 1.0 at outer edge)
2. Apply smooth falloff: `smoothstep(blend_factor)` or similar
3. Find corresponding vertex position in the offset frame's mesh
4. Interpolate: `final_pos = lerp(original_pos, target_pos, smooth_blend_factor)`

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
