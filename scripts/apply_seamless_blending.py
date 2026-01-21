#!/usr/bin/env python3
"""
Seamless Mesh Blending for Infinite Wave Animation

This script post-processes exported OBJ mesh files to create seamless transitions
between adjacent meshes when placed side by side in Unreal Engine.

For each frame N, it blends the edge vertices toward frame N+offset, creating
a smooth transition zone that eliminates visible seams.

Usage:
    python apply_seamless_blending.py --blend-file <blender_file> --reference-mesh <mesh_name> --input <folder> [options]

Example:
    python apply_seamless_blending.py \
        --blend-file ../3dmodels/breaking_waves_beach_break_2.blend \
        --reference-mesh "frame_85_reference" \
        --input /hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_05 \
        --frame-offset 85
"""

import argparse
import os
import re
import sys
import struct
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class Vertex:
    x: float
    y: float
    z: float


@dataclass
class OBJMesh:
    """Represents a parsed OBJ file"""
    vertices: List[Vertex]
    faces: List[List[int]]  # List of face vertex indices (1-based as in OBJ)
    normals: List[Tuple[float, float, float]]
    texcoords: List[Tuple[float, float]]
    other_lines: List[str]  # Other lines to preserve (comments, materials, etc.)

    def get_bounds(self, axis: int) -> Tuple[float, float]:
        """Get min/max bounds along specified axis (0=x, 1=y, 2=z)"""
        if not self.vertices:
            return (0.0, 0.0)
        values = [self._get_axis_value(v, axis) for v in self.vertices]
        return (min(values), max(values))

    def _get_axis_value(self, v: Vertex, axis: int) -> float:
        if axis == 0:
            return v.x
        elif axis == 1:
            return v.y
        else:
            return v.z


def parse_obj_file(filepath: str) -> OBJMesh:
    """Parse an OBJ file and return mesh data"""
    vertices = []
    faces = []
    normals = []
    texcoords = []
    other_lines = []

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if not parts:
                continue

            if parts[0] == 'v' and len(parts) >= 4:
                # Vertex position
                vertices.append(Vertex(
                    x=float(parts[1]),
                    y=float(parts[2]),
                    z=float(parts[3])
                ))
            elif parts[0] == 'vn' and len(parts) >= 4:
                # Vertex normal
                normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif parts[0] == 'vt' and len(parts) >= 3:
                # Texture coordinate
                texcoords.append((float(parts[1]), float(parts[2])))
            elif parts[0] == 'f':
                # Face - can be "f v1 v2 v3" or "f v1/vt1 v2/vt2 v3/vt3" or "f v1/vt1/vn1 ..."
                face_verts = []
                for part in parts[1:]:
                    # Extract vertex index (first number before any /)
                    v_idx = int(part.split('/')[0])
                    face_verts.append(v_idx)
                faces.append(face_verts)
            else:
                # Preserve other lines (comments, materials, groups, etc.)
                other_lines.append(line)

    return OBJMesh(vertices=vertices, faces=faces, normals=normals,
                   texcoords=texcoords, other_lines=other_lines)


def write_obj_file(filepath: str, mesh: OBJMesh):
    """Write mesh data to OBJ file"""
    with open(filepath, 'w') as f:
        # Write header comment
        f.write("# Seamless blended mesh\n")

        # Write other preserved lines (like material references)
        for line in mesh.other_lines:
            if line.startswith('mtllib') or line.startswith('usemtl') or line.startswith('o ') or line.startswith('g '):
                f.write(f"{line}\n")

        # Write vertices
        for v in mesh.vertices:
            f.write(f"v {v.x:.6f} {v.y:.6f} {v.z:.6f}\n")

        # Write texture coordinates
        for vt in mesh.texcoords:
            f.write(f"vt {vt[0]:.6f} {vt[1]:.6f}\n")

        # Write normals
        for vn in mesh.normals:
            f.write(f"vn {vn[0]:.6f} {vn[1]:.6f} {vn[2]:.6f}\n")

        # Write faces
        for face in mesh.faces:
            f.write("f " + " ".join(str(v) for v in face) + "\n")


