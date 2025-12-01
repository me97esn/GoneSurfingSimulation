#!/bin/bash

# Parallel version of export_waves_display.sh
# Splits the frame range across multiple CPU cores for faster processing
#
# Usage: ./export_waves_display_parallel.sh [start_frame] [end_frame] [output_dir] [skip_existing] [num_jobs]
#   start_frame:    Starting frame number (default: 752)
#   end_frame:      Ending frame number (default: 868)
#   output_dir:     Base output directory (default: /hdd/gone_surfing_exports/medium_wave_left)
#   skip_existing:  'skip' to skip existing files, 'overwrite' to overwrite (default: skip)
#   num_jobs:       Number of parallel jobs (default: 8)
#
# Examples:
#   ./export_waves_display_parallel.sh                              # Use all defaults, 8 parallel jobs
#   ./export_waves_display_parallel.sh 752 868                      # Custom range, 8 jobs
#   ./export_waves_display_parallel.sh 752 868 /output skip 4       # 4 parallel jobs

set -e  # Exit on error

# Configuration
BLEND_FILE="../3dmodels/breaking_waves_beach_break_2.blend"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/export_waves_display.py"

# Parse command-line arguments with defaults
START_FRAME=${1:-752}
END_FRAME=${2:-868}
OUTPUT_BASE_DIR=${3:-/hdd/gone_surfing_exports/medium_wave_left}
SKIP_EXISTING=${4:-skip}
NUM_JOBS=${5:-8}

# Quality levels - decimate ratios
QUALITY_LEVELS="0.02,0.01"

echo "============================================================"
echo "WAVE DISPLAY EXPORT - PARALLEL (${NUM_JOBS} jobs)"
echo "============================================================"
echo "Blend file: $BLEND_FILE"
echo "Start frame: $START_FRAME"
echo "End frame: $END_FRAME"
echo "Output base directory: $OUTPUT_BASE_DIR"
echo "Quality levels (decimate ratios): $QUALITY_LEVELS"
echo "Skip existing files: $SKIP_EXISTING"
echo "Parallel jobs: $NUM_JOBS"
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

# Calculate frames per job
TOTAL_FRAMES=$((END_FRAME - START_FRAME + 1))
FRAMES_PER_JOB=$(((TOTAL_FRAMES + NUM_JOBS - 1) / NUM_JOBS))  # Round up

echo "Total frames: $TOTAL_FRAMES"
echo "Frames per job: ~$FRAMES_PER_JOB"
echo ""
echo "Splitting work into $NUM_JOBS parallel jobs..."
echo "============================================================"
echo ""

# Create temporary directory for job logs
LOG_DIR="$OUTPUT_BASE_DIR/parallel_logs"
mkdir -p "$LOG_DIR"

# Array to store background job PIDs
declare -a JOB_PIDS=()

# Start time
START_TIME=$(date +%s)

# Launch parallel jobs
for ((job=0; job<NUM_JOBS; job++)); do
    # Calculate frame range for this job
    JOB_START=$((START_FRAME + job * FRAMES_PER_JOB))
    JOB_END=$((JOB_START + FRAMES_PER_JOB - 1))

    # Don't go past the end frame
    if [ $JOB_END -gt $END_FRAME ]; then
        JOB_END=$END_FRAME
    fi

    # Skip if start is past end
    if [ $JOB_START -gt $END_FRAME ]; then
        break
    fi

    LOG_FILE="$LOG_DIR/job_${job}_frames_${JOB_START}_${JOB_END}.log"

    echo "Starting job $((job+1))/$NUM_JOBS: frames $JOB_START-$JOB_END (log: $LOG_FILE)"

    # Launch Blender in background
    blender "$BLEND_FILE" --background --python "$PYTHON_SCRIPT" -- \
        $JOB_START $JOB_END "$OUTPUT_BASE_DIR" "$QUALITY_LEVELS" "$SKIP_EXISTING" \
        > "$LOG_FILE" 2>&1 &

    # Store the PID
    JOB_PIDS+=($!)
done

echo ""
echo "All $NUM_JOBS jobs launched. Waiting for completion..."
echo "You can monitor progress by tailing the log files in: $LOG_DIR"
echo ""

# Wait for all jobs to complete and check exit codes
FAILED_JOBS=0
for ((i=0; i<${#JOB_PIDS[@]}; i++)); do
    PID=${JOB_PIDS[$i]}

    # Wait for this specific job
    if wait $PID; then
        echo "✓ Job $((i+1)) (PID $PID) completed successfully"
    else
        EXIT_CODE=$?
        echo "✗ Job $((i+1)) (PID $PID) FAILED with exit code $EXIT_CODE"
        FAILED_JOBS=$((FAILED_JOBS + 1))
    fi
done

# Calculate total time
END_TIME=$(date +%s)
TOTAL_SECONDS=$((END_TIME - START_TIME))
HOURS=$((TOTAL_SECONDS / 3600))
MINUTES=$(((TOTAL_SECONDS % 3600) / 60))
SECONDS=$((TOTAL_SECONDS % 60))

echo ""
echo "============================================================"
if [ $FAILED_JOBS -eq 0 ]; then
    echo "ALL JOBS COMPLETED SUCCESSFULLY!"
else
    echo "COMPLETED WITH ERRORS: $FAILED_JOBS job(s) failed"
    echo "Check log files in $LOG_DIR for details"
fi
echo "============================================================"
echo "Total time: ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo "Output directory: $OUTPUT_BASE_DIR"
echo ""
echo "Generated directories:"
for ratio in $(echo $QUALITY_LEVELS | tr ',' ' '); do
    ratio_name=$(echo $ratio | sed 's/\\./_/g')
    dir_name="chunks_ratio_${ratio_name}"
    dir_path="${OUTPUT_BASE_DIR}/${dir_name}"
    if [ -d "$dir_path" ]; then
        file_count=$(find "$dir_path" -name "*.obj" 2>/dev/null | wc -l)
        echo "  - ${dir_name}: ${file_count} OBJ files"
    fi
done
echo ""
echo "To use in Unreal Engine:"
echo "1. Import the meshes from one of the quality level directories"
echo "2. Use the MeshArrayActor button to load meshes into Niagara system"
echo "============================================================"

# Exit with error if any jobs failed
if [ $FAILED_JOBS -gt 0 ]; then
    exit 1
fi
