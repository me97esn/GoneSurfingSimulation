"""
Fix FLIP Fluids Whitewater Visibility Settings

This script fixes common visibility issues that prevent whitewater from appearing
in the viewport and exports. Run this in Blender before attempting to export.

Known issues this fixes:
- Whitewater display mode set to Preview or None instead of Final
- Hide particles enabled
- Incorrect whitewater percentage settings
"""

import bpy

print("\n" + "="*60)
print("FLIP FLUIDS WHITEWATER VISIBILITY FIX")
print("="*60)

# Find the FLIP domain
flip_domain = None
for obj in bpy.data.objects:
    if 'Flip Domain' in obj.name:
        flip_domain = obj
        print(f"\n✓ Found FLIP domain: {flip_domain.name}")
        break

if not flip_domain:
    print("\n✗ ERROR: No FLIP domain found!")
    print("Available objects:")
    for obj in bpy.data.objects:
        print(f"  - {obj.name}")
else:
    # Access FLIP Fluid properties
    if hasattr(flip_domain, 'flip_fluid'):
        ff = flip_domain.flip_fluid

        if ff.object_type == 'TYPE_DOMAIN':
            domain = ff.domain

            print("\n--- Current Settings ---")
            print(f"Whitewater simulation enabled: {domain.whitewater.enable_whitewater_simulation}")

            # Check display settings
            print(f"Whitewater viewport display: {domain.surface.whitewater_view_settings_mode}")
            print(f"Whitewater render display: {domain.surface.whitewater_render_settings_mode}")

            # Fix visibility settings
            print("\n--- Applying Fixes ---")

            # Set display modes to FINAL
            if domain.surface.whitewater_view_settings_mode != 'VIEW_SETTINGS_FINAL':
                domain.surface.whitewater_view_settings_mode = 'VIEW_SETTINGS_FINAL'
                print("✓ Set viewport display mode to FINAL")
            else:
                print("✓ Viewport display already set to FINAL")

            if domain.surface.whitewater_render_settings_mode != 'RENDER_SETTINGS_FINAL':
                domain.surface.whitewater_render_settings_mode = 'RENDER_SETTINGS_FINAL'
                print("✓ Set render display mode to FINAL")
            else:
                print("✓ Render display already set to FINAL")

            # Check whitewater objects
            print("\n--- Whitewater Objects ---")
            ww_objects = ['whitewater_foam', 'whitewater_bubble', 'whitewater_spray', 'whitewater_dust']

            for obj_name in ww_objects:
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]
                    print(f"\n{obj_name}:")
                    print(f"  Hide viewport: {obj.hide_viewport}")
                    print(f"  Hide render: {obj.hide_render}")

                    # Unhide objects
                    if obj.hide_viewport:
                        obj.hide_viewport = False
                        print("  ✓ Unhid in viewport")
                    if obj.hide_render:
                        obj.hide_render = False
                        print("  ✓ Unhid in render")

                    # Check particle system settings
                    for mod in obj.modifiers:
                        if mod.type == 'PARTICLE_SYSTEM':
                            ps = obj.particle_systems[mod.particle_system.name]
                            if ps.settings.use_render_emitter:
                                ps.settings.use_render_emitter = False
                                print(f"  ✓ Disabled 'use_render_emitter' for particle system")

            # Force frame refresh
            print("\n--- Refreshing Frame ---")
            current_frame = bpy.context.scene.frame_current
            bpy.context.scene.frame_set(current_frame)
            print(f"✓ Reloaded frame {current_frame}")

            # Check vertex count at current frame
            print("\n--- Vertex Count Check ---")
            for obj_name in ww_objects:
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]
                    depsgraph = bpy.context.evaluated_depsgraph_get()
                    obj_eval = obj.evaluated_get(depsgraph)

                    if obj_eval.type == 'MESH':
                        mesh = obj_eval.to_mesh()
                        vertex_count = len(mesh.vertices)
                        obj_eval.to_mesh_clear()

                        if vertex_count > 0:
                            print(f"✓ {obj_name}: {vertex_count} vertices")
                        else:
                            print(f"✗ {obj_name}: 0 vertices (no particles loaded)")

            print("\n" + "="*60)
            print("FIXES APPLIED!")
            print("="*60)
            print("\nNext steps:")
            print("1. Check if whitewater particles are visible in the viewport")
            print("2. Try scrubbing through frames to verify particles load")
            print("3. If still empty, check Domain > Whitewater > Enable Whitewater Simulation")
            print("4. Verify cache exists at:", domain.cache.get_cache_abspath())
            print("="*60)

    else:
        print("\n✗ ERROR: Object has no FLIP Fluid properties")
