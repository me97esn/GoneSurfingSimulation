#! /bin/bash
start_frame=752
# end_frame=1325
end_frame=752
folder=/hdd/gone_surfing_exports/medium_wave_left
tmp_folder=/hdd/gone_surfing_exports/medium_wave_left/tmp
tmp_folder_samples=/hdd/gone_surfing_exports/medium_wave_left/tmp_samples
# tmp_folder=/tmp/medium_wave_left_water_velocities
# tmp_folder_samples=/tmp/medium_wave_left_water_velocities_samples

mkdir -p $folder
mkdir -p $tmp_folder
mkdir -p $tmp_folder_samples


# # Read the blur data files from blender/flip fluids, and convert them to human readable json
# # Split into multiple calls since nodejs runs out of memory
# for (( k = $start_frame; k < end_frame+100; k+=100 )); do
#   local_start_frame=$k
#   local_end_frame=$((k+100))
#   if [ $k -gt $end_frame ]; then
#     local_start_frame=$end_frame
#     local_end_frame=$end_frame
#   fi
#   if [ $local_end_frame -gt $end_frame ]; then
#     local_end_frame=$end_frame
#   fi
#   echo "Creating water velocity datatable for frames $local_start_frame to $local_end_frame"
#   node -max-old-space-size=32768 create_water_velocity_datatable.js $tmp_folder $local_start_frame $local_end_frame
# done
# ## Read the files from the previous step and make sure that they are evenly spread. This also merges all of the frame files into one file
# # python3 convert_vertices_to_samples.py $tmp_folder $tmp_folder_samples/x_samples.json $start_frame $end_frame x_values 
# # python3 convert_vertices_to_samples.py $tmp_folder $tmp_folder_samples/y_samples.json $start_frame $end_frame y_values
# # python3 convert_vertices_to_samples.py $tmp_folder $tmp_folder_samples/z_samples.json $start_frame $end_frame z_values
python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/height.json $start_frame $end_frame height 


# python3 convert_evenly_spread_samples_data_to_2d_array_of_samples.py $tmp_folder_samples/height.json $tmp_folder_samples/height_as_2d_array_samples.json  $start_frame $end_frame height 


# # Convert the samples from the previous step to frequency domain
# python3 convert_waveheight_samples_to_frequency_domain.py $tmp_folder_samples/x_samples.json $tmp_folder_samples/x_frequencies.json 25 25
# python3 convert_waveheight_samples_to_frequency_domain.py $tmp_folder_samples/y_samples.json $tmp_folder_samples/y_frequencies.json 25 25
# python3 convert_waveheight_samples_to_frequency_domain.py $tmp_folder_samples/z_samples.json $tmp_folder_samples/z_frequencies.json 25 25
# python3 convert_waveheight_samples_to_frequency_domain.py $tmp_folder_samples/height.json $tmp_folder_samples/height_frequencies.json 25 100
#
# # Convert the frequency domain files to UE4 datatable format
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/x_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_x_frequencies_struct.json $folder/velocity_x_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/y_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_y_frequencies_struct.json $folder/velocity_y_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/z_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_z_frequencies_struct.json $folder/velocity_z_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/height_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/height_frequencies_struct.json $folder/height_frequencies_struct_metadata.json
#
# # TODO: Rename this file since it creates datatable for both velocities and height
#
