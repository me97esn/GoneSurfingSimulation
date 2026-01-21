# Spec: export_waves_display


## Overview
Create a script that exports the fluid surface from blender to obj files. Split up into smaller chunks.

## Objective


## Requirements

### Functional Requirements
1. **FR-1**: It should load the blender file, similar to how the open_simulation.sh does. It should go to start_frame, specified as an input to the script.
2. **FR-2**: It should add a boolean modifier to the fluid_surface mesh. The boolean should use 'difference', with the BoolBoundary as input 
3. **FR-3**: It should add a Decimate modifier to the fluid_surface mesh, after the boolean modifier, with settings: Collapse, ratio: 0.05
4
4. **FR-4**: It should split the fluid_surface mesh into smaller chunks. The mesh should be split 3 times along it's longest axis, and 1 time along it's second longest axis. It should split into a total of 3x1 chunks.
5. **FR-5**: It should export each chunk as an obj file. The name of the file should be {x chunk number}_{y chunk number}_mesh_{frame number}.obj. The folder where to store the files should be configurable, with default value '/hdd/gone_surfing_exports/medium_wave_left/chunks_epic_resolution'. So it should export 0_0_mesh_758.obj, 0_1_mesh_758.obj... if the start frame is 758.
6. **FR-6**: It should repeat **FR-2** to **FR-5** for each frame from start_frame to end_frame (which should also be configurable).
7. **FR-7**: It should repeat **FR-2** to **FR-6** again, but now with other values for the modifier in **FR-3**. It should now use Collapse, ratio: 0.04. The folder where to export, in **FR-5**, should be the another folder with default value '/hdd/gone_surfing_exports/medium_wave_left/chunks_higher_resolution'
8. **FR-8**: It should repeat **FR-7** again multiple times, with ratio decreasing 0.01 each time down to 0.01
9. **FR-9**: It should update the readme, the part about "Export the wave animation (Alternative stop motion meshes for use in mobile games)", with info about how to run the script.
10. **FR-10**: The mesh chunks shall use fixed world coordinates across all frames. The chunk boundaries must be calculated once from the start_frame's bounding box and then reused for all subsequent frames, ensuring that each chunk (e.g., 0_0, 0_1, etc.) represents the same spatial region in every frame.
11. **FR-11**: The chunks shall have straight edges created by using plane bisection operations, ensuring clean rectangular boundaries instead of jagged edges following vertex positions.
12. **FR-12**: The script shall remove the flat bottom plane created by the boolean modifier while preserving the underside of breaking waves. This is done by removing only nearly-horizontal downward-facing faces (Z-normal < -0.95) after the boolean operation. This threshold preserves curved/angled surfaces like wave undersides while removing the flat bottom.

### Non-Functional Requirements


## Acceptance Criteria


## Implementation Details


## Notes for AI Agent


## Status

- [x] Specification written
- [x] Implementation complete
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Merged to main

## Implementation Notes

### Implementation Overview
- Created `export_waves_display.py` - Python script that runs inside Blender
- Created `export_waves_display.sh` - Bash wrapper with configurable parameters
- Updated README with automated workflow instructions

### FR-1 Implementation (Load Blender file):
- Bash script loads the Blender file using `blender --background` command
- Start frame is passed as command-line argument (default: 752)
- Python script receives arguments via `sys.argv` after `--` separator

### FR-2 Implementation (Boolean modifier):
- Python script adds Boolean modifier to `fluid_surface` mesh
- Uses 'DIFFERENCE' operation with `BoolBoundary` object
- Automatically detects if BoolBoundary exists, warns if not found
- Creates a flat bottom surface at the cut plane (removed by FR-12)

### FR-3 Implementation (Decimate modifier):
- Adds Decimate modifier with 'COLLAPSE' type
- Ratio is configurable per quality level
- Applied after boolean modifier, before FR-12 face removal

### FR-4 Implementation (Split into chunks):
- Automatically determines longest and second-longest axes
- Splits 3 times along longest axis, 1 time along second longest
- Total of 3 chunks (3×1) per frame
- Uses bmesh operations to isolate vertices within each chunk's bounds

### FR-5 Implementation (Export chunks):
- Exports each chunk as separate OBJ file
- Naming format: `{x}_{y}_mesh_{frame}.obj`
- Default output folder: `/hdd/gone_surfing_exports/medium_wave_left/chunks_epic_resolution`
- Uses Blender's `wm.obj_export` with settings: forward='X', up='Z'

### FR-6 Implementation (Process all frames):
- Loops from start_frame to end_frame (inclusive)
- Each frame processed independently
- Progress indicator shows every 10 frames

### FR-7 & FR-8 Implementation (Multiple quality levels):
- Processes 5 quality levels: 0.05, 0.04, 0.03, 0.02, 0.01
- First level (0.05) outputs to `chunks_epic_resolution`
- Second level (0.04) outputs to `chunks_higher_resolution`
- Remaining levels output to `chunks_ratio_0_0X`
- Each quality level is a complete independent export

### FR-9 Implementation (Update README):
- Updated "Export the wave animation (Alternative stop motion meshes)" section
- Replaced 5-step manual process with single command
- Added usage examples and output directory descriptions
- Documented import process for Unreal Engine

### FR-10 Implementation (Fixed world coordinates):
- Chunk boundaries calculated once from start_frame's bounding box
- Boundaries stored and reused for all subsequent frames
- Ensures each chunk (0_0, 0_1, etc.) represents same spatial region in every frame
- Critical for Unreal Engine's Niagara system and MeshArrayActor consistency

### FR-11 Implementation (Straight edges):
- Uses `bmesh.ops.bisect_plane()` to cut mesh at exact chunk boundaries
- Creates 4 bisect planes per chunk (min/max on primary and secondary axes)
- `clear_outer=True` removes geometry outside the boundary
- Results in perfectly rectangular chunks with straight edges

### FR-12 Implementation (Remove flat bottom faces):
- Applied to the full mesh BEFORE chunking (critical for consistent results)
- Uses `bmesh.ops.recalc_face_normals()` to ensure normals are correctly oriented
- Iterates through all faces and identifies those with Z-normal < -0.95
- Removes only nearly-horizontal downward-facing faces using `bmesh.ops.delete()`
- Threshold of -0.95 preserves curved/angled surfaces like wave undersides
- Only removes the flat bottom plane created by the boolean modifier
- Must be done before chunking because recalculating normals on individual chunks can cause unpredictable flipping

### Script Features:
- **Fully automated**: Runs in Blender background mode, no GUI interaction
- **Configurable**: Command-line arguments for start/end frames and output directory
- **Progress tracking**: Prints status for each frame and chunk
- **Error handling**: Validates input files exist, provides helpful error messages
- **Summary statistics**: Shows total files created per quality level

### Usage:
```bash
# Basic usage with defaults
./export_waves_display.sh

# Custom frame range
./export_waves_display.sh 752 868

# Custom output directory
./export_waves_display.sh 752 868 /custom/output
```

### Performance Notes:
- Processing time depends on mesh complexity and frame count
- Each quality level processes all frames independently
- Total files: 5 quality levels × frame count × 3 chunks
- Example: 117 frames = 1,755 OBJ files total
