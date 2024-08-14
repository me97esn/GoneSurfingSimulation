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
    sorted_values = sorted(data[values])

    if smallest_x is None:
        smallest_x = data_sorted_by_x[0][0]
        largest_x = data_sorted_by_x[-1][0]
        smallest_y = data_sorted_by_y[0][1]
        largest_y = data_sorted_by_y[-1][1]
        largest_sample = sorted_values[-1]
        smallest_sample = sorted_values[0]
        num_of_x = (largest_x - smallest_x) / step_size
        num_of_y = (largest_y - smallest_y) / step_size

    grid_x, grid_y = np.mgrid[smallest_x:largest_x:complex(0,num_of_x), smallest_y:largest_y:complex(0,num_of_y)]

    grid_samples = griddata(data['coordinates'], data[values], (grid_x, grid_y), method='nearest', fill_value=0)

    # grid_y = griddata(data['coordinates'], data['y_values'], np.array(sample_coords), method='cubic', fill_value=0)
    # grid_z = griddata(data['coordinates'], data['z_values'], np.array(sample_coords), method='cubic', fill_value=0)

    def convert_grid_to_array_of_values(grid):
        samples = []
        for row in grid:
            for sample in row:
                samples.append(sample)
        return samples

    def convert_grid_to_coordinates(grid_x, grid_y):
        """
        A grid has the form 
grid_x: [[10.   10.   10.   10.   10.  ]
 [10.25 10.25 10.25 10.25 10.25]
 [10.5  10.5  10.5  10.5  10.5 ]
 [10.75 10.75 10.75 10.75 10.75]
 [11.   11.   11.   11.   11.  ]]
grid_y: [[0.   0.25 0.5  0.75 1.  ]
 [0.   0.25 0.5  0.75 1.  ]
 [0.   0.25 0.5  0.75 1.  ]
 [0.   0.25 0.5  0.75 1.  ]
 [0.   0.25 0.5  0.75 1.  ]]
, and we want to convert it to a list of coordinates, like this:
[[10.0, 0.0], [10.25, 0.0], [10.5, 0.0], [10.75, 0.0], [11.0, 0.0], [10.0, 0.25], [10.25, 0.25], [10.5, 0.25], [10.75, 0.25], [11.0, 0.25], [10.0, 0.5], [10.25, 0.5], [10.5, 0.5], [10.75, 0.5], [11.0, 0.5], [10.0, 0.75], [10.25, 0.75], [10.5, 0.75], [10.75, 0.75], [11.0, 0.75], [10.0, 1.0], [10.25, 1.0], [10.5, 1.0], [10.75, 1.0], [11.0, 1.0]]
        """
        return [[grid_x[i][j], grid_y[i][j]] for i in range(len(grid_x)) for j in range(len(grid_x[0]))]

    def reformat_data(samples_grid):
        return samples_grid.tolist()
        # samples_per_x_coord = {}
        # for x in sample_x_coords:
        #     samples_per_x_coord[x] = []
        # for i, sample in enumerate(samples_grid):
        #     coord = sample_coords[i]
        #     samples_per_x_coord[coord[0]].append(sample)
        # reformatted_result = []
        # for x in samples_per_x_coord:
        #     reformatted_result.append(samples_per_x_coord[x])
        # return reformatted_result
        # Restructure the data to use the same format as the wave height data

    # samples_dict_per_frame[int(file.replace('.json', ''))] = reformat_data(grid_x)
    # non_reformatted_samples_dict_per_frame[int(file.replace('.json', ''))] = {"samples":data[values], "coordinates":data['coordinates']}

    non_reformatted_samples_dict_per_frame[int(file.replace('.json', ''))] = {"samples":convert_grid_to_array_of_values(grid_samples), "coordinates":convert_grid_to_coordinates(grid_x, grid_y)}
    # non_reformatted_samples_dict_per_frame[int(file.replace('.json', ''))] = {"samples":grid_x, "coordinates": sample_coords}

    # y_samples_dict_per_frame[int(file.replace('.json', ''))] = reformat_data(grid_y)
    # z_samples_dict_per_frame[int(file.replace('.json', ''))] = reformat_data(grid_z)

def format_samples_to_ue4_struct_format(data_dict):
    output_samples = []
    for frame in range(start_frame, end_frame+1):
        if frame not in data_dict:
            print(f"Frame {frame} not found in data_dict")
            continue
        output_samples.append(data_dict[frame])
     
    return {"step_size": step_size, "samples": output_samples, "start_frame": start_frame, "end_frame": end_frame, "start_trace_x": smallest_x, "start_trace_y": smallest_y, "x_length": int( largest_x - smallest_x ), "y_length": int( largest_y - smallest_y ) }
# print('writing to', target_file)
# file = open(target_file, "w")
# file.write(json.dumps(format_samples_to_ue4_struct_format(samples_dict_per_frame)))
target_file_non_formatted = f"{target_file.replace('.json', '')}_non_formatted.json"
file_non_formatted = open(target_file_non_formatted, "w")
print('writing to', target_file_non_formatted)
file_non_formatted.write(json.dumps(non_reformatted_samples_dict_per_frame, cls=NumpyArrayEncoder))
# file.close()

