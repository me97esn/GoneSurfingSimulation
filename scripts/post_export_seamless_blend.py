"""
Post-export script to create seamless blended meshes from already-exported OBJ files.

This script replicates what was done manually in simple_model_seamless.blend:
1. Import OBJ chunks for frame X at origin
2. Import OBJ chunks for frame X + frame_offset at tiling position
3. Apply the same blend_gap_v2.py logic (which already works)
4. Trim result to ≤5% wider than original mesh
5. Export the blended result

Usage:
    blender --background --python post_export_seamless_blend.py -- \
        --input-dir /path/to/exported/objs \
        --output-dir /path/to/output \
        --start-frame 886 \
        --end-frame 1078 \
        --frame-offset -95 \
        --tiling-x 123.4486 \
        --tiling-y -59.6493
"""
import bpy
import bmesh
from mathutils import Vector
import math
import os
import sys
import argparse
import glob


# Blending parameters - SAME as blend_gap_v2.py
BLEND_WIDTH = 15.0
MAX_WIDTH_INCREASE = 0.05  # 5% maximum width increase


def smoothstep(x):
    """Smooth interpolation function (Hermite interpolation)."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def get_height_at_position(mesh_objs, x, y, search_radius=5.0):
    """Get approximate height (Z) at X,Y position by averaging nearby vertices."""
    heights = []
    weights = []

    for obj in mesh_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_xy = math.sqrt((world_pos.x - x)**2 + (world_pos.y - y)**2)
            if dist_xy < search_radius:
                weight = 1.0 / (dist_xy + 0.1)
                heights.append(world_pos.z)
                weights.append(weight)

    if heights:
        total_weight = sum(weights)
        return sum(h * w for h, w in zip(heights, weights)) / total_weight
    return None


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def import_frame_meshes(input_dir, frame, location=(0, 0, 0), name_suffix=""):
    """
    Import all OBJ chunks for a specific frame.
    Returns list of imported mesh objects.
    """
    pattern = os.path.join(input_dir, f"*_mesh_{frame}.obj")
    obj_files = sorted(glob.glob(pattern))

    imported_objs = []
    for obj_file in obj_files:
        # Import with axis settings matching Blender defaults
        bpy.ops.wm.obj_import(filepath=obj_file)
        # OBJ files may contain multiple objects - capture ALL newly imported ones
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                # Rename to include suffix for identification
                if name_suffix:
                    obj.name = f"{obj.name}_{name_suffix}"
                # Reset any rotation from OBJ importer and apply Z rotation of 90°
                # to match simple_model_seamless.blend orientation
                # OBJ importer adds X rotation for axis conversion - we must remove it
                obj.rotation_euler.x = 0
                obj.rotation_euler.y = 0
                obj.rotation_euler.z = 1.5708  # 90 degrees
                # Set location
                obj.location = Vector(location)
                imported_objs.append(obj)

    # Apply ALL transforms so vertex world coordinates are correct
    bpy.ops.object.select_all(action='DESELECT')
    for obj in imported_objs:
        obj.select_set(True)
    if imported_objs:
        bpy.context.view_layer.objects.active = imported_objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.context.view_layer.update()
    return imported_objs


def get_mesh_bounds_x(mesh_objs):
    """Get the X bounds of mesh objects in world coordinates."""
    min_x = float('inf')
    max_x = -float('inf')

    for obj in mesh_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_x = (matrix @ v.co).x
            min_x = min(min_x, world_x)
            max_x = max(max_x, world_x)

    return min_x, max_x


def blend_mesh_edges_v2(primary_objs, adjacent_objs, blend_width=BLEND_WIDTH):
    """
    Blend the edges using height interpolation.
    Handles both gap and large overlap scenarios.
    """
    # Find the boundaries
    max_x_primary = -float('inf')
    min_x_adjacent = float('inf')

    for obj in primary_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_x = (matrix @ v.co).x
            max_x_primary = max(max_x_primary, world_x)

    for obj in adjacent_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_x = (matrix @ v.co).x
            min_x_adjacent = min(min_x_adjacent, world_x)

    gap_width = min_x_adjacent - max_x_primary
    gap_center = (max_x_primary + min_x_adjacent) / 2.0

    print(f"Gap analysis:")
    print(f"  Primary max X: {max_x_primary:.4f}")
    print(f"  Adjacent min X: {min_x_adjacent:.4f}")
    print(f"  Gap width: {gap_width:.4f}")
    print(f"  Gap center: {gap_center:.4f}")
    print(f"  Blend width: {blend_width:.4f}")

    # Determine if we have a gap or overlap
    is_overlap = gap_width < 0

    if is_overlap:
        # For large overlaps, use the overlap region for blending
        # Blend vertices in the overlap region based on X position
        overlap_start = min_x_adjacent
        overlap_end = max_x_primary
        overlap_center = (overlap_start + overlap_end) / 2.0
        print(f"  OVERLAP mode: blending in region X=[{overlap_start:.2f}, {overlap_end:.2f}]")

    # For primary meshes: adjust vertices near the right edge
    print("\nBlending primary vertices...")
    modified_primary = 0

    for obj in primary_objs:
        matrix = obj.matrix_world
        matrix_inv = matrix.inverted()

        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_from_edge = max_x_primary - world_pos.x

            if dist_from_edge < blend_width:
                blend_factor = 1.0 - (dist_from_edge / blend_width)
                smooth_factor = smoothstep(blend_factor)

                # For overlap: search at the vertex's X position, not at min_x_adjacent
                if is_overlap:
                    search_x = world_pos.x
                else:
                    search_x = min_x_adjacent

                target_height = get_height_at_position(adjacent_objs, search_x, world_pos.y, search_radius=15.0)

                if target_height is not None:
                    if is_overlap:
                        # In overlap: blend height only, don't move X
                        new_x = world_pos.x
                    else:
                        overlap_target_x = min_x_adjacent + blend_width * 0.3
                        new_x = world_pos.x + (overlap_target_x - world_pos.x) * smooth_factor
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * 0.7

                    new_world_pos = Vector((new_x, world_pos.y, new_z))
                    v.co = matrix_inv @ new_world_pos
                    modified_primary += 1

        obj.data.update()

    print(f"  Modified {modified_primary} vertices")

    # For adjacent meshes: adjust vertices near the left edge
    print("Blending adjacent vertices...")
    modified_adjacent = 0

    for obj in adjacent_objs:
        matrix = obj.matrix_world
        matrix_inv = matrix.inverted()

        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_from_edge = world_pos.x - min_x_adjacent

            if dist_from_edge < blend_width:
                blend_factor = 1.0 - (dist_from_edge / blend_width)
                smooth_factor = smoothstep(blend_factor)

                # For overlap: search at the vertex's X position
                if is_overlap:
                    search_x = world_pos.x
                else:
                    search_x = max_x_primary

                target_height = get_height_at_position(primary_objs, search_x, world_pos.y, search_radius=15.0)

                if target_height is not None:
                    if is_overlap:
                        # In overlap: blend height only
                        new_x = world_pos.x
                    else:
                        overlap_target_x = max_x_primary - blend_width * 0.3
                        new_x = world_pos.x + (overlap_target_x - world_pos.x) * smooth_factor
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * 0.7

                    new_world_pos = Vector((new_x, world_pos.y, new_z))
                    v.co = matrix_inv @ new_world_pos
                    modified_adjacent += 1

        obj.data.update()

    print(f"  Modified {modified_adjacent} vertices")

    return gap_center


def join_and_merge(primary_objs, adjacent_objs, gap_center):
    """Join all meshes and merge vertices at seam."""
    print("\nJoining meshes...")
    bpy.ops.object.select_all(action='DESELECT')
    for obj in primary_objs + adjacent_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = primary_objs[0]
    bpy.ops.object.join()

    joined_obj = bpy.context.active_object
    joined_obj.name = "seamless_wave"

    # Merge close vertices at seam
    print("Merging close vertices at seam...")
    bm = bmesh.new()
    bm.from_mesh(joined_obj.data)

    matrix = joined_obj.matrix_world
    seam_verts = []
    for v in bm.verts:
        world_x = (matrix @ v.co).x
        if abs(world_x - gap_center) < 3.0:
            seam_verts.append(v)

    verts_before = len(bm.verts)
    print(f"  Found {len(seam_verts)} vertices near seam")
    bmesh.ops.remove_doubles(bm, verts=seam_verts, dist=0.3)
    verts_after = len(bm.verts)
    print(f"  Merged {verts_before - verts_after} vertices")

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(joined_obj.data)
    bm.free()

    for poly in joined_obj.data.polygons:
        poly.use_smooth = True

    joined_obj.data.update()
    print(f"  Final mesh: {len(joined_obj.data.vertices)} vertices")

    return joined_obj


def trim_mesh_width(mesh_obj, original_min_x, original_max_x, max_increase=MAX_WIDTH_INCREASE):
    """Trim the mesh so it's no more than max_increase wider than original."""
    original_width = original_max_x - original_min_x
    allowed_extra = original_width * max_increase

    trim_min_x = original_min_x - allowed_extra / 2
    trim_max_x = original_max_x + allowed_extra / 2

    print(f"\nTrimming mesh to fit bounds:")
    print(f"  Original width: {original_width:.4f}")
    print(f"  Allowed extra (5%): {allowed_extra:.4f}")
    print(f"  Trim bounds: [{trim_min_x:.4f}, {trim_max_x:.4f}]")

    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)

    matrix = mesh_obj.matrix_world
    verts_to_delete = []

    for v in bm.verts:
        world_x = (matrix @ v.co).x
        if world_x < trim_min_x or world_x > trim_max_x:
            verts_to_delete.append(v)

    verts_before = len(bm.verts)
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
    verts_after = len(bm.verts)
    print(f"  Removed {verts_before - verts_after} vertices outside bounds")

    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(mesh_obj.data)
    bm.free()

    mesh_obj.data.update()
    print(f"  Final trimmed mesh: {len(mesh_obj.data.vertices)} vertices")

    return mesh_obj


