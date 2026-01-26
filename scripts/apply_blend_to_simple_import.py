"""
Apply seamless blending from blend_gap_v2.py to the meshes in simple_import_test.blend.
No export - just blend and save the blend file for verification.
"""
import bpy
import bmesh
from mathutils import Vector
import math

INPUT_BLEND = "/tmp/simple_import_test.blend"
OUTPUT_BLEND = "/tmp/simple_import_blended.blend"
BLEND_WIDTH = 15.0


def smoothstep(x):
    """Smooth interpolation function (Hermite interpolation)."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def get_height_at_position(mesh_objs, x, y, search_radius=5.0):
    """
    Get the approximate height (Z) at a given X,Y position by averaging nearby vertices.
    """
    heights = []
    weights = []

    for obj in mesh_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_xy = math.sqrt((world_pos.x - x)**2 + (world_pos.y - y)**2)
            if dist_xy < search_radius:
                weight = 1.0 / (dist_xy + 0.1)  # Inverse distance weighting
                heights.append(world_pos.z)
                weights.append(weight)

    if heights:
        total_weight = sum(weights)
        return sum(h * w for h, w in zip(heights, weights)) / total_weight
    return None


def blend_mesh_edges_v2(mesh_998_objs, mesh_903_objs, blend_width=15.0):
    """
    Blend the edges using height interpolation.
    """
    # Find the gap boundaries
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

    gap_width = min_x_903 - max_x_998
    gap_center = (max_x_998 + min_x_903) / 2.0

    print(f"Gap analysis:")
    print(f"  998 max X: {max_x_998:.4f}")
    print(f"  903 min X: {min_x_903:.4f}")
    print(f"  Gap width: {gap_width:.4f}")
    print(f"  Gap center: {gap_center:.4f}")
    print(f"  Blend width: {blend_width:.4f}")

    # For 998 meshes: adjust vertices near the right edge
    # Move them to gap_center on X, and interpolate Z based on position
    print("\nBlending 998 vertices...")
    modified_998 = 0

    for obj in mesh_998_objs:
        matrix = obj.matrix_world
        matrix_inv = matrix.inverted()

        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_from_edge = max_x_998 - world_pos.x

            if dist_from_edge < blend_width:
                # Blend factor: 1 at edge, 0 at blend_width
                blend_factor = 1.0 - (dist_from_edge / blend_width)
                smooth_factor = smoothstep(blend_factor)

                # Get the target height from the 903 mesh at this Y position
                target_height = get_height_at_position(mesh_903_objs, min_x_903, world_pos.y, search_radius=10.0)

                if target_height is not None:
                    # Make meshes OVERLAP by moving past gap_center
                    # At edge: move to min_x_903 (into the other mesh)
                    # This creates overlap instead of just meeting
                    overlap_target_x = min_x_903 + blend_width * 0.3  # Move into 903 territory
                    new_x = world_pos.x + (overlap_target_x - world_pos.x) * smooth_factor
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * 0.7  # Strong height blend

                    new_world_pos = Vector((new_x, world_pos.y, new_z))
                    v.co = matrix_inv @ new_world_pos
                    modified_998 += 1

        obj.data.update()

    print(f"  Modified {modified_998} vertices")

    # For 903 meshes: adjust vertices near the left edge
    print("Blending 903 vertices...")
    modified_903 = 0

    for obj in mesh_903_objs:
        matrix = obj.matrix_world
        matrix_inv = matrix.inverted()

        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_from_edge = world_pos.x - min_x_903

            if dist_from_edge < blend_width:
                blend_factor = 1.0 - (dist_from_edge / blend_width)
                smooth_factor = smoothstep(blend_factor)

                target_height = get_height_at_position(mesh_998_objs, max_x_998, world_pos.y, search_radius=10.0)

                if target_height is not None:
                    # Move into 998 territory
                    overlap_target_x = max_x_998 - blend_width * 0.3
                    new_x = world_pos.x + (overlap_target_x - world_pos.x) * smooth_factor
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * 0.7

                    new_world_pos = Vector((new_x, world_pos.y, new_z))
                    v.co = matrix_inv @ new_world_pos
                    modified_903 += 1

        obj.data.update()

    print(f"  Modified {modified_903} vertices")

    # Verify
    new_max_x_998 = -float('inf')
    new_min_x_903 = float('inf')

    for obj in mesh_998_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_x = (matrix @ v.co).x
            new_max_x_998 = max(new_max_x_998, world_x)

    for obj in mesh_903_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_x = (matrix @ v.co).x
            new_min_x_903 = min(new_min_x_903, world_x)

    print(f"\nAfter blending:")
    print(f"  998 max X: {new_max_x_998:.4f}")
    print(f"  903 min X: {new_min_x_903:.4f}")
    print(f"  New gap: {new_min_x_903 - new_max_x_998:.4f}")

    # Join all meshes
    print("\nJoining meshes...")
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_998_objs + mesh_903_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_998_objs[0]
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

    # Recalculate normals
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(joined_obj.data)
    bm.free()

    # Enable smooth shading
    for poly in joined_obj.data.polygons:
        poly.use_smooth = True

    joined_obj.data.update()
    print(f"  Final mesh: {len(joined_obj.data.vertices)} vertices")


def main():
    # Open the blend file
    print(f"Opening: {INPUT_BLEND}")
    bpy.ops.wm.open_mainfile(filepath=INPUT_BLEND)

    # Find meshes by frame number in name
    mesh_998_objs = []
    mesh_903_objs = []

    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if '998' in obj.name:
                mesh_998_objs.append(obj)
            elif '903' in obj.name:
                mesh_903_objs.append(obj)

    print(f"Found {len(mesh_998_objs)} meshes from 998")
    print(f"Found {len(mesh_903_objs)} meshes from 903")

    if not mesh_998_objs or not mesh_903_objs:
        print("ERROR: Could not find meshes for both frames!")
        return

    # Apply blending
    blend_mesh_edges_v2(mesh_998_objs, mesh_903_objs, blend_width=BLEND_WIDTH)

    # Save
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
    print(f"\nSaved: {OUTPUT_BLEND}")
    print("Blending complete!")


if __name__ == "__main__":
    main()
