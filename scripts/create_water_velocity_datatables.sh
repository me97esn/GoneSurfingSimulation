#! /bin/bash
start_frame=752
end_frame=760 #1325

mkdir -p /tmp/medium_wave_left_water_velocities
mkdir -p /tmp/medium_wave_left_water_velocities_samples

# Split into multiple calls since nodejs runs out of memory
for (( k = $start_frame; k < end_frame+100; k+=100 )); do
  local_start_frame=$k
  local_end_frame=$((k+100))
  if [ $k -gt $end_frame ]; then
    local_start_frame=$end_frame
    local_end_frame=$end_frame
  fi
  if [ $local_end_frame -gt $end_frame ]; then
    local_end_frame=$end_frame
  fi
  echo "Creating water velocity datatable for frames $local_start_frame to $local_end_frame"
  node -max-old-space-size=32768 create_water_velocity_datatable.js /tmp/medium_wave_left_water_velocities $local_start_frame $local_end_frame
done

python3 convert_vertices_to_samples.py /tmp/medium_wave_left_water_velocities /tmp/medium_wave_left_water_velocities_samples/x_samples.json $start_frame $end_frame x_values 
python3 convert_vertices_to_samples.py /tmp/medium_wave_left_water_velocities /tmp/medium_wave_left_water_velocities_samples/y_samples.json $start_frame $end_frame y_values
python3 convert_vertices_to_samples.py /tmp/medium_wave_left_water_velocities /tmp/medium_wave_left_water_velocities_samples/z_samples.json $start_frame $end_frame z_values

python3 convert_waveheight_samples_to_frequency_domain.py /tmp/medium_wave_left_water_velocities_samples/x_samples.json /tmp/medium_wave_left_water_velocities_samples/x_frequencies.json 25 120
python3 convert_waveheight_samples_to_frequency_domain.py /tmp/medium_wave_left_water_velocities_samples/y_samples.json /tmp/medium_wave_left_water_velocities_samples/y_frequencies.json 25 120
python3 convert_waveheight_samples_to_frequency_domain.py /tmp/medium_wave_left_water_velocities_samples/z_samples.json /tmp/medium_wave_left_water_velocities_samples/z_frequencies.json 25 120

node convert_frequencies_json_to_ue4_datatable_format.js /tmp/medium_wave_left_water_velocities_samples/x_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_x_frequencies_struct.json /hdd/gone_surfing_exports/medium_wave_left/velocity_x_frequencies_struct_metadata.json
node convert_frequencies_json_to_ue4_datatable_format.js /tmp/medium_wave_left_water_velocities_samples/y_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_y_frequencies_struct.json /hdd/gone_surfing_exports/medium_wave_left/velocity_y_frequencies_struct_metadata.json
node convert_frequencies_json_to_ue4_datatable_format.js /tmp/medium_wave_left_water_velocities_samples/z_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_z_frequencies_struct.json /hdd/gone_surfing_exports/medium_wave_left/velocity_z_frequencies_struct_metadata.json