def process_frame(input_dir, output_dir, frame, frame_offset, tiling_pos,
                  start_frame, end_frame):
    """Process a single frame: import, blend, trim, and export."""
    print(f"\n{'='*60}")
    print(f"Processing frame {frame}")
    print(f"{'='*60}")

    # Calculate adjacent frame with wrapping
    adjacent_frame = frame + frame_offset
    if adjacent_frame > end_frame:
        adjacent_frame = start_frame + (adjacent_frame - end_frame - 1)
    elif adjacent_frame < start_frame:
        adjacent_frame = end_frame - (start_frame - adjacent_frame - 1)

    print(f"Primary frame: {frame}")
    print(f"Adjacent frame: {adjacent_frame} (offset: {frame_offset})")

    clear_scene()

    # Import primary frame meshes at origin
    print(f"\nImporting frame {frame} meshes at origin...")
    primary_objs = import_frame_meshes(input_dir, frame, location=(0, 0, 0), name_suffix="primary")
    if not primary_objs:
        print(f"ERROR: No meshes found for frame {frame}")
        return False
    print(f"  Imported {len(primary_objs)} meshes")

    # Get original bounds before importing adjacent
    original_min_x, original_max_x = get_mesh_bounds_x(primary_objs)
    print(f"  Original bounds: X=[{original_min_x:.4f}, {original_max_x:.4f}]")

    # Import adjacent frame meshes at tiling position (same as simple_model_seamless.blend)
    print(f"\nImporting frame {adjacent_frame} meshes at position {tiling_pos}...")
    adjacent_objs = import_frame_meshes(input_dir, adjacent_frame, location=tiling_pos, name_suffix="adjacent")
    if not adjacent_objs:
        print(f"ERROR: No meshes found for frame {adjacent_frame}")
        return False
    print(f"  Imported {len(adjacent_objs)} meshes")

    # Apply seamless blending (same as blend_gap_v2.py)
    gap_center = blend_mesh_edges_v2(primary_objs, adjacent_objs)

    # Join and merge
    joined_obj = join_and_merge(primary_objs, adjacent_objs, gap_center)

    # Trim to original size + 5%
    trimmed_obj = trim_mesh_width(joined_obj, original_min_x, original_max_x)

    # Reverse the 90° Z rotation before export so output matches original OBJ orientation
    # We applied +90° Z rotation during import for blending, now reverse it
    trimmed_obj.rotation_euler.z = -1.5708  # -90 degrees
    bpy.ops.object.select_all(action='DESELECT')
    trimmed_obj.select_set(True)
    bpy.context.view_layer.objects.active = trimmed_obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Export
    output_path = os.path.join(output_dir, f"seamless_mesh_{frame}.obj")

    bpy.ops.wm.obj_export(
        filepath=output_path,
        export_selected_objects=True,
        export_materials=False,
        export_uv=False,
        export_normals=True,
        forward_axis='Y',
        up_axis='Z'
    )

    print(f"\nExported: {output_path}")
    return True


