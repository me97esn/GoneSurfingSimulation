"""
Test script for seamless blending between frames 903 and 998.
Run this to verify the overlap blending works before running the full export.

Usage:
  blender breaking_waves_beach_break_2.blend --background --python test_seamless_blend.py

Or open Blender with the file and run this script from the scripting tab.
"""
import bpy
import bmesh
import math
import os
from mathutils import Vector
from mathutils.kdtree import KDTree

# Configuration
FRAME_A = 998  # First frame (will be at origin)
FRAME_B = 903  # Second frame (will be offset to tile)
FLUID_SURFACE_NAME = 'fluid_surface'
REFERENCE_MESH_NAME = '1_0_mesh_903_reference'
DECIMATE_RATIO = 0.03  # Same as export script
OUTPUT_DIR = '/tmp/seamless_test'


def smoothstep(t):
    """Smooth interpolation function (ease-in-out)"""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def get_height_at_position(world_verts, target_pos, blend_axis_idx, search_radius=10.0):
    """Get the approximate height (Z) at a given position by averaging nearby vertices."""
    heights = []
    weights = []
    non_blend_axes = [i for i in range(3) if i != blend_axis_idx]

    for world_pos in world_verts:
        dist_sq = 0
        for axis in non_blend_axes:
            dist_sq += (world_pos[axis] - target_pos[axis])**2
        dist = math.sqrt(dist_sq)

        if dist < search_radius:
            weight = 1.0 / (dist + 0.1)
            heights.append(world_pos.z)
            weights.append(weight)

    if heights:
        total_weight = sum(weights)
        return sum(h * w for h, w in zip(heights, weights)) / total_weight
    return None


def create_mesh_from_frame(fluid_surface, frame, decimate_ratio):
    """Create a decimated mesh from the fluid surface at a specific frame."""
    bpy.context.scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = fluid_surface.evaluated_get(depsgraph)

    # Create mesh from evaluated object
    mesh = bpy.data.meshes.new_from_object(eval_obj)
    obj = bpy.data.objects.new(f"mesh_{frame}", mesh)
    bpy.context.collection.objects.link(obj)

    # Add decimate modifier
    decimate_mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
    decimate_mod.decimate_type = 'COLLAPSE'
    decimate_mod.ratio = decimate_ratio

    # Apply modifier
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_decimated = obj.evaluated_get(depsgraph)
    final_mesh = bpy.data.meshes.new_from_object(eval_decimated)
    final_obj = bpy.data.objects.new(f"decimated_{frame}", final_mesh)
    bpy.context.collection.objects.link(final_obj)

    # Cleanup intermediate object
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(mesh)

    return final_obj


