"""
Export wave animation as chunked OBJ meshes at multiple quality levels.
This script is designed to be run inside Blender (via command line).

Includes seamless edge blending for infinite wave tiling.
"""
import bpy
import os
import sys
import bmesh
import time
import math
from mathutils import Vector
from mathutils.kdtree import KDTree

# Get command-line arguments passed after --
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []

if len(argv) < 4:
    print("Error: Missing required arguments")
    print("Usage: blender file.blend --background --python export_waves_display.py -- <start_frame> <end_frame> <output_base_dir> <quality_levels_csv> [skip_existing] [frame_offset] [reference_mesh] [grid_step_size]")
    print("Example: blender file.blend --background --python export_waves_display.py -- 752 868 /hdd/exports 0.05,0.04,0.03,0.02,0.01 skip -95 1_0_mesh_903_reference 2.0")
    sys.exit(1)

start_frame = int(argv[0])
end_frame = int(argv[1])
output_base_dir = argv[2]
quality_levels = [float(x) for x in argv[3].split(',')]
skip_existing = argv[4] if len(argv) > 4 else 'skip'
frame_offset = int(argv[5]) if len(argv) > 5 else -95
reference_mesh_name = argv[6] if len(argv) > 6 else '1_0_mesh_903_reference'
grid_step_size = float(argv[7]) if len(argv) > 7 else 2.0

# Seamless blending configuration
BLEND_WIDTH_PERCENT = 3.0  # Width of blend zone as percentage of mesh extent

print(f"="*60)
print(f"WAVE DISPLAY EXPORT (with seamless blending)")
print(f"="*60)
print(f"Start frame: {start_frame}")
print(f"End frame: {end_frame}")
print(f"Output base directory: {output_base_dir}")
print(f"Quality levels (decimate ratios): {quality_levels}")
print(f"Skip existing files: {skip_existing}")
print(f"Frame offset for blending: {frame_offset}")
print(f"Reference mesh: {reference_mesh_name}")
print(f"Blend width: {BLEND_WIDTH_PERCENT}%")
print(f"="*60)

# Configuration
CHUNKS_X = 3  # Split 3 times along longest axis
CHUNKS_Y = 1  # Split 1 time along second longest axis
FLUID_SURFACE_NAME = 'fluid_surface'
BOOL_BOUNDARY_NAME = 'BoolBoundary'


def smoothstep(t):
    """Smooth interpolation function (ease-in-out)"""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def get_height_at_position(world_verts, target_pos, blend_axis_idx, search_radius=10.0):
    """
    Get the approximate height (Z) at a given position by averaging nearby vertices.
    Uses inverse distance weighting for smooth interpolation.

    Args:
        world_verts: List of world-space vertex positions
        target_pos: Position to find height at (Vector)
        blend_axis_idx: Axis index being blended (0=x, 1=y, 2=z)
        search_radius: Radius to search for nearby vertices

    Returns:
        Average height (Z value) at the position, or None if no vertices found
    """
    heights = []
    weights = []

    # Non-blend axes for distance calculation
    non_blend_axes = [i for i in range(3) if i != blend_axis_idx]

    for world_pos in world_verts:
        # Calculate 2D distance on non-blend axes
        dist_sq = 0
        for axis in non_blend_axes:
            dist_sq += (world_pos[axis] - target_pos[axis])**2
        dist = math.sqrt(dist_sq)

        if dist < search_radius:
            weight = 1.0 / (dist + 0.1)  # Inverse distance weighting
            heights.append(world_pos.z)
            weights.append(weight)

    if heights:
        total_weight = sum(weights)
        return sum(h * w for h, w in zip(heights, weights)) / total_weight
    return None


def get_reference_mesh_offset(reference_mesh_name):
    """Get the position offset from the reference mesh"""
    ref_obj = bpy.data.objects.get(reference_mesh_name)
    if ref_obj:
        return ref_obj.location.copy()
    else:
        print(f"  Warning: Reference mesh '{reference_mesh_name}' not found")
        return None


