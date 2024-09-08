import os
import json
target_object = bpy.data.objects['fluid_surface']
start_frame = 752
end_frame = 1325
# end_frame = 754
scn = bpy.context.scene
step = 2
# output_directory = "/home/emil/workspace/GoneSurfingScripts"
output_directory = "/hdd/gone_surfing_exports/medium_wave_left"
output_filename = "wave_samples.json"
output_filename_normals_x = "wave_normals_x.json"
output_filename_normals_y = "wave_normals_y.json"
output_filename_normals_z = "wave_normals_z.json"
def samples_skeleton():
    return {
        "step_size":step, 
        "samples":[], 
        "start_frame":start_frame, 
        "end_frame":end_frame, 
        "start_trace_x":-60, 
        "start_trace_y":-200, 
        "x_length":160, 
        "y_length":350, 
        "coordinates":[]}

samples = samples_skeleton()
normals_x = samples_skeleton()
normals_y = samples_skeleton()
normals_z = samples_skeleton()

for frame in range(start_frame, end_frame+1):
    scn.frame_set(frame)
    frame_samples = []
    frame_coordinates = []
    frame_normals_x = []
    frame_normals_y = []
    frame_normals_z = []
    for x in range(int(samples["x_length"]/step)):
        row = []
        coordinates_row = []
        normals_row_x = []
        normals_row_y = []
        normals_row_z = []
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
            normals_row_x.append(normals.x)
            normals_row_y.append(normals.y)
            normals_row_z.append(normals.z)
        frame_samples.append(row)
        frame_coordinates.append(coordinates_row)
        frame_normals_x.append(normals_row_x)
        frame_normals_y.append(normals_row_y)
        frame_normals_z.append(normals_row_z)
    for d in [normals_x, normals_y, normals_z, samples]:
        d["coordinates"].append(frame_coordinates)
    samples["samples"].append(frame_samples)
    normals_x["samples"].append(frame_normals_x)
    normals_y["samples"].append(frame_normals_y)
    normals_z["samples"].append(frame_normals_z)

output_filepath = os.path.join(output_directory, output_filename)
file = open(output_filepath, "w")
file.write(json.dumps(samples))
file.close()

output_filepath_normals_x = os.path.join(output_directory, output_filename_normals_x)
file = open(output_filepath_normals_x, "w")
file.write(json.dumps(normals_x))
file.close()

output_filepath_normals_y = os.path.join(output_directory, output_filename_normals_y)
file = open(output_filepath_normals_y, "w")
file.write(json.dumps(normals_y))
file.close()

output_filepath_normals_z = os.path.join(output_directory, output_filename_normals_z)
file = open(output_filepath_normals_z, "w")
file.write(json.dumps(normals_z))
file.close()

print('written sampling files')
