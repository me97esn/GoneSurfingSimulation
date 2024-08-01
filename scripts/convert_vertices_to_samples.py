# Description: This script takes a folder of JSON files, each containing a list of vertices and their corresponding x values. It prepares the data for fourier transform by making sure that the coordinates for each sample are evenly distributed. The vertices are not, but fouriere transform requires evenly distributed samples. 
import json
import sys
from os import listdir
from os.path import isfile, join
from scipy.interpolate import griddata
import numpy as np
import math
import os
from json import JSONEncoder


# Create a function to be called while serializing JSON


class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.int64):
            return int(obj)
        return JSONEncoder.default(self, obj)

source_folder = sys.argv[1]
target_folder = sys.argv[2]

onlyfiles = [f for f in listdir(source_folder) if isfile(join(source_folder, f))]

smallest_x = None
step_size = 1
for file in onlyfiles:
    f = open(f"{source_folder}/{file}")

    data = json.load(f)
    data_sorted_by_x = sorted(data['coordinates'], key=lambda d: d[0])
    data_sorted_by_y = sorted(data['coordinates'], key=lambda d: d[1])
    
    if smallest_x is None:
        smallest_x = data_sorted_by_x[0][0]
        largest_x = data_sorted_by_x[-1][0]
        smallest_y = data_sorted_by_y[0][1]
        largest_y = data_sorted_by_y[-1][1]
        print('smallest_x', smallest_x)
        print('largest_x', largest_x)
        print('smallest_y', smallest_y)
        print('largest_y', largest_y)

        border = 10
        sample_x_coords = np.arange(math.ceil(smallest_x+border),math.floor(largest_x-border),step_size)
        sample_y_coords = np.arange(math.ceil(smallest_y+border),math.floor(largest_y-border),step_size)
        sample_coords=[[j,i] for i in sample_y_coords for j in sample_x_coords]

    grid_x = griddata(data['coordinates'], data['x_values'], np.array(sample_coords), method='cubic', fill_value=0)
    grid_y = griddata(data['coordinates'], data['y_values'], np.array(sample_coords), method='cubic', fill_value=0)
    grid_z = griddata(data['coordinates'], data['z_values'], np.array(sample_coords), method='cubic', fill_value=0)
    
    if not os.path.exists(target_folder):
        os.mkdir(target_folder) 
    target_file = open(f"{target_folder}/{file}_x_samples.json", "w")
    result = {
        'coordinates': sample_coords, 
        'x_values': grid_x,
        'y_values': grid_y,
        'z_values': grid_z
    }
    print('writing to file', f"{target_folder}/x_samples_{file}.json")
    print(json.dumps(result, cls=NumpyArrayEncoder))
    target_file.write(json.dumps(result, cls=NumpyArrayEncoder))
    target_file.close()
    f.close()
