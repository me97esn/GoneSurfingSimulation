"""
Merge per-frame unified wave data files into a single combined JSON file.

Usage:
    python merge_unified_wave_data.py <input_dir> [output_file]

Example:
    python merge_unified_wave_data.py /hdd/gone_surfing_exports/medium_wave_left/unified
    python merge_unified_wave_data.py /hdd/gone_surfing_exports/medium_wave_left/unified /hdd/gone_surfing_exports/medium_wave_left/unified/wave_unified_data.json
"""
import json
import glob
import os
import sys

if len(sys.argv) < 2:
    print("Usage: python merge_unified_wave_data.py <input_dir> [output_file]")
    sys.exit(1)

input_dir = sys.argv[1]
output_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "wave_unified_data.json")

# Find all per-frame files
pattern = os.path.join(input_dir, "wave_data_frame_*.json")
frame_files = sorted(glob.glob(pattern))

if not frame_files:
    print(f"No frame files found matching {pattern}")
    sys.exit(1)

print(f"Found {len(frame_files)} frame files in {input_dir}")

# Read first frame to get grid info
with open(frame_files[0]) as f:
    first = json.load(f)

combined = {
    "grid": first["grid"],
    "frames": []
}

for i, filepath in enumerate(frame_files):
    with open(filepath) as f:
        frame_data = json.load(f)

    combined["frames"].append({
        "frame": frame_data["frame"],
        "h": frame_data["data"]["h"],
        "nx": frame_data["data"]["nx"],
        "ny": frame_data["data"]["ny"],
        "nz": frame_data["data"]["nz"],
        "vx": frame_data["data"]["vx"],
        "vy": frame_data["data"]["vy"],
        "vz": frame_data["data"]["vz"]
    })

    if (i + 1) % 50 == 0:
        print(f"  Processed {i + 1}/{len(frame_files)} files")

print(f"Writing combined file to {output_file}")
with open(output_file, "w") as f:
    json.dump(combined, f)

file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
print(f"Done. {len(combined['frames'])} frames, {file_size_mb:.1f} MB")
