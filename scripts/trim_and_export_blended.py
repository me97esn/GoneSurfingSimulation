"""
Trim the blended mesh to keep only the frame 998 portion plus 5-10% extra
for the blended seam area, then export as OBJ.
"""
import bpy
import bmesh

INPUT_BLEND = "/tmp/simple_import_blended.blend"
OUTPUT_OBJ = "/tmp/seamless_998_trimmed.obj"

# Original frame 998 bounds (from the simple_import_test output)
# Before blending: 998 X range was approximately [0.32, 122.70]
ORIGINAL_998_MIN_X = 0.32
ORIGINAL_998_MAX_X = 122.70

# Extra width percentage (5-10%)
EXTRA_WIDTH_PERCENT = 0.07  # 7%


def trim_mesh_to_bounds(obj, min_x, max_x):
    """
    Remove all vertices outside X bounds, which removes their connected faces.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    matrix = obj.matrix_world
    matrix_inv = matrix.inverted()

    # Find vertices outside bounds and delete them
    verts_to_delete = []
    for v in bm.verts:
        world_x = (matrix @ v.co).x
        if world_x < min_x or world_x > max_x:
            verts_to_delete.append(v)

    print(f"  Deleting {len(verts_to_delete)} vertices outside X bounds [{min_x:.2f}, {max_x:.2f}]")

    # Delete vertices (this also removes connected edges and faces)
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    # Recalculate normals
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def main():
    # Open the blended file
    print(f"Opening: {INPUT_BLEND}")
    bpy.ops.wm.open_mainfile(filepath=INPUT_BLEND)

    # Find the seamless_wave mesh
    seamless_obj = bpy.data.objects.get("seamless_wave")
    if not seamless_obj:
        print("ERROR: seamless_wave object not found!")
        return

    # Calculate trimmed bounds
    original_width = ORIGINAL_998_MAX_X - ORIGINAL_998_MIN_X
    extra_width = original_width * EXTRA_WIDTH_PERCENT

    trim_min_x = ORIGINAL_998_MIN_X
    trim_max_x = ORIGINAL_998_MAX_X + extra_width

    print(f"Original 998 X bounds: [{ORIGINAL_998_MIN_X:.2f}, {ORIGINAL_998_MAX_X:.2f}]")
    print(f"Original width: {original_width:.2f}")
    print(f"Extra width ({EXTRA_WIDTH_PERCENT*100:.0f}%): {extra_width:.2f}")
    print(f"Trimming to X bounds: [{trim_min_x:.2f}, {trim_max_x:.2f}]")

    # Get current mesh bounds
    matrix = seamless_obj.matrix_world
    xs = [(matrix @ v.co).x for v in seamless_obj.data.vertices]
    print(f"\nBefore trimming:")
    print(f"  Mesh X bounds: [{min(xs):.2f}, {max(xs):.2f}]")
    print(f"  Vertices: {len(seamless_obj.data.vertices)}")
    print(f"  Faces: {len(seamless_obj.data.polygons)}")

    # Trim the mesh
    print("\nTrimming mesh...")
    trim_mesh_to_bounds(seamless_obj, trim_min_x, trim_max_x)

    # Verify new bounds
    xs = [(matrix @ v.co).x for v in seamless_obj.data.vertices]
    print(f"\nAfter trimming:")
    print(f"  Mesh X bounds: [{min(xs):.2f}, {max(xs):.2f}]")
    print(f"  Vertices: {len(seamless_obj.data.vertices)}")
    print(f"  Faces: {len(seamless_obj.data.polygons)}")

    # Export as OBJ
    print(f"\nExporting to: {OUTPUT_OBJ}")
    bpy.ops.object.select_all(action='DESELECT')
    seamless_obj.select_set(True)
    bpy.context.view_layer.objects.active = seamless_obj

    bpy.ops.wm.obj_export(
        filepath=OUTPUT_OBJ,
        export_selected_objects=True,
        export_materials=False,
        export_uv=False,
        export_normals=True,
        forward_axis='Y',
        up_axis='Z'
    )

    print("Export complete!")


if __name__ == "__main__":
    main()