def blend_meshes(mesh_a_obj, mesh_b_obj, blend_axis_idx, blend_width=15.0):
    """
    Blend two meshes - handles both gap and overlap cases.

    Args:
        mesh_a_obj: First mesh object (at origin)
        mesh_b_obj: Second mesh object (offset to tile position)
        blend_axis_idx: Axis to blend along (0=x, 1=y, 2=z)
        blend_width: Width of the blend zone
    """
    OVERLAP_FACTOR = 0.5  # More aggressive - push 50% into other mesh's territory
    HEIGHT_BLEND_STRENGTH = 0.8  # Stronger height blending

    matrix_a = mesh_a_obj.matrix_world
    matrix_b = mesh_b_obj.matrix_world

    # Get world positions
    verts_a_world = [matrix_a @ v.co.copy() for v in mesh_a_obj.data.vertices]
    verts_b_world = [matrix_b @ v.co.copy() for v in mesh_b_obj.data.vertices]

    # Find bounds on blend axis
    axis_vals_a = [v[blend_axis_idx] for v in verts_a_world]
    axis_vals_b = [v[blend_axis_idx] for v in verts_b_world]

    max_a = max(axis_vals_a)
    min_a = min(axis_vals_a)
    max_b = max(axis_vals_b)
    min_b = min(axis_vals_b)

    print(f"  Mesh A bounds on axis {blend_axis_idx}: [{min_a:.2f}, {max_a:.2f}]")
    print(f"  Mesh B bounds on axis {blend_axis_idx}: [{min_b:.2f}, {max_b:.2f}]")

    # Calculate overlap region
    overlap_start = max(min_a, min_b)
    overlap_end = min(max_a, max_b)
    overlap_width = overlap_end - overlap_start

    print(f"  Overlap region: [{overlap_start:.2f}, {overlap_end:.2f}] (width: {overlap_width:.2f})")

    non_blend_axes = [i for i in range(3) if i != blend_axis_idx]

    # Build KD-trees for matching
    kd_b = KDTree(len(verts_b_world))
    for i, v in enumerate(verts_b_world):
        match_pos = Vector((v[non_blend_axes[0]], v[non_blend_axes[1]], 0))
        kd_b.insert(match_pos, i)
    kd_b.balance()

    kd_a = KDTree(len(verts_a_world))
    for i, v in enumerate(verts_a_world):
        match_pos = Vector((v[non_blend_axes[0]], v[non_blend_axes[1]], 0))
        kd_a.insert(match_pos, i)
    kd_a.balance()

    blended_a = 0
    blended_b = 0

    if overlap_width > 0:
        # OVERLAP CASE: Move vertices toward each other in the overlap region
        seam_center = (overlap_start + overlap_end) / 2.0
        print(f"  Handling OVERLAP case (overlap: {overlap_width:.2f})")
        print(f"  Seam center: {seam_center:.2f}")
        print(f"  Using overlap blending - moving vertices toward matching positions")

        # Build KD-trees for matching vertices on non-blend axes
        kd_b = KDTree(len(verts_b_world))
        for i, v in enumerate(verts_b_world):
            match_pos = Vector((v[non_blend_axes[0]], v[non_blend_axes[1]], 0))
            kd_b.insert(match_pos, i)
        kd_b.balance()

        kd_a = KDTree(len(verts_a_world))
        for i, v in enumerate(verts_a_world):
            match_pos = Vector((v[non_blend_axes[0]], v[non_blend_axes[1]], 0))
            kd_a.insert(match_pos, i)
        kd_a.balance()

        # Blend mesh A vertices in overlap - only blend Z heights
        print("  Blending mesh A heights in overlap...")
        for i, vert in enumerate(mesh_a_obj.data.vertices):
            world_pos = verts_a_world[i]
            axis_pos = world_pos[blend_axis_idx]

            if overlap_start <= axis_pos <= overlap_end:
                # Blend factor: 1 at overlap_end (right edge), 0 at overlap_start
                blend_factor = (axis_pos - overlap_start) / overlap_width
                smooth_factor = smoothstep(blend_factor)

                # Get target height from mesh B
                target_height = get_height_at_position(verts_b_world, world_pos, blend_axis_idx, search_radius=15.0)

                if target_height is not None:
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * HEIGHT_BLEND_STRENGTH
                    new_world_pos = world_pos.copy()
                    new_world_pos.z = new_z
                    vert.co = matrix_a.inverted() @ new_world_pos
                    blended_a += 1

        mesh_a_obj.data.update()

        # Blend mesh B vertices in overlap - only blend Z heights
        print("  Blending mesh B heights in overlap...")
        for i, vert in enumerate(mesh_b_obj.data.vertices):
            world_pos = verts_b_world[i]
            axis_pos = world_pos[blend_axis_idx]

            if overlap_start <= axis_pos <= overlap_end:
                # Blend factor: 1 at overlap_start (left edge), 0 at overlap_end
                blend_factor = 1.0 - (axis_pos - overlap_start) / overlap_width
                smooth_factor = smoothstep(blend_factor)

                # Get target height from mesh A
                target_height = get_height_at_position(verts_a_world, world_pos, blend_axis_idx, search_radius=15.0)

                if target_height is not None:
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * HEIGHT_BLEND_STRENGTH
                    new_world_pos = world_pos.copy()
                    new_world_pos.z = new_z
                    vert.co = matrix_b.inverted() @ new_world_pos
                    blended_b += 1

        mesh_b_obj.data.update()

    else:
        # GAP CASE: There's a gap between meshes, use overlap approach to close it
        gap_width = -overlap_width  # Convert to positive
        gap_edge_a = min_a  # A's MIN edge faces the gap
        gap_edge_b = max_b  # B's MAX edge faces the gap
        gap_center = (gap_edge_a + gap_edge_b) / 2.0

        print(f"  Handling GAP case (gap: {gap_width:.2f})")
        print(f"  Gap center: {gap_center:.2f}")

        # Blend mesh A vertices (near MIN edge, facing gap)
        print("  Blending mesh A vertices...")
        for i, vert in enumerate(mesh_a_obj.data.vertices):
            world_pos = verts_a_world[i]
            axis_pos = world_pos[blend_axis_idx]
            dist_from_edge = axis_pos - gap_edge_a

            if 0 <= dist_from_edge <= blend_width:
                blend_factor = 1.0 - (dist_from_edge / blend_width)
                smooth_factor = smoothstep(blend_factor)

                target_height = get_height_at_position(verts_b_world, world_pos, blend_axis_idx, search_radius=10.0)

                if target_height is not None:
                    overlap_target = gap_edge_b - blend_width * OVERLAP_FACTOR
                    new_axis_pos = axis_pos + (overlap_target - axis_pos) * smooth_factor
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * HEIGHT_BLEND_STRENGTH

                    new_world_pos = world_pos.copy()
                    new_world_pos[blend_axis_idx] = new_axis_pos
                    new_world_pos.z = new_z
                    vert.co = matrix_a.inverted() @ new_world_pos
                    blended_a += 1

        mesh_a_obj.data.update()

        # Blend mesh B vertices (near MAX edge, facing gap)
        print("  Blending mesh B vertices...")
        for i, vert in enumerate(mesh_b_obj.data.vertices):
            world_pos = verts_b_world[i]
            axis_pos = world_pos[blend_axis_idx]
            dist_from_edge = gap_edge_b - axis_pos

            if 0 <= dist_from_edge <= blend_width:
                blend_factor = 1.0 - (dist_from_edge / blend_width)
                smooth_factor = smoothstep(blend_factor)

                target_height = get_height_at_position(verts_a_world, world_pos, blend_axis_idx, search_radius=10.0)

                if target_height is not None:
                    overlap_target = gap_edge_a + blend_width * OVERLAP_FACTOR
                    new_axis_pos = axis_pos + (overlap_target - axis_pos) * smooth_factor
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * HEIGHT_BLEND_STRENGTH

                    new_world_pos = world_pos.copy()
                    new_world_pos[blend_axis_idx] = new_axis_pos
                    new_world_pos.z = new_z
                    vert.co = matrix_b.inverted() @ new_world_pos
                    blended_b += 1

        mesh_b_obj.data.update()
        seam_center = gap_center

    print(f"  Blended {blended_a} vertices in mesh A, {blended_b} vertices in mesh B")

    return seam_center, max(overlap_width, blend_width)


