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
start_frame = int(sys.argv[3])
end_frame = int(sys.argv[4])

onlyfiles = [f for f in listdir(source_folder) if isfile(join(source_folder, f))]

smallest_x = None
step_size = 0.5
samples_dict_per_frame = {}
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
    
    # if not os.path.exists(target_folder):
    #     os.mkdir(target_folder) 
    # target_file = open(f"{target_folder}/{file}_x_samples.json", "w")

    # Restructure the data to use the same format as the wave height data
    # TODO Only x values now, should do the same for y and z
    # The files are probably not read in the correct order, so we need to restructure the data
    samples_per_x_coord = {}
    for x in sample_x_coords:
        samples_per_x_coord[x] = []
    for i, sample in enumerate(grid_x):
        coord = sample_coords[i]
        samples_per_x_coord[coord[0]].append(sample)
        # print(i, sample, coord)
    reformatted_result = []
    for x in samples_per_x_coord:
        reformatted_result.append(samples_per_x_coord[x])
    samples_dict_per_frame[int(file.replace('.json', ''))] = reformatted_result
# Done with reading all files, now write the samples to one file
# print('samples_dict_per_frame', samples_dict_per_frame)

output_samples = []
for frame in range(start_frame, end_frame+1):
    if frame not in samples_dict_per_frame:
        print('frame not in samples_dict_per_frame')
        continue
    output_samples.append(samples_dict_per_frame[frame])

# {"step_size": 100, "samples": [[[17.39013671875, 17.326210021972656, 15.935287475585938]], [[17.390716552734375, 17.321426391601562, 15.921951293945312]], [[17.390487670898438, 17.316307067871094, 15.914993286132812]], [[17.3892822265625, 17.31640625, 15.87310791015625]], [[17.388229370117188, 17.321388244628906, 15.882888793945312]], [[17.389022827148438, 17.326515197753906, 15.883934020996094]], [[17.38909149169922, 17.322525024414062, 15.933441162109375]], [[17.388580322265625, 17.32244110107422, 15.94232177734375]], [[17.387252807617188, 17.315940856933594, 15.939109802246094]]], "start_frame": 752, "end_frame": 760, "start_trace_x": -60, "start_trace_y": -200, "x_length": 160, "y_length": 350}

result = {"step_size": step_size, "samples": output_samples, "start_frame": start_frame, "end_frame": end_frame, "start_trace_x": sample_x_coords[0], "start_trace_y": sample_y_coords[0], "x_length": int( largest_x - smallest_x ), "y_length": int( largest_y - smallest_y ) }
if not os.path.exists(target_folder):
    os.mkdir(target_folder)
target_file = open(f"{target_folder}/x_samples.json", "w")
print('writing to', f"{target_folder}/x_samples.json")
print('result', result)
target_file.write(json.dumps(result))
target_file.close() 
