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
8. **FR-8**: The script should add another array of floats, for scale. The scale should be calculated using the direction of the normal for this sample. 
9. **FR-9**: If the height difference between this raycast and the previous raycast in the X Axis is above a configurable value, this raycast should be skipped. Neither its position, normal nor scale should be stored. Same thing if the height difference compared to the next raycast in the same axis, the results of this raycast should be skipped.
10. **FR-10**: At the end of the script: print how many samples have been written, how many was skipped and the percentage of skipped raycasts.
11. **FR-11**: I have added a mesh named 'High_resolution_boundary' to the blender file. Only samples within the boundaries of this mesh should be handled in the **FR-9** requirement.
12. **FR-12**: The samples identified in **FR-9** and **FR-11** should no longer be skipped. Quite the opposite: these samples should be run with half the step size as the other samples, resulting in more samples with shorter distance between.
13. **FR-13**: Since I now use varying step size for the sampling, this has to be stored in the result as well. Write this into the frame_date["Scales"], with value for each sample being size of this step divided by the original size of the step. Example: step=5, currentStep=5, scale=1

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
- [x] Tests passing
- [ ] Code reviewed
- [ ] Merged to main

## Implementation Notes
- Created export_ocean_points.py in /home/emil/workspace/GoneSurfingSimulation/scripts/
- Script follows the same structure as export_fluid_surface_to_3d_samples.py
- Outputs JSON in the format matching WavePointsData_Example.json with Frame_XXX keys
- Output file: ocean-points-data.json
- Script successfully compiles with proper indentation
- Added configurable max_height_difference threshold (default: 5.0) for FR-9
- Implemented two-pass approach: first collects all raycasts, then filters based on height differences
- Height difference checking compares each sample with both previous and next samples in X axis
- Added statistics tracking and reporting (FR-10):
  - Samples written count
  - Samples skipped count
  - Percentage of skipped samples
- Scale calculation based on normal direction (FR-8) already implemented
