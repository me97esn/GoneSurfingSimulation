#!/usr/bin/env python3
"""
Seamless Mesh Blending for Infinite Wave Animation

This script post-processes exported OBJ mesh files to create seamless transitions
between adjacent meshes when placed side by side in Unreal Engine.

The exported meshes have distorted/curved edges due to decimation. This script:
1. Cuts away the distorted edges (~3% of mesh width) from both left and right sides
2. Blends the remaining edge vertices toward the original simulation data

For each frame N:
- Right edge: blends toward frame N+frame_offset (the mesh placed to the right)
- Left edge: blends toward frame N-frame_offset (the mesh placed to the left)

IMPORTANT: Requires a reference mesh to be set up in Blender first!
The reference mesh defines the exact position offset where adjacent meshes are placed.

Usage:
    python apply_seamless_blending.py --blend-file <blender_file> --reference-mesh <mesh_name> --input <folder> [options]

Example:
    python apply_seamless_blending.py \
        --blend-file ../3dmodels/breaking_waves_beach_break_2.blend \
        --reference-mesh "frame_857_reference" \
        --input /hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_05 \
        --frame-offset -95
"""

import argparse
import os
import re
import sys
import subprocess
import tempfile
import shutil
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


def cut_and_blend_mesh(
    mesh: OBJMesh,
    simulation_vertices_right: List[Tuple[float, float, float]],
    simulation_vertices_left: List[Tuple[float, float, float]],
    blend_axis: int,
    cut_width_percent: float,
    blend_width_percent: float,
    mesh_offset_right: float,
    mesh_offset_left: float
) -> OBJMesh:
    """
    Cut away distorted edges and blend remaining edge vertices toward simulation data.

    Args:
        mesh: The exported OBJ mesh to modify
        simulation_vertices_right: Original simulation vertices for the mesh placed to the right
        simulation_vertices_left: Original simulation vertices for the mesh placed to the left
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

    # Build spatial lookup for simulation vertices (for finding corresponding vertices)
    def build_spatial_lookup(sim_vertices: List[Tuple[float, float, float]]) -> Dict[Tuple[float, float], List[Tuple[float, float, float]]]:
        lookup = {}
        for v in sim_vertices:
            # Create key based on non-blend axes (rounded for matching)
            if blend_axis == 0:
                key = (round(v[1], 2), round(v[2], 2))
            elif blend_axis == 1:
                key = (round(v[0], 2), round(v[2], 2))
            else:
                key = (round(v[0], 2), round(v[1], 2))

            if key not in lookup:
                lookup[key] = []
            lookup[key].append(v)
        return lookup

    sim_lookup_right = build_spatial_lookup(simulation_vertices_right) if simulation_vertices_right else {}
    sim_lookup_left = build_spatial_lookup(simulation_vertices_left) if simulation_vertices_left else {}

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

    def find_nearest_sim_vertex(v: Vertex, sim_lookup: Dict, axis_offset: float, is_right_edge: bool) -> Optional[Tuple[float, float, float]]:
        """Find the nearest simulation vertex for blending"""
        if blend_axis == 0:
            key = (round(v.y, 2), round(v.z, 2))
        elif blend_axis == 1:
            key = (round(v.x, 2), round(v.z, 2))
        else:
            key = (round(v.x, 2), round(v.y, 2))

        if key not in sim_lookup:
            # Try nearby keys with looser tolerance
            for delta1 in [-0.05, 0, 0.05]:
                for delta2 in [-0.05, 0, 0.05]:
                    nearby_key = (round(key[0] + delta1, 2), round(key[1] + delta2, 2))
                    if nearby_key in sim_lookup:
                        key = nearby_key
                        break
                if key in sim_lookup:
                    break

        if key not in sim_lookup:
            return None

        candidates = sim_lookup[key]

        # Find the vertex at the edge of the simulation mesh
        # For right edge blending, we want the leftmost vertex from the right mesh
        # For left edge blending, we want the rightmost vertex from the left mesh
        if is_right_edge:
            # Simulation mesh is placed to the right, so its left edge aligns with our right edge
            # Find the minimum position along blend axis
            best = min(candidates, key=lambda c: c[blend_axis])
        else:
            # Simulation mesh is placed to the left, so its right edge aligns with our left edge
            # Find the maximum position along blend axis
            best = max(candidates, key=lambda c: c[blend_axis])

        # Apply position offset to get world position
        result = list(best)
        result[blend_axis] += axis_offset
        return tuple(result)

    # Blend vertices in both blend zones
    blended_right = 0
    blended_left = 0

    for v in mesh.vertices:
        pos = mesh._get_axis_value(v, blend_axis)

        # Check right edge blend zone
        if pos >= right_blend_start and sim_lookup_right:
            # Calculate blend factor (0 at blend_start, 1 at cut_boundary/edge)
            blend_factor = (pos - right_blend_start) / blend_width if blend_width > 0 else 0
            smooth_factor = smoothstep(blend_factor)

            target = find_nearest_sim_vertex(v, sim_lookup_right, mesh_offset_right, is_right_edge=True)
            if target:
                v.x = lerp(v.x, target[0], smooth_factor)
                v.y = lerp(v.y, target[1], smooth_factor)
                v.z = lerp(v.z, target[2], smooth_factor)
                blended_right += 1

        # Check left edge blend zone
        elif pos <= left_blend_end and sim_lookup_left:
            # Calculate blend factor (0 at blend_end, 1 at cut_boundary/edge)
            blend_factor = (left_blend_end - pos) / blend_width if blend_width > 0 else 0
            smooth_factor = smoothstep(blend_factor)

            target = find_nearest_sim_vertex(v, sim_lookup_left, mesh_offset_left, is_right_edge=False)
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
    3. Name it (e.g., "frame_857_reference")
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


def get_simulation_vertices_for_frame(blend_file: str, frame: int, fluid_surface_name: str = "fluid_surface") -> List[Tuple[float, float, float]]:
    """
    Load original simulation vertex positions from Blender file at a specific frame.
    This runs Blender in background mode and extracts the undistorted vertex positions.
    """
    # Create a temporary Python script to extract vertex positions
    script_content = f'''
import bpy
import sys

frame = {frame}
fluid_surface_name = "{fluid_surface_name}"

# Set the frame
bpy.context.scene.frame_set(frame)

# Find the fluid surface object
fluid_surface = None
for obj in bpy.data.objects:
    if fluid_surface_name in obj.name:
        fluid_surface = obj
        break

if fluid_surface is None:
    print("ERROR:Fluid surface object not found")
    sys.exit(1)

# Get evaluated mesh (with modifiers/simulation applied but before our export modifiers)
depsgraph = bpy.context.evaluated_depsgraph_get()
obj_eval = fluid_surface.evaluated_get(depsgraph)

# Get mesh data
mesh = obj_eval.to_mesh()

# Output vertex positions
print("VERTICES_START")
for v in mesh.vertices:
    # Apply object transform to get world coordinates
    world_pos = obj_eval.matrix_world @ v.co
    print(f"{{world_pos.x:.6f}},{{world_pos.y:.6f}},{{world_pos.z:.6f}}")
print("VERTICES_END")

# Clean up
obj_eval.to_mesh_clear()
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        # Run Blender in background mode
        result = subprocess.run(
            ['blender', blend_file, '--background', '--python', script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Parse the output to extract vertices
        vertices = []
        in_vertices = False

        for line in result.stdout.split('\n'):
            if line == "VERTICES_START":
                in_vertices = True
                continue
            elif line == "VERTICES_END":
                in_vertices = False
                continue
            elif line.startswith("ERROR:"):
                print(f"Error loading frame {frame}: {line}")
                return []
            elif in_vertices and ',' in line:
                try:
                    coords = line.split(',')
                    vertices.append((float(coords[0]), float(coords[1]), float(coords[2])))
                except (ValueError, IndexError):
                    continue

        return vertices

    except subprocess.TimeoutExpired:
        print(f"Timeout loading frame {frame}")
        return []
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


def get_mesh_dimensions(input_folder: str, frames: List[int], blend_axis: int) -> Tuple[float, float]:
    """Get the mesh dimensions from a sample mesh to calculate offsets"""
    # Load first available mesh to get dimensions
    sample_files = find_frame_files(input_folder, frames[0])
    if not sample_files:
        return (0.0, 0.0)

    mesh = parse_obj_file(sample_files[0])
    return mesh.get_bounds(blend_axis)


def process_folder(
    input_folder: str,
    output_folder: str,
    blend_file: str,
    position_offset: Tuple[float, float, float],
    frame_offset: int,
    cut_width_percent: float,
    blend_width_percent: float,
    blend_axis: int,
    left_edge_chunk_x: int,
    right_edge_chunk_x: int
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
    print(f"Left edge chunk x: {left_edge_chunk_x}")
    print(f"Right edge chunk x: {right_edge_chunk_x}")
    print()

    # Create output folder
    os.makedirs(output_folder, exist_ok=True)

    # Use the reference mesh position to determine the offset along the blend axis
    # The reference mesh shows where the RIGHT adjacent mesh is placed
    mesh_offset_right = position_offset[blend_axis]
    # The LEFT adjacent mesh is at the negative of this offset
    mesh_offset_left = -mesh_offset_right
    print(f"Position offsets along blend axis: right={mesh_offset_right:.2f}, left={mesh_offset_left:.2f}")
    print()

    # Cache for simulation vertices (to avoid loading same frame multiple times)
    sim_cache: Dict[int, List[Tuple[float, float, float]]] = {}

    def get_cached_simulation_vertices(frame: int) -> List[Tuple[float, float, float]]:
        if frame not in sim_cache:
            print(f"    Loading simulation data for frame {frame}...")
            sim_cache[frame] = get_simulation_vertices_for_frame(blend_file, frame)
            print(f"    Loaded {len(sim_cache[frame])} vertices")
        return sim_cache[frame]

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

        # Load simulation data for target frames
        sim_vertices_right = get_cached_simulation_vertices(right_target_frame)
        sim_vertices_left = get_cached_simulation_vertices(left_target_frame)

        # Process all chunk files for this frame
        all_files = find_frame_files(input_folder, frame)

        for source_file in all_files:
            filename = os.path.basename(source_file)

            # Parse chunk coordinates from filename
            match = re.match(r'^(\d+)_(\d+)_mesh_\d+\.obj$', filename)
            if not match:
                continue

            chunk_x = int(match.group(1))

            # Determine which edges this chunk has
            has_right_edge = (chunk_x == right_edge_chunk_x)
            has_left_edge = (chunk_x == left_edge_chunk_x)

            # Load the mesh
            mesh = parse_obj_file(source_file)

            if has_right_edge or has_left_edge:
                # Apply cut and blend
                mesh = cut_and_blend_mesh(
                    mesh=mesh,
                    simulation_vertices_right=sim_vertices_right if has_right_edge else [],
                    simulation_vertices_left=sim_vertices_left if has_left_edge else [],
                    blend_axis=blend_axis,
                    cut_width_percent=cut_width_percent,
                    blend_width_percent=blend_width_percent,
                    mesh_offset_right=mesh_offset_right,
                    mesh_offset_left=mesh_offset_left
                )

            # Write output
            output_file = os.path.join(output_folder, filename)
            write_obj_file(output_file, mesh)

        # Clear old cache entries to manage memory (keep only recent frames)
        if len(sim_cache) > 10:
            oldest_cached = min(sim_cache.keys())
            del sim_cache[oldest_cached]

    print(f"\nProcessed {len(frames)} frames")


def main():
    parser = argparse.ArgumentParser(
        description='Apply seamless blending to exported wave mesh OBJ files'
    )
    parser.add_argument('--blend-file', required=True,
                        help='Path to Blender simulation file (for reading original vertex positions AND reference mesh)')
    parser.add_argument('--reference-mesh', required=True,
                        help='REQUIRED: Name of reference mesh in Blender that defines adjacent mesh position')
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
    parser.add_argument('--left-edge-chunk', type=int, default=0,
                        help='X index of left edge chunks (default: 0)')
    parser.add_argument('--right-edge-chunk', type=int, default=2,
                        help='X index of right edge chunks (default: 2 for 3x1 grid)')

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
    print("SEAMLESS MESH BLENDING (Cut and Blend)")
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
        blend_axis=blend_axis,
        left_edge_chunk_x=args.left_edge_chunk,
        right_edge_chunk_x=args.right_edge_chunk
    )

    print()
    print("=" * 60)
    print("BLENDING COMPLETE")
    print("=" * 60)
    print(f"Output written to: {output_folder}")


if __name__ == '__main__':
    main()
