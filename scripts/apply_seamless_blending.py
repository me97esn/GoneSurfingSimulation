#!/usr/bin/env python3
"""
Seamless Mesh Blending for Infinite Wave Animation

This script post-processes exported OBJ mesh files to create seamless transitions
between adjacent meshes when placed side by side in Unreal Engine.

The exported meshes have distorted/curved edges due to decimation. This script:
1. Cuts away the distorted edges (~3% of mesh width) from both left and right sides
2. Blends the remaining edge vertices toward adjacent frame's exported OBJ mesh

For each frame N:
- Right edge: blends toward frame N+frame_offset (the mesh placed to the right)
- Left edge: blends toward frame N-frame_offset (the mesh placed to the left)

IMPORTANT: Requires a reference mesh to be set up in Blender first!
The reference mesh defines the exact position offset where adjacent meshes are placed.

Usage:
    python apply_seamless_blending.py --blend-file <blender_file> --input <folder> [options]

Example:
    python apply_seamless_blending.py \
        --blend-file ../3dmodels/breaking_waves_beach_break_2.blend \
        --input /hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_05 \
        --frame-offset -95
"""

import argparse
import os
import re
import sys
import subprocess
import tempfile
from typing import List, Tuple, Dict, Optional, Set
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
    faces: List[List[Tuple[int, Optional[int], Optional[int]]]]  # List of (v, vt, vn) tuples
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

    def set_axis_value(self, v: Vertex, axis: int, value: float):
        if axis == 0:
            v.x = value
        elif axis == 1:
            v.y = value
        else:
            v.z = value


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
                    indices = part.split('/')
                    v_idx = int(indices[0])
                    vt_idx = int(indices[1]) if len(indices) > 1 and indices[1] else None
                    vn_idx = int(indices[2]) if len(indices) > 2 and indices[2] else None
                    face_verts.append((v_idx, vt_idx, vn_idx))
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

        # Write faces with proper format
        for face in mesh.faces:
            face_str = "f"
            for v_idx, vt_idx, vn_idx in face:
                if vt_idx is not None and vn_idx is not None:
                    face_str += f" {v_idx}/{vt_idx}/{vn_idx}"
                elif vt_idx is not None:
                    face_str += f" {v_idx}/{vt_idx}"
                elif vn_idx is not None:
                    face_str += f" {v_idx}//{vn_idx}"
                else:
                    face_str += f" {v_idx}"
            f.write(face_str + "\n")


