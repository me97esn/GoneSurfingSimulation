#!/bin/bash

# Export wave animation as chunked OBJ meshes at multiple quality levels
# This script automates the export process described in the README for stop motion meshes
#
# Usage: ./export_waves_display.sh [start_frame] [end_frame] [output_dir]
#   start_frame: Starting frame number (default: 752)
#   end_frame:   Ending frame number (default: 868)
#   output_dir:  Base output directory (default: /hdd/gone_surfing_exports/medium_wave_left)
#
# Examples:
#   ./export_waves_display.sh                    # Use all defaults
#   ./export_waves_display.sh 752 868           # Custom frame range
#   ./export_waves_display.sh 752 868 /output   # Custom frame range and output

set -e  # Exit on error

# Configuration
BLEND_FILE="../3dmodels/breaking_waves_beach_break_2.blend"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/export_waves_display.py"

# Parse command-line arguments with defaults
START_FRAME=${1:-752}
END_FRAME=${2:-868}
OUTPUT_BASE_DIR=${3:-/hdd/gone_surfing_exports/medium_wave_left}

# Quality levels - decimate ratios from 0.05 down to 0.01
# FR-7 and FR-8: Multiple quality levels with decreasing ratios
QUALITY_LEVELS="0.05,0.04,0.03,0.02,0.01"

echo "============================================================"
echo "WAVE DISPLAY EXPORT - CHUNKED MESHES"
echo "============================================================"
echo "Blend file: $BLEND_FILE"
echo "Start frame: $START_FRAME"
echo "End frame: $END_FRAME"
echo "Output base directory: $OUTPUT_BASE_DIR"
echo "Quality levels (decimate ratios): $QUALITY_LEVELS"
echo ""
echo "Output directories will be created:"
echo "  - ${OUTPUT_BASE_DIR}/chunks_epic_resolution (ratio: 0.05)"
echo "  - ${OUTPUT_BASE_DIR}/chunks_higher_resolution (ratio: 0.04)"
echo "  - ${OUTPUT_BASE_DIR}/chunks_ratio_0_03 (ratio: 0.03)"
echo "  - ${OUTPUT_BASE_DIR}/chunks_ratio_0_02 (ratio: 0.02)"
echo "  - ${OUTPUT_BASE_DIR}/chunks_ratio_0_01 (ratio: 0.01)"
echo ""
echo "This will create $(echo $QUALITY_LEVELS | tr ',' '\n' | wc -l) quality levels"
echo "Each with $((END_FRAME - START_FRAME + 1)) frames"
echo "Each frame split into 24 chunks (3x8)"
echo ""
echo "Total files to be created: $(( $(echo $QUALITY_LEVELS | tr ',' '\n' | wc -l) * (END_FRAME - START_FRAME + 1) * 24 ))"
echo "============================================================"
echo ""

# Verify Blender file exists
if [ ! -f "$BLEND_FILE" ]; then
    echo "ERROR: Blender file not found: $BLEND_FILE"
    exit 1
fi

# Verify Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "ERROR: Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_BASE_DIR"

# Run Blender in background mode
echo "Starting Blender export process..."
echo "This may take a long time depending on the number of frames and quality levels."
echo ""

blender "$BLEND_FILE" --background --python "$PYTHON_SCRIPT" -- \
    $START_FRAME $END_FRAME "$OUTPUT_BASE_DIR" "$QUALITY_LEVELS"

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "ERROR: Blender export failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi

echo ""
echo "============================================================"
echo "EXPORT COMPLETE!"
echo "============================================================"
echo "Output directory: $OUTPUT_BASE_DIR"
echo ""
echo "Generated directories:"
for ratio in $(echo $QUALITY_LEVELS | tr ',' ' '); do
    ratio_name=$(echo $ratio | sed 's/\./_/g')
    if [ "$ratio" = "0.05" ]; then
        dir_name="chunks_epic_resolution"
    elif [ "$ratio" = "0.04" ]; then
        dir_name="chunks_higher_resolution"
    else
        dir_name="chunks_ratio_${ratio_name}"
    fi
    dir_path="${OUTPUT_BASE_DIR}/${dir_name}"
    if [ -d "$dir_path" ]; then
        file_count=$(find "$dir_path" -name "*.obj" | wc -l)
        echo "  - ${dir_name}: ${file_count} OBJ files"
    fi
done
echo ""
echo "To use in Unreal Engine:"
echo "1. Import the meshes from one of the quality level directories"
echo "2. Use the MeshArrayActor button to load meshes into Niagara system"
echo "============================================================"
