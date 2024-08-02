#! /bin/bash
start_frame=752
end_frame=760 #1325
node -max-old-space-size=32768 create_water_velocity_datatable.js /tmp/medium_wave_left_water_velocities $start_frame $end_frame  
python3 convert_vertices_to_samples.py /tmp/medium_wave_left_water_velocities /tmp/medium_wave_left_water_velocities_samples/ $start_frame $end_frame
python3 convert_waveheight_samples_to_frequency_domain.py /tmp/medium_wave_left_water_velocities_samples/x_samples.json /tmp/medium_wave_left_water_velocities_samples/x_frequencies.json 25 120

# node convert_frequencies_json_to_ue4_datatable_format.js /tmp/medium_wave_left_water_velocities_samples/x_samples.json /hdd/gone_surfing_exports/medium_wave_left/velocity_x_frequencies_struct.json /hdd/gone_surfing_exports/medium_wave_left/velocity_x_frequencies_struct_metadata.json

