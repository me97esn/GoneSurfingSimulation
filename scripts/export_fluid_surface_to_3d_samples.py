import os
import json
target_object = bpy.data.objects['fluid_surface']

output_directory = "/tmp"
output_filename = "output.txt"
output_filepath = os.path.join(output_directory, output_filename)
file = open(output_filepath, "w")
result = []
for x in range(100):
    row = []
    for y in range(100):
        ray_begin = Vector((0+x, 0+y, 111))
        ray_end = Vector((0+x, 0+y, -100))
        ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
        ray_direction = ray_end - ray_begin
        ray_direction.normalize()
        hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)
        sample = location.z
        row.append(sample)
    result.append(row)

file.write(json.dumps(result))
file.close()
