"""
Manual White Water Export Script

Run this from within the Blender Scripting workspace:
1. Open breaking_waves_beach_break_2.blend in Blender (GUI mode)
2. Open this script in the Scripting workspace
3. Adjust the configuration variables below if needed
4. Run the script (Alt+P or click "Run Script")
"""

import bpy
import os

# ============================================================================
# CONFIGURATION - Adjust these as needed
# ============================================================================
START_FRAME = 886
END_FRAME = 1078
OUTPUT_DIR = "/hdd/gone_surfing_exports/medium_wave_left/white_water"

# Which white water types to export (foam is the most visible)
EXPORT_FOAM = True
EXPORT_BUBBLE = False  # Set to True if you also want bubbles
EXPORT_SPRAY = False   # Set to True if you also want spray
EXPORT_DUST = False    # Set to True if you also want dust

# ============================================================================
# SCRIPT - No need to modify below this line
# ============================================================================

def export_whitewater_sequence():
    """Export white water particles as OBJ sequence"""

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Find white water objects to export
    objects_to_export = []

    if EXPORT_FOAM and 'whitewater_foam' in bpy.data.objects:
        objects_to_export.append(('foam', bpy.data.objects['whitewater_foam']))

    if EXPORT_BUBBLE and 'whitewater_bubble' in bpy.data.objects:
        objects_to_export.append(('bubble', bpy.data.objects['whitewater_bubble']))

    if EXPORT_SPRAY and 'whitewater_spray' in bpy.data.objects:
        objects_to_export.append(('spray', bpy.data.objects['whitewater_spray']))

    if EXPORT_DUST and 'whitewater_dust' in bpy.data.objects:
        objects_to_export.append(('dust', bpy.data.objects['whitewater_dust']))

    if not objects_to_export:
        print("ERROR: No white water objects found!")
        print("Available objects:")
        for obj in bpy.data.objects:
            if 'whitewater' in obj.name.lower():
                print(f"  - {obj.name}")
        return

    print(f"\n{'='*60}")
    print("WHITE WATER EXPORT")
    print(f"{'='*60}")
    print(f"Frame range: {START_FRAME} to {END_FRAME}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Objects to export: {[name for name, _ in objects_to_export]}")
    print(f"{'='*60}\n")

    # Export each type separately
    for ww_type, ww_obj in objects_to_export:
        print(f"\n--- Exporting {ww_type} ---")

        # Check and remove problematic modifiers that block export
        removed_modifiers = []
        for mod in ww_obj.modifiers:
            print(f"  Found modifier: {mod.name} ({mod.type})")
            # Remove the modifier temporarily to allow proper export
            removed_modifiers.append((mod.name, mod.type, mod))
            ww_obj.modifiers.remove(mod)

        if removed_modifiers:
            print(f"  ✓ Removed {len(removed_modifiers)} modifier(s) for export")

        # Deselect all and select only this white water object
        bpy.ops.object.select_all(action='DESELECT')
        ww_obj.select_set(True)
        bpy.context.view_layer.objects.active = ww_obj

        # Export each frame
        for frame in range(START_FRAME, END_FRAME + 1):
            # Set the current frame
            bpy.context.scene.frame_set(frame)

            # Construct output path
            if len(objects_to_export) > 1:
                # Include type in filename if exporting multiple types
                output_file = os.path.join(OUTPUT_DIR, f"{ww_type}_{frame:06d}.obj")
            else:
                # Just use frame number if only one type
                output_file = os.path.join(OUTPUT_DIR, f"{frame:06d}.obj")

            # Export OBJ
            try:
                bpy.ops.wm.obj_export(
                    filepath=output_file,
                    export_selected_objects=True,
                    export_animation=False,
                    forward_axis='X',
                    up_axis='Z'
                )

                # Check vertex count for progress reporting
                if frame % 50 == 0 or frame == START_FRAME:
                    # Count vertices in the exported file
                    with open(output_file, 'r') as f:
                        vertex_count = sum(1 for line in f if line.startswith('v '))
                    print(f"  Frame {frame}: {vertex_count} particles exported")

            except Exception as e:
                print(f"  Frame {frame}: ERROR - {e}")

        print(f"✓ {ww_type} export complete!")

    print(f"\n{'='*60}")
    print("EXPORT COMPLETE!")
    print(f"{'='*60}")
    print(f"Total frames: {END_FRAME - START_FRAME + 1}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"\nNext step: Run the conversion script:")
    print(f"  cd {os.path.dirname(OUTPUT_DIR)}/../../scripts")
    print(f"  node export_white_water_points.js {START_FRAME} {END_FRAME}")
    print(f"{'='*60}")

# Run the export
export_whitewater_sequence()
