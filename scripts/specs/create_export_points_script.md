# Spec: create-script-for-exporting-ocean-surface-samples

## Overview
This exports the samples of the ocean surface in a format that can be imported into Unreal.
## Objective
This should create a script that can be run in blender, that exports all of the samples. 
## Requirements

### Functional Requirements
1. **FR-1**: The implementation shall create a script in the same folder as export_fluid_surface_to_3d_samples.py
2. **FR-2**: The created script should be similar to export_fluid_surface_to_3d_samples.py, but write the data in another format to another file.
3. **FR-3**: The created script should write json to a file with the format as in the WavePointsData_Example.json file.
4. **FR-4**: The keys for each row should be in the format "Frame_752" where the number is the frame number.
5. **FR-5**: The result json file should be named ocean-points-data.json
6. **FR-6**: The script file should be a python file
7. **FR-7**: Make sure that the python file is correctly indented and compiles
8. **FR-8**: The normal exported should not be normal value returned from the ray_cast function. The normal should instead be calculated. The way to calculate the normals is that each ray_cast should do another two raycast, one halfway to the next ray_cast location in y direction, and one halfway from the previous ray_cast location in the same direction. Then imagine a horisontal plane is placed so that it touches both of the two extra ray_cast hits. The plane should only be rotated around one axis.
The normal for this plane should be used as normal for this sample point.


### Non-Functional Requirements
1. **NFR-1**: The implementation shall be simple and readable
2. **NFR-2**: The code shall follow project coding standards

## Acceptance Criteria


## Implementation Details

## Notes for AI Agent
- Implement as a python script

## Status
- [x] Specification written
- [x] Implementation complete
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Merged to main

## Implementation Notes
- Created export_ocean_points.py in /home/emil/workspace/GoneSurfingSimulation/scripts/
- Script follows the same structure as export_fluid_surface_to_3d_samples.py
- Outputs JSON in the format matching WavePointsData_Example.json with Frame_XXX keys
- Output file: ocean-points-data.json
- Script successfully compiles with proper indentation
