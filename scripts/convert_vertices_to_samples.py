# Description: This script takes a folder of JSON files, each containing a list of vertices and their corresponding x values. It prepares the data for fourier transform by making sure that the coordinates for each sample are evenly distributed. The vertices are not, but fouriere transform requires evenly distributed samples. 
import json
import sys
from os import listdir
from os.path import isfile, join
from scipy.interpolate import griddata
import numpy as np
import math

folder = sys.argv[1]

onlyfiles = [f for f in listdir(folder) if isfile(join(folder, f))]

smallest_x = None
step_size = 10
# Opening JSON file
for file in onlyfiles:
    f = open(f"{folder}/{file}")

    # returns JSON object as 
    # a dictionary
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
        print('sample_coords', sample_coords)

    grid = griddata(data['coordinates'], data['x_values'], np.array(sample_coords), method='cubic', fill_value=0)
    print(grid)
#     # Closing file
    f.close()
#
# # # returns JSON object as 
# # # a dictionary
# # data = json.load(f)
# #
# # # Iterating through the json
# # # list
# # for i in data['emp_details']:
# #     print(i)
# #
# # # Closing file
# # f.close()
