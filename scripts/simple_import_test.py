"""
Simple test: Import chunks for frame 903 and 998 and position them
exactly like simple_model_seamless.blend. Nothing else.
"""
import bpy
import os
import glob

EXPORT_DIR = "/hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_03"
OUTPUT_BLEND = "/tmp/simple_import_test.blend"

# From simple_model_seamless.blend:
# chunk_*_998: Location (0, 0, 0), Rotation Z=90°
# chunk_*_903: Location (123.4486, -59.6493, 0), Rotation Z=90°

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def import_frame(frame, location, z_rotation):
    """Import chunks for a frame and set location/rotation (no transform_apply)."""
    pattern = os.path.join(EXPORT_DIR, f"*_mesh_{frame}.obj")
    obj_files = sorted(glob.glob(pattern))

    for obj_file in obj_files:
        bpy.ops.wm.obj_import(filepath=obj_file)
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                # Set rotation and location like simple_model_seamless.blend
                obj.rotation_euler.x = 0
                obj.rotation_euler.y = 0
                obj.rotation_euler.z = z_rotation
                obj.location = location


def main():
    clear_scene()

    # Import frame 998 at origin with Z=90° rotation
    import_frame(998, (0, 0, 0), 1.5708)

    # Import frame 903 at tiling position with Z=90° rotation
    import_frame(903, (123.4486, -59.6493, 0), 1.5708)

    # Save
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
    print(f"Saved: {OUTPUT_BLEND}")


if __name__ == "__main__":
    main()
