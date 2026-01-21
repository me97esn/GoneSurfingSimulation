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

1. **One-time setup in Blender**: User imports one of the exported OBJ files (e.g., frame 85) into the original Blender file and positions it exactly where it would be placed in the game relative to frame 0. This establishes the spatial relationship between adjacent meshes.

2. **Integrated into export pipeline**: Modify the existing export scripts to:
   - Take the frame offset as a configurable parameter (default: 85)
   - For each frame N being exported, also load the geometry from frame N+offset
   - Create a transition zone on one edge (~5% of mesh width)
   - Interpolate vertex positions in the transition zone to match frame N+offset's corresponding edge
   - Export the blended mesh

### Why One Edge is Sufficient

Since meshes are placed in sequence (0, 85, 170, 255, ...), blending only the "right" edge of each mesh is sufficient:
- Mesh 0's right edge blends toward mesh 85
- Mesh 85's right edge blends toward mesh 170
- And so on...

This creates seamless transitions for infinite side-by-side placement.

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `frame_offset` | 85 | Number of frames between adjacent meshes |
| `blend_width_percent` | 5.0 | Width of the transition zone as percentage of mesh width |
| `blend_axis` | "x" | Axis along which meshes are placed side by side ("x", "y", or "z") |
| `blend_direction` | "positive" | Which edge to blend ("positive" or "negative" end of the axis) |
| `reference_mesh_name` | (user specified) | Name of the imported reference mesh used to establish positioning |

## Workflow

1. **One-time setup**:
   - Open the original Blender file
   - Import a reference mesh (e.g., frame 85 OBJ)
   - Position it exactly where it would be placed in the game relative to frame 0
   - Note the position offset for the export script

2. **Export with blending**:
   - Run the modified export script with frame offset parameter
   - Script automatically blends each frame's edge with frame+offset
   - Meshes are exported ready for seamless placement

## Technical Considerations

- The blend needs to work for all frames in the animation
- Each frame N should blend seamlessly with frame N+offset
- For frames near the end of the animation where N+offset exceeds total frames, wrap around (modulo)
- The chunk splitting (8x3 grid) needs consideration - only edge chunks along the blend axis need blending
- Vertex interpolation should use smooth falloff (e.g., ease-in-out) to avoid harsh transitions
- The reference mesh positioning determines the spatial offset between adjacent meshes

## Implementation Notes

### Blending Algorithm

For vertices in the transition zone:
1. Determine blend factor based on position (0.0 at inner edge, 1.0 at outer edge)
2. Apply smooth falloff: `smoothstep(blend_factor)` or similar
3. Find corresponding vertex position in the offset frame's mesh
4. Interpolate: `final_pos = lerp(original_pos, target_pos, smooth_blend_factor)`

### Chunk Handling

Since meshes are split into 8x3 chunks:
- Only chunks on the blend edge need modification
- For X-axis blending with positive direction: chunks at x=7 (rightmost column)
- Other chunks export unchanged

## Success Criteria

- Adjacent meshes appear seamless when viewed in Unreal Engine
- No visible seam or discontinuity at any viewing distance
- Works for infinite side-by-side mesh placement
- Animation still loops correctly
- Performance impact is negligible (same polygon count)
- Configurable axis allows adjustment if X is not correct
