# Generating data

## Run the simulation

run the script `./open_simulation.sh` to open blender with the simulation. This is needed for the generation of the water forces (blur files).

## Export the wave animation

1. From blender, open the file breaking_waves_beach_break_2_water_display.blend. Add or edit modifier:Remesh with settings, voxelsize: 0.5, adaptivity: 0.
2. Set the start frame to 1 (Important! Even if the waves should start at a later frame, the animation has to be exported from the first frame, otherwise it will be corrupted) and the end frame to prefered end frame (currently 868). NOTE: Last time I wrote this, I wrote 0. But this doesn't work and I beleive this is incorrect. frame 0 gave an error when trying to import into UE4. But this could be because both the simulation and the animation starts at frame 1. Perhaps the important thing is to start on the first simulation&animation frame?
3. Select the water and export as alembic: Selected objects only, scale: 1.000,
   uncheck: Vertex colors, Face sets, Use subdivision Schema, Apply subsurf, Curves as Mesh, Triangulate,;Export hair, Export particles, Flatten hierarchy
   Check: Normals, Visible objects only, Renderable objects only, UVs, Pack UV Islands

4. To export the simulation from blender to UE4, use alembic exporter. But for this exporter to export the animation, and not only the first frame, a modifier has to be added to the water surface (as of this writing. This bug should be fixed by now, but apparantly isn't).
5. Go to frame 1, and set the simulation and animation to start on frame 1
6. To choose resolution, choose the Water surface, and change the Flip fluids setting to display preview in the render and viewport.
7. To import this animation into ue4: use geometry cache which imports the entire animation. I have often had problems with normals being on the inside. I have not been able to solve that satisfactory, but the way I handle it is by setting the water material in UE4 to be double sided.

## Import the alembic animation into UE4

1. Import the animation as geometry cache. It should start from the startframe, _not_ from frame 1. I have hade problems with scale and rotation, it seems to vary how it behaves. Be prepared to play around with scale at import time if the imported animation looks too small (scaling after import also works, but the animation has to be roughly correct scale at import to be of good quality)
2. To place the animation at the correct place: open WaterController, and in construction script enable the "display all blocks" node. Then make sure that the alembic animation and the blocks align.

- Sometimes the scale is very small. I don't know why, but it seems that I can manually change the scale at import time.

## White water

1. run `./open_simulation.sh`
2. Set the start frame to the correct start frame (don't have to be 0) and the end frame to the same as in the wave animation export (868)
3. select the white water foam object
4. export as obj files. Settings:
   Selection only
   Object as Obj Objects
   Animation
   Forward: X Forward
   Up: Z Up
5. Open the script `convert_whitewater_obj_files_to_houdini_json.js`.
   - Make sure that the path in this file is the same as the previosly exported obj files
   - Make sure that the startFrame is correct
6. Run the script `./convert_whitewater_obj_files_to_hjson.sh` which creates a datatable file for UE4 to import
7. In UE4, re-import the json files
8. In UE4, re-compile the particle system

## Water forces/velocities

For the water velocities, bjson files are read.

1. Open the file create_water_velocity_datatable.js. Make sure that the path for flip_fluid_cache_folder is the correct one (should match the folder used in the Simulation)
2. Open the file ./create_water_velocity_datatables.sh. Change the numbers to match the start and end frames. These should be split up into multiple scripts, each with different frame numbers.
3. run the script `./create_water_velocity_datatables.sh`. This creates datatables for the water velocity to be imported into UE4
4. Import the files into UE4 as WaveVerticesLocations_Struct

## Water height

For water height, x3d files are read. Therefor a different script is used then for the wave forces.

1. The scripts append data to the target json files. The first step if these files should be newly created is to delete the old target json files. These are specified in the ./convert_x3d_files_to_ue4_datatable.sh file
1. From a terminal, run `./open_simulation.sh`. This makes sure that the blender with FlipFluids addon installed is used
1. Choose the water surface and modyfy the modifier: remesh to have the amount of resolution I prefer. The higher the less data, but make sure that the slopes are still close to the original, and that no part of the water surface disappears. I should probably have adaptivity:0
1. Open the file ./export_selection_as_x3d.py, change the start_frame and end_frame and copy the content.
1. In blender, select the fluid surface, click on Scripting and paste the content from the line above
1. Press enter twice to start the export
1. If the exported x3d files becomes too large to include in one json file, split them over multiple directories and adjust the script convert_x3d_files_to_ue4_datatable.sh accordingly
1. Open the file ./convert_x3d_files_to_ue4_datatable.sh and make sure that the url is the same one exported in the above step, and run it
   Note: I've noticed that if the generated json file is too large (500Mb in my case) I get an "infinite loop" error when playing in UE4.
1. In ue4, import the file as "WaveVerticesLocations_Struct"
