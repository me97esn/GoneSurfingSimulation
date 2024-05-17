import os
import json
target_object = bpy.data.objects['fluid_surface']

output_directory = "/tmp"
output_filename = "output.txt"
output_filepath = os.path.join(output_directory, output_filename)
file = open(output_filepath, "w")
result = []
for x in range(100):
    ray_begin = Vector((8, 0+x, 111))
    ray_end = Vector((8, 0+x, -100))
    ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
    ray_direction = ray_end - ray_begin
    ray_direction.normalize()
    hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)
    print(hit, location, normals, index)
    sample = location.z
    result.append(sample)

file.write(json.dumps(result))
file.close()
