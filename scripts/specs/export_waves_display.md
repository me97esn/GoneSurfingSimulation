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
4. **FR-4**: It should split the fluid_surface mesh into smaller chunks. The mesh should be split 3 times along it's longest axis, and 8 times along it's second longest axis. It should split into a total of 3*8 equally sized chunks.
5. **FR-5**: It should export each chunk as an obj file. The name of the file should be {x chunk number}_{y chunk number}_mesh_{frame number}.obj. The folder where to store the files should be configurable, with default value '/hdd/gone_surfing_exports/medium_wave_left/chunks_epic_resolution'. So it should export 0_0_mesh_758.obj, 0_1_mesh_758.obj... if the start frame is 758.
6. **FR-6**: It should repeat **FR-2** to **FR-5** for each frame from start_frame to end_frame (which should also be configurable).
7. **FR-7**: It should repeat **FR-2** to **FR-6** again, but now with other values for the modifier in **FR-3**. It should now use Collapse, ratio: 0.04. The folder where to export, in **FR-5**, should be the another folder with default value '/hdd/gone_surfing_exports/medium_wave_left/chunks_higher_resolution'
8. **FR-8**: It should repeat **FR-7** again multiple times, with ratio decreasing 0.01 each time down to 0.01

### Non-Functional Requirements


## Acceptance Criteria


## Implementation Details


## Notes for AI Agent


## Status

- [ ] Specification written
- [ ] Implementation complete
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Merged to main

## Implementation Notes
