"""
Blend, trim, and export meshes while preserving the original file structure.
- 0_0_mesh_998.obj contains chunk_0_0_998 and chunk_2_0_998
- 1_0_mesh_998.obj contains chunk_1_0_998
"""
import bpy
import bmesh
from mathutils import Vector
import math
import os

INPUT_BLEND = "/tmp/simple_import_test.blend"
OUTPUT_DIR = "/tmp/seamless_chunks"

# Original frame 998 bounds
ORIGINAL_998_MIN_X = 0.32
ORIGINAL_998_MAX_X = 122.70
EXTRA_WIDTH_PERCENT = 0.07  # 7%

BLEND_WIDTH = 15.0


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


def blend_mesh_edges(mesh_998_objs, mesh_903_objs, blend_width=15.0):
    """Blend edges without joining meshes."""
    # Find gap boundaries
    max_x_998 = -float('inf')
    min_x_903 = float('inf')

    for obj in mesh_998_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_x = (matrix @ v.co).x
            max_x_998 = max(max_x_998, world_x)

    for obj in mesh_903_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_x = (matrix @ v.co).x
            min_x_903 = min(min_x_903, world_x)

    gap_center = (max_x_998 + min_x_903) / 2.0
    print(f"Gap analysis: 998 max X={max_x_998:.2f}, 903 min X={min_x_903:.2f}")

    # Blend 998 vertices near right edge
    print("Blending 998 vertices...")
    modified = 0
    for obj in mesh_998_objs:
        matrix = obj.matrix_world
        matrix_inv = matrix.inverted()

        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_from_edge = max_x_998 - world_pos.x

            if dist_from_edge < blend_width:
                blend_factor = 1.0 - (dist_from_edge / blend_width)
                smooth_factor = smoothstep(blend_factor)

                target_height = get_height_at_position(mesh_903_objs, min_x_903, world_pos.y, search_radius=10.0)

                if target_height is not None:
                    overlap_target_x = min_x_903 + blend_width * 0.3
                    new_x = world_pos.x + (overlap_target_x - world_pos.x) * smooth_factor
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * 0.7

                    new_world_pos = Vector((new_x, world_pos.y, new_z))
                    v.co = matrix_inv @ new_world_pos
                    modified += 1

        obj.data.update()

    print(f"  Modified {modified} vertices in 998 meshes")


def trim_mesh(obj, min_x, max_x):
    """Trim a single mesh to X bounds."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    matrix = obj.matrix_world

    verts_to_delete = []
    for v in bm.verts:
        world_x = (matrix @ v.co).x
        if world_x < min_x or world_x > max_x:
            verts_to_delete.append(v)

    if verts_to_delete:
        bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    return len(verts_to_delete)


def export_obj_with_objects(filepath, objects):
    """Export specific objects to OBJ file."""
    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')

    # Select only these objects
    for obj in objects:
        obj.select_set(True)

    # Set first as active
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
    print("Opening blend file...")
    bpy.ops.wm.open_mainfile(filepath=INPUT_BLEND)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Find all mesh objects
    mesh_998_objs = []
    mesh_903_objs = []

    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if '998' in obj.name:
                mesh_998_objs.append(obj)
                print(f"  Found 998 mesh: {obj.name}")
            elif '903' in obj.name:
                mesh_903_objs.append(obj)
                print(f"  Found 903 mesh: {obj.name}")

    print(f"\nFound {len(mesh_998_objs)} meshes from 998, {len(mesh_903_objs)} from 903")

    # Apply blending (only modifies 998 meshes at the edge)
    print("\nApplying blending...")
    blend_mesh_edges(mesh_998_objs, mesh_903_objs, blend_width=BLEND_WIDTH)

    # Calculate trim bounds
    original_width = ORIGINAL_998_MAX_X - ORIGINAL_998_MIN_X
    extra_width = original_width * EXTRA_WIDTH_PERCENT
    trim_min_x = ORIGINAL_998_MIN_X
    trim_max_x = ORIGINAL_998_MAX_X + extra_width

    print(f"\nTrimming to X bounds: [{trim_min_x:.2f}, {trim_max_x:.2f}]")

    # Trim each 998 mesh
    for obj in mesh_998_objs:
        verts_deleted = trim_mesh(obj, trim_min_x, trim_max_x)
        print(f"  {obj.name}: deleted {verts_deleted} vertices")

    # Group meshes by original file structure
    # chunk_0_0_998 and chunk_2_0_998 go in 0_0_mesh_998.obj
    # chunk_1_0_998 goes in 1_0_mesh_998.obj
    file_groups = {
        '0_0': [],
        '1_0': []
    }

    for obj in mesh_998_objs:
        # Extract chunk coordinates from name (e.g., "chunk_0_0_998" -> "0_0")
        name = obj.name
        if 'chunk_0_0' in name or 'chunk_2_0' in name:
            file_groups['0_0'].append(obj)
        elif 'chunk_1_0' in name:
            file_groups['1_0'].append(obj)
        else:
            # Fallback: try to parse from mesh data name
            print(f"  Warning: Could not classify {name}, adding to 0_0")
            file_groups['0_0'].append(obj)

    # Export each group
    print("\nExporting...")
    for prefix, objs in file_groups.items():
        if objs:
            output_path = os.path.join(OUTPUT_DIR, f"{prefix}_mesh_998.obj")
            print(f"  {output_path}: {[o.name for o in objs]}")
            export_obj_with_objects(output_path, objs)

    print("\nDone! Files exported to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
