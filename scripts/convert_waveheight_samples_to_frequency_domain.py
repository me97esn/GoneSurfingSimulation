import numpy as np
import json
import os
import sys
from json import JSONEncoder

class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif np.iscomplexobj(obj):
            return [np.real(obj), np.imag(obj)]
        return JSONEncoder.default(self, obj)
number_of_frequencies_to_include = int(sys.argv[3]) or 10
number_of_rows_to_include = int(sys.argv[4]) or 10

filename = sys.argv[1] 
f = open(filename, "r")
samples_data = json.load(f)
samples = samples_data["samples"]

output_filepath_freqs = sys.argv[2] 
file_freqs = open(output_filepath_freqs, "w")
frequencies_result = {
    "start_trace_y": samples_data["start_trace_y"],
    "start_trace_x": samples_data["start_trace_x"],
    "step_size": samples_data["step_size"],
    "start_frame": samples_data["start_frame"],
    "number_of_frequencies_to_include": number_of_frequencies_to_include,
    "number_of_rows_to_include": number_of_rows_to_include,
    "len_x": len(samples[0]),
    "len_y": len(samples[0][0])}

# This is the number of low frequency frequencies, and high frequency frequencies to include. They are by coincidence the same number.
frequencies_all_frames = [np.fft.fftn(frame) for frame in samples]
filtered_frequencies_all_frames = [np.array([[z for zi, z in enumerate(arr) if zi < number_of_frequencies_to_include or zi >= len(arr)-number_of_frequencies_to_include ] for arr in frame_frequencies]) for frame_frequencies in frequencies_all_frames]

# Also filter out the rows, since I use 2d fft, I can filter both x and y
double_filtered_freqs = []
for frame in range(len( filtered_frequencies_all_frames)):
    frame_data = []
    double_filtered_freqs.append(frame_data)
    for y in range(len(filtered_frequencies_all_frames[frame])):
        if y < number_of_rows_to_include or y >= len( filtered_frequencies_all_frames[frame])-number_of_rows_to_include:
            frame_data.append(filtered_frequencies_all_frames[frame][y])

# frequencies_result["frequencies_per_frame"] = filtered_frequencies_all_frames
frequencies_result["frequencies_per_frame"] = double_filtered_freqs 
file_freqs.write(json.dumps(frequencies_result, cls=NumpyArrayEncoder))
file_freqs.close()
