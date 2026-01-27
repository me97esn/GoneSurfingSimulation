"""
Same as blend_trim_export_separate.py but for frame 903.
Frame 903 is at origin, frame 998 is the adjacent frame at the tiling offset.
"""
import bpy
import bmesh
from mathutils import Vector
import math
import os
import glob

EXPORT_DIR = "/hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_03"
OUTPUT_DIR = "/tmp/seamless_chunks_903"
OUTPUT_BLEND = "/tmp/simple_import_test_903.blend"

BLEND_WIDTH = 15.0
EXTRA_WIDTH_PERCENT = 0.07  # 7%


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def get_height_at_position(mesh_objs, x, y, search_radius=5.0):
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
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def import_frame(frame, location, z_rotation):
    pattern = os.path.join(EXPORT_DIR, f"*_mesh_{frame}.obj")
    obj_files = sorted(glob.glob(pattern))
    imported = []
    for obj_file in obj_files:
        bpy.ops.wm.obj_import(filepath=obj_file)
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                obj.rotation_euler.x = 0
                obj.rotation_euler.y = 0
                obj.rotation_euler.z = z_rotation
                obj.location = location
                imported.append(obj)
    return imported


def blend_mesh_edges(primary_objs, adjacent_objs, blend_width=15.0):
    max_x_primary = -float('inf')
    min_x_adjacent = float('inf')

    for obj in primary_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            max_x_primary = max(max_x_primary, (matrix @ v.co).x)

    for obj in adjacent_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            min_x_adjacent = min(min_x_adjacent, (matrix @ v.co).x)

    print(f"Gap analysis: primary max X={max_x_primary:.2f}, adjacent min X={min_x_adjacent:.2f}")

    modified = 0
    for obj in primary_objs:
        matrix = obj.matrix_world
        matrix_inv = matrix.inverted()
        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_from_edge = max_x_primary - world_pos.x
            if dist_from_edge < blend_width:
                blend_factor = 1.0 - (dist_from_edge / blend_width)
                smooth_factor = smoothstep(blend_factor)
                target_height = get_height_at_position(adjacent_objs, min_x_adjacent, world_pos.y, search_radius=10.0)
                if target_height is not None:
                    overlap_target_x = min_x_adjacent + blend_width * 0.3
                    new_x = world_pos.x + (overlap_target_x - world_pos.x) * smooth_factor
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * 0.7
                    v.co = matrix_inv @ Vector((new_x, world_pos.y, new_z))
                    modified += 1
        obj.data.update()
    print(f"  Modified {modified} vertices in primary meshes")


def trim_mesh(obj, min_x, max_x):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    matrix = obj.matrix_world
    verts_to_delete = [v for v in bm.verts if (matrix @ v.co).x < min_x or (matrix @ v.co).x > max_x]
    if verts_to_delete:
        bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return len(verts_to_delete)


def export_obj_with_objects(filepath, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.wm.obj_export(
        filepath=filepath,
        export_selected_objects=True,
        export_materials=False,
        export_uv=False,
        export_normals=True,
        forward_axis='Y',
        up_axis='Z'
    )


def main():
    clear_scene()

    # Frame 903 at origin, frame 998 as adjacent at tiling offset
    print("Importing frame 903 at origin...")
    objs_903 = import_frame(903, (0, 0, 0), 1.5708)

    print("Importing frame 998 at tiling offset...")
    objs_998 = import_frame(998, (123.4486, -59.6493, 0), 1.5708)

    print(f"\nFound {len(objs_903)} meshes for 903, {len(objs_998)} for 998")

    # Get 903 X bounds before blending
    all_xs = []
    for obj in objs_903:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            all_xs.append((matrix @ v.co).x)
    original_min_x = min(all_xs)
    original_max_x = max(all_xs)
    print(f"903 original X bounds: [{original_min_x:.2f}, {original_max_x:.2f}]")

    # Blend 903 edges toward 998
    print("\nApplying blending...")
    blend_mesh_edges(objs_903, objs_998, blend_width=BLEND_WIDTH)

    # Calculate trim bounds
    original_width = original_max_x - original_min_x
    extra_width = original_width * EXTRA_WIDTH_PERCENT
    trim_min_x = original_min_x
    trim_max_x = original_max_x + extra_width
    print(f"Trimming to X bounds: [{trim_min_x:.2f}, {trim_max_x:.2f}]")

    # Trim each 903 mesh
    for obj in objs_903:
        verts_deleted = trim_mesh(obj, trim_min_x, trim_max_x)
        print(f"  {obj.name}: deleted {verts_deleted} vertices")

    # Group by original file structure
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    file_groups = {'0_0': [], '1_0': []}
    for obj in objs_903:
        name = obj.name
        if 'chunk_0_0' in name or 'chunk_2_0' in name:
            file_groups['0_0'].append(obj)
        elif 'chunk_1_0' in name:
            file_groups['1_0'].append(obj)
        else:
            print(f"  Warning: Could not classify {name}, adding to 0_0")
            file_groups['0_0'].append(obj)

    # Export
    print("\nExporting...")
    for prefix, objs in file_groups.items():
        if objs:
            output_path = os.path.join(OUTPUT_DIR, f"{prefix}_mesh_903.obj")
            print(f"  {output_path}: {[o.name for o in objs]}")
            export_obj_with_objects(output_path, objs)

    print("\nDone! Files exported to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
