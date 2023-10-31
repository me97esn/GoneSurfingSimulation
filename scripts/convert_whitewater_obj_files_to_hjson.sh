# !/bin/bash

node --max-old-space-size=8192 convert_whitewater_obj_files_to_houdini_json.js /hdd/gone_surfing_exports/medium_wave_left/medium_left_white_water_foam-1.hjson 0 0.5 &
node --max-old-space-size=8192 convert_whitewater_obj_files_to_houdini_json.js /hdd/gone_surfing_exports/medium_wave_left/medium_left_white_water_foam-2.hjson 0.5 1
# node --max-old-space-size=8192 convert_whitewater_obj_files_to_houdini_json.js D:\\gone_surfing_exports\\medium_wave_left\\medium_left_white_water_foam-1.hjson 0 0.5
# node --max-old-space-size=8192 convert_whitewater_obj_files_to_houdini_json.js D:\\gone_surfing_exports\\medium_wave_left\\medium_left_white_water_foam-2.hjson 0.5 1
