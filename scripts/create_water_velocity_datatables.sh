#! /bin/bash
# node -max-old-space-size=32768 create_water_velocity_datatable.js /tmp/medium_wave_left_water_velocities 752 760 #1325
python3 convert_vertices_to_samples.py /tmp/medium_wave_left_water_velocities /tmp/medium_wave_left_water_velocities_samples
