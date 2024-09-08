import json
import sys
from os import listdir
from os.path import isfile, join
from scipy.interpolate import griddata
import numpy as np
import math
import os
from json import JSONEncoder

class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.int64):
            return int(obj)
        return JSONEncoder.default(self, obj)

source_file = sys.argv[1]
target_file = sys.argv[2]
start_frame = int(sys.argv[3])
end_frame = int(sys.argv[4])

f = open(f"{source_file}")
data = json.load(f)
frames = []
for frame in data:
    frames.append(frame)
# sort the frames
frames = sorted(frames, key=lambda d: d)

result = []
for frame in frames:
    frame_samples = []
    samples = data[frame]['samples']
    coordinates = data[frame]['coordinates']
    result.push(frame_samples)

def reformat_data(coords, samples):
    """
    Coords has the format [
        [x1, y1], [x2, y1], [x3, y1], 
        [x1, y2], [x2, y2], [x3, y2],
        [x1, y3], [x2, y3], [x3, y3],
        [x1, y4], [x2, y4], [x3, y4]...
    ]
        and samples has the format [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12...]
    For the fft to work, the samples are converted to the format 
    [
        [s1, s2, s3], [s4, s5, s6], [s7, s8, s9], [s10, s11, s12]...
    ]
    """
    result = []
    # TODO: This doens't work, since the number of columns is not always 3
    for i in range(0, len(samples), 3):
        result.append(samples[i:i+3])
    return result

target_file = f"{target_file}"
f = open(target_file , "w")
print('writing to', target_file )
# f.write(json.dumps(samples_dict_per_frame, cls=NumpyArrayEncoder))

