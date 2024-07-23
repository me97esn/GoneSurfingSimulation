import json
import sys
from os import listdir
from os.path import isfile, join
from scipy.interpolate import griddata
import numpy as np

folder = sys.argv[1]
print(folder)

onlyfiles = [f for f in listdir(folder) if isfile(join(folder, f))]

# sample_coords = x = np.arange(6).reshape(2,2)
# sample_x_coords = np.arange(0,180,1)
# sample_y_coords = np.arange(130,515,1)
sample_x_coords = np.arange(-15,-11,1)
sample_y_coords = np.arange(-270,-260,1)
# TODO: What are the min and max values for x and y? And which axis is which?
sample_coords=[[j,i] for i in sample_y_coords for j in sample_x_coords]
print(sample_coords)

# Opening JSON file
for file in onlyfiles:
    f = open(f"{folder}/{file}")

    # returns JSON object as 
    # a dictionary
    data = json.load(f)

    # Iterating through the json
    # list
    # x: 0 to 180
    # y: 130 to 515
    grid = griddata(data['coordinates'], data['x_values'], np.array(sample_coords), method='cubic')
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
