import os
import json
target_object = bpy.data.objects['fluid_surface']
start_frame = 752
end_frame = 1325
# end_frame = 800
scn = bpy.context.scene

output_directory = "/hdd/gone_surfing_exports/medium_wave_left/"
output_filename = "wave_samples.json"
output_filepath = os.path.join(output_directory, output_filename)
file = open(output_filepath, "w")
samples = []
for frame in range(start_frame, end_frame+1):
    scn.frame_set(frame)
    frame_samples = []
    step = 0.5
    y_length = 350
    x_length = 160
    start_trace_x = -60
    start_trace_y = -200
    for x in range(int(x_length/step)):
        row = []
        for y in range(int(y_length/step)):
            ray_begin = Vector((start_trace_x+step * x, start_trace_y+step*y, 100))
            ray_end = Vector((start_trace_x+step*x, start_trace_y+step*y, -100))
            ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
            ray_direction = ray_end - ray_begin
            ray_direction.normalize()
            hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)
            sample = location.z
            row.append(sample)
        frame_samples.append(row)
    samples.append(frame_samples)

file.write(json.dumps(samples))
file.close()
