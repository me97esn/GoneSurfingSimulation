# Generating data

## Run the simulation

run the script `./open_simulation.sh` to open blender with the simulation. This is needed for the generation of the water forces (blur files).
Also click the flip fluids sidebar and the button about enabling blur data https://github.com/rlguy/Blender-FLIP-Fluids/wiki/Domain-Attributes-and-Data-Settings#motion-blur-rendering-automatic-setup.

To start the simulation immediately, and make sure it restarts if it crashes, run the script `./run_simulation.sh`

## Export wave animation + wave height data

This export produces both the stop-motion OBJ meshes and wave height/normal grid data from the same seamlessly blended mesh. The blending, chunking, decimation, and height sampling all happen in one step.

### One-time setup: Position reference mesh in Blender

The reference mesh determines the exact position offset where adjacent meshes are placed for seamless tiling.

1. Open the simulation Blender file
2. Import a reference mesh (e.g., an OBJ from the frame that will be placed adjacent - typically frame N-95)
   - Use import settings: Forward=X, Up=Z (to match export settings)
3. Position it exactly where it would be placed adjacent to frame 0 in Unreal (edge-to-edge)
4. Name the imported mesh `1_0_mesh_903_reference` (this is the default name the script looks for)
5. Save the Blender file

### Step 1: Run the export

#### Parallel Export (Recommended - Much Faster!)

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
```

**Performance**: With 8 cores, this can be up to ~8x faster than the sequential version.

**Monitoring**: Progress logs are saved to `{output_dir}/parallel_logs/` for each job.

#### Sequential Export (Single-threaded)

For smaller jobs or debugging:

```bash
blender ../3dmodels/breaking_waves_beach_break_2.blend --background --python export_waves_display.py -- <start_frame> <end_frame> <output_dir> <decimate_ratio> <skip_existing> <frame_offset> <reference_mesh_name> <grid_step_size>
```

**Example:**

```bash
blender ../3dmodels/breaking_waves_beach_break_2.blend --background --python export_waves_display.py -- 886 1078 //hdd/gone_surfing_exports/medium_wave_left/unified 0.03 skip -95 1_0_mesh_903_reference 2.0
```

**Parameters:**

- `start_frame`, `end_frame`: Frame range to export
- `output_dir`: Base output directory
- `decimate_ratio`: Mesh decimation ratio (e.g., 0.03 = 3% of polygons)
- `skip_existing`: `skip` to resume, `overwrite` to redo all
- `frame_offset`: Frame offset to adjacent mesh for blending (e.g., -95)
- `reference_mesh_name`: Name of the reference mesh in the Blender file
- `grid_step_size`: Grid sampling step size in Blender units (default: 2.0)

**Output:**

- `chunks_ratio_*/*.obj` - Decimated mesh chunks at various quality levels
- `unified/wave_data_frame_*.json` - Per-frame height + normal grid data
- `unified/wave_unified_metadata.json` - Grid config in UE datatable format

### Step 2: Merge wave data for Unreal import

After the export completes, merge the per-frame JSON files into a single UE datatable:

```bash
python3 merge_unified_wave_data.py <input_dir> [output_file]
```

**Example:**

```bash
python3 merge_unified_wave_data.py /hdd/gone_surfing_exports/medium_wave_left/unified
```

This produces:
- `wave_unified_data.json` - UE datatable with one row per frame, containing flat arrays for `h`, `nx`, `ny`, `nz`
- `wave_unified_metadata.json` - Grid dimensions, tiling parameters, seam boundaries (written by step 1)

### Step 3: Import into Unreal Engine

1. Import `wave_unified_metadata.json` and `wave_unified_data.json` as datatables
2. Import the OBJ meshes from a quality level directory
3. Use the MeshArrayActor button to load the meshes into the Niagara system

See [UNIFIED_WAVE_UE_IMPORT.md](UNIFIED_WAVE_UE_IMPORT.md) for detailed struct definitions and Blueprint lookup code.

### Optional: Verify exported data

Plot a single frame's wave data to visually compare with the Blender mesh:

```bash
python3 plot_unified_wave_data.py /hdd/gone_surfing_exports/medium_wave_left/unified/wave_data_frame_886.json
```

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
   - Press **Alt+P** or click the **Run Script** button
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

## Water forces/velocities

For the water velocities, bjson files are read.

1. Open the file create_water_velocity_datatable.js. Make sure that the path for flip_fluid_cache_folder is the correct one (should match the folder used in the Simulation)
2. Open the file ./create_water_velocity_datatables.sh. Change the numbers to match the start and end frames. These should be split up into multiple scripts, each with different frame numbers.
3. run the script `./create_water_velocity_datatables.sh`. This creates datatables for the water velocity to be imported into UE4
4. Import the files into UE4 as WaveVerticesLocations_Struct