def smoothstep(t: float) -> float:
    """Smooth interpolation function (ease-in-out)"""
    # Clamp t to [0, 1]
    t = max(0.0, min(1.0, t))
    # Smoothstep formula: 3t² - 2t³
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b"""
    return a + (b - a) * t


def build_spatial_lookup(vertices: List[Vertex], blend_axis: int) -> Dict[Tuple[float, float], List[Vertex]]:
    """
    Build a spatial lookup for vertices based on non-blend axes.
    This allows finding corresponding vertices between two meshes.
    """
    lookup = {}
    for v in vertices:
        # Create key based on non-blend axes (rounded for matching)
        if blend_axis == 0:
            key = (round(v.y, 2), round(v.z, 2))
        elif blend_axis == 1:
            key = (round(v.x, 2), round(v.z, 2))
        else:
            key = (round(v.x, 2), round(v.y, 2))

        if key not in lookup:
            lookup[key] = []
        lookup[key].append(v)
    return lookup


def find_nearest_vertex_at_edge(
    v: Vertex,
    target_lookup: Dict[Tuple[float, float], List[Vertex]],
    blend_axis: int,
    is_right_edge: bool,
    axis_offset: float
) -> Optional[Tuple[float, float, float]]:
    """
    Find the nearest vertex in the target mesh for blending.

    Args:
        v: Source vertex to find a match for
        target_lookup: Spatial lookup of target mesh vertices
        blend_axis: Which axis to blend along (0=x, 1=y, 2=z)
        is_right_edge: True if blending right edge (find leftmost target vertex)
        axis_offset: Position offset to apply to target vertex along blend axis

    Returns:
        Target vertex position with offset applied, or None if no match found
    """
    # Create key based on non-blend axes
    if blend_axis == 0:
        key = (round(v.y, 2), round(v.z, 2))
    elif blend_axis == 1:
        key = (round(v.x, 2), round(v.z, 2))
    else:
        key = (round(v.x, 2), round(v.y, 2))

    # Try exact match first, then nearby keys with looser tolerance
    candidates = None
    for delta1 in [0, -0.05, 0.05, -0.1, 0.1]:
        for delta2 in [0, -0.05, 0.05, -0.1, 0.1]:
            nearby_key = (round(key[0] + delta1, 2), round(key[1] + delta2, 2))
            if nearby_key in target_lookup:
                candidates = target_lookup[nearby_key]
                break
        if candidates:
            break

    if not candidates:
        return None

    # Find the vertex at the appropriate edge of the target mesh
    # For right edge blending: we want the leftmost vertex from the adjacent mesh (its left edge)
    # For left edge blending: we want the rightmost vertex from the adjacent mesh (its right edge)
    if is_right_edge:
        # Adjacent mesh is to the right, so we blend toward its LEFT edge (minimum position)
        best = min(candidates, key=lambda c: c.x if blend_axis == 0 else (c.y if blend_axis == 1 else c.z))
    else:
        # Adjacent mesh is to the left, so we blend toward its RIGHT edge (maximum position)
        best = max(candidates, key=lambda c: c.x if blend_axis == 0 else (c.y if blend_axis == 1 else c.z))

    # Apply position offset to get world position
    result = [best.x, best.y, best.z]
    result[blend_axis] += axis_offset
    return tuple(result)


def cut_and_blend_mesh(
    mesh: OBJMesh,
    target_mesh_right: Optional[OBJMesh],
    target_mesh_left: Optional[OBJMesh],
    blend_axis: int,
    cut_width_percent: float,
    blend_width_percent: float,
    mesh_offset_right: float,
    mesh_offset_left: float
) -> OBJMesh:
    """
    Cut away distorted edges and blend remaining edge vertices toward adjacent mesh edges.

    Args:
        mesh: The exported OBJ mesh to modify
        target_mesh_right: OBJ mesh from adjacent frame (placed to the right), or None
        target_mesh_left: OBJ mesh from adjacent frame (placed to the left), or None
        blend_axis: Which axis to blend along (0=x, 1=y, 2=z)
        cut_width_percent: Width of edge to cut away as percentage of mesh width
        blend_width_percent: Width of blend zone as percentage of mesh width
        mesh_offset_right: Position offset of the mesh to the right along blend axis
        mesh_offset_left: Position offset of the mesh to the left along blend axis

    Returns:
        Modified mesh with cut edges and blended vertices
    """
    # Get mesh bounds along blend axis
    mesh_min, mesh_max = mesh.get_bounds(blend_axis)
    mesh_width = mesh_max - mesh_min
    cut_width = mesh_width * (cut_width_percent / 100.0)
    blend_width = mesh_width * (blend_width_percent / 100.0)

    # Calculate cut and blend boundaries for both edges
    # Right edge (positive direction)
    right_cut_boundary = mesh_max - cut_width
    right_blend_start = right_cut_boundary - blend_width

    # Left edge (negative direction)
    left_cut_boundary = mesh_min + cut_width
    left_blend_end = left_cut_boundary + blend_width

    # Build spatial lookups for target meshes
    target_lookup_right = build_spatial_lookup(target_mesh_right.vertices, blend_axis) if target_mesh_right else {}
    target_lookup_left = build_spatial_lookup(target_mesh_left.vertices, blend_axis) if target_mesh_left else {}

    # Find vertices to remove (beyond cut boundaries) and track which vertices to keep
    vertices_to_remove: Set[int] = set()
    vertex_index_map: Dict[int, int] = {}  # old index -> new index

    for i, v in enumerate(mesh.vertices):
        pos = mesh._get_axis_value(v, blend_axis)

        # Check if vertex is beyond cut boundaries
        if pos > right_cut_boundary or pos < left_cut_boundary:
            vertices_to_remove.add(i + 1)  # OBJ uses 1-based indices

    # Create new vertex list and build index mapping
    new_vertices = []
    new_index = 1
    for i, v in enumerate(mesh.vertices):
        old_index = i + 1
        if old_index not in vertices_to_remove:
            vertex_index_map[old_index] = new_index
            new_vertices.append(v)
            new_index += 1

    # Filter and remap faces (remove faces with missing vertices)
    new_faces = []
    for face in mesh.faces:
        # Check if all vertices in face are still valid
        all_valid = True
        new_face = []
        for v_idx, vt_idx, vn_idx in face:
            if v_idx in vertices_to_remove:
                all_valid = False
                break
            new_face.append((vertex_index_map[v_idx], vt_idx, vn_idx))

        if all_valid:
            new_faces.append(new_face)

    # Update mesh with new vertices and faces
    mesh.vertices = new_vertices
    mesh.faces = new_faces

    # Recalculate bounds after cutting
    mesh_min, mesh_max = mesh.get_bounds(blend_axis)

    # Blend vertices in both blend zones
    blended_right = 0
    blended_left = 0

    for v in mesh.vertices:
        pos = mesh._get_axis_value(v, blend_axis)

        # Check right edge blend zone
        if pos >= right_blend_start and target_lookup_right:
            # Calculate blend factor (0 at blend_start, 1 at cut_boundary/edge)
            blend_factor = (pos - right_blend_start) / blend_width if blend_width > 0 else 0
            smooth_factor = smoothstep(blend_factor)

            target = find_nearest_vertex_at_edge(v, target_lookup_right, blend_axis, is_right_edge=True, axis_offset=mesh_offset_right)
            if target:
                v.x = lerp(v.x, target[0], smooth_factor)
                v.y = lerp(v.y, target[1], smooth_factor)
                v.z = lerp(v.z, target[2], smooth_factor)
                blended_right += 1

        # Check left edge blend zone
        elif pos <= left_blend_end and target_lookup_left:
            # Calculate blend factor (0 at blend_end, 1 at cut_boundary/edge)
            blend_factor = (left_blend_end - pos) / blend_width if blend_width > 0 else 0
            smooth_factor = smoothstep(blend_factor)

            target = find_nearest_vertex_at_edge(v, target_lookup_left, blend_axis, is_right_edge=False, axis_offset=mesh_offset_left)
            if target:
                v.x = lerp(v.x, target[0], smooth_factor)
                v.y = lerp(v.y, target[1], smooth_factor)
                v.z = lerp(v.z, target[2], smooth_factor)
                blended_left += 1

    return mesh


def get_reference_mesh_position(blend_file: str, reference_mesh_name: str) -> Tuple[float, float, float]:
    """
    Read the position of the reference mesh from a Blender file.
    This is CRITICAL for determining the exact offset where adjacent meshes are placed.

    The reference mesh must be set up in Blender beforehand:
    1. Import a mesh from the adjacent frame (e.g., frame N-95)
    2. Position it exactly where it would be placed in Unreal
    3. Name it (e.g., "1_0_mesh_903_reference")
    4. Save the Blender file
    """
    # Create a temporary Python script to extract the position
    script_content = f'''
import bpy
import sys

mesh_name = "{reference_mesh_name}"

if mesh_name in bpy.data.objects:
    obj = bpy.data.objects[mesh_name]
    pos = obj.location
    print(f"POSITION:{{pos.x}},{{pos.y}},{{pos.z}}")
else:
    print(f"ERROR:Object '{{mesh_name}}' not found")
    print("Available objects:")
    for obj in bpy.data.objects:
        print(f"  - {{obj.name}}")
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


def find_frame_files(input_folder: str, frame: int, chunk_x: Optional[int] = None) -> List[str]:
    """Find all OBJ files for a specific frame and optionally specific chunk x position"""
    if chunk_x is not None:
        pattern = re.compile(rf'^{chunk_x}_(\d+)_mesh_{frame}\.obj$')
    else:
        pattern = re.compile(rf'^(\d+)_(\d+)_mesh_{frame}\.obj$')

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


def load_chunk_mesh(input_folder: str, frame: int, chunk_x: int, chunk_y: int = 0) -> Optional[OBJMesh]:
    """Load a specific chunk's OBJ mesh for a given frame"""
    filename = f"{chunk_x}_{chunk_y}_mesh_{frame}.obj"
    filepath = os.path.join(input_folder, filename)

    if os.path.exists(filepath):
        return parse_obj_file(filepath)
    return None


