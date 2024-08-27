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

filename = sys.argv[1]
f = open(filename, "r")

## Expects data on the format:
"""
{
    "start_trace_y": 0,
    "start_trace_x": 0,
    "step_size": 1,
    "start_frame": 0,
    "samples": [ # frame
        [ # row
            [0.1, 0.2, 0.3],# column
            [0.4, 0.5, 0.6],# column
            [0.7, 0.8, 0.9]# column
        ], # row
        [
            [0.1, 0.2, 0.3],# column
            [0.4, 0.5, 0.6],# column
            [0.7, 0.8, 0.9]# column
        ]
    ]
    "normals": [# frame
        [ # row
            [#column
                [0,0,1] #Vector3d, [0,0,0.32], [0,0,1]],...
        ], 

}
"""
# Note that no coordinates is in the data, this is because samples are evenly spread with step_size from start_trace_x and start_trace_y


samples_data = json.load(f)

samples = samples_data["samples"]

output_filepath_freqs = sys.argv[2] 
file_freqs = open(output_filepath_freqs, "w")
frequencies_result = {
    "start_trace_y": samples_data["start_trace_y"],
    "start_trace_x": samples_data["start_trace_x"],
    "step_size": samples_data["step_size"],
    "start_frame": samples_data["start_frame"],
    "number_of_frequencies_to_include": -1, # deprecated, should remove from UE Struct
    "number_of_rows_to_include": -1, # deprecated, should remove from UE Struct
    "len_x": len(samples[0]),
    "len_y": len(samples[0][0])}
print(f'writing to {output_filepath_freqs}')
frequencies_result["frequencies_per_frame"] = [np.fft.fft2(samples_one_frame) for samples_one_frame in samples]
file_freqs.write(json.dumps(frequencies_result, cls=NumpyArrayEncoder))
file_freqs.close()
