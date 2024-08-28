#! /bin/bash


# I am creating data files for wave height in two ways: one with jittery waves and one with stable waves. The jittery should only be used to help in placing the water velocities, while the stable should be used for the actual wave height. The axis are different in these two files.

start_frame=752
# end_frame=1325
end_frame=760
folder=/hdd/gone_surfing_exports/medium_wave_left
tmp_folder=/hdd/gone_surfing_exports/medium_wave_left/tmp
tmp_folder_samples=/hdd/gone_surfing_exports/medium_wave_left/tmp_samples
step_size=5
number_of_frequencies_to_include=100
number_of_rows_to_include=100

# tmp_folder=/tmp/medium_wave_left_water_velocities
# tmp_folder_samples=/tmp/medium_wave_left_water_velocities_samples

#######################################################
# Here starts the handling of sample files created in blender using flip fluids bobj files
#######################################################
mkdir -p $folder
mkdir -p $tmp_folder
mkdir -p $tmp_folder_samples


# Read the blur data files from blender/flip fluids, and convert them to human readable json
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
  # echo "Creating water velocity datatable for frames $local_start_frame to $local_end_frame"
  # node -max-old-space-size=32768 create_water_velocity_datatable.js $tmp_folder $local_start_frame $local_end_frame
done
# ## Read the files from the previous step and make sure that they are evenly spread. This also merges all of the frame files into one file
# python3 convert_vertices_to_samples.py $tmp_folder $tmp_folder_samples/dx.json $start_frame $end_frame dx
# # python3 convert_vertices_to_samples.py $tmp_folder $tmp_folder_samples/dy.json $start_frame $end_frame dy
# # python3 convert_vertices_to_samples.py $tmp_folder $tmp_folder_samples/dz.json $start_frame $end_frame dz
# python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/height-per-frame.json height $step_size
# python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/height-per-frame-example.json height 50
#
# python3 reformat_coords_and_values_to_3d_samples.py $tmp_folder_samples/height-per-frame.json $tmp_folder_samples/height_3d_samples.json $start_frame $number_of_frequencies_to_include $number_of_rows_to_include
# python3 reformat_coords_and_values_to_3d_samples.py $tmp_folder_samples/height-per-frame-example.json $tmp_folder_samples/height_3d_samples-example.json $start_frame $number_of_frequencies_to_include $number_of_rows_to_include


# # Convert the samples from the previous step to frequency domain
# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/x_samples.json $tmp_folder_samples/x_frequencies.json 25 25
# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/y_samples.json $tmp_folder_samples/y_frequencies.json 25 25
# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/z_samples.json $tmp_folder_samples/z_frequencies.json 25 25
# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/height_3d_samples.json $tmp_folder_samples/height_jittery_frequencies.json 
# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/height_3d_samples-example.json $tmp_folder_samples/height_frequencies-example.json 

# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/height_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/height_frequencies_struct.json $folder/height_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/height_frequencies-example.json /hdd/gone_surfing_exports/medium_wave_left/height_frequencies_struct-example.json $folder/height_frequencies_struct_metadata-example.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/height_frequencies_stable.json /hdd/gone_surfing_exports/medium_wave_left/height_frequencies_struct-stable.json $folder/height_frequencies_struct_metadata-example.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/height_jittery_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/height_frequencies_struct-jittery.json $folder/height_frequencies_struct_metadata-example.json

#######################################################
# Here starts the handling of sample files created in blender using ray trace
#######################################################

# Convert the files created using ray trace in blender
python3 convert_samples_to_frequency_domain.py $folder/wave_samples.json $tmp_folder_samples/height_frequencies_stable.json 
node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/height_frequencies_stable.json /hdd/gone_surfing_exports/medium_wave_left/height_frequencies_stable_struct.json $folder/height_frequencies_struct_stable_metadata.json

# TODO: Also convert the normals files to frequency domain!

# # Convert the frequency domain files to UE4 datatable format
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/x_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_x_frequencies_struct.json $folder/velocity_x_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/y_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_y_frequencies_struct.json $folder/velocity_y_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/z_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_z_frequencies_struct.json $folder/velocity_z_frequencies_struct_metadata.json