def get_mesh_world_bounds(obj):
    """Get the world-space vertex bounds of a mesh object."""
    matrix = obj.matrix_world
    xs, ys, zs = [], [], []
    for v in obj.data.vertices:
        world_pos = matrix @ v.co
        xs.append(world_pos.x)
        ys.append(world_pos.y)
        zs.append(world_pos.z)
    return {
        'x': (min(xs), max(xs)),
        'y': (min(ys), max(ys)),
        'z': (min(zs), max(zs)),
        'center': Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
    }


def main():
    print("="*60)
    print("SEAMLESS BLEND TEST")
    print("="*60)

    # Get fluid surface
    fluid_surface = bpy.data.objects.get(FLUID_SURFACE_NAME)
    if not fluid_surface:
        print(f"ERROR: Fluid surface '{FLUID_SURFACE_NAME}' not found!")
        return

    # Get reference mesh - this shows where the tiled copy should be positioned
    ref_obj = bpy.data.objects.get(REFERENCE_MESH_NAME)
    if not ref_obj:
        print(f"ERROR: Reference mesh '{REFERENCE_MESH_NAME}' not found!")
        return

    # Use reference mesh's OBJECT LOCATION (same as export script)
    # This is the offset to apply to the adjacent mesh for tiling
    reference_offset = ref_obj.location.copy()
    print(f"Reference mesh object location: {reference_offset}")

    # The blend axis is X (like in simple_model_seamless.blend)
    # The reference mesh's X offset determines where to place the tiled mesh
    blend_axis_idx = 0  # X axis
    axis_names = ['x', 'y', 'z']
    ref_axis_offset = reference_offset.x  # Use X offset for positioning
    print(f"Blend axis: {axis_names[blend_axis_idx]} (offset: {ref_axis_offset:.2f})")

    # Create meshes from both frames
    print(f"\nCreating mesh from frame {FRAME_A}...")
    mesh_a = create_mesh_from_frame(fluid_surface, FRAME_A, DECIMATE_RATIO)
    print(f"  Vertices: {len(mesh_a.data.vertices)}, Faces: {len(mesh_a.data.polygons)}")

    print(f"\nCreating mesh from frame {FRAME_B}...")
    mesh_b = create_mesh_from_frame(fluid_surface, FRAME_B, DECIMATE_RATIO)
    print(f"  Vertices: {len(mesh_b.data.vertices)}, Faces: {len(mesh_b.data.polygons)}")

    # Get mesh A (frame 998) world-space bounds
    mesh_a_bounds = get_mesh_world_bounds(mesh_a)
    print(f"\nMesh A (frame {FRAME_A}) vertex bounds:")
    print(f"  X: [{mesh_a_bounds['x'][0]:.2f}, {mesh_a_bounds['x'][1]:.2f}]")
    print(f"  Y: [{mesh_a_bounds['y'][0]:.2f}, {mesh_a_bounds['y'][1]:.2f}]")
    print(f"  Center: {mesh_a_bounds['center']}")

    # Get mesh B (frame 903) world-space bounds before repositioning
    mesh_b_bounds = get_mesh_world_bounds(mesh_b)
    print(f"\nMesh B (frame {FRAME_B}) vertex bounds (before positioning):")
    print(f"  X: [{mesh_b_bounds['x'][0]:.2f}, {mesh_b_bounds['x'][1]:.2f}]")
    print(f"  Y: [{mesh_b_bounds['y'][0]:.2f}, {mesh_b_bounds['y'][1]:.2f}]")
    print(f"  Center: {mesh_b_bounds['center']}")

    # Position mesh B using FULL reference offset (same as export script)
    # The reference mesh shows exactly where the tiled copy should be placed
    mesh_b.location = reference_offset.copy()
    bpy.context.view_layer.objects.active = mesh_b
    mesh_b.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    # Verify new position
    mesh_b_new_bounds = get_mesh_world_bounds(mesh_b)
    print(f"\nMesh B positioned with full reference offset {reference_offset}:")
    print(f"  X: [{mesh_b_new_bounds['x'][0]:.2f}, {mesh_b_new_bounds['x'][1]:.2f}]")
    print(f"  Y: [{mesh_b_new_bounds['y'][0]:.2f}, {mesh_b_new_bounds['y'][1]:.2f}]")
    print(f"  Center: {mesh_b_new_bounds['center']}")

    # Blend the meshes (handles both gap and overlap cases)
    print("\nBlending meshes...")
    seam_center, blend_zone = blend_meshes(mesh_a, mesh_b, blend_axis_idx, blend_width=25.0)  # Wider blend zone

    # Join meshes
    print("\nJoining meshes...")
    bpy.ops.object.select_all(action='DESELECT')
    mesh_a.select_set(True)
    mesh_b.select_set(True)
    bpy.context.view_layer.objects.active = mesh_a
    bpy.ops.object.join()

    joined_obj = bpy.context.active_object
    joined_obj.name = f"seamless_{FRAME_A}_{FRAME_B}"

    # Merge and connect edge vertices at seam
    print("Processing seam vertices...")
    bm = bmesh.new()
    bm.from_mesh(joined_obj.data)
    bm.verts.ensure_lookup_table()

    matrix = joined_obj.matrix_world
    non_blend_axes = [i for i in range(3) if i != blend_axis_idx]

    # Find vertices on the cut edges (very close to seam_center)
    edge_tolerance = 2.0  # Vertices within this distance of seam_center are edge vertices
    edge_verts_positive = []  # From mesh A (Y > seam_center originally)
    edge_verts_negative = []  # From mesh B (Y < seam_center originally)

    for v in bm.verts:
        world_pos = matrix @ v.co
        dist_from_seam = world_pos[blend_axis_idx] - seam_center

        if abs(dist_from_seam) < edge_tolerance:
            if dist_from_seam >= 0:
                edge_verts_positive.append(v)
            else:
                edge_verts_negative.append(v)

    print(f"  Edge vertices from mesh A (positive side): {len(edge_verts_positive)}")
    print(f"  Edge vertices from mesh B (negative side): {len(edge_verts_negative)}")

    # Debug: show Y range of edge vertices
    if edge_verts_positive:
        y_vals_pos = [((matrix @ v.co)[blend_axis_idx]) for v in edge_verts_positive]
        print(f"    Mesh A edge Y range: [{min(y_vals_pos):.2f}, {max(y_vals_pos):.2f}]")
    if edge_verts_negative:
        y_vals_neg = [((matrix @ v.co)[blend_axis_idx]) for v in edge_verts_negative]
        print(f"    Mesh B edge Y range: [{min(y_vals_neg):.2f}, {max(y_vals_neg):.2f}]")

    # Build KD-tree for negative side vertices (matching on non-blend axes)
    kd_negative = KDTree(len(edge_verts_negative))
    for i, v in enumerate(edge_verts_negative):
        world_pos = matrix @ v.co
        match_pos = Vector((world_pos[non_blend_axes[0]], world_pos[non_blend_axes[1]], 0))
        kd_negative.insert(match_pos, i)
    kd_negative.balance()

    # Move positive edge vertices to match negative ones and set both to seam_center
    matched_pairs = 0
    for v_pos in edge_verts_positive:
        world_pos_a = matrix @ v_pos.co
        match_pos = Vector((world_pos_a[non_blend_axes[0]], world_pos_a[non_blend_axes[1]], 0))
        co, idx, dist = kd_negative.find(match_pos)

        if idx is not None and dist < 5.0:  # Match within 5 units on X/Z
            v_neg = edge_verts_negative[idx]
            world_pos_b = matrix @ v_neg.co

            # Average position on non-blend axes, exact seam_center on blend axis
            avg_pos = world_pos_a.copy()
            for axis in non_blend_axes:
                avg_pos[axis] = (world_pos_a[axis] + world_pos_b[axis]) / 2.0
            avg_pos[blend_axis_idx] = seam_center

            # Move both vertices to average position
            local_pos = matrix.inverted() @ avg_pos
            v_pos.co = local_pos
            v_neg.co = local_pos
            matched_pairs += 1

    print(f"  Matched and aligned {matched_pairs} vertex pairs")

    # Now find all vertices near seam and merge
    seam_verts = []
    for v in bm.verts:
        world_pos = matrix @ v.co
        if abs(world_pos[blend_axis_idx] - seam_center) < blend_zone:
            seam_verts.append(v)

    verts_before = len(bm.verts)
    print(f"  Found {len(seam_verts)} vertices near seam for merging")

    bmesh.ops.remove_doubles(bm, verts=seam_verts, dist=1.5)  # Moderate merge distance

    verts_after = len(bm.verts)
    print(f"  Merged {verts_before - verts_after} vertices")

    # Find and fill holes at the seam
    print("  Finding and filling holes...")
    # Identify boundary edges (edges with only one face)
    boundary_edges = [e for e in bm.edges if len(e.link_faces) == 1]
    print(f"    Found {len(boundary_edges)} boundary edges")

    # Filter to edges near the seam
    seam_boundary_edges = []
    for e in boundary_edges:
        edge_center_y = (e.verts[0].co[blend_axis_idx] + e.verts[1].co[blend_axis_idx]) / 2
        if abs(edge_center_y - seam_center) < blend_zone:
            seam_boundary_edges.append(e)

    print(f"    Found {len(seam_boundary_edges)} boundary edges near seam")

    if seam_boundary_edges:
        # Try to fill holes by creating faces from boundary loops
        try:
            # Get boundary verts
            boundary_verts = set()
            for e in seam_boundary_edges:
                boundary_verts.add(e.verts[0])
                boundary_verts.add(e.verts[1])

            # Use holes_fill to close small holes
            bmesh.ops.holes_fill(bm, edges=seam_boundary_edges, sides=6)
            print(f"    Filled holes with up to 6 sides")
        except Exception as ex:
            print(f"    Could not fill holes: {ex}")

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(joined_obj.data)
    bm.free()

    # Enable smooth shading
    for poly in joined_obj.data.polygons:
        poly.use_smooth = True

    joined_obj.data.update()

    print(f"\nFinal mesh: {len(joined_obj.data.vertices)} vertices, {len(joined_obj.data.polygons)} faces")

    # Export to OBJ for inspection
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"seamless_{FRAME_A}_{FRAME_B}.obj")

    bpy.ops.object.select_all(action='DESELECT')
    joined_obj.select_set(True)
    bpy.context.view_layer.objects.active = joined_obj

    bpy.ops.wm.obj_export(
        filepath=output_path,
        export_selected_objects=True,
        export_animation=False,
        forward_axis='X',
        up_axis='Z',
        apply_modifiers=True
    )

    print(f"\nExported to: {output_path}")

    # Also save blend file
    blend_path = os.path.join(OUTPUT_DIR, f"seamless_{FRAME_A}_{FRAME_B}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True)
    print(f"Saved blend file: {blend_path}")

    print("\n" + "="*60)
    print("TEST COMPLETE!")
    print("="*60)
    print(f"\nYou can now inspect the results:")
    print(f"  1. Open {blend_path} in Blender")
    print(f"  2. Import {output_path} into your 3D viewer")
    print(f"\nLook for:")
    print(f"  - No visible gap at the seam")
    print(f"  - Smooth height transition")
    print(f"  - No distortion away from the seam")


if __name__ == "__main__":
    main()
