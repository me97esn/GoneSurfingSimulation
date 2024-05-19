import os
import json
target_object = bpy.data.objects['fluid_surface']
start_frame = 752
end_frame = 1325
# end_frame = 762 
scn = bpy.context.scene

output_directory = "/home/emil/workspace/GoneSurfingScripts"
output_filename = "wave_samples.json"
# TODO: write python file instead
output_filepath = os.path.join(output_directory, output_filename)
file = open(output_filepath, "w")
result = []
for frame in range(start_frame, end_frame+1):
    scn.frame_set(frame)
    frame_samples = []
    step = 3
    y_length = 400
    x_length = 150
    for x in range(x_length/step):
        row = []
        for y in range(y_length/step):
            ray_begin = Vector((-70+step * x, -250+step*y, 111))
            ray_end = Vector((-70+step*x, -250+step*y, -100))
            ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
            ray_direction = ray_end - ray_begin
            ray_direction.normalize()
            hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)
            sample = location.z
            row.append(sample)
        frame_samples.append(row)
    result.append(frame_samples)

file.write(json.dumps(result))
file.close()