def create_joined_blended_mesh(fluid_surface, current_frame, frame_offset, reference_offset, blend_axis_idx, blend_width_percent):
    """
    Create a joined mesh from current frame and adjacent frame with blended overlap.

    This approach:
    1. Gets the current frame mesh and the adjacent frame mesh
    2. Positions the adjacent mesh at its tiling location (reference_offset)
    3. Blends vertices in the overlapping region for smooth transition
    4. Joins the meshes into a single continuous surface

    Args:
        fluid_surface: The original fluid surface object
        current_frame: Current frame number
        frame_offset: Frame offset to adjacent mesh (e.g., -95)
        reference_offset: Position offset from reference mesh
        blend_axis_idx: Axis index to blend along (0=x, 1=y, 2=z)
        blend_width_percent: Width of blend zone as percentage

    Returns:
        The joined mesh object with blended overlap
    """
    ref_axis_offset = reference_offset[blend_axis_idx]

    # Determine which adjacent frame to use based on reference offset direction
    # If ref_axis_offset < 0, the adjacent mesh is placed in negative direction
    if ref_axis_offset < 0:
        adjacent_frame = current_frame + frame_offset  # e.g., 903 + (-95) = 808
    else:
        adjacent_frame = current_frame - frame_offset

    print(f"  Creating joined blended mesh:")
    print(f"    Current frame: {current_frame}")
    print(f"    Adjacent frame: {adjacent_frame}")
    print(f"    Reference offset on axis {blend_axis_idx}: {ref_axis_offset:.2f}")

    # Store original frame
    original_frame = bpy.context.scene.frame_current

    # Get current frame mesh
    bpy.context.scene.frame_set(current_frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_current = fluid_surface.evaluated_get(depsgraph)

    current_obj = bpy.data.objects.new(f"current_{current_frame}", bpy.data.meshes.new_from_object(eval_current))
    bpy.context.collection.objects.link(current_obj)

    # Get current mesh bounds
    current_matrix = current_obj.matrix_world
    current_verts_world = [current_matrix @ v.co for v in current_obj.data.vertices]
    current_axis_values = [v[blend_axis_idx] for v in current_verts_world]
    current_min = min(current_axis_values)
    current_max = max(current_axis_values)
    current_extent = current_max - current_min

    print(f"    Current mesh bounds on axis {blend_axis_idx}: [{current_min:.2f}, {current_max:.2f}]")

    # Get adjacent frame mesh
    bpy.context.scene.frame_set(adjacent_frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_adjacent = fluid_surface.evaluated_get(depsgraph)

    adjacent_obj = bpy.data.objects.new(f"adjacent_{adjacent_frame}", bpy.data.meshes.new_from_object(eval_adjacent))
    bpy.context.collection.objects.link(adjacent_obj)

    # Position adjacent mesh at its tiling location using FULL reference offset
    # The reference mesh shows exactly where the tiled copy should be placed
    adjacent_obj.location = reference_offset.copy()

    # Apply the location transform to the mesh data
    bpy.context.view_layer.objects.active = adjacent_obj
    adjacent_obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    # Get adjacent mesh bounds (after positioning)
    adjacent_matrix = adjacent_obj.matrix_world
    adjacent_verts_world = [adjacent_matrix @ v.co for v in adjacent_obj.data.vertices]
    adjacent_axis_values = [v[blend_axis_idx] for v in adjacent_verts_world]
    adjacent_min = min(adjacent_axis_values)
    adjacent_max = max(adjacent_axis_values)

    print(f"    Adjacent mesh bounds on axis {blend_axis_idx}: [{adjacent_min:.2f}, {adjacent_max:.2f}]")

    # Calculate overlap region
    overlap_start = max(current_min, adjacent_min)
    overlap_end = min(current_max, adjacent_max)
    overlap_width = overlap_end - overlap_start

    print(f"    Overlap region: [{overlap_start:.2f}, {overlap_end:.2f}] (width: {overlap_width:.2f})")

    if overlap_width <= 0:
        gap_width = -overlap_width
        print(f"    Gap between meshes: {gap_width:.2f} units - blending edge vertices to close gap")

        # For a gap, we need to move edge vertices toward each other
        # The edge of current mesh closest to the gap, and edge of adjacent mesh closest to the gap
        # Meet in the middle

        non_blend_axes = [i for i in range(3) if i != blend_axis_idx]

        # Determine which edges are facing the gap
        if ref_axis_offset < 0:
            # Adjacent is in negative direction
            # Current's MIN edge faces the gap, Adjacent's MAX edge faces the gap
            current_gap_edge = current_min
            adjacent_gap_edge = adjacent_max
            gap_center = (current_min + adjacent_max) / 2.0
        else:
            # Adjacent is in positive direction
            current_gap_edge = current_max
            adjacent_gap_edge = adjacent_min
            gap_center = (current_max + adjacent_min) / 2.0

        print(f"    Current edge at gap: {current_gap_edge:.2f}")
        print(f"    Adjacent edge at gap: {adjacent_gap_edge:.2f}")
        print(f"    Gap center: {gap_center:.2f}")

        # Define blend zone width (use a percentage of the mesh extent or a fixed amount)
        blend_zone_width = max(gap_width * 3, current_extent * 0.05)  # At least 3x gap width or 5% of mesh
        print(f"    Blend zone width: {blend_zone_width:.2f}")

        # Overlap factor: how far past the gap center vertices should move (as fraction of blend zone)
        OVERLAP_FACTOR = 0.3  # Move 30% into the other mesh's territory
        # Height blend strength: how much to blend Z values (0 = no height blend, 1 = full blend)
        HEIGHT_BLEND_STRENGTH = 0.7

        # Build KD-trees for spatial matching (using non-blend axes)
        current_world_verts = [current_matrix @ v.co.copy() for v in current_obj.data.vertices]
        adjacent_world_verts = [adjacent_matrix @ v.co.copy() for v in adjacent_obj.data.vertices]

        adjacent_kd = KDTree(len(adjacent_world_verts))
        for i, v in enumerate(adjacent_world_verts):
            match_pos = Vector((v[non_blend_axes[0]], v[non_blend_axes[1]], 0))
            adjacent_kd.insert(match_pos, i)
        adjacent_kd.balance()

        current_kd = KDTree(len(current_world_verts))
        for i, v in enumerate(current_world_verts):
            match_pos = Vector((v[non_blend_axes[0]], v[non_blend_axes[1]], 0))
            current_kd.insert(match_pos, i)
        current_kd.balance()

        blended_current = 0
        blended_adjacent = 0

        # Blend current mesh vertices near the gap edge using OVERLAP approach
        for i, vert in enumerate(current_obj.data.vertices):
            world_pos = current_world_verts[i]
            axis_pos = world_pos[blend_axis_idx]

            # Check if vertex is in the blend zone (near the gap edge)
            if ref_axis_offset < 0:
                # Current's MIN edge faces gap
                dist_from_edge = axis_pos - current_gap_edge
                if 0 <= dist_from_edge <= blend_zone_width:
                    # Blend factor: 1 at edge (move fully), 0 at blend_zone_width (don't move)
                    blend_factor = 1.0 - (dist_from_edge / blend_zone_width)
                    smooth_factor = smoothstep(blend_factor)

                    # Get target height from adjacent mesh using weighted interpolation
                    target_height = get_height_at_position(adjacent_world_verts, world_pos, blend_axis_idx, search_radius=10.0)

                    if target_height is not None:
                        # OVERLAP approach: move PAST the gap center into adjacent mesh territory
                        overlap_target = adjacent_gap_edge - blend_zone_width * OVERLAP_FACTOR
                        new_axis_pos = axis_pos + (overlap_target - axis_pos) * smooth_factor
                        new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * HEIGHT_BLEND_STRENGTH

                        new_world_pos = world_pos.copy()
                        new_world_pos[blend_axis_idx] = new_axis_pos
                        new_world_pos.z = new_z
                        vert.co = current_matrix.inverted() @ new_world_pos
                        blended_current += 1
            else:
                # Current's MAX edge faces gap
                dist_from_edge = current_gap_edge - axis_pos
                if 0 <= dist_from_edge <= blend_zone_width:
                    blend_factor = 1.0 - (dist_from_edge / blend_zone_width)
                    smooth_factor = smoothstep(blend_factor)

                    target_height = get_height_at_position(adjacent_world_verts, world_pos, blend_axis_idx, search_radius=10.0)

                    if target_height is not None:
                        # OVERLAP approach: move PAST the gap center into adjacent mesh territory
                        overlap_target = adjacent_gap_edge + blend_zone_width * OVERLAP_FACTOR
                        new_axis_pos = axis_pos + (overlap_target - axis_pos) * smooth_factor
                        new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * HEIGHT_BLEND_STRENGTH

                        new_world_pos = world_pos.copy()
                        new_world_pos[blend_axis_idx] = new_axis_pos
                        new_world_pos.z = new_z
                        vert.co = current_matrix.inverted() @ new_world_pos
                        blended_current += 1

        current_obj.data.update()

        # Blend adjacent mesh vertices near the gap edge using OVERLAP approach
        for i, vert in enumerate(adjacent_obj.data.vertices):
            world_pos = adjacent_world_verts[i]
            axis_pos = world_pos[blend_axis_idx]

            if ref_axis_offset < 0:
                # Adjacent's MAX edge faces gap
                dist_from_edge = adjacent_gap_edge - axis_pos
                if 0 <= dist_from_edge <= blend_zone_width:
                    blend_factor = 1.0 - (dist_from_edge / blend_zone_width)
                    smooth_factor = smoothstep(blend_factor)

                    target_height = get_height_at_position(current_world_verts, world_pos, blend_axis_idx, search_radius=10.0)

                    if target_height is not None:
                        # OVERLAP approach: move PAST the gap center into current mesh territory
                        overlap_target = current_gap_edge + blend_zone_width * OVERLAP_FACTOR
                        new_axis_pos = axis_pos + (overlap_target - axis_pos) * smooth_factor
                        new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * HEIGHT_BLEND_STRENGTH

                        new_world_pos = world_pos.copy()
                        new_world_pos[blend_axis_idx] = new_axis_pos
                        new_world_pos.z = new_z
                        vert.co = adjacent_matrix.inverted() @ new_world_pos
                        blended_adjacent += 1
            else:
                # Adjacent's MIN edge faces gap
                dist_from_edge = axis_pos - adjacent_gap_edge
                if 0 <= dist_from_edge <= blend_zone_width:
                    blend_factor = 1.0 - (dist_from_edge / blend_zone_width)
                    smooth_factor = smoothstep(blend_factor)

                    target_height = get_height_at_position(current_world_verts, world_pos, blend_axis_idx, search_radius=10.0)

                    if target_height is not None:
                        # OVERLAP approach: move PAST the gap center into current mesh territory
                        overlap_target = current_gap_edge - blend_zone_width * OVERLAP_FACTOR
                        new_axis_pos = axis_pos + (overlap_target - axis_pos) * smooth_factor
                        new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * HEIGHT_BLEND_STRENGTH

                        new_world_pos = world_pos.copy()
                        new_world_pos[blend_axis_idx] = new_axis_pos
                        new_world_pos.z = new_z
                        vert.co = adjacent_matrix.inverted() @ new_world_pos
                        blended_adjacent += 1

        adjacent_obj.data.update()

        print(f"    Blended {blended_current} current mesh vertices, {blended_adjacent} adjacent mesh vertices")

        # Join the meshes
        bpy.ops.object.select_all(action='DESELECT')
        current_obj.select_set(True)
        adjacent_obj.select_set(True)
        bpy.context.view_layer.objects.active = current_obj
        bpy.ops.object.join()

        # Merge close vertices at the seam (with larger merge distance for overlap approach)
        print(f"    Merging close vertices at the gap seam...")
        bm_merged = bmesh.new()
        bm_merged.from_mesh(current_obj.data)

        # Apply world transform to identify seam vertices
        matrix_merged = current_obj.matrix_world
        seam_verts = []
        for v in bm_merged.verts:
            world_pos = matrix_merged @ v.co
            # Select vertices near the original gap region
            if abs(world_pos[blend_axis_idx] - gap_center) < blend_zone_width:
                seam_verts.append(v)

        verts_before = len(bm_merged.verts)
        print(f"    Found {len(seam_verts)} vertices near seam")

        # Use larger merge distance (0.3) for overlap approach
        bmesh.ops.remove_doubles(bm_merged, verts=seam_verts, dist=0.3)

        # Recalculate normals for smooth shading at the seam
        bmesh.ops.recalc_face_normals(bm_merged, faces=bm_merged.faces)

        print(f"    Merged vertices: {len(bm_merged.verts)} (was {verts_before}, removed {verts_before - len(bm_merged.verts)})")

        bm_merged.to_mesh(current_obj.data)
        bm_merged.free()
        current_obj.data.update()

        joined_obj = current_obj
        joined_obj.name = f"joined_{current_frame}"
        print(f"    Joined mesh: {len(joined_obj.data.vertices)} vertices, {len(joined_obj.data.polygons)} faces")

        bpy.context.scene.frame_set(original_frame)
        return joined_obj

    # Blend vertices in the overlap region
    # Current mesh: vertices near the edge toward adjacent mesh blend toward adjacent positions
    # Adjacent mesh: vertices near the edge toward current mesh blend toward current positions

    non_blend_axes = [i for i in range(3) if i != blend_axis_idx]

    # Determine which direction to blend based on overlap position
    # If adjacent mesh is in negative direction (ref_axis_offset < 0):
    #   - Current mesh's MIN edge overlaps with adjacent mesh's MAX edge
    #   - Blend current vertices near current_min toward adjacent vertices
    #   - Blend adjacent vertices near adjacent_max toward current vertices

    if ref_axis_offset < 0:
        # Adjacent is in negative direction
        # Current's min edge meets adjacent's max edge
        current_blend_edge = current_min
        adjacent_blend_edge = adjacent_max
        # Blend zone for current: from current_min to current_min + overlap_width
        # Blend zone for adjacent: from adjacent_max - overlap_width to adjacent_max
    else:
        # Adjacent is in positive direction
        current_blend_edge = current_max
        adjacent_blend_edge = adjacent_min

    # Collect world positions of both meshes for matching
    current_world_verts = [current_matrix @ v.co.copy() for v in current_obj.data.vertices]
    adjacent_world_verts = [adjacent_matrix @ v.co.copy() for v in adjacent_obj.data.vertices]

    # Build KD-trees for fast spatial lookups (using non-blend axes for matching)
    print(f"    Building KD-trees for spatial matching...")

    # KD-tree for adjacent mesh vertices
    adjacent_kd = KDTree(len(adjacent_world_verts))
    for i, v in enumerate(adjacent_world_verts):
        # Use position on non-blend axes for matching
        match_pos = Vector((v[non_blend_axes[0]], v[non_blend_axes[1]], 0))
        adjacent_kd.insert(match_pos, i)
    adjacent_kd.balance()

    # KD-tree for current mesh vertices
    current_kd = KDTree(len(current_world_verts))
    for i, v in enumerate(current_world_verts):
        match_pos = Vector((v[non_blend_axes[0]], v[non_blend_axes[1]], 0))
        current_kd.insert(match_pos, i)
    current_kd.balance()

    print(f"    KD-trees built")

    blended_current = 0
    blended_adjacent = 0

    # Blend current mesh vertices in overlap region
    for i, vert in enumerate(current_obj.data.vertices):
        world_pos = current_world_verts[i]
        axis_pos = world_pos[blend_axis_idx]

        # Check if vertex is in overlap region
        if overlap_start <= axis_pos <= overlap_end:
            # Calculate blend factor based on position in overlap
            if ref_axis_offset < 0:
                # Blending from current_min toward overlap_end
                # At current_min (overlap_start): blend_factor = 1 (fully toward adjacent)
                # At overlap_end: blend_factor = 0 (keep current)
                blend_factor = 1.0 - (axis_pos - overlap_start) / overlap_width
            else:
                # Blending from current_max toward overlap_start
                blend_factor = (axis_pos - overlap_start) / overlap_width

            smooth_factor = smoothstep(blend_factor)

            # Find closest adjacent vertex using KD-tree
            match_pos = Vector((world_pos[non_blend_axes[0]], world_pos[non_blend_axes[1]], 0))
            co, idx, dist = adjacent_kd.find(match_pos)
            if idx is not None:
                target_pos = adjacent_world_verts[idx]
                # Blend position
                new_world_pos = world_pos.lerp(target_pos, smooth_factor)
                vert.co = current_matrix.inverted() @ new_world_pos
                blended_current += 1

    current_obj.data.update()

    # Blend adjacent mesh vertices in overlap region
    for i, vert in enumerate(adjacent_obj.data.vertices):
        world_pos = adjacent_world_verts[i]
        axis_pos = world_pos[blend_axis_idx]

        # Check if vertex is in overlap region
        if overlap_start <= axis_pos <= overlap_end:
            # Calculate blend factor (opposite direction from current mesh)
            if ref_axis_offset < 0:
                # At overlap_start: blend_factor = 0 (keep adjacent)
                # At overlap_end (adjacent_max): blend_factor = 1 (fully toward current)
                blend_factor = (axis_pos - overlap_start) / overlap_width
            else:
                blend_factor = 1.0 - (axis_pos - overlap_start) / overlap_width

            smooth_factor = smoothstep(blend_factor)

            # Find closest current vertex using KD-tree
            match_pos = Vector((world_pos[non_blend_axes[0]], world_pos[non_blend_axes[1]], 0))
            co, idx, dist = current_kd.find(match_pos)
            if idx is not None:
                target_pos = current_world_verts[idx]
                # Blend position
                new_world_pos = world_pos.lerp(target_pos, smooth_factor)
                vert.co = adjacent_matrix.inverted() @ new_world_pos
                blended_adjacent += 1

    adjacent_obj.data.update()

    print(f"    Blended {blended_current} current mesh vertices, {blended_adjacent} adjacent mesh vertices")

    # Join the meshes
    bpy.ops.object.select_all(action='DESELECT')
    current_obj.select_set(True)
    adjacent_obj.select_set(True)
    bpy.context.view_layer.objects.active = current_obj
    bpy.ops.object.join()

    # IMPORTANT: Merge close vertices to eliminate double geometry in overlap region
    # The blending moved vertices toward each other, so they should be close enough to merge
    print(f"    Merging close vertices to eliminate double geometry...")
    bm_merged = bmesh.new()
    bm_merged.from_mesh(current_obj.data)
    verts_before = len(bm_merged.verts)

    # Merge vertices that are very close together (within 0.1 units)
    bmesh.ops.remove_doubles(bm_merged, verts=bm_merged.verts, dist=0.1)

    print(f"    Merged vertices: {len(bm_merged.verts)} (was {verts_before}, removed {verts_before - len(bm_merged.verts)})")

    bm_merged.to_mesh(current_obj.data)
    bm_merged.free()
    current_obj.data.update()

    # The joined mesh is now in current_obj
    joined_obj = current_obj
    joined_obj.name = f"joined_{current_frame}"

    print(f"    Joined mesh: {len(joined_obj.data.vertices)} vertices, {len(joined_obj.data.polygons)} faces")

    # Restore original frame
    bpy.context.scene.frame_set(original_frame)

    return joined_obj


def create_edge_vertex_group(work_obj, blend_axis_idx, blend_width_percent):
    """
    Create a vertex group containing edge vertices that should be preserved during decimation.

    Vertices at the edges get weight 0 (preserve), middle vertices get weight 1 (decimate).
    """
    mesh = work_obj.data
    matrix = work_obj.matrix_world

    # Get world positions
    world_verts = [matrix @ v.co for v in mesh.vertices]

    # Get bounds along blend axis
    axis_values = [v[blend_axis_idx] for v in world_verts]
    mesh_min = min(axis_values)
    mesh_max = max(axis_values)
    mesh_extent = mesh_max - mesh_min
    blend_width = mesh_extent * (blend_width_percent / 100.0)

    # Create or get vertex group
    vg_name = "EdgePreserve"
    if vg_name in work_obj.vertex_groups:
        vg = work_obj.vertex_groups[vg_name]
    else:
        vg = work_obj.vertex_groups.new(name=vg_name)

    # Assign weights: 0 = preserve (don't decimate), 1 = decimate normally
    edge_count = 0
    for i, vert in enumerate(mesh.vertices):
        axis_pos = world_verts[i][blend_axis_idx]

        # Check if vertex is in edge zone
        if axis_pos >= mesh_max - blend_width or axis_pos <= mesh_min + blend_width:
            # Edge vertex - weight 0 means preserve
            vg.add([i], 0.0, 'REPLACE')
            edge_count += 1
        else:
            # Middle vertex - weight 1 means normal decimation
            vg.add([i], 1.0, 'REPLACE')

    print(f"  Created vertex group '{vg_name}': {edge_count} edge vertices (preserved), {len(mesh.vertices) - edge_count} middle vertices")
    return vg_name


def sample_unified_grid(mesh_obj, grid_config):
    """
    Sample height and normals on a regular grid via ray-casting.

    Args:
        mesh_obj: Blender mesh object (the joined blended mesh)
        grid_config: dict with start_x, start_y, width, height, step_size

    Returns:
        dict with arrays: h, nx, ny, nz (each width*height floats)
    """
    start_x = grid_config['start_x']
    start_y = grid_config['start_y']
    width = grid_config['width']
    height = grid_config['height']
    step = grid_config['step_size']
    total = width * height

    h = [0.0] * total
    nx = [0.0] * total
    ny = [0.0] * total
    nz = [1.0] * total

    matrix_inv = mesh_obj.matrix_world.inverted()
    ray_dir = Vector((0, 0, -1))

    hit_count = 0
    for y_idx in range(height):
        for x_idx in range(width):
            x_pos = start_x + step * x_idx
            y_pos = start_y + step * y_idx

            ray_origin = Vector((x_pos, y_pos, 100))
            ray_origin_local = matrix_inv @ ray_origin

            hit, location, normal, face_idx = mesh_obj.ray_cast(ray_origin_local, ray_dir)

            i = y_idx * width + x_idx
            if hit:
                h[i] = float(location.z)
                normal.normalize()
                nx[i] = float(normal.x)
                ny[i] = float(normal.y)
                nz[i] = float(normal.z)
                hit_count += 1

    print(f"    Grid sampling: {hit_count}/{total} rays hit ({100*hit_count/total:.1f}%)")
    return {'h': h, 'nx': nx, 'ny': ny, 'nz': nz}


def write_unified_metadata(output_dir, grid_config, blend_config, start_frame, end_frame, reference_mesh_name):
    """Write wave_unified_metadata.json with tiling and grid parameters."""
    import json
    from datetime import datetime

    reference_offset = blend_config['reference_offset']
    seam_boundaries = blend_config['seam_boundaries']

    metadata = {
        "version": "1.0",
        "export_date": datetime.now().isoformat(),

        "tiling": {
            "tiling_x": abs(reference_offset.x),
            "tiling_y": abs(reference_offset.y),
            "comment": "Dimensions for infinite tiling, from reference mesh offset"
        },

        "grid": {
            "step_size": grid_config['step_size'],
            "grid_start_x": grid_config['start_x'],
            "grid_start_y": grid_config['start_y'],
            "grid_width": grid_config['width'],
            "grid_height": grid_config['height'],
            "comment": "Grid covers one tiling tile in X, full mesh extent in Y"
        },

        "seam_boundaries": {
            "min": seam_boundaries['min'],
            "max": seam_boundaries['max'],
            "axis": "x",
            "comment": "Seam boundaries used for mesh trimming"
        },

        "frames": {
            "start_frame": start_frame,
            "end_frame": end_frame,
            "frame_offset": blend_config['frame_offset'],
            "comment": "frame_offset is the offset to adjacent frame for blending"
        },

        "reference_mesh": {
            "name": reference_mesh_name,
            "offset_x": float(reference_offset.x),
            "offset_y": float(reference_offset.y),
            "offset_z": float(reference_offset.z)
        }
    }

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "wave_unified_metadata.json")
    with open(filepath, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Written unified metadata to {filepath}")


def write_unified_frame_data(frame, grid_config, samples, output_dir):
    """Write per-frame wave_data_frame_{frame}.json with height, normals, and velocity placeholders."""
    import json

    frame_data = {
        "frame": frame,
        "grid": {
            "width": grid_config['width'],
            "height": grid_config['height'],
            "step": grid_config['step_size'],
            "start_x": grid_config['start_x'],
            "start_y": grid_config['start_y']
        },
        "data": {
            "h": samples['h'],
            "nx": samples['nx'],
            "ny": samples['ny'],
            "nz": samples['nz'],
            "vx": [],
            "vy": [],
            "vz": []
        }
    }

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"wave_data_frame_{frame}.json")
    with open(filepath, "w") as f:
        json.dump(frame_data, f)
    print(f"    Written unified frame data to {filepath}")


def get_mesh_bounds(obj):
    """Get the bounding box of a mesh object in world space"""
    if len(obj.data.vertices) == 0:
        return None

    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_x = min(c.x for c in bbox_corners)
    max_x = max(c.x for c in bbox_corners)
    min_y = min(c.y for c in bbox_corners)
    max_y = max(c.y for c in bbox_corners)
    min_z = min(c.z for c in bbox_corners)
    max_z = max(c.z for c in bbox_corners)

    return {
        'min': Vector((min_x, min_y, min_z)),
        'max': Vector((max_x, max_y, max_z)),
        'size': Vector((max_x - min_x, max_y - min_y, max_z - min_z))
    }

def split_mesh_into_chunks(obj, chunks_x, chunks_y):
    """
    Split mesh into chunks using boolean operations.
    Returns list of chunk objects with their grid positions.
    """
    bounds = get_mesh_bounds(obj)
    if not bounds:
        return []

    # Determine which axes to split (longest and second longest)
    size = bounds['size']
    axes = [(size.x, 'x', 0), (size.y, 'y', 1), (size.z, 'z', 2)]
    axes.sort(reverse=True, key=lambda x: x[0])

    # Longest axis gets CHUNKS_X splits, second longest gets CHUNKS_Y
    primary_axis = axes[0][1]  # 'x', 'y', or 'z'
    secondary_axis = axes[1][1]

    print(f"  Splitting along {primary_axis} ({chunks_x} chunks) and {secondary_axis} ({chunks_y} chunks)")

    # Calculate chunk dimensions
    primary_idx = axes[0][2]
    secondary_idx = axes[1][2]

    primary_min = bounds['min'][primary_idx]
    primary_max = bounds['max'][primary_idx]
    secondary_min = bounds['min'][secondary_idx]
    secondary_max = bounds['max'][secondary_idx]

    primary_size = (primary_max - primary_min) / chunks_x
    secondary_size = (secondary_max - secondary_min) / chunks_y

    chunks = []

    for i in range(chunks_x):
        for j in range(chunks_y):
            # Calculate bounds for this chunk
            p_start = primary_min + i * primary_size
            p_end = primary_min + (i + 1) * primary_size
            s_start = secondary_min + j * secondary_size
            s_end = secondary_min + (j + 1) * secondary_size

            # Create a duplicate of the object for this chunk
            chunk_obj = obj.copy()
            chunk_obj.data = obj.data.copy()
            bpy.context.collection.objects.link(chunk_obj)

            # Add boolean modifiers to isolate this chunk
            # We'll use cube primitives as cutters

            # Create bounding box for this chunk
            # Note: This is a simplified approach - in production you might want
            # to use actual boolean operations with cube meshes

            chunks.append({
                'object': chunk_obj,
                'grid_x': i,
                'grid_y': j,
                'bounds': {
                    primary_axis: (p_start, p_end),
                    secondary_axis: (s_start, s_end)
                }
            })

    return chunks

def export_chunks_for_frame(fluid_surface, frame, quality_ratio, output_dir, chunks_x, chunks_y, fixed_chunk_bounds, skip_existing_files=True, blend_config=None, unified_config=None):
    """Export all chunks for a single frame at specified quality using fixed world coordinates"""
    # Check if all chunks for this frame already exist
    # For 3x1 configuration: we export 2 files (0_0 contains chunks 0&2, 1_0 is middle chunk)
    if skip_existing_files:
        all_chunks_exist = True
        # Check for combined chunk file (0_0) and middle chunk file (1_0)
        for j in range(chunks_y):
            chunk_0_filename = f"0_{j}_mesh_{frame}.obj"
            chunk_1_filename = f"1_{j}_mesh_{frame}.obj"
            chunk_0_filepath = os.path.join(output_dir, chunk_0_filename)
            chunk_1_filepath = os.path.join(output_dir, chunk_1_filename)
            if not os.path.exists(chunk_0_filepath) or not os.path.exists(chunk_1_filepath):
                all_chunks_exist = False
                break

        if all_chunks_exist:
            print(f"  Frame {frame}: All chunks already exist, skipping")
            return

    # Set the current frame
    bpy.context.scene.frame_set(frame)

    # NEW APPROACH: Join meshes, blend overlap, then decimate
    if blend_config and blend_config.get('enabled', False):
        print(f"  Using joined-mesh blending approach")

        # Create joined blended mesh (current frame + adjacent frame with blended overlap)
        joined_obj = create_joined_blended_mesh(
            fluid_surface,
            frame,
            blend_config['frame_offset'],
            blend_config['reference_offset'],
            blend_config['blend_axis_idx'],
            blend_config['blend_width_percent']
        )

        # Sample unified grid from the full-resolution blended mesh (before decimation)
        if unified_config:
            unified_output_dir = unified_config['output_dir']
            frame_filepath = os.path.join(unified_output_dir, f"wave_data_frame_{frame}.json")
            if not os.path.exists(frame_filepath):
                print(f"  Sampling unified grid from blended mesh...")
                samples = sample_unified_grid(joined_obj, unified_config['grid_config'])
                write_unified_frame_data(frame, unified_config['grid_config'], samples, unified_output_dir)
            else:
                print(f"  Unified frame data already exists, skipping")

        # Store original bounds before any processing (we'll trim back to this + margin)
        blend_axis_idx = blend_config['blend_axis_idx']
        original_seam_min = blend_config['seam_boundaries']['min']
        original_seam_max = blend_config['seam_boundaries']['max']
        original_extent = original_seam_max - original_seam_min
        trim_margin = original_extent * (blend_config['blend_width_percent'] / 100.0)

        # Trim boundaries: original size + 3% on each side
        trim_min = original_seam_min - trim_margin
        trim_max = original_seam_max + trim_margin

        print(f"  Original seam bounds: [{original_seam_min:.2f}, {original_seam_max:.2f}]")
        print(f"  Trim margin ({blend_config['blend_width_percent']}%): {trim_margin:.2f}")
        print(f"  Trim bounds: [{trim_min:.2f}, {trim_max:.2f}]")

        # Add decimate modifier to joined mesh
        decimate_mod = joined_obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate_mod.decimate_type = 'COLLAPSE'
        decimate_mod.ratio = quality_ratio
        print(f"  Added Decimate modifier with ratio {quality_ratio}")

        # Apply decimate modifier
        bpy.context.view_layer.objects.active = joined_obj
        joined_obj.select_set(True)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = joined_obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(eval_obj)
        final_obj = bpy.data.objects.new(f"processed_{frame}", mesh)
        bpy.context.collection.objects.link(final_obj)

        # Clean up joined object
        bpy.data.objects.remove(joined_obj)

        # Trim back to original size + margin using bisect
        print(f"  Trimming joined mesh to original bounds + {blend_config['blend_width_percent']}% margin")
        bm_trim = bmesh.new()
        bm_trim.from_mesh(final_obj.data)
        bm_trim.transform(final_obj.matrix_world)

        # Bisect at trim_min (remove everything below)
        plane_co_min = Vector([0, 0, 0])
        plane_co_min[blend_axis_idx] = trim_min
        plane_no_min = Vector([0, 0, 0])
        plane_no_min[blend_axis_idx] = -1.0

        verts_before = len(bm_trim.verts)
        bmesh.ops.bisect_plane(bm_trim, geom=bm_trim.verts[:] + bm_trim.edges[:] + bm_trim.faces[:],
                               plane_co=plane_co_min, plane_no=plane_no_min, clear_outer=True)
        print(f"    After min trim at {trim_min:.2f}: {len(bm_trim.verts)} verts (was {verts_before})")

        # Bisect at trim_max (remove everything above)
        plane_co_max = Vector([0, 0, 0])
        plane_co_max[blend_axis_idx] = trim_max
        plane_no_max = Vector([0, 0, 0])
        plane_no_max[blend_axis_idx] = 1.0

        verts_before = len(bm_trim.verts)
        bmesh.ops.bisect_plane(bm_trim, geom=bm_trim.verts[:] + bm_trim.edges[:] + bm_trim.faces[:],
                               plane_co=plane_co_max, plane_no=plane_no_max, clear_outer=True)
        print(f"    After max trim at {trim_max:.2f}: {len(bm_trim.verts)} verts (was {verts_before})")

        bm_trim.to_mesh(final_obj.data)
        bm_trim.free()
        final_obj.data.update()

    else:
        # Original approach: single frame processing
        # Get or create a working copy of the fluid surface
        work_obj = fluid_surface.copy()
        work_obj.data = fluid_surface.data.copy()
        bpy.context.collection.objects.link(work_obj)
        bpy.context.view_layer.objects.active = work_obj

        # FR-2: Add boolean modifier (difference with BoolBoundary) - optional
        bool_boundary = bpy.data.objects.get(BOOL_BOUNDARY_NAME)
        if bool_boundary:
            bool_mod = work_obj.modifiers.new(name="Boolean", type='BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.object = bool_boundary
            bool_mod.show_viewport = True
            bool_mod.show_render = True
            print(f"  Added Boolean modifier with {BOOL_BOUNDARY_NAME}")

        # FR-3: Add decimate modifier
        decimate_mod = work_obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate_mod.decimate_type = 'COLLAPSE'
        decimate_mod.ratio = quality_ratio
        print(f"  Added Decimate modifier with ratio {quality_ratio}")

        # Apply modifiers
        bpy.context.view_layer.objects.active = work_obj
        work_obj.select_set(True)

        # Apply modifiers by converting to mesh
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = work_obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(eval_obj)
        final_obj = bpy.data.objects.new(f"processed_{frame}", mesh)
        bpy.context.collection.objects.link(final_obj)

        # Clean up work object
        bpy.data.objects.remove(work_obj)

    # FR-4 & FR-5: Split into chunks and export using fixed world coordinates (FR-10)
    bounds = get_mesh_bounds(final_obj)
    if not bounds:
        print(f"  Warning: No geometry for frame {frame}")
        # Cleanup
        bpy.data.objects.remove(final_obj)
        return

    # FR-10: Use fixed chunk boundaries calculated from start_frame
    primary_idx = fixed_chunk_bounds['primary_idx']
    secondary_idx = fixed_chunk_bounds['secondary_idx']
    primary_min = fixed_chunk_bounds['primary_min']
    primary_max = fixed_chunk_bounds['primary_max']
    secondary_min = fixed_chunk_bounds['secondary_min']
    secondary_max = fixed_chunk_bounds['secondary_max']
    chunk_primary = fixed_chunk_bounds['chunk_primary']
    chunk_secondary = fixed_chunk_bounds['chunk_secondary']

    # Debug: Show actual mesh bounds vs fixed chunk boundaries
    print(f"  Fixed chunk boundaries: primary [{primary_min:.2f}, {primary_max:.2f}], secondary [{secondary_min:.2f}, {secondary_max:.2f}]")
    print(f"  Current mesh bounds: min={bounds['min']}, max={bounds['max']}")
    print(f"  Mesh world matrix: {final_obj.matrix_world}")

    # FR-12: Remove the flat bottom created by the boolean modifier
    # This removes only nearly-horizontal downward-facing faces (the cut plane bottom)
    # while preserving the underside of breaking waves (which have varied normals)
    print(f"  FR-12: Removing flat bottom plane created by boolean modifier")
    bm_full = bmesh.new()
    bm_full.from_mesh(final_obj.data)

    # Recalculate normals to ensure they're correct
    bmesh.ops.recalc_face_normals(bm_full, faces=bm_full.faces)
    bm_full.normal_update()

    # Count faces before removal
    total_faces_before = len(bm_full.faces)

    # Find faces that are nearly horizontal and pointing downward
    # These are the flat bottom faces created by the boolean modifier
    # Breaking wave undersides will have varied normals (not purely vertical)
    faces_to_remove = []
    HORIZONTAL_THRESHOLD = -0.95  # Normal Z must be less than -0.95 (nearly straight down)

    for face in bm_full.faces:
        # Only remove faces that are nearly perfectly horizontal and pointing down
        # This preserves curved/angled surfaces like wave undersides
        if face.normal.z < HORIZONTAL_THRESHOLD:
            faces_to_remove.append(face)

    # Remove the flat bottom faces
    bmesh.ops.delete(bm_full, geom=faces_to_remove, context='FACES')

    # Count faces after removal
    total_faces_after = len(bm_full.faces)

    print(f"  Removed {len(faces_to_remove)} nearly-horizontal bottom faces (before: {total_faces_before}, after: {total_faces_after})")

    # Update the mesh with cleaned geometry
    bm_full.to_mesh(final_obj.data)
    bm_full.free()
    final_obj.data.update()

    # Export each chunk
    os.makedirs(output_dir, exist_ok=True)

    # Calculate adjusted chunk boundaries for 3x1 configuration:
    # - Middle chunk (i=1): 20% bigger
    # - Side chunks (i=0, i=2): 10% smaller each
    # Total size remains the same: -0.1 + 1.2 + (-0.1) = 1.0
    total_primary_size = primary_max - primary_min
    original_chunk_size = total_primary_size / chunks_x  # Each chunk was 1/3

    # New sizes (as fractions of total):
    # Chunk 0: 1/3 - 10% = 1/3 * 0.9 = 0.3
    # Chunk 1: 1/3 + 20% = 1/3 * 1.2 = 0.4
    # Chunk 2: 1/3 - 10% = 1/3 * 0.9 = 0.3
    chunk_sizes = [
        original_chunk_size * 0.9,  # Chunk 0: 10% smaller
        original_chunk_size * 1.2,  # Chunk 1: 20% bigger
        original_chunk_size * 0.9   # Chunk 2: 10% smaller
    ]

    # Calculate cumulative boundaries
    chunk_boundaries = [primary_min]
    for size in chunk_sizes:
        chunk_boundaries.append(chunk_boundaries[-1] + size)

    print(f"  Adjusted chunk boundaries: {chunk_boundaries}")
    print(f"  Chunk 0 size: {chunk_sizes[0]:.2f} (90% of original)")
    print(f"  Chunk 1 size: {chunk_sizes[1]:.2f} (120% of original)")
    print(f"  Chunk 2 size: {chunk_sizes[2]:.2f} (90% of original)")

    for i in range(chunks_x):
        for j in range(chunks_y):
            # Use adjusted boundaries for primary axis
            p_start = chunk_boundaries[i]
            p_end = chunk_boundaries[i + 1]
            s_start = secondary_min + j * chunk_secondary
            s_end = secondary_min + (j + 1) * chunk_secondary

            # Create bounding box planes for this chunk
            # We'll use bisect to create clean straight edges
            bm = bmesh.new()
            bm.from_mesh(final_obj.data)

            # Apply world transform to bmesh
            bm.transform(final_obj.matrix_world)

            print(f"    Chunk ({i},{j}): Initial faces: {len(bm.faces)}, verts: {len(bm.verts)}")

            # Create plane normals and points for bisecting
            # For min boundaries: normal points inward (positive direction), keeps geometry >= p_start
            # For max boundaries: normal points inward (negative direction), keeps geometry <= p_end

            # Bisect along primary axis (min) - keep everything >= p_start
            plane_no_p_min = Vector([0, 0, 0])
            plane_no_p_min[primary_idx] = -1.0  # Normal points in negative direction, clear_outer removes < p_start
            plane_co_p_min = Vector([0, 0, 0])
            plane_co_p_min[primary_idx] = p_start

            # Bisect along primary axis (max) - keep everything <= p_end
            plane_no_p_max = Vector([0, 0, 0])
            plane_no_p_max[primary_idx] = 1.0  # Normal points in positive direction, clear_outer removes > p_end
            plane_co_p_max = Vector([0, 0, 0])
            plane_co_p_max[primary_idx] = p_end

            # Bisect along secondary axis (min) - keep everything >= s_start
            plane_no_s_min = Vector([0, 0, 0])
            plane_no_s_min[secondary_idx] = -1.0
            plane_co_s_min = Vector([0, 0, 0])
            plane_co_s_min[secondary_idx] = s_start

            # Bisect along secondary axis (max) - keep everything <= s_end
            plane_no_s_max = Vector([0, 0, 0])
            plane_no_s_max[secondary_idx] = 1.0
            plane_co_s_max = Vector([0, 0, 0])
            plane_co_s_max[secondary_idx] = s_end

            # FR-11: Perform bisect operations to cut the mesh at chunk boundaries
            # This creates clean straight edges
            print(f"    Chunk ({i},{j}): Bisecting primary min at {p_start:.2f}")
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_p_min, plane_no=plane_no_p_min, clear_outer=True)
            print(f"    Chunk ({i},{j}): After primary min bisect: faces={len(bm.faces)}, verts={len(bm.verts)}")

            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_p_max, plane_no=plane_no_p_max, clear_outer=True)
            print(f"    Chunk ({i},{j}): After primary max bisect: faces={len(bm.faces)}, verts={len(bm.verts)}")

            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_s_min, plane_no=plane_no_s_min, clear_outer=True)
            print(f"    Chunk ({i},{j}): After secondary min bisect: faces={len(bm.faces)}, verts={len(bm.verts)}")

            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_s_max, plane_no=plane_no_s_max, clear_outer=True)
            print(f"    Chunk ({i},{j}): After secondary max bisect: faces={len(bm.faces)}, verts={len(bm.verts)}")

            # Create chunk mesh
            chunk_mesh = bpy.data.meshes.new(f"chunk_{i}_{j}_{frame}")
            bm.to_mesh(chunk_mesh)
            bm.free()

            chunk_obj = bpy.data.objects.new(f"chunk_{i}_{j}_{frame}", chunk_mesh)
            bpy.context.collection.objects.link(chunk_obj)

            # Store chunk objects for later export
            if i == 0:
                chunk_0_obj = chunk_obj
                chunk_0_mesh = chunk_mesh
            elif i == 1:
                # Export middle chunk (i=1) immediately as separate file
                chunk_filename = f"{i}_{j}_mesh_{frame}.obj"
                chunk_filepath = os.path.join(output_dir, chunk_filename)

                # Select only this chunk
                bpy.ops.object.select_all(action='DESELECT')
                chunk_obj.select_set(True)
                bpy.context.view_layer.objects.active = chunk_obj

                # Export OBJ
                bpy.ops.wm.obj_export(
                    filepath=chunk_filepath,
                    export_selected_objects=True,
                    export_animation=False,
                    forward_axis='X',
                    up_axis='Z',
                    apply_modifiers=True
                )

                # Cleanup chunk object
                bpy.data.objects.remove(chunk_obj)
                bpy.data.meshes.remove(chunk_mesh)
            elif i == 2:
                # Combine chunk 0 and chunk 2 into a single file
                chunk_filename = f"0_{j}_mesh_{frame}.obj"
                chunk_filepath = os.path.join(output_dir, chunk_filename)

                # Select both chunk 0 and chunk 2
                bpy.ops.object.select_all(action='DESELECT')
                chunk_0_obj.select_set(True)
                chunk_obj.select_set(True)
                bpy.context.view_layer.objects.active = chunk_0_obj

                # Export both chunks together
                bpy.ops.wm.obj_export(
                    filepath=chunk_filepath,
                    export_selected_objects=True,
                    export_animation=False,
                    forward_axis='X',
                    up_axis='Z',
                    apply_modifiers=True
                )

                # Cleanup both chunk objects
                bpy.data.objects.remove(chunk_0_obj)
                bpy.data.meshes.remove(chunk_0_mesh)
                bpy.data.objects.remove(chunk_obj)
                bpy.data.meshes.remove(chunk_mesh)

    # Cleanup
    bpy.data.objects.remove(final_obj)

    print(f"  Exported {chunks_x * chunks_y} chunks for frame {frame}")

