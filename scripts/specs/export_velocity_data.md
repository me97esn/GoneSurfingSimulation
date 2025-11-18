# Spec: create-script-for-exporting-ocean-surface-samples

## Overview


## Objective


## Requirements

### Functional Requirements

1. **FR-1**: The implementation shall create a script to export blur data (aka velocities) named export_wave_velocity_single_line
2. **FR-2**: The script shall be inspired by the create_water_velocity_datatable.sh in that it should read the same files, extract the same data as this does. But instead of writing multiple files, it should collect everything in one single file
2. **FR-2**: The output file should be in the WavePointsData_Example.json format.
2. **FR-2**: The output from the create_water_velocity_datatable.sh file stores data for all vertices. This new script shall store the data for one line only, going along the y axis. 
3. **FR-3**: The script shall first scan through all of the vertices of the start frame to find the vertex with the biggest sum of blur.x + blur.y + blur.z. When it has found this vertex, it should use this position to use as the second **FR-2**.
4. **FR-4**: An update to the second **FR-2**: I don't know if it should be along the y axis, x or z axis. It should create one result file for each of these axises.
5. **FR-5**: If no vertice is found when looking at the exact position along the line in **FR-2** and **FR-4**, a vertex nearby can be used.

### Non-Functional Requirements

## Acceptance Criteria

## Implementation Details

## Notes for AI Agent

- Implement as a python script or keep it as nodejs, both is ok.
- The amount of data handled can be rather big. There is apx 200 bobj files, each apx 8 MByte.

## Status

- [x] Specification written
- [x] Implementation complete
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Merged to main

## Implementation Notes

- Created `export_wave_velocity_single_line.js` in `/home/emil/workspace/GoneSurfingSimulation/scripts/`
- Implemented as Node.js script to match existing infrastructure
- Reads `.bobj` and `blur*.bobj` files from FLIP Fluids cache
- Outputs in WavePointsData format with "Velocities" array instead of "Normals"
- Processes frames 905-1101
- Memory efficient: processes files sequentially, doesn't load all data at once

### FR-3 Implementation (Auto-detect highest velocity):
- Scans all vertices in the start frame (905)
- Calculates velocity magnitude: sqrt(vx² + vy² + vz²) for each vertex
- Identifies the vertex with the maximum velocity magnitude
- Uses this vertex's position as the sampling line location

### FR-4 Implementation (Three output files for each axis):
- Creates three separate output files:
  1. `wave-velocity-line-x.json` - Samples along Y and Z axes at fixed X position
  2. `wave-velocity-line-y.json` - Samples along X and Z axes at fixed Y position
  3. `wave-velocity-line-z.json` - Samples along X and Y axes at fixed Z position
- Each file contains vertices near the detected highest-velocity position

### FR-5 Implementation (Nearby vertex tolerance):
- `position_tolerance = 0.5` - Tolerance for matching vertices (±0.5 units)
- Captures vertices within tolerance distance of the target line
- Ensures data is captured even if exact position doesn't have vertices

### Configuration:
- `position_tolerance = 0.5` - Distance tolerance for matching vertices
- `start_frame = 905`, `end_frame = 1101` - Frame range
- Output directory: `/hdd/gone_surfing_exports/medium_wave_left/`

### Expected Output:
- Three JSON files, each with velocity data along one axis
- Number of samples per frame depends on fluid simulation mesh density
- Each frame contains Position (X, Y, Z) and Velocity (X, Y, Z) arrays
