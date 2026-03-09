"""
Merge per-frame unified wave data files into UE datatable JSON files.

Produces two files:
  - wave_unified_data.json: UE datatable with one row per frame (Name, h, nx, ny, nz, vx, vy, vz)
  - wave_unified_metadata.json is already written by the export script

Usage:
    python merge_unified_wave_data.py <input_dir> [output_file]

Example:
    python merge_unified_wave_data.py /hdd/gone_surfing_exports/medium_wave_left/unified
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
frame_files = sorted(glob.glob(pattern), key=lambda f: int(os.path.basename(f).split('_')[-1].split('.')[0]))

if not frame_files:
    print(f"No frame files found matching {pattern}")
    sys.exit(1)

print(f"Found {len(frame_files)} frame files in {input_dir}")

# UE datatable format: top-level array, each element has a "Name" field
datatable = []

for i, filepath in enumerate(frame_files):
    with open(filepath) as f:
        frame_data = json.load(f)

    row = {
        "Name": f"Frame_{frame_data['frame']}",
        "h": frame_data["data"]["h"],
        "nx": frame_data["data"]["nx"],
        "ny": frame_data["data"]["ny"],
        "nz": frame_data["data"]["nz"],
        "vx": frame_data["data"].get("vx", []),
        "vy": frame_data["data"].get("vy", []),
        "vz": frame_data["data"].get("vz", []),
    }
    datatable.append(row)

    if (i + 1) % 50 == 0:
        print(f"  Processed {i + 1}/{len(frame_files)} files")

print(f"Writing UE datatable to {output_file}")
with open(output_file, "w") as f:
    json.dump(datatable, f)

file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
print(f"Done. {len(datatable)} frames, {file_size_mb:.1f} MB")
