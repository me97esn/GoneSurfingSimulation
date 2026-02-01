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

### Parallel Export (Recommended - Much Faster!)

For large frame ranges, use the parallel version which splits work across multiple CPU cores:

```bash
./export_waves_display_parallel.sh [start_frame] [end_frame] [output_dir] [skip_existing] [num_jobs]
```

**Parameters**:

- `start_frame`: Starting frame number (default: 752)
- `end_frame`: Ending frame number (default: 868)
- `output_dir`: Base output directory (default: `/hdd/gone_surfing_exports/medium_wave_left`)
- `skip_existing`: `skip` to skip existing files (resume), `overwrite` to overwrite all (default: `skip`)
- `num_jobs`: Number of parallel jobs (default: 8)

**Examples**:

```bash
# Use defaults (8 parallel jobs, frames 752-868)
./export_waves_display_parallel.sh

# Custom frame range with 8 parallel jobs
./export_waves_display_parallel.sh 752 868

# Use 4 parallel jobs (if you have fewer cores)
./export_waves_display_parallel.sh 752 868 /hdd/exports skip 4

# Maximum speed with 8 cores
./export_waves_display_parallel.sh 752 868 /hdd/exports skip 8
```

**Performance**: With 8 cores, this can be up to ~8x faster than the sequential version (e.g., 200 hours → ~25 hours).

**Monitoring**: Progress logs are saved to `{output_dir}/parallel_logs/` for each job. You can tail these files to monitor progress.

### Sequential Export (Single-threaded)

For smaller jobs or debugging, use the sequential version:

```bash
./export_waves_display.sh [start_frame] [end_frame] [output_dir] [skip_existing]
```

**Examples**:

```bash
# Use defaults (frames 752-868, skip existing files)
./export_waves_display.sh

# Custom frame range, skip existing files (resume interrupted export)
./export_waves_display.sh 752 868

# Custom frame range and output directory, skip existing
./export_waves_display.sh 752 868 /hdd/exports

# Overwrite all files (re-export everything)
./export_waves_display.sh 752 868 /hdd/exports overwrite

# Resume from where export stopped (skip existing files)
./export_waves_display.sh 752 868 /hdd/exports skip
```

This script will:

1. Load the Blender file `breaking_waves_beach_break_2.blend` in background mode
2. Apply a boolean modifier (difference with BoolBoundary) to flatten the bottom
3. Apply decimate modifiers at multiple quality levels (ratios: 0.1 to 0.01 in steps of 0.01)
4. Split each frame into 3 chunks (3x1 grid along the longest axis)
5. Export each chunk as an OBJ file with naming: `{x}_{y}_mesh_{frame}.obj`

**Output directories** (created automatically, from highest to lowest quality):

- `chunks_ratio_0_1` - Decimate ratio 0.1 (highest quality, 10% of polygons retained, largest file size)
- `chunks_ratio_0_09` - Decimate ratio 0.09 (9% of polygons retained)
- `chunks_ratio_0_08` - Decimate ratio 0.08 (8% of polygons retained)
- `chunks_ratio_0_07` - Decimate ratio 0.07 (7% of polygons retained)
- `chunks_ratio_0_06` - Decimate ratio 0.06 (6% of polygons retained)
- `chunks_ratio_0_05` - Decimate ratio 0.05 (5% of polygons retained)
- `chunks_ratio_0_04` - Decimate ratio 0.04 (4% of polygons retained)
- `chunks_ratio_0_03` - Decimate ratio 0.03 (3% of polygons retained)
- `chunks_ratio_0_02` - Decimate ratio 0.02 (2% of polygons retained)
- `chunks_ratio_0_01` - Decimate ratio 0.01 (lowest quality, 1% of polygons retained, smallest file size)

**Import to Unreal Engine**:

1. Choose a quality level directory based on your performance needs
2. Import the OBJ meshes from that directory
3. Use the MeshArrayActor button to load the meshes into the Niagara system

The script runs fully automated in Blender's background mode, so no manual interaction is required.

### Apply Seamless Blending (Optional)

If you're placing meshes side by side to create an infinite scrollable wave, you can apply seamless blending to eliminate visible seams between adjacent meshes.

The exported meshes have distorted/curved edges due to decimation. The blending script:

1. Cuts away the distorted edges (~3% of mesh width) from both left and right sides
2. Blends the remaining edge vertices toward adjacent frame's exported OBJ mesh edges

This removes the curved edges and creates smooth transitions using matching decimated mesh data (OBJ-to-OBJ blending).

#### Step 1: One-time setup - Position reference mesh in Blender (REQUIRED)

The reference mesh is **required** to determine the exact position offset where adjacent meshes are placed.

1. Open the simulation Blender file
2. Import a reference mesh (e.g., an OBJ from the frame that will be placed adjacent - typically frame N-95)
   - Use import settings: Forward=X, Up=Z (to match export settings)
3. Position it exactly where it would be placed adjacent to frame 0 in Unreal (edge-to-edge)
4. Name the imported mesh `1_0_mesh_903_reference` (this is the default name the script looks for)
5. Save the Blender file

#### Step 2: Run the blending script

```bash
python apply_seamless_blending.py \
    --blend-file ../3dmodels/breaking_waves_beach_break_2.blend \
    --input /hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_05
```

**Parameters**:

- `--blend-file`: Path to the Blender simulation file (for reading reference mesh position ONLY)
- `--reference-mesh`: Name of reference mesh in Blender (default: `1_0_mesh_903_reference`)
- `--input`: Folder containing exported OBJ files
- `--output`: Output folder for blended meshes (default: `/tmp/seamless_blended_meshes`)
- `--frame-offset`: Frame offset to adjacent mesh (default: -95, negative = earlier frame)
- `--cut-width`: Width of edge to cut away as percentage (default: 3.0)
- `--blend-width`: Blend zone width as percentage (default: 3.0)
- `--blend-axis`: Axis along which meshes are placed: x, y, or z (default: x)
- `--left-edge-chunk`: X index of left edge chunks (default: 0)
- `--right-edge-chunk`: X index of right edge chunks (default: 2 for 3x1 grid)

The script reads the reference mesh position to determine the exact offset, then loads adjacent frames' OBJ files for blending. For each frame N:

- Right edge blends toward the LEFT edge of frame N+offset's OBJ (the mesh placed to the right)
- Left edge blends toward the RIGHT edge of frame N-offset's OBJ (the mesh placed to the left)

## Import the alembic animation into UE4

1. Import the animation as geometry cache. It should start from the startframe, _not_ from frame 1. I have hade problems with scale and rotation, it seems to vary how it behaves. Be prepared to play around with scale at import time if the imported animation looks too small (scaling after import also works, but the animation has to be roughly correct scale at import to be of good quality)
2. To place the animation at the correct place: open WaterController, and in construction script enable the "display all blocks" node. Then make sure that the alembic animation and the blocks align.

- Sometimes the scale is very small. I don't know why, but it seems that I can manually change the scale at import time.

## White water

### Export white water particles and convert to Niagara Datatable format

White water particles must be exported manually from Blender's GUI (background mode doesn't load the FLIP Fluids whitewater mesh cache).

#### Step 0: Remove the old obj files from the target folder (currently /hdd/gone_surfing_exports/medium_wave_left/white_water)

#### Step 1: Export OBJ files from Blender

1. Open Blender with the simulation file:

   ```bash
   blender ../3dmodels/breaking_waves_beach_break_2.blend
   ```

2. Switch to the **Scripting** workspace (tab at the top of Blender)

3. Open the export script:

   - Click **Open** button in the scripting panel
   - Navigate to and select `scripts/export_white_water_manual.py`

4. **Configure the export** (edit the script if needed):

   - `START_FRAME` - Starting frame number (default: 752)
   - `END_FRAME` - Ending frame number (default: 1325)
   - `OUTPUT_DIR` - Output directory (default: `/hdd/gone_surfing_exports/medium_wave_left/white_water`)
   - `EXPORT_FOAM` - Export foam particles (default: True)
   - Set `EXPORT_BUBBLE`, `EXPORT_SPRAY`, `EXPORT_DUST` to True if needed

5. Run the script:
   - Press **Alt+P** or click the ▶️ **Run Script** button
   - The script will print progress every 50 frames
   - Wait for completion (this may take a while for large frame ranges)

#### Step 2: Convert OBJ files to Unreal Niagara format

After the OBJ export completes, run the conversion script:

```bash
cd scripts
node export_white_water_points.js [start_frame] [end_frame]
```

**Examples**:

```bash
# Use defaults (frames 752-1325)
node export_white_water_points.js 752 1325

# Custom frame range
node export_white_water_points.js 886 1078
```

This will create 3 JSON files in the output directory:

- `white-water-points-data-rotX.json` - Rotated 90° around X-axis
- `white-water-points-data-rotY.json` - Rotated 90° around Y-axis
- `white-water-points-data-rotZ.json` - Rotated 90° around Z-axis

**Why manual export?** Blender's background mode doesn't properly load the FLIP Fluids whitewater mesh cache, resulting in empty exports. Running the export script from within Blender's GUI ensures the cache is properly loaded.

**Import to Unreal**: Import one of the JSON files as a datatable and configure your Niagara particle system to use it. The files are in WavePointsData format, compatible with Niagara systems. Compare the three rotation variants in Unreal to determine which axis produces the correct orientation.

## Water height

Export fluid surface height samples and normals to JSON files:

```bash
blender ../3dmodels/breaking_waves_beach_break_2.blend --background --python export_fluid_surface_to_3d_samples.py -- [start_frame] [end_frame] [output_dir] [step]
```

**Example:**

```bash
blender ../3dmodels/breaking_waves_beach_break_2.blend --background --python export_fluid_surface_to_3d_samples.py -- 886 1078 /hdd/gone_surfing_exports/medium_wave_left 2
```

**Parameters:**

- `start_frame`: Starting frame number (default: 752)
- `end_frame`: Ending frame number (default: 1325)
- `output_dir`: Output directory for JSON files (default: `/hdd/gone_surfing_exports/medium_wave_left`)
- `step`: Sample step size (default: 1). Note: shorter step_size requires more frequencies in the ifft

**Output files:**

- `wave_samples.json` - Height samples
- `wave_normals_x.json` - Normal X components
- `wave_normals_y.json` - Normal Y components
- `wave_normals_z.json` - Normal Z components

After the export is finished: The samples are converted in the same step as the velocity data below

## Water forces/velocities

For the water velocities, bjson files are read.

1. Open the file create_water_velocity_datatable.js. Make sure that the path for flip_fluid_cache_folder is the correct one (should match the folder used in the Simulation)
2. Open the file ./create_water_velocity_datatables.sh. Change the numbers to match the start and end frames. These should be split up into multiple scripts, each with different frame numbers.
3. run the script `./create_water_velocity_datatables.sh`. This creates datatables for the water velocity to be imported into UE4
4. Import the files into UE4 as WaveVerticesLocations_Struct