# Main execution
# Get the fluid surface object
fluid_surface = bpy.data.objects.get(FLUID_SURFACE_NAME)
if not fluid_surface:
    print(f"Error: Object '{FLUID_SURFACE_NAME}' not found!")
    sys.exit(1)

print(f"\nFound fluid surface: {fluid_surface.name}")

# FR-10: Calculate fixed chunk boundaries from start_frame
print(f"\n{'='*60}")
print(f"FR-10: Calculating fixed world coordinate chunk boundaries from frame {start_frame}")
print(f"{'='*60}")

# Set to start frame
bpy.context.scene.frame_set(start_frame)

# Create temporary processed object to get bounding box
temp_obj = fluid_surface.copy()
temp_obj.data = fluid_surface.data.copy()
bpy.context.collection.objects.link(temp_obj)
bpy.context.view_layer.objects.active = temp_obj

# Add boolean modifier if available
bool_boundary = bpy.data.objects.get(BOOL_BOUNDARY_NAME)
if bool_boundary:
    bool_mod = temp_obj.modifiers.new(name="Boolean", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = bool_boundary

# Add decimate modifier (using first quality level for boundary calculation)
decimate_mod = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
decimate_mod.decimate_type = 'COLLAPSE'
decimate_mod.ratio = quality_levels[0]

# Apply modifiers
bpy.context.view_layer.objects.active = temp_obj
temp_obj.select_set(True)
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_obj = temp_obj.evaluated_get(depsgraph)
temp_mesh = bpy.data.meshes.new_from_object(eval_obj)
temp_final = bpy.data.objects.new("temp_bounds", temp_mesh)
bpy.context.collection.objects.link(temp_final)

# Get bounds from start frame
bounds = get_mesh_bounds(temp_final)
if not bounds:
    print(f"Error: No geometry in start frame {start_frame}")
    sys.exit(1)

# Determine longest and second-longest axes
size = bounds['size']
axes_sorted = [(size.x, 'x', 0), (size.y, 'y', 1), (size.z, 'z', 2)]
axes_sorted.sort(reverse=True, key=lambda x: x[0])

primary_idx = axes_sorted[0][2]
secondary_idx = axes_sorted[1][2]
primary_axis_name = axes_sorted[0][1]
secondary_axis_name = axes_sorted[1][1]

primary_min = bounds['min'][primary_idx]
primary_max = bounds['max'][primary_idx]
secondary_min = bounds['min'][secondary_idx]
secondary_max = bounds['max'][secondary_idx]

chunk_primary = (primary_max - primary_min) / CHUNKS_X
chunk_secondary = (secondary_max - secondary_min) / CHUNKS_Y

# Store fixed chunk boundaries
fixed_chunk_bounds = {
    'primary_idx': primary_idx,
    'secondary_idx': secondary_idx,
    'primary_min': primary_min,
    'primary_max': primary_max,
    'secondary_min': secondary_min,
    'secondary_max': secondary_max,
    'chunk_primary': chunk_primary,
    'chunk_secondary': chunk_secondary
}

print(f"Chunk grid aligned to {primary_axis_name}-axis (longest) × {secondary_axis_name}-axis (second longest)")
print(f"Primary axis ({primary_axis_name}): {primary_min:.2f} to {primary_max:.2f}, chunk size: {chunk_primary:.2f}")
print(f"Secondary axis ({secondary_axis_name}): {secondary_min:.2f} to {secondary_max:.2f}, chunk size: {chunk_secondary:.2f}")
print(f"These boundaries will be used for ALL frames to ensure consistent chunk positions")

# Cleanup temporary objects
bpy.data.objects.remove(temp_obj)
bpy.data.objects.remove(temp_final)
bpy.data.meshes.remove(temp_mesh)

# Set up seamless blending configuration
print(f"\n{'='*60}")
print(f"Setting up seamless blending")
print(f"{'='*60}")

blend_config = None
reference_offset = get_reference_mesh_offset(reference_mesh_name)
if reference_offset:
    # Use X axis for blending (matching blend_gap_v2.py which works correctly)
    # The meshes tile along X axis, so that's where the seam needs to be blended
    blend_axis_idx = 0  # X axis
    axis_names = ['x', 'y', 'z']

    print(f"Reference mesh '{reference_mesh_name}' found at position: {reference_offset}")
    print(f"Blend axis: {axis_names[blend_axis_idx]} (X axis, matching blend_gap_v2.py)")

    # Calculate seam boundaries for clean edge cutting
    # The seam boundaries define where we cut the mesh to create straight edges
    # They must span exactly the reference offset distance so adjacent meshes meet perfectly
    # IMPORTANT: These must be FIXED values, not dependent on any frame's mesh bounds
    ref_axis_offset = abs(reference_offset[blend_axis_idx])

    # Use fixed seam boundaries that work for all frames
    # For X-axis blending: mesh typically starts around X=0
    # We set seam_min = 5 to be safely inside the minimum bound
    # seam_max = seam_min + reference_offset to ensure perfect tiling
    SEAM_MIN = 5.0  # Fixed value for X-axis (mesh starts around X=0)
    seam_min = SEAM_MIN
    seam_max = seam_min + ref_axis_offset

    seam_boundaries = {
        'min': seam_min,
        'max': seam_max
    }

    print(f"Seam boundaries: min={seam_min:.2f}, max={seam_max:.2f} (span={seam_max - seam_min:.2f})")
    print(f"Reference offset: {ref_axis_offset:.2f}")

    blend_config = {
        'enabled': True,
        'frame_offset': frame_offset,
        'reference_offset': reference_offset,
        'blend_axis_idx': blend_axis_idx,
        'blend_width_percent': BLEND_WIDTH_PERCENT,
        'seam_boundaries': seam_boundaries
    }
    print(f"Seamless edge cutting ENABLED")
else:
    print(f"Warning: Reference mesh '{reference_mesh_name}' not found")
    print(f"Seamless blending DISABLED - edges will not be blended")

# Set up unified grid sampling configuration
unified_config = None
if blend_config:
    print(f"\n{'='*60}")
    print(f"Setting up unified grid sampling")
    print(f"{'='*60}")

    # Evaluate mesh at start frame to get Y bounds
    bpy.context.scene.frame_set(start_frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = fluid_surface.evaluated_get(depsgraph)
    temp_mesh = obj_eval.to_mesh()

    # Use local-space bounds (no matrix_world) because the joined blended mesh
    # has identity matrix — its vertices are in the fluid surface's local space
    ys = [v.co.y for v in temp_mesh.vertices]
    mesh_min_y = min(ys)
    mesh_max_y = max(ys)
    mesh_y_extent = mesh_max_y - mesh_min_y
    obj_eval.to_mesh_clear()

    tiling_x = abs(blend_config['reference_offset'].x)
    grid_start_x = blend_config['seam_boundaries']['min']
    grid_start_y = mesh_min_y

    grid_width = int(tiling_x / grid_step_size)
    grid_height = int(mesh_y_extent / grid_step_size)

    grid_config = {
        'start_x': grid_start_x,
        'start_y': grid_start_y,
        'width': grid_width,
        'height': grid_height,
        'step_size': grid_step_size
    }

    unified_output_dir = os.path.join(output_base_dir, "unified")

    unified_config = {
        'grid_config': grid_config,
        'output_dir': unified_output_dir
    }

    print(f"Grid: {grid_width} x {grid_height} samples, step={grid_step_size}")
    print(f"Grid start: ({grid_start_x:.2f}, {grid_start_y:.2f})")
    print(f"Grid covers: X=[{grid_start_x:.2f}, {grid_start_x + grid_width * grid_step_size:.2f}], Y=[{grid_start_y:.2f}, {grid_start_y + grid_height * grid_step_size:.2f}]")
    print(f"Unified output: {unified_output_dir}")

    # Write metadata once
    write_unified_metadata(unified_output_dir, grid_config, blend_config, start_frame, end_frame, reference_mesh_name)

# Convert skip_existing string to boolean
skip_existing_files = (skip_existing.lower() == 'skip')

# Initialize timing variables
total_frames_to_export = (end_frame - start_frame + 1) * len(quality_levels)
current_frame_index = 0
frame_times = []
overall_start_time = time.time()

# FR-6, FR-7, FR-8: Process each quality level
for quality_idx, quality_ratio in enumerate(quality_levels):
    quality_name = f"ratio_{str(quality_ratio).replace('.', '_')}"
    quality_folder = f"chunks_{quality_name}"
    output_dir = os.path.join(output_base_dir, quality_folder)

    print(f"\n{'-'*60}")
    print(f"Processing quality level {quality_idx + 1}/{len(quality_levels)}: ratio={quality_ratio}")
    print(f"Output directory: {output_dir}")
    print(f"{'-'*60}")

    # FR-6: Process each frame
    for frame in range(start_frame, end_frame + 1):
        frame_start_time = time.time()

        print(f"\nFrame {frame}:")
        export_chunks_for_frame(fluid_surface, frame, quality_ratio, output_dir, CHUNKS_X, CHUNKS_Y, fixed_chunk_bounds, skip_existing_files, blend_config, unified_config)

        # Calculate time for this frame
        frame_duration = time.time() - frame_start_time
        frame_times.append(frame_duration)
        current_frame_index += 1

        # Calculate and display time estimate
        if len(frame_times) > 0:
            avg_time_per_frame = sum(frame_times) / len(frame_times)
            frames_remaining = total_frames_to_export - current_frame_index
            estimated_seconds_remaining = avg_time_per_frame * frames_remaining

            # Format time estimate
            hours = int(estimated_seconds_remaining // 3600)
            minutes = int((estimated_seconds_remaining % 3600) // 60)
            seconds = int(estimated_seconds_remaining % 60)

            elapsed_seconds = time.time() - overall_start_time
            elapsed_hours = int(elapsed_seconds // 3600)
            elapsed_minutes = int((elapsed_seconds % 3600) // 60)
            elapsed_secs = int(elapsed_seconds % 60)

            print(f"  Frame completed in {frame_duration:.1f}s")
            print(f"  Progress: {current_frame_index}/{total_frames_to_export} frames ({100*current_frame_index/total_frames_to_export:.1f}%)")
            print(f"  Elapsed: {elapsed_hours}h {elapsed_minutes}m {elapsed_secs}s")
            print(f"  Estimated time remaining: {hours}h {minutes}m {seconds}s")

print(f"\n{'='*60}")
print(f"EXPORT COMPLETE!")
print(f"{'='*60}")
print(f"Processed {len(quality_levels)} quality levels")
print(f"Processed {end_frame - start_frame + 1} frames per quality level")
print(f"Total chunks per frame: {CHUNKS_X * CHUNKS_Y}")
print(f"Total frames exported: {current_frame_index}")

# Calculate and display total time
total_elapsed = time.time() - overall_start_time
total_hours = int(total_elapsed // 3600)
total_minutes = int((total_elapsed % 3600) // 60)
total_seconds = int(total_elapsed % 60)
print(f"Total time: {total_hours}h {total_minutes}m {total_seconds}s")
print(f"{'='*60}")
