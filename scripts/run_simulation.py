import bpy

# File is already opened via command line argument
domain_properties = bpy.context.scene.flip_fluid.get_domain_properties()
domain_properties.surface.generate_motion_blur_data = True
bpy.ops.flip_fluid_operators.bake_fluid_simulation()
