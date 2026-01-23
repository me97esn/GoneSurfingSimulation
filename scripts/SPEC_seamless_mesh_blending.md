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

### Approach: OBJ-to-OBJ Blending

**Separate post-processing step** (not integrated into export pipeline):

The seamless blending is implemented as a separate script that runs on already-exported OBJ files. This approach:
- Blends between exported OBJ meshes from adjacent frames (not original Blender simulation data)
- Works correctly with decimated/chunked meshes since both source and target have matching topology
- The export takes many hours to complete, so keeping blending separate allows quick iteration
- Can re-run blending with different settings without touching the original exports

**Problem with exported meshes:**
The decimation/compression during export causes the mesh edges to curve outward. When two meshes are placed side by side, both edges curve away from each other, creating a visible gap.

**Solution - Cut and blend both edges using adjacent OBJ files:**
1. **Cut away the distorted edges** (~3% of mesh width) from **both** the left and right sides
2. **Load adjacent frame's exported OBJ** (not original simulation data - topology must match)
3. **Blend vertices in both cut zones**:
   - Right edge of frame N: blend toward the LEFT edge of frame N-95's OBJ (the mesh placed to the right)
   - Left edge of frame N: blend toward the RIGHT edge of frame N+95's OBJ (the mesh placed to the left)

This removes the curved/distorted edges on both sides and creates smooth transitions using matching decimated mesh data.

**Workflow:**

1. **First**: Export all meshes using the existing `export_waves_display.sh` script (unchanged)
2. **Second**: Run the seamless blending script which:
   - Loads the exported OBJ file for frame N
   - Loads the exported OBJ files from adjacent frames (N-95 and N+95)
   - Cuts away ~3% from both edges
   - Blends remaining edge vertices toward the adjacent frame's OBJ mesh edge vertices
   - Writes the modified meshes to output folder

**Seamless blending script** (`apply_seamless_blending.py`):
   - Takes the exported OBJ folder as input
   - Takes the Blender simulation file to read reference mesh position only
   - Takes the frame offset as a configurable parameter (default: -95, negative = earlier frame)
   - For each frame N:
     1. Load the exported OBJ mesh for frame N
     2. Load exported OBJ from frame N-95 (for right edge blending)
     3. Load exported OBJ from frame N+95 (for left edge blending)
     4. Cut away ~3% from both edges (removes distorted vertices)
     5. Blend the edge vertices toward the adjacent OBJ mesh positions
   - Writes to output folder (default: /tmp/seamless_blended_meshes)

### Why Both Edges Need Blending

Since meshes are placed in sequence (0, 95, 190, 285, ...), both edges of each mesh need blending:
- Mesh 0's RIGHT edge blends toward mesh 95's LEFT edge (mesh 95 is placed to the right)
- Mesh 0's LEFT edge blends toward mesh -95's RIGHT edge (earlier mesh placed to the left, with wraparound)

This creates seamless transitions for infinite side-by-side placement in both directions.

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `input_folder` | (required) | Path to folder containing exported OBJ files |
| `output_folder` | /tmp/seamless_blended_meshes | Path to output folder |
| `blend_file` | (required) | Path to Blender simulation file (for reading reference mesh position ONLY) |
| `reference_mesh` | 1_0_mesh_903_reference | **CRITICAL**: Name of reference mesh in Blender file that defines the position offset for adjacent meshes |
| `frame_offset` | -95 | Frame offset to adjacent mesh (negative = earlier frame placed to the right) |
| `cut_width_percent` | 3.0 | Width of edge to cut away as percentage of mesh width |
| `blend_width_percent` | 3.0 | Width of the blend zone as percentage of mesh width (same as cut width) |
| `blend_axis` | "x" | Axis along which meshes are placed side by side ("x", "y", or "z") |
| `left_edge_chunk` | 0 | X index of left edge chunks (for 3x1 grid) |
| `right_edge_chunk` | 2 | X index of right edge chunks (for 3x1 grid) |

## Reference Mesh Setup (CRITICAL - Required One-Time Setup)

**The reference mesh is REQUIRED** to determine the exact position offset where adjacent meshes are placed. Without this, the blending cannot know where the adjacent mesh will be positioned in Unreal.

### Setup Steps:
1. Open the simulation Blender file
2. Import a reference mesh (e.g., an OBJ from the frame that will be placed adjacent - typically frame N-95)
   - Use import settings: Forward=X, Up=Z (to match export settings)
3. Position it exactly where it would be placed adjacent to frame 0 in Unreal (edge-to-edge)
4. Name the imported mesh `1_0_mesh_903_reference` (this is the default name the script looks for)
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
   - The script reads the reference mesh position from Blender, then processes OBJ files directly
   - Example: `python apply_seamless_blending.py --blend-file ../3dmodels/breaking_waves_beach_break_2.blend --input /hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_05`
   - Outputs to `/tmp/seamless_blended_meshes` by default
   - Fast to run, can iterate multiple times with different parameters

4. **Import to Unreal** (unchanged):
   - Import the blended OBJ files as before

## Technical Considerations

- The blend needs to work for all frames in the animation
- Each frame N blends toward adjacent frames' OBJ meshes (N-offset for right, N+offset for left)
- For frames near the start/end of the animation, wrap around (modulo)
- The chunk splitting (3x1 grid) needs consideration - only edge chunks along the blend axis need blending
- Vertex interpolation should use smooth falloff (smoothstep) to avoid harsh transitions
- Script must parse OBJ files, modify vertex positions, and write back valid OBJ files
- OBJ-to-OBJ blending works because both meshes have been decimated with the same settings
- Should process all quality level folders if specified, or a single folder
- Cutting edges will remove some geometry - faces referencing removed vertices are removed
- The cut removes the distorted edge caused by decimation/export compression

## Implementation Notes

### Cut and Blend Algorithm (OBJ-to-OBJ)

1. **Load exported OBJ mesh** for frame N
2. **Load adjacent OBJ meshes**:
   - For right edge: load left-edge chunk from frame N+frame_offset
   - For left edge: load right-edge chunk from frame N-frame_offset
3. **Calculate cut boundaries**:
   - Right: mesh_max - (mesh_width * cut_width_percent / 100)
   - Left: mesh_min + (mesh_width * cut_width_percent / 100)
4. **Remove vertices beyond cut boundaries** (the distorted edges)
5. **For vertices in the blend zones**:
   - Build spatial lookup of adjacent OBJ vertices (keyed by non-blend axis coordinates)
   - Determine blend factor based on position (0.0 at inner edge, 1.0 at outer edge)
   - Apply smooth falloff: `smoothstep(blend_factor)`
   - Find corresponding vertex in adjacent OBJ mesh's edge
   - Apply position offset to get world position
   - Interpolate: `final_pos = lerp(current_pos, target_pos + offset, smooth_blend_factor)`
6. **Remove faces** that reference removed vertices

### Chunk Handling

Since meshes are split into 3x1 chunks:
- Only chunks on the blend edges need modification
- For X-axis blending:
  - Right edge chunks at x=2 (rightmost column) - blend toward adjacent frame's x=0 (leftmost) chunk
  - Left edge chunks at x=0 (leftmost column) - blend toward adjacent frame's x=2 (rightmost) chunk
- Middle chunks (x=1) are copied unchanged

## Success Criteria

- Adjacent meshes appear seamless when viewed in Unreal Engine
- No visible seam or discontinuity at any viewing distance
- Works for infinite side-by-side mesh placement
- Animation still loops correctly
- Performance impact is negligible (same polygon count)
- Configurable axis allows adjustment if X is not correct
