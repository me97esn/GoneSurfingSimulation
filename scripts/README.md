# Generating data

## Run the simulation

run the script `./open_simulation.sh` to open blender with the simulation. This is needed for the generation of the water forces (blur files).
To start the simulation emidiately, run the script `./run_simulation.sh`

## Export the wave animation (Alternative stop motion meshes for use in mobile games)

1. From blender, open the file breaking_waves_beach_break_2_water_display.blend.
2. Make sure that the bottom side of the simulation is completely flat. There should be a boolean modifier that cuts off the bottom of the water mesh.
3. Add a decimate modifier to reduce the polycount. A decimate ratio of 0.005 was used for the epic resolution.
4. Export the anmitation as obj, animation.
5. In blender, import the meshes. Then use the button in the MeshArrayActor to load the meshes inte the Niagara system.

## White water

### Export white water particles from Blender

1. Run `./open_simulation.sh`
2. Set the start frame to the correct start frame (don't have to be 0) and the end frame to the same as in the wave animation export (868)
3. Select the white water foam object
4. Export as obj files. Settings:
   - Selection only
   - Object as Obj Objects
   - Animation
   - Forward: X Forward
   - Up: Z Up

### Convert to Niagara Datatable format (for Unreal Engine)

1. Open the script `export_white_water_points.js`
   - Make sure that the `dir` variable points to the folder containing the exported OBJ files
   - Make sure that `startFrame` matches the frame number used in the export
2. Run the script:
   ```bash
   node export_white_water_points.js [output_file_path]
   ```
   - If no output path is provided, the file will be saved as `white-water-points-data.json` in the source directory
3. In UE4/UE5, import the JSON file as a datatable
4. In UE4/UE5, configure your Niagara particle system to use the imported datatable

**Note**: This script exports particle positions in the same format as `export_ocean_points.py` (WavePointsData format), making it compatible with Niagara systems that use this structure.

## Water height

1. From a terminal, run `./open_simulation.sh`. This makes sure that the blender with FlipFluids addon installed is used

1. Open the file ./export_ocean_points.py, change the start_frame, end_frame and step to match the simulation. Note that shorter step_size requires more frequencies to be used in the ifft, otherwise the result will be worse then with big step size.
   1.Open a Text Editor view in Blender.
   1.Press Alt + O, or go to Text>Open Text Block and open the .py file
   1.Then simply press Run script :D
1. After the export is finished: The samples are converted in the same step as the velocity data below

## Water forces/velocities

For the water velocities, bjson files are read.

1. Open the file create_water_velocity_datatable.js. Make sure that the path for flip_fluid_cache_folder is the correct one (should match the folder used in the Simulation)
2. Open the file ./create_water_velocity_datatables.sh. Change the numbers to match the start and end frames. These should be split up into multiple scripts, each with different frame numbers.
3. run the script `./create_water_velocity_datatables.sh`. This creates datatables for the water velocity to be imported into UE4
4. Import the files into UE4 as WaveVerticesLocations_Struct
