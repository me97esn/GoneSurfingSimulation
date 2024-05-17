target_object = bpy.data.objects['fluid_surface']
ray_direction = ray_end - ray_begin
ray_direction.normalize()

for x in range(100):
    ray_begin = Vector((8, 0+x, 111))
    ray_end = Vector((8, 0+x, -100))
    ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
    target_object.ray_cast(ray_begin_local, ray_direction)
