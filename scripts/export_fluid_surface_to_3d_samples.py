import os
import json
target_object = bpy.data.objects['fluid_surface']
start_frame = 752
end_frame = 1325
# end_frame = 754
scn = bpy.context.scene
step = 5 
output_directory = "/home/emil/workspace/GoneSurfingScripts"
output_filename = "wave_samples.json"
output_filepath = os.path.join(output_directory, output_filename)
file = open(output_filepath, "w")
samples = {
    "step_size":step, 
    "samples":[], 
    "start_frame":start_frame, 
    "end_frame":end_frame, 
    "start_trace_x":-60, 
    "start_trace_y":-200, 
    "x_length":160, 
    "y_length":350, 
    "coordinates":[],
    "normals":[]}
for frame in range(start_frame, end_frame+1):
    scn.frame_set(frame)
    frame_samples = []
    frame_coordinates = []
    frame_normals = []
    for x in range(int(samples["x_length"]/step)):
        row = []
        coordinates_row = []
        normals_row = []
        for y in range(int(samples["y_length"]/step)):
            ray_begin = Vector((samples["start_trace_x"]+step * x, samples["start_trace_y"]+step*y, 100))
            ray_end = Vector((samples["start_trace_x"]+step*x, samples["start_trace_y"]+step*y, -100))
            ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
            ray_direction = ray_end - ray_begin
            ray_direction.normalize()
            hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)
            sample = location.z
            row.append(sample)
            coordinates_row.append([location.x, location.y])
            normals_row.append([normals.x, normals.y, normals.z])
        frame_samples.append(row)
        frame_coordinates.append(coordinates_row)
        frame_normals.append(normals_row)
    samples["samples"].append(frame_samples)
    samples["coordinates"].append(frame_coordinates)
    samples["normals"].append(frame_normals)

file.write(json.dumps(samples))
file.close()