def process_folder(
    input_folder: str,
    output_folder: str,
    blend_file: str,
    position_offset: Tuple[float, float, float],
    frame_offset: int,
    cut_width_percent: float,
    blend_width_percent: float,
    blend_axis: int
):
    """Process all frames in a folder"""

    frames = get_all_frames(input_folder)
    if not frames:
        print(f"No OBJ files found in {input_folder}")
        return

    print(f"Found {len(frames)} frames: {frames[0]} to {frames[-1]}")
    print(f"Reference mesh position offset: {position_offset}")
    print(f"Frame offset: {frame_offset}")
    print(f"Cut width: {cut_width_percent}%")
    print(f"Blend width: {blend_width_percent}%")
    print(f"Blend axis: {['x', 'y', 'z'][blend_axis]}")
    print()

    # Create output folder
    os.makedirs(output_folder, exist_ok=True)

    # Use the reference mesh position to determine the offset along the blend axis
    # The reference mesh shows where ONE adjacent mesh is placed (in the direction of the offset)
    # For negative offset: that's the "negative/min" direction mesh
    # For positive offset: that's the "positive/max" direction mesh
    ref_offset = position_offset[blend_axis]
    if ref_offset < 0:
        # Reference mesh is in negative direction (min side)
        mesh_offset_negative = ref_offset
        mesh_offset_positive = -ref_offset
    else:
        # Reference mesh is in positive direction (max side)
        mesh_offset_positive = ref_offset
        mesh_offset_negative = -ref_offset
    print(f"Position offsets along blend axis: positive={mesh_offset_positive:.2f}, negative={mesh_offset_negative:.2f}")
    print()

    # Cache for loaded OBJ meshes (to avoid loading same mesh multiple times)
    mesh_cache: Dict[Tuple[int, int, int], OBJMesh] = {}  # (frame, chunk_x, chunk_y) -> mesh

    def get_cached_mesh(frame: int, chunk_x: int, chunk_y: int = 0) -> Optional[OBJMesh]:
        cache_key = (frame, chunk_x, chunk_y)
        if cache_key not in mesh_cache:
            mesh = load_chunk_mesh(input_folder, frame, chunk_x, chunk_y)
            if mesh:
                mesh_cache[cache_key] = mesh
        return mesh_cache.get(cache_key)

    # Process each frame
    for i, frame in enumerate(frames):
        print(f"Processing frame {frame} ({i + 1}/{len(frames)})...")

        # Calculate target frames for blending (with wraparound)
        # frame_offset is typically negative (-95), so:
        # - right_target = frame + (-95) = earlier frame (mesh placed to the right)
        # - left_target = frame - (-95) = frame + 95 = later frame (mesh placed to the left)
        right_target_frame = frames[(frames.index(frame) + frame_offset) % len(frames)]
        left_target_frame = frames[(frames.index(frame) - frame_offset) % len(frames)]

        print(f"  Right edge blends toward frame {right_target_frame}")
        print(f"  Left edge blends toward frame {left_target_frame}")

        # Process all chunk files for this frame
        all_files = find_frame_files(input_folder, frame)

        for source_file in all_files:
            filename = os.path.basename(source_file)

            # Parse chunk coordinates from filename
            match = re.match(r'^(\d+)_(\d+)_mesh_\d+\.obj$', filename)
            if not match:
                continue

            chunk_x = int(match.group(1))
            chunk_y = int(match.group(2))

            # Load the mesh
            mesh = parse_obj_file(source_file)

            # Load target meshes from adjacent frames (same chunk position)
            # Each chunk spans the full width, so we blend both edges
            target_mesh_right = get_cached_mesh(right_target_frame, chunk_x, chunk_y)
            target_mesh_left = get_cached_mesh(left_target_frame, chunk_x, chunk_y)

            if target_mesh_right:
                print(f"    Loaded right target: {chunk_x}_{chunk_y}_mesh_{right_target_frame}.obj ({len(target_mesh_right.vertices)} vertices)")
            if target_mesh_left:
                print(f"    Loaded left target: {chunk_x}_{chunk_y}_mesh_{left_target_frame}.obj ({len(target_mesh_left.vertices)} vertices)")

            # Apply cut and blend to both edges
            mesh = cut_and_blend_mesh(
                mesh=mesh,
                target_mesh_right=target_mesh_right,
                target_mesh_left=target_mesh_left,
                blend_axis=blend_axis,
                cut_width_percent=cut_width_percent,
                blend_width_percent=blend_width_percent,
                mesh_offset_right=mesh_offset_positive,
                mesh_offset_left=mesh_offset_negative
            )

            # Write output
            output_file = os.path.join(output_folder, filename)
            write_obj_file(output_file, mesh)

        # Clear old cache entries to manage memory (keep only recent frames)
        if len(mesh_cache) > 20:
            # Remove oldest entries
            keys_to_remove = sorted(mesh_cache.keys())[:10]
            for key in keys_to_remove:
                del mesh_cache[key]

    print(f"\nProcessed {len(frames)} frames")


