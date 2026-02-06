#!/usr/bin/env python3
"""
Add valid data region metadata to wave height sample metadata files.

This script adds fields to skip zero-padded borders in the exported wave data.
The exported wave samples from Blender contain zero-padded borders on all sides
which cause incorrect wave height calculations when using infinite tiling in UE.

The script adds the following fields to the metadata JSON:
- valid_data_offset_x: Number of indices to skip at the start of X dimension (default: 1)
- valid_data_offset_y: Number of indices to skip at the start of Y dimension (default: 27)
- valid_data_width: Number of valid samples in X dimension (0 = auto-calculate)
- valid_data_height: Number of valid samples in Y dimension (0 = auto-calculate)

Usage:
    python add_valid_data_region_to_metadata.py <metadata_file>

Example:
    python add_valid_data_region_to_metadata.py /path/to/height_samples_struct_metadata.json
"""

import json
import sys
import os


def add_valid_data_region(metadata_file, offset_x=1, offset_y=27, width=59, height=200):
    """
    Add valid data region fields to metadata JSON file.

    Args:
        metadata_file: Path to the metadata JSON file
        offset_x: Number of X indices to skip (left border)
        offset_y: Number of Y indices to skip (top border)
        width: Number of valid X samples (0 = auto-calculate from len_x - offset_x)
        height: Number of valid Y samples (0 = auto-calculate from len_y - offset_y)
    """
    # Check if file exists
    if not os.path.exists(metadata_file):
        print(f"Error: File not found: {metadata_file}")
        return False

    # Read the metadata JSON
    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False

    # Check if it's a list with at least one item
    if not isinstance(metadata, list) or len(metadata) == 0:
        print("Error: Metadata should be a JSON array with at least one object")
        return False

    # Get the first metadata object
    meta = metadata[0]

    # Add or update the valid data region fields
    meta['valid_data_offset_x'] = offset_x
    meta['valid_data_offset_y'] = offset_y
    meta['valid_data_width'] = width
    meta['valid_data_height'] = height

    # Write the updated metadata back to file
    try:
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✓ Successfully updated {metadata_file}")
        print(f"  - valid_data_offset_x: {offset_x}")
        print(f"  - valid_data_offset_y: {offset_y}")
        print(f"  - valid_data_width: {width}")
        print(f"  - valid_data_height: {height}")
        return True
    except Exception as e:
        print(f"Error writing JSON file: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nError: Missing required argument <metadata_file>")
        sys.exit(1)

    metadata_file = sys.argv[1]

    # Default values based on the analysis of wave export data
    # These values skip the zero-padded borders:
    # - X: Skip index 0 (left) and 60 (right), use indices 1-59 (59 samples)
    # - Y: Skip indices 0-26 (top) and 227-229 (bottom), use indices 27-226 (200 samples)
    success = add_valid_data_region(
        metadata_file,
        offset_x=1,    # Skip first X index (left border)
        offset_y=27,   # Skip first 27 Y indices (top border)
        width=59,      # Valid X samples (excluding both left and right borders)
        height=200     # Valid Y samples (excluding both top and bottom borders)
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