def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description='Post-export seamless blending')
    parser.add_argument('--input-dir', required=True, help='Input directory with exported OBJs')
    parser.add_argument('--output-dir', required=True, help='Output directory for seamless meshes')
    parser.add_argument('--start-frame', type=int, required=True, help='Start frame number')
    parser.add_argument('--end-frame', type=int, required=True, help='End frame number')
    parser.add_argument('--frame-offset', type=int, required=True, help='Frame offset for tiling')
    parser.add_argument('--tiling-x', type=float, required=True, help='X position for tiling')
    parser.add_argument('--tiling-y', type=float, default=0.0, help='Y position for tiling')
    parser.add_argument('--tiling-z', type=float, default=0.0, help='Z position for tiling')
    parser.add_argument('--single-frame', type=int, help='Process only this single frame (for testing)')

    args = parser.parse_args(argv)

    os.makedirs(args.output_dir, exist_ok=True)

    tiling_pos = (args.tiling_x, args.tiling_y, args.tiling_z)

    print(f"Post-Export Seamless Blend")
    print(f"==========================")
    print(f"Input dir: {args.input_dir}")
    print(f"Output dir: {args.output_dir}")
    print(f"Frame range: {args.start_frame} - {args.end_frame}")
    print(f"Frame offset: {args.frame_offset}")
    print(f"Tiling position: {tiling_pos}")

    if args.single_frame is not None:
        frames = [args.single_frame]
    else:
        frames = range(args.start_frame, args.end_frame + 1)

    success_count = 0
    fail_count = 0

    for frame in frames:
        try:
            if process_frame(
                args.input_dir, args.output_dir, frame,
                args.frame_offset, tiling_pos,
                args.start_frame, args.end_frame
            ):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"ERROR processing frame {frame}: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
