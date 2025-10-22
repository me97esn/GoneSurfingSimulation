# Spec: create-script-for-exporting-ocean-surface-samples

## Overview
Create a script for converting .obj files to UE Datatable.
## Objective
This script should export white water particles in the same format as the format used for water display particles. This data can be used by a Niagara particle system in Unreal to display the white water.
## Requirements

### Functional Requirements
1. **FR-1**: Create a new script called export_white_water_points.js
2. **FR-2**: The script shall write data in the format of WavePointsData_Example.json
3. **FR-3**: The keys in the resulting data table should be the same as those exported by export_ocean_points.py
4. **FR-4**: Update the README.md, the part about whitewater. Replace with info about how to run this script.
5. **FR-5**: The Normals and Scales can be empty arrays in the result file.
6. **FR-6**: The Positions array should be filled with position for each of the particle in the source files. The same way that convert_whitewater_obj_files_to_houdini_json.js reads positions from these files.

### Non-Functional Requirements
1. **NFR-1**: The implementation shall be simple and readable

## Acceptance Criteria


## Implementation Details
- Use Nodejs

## Notes for AI Agent
- Read the same files as the convert_whitewater_obj_files_to_houdini_json.js script.
- Don't split the result into multiple json files, keep everything in one file.

## Status
- [] Specification written
- [] Implementation complete
- [] Tests passing
- [ ] Code reviewed
- [ ] Merged to main