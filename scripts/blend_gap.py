"""
Script to blend the gap between two sets of meshes for seamless tiling.
Works on the simple_model_seamless.blend file.
"""
import bpy
import bmesh
from mathutils import Vector
from mathutils.kdtree import KDTree


def smoothstep(x):
    """Smooth interpolation function (Hermite interpolation)."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def blend_mesh_edges(mesh_998_objs, mesh_903_objs, blend_width=10.0):
    """
    Blend the edges of two sets of meshes to close the gap.

    Args:
        mesh_998_objs: List of mesh objects from frame 998 (left side, lower X)
        mesh_903_objs: List of mesh objects from frame 903 (right side, higher X)
        blend_width: Width of the blend zone on each side of the gap
    """
    # Find the gap boundaries
    # 998 meshes end at their max X, 903 meshes start at their min X
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

    # Collect all vertices from both sides with their world positions
    # We'll use Y,Z for matching (the non-gap axes)

    # Build KD-tree for 903 edge vertices (for finding matches from 998 side)
    verts_903_edge = []  # (obj, vert_index, world_pos)
    for obj in mesh_903_objs:
        matrix = obj.matrix_world
        for i, v in enumerate(obj.data.vertices):
            world_pos = matrix @ v.co
            # Only include vertices near the gap edge (within blend_width)
            if world_pos.x <= min_x_903 + blend_width:
                verts_903_edge.append((obj, i, world_pos.copy()))

    # Build KD-tree for 998 edge vertices
    verts_998_edge = []
    for obj in mesh_998_objs:
        matrix = obj.matrix_world
        for i, v in enumerate(obj.data.vertices):
            world_pos = matrix @ v.co
            if world_pos.x >= max_x_998 - blend_width:
                verts_998_edge.append((obj, i, world_pos.copy()))

    print(f"  998 edge vertices: {len(verts_998_edge)}")
    print(f"  903 edge vertices: {len(verts_903_edge)}")

    # Build KD-tree for 903 vertices (matching on Y,Z)
    kd_903 = KDTree(len(verts_903_edge))
    for i, (obj, vi, world_pos) in enumerate(verts_903_edge):
        # Match based on Y and Z only
        match_pos = Vector((0, world_pos.y, world_pos.z))
        kd_903.insert(match_pos, i)
    kd_903.balance()

    # Build KD-tree for 998 vertices
    kd_998 = KDTree(len(verts_998_edge))
    for i, (obj, vi, world_pos) in enumerate(verts_998_edge):
        match_pos = Vector((0, world_pos.y, world_pos.z))
        kd_998.insert(match_pos, i)
    kd_998.balance()

    # Track which vertices we've modified
    modified_998 = set()
    modified_903 = set()

    # Blend 998 vertices toward gap center
    print("Blending 998 vertices...")
    for obj, vi, world_pos in verts_998_edge:
        # Calculate distance from gap edge
        dist_from_edge = max_x_998 - world_pos.x

        # Blend factor: 1 at edge (x = max_x_998), 0 at blend_width away
        if dist_from_edge <= blend_width:
            blend_factor = 1.0 - (dist_from_edge / blend_width)
            smooth_factor = smoothstep(blend_factor)

            # Find matching vertex on 903 side
            match_pos = Vector((0, world_pos.y, world_pos.z))
            co, idx, dist = kd_903.find(match_pos)

            if idx is not None and dist < 5.0:  # Only match if reasonably close
                target_obj, target_vi, target_world_pos = verts_903_edge[idx]

                # Calculate meeting point at gap center
                # The new position should be at gap_center on X, blending Y and Z
                meeting_point = Vector((
                    gap_center,
                    (world_pos.y + target_world_pos.y) / 2.0,
                    (world_pos.z + target_world_pos.z) / 2.0
                ))

                # At edge (blend_factor=1): move fully to meeting point
                # Away from edge: gradual transition
                new_world_pos = world_pos.lerp(meeting_point, smooth_factor)

                # Convert back to local coordinates
                matrix_inv = obj.matrix_world.inverted()
                obj.data.vertices[vi].co = matrix_inv @ new_world_pos
                modified_998.add((obj.name, vi))

    # Update 998 meshes
    for obj in mesh_998_objs:
        obj.data.update()

    # Blend 903 vertices toward gap center
    print("Blending 903 vertices...")
    for obj, vi, world_pos in verts_903_edge:
        dist_from_edge = world_pos.x - min_x_903

        if dist_from_edge <= blend_width:
            blend_factor = 1.0 - (dist_from_edge / blend_width)
            smooth_factor = smoothstep(blend_factor)

            # Find matching vertex on 998 side
            match_pos = Vector((0, world_pos.y, world_pos.z))
            co, idx, dist = kd_998.find(match_pos)

            if idx is not None and dist < 5.0:
                target_obj, target_vi, target_world_pos = verts_998_edge[idx]

                # Calculate meeting point at gap center
                meeting_point = Vector((
                    gap_center,
                    (world_pos.y + target_world_pos.y) / 2.0,
                    (world_pos.z + target_world_pos.z) / 2.0
                ))

                new_world_pos = world_pos.lerp(meeting_point, smooth_factor)

                matrix_inv = obj.matrix_world.inverted()
                obj.data.vertices[vi].co = matrix_inv @ new_world_pos
                modified_903.add((obj.name, vi))

    # Update 903 meshes
    for obj in mesh_903_objs:
        obj.data.update()

    print(f"  Modified 998 vertices: {len(modified_998)}")
    print(f"  Modified 903 vertices: {len(modified_903)}")

    # Verify the gap is closed
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

    new_gap_width = new_min_x_903 - new_max_x_998
    print(f"\nAfter blending:")
    print(f"  998 max X: {new_max_x_998:.4f}")
    print(f"  903 min X: {new_min_x_903:.4f}")
    print(f"  New gap width: {new_gap_width:.4f}")

    # Join all meshes and merge close vertices at the seam
    print("\nJoining meshes and merging seam vertices...")

    # Select all mesh objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_998_objs + mesh_903_objs:
        obj.select_set(True)

    # Set one as active
    bpy.context.view_layer.objects.active = mesh_998_objs[0]

    # Join them
    bpy.ops.object.join()

    # The joined mesh is now the active object
    joined_obj = bpy.context.active_object
    joined_obj.name = "seamless_wave"

    # Merge close vertices using bmesh
    bm = bmesh.new()
    bm.from_mesh(joined_obj.data)

    verts_before = len(bm.verts)

    # Only merge vertices near the seam (X near gap_center)
    # After joining, we need to use the joined object's matrix
    matrix = joined_obj.matrix_world
    seam_verts = []
    for v in bm.verts:
        world_x = (matrix @ v.co).x
        if abs(world_x - gap_center) < 5.0:  # Even wider search area
            seam_verts.append(v)

    print(f"  Found {len(seam_verts)} vertices near seam")
    bmesh.ops.remove_doubles(bm, verts=seam_verts, dist=0.5)  # Even larger merge distance

    verts_after = len(bm.verts)
    print(f"  Merged {verts_before - verts_after} vertices at seam")

    # Recalculate normals for smooth shading at the seam
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(joined_obj.data)
    bm.free()
    joined_obj.data.update()

    # Enable smooth shading
    for poly in joined_obj.data.polygons:
        poly.use_smooth = True

    # Use auto smooth for better normal handling
    joined_obj.data.auto_smooth_angle = 1.0472  # 60 degrees

    print(f"  Final mesh: {len(joined_obj.data.vertices)} vertices, {len(joined_obj.data.polygons)} faces")


def main():
    # Separate meshes into 998 and 903 groups
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

    # Blend the edges with wider blend zone
    blend_mesh_edges(mesh_998_objs, mesh_903_objs, blend_width=10.0)

    print("\nBlending complete!")


if __name__ == "__main__":
    main()
