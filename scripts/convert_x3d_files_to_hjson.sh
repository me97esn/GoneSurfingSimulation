# !/bin/bash
date
node --max-old-space-size=4096 convert_x3d_to_houdini_json.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_waves_display_w_normals-1.hjson  0 0.33 &
node --max-old-space-size=4096 convert_x3d_to_houdini_json.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_waves_display_w_normals-2.hjson  0.33 0.66 &
node --max-old-space-size=4096 convert_x3d_to_houdini_json.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_waves_display_w_normals-3.hjson  0.66 1
# node --max-old-space-size=4096 convert_x3d_to_houdini_json.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_waves_display_w_normals-2.hjson  0.5 0.75 
# node --max-old-space-size=4096 convert_x3d_to_houdini_json.js /hdd/gone_surfing_exports/medium_wave_left/medium_wave_left_waves_display_w_normals-1.hjson  0.75 1
date
