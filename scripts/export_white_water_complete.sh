#!/bin/bash

# Combined script to export white water particles from Blender and convert to Unreal format
# This replaces the two-step manual process in the README
#
# Usage: ./export_white_water_complete.sh [start_frame] [end_frame]
#   start_frame: Starting frame number (default: 752)
#   end_frame:   Ending frame number (default: 1325)
#
# Example: ./export_white_water_complete.sh 752 1000

set -e  # Exit on error

# Configuration
BLEND_FILE="../3dmodels/breaking_waves_beach_break_2.blend"
OUTPUT_DIR="/hdd/gone_surfing_exports/medium_wave_left/white_water"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse command-line arguments with defaults
START_FRAME=${1:-752}
END_FRAME=${2:-1325}

echo "============================================================"
echo "WHITE WATER EXPORT - COMPLETE PIPELINE"
echo "============================================================"
echo "Start frame: $START_FRAME"
echo "End frame: $END_FRAME"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Step 1: Export OBJ files from Blender
echo "STEP 1: Exporting OBJ files from Blender..."
echo "------------------------------------------------------------"

blender "$BLEND_FILE" --background --python - <<EOF
import bpy
import os

# Configuration
start_frame = $START_FRAME
end_frame = $END_FRAME
output_dir = "$OUTPUT_DIR"

# Create output directory
os.makedirs(output_dir, exist_ok=True)

# Set frame range
bpy.context.scene.frame_start = start_frame
bpy.context.scene.frame_end = end_frame

# Select the white water foam object
# Try different possible names for the white water object
white_water_objects = ['whitewater_foam', 'foam', 'Foam', 'whitewater', 'Whitewater']
white_water_obj = None

for obj_name in white_water_objects:
    if obj_name in bpy.data.objects:
        white_water_obj = bpy.data.objects[obj_name]
        break

if white_water_obj is None:
    print("Error: Could not find white water object. Available objects:")
    for obj in bpy.data.objects:
        print(f"  - {obj.name}")
    exit(1)

print(f"Found white water object: {white_water_obj.name}")

# Deselect all and select only the white water object
bpy.ops.object.select_all(action='DESELECT')
white_water_obj.select_set(True)
bpy.context.view_layer.objects.active = white_water_obj

# Export as OBJ sequence
print(f"Exporting frames {start_frame} to {end_frame}...")

for frame in range(start_frame, end_frame + 1):
    bpy.context.scene.frame_set(frame)

    # Construct the output path with 6-digit frame number
    output_file = os.path.join(output_dir, f"{frame:06d}.obj")

    # Export OBJ
    bpy.ops.wm.obj_export(
        filepath=output_file,
        export_selected_objects=True,
        export_animation=False,
        forward_axis='X',
        up_axis='Z'
    )

    if frame % 50 == 0 or frame == start_frame:
        print(f"  Exported frame {frame}")

print(f"Export complete! {end_frame - start_frame + 1} files written to {output_dir}")
EOF

if [ $? -ne 0 ]; then
    echo "ERROR: Blender export failed!"
    exit 1
fi

echo ""
echo "✓ OBJ export completed successfully"
echo ""

# Step 2: Convert to Unreal Niagara format
echo "STEP 2: Converting to Unreal Niagara Datatable format..."
echo "------------------------------------------------------------"

cd "$SCRIPT_DIR"
node export_white_water_points.js $START_FRAME $END_FRAME

if [ $? -ne 0 ]; then
    echo "ERROR: Conversion to Unreal format failed!"
    exit 1
fi

echo ""
echo "✓ Conversion completed successfully"
echo ""

# Summary
echo "============================================================"
echo "WHITE WATER EXPORT COMPLETE!"
echo "============================================================"
echo "Output files created in: $OUTPUT_DIR"
echo "  - OBJ files: ${START_FRAME}...${END_FRAME}.obj"
echo "  - JSON files:"
echo "    - white-water-points-data-rotX.json"
echo "    - white-water-points-data-rotY.json"
echo "    - white-water-points-data-rotZ.json"
echo ""
echo "These files can now be imported into Unreal Engine."
echo "============================================================"
