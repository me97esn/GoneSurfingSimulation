# Description: This script takes a file with the following structure:
# 
# { "frame_number<int>":{
#     "coordinates": [[x1, y1], [x2, y1], ...],
#     "samples": [v1, v2, v3, v4, ...]
#     "samples_2d": [[v1, v2, v3, v4], [v7, v8, v9, v10], ...]
#     "start_trace_x": <int>
#     "start_trace_y": <int>
#     "start_frame": <int>
#     "step_size": <float>
#     "len_x": <int>
#     "len_y": <int>
#   }   
# }
#   and reformat it to the following structure:
# { "samples:[[[v1, v2, v3], [v4, v5, v6], ...], [[v7, v8, v9], [v10, v11, v12], ...], ...]
# "step_size": <float>
# "start_trace_x": <int>
# "start_trace_y": <int>
# "start_frame": <int>
# "number_of_frequencies_to_include": <int>
# "number_of_rows_to_include": <int>
# "len_x": <int>
# "len_y": <int>
#}



import numpy as np
import json
import sys
source_file = sys.argv[1]
target_file = sys.argv[2]
start_frame = int(sys.argv[3])
number_of_frequencies_to_include = sys.argv[4]
number_of_rows_to_include = sys.argv[5]


result = { "samples":[], "step_size": None, "start_trace_x": None, "start_trace_y": None, "start_frame": None, "number_of_frequencies_to_include": None, "number_of_rows_to_include": None, "len_x": None, "len_y": None}

f = open(source_file)
data = json.load(f)
frames_sorted = sorted(data.keys(), key=lambda d: int(d))
for frame in frames_sorted:
    frame_data = data[frame]
    result["samples"].append(frame_data["samples_2d"])
    result["step_size"] = frame_data["step_size"]
    result["start_trace_x"] = frame_data["start_trace_x"]
    result["start_trace_y"] = frame_data["start_trace_y"]
    result["start_frame"] = start_frame
    result["number_of_frequencies_to_include"] = number_of_frequencies_to_include
    result["number_of_rows_to_include"] = number_of_rows_to_include
    result["len_x"] = frame_data["len_x"]
    result["len_y"] = frame_data["len_y"]

target_file = f"{target_file}"
f = open(target_file , "w")
print('writing to', target_file )
f.write(json.dumps(result))
