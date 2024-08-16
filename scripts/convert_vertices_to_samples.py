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

smallest_x = None
step_size = 0.5 
minValue = 3
samples_dict_per_frame = {}
samples_dict_per_frame= {}
x_border=20
y_border=40

onlyfiles = [f for f in listdir(source_folder) if isfile(join(source_folder, f))]

def filterSamplesAboveMinValue(coordinates, values, minValue):
    filtered_coordinates = []
    filtered_values = []
    for i, value in enumerate(values):
        if value > minValue:
            filtered_coordinates.append(coordinates[i])
            filtered_values.append(value)
    return filtered_coordinates, filtered_values

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
        num_of_x = (largest_x - smallest_x) / step_size
        num_of_y = (largest_y - smallest_y) / step_size

    coordinatesWithValueAboveMinTreshold, valuesAboveMinThreshold = filterSamplesAboveMinValue(data['coordinates'], data[values], minValue=minValue)
    grid_x, grid_y = np.mgrid[smallest_x+x_border:largest_x-x_border:complex(0,num_of_x), smallest_y+y_border:largest_y-y_border:complex(0,num_of_y)]

    grid_samples = griddata(coordinatesWithValueAboveMinTreshold, valuesAboveMinThreshold, (grid_x, grid_y), method='linear', fill_value=0)



    # TODO: ignore the samples that are outside the borders (3 directions).
    # Perhaps I should sort the values to get better results?
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

    array_of_values = convert_grid_to_array_of_values(grid_samples)
    array_of_coordinates = convert_grid_to_coordinates(grid_x, grid_y)

    samples_dict_per_frame[int(file.replace('.json', ''))] = {"samples":array_of_values, "coordinates":array_of_coordinates}

target_file = f"{target_file}"
f = open(target_file , "w")
print('writing to', target_file )
f.write(json.dumps(samples_dict_per_frame, cls=NumpyArrayEncoder))

