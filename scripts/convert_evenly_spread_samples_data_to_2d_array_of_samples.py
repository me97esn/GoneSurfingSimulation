# Description: This script takes a folder of JSON files, each containing a list of vertices and their corresponding x, y or z values. It prepares the data for fourier transform by making sure that the coordinates for each sample are evenly distributed. The vertices are not, but fouriere transform requires evenly distributed samples. 
# This script also splits the data into x, y and z values, and saves them in separate files. This is to make it possible to fourier transform x, y and z values separately.
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
target_file = f"{target_file}"
f = open(target_file , "w")
print('writing to', target_file )
f.write(json.dumps(samples_dict_per_frame, cls=NumpyArrayEncoder))

