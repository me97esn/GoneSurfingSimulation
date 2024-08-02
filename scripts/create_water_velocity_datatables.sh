#! /bin/bash
start_frame=752
end_frame=760 #1325
node -max-old-space-size=32768 create_water_velocity_datatable.js /tmp/medium_wave_left_water_velocities $start_frame $end_frame  
python3 convert_vertices_to_samples.py /tmp/medium_wave_left_water_velocities /tmp/medium_wave_left_water_velocities_samples $start_frame $end_frame
