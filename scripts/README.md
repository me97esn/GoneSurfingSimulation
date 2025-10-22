# Generating data

## Run the simulation

run the script `./open_simulation.sh` to open blender with the simulation. This is needed for the generation of the water forces (blur files).

## Export the wave animation (Alternative: Alembic, for use in desktop games)

. From blender, open the file breaking_waves_beach_break_2_water_display.blend. Add or edit modifier:Remesh with settings, voxelsize: 0.5, adaptivity: 0.
2. Set the start frame to 1 (Important! Even if the waves should start at a later frame, the animation has to be exported from the first frame, otherwise it will be corrupted) and the end frame to prefered end frame (currently 868). NOTE: Last time I wrote this, I wrote 0. But this doesn't work and I beleive this is incorrect. frame 0 gave an error when trying to import into UE4. But this could be because both the simulation and the animation starts at frame 1. Perhaps the important thing is to start on the first simulation&animation frame?
3. Select the water and export as alembic: Selected objects only, scale: 1.000,
   uncheck: Vertex colors, Face sets, Use subdivision Schema, Apply subsurf, Curves as Mesh, Triangulate,;Export hair, Export particles, Flatten hierarchy
   Check: Normals, Visible objects only, Renderable objects only, UVs, Pack UV Islands

4. To export the simulation from blender to UE4, use alembic exporter. But for this exporter to export the animation, and not only the first frame, a modifier has to be added to the water surface (as of this writing. This bug should be fixed by now, but apparantly isn't).
5. Go to frame 1, and set the simulation and animation to start on frame 1
6. To choose resolution, choose the Water surface, and change the Flip fluids setting to display preview in the render and viewport.
7. To import this animation into ue4: use geometry cache which imports the entire animation. I have often had problems with normals being on the inside. I have not been able to solve that satisfactory, but the way I handle it is by setting the water material in UE4 to be double sided.

## Export the wave animation (Alternative json file, for use in mobile games)
1. From blender, open the file breaking_waves_beach_break_2_water_display.blend. 
2. Open a Text Editor view in Blender.
3. Press Alt + O, or go to Text>Open Text Block and open the export_ocean_points.py file
4. adjust the start frame and end frame. Roughly 300 frames works, but exporting too much crashes blender.
5. Adjust the resulting file name. If the export is split into multiple files, a new file name has to be choosen.
6. Then simply press Run script :D
7. The json file(s) can then be imported into Unreal using the WavePointsDataStruct.


## Import the alembic animation into UE4

1. Import the animation as geometry cache. It should start from the startframe, _not_ from frame 1. I have hade problems with scale and rotation, it seems to vary how it behaves. Be prepared to play around with scale at import time if the imported animation looks too small (scaling after import also works, but the animation has to be roughly correct scale at import to be of good quality)
2. To place the animation at the correct place: open WaterController, and in construction script enable the "display all blocks" node. Then make sure that the alembic animation and the blocks align.

- Sometimes the scale is very small. I don't know why, but it seems that I can manually change the scale at import time.

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

1. Open the script `export_white_water_plain_niagara_datatable.js`
   - Make sure that the `dir` variable points to the folder containing the exported OBJ files
   - Make sure that `startFrame` matches the frame number used in the export
2. Run the script:
   ```bash
   node export_white_water_plain_niagara_datatable.js [output_file_path]
   ```
   - If no output path is provided, the file will be saved as `white-water-points-data.json` in the source directory
3. In UE4/UE5, import the JSON file as a datatable
4. In UE4/UE5, configure your Niagara particle system to use the imported datatable

**Note**: This script exports particle positions in the same format as `export_ocean_points.py` (WavePointsData format), making it compatible with Niagara systems that use this structure.

## Water height

1. From a terminal, run `./open_simulation.sh`. This makes sure that the blender with FlipFluids addon installed is used

1. Open the file ./export_fluid_surface_to_3d_samples.py, change the start_frame, end_frame and step to match the simulation. Note that shorter step_size requires more frequencies to be used in the ifft, otherwise the result will be worse then with big step size.
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