def smoothstep(t: float) -> float:
    """Smooth interpolation function (ease-in-out)"""
    # Clamp t to [0, 1]
    t = max(0.0, min(1.0, t))
    # Smoothstep formula: 3t² - 2t³
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b"""
    return a + (b - a) * t


def get_reference_mesh_position(blend_file: str, reference_mesh_name: str) -> Tuple[float, float, float]:
    """
    Read the position of the reference mesh from a Blender file.
    This requires running Blender in background mode.
    """
    import subprocess
    import tempfile

    # Create a temporary Python script to extract the position
    script_content = f'''
import bpy
import sys

mesh_name = "{reference_mesh_name}"

if mesh_name in bpy.data.objects:
    obj = bpy.data.objects[mesh_name]
    pos = obj.location
    print(f"POSITION:{pos.x},{pos.y},{pos.z}")
else:
    print(f"ERROR:Object '{mesh_name}' not found")
    print("Available objects:")
    for obj in bpy.data.objects:
        print(f"  - {obj.name}")
    sys.exit(1)
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        # Run Blender in background mode
        result = subprocess.run(
            ['blender', blend_file, '--background', '--python', script_path],
            capture_output=True,
            text=True
        )

        # Parse the output to find the position
        for line in result.stdout.split('\n'):
            if line.startswith('POSITION:'):
                coords = line.replace('POSITION:', '').split(',')
                return (float(coords[0]), float(coords[1]), float(coords[2]))
            elif line.startswith('ERROR:'):
                print(f"Error: {line.replace('ERROR:', '')}")
                print(result.stdout)
                sys.exit(1)

        print(f"Error: Could not find position in Blender output")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)

    finally:
        os.unlink(script_path)


def find_frame_files(input_folder: str, frame: int, chunk_x: int) -> List[str]:
    """Find all OBJ files for a specific frame and chunk x position"""
    pattern = re.compile(rf'^{chunk_x}_(\d+)_mesh_{frame}\.obj$')
    files = []

    for filename in os.listdir(input_folder):
        if pattern.match(filename):
            files.append(os.path.join(input_folder, filename))

    return files


def get_all_frames(input_folder: str) -> List[int]:
    """Get all unique frame numbers from the input folder"""
    pattern = re.compile(r'^\d+_\d+_mesh_(\d+)\.obj$')
    frames = set()

    for filename in os.listdir(input_folder):
        match = pattern.match(filename)
        if match:
            frames.add(int(match.group(1)))

    return sorted(frames)


def blend_meshes(
    source_mesh: OBJMesh,
    target_mesh: OBJMesh,
    position_offset: Tuple[float, float, float],
    blend_axis: int,
    blend_direction: str,
    blend_width_percent: float
) -> OBJMesh:
    """
    Blend the edge vertices of source_mesh toward target_mesh.

    Args:
        source_mesh: The mesh to modify
        target_mesh: The mesh to blend toward (at frame N+offset)
        position_offset: The (x, y, z) offset where target mesh is placed
        blend_axis: Which axis to blend along (0=x, 1=y, 2=z)
        blend_direction: "positive" or "negative" - which edge to blend
        blend_width_percent: Width of blend zone as percentage of mesh width

    Returns:
        Modified source_mesh with blended vertices
    """
    # Get mesh bounds along blend axis
    source_min, source_max = source_mesh.get_bounds(blend_axis)
    mesh_width = source_max - source_min
    blend_width = mesh_width * (blend_width_percent / 100.0)

    # Determine blend zone boundaries
    if blend_direction == "positive":
        # Blend the positive edge (e.g., right side for x-axis)
        blend_start = source_max - blend_width
        blend_end = source_max
    else:
        # Blend the negative edge (e.g., left side for x-axis)
        blend_start = source_min
        blend_end = source_min + blend_width

    # Get position offset along blend axis
    axis_offset = position_offset[blend_axis]

    # Build a spatial lookup for target mesh vertices
    # We'll find the nearest vertex in the target mesh for each source vertex in the blend zone
    target_vertices_by_position = {}
    for i, v in enumerate(target_mesh.vertices):
        # Create a key based on the non-blend axes (for finding corresponding vertices)
        if blend_axis == 0:
            key = (round(v.y, 3), round(v.z, 3))
        elif blend_axis == 1:
            key = (round(v.x, 3), round(v.z, 3))
        else:
            key = (round(v.x, 3), round(v.y, 3))

        if key not in target_vertices_by_position:
            target_vertices_by_position[key] = []
        target_vertices_by_position[key].append(v)

    # Blend vertices in the transition zone
    blended_count = 0
    for v in source_mesh.vertices:
        # Get vertex position along blend axis
        if blend_axis == 0:
            pos = v.x
        elif blend_axis == 1:
            pos = v.y
        else:
            pos = v.z

        # Check if vertex is in blend zone
        if blend_direction == "positive":
            if pos < blend_start:
                continue
            # Calculate blend factor (0 at blend_start, 1 at blend_end)
            blend_factor = (pos - blend_start) / blend_width if blend_width > 0 else 0
        else:
            if pos > blend_end:
                continue
            # Calculate blend factor (1 at blend_start, 0 at blend_end)
            blend_factor = 1.0 - ((pos - blend_start) / blend_width) if blend_width > 0 else 0

        # Apply smoothstep for smooth transition
        smooth_factor = smoothstep(blend_factor)

        # Find corresponding vertex in target mesh
        if blend_axis == 0:
            key = (round(v.y, 3), round(v.z, 3))
        elif blend_axis == 1:
            key = (round(v.x, 3), round(v.z, 3))
        else:
            key = (round(v.x, 3), round(v.y, 3))

        if key in target_vertices_by_position:
            # Find the target vertex with the closest position along blend axis
            # (accounting for the position offset)
            target_candidates = target_vertices_by_position[key]

            # The target mesh is offset, so we need to find the corresponding edge
            # For positive blend direction, we want the negative edge of target mesh
            # (because target mesh's left edge aligns with source mesh's right edge)
            if blend_direction == "positive":
                # Find target vertex closest to the negative edge (minimum along blend axis)
                best_target = min(target_candidates,
                    key=lambda tv: tv.x if blend_axis == 0 else (tv.y if blend_axis == 1 else tv.z))
            else:
                # Find target vertex closest to the positive edge
                best_target = max(target_candidates,
                    key=lambda tv: tv.x if blend_axis == 0 else (tv.y if blend_axis == 1 else tv.z))

            # Calculate target position (with offset applied)
            target_x = best_target.x + position_offset[0]
            target_y = best_target.y + position_offset[1]
            target_z = best_target.z + position_offset[2]

            # Interpolate vertex position
            v.x = lerp(v.x, target_x, smooth_factor)
            v.y = lerp(v.y, target_y, smooth_factor)
            v.z = lerp(v.z, target_z, smooth_factor)
            blended_count += 1

    return source_mesh


def process_folder(
    input_folder: str,
    output_folder: str,
    position_offset: Tuple[float, float, float],
    frame_offset: int,
    blend_width_percent: float,
    blend_axis: int,
    blend_direction: str,
    edge_chunk_x: int
):
    """Process all frames in a folder"""

    frames = get_all_frames(input_folder)
    if not frames:
        print(f"No OBJ files found in {input_folder}")
        return

    print(f"Found {len(frames)} frames: {frames[0]} to {frames[-1]}")
    print(f"Position offset: {position_offset}")
    print(f"Frame offset: {frame_offset}")
    print(f"Blend width: {blend_width_percent}%")
    print(f"Blend axis: {['x', 'y', 'z'][blend_axis]}")
    print(f"Blend direction: {blend_direction}")
    print(f"Edge chunk x: {edge_chunk_x}")
    print()

    # Create output folder if different from input
    if output_folder != input_folder:
        os.makedirs(output_folder, exist_ok=True)

    # Process each frame
    for i, frame in enumerate(frames):
        # Calculate target frame (with wraparound)
        target_frame = frames[(frames.index(frame) + frame_offset) % len(frames)]

        # Find edge chunk files for this frame
        source_files = find_frame_files(input_folder, frame, edge_chunk_x)

        if not source_files:
            print(f"  Frame {frame}: No edge chunk files found for chunk_x={edge_chunk_x}")
            continue

        for source_file in source_files:
            # Determine the corresponding target file
            filename = os.path.basename(source_file)
            # Extract chunk_y from filename
            match = re.match(rf'^{edge_chunk_x}_(\d+)_mesh_\d+\.obj$', filename)
            if not match:
                continue
            chunk_y = match.group(1)

            target_filename = f"{edge_chunk_x}_{chunk_y}_mesh_{target_frame}.obj"
            target_file = os.path.join(input_folder, target_filename)

            if not os.path.exists(target_file):
                print(f"  Frame {frame}: Target file not found: {target_filename}")
                continue

            # Load meshes
            source_mesh = parse_obj_file(source_file)
            target_mesh = parse_obj_file(target_file)

            # Blend meshes
            blended_mesh = blend_meshes(
                source_mesh=source_mesh,
                target_mesh=target_mesh,
                position_offset=position_offset,
                blend_axis=blend_axis,
                blend_direction=blend_direction,
                blend_width_percent=blend_width_percent
            )

            # Write output
            if output_folder != input_folder:
                output_file = os.path.join(output_folder, filename)
            else:
                output_file = source_file

            write_obj_file(output_file, blended_mesh)

        # Progress update
        if (i + 1) % 10 == 0 or i == len(frames) - 1:
            print(f"  Processed {i + 1}/{len(frames)} frames")

    # Copy non-edge chunks to output folder if different
    if output_folder != input_folder:
        print("\nCopying non-edge chunk files...")
        import shutil
        for filename in os.listdir(input_folder):
            if filename.endswith('.obj'):
                match = re.match(r'^(\d+)_\d+_mesh_\d+\.obj$', filename)
                if match and int(match.group(1)) != edge_chunk_x:
                    src = os.path.join(input_folder, filename)
                    dst = os.path.join(output_folder, filename)
                    shutil.copy2(src, dst)


def main():
    parser = argparse.ArgumentParser(
        description='Apply seamless blending to exported wave mesh OBJ files'
    )
    parser.add_argument('--blend-file', required=True,
                        help='Path to Blender file containing reference mesh')
    parser.add_argument('--reference-mesh', required=True,
                        help='Name of reference mesh in Blender file')
    parser.add_argument('--input', required=True,
                        help='Input folder containing OBJ files')
    parser.add_argument('--output', default=None,
                        help='Output folder (default: /tmp/seamless_blended_meshes)')
    parser.add_argument('--frame-offset', type=int, default=85,
                        help='Frame offset between adjacent meshes (default: 85)')
    parser.add_argument('--blend-width', type=float, default=5.0,
                        help='Blend zone width as percentage (default: 5.0)')
    parser.add_argument('--blend-axis', choices=['x', 'y', 'z'], default='x',
                        help='Axis along which meshes are placed (default: x)')
    parser.add_argument('--blend-direction', choices=['positive', 'negative'], default='positive',
                        help='Which edge to blend (default: positive)')
    parser.add_argument('--edge-chunk', type=int, default=2,
                        help='X index of edge chunks to blend (default: 2 for 3x1 grid)')

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.blend_file):
        print(f"Error: Blender file not found: {args.blend_file}")
        sys.exit(1)

    if not os.path.isdir(args.input):
        print(f"Error: Input folder not found: {args.input}")
        sys.exit(1)

    # Default output to /tmp folder to avoid accidentally overwriting input
    if args.output:
        output_folder = args.output
    else:
        output_folder = '/tmp/seamless_blended_meshes'
        print(f"No --output specified, using default: {output_folder}")

    # Convert axis to index
    axis_map = {'x': 0, 'y': 1, 'z': 2}
    blend_axis = axis_map[args.blend_axis]

    print("=" * 60)
    print("SEAMLESS MESH BLENDING")
    print("=" * 60)
    print(f"Blender file: {args.blend_file}")
    print(f"Reference mesh: {args.reference_mesh}")
    print(f"Input folder: {args.input}")
    print(f"Output folder: {output_folder}")
    print()

    # Get reference mesh position from Blender file
    print("Reading reference mesh position from Blender file...")
    position_offset = get_reference_mesh_position(args.blend_file, args.reference_mesh)
    print(f"Reference mesh position: {position_offset}")
    print()

    # Process the folder
    process_folder(
        input_folder=args.input,
        output_folder=output_folder,
        position_offset=position_offset,
        frame_offset=args.frame_offset,
        blend_width_percent=args.blend_width,
        blend_axis=blend_axis,
        blend_direction=args.blend_direction,
        edge_chunk_x=args.edge_chunk
    )

    print()
    print("=" * 60)
    print("BLENDING COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
