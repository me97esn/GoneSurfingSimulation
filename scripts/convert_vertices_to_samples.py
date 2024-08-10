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

source_folder = sys.argv[1]
target_file = sys.argv[2]
start_frame = int(sys.argv[3])
end_frame = int(sys.argv[4])
values = sys.argv[5]

onlyfiles = [f for f in listdir(source_folder) if isfile(join(source_folder, f))]


smallest_x = None
step_size = 0.5
samples_dict_per_frame = {}
non_reformatted_samples_dict_per_frame = {}
# y_samples_dict_per_frame = {}
# z_samples_dict_per_frame = {}
for file in onlyfiles:
    print(f"Processing {file}")
    f = open(f"{source_folder}/{file}")


    data = json.load(f)
    data_sorted_by_x = sorted(data['coordinates'], key=lambda d: d[0])
    data_sorted_by_y = sorted(data['coordinates'], key=lambda d: d[1])

    if smallest_x is None:
        smallest_x = data_sorted_by_x[0][0]
        largest_x = data_sorted_by_x[-1][0]
        smallest_y = data_sorted_by_y[0][1]
        largest_y = data_sorted_by_y[-1][1]
        # print('smallest_x', smallest_x)
        # print('largest_x', largest_x)
        # print('smallest_y', smallest_y)
        # print('largest_y', largest_y)

        border = 10
        sample_x_coords = np.arange(math.ceil(smallest_x+border),math.floor(largest_x-border),step_size)
        sample_y_coords = np.arange(math.ceil(smallest_y+border),math.floor(largest_y-border),step_size)
        sample_coords=[[j,i] for i in sample_y_coords for j in sample_x_coords]
        # print('sample_x_coords', sample_x_coords)
        # print('sample_y_coords', sample_y_coords)

    out_coords = np.array(sample_coords)
    grid_x = griddata(data['coordinates'], data[values], out_coords, method='cubic', fill_value=0)
    # grid_y = griddata(data['coordinates'], data['y_values'], np.array(sample_coords), method='cubic', fill_value=0)
    # grid_z = griddata(data['coordinates'], data['z_values'], np.array(sample_coords), method='cubic', fill_value=0)

    def reformat_data(samples_grid):
        samples_per_x_coord = {}
        for x in sample_x_coords:
            samples_per_x_coord[x] = []
        for i, sample in enumerate(samples_grid):
            coord = sample_coords[i]
            samples_per_x_coord[coord[0]].append(sample)
        reformatted_result = []
        for x in samples_per_x_coord:
            reformatted_result.append(samples_per_x_coord[x])
        return reformatted_result
        # Restructure the data to use the same format as the wave height data

    samples_dict_per_frame[int(file.replace('.json', ''))] = reformat_data(grid_x)
    non_reformatted_samples_dict_per_frame[int(file.replace('.json', ''))] = {"samples":grid_x, "coordinates": out_coords} 

    # y_samples_dict_per_frame[int(file.replace('.json', ''))] = reformat_data(grid_y)
    # z_samples_dict_per_frame[int(file.replace('.json', ''))] = reformat_data(grid_z)

def format_samples_to_ue4_struct_format(data_dict):
    output_samples = []
    for frame in range(start_frame, end_frame+1):
        if frame not in data_dict:
            print(f"Frame {frame} not found in data_dict")
            continue
        output_samples.append(data_dict[frame])
     
    return {"step_size": step_size, "samples": output_samples, "start_frame": start_frame, "end_frame": end_frame, "start_trace_x": sample_x_coords[0], "start_trace_y": sample_y_coords[0], "x_length": int( largest_x - smallest_x ), "y_length": int( largest_y - smallest_y ) }
print('writing to', target_file)
target_file_non_formatted = f"{target_file.replace('.json', '')}_non_formatted.json"
file = open(target_file, "w")
file_non_formatted = open(target_file_non_formatted, "w")
file.write(json.dumps(format_samples_to_ue4_struct_format(samples_dict_per_frame)))
print('writing to', target_file_non_formatted)
file_non_formatted.write(json.dumps(non_reformatted_samples_dict_per_frame, cls=NumpyArrayEncoder))
file.close()

