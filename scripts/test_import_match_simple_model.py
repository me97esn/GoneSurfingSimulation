"""
Test script to import chunks from export folder and position them
exactly like simple_model_seamless.blend for comparison.
"""
import bpy
import os
import glob

# Configuration - matches simple_model_seamless.blend exactly
EXPORT_DIR = "/hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_03"
OUTPUT_BLEND = "/tmp/test_import_match.blend"

# Transforms from simple_model_seamless.blend:
# chunk_0_0_998: Location (0, 0, 0), Rotation Z=90° (1.5708)
# chunk_0_0_903: Location (123.4486, -59.6493, 0), Rotation Z=90° (1.5708)
FRAME_998_LOCATION = (0, 0, 0)
FRAME_903_LOCATION = (123.4486, -59.6493, 0)
Z_ROTATION = 1.5708  # 90 degrees


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def import_frame_chunks(frame, location, z_rotation):
    """Import all chunks for a frame and apply transforms like simple_model_seamless.blend."""
    pattern = os.path.join(EXPORT_DIR, f"*_mesh_{frame}.obj")
    obj_files = sorted(glob.glob(pattern))

    print(f"\nImporting frame {frame} chunks...")
    print(f"  Location: {location}")
    print(f"  Z Rotation: {z_rotation} rad ({z_rotation * 57.3:.1f}°)")

    imported = []
    for obj_file in obj_files:
        print(f"  Importing: {os.path.basename(obj_file)}")
        bpy.ops.wm.obj_import(filepath=obj_file)

        # Get all selected objects (OBJ may contain multiple meshes)
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                # Reset any rotation from importer, apply our transforms
                # DON'T bake transforms - keep them as object transforms like simple_model_seamless.blend
                obj.rotation_euler.x = 0
                obj.rotation_euler.y = 0
                obj.rotation_euler.z = z_rotation
                obj.location = location
                imported.append(obj)
                print(f"    -> {obj.name}")

    return imported


def main():
    print("="*60)
    print("TEST: Import chunks matching simple_model_seamless.blend")
    print("="*60)

    clear_scene()

    # Import frame 998 at origin with Z rotation
    objs_998 = import_frame_chunks(998, FRAME_998_LOCATION, Z_ROTATION)

    # Import frame 903 at tiling position with Z rotation
    objs_903 = import_frame_chunks(903, FRAME_903_LOCATION, Z_ROTATION)

    print(f"\nImported {len(objs_998)} objects for frame 998")
    print(f"Imported {len(objs_903)} objects for frame 903")

    # Print world bounds for verification
    print("\n" + "="*60)
    print("VERIFICATION - World space bounds:")
    print("="*60)

    for label, objs in [("Frame 998", objs_998), ("Frame 903", objs_903)]:
        all_wxs, all_wys = [], []
        for obj in objs:
            matrix = obj.matrix_world
            for v in obj.data.vertices:
                world_pos = matrix @ v.co
                all_wxs.append(world_pos.x)
                all_wys.append(world_pos.y)

        if all_wxs:
            print(f"\n{label}:")
            print(f"  World X: [{min(all_wxs):.2f}, {max(all_wxs):.2f}]")
            print(f"  World Y: [{min(all_wys):.2f}, {max(all_wys):.2f}]")

    # Check gap
    if objs_998 and objs_903:
        max_x_998 = max((obj.matrix_world @ v.co).x
                        for obj in objs_998 for v in obj.data.vertices)
        min_x_903 = min((obj.matrix_world @ v.co).x
                        for obj in objs_903 for v in obj.data.vertices)
        print(f"\nGap between meshes: {min_x_903 - max_x_998:.2f} units")

    # Save blend file
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
    print(f"\nSaved: {OUTPUT_BLEND}")
    print("\nCompare this file with simple_model_seamless.blend to verify transforms match.")


if __name__ == "__main__":
    main()