def main():
    parser = argparse.ArgumentParser(
        description='Apply seamless blending to exported wave mesh OBJ files'
    )
    parser.add_argument('--blend-file', required=True,
                        help='Path to Blender simulation file (for reading reference mesh position)')
    parser.add_argument('--reference-mesh', default='1_0_mesh_903_reference',
                        help='Name of reference mesh in Blender that defines adjacent mesh position (default: 1_0_mesh_903_reference)')
    parser.add_argument('--input', required=True,
                        help='Input folder containing exported OBJ files')
    parser.add_argument('--output', default=None,
                        help='Output folder (default: /tmp/seamless_blended_meshes)')
    parser.add_argument('--frame-offset', type=int, default=-95,
                        help='Frame offset to adjacent mesh (default: -95, negative = earlier frame)')
    parser.add_argument('--cut-width', type=float, default=3.0,
                        help='Width of edge to cut away as percentage (default: 3.0)')
    parser.add_argument('--blend-width', type=float, default=3.0,
                        help='Blend zone width as percentage (default: 3.0)')
    parser.add_argument('--blend-axis', choices=['x', 'y', 'z'], default='x',
                        help='Axis along which meshes are placed (default: x)')

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
    print("SEAMLESS MESH BLENDING (OBJ-to-OBJ)")
    print("=" * 60)
    print(f"Blender file: {args.blend_file}")
    print(f"Reference mesh: {args.reference_mesh}")
    print(f"Input folder: {args.input}")
    print(f"Output folder: {output_folder}")
    print()

    # Get reference mesh position from Blender file (CRITICAL)
    print("Reading reference mesh position from Blender file...")
    position_offset = get_reference_mesh_position(args.blend_file, args.reference_mesh)
    print(f"Reference mesh position: {position_offset}")
    print()

    # Process the folder
    process_folder(
        input_folder=args.input,
        output_folder=output_folder,
        blend_file=args.blend_file,
        position_offset=position_offset,
        frame_offset=args.frame_offset,
        cut_width_percent=args.cut_width,
        blend_width_percent=args.blend_width,
        blend_axis=blend_axis
    )

    print()
    print("=" * 60)
    print("BLENDING COMPLETE")
    print("=" * 60)
    print(f"Output written to: {output_folder}")


if __name__ == '__main__':
    main()
