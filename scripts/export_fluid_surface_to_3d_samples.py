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
samples = []
for frame in range(start_frame, end_frame+1):
    scn.frame_set(frame)
    frame_samples = []
    step = 10
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

# Now: also write a subset of the frequencies after fft, to another file.
output_filename_freqs = "wave_frequencies_subset.json"
output_filepath_freqs = os.path.join(output_directory, output_filename_freqs)
file_freqs = open(output_filepath_freqs, "w")
number_of_frequencies_to_include = 10
frequencies_result = {"number_of_frequencies_to_include": number_of_frequencies_to_include }

frequencies_all_frames = [np.fft.fftn(frame) for frame in samples]
filtered_frequencies_all_frames = [np.array([[z for zi, z in enumerate(arr) if zi < number_of_freqs or zi >= len(arr)-number_of_freqs] for arr in frame_frequencies]) for frame_frequencies in frequencies_all_frames]
frequencies_result["frequencies_per_frame"] = filtered_frequencies_all_frames
file_freqs.write(json.dumps(frequencies_result))
file_freqs.close()
