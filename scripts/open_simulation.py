import bpy
bpy.ops.wm.open_mainfile(filepath="../3dmodels/breaking_waves_beach_break_2.blend")
domain_properties = bpy.context.scene.flip_fluid.get_domain_properties()
domain_properties.surface.generate_motion_blur_data = True

# bpy.ops.flip_fluid_operators.bake_fluid_simulation_cmd()
