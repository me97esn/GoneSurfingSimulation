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



source_folder = sys.argv[1]
target_file = sys.argv[2]
values = sys.argv[3]
step_size = float(sys.argv[4])

