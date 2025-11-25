# Generating data

## Run the simulation

run the script `./open_simulation.sh` to open blender with the simulation. This is needed for the generation of the water forces (blur files).
Also click the flip fluids sidebar and the button about enabling blur data https://github.com/rlguy/Blender-FLIP-Fluids/wiki/Domain-Attributes-and-Data-Settings#motion-blur-rendering-automatic-setup.

To start the simulation immediately, and make sure it restarts if it crashes, run the script `./run_simulation.sh`

## Export the wave animation (Alternative: Alembic, for use in desktop games)

. From blender, open the file breaking_waves_beach_break_2_water_display.blend. Add or edit modifier:Remesh with settings, voxelsize: 0.5, adaptivity: 0. 2. Set the start frame to 1 (Important! Even if the waves should start at a later frame, the animation has to be exported from the first frame, otherwise it will be corrupted) and the end frame to prefered end frame (currently 868). NOTE: Last time I wrote this, I wrote 0. But this doesn't work and I beleive this is incorrect. frame 0 gave an error when trying to import into UE4. But this could be because both the simulation and the animation starts at frame 1. Perhaps the important thing is to start on the first simulation&animation frame? 3. Select the water and export as alembic: Selected objects only, scale: 1.000,
uncheck: Vertex colors, Face sets, Use subdivision Schema, Apply subsurf, Curves as Mesh, Triangulate,;Export hair, Export particles, Flatten hierarchy
Check: Normals, Visible objects only, Renderable objects only, UVs, Pack UV Islands

4. To export the simulation from blender to UE4, use alembic exporter. But for this exporter to export the animation, and not only the first frame, a modifier has to be added to the water surface (as of this writing. This bug should be fixed by now, but apparantly isn't).
5. Go to frame 1, and set the simulation and animation to start on frame 1
6. To choose resolution, choose the Water surface, and change the Flip fluids setting to display preview in the render and viewport.
7. To import this animation into ue4: use geometry cache which imports the entire animation. I have often had problems with normals being on the inside. I have not been able to solve that satisfactory, but the way I handle it is by setting the water material in UE4 to be double sided.

## Export the wave animation (Alternative stop motion meshes for use in mobile games)

Run the automated export script:

```bash
./export_waves_display.sh [start_frame] [end_frame] [output_dir]
```

**Examples**:

```bash
# Use defaults (frames 752-868)
./export_waves_display.sh

# Custom frame range
./export_waves_display.sh 752 868

# Custom frame range and output directory
./export_waves_display.sh 752 868 /hdd/exports
```

This script will:
1. Load the Blender file `breaking_waves_beach_break_2.blend` in background mode
2. Apply a boolean modifier (difference with BoolBoundary) to flatten the bottom
3. Apply decimate modifiers at multiple quality levels (ratios: 0.05, 0.04, 0.03, 0.02, 0.01)
4. Split each frame into 24 chunks (3x8 grid along the longest axes)
5. Export each chunk as an OBJ file with naming: `{x}_{y}_mesh_{frame}.obj`

**Output directories** (created automatically):
- `chunks_epic_resolution` - Decimate ratio 0.05 (highest quality)
- `chunks_higher_resolution` - Decimate ratio 0.04
- `chunks_ratio_0_03` - Decimate ratio 0.03
- `chunks_ratio_0_02` - Decimate ratio 0.02
- `chunks_ratio_0_01` - Decimate ratio 0.01 (lowest quality, smallest file size)

**Import to Unreal Engine**:
1. Choose a quality level directory based on your performance needs
2. Import the OBJ meshes from that directory
3. Use the MeshArrayActor button to load the meshes into the Niagara system

The script runs fully automated in Blender's background mode, so no manual interaction is required.

## Import the alembic animation into UE4

1. Import the animation as geometry cache. It should start from the startframe, _not_ from frame 1. I have hade problems with scale and rotation, it seems to vary how it behaves. Be prepared to play around with scale at import time if the imported animation looks too small (scaling after import also works, but the animation has to be roughly correct scale at import to be of good quality)
2. To place the animation at the correct place: open WaterController, and in construction script enable the "display all blocks" node. Then make sure that the alembic animation and the blocks align.

- Sometimes the scale is very small. I don't know why, but it seems that I can manually change the scale at import time.

## White water

### Export white water particles and convert to Niagara Datatable format

Run the complete export script:

```bash
./export_white_water_complete.sh [start_frame] [end_frame]
```

**Examples**:

```bash
# Use defaults (frames 752-1325)
./export_white_water_complete.sh

./export_white_water_complete.sh 886 1078
```

This script will:

1. Export white water particles from Blender as OBJ files
2. Convert the OBJ files to Niagara Datatable format (creates 3 JSON files with different rotations)
3. Output files to `/hdd/gone_surfing_exports/medium_wave_left/white_water/`

The script runs Blender in background mode and automatically finds the white water foam object, so no manual interaction is required.

**Advanced Configuration**: Edit `export_white_water_complete.sh` to change:

- `OUTPUT_DIR` - Where to save the files (default: `/hdd/gone_surfing_exports/medium_wave_left/white_water`)
- `BLEND_FILE` - Path to the .blend file (default: `../3dmodels/breaking_waves_beach_break_2.blend`)

**Output files**:

- `white-water-points-data-rotX.json` - Rotated 90° around X-axis
- `white-water-points-data-rotY.json` - Rotated 90° around Y-axis
- `white-water-points-data-rotZ.json` - Rotated 90° around Z-axis

**Import to Unreal**: Import one of the JSON files as a datatable and configure your Niagara particle system to use it. The files are in WavePointsData format, compatible with Niagara systems.

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
