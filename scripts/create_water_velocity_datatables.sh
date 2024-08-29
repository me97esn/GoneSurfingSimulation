#! /bin/bash


# I am creating data files for wave height in two ways: one with jittery waves and one with stable waves. The jittery should only be used to help in placing the water velocities, while the stable should be used for the actual wave height. The axis are different in these two files.

folder=/hdd/gone_surfing_exports/medium_wave_left
tmp_folder=/hdd/gone_surfing_exports/medium_wave_left/tmp
tmp_folder_samples=/hdd/gone_surfing_exports/medium_wave_left/tmp_samples
step_size=5

# tmp_folder=/tmp/medium_wave_left_water_velocities
# tmp_folder_samples=/tmp/medium_wave_left_water_velocities_samples

mkdir -p $folder
mkdir -p $tmp_folder
mkdir -p $tmp_folder_samples

#######################################################
# Here starts the handling of sample files created in blender using flip fluids bobj files
#######################################################
start_frame=752
# end_frame=1325
end_frame=753

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
# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/dx.json $start_frame $end_frame dx
# # python3 convert_vertices_to_samples.py $tmp_folder $tmp_folder_samples/dy.json $start_frame $end_frame dy
# # python3 convert_vertices_to_samples.py $tmp_folder $tmp_folder_samples/dz.json $start_frame $end_frame dz
python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/dx-per-frame-example.json dx 50
python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/dx-per-frame.json dx $step_size
python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/dx-per-frame.json $tmp_folder_samples/dx-frequencies.json 
node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/dx-frequencies.json $folder/dx_frequencies_struct.json $folder/dx_frequencies_struct_metadata.json

exit 1

#######################################################
# Here starts the handling of sample files created in blender using ray trace
#######################################################

# Convert the files created using ray trace in blender
python3 convert_samples_to_frequency_domain.py $folder/wave_samples.json $tmp_folder_samples/height_frequencies.json 
python3 convert_samples_to_frequency_domain.py $folder/wave_normals_x.json $tmp_folder_samples/wave_normals_x_frequencies.json 
python3 convert_samples_to_frequency_domain.py $folder/wave_normals_y.json $tmp_folder_samples/wave_normals_y_frequencies.json
python3 convert_samples_to_frequency_domain.py $folder/wave_normals_z.json $tmp_folder_samples/wave_normals_z_frequencies.json

node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/height_frequencies.json $folder/height_frequencies_struct.json $folder/height_frequencies_struct_metadata.json
node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/wave_normals_x_frequencies.json $folder/wave_normals_x_frequencies_struct.json $folder/wave_normals_x_frequencies_struct_metadata.json
node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/wave_normals_y_frequencies.json $folder/wave_normals_y_frequencies_struct.json $folder/wave_normals_y_frequencies_struct_metadata.json
node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/wave_normals_z_frequencies.json $folder/wave_normals_z_frequencies_struct.json $folder/wave_normals_z_frequencies_struct_metadata.json

# # Convert the frequency domain files to UE4 datatable format
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/x_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_x_frequencies_struct.json $folder/velocity_x_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/y_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_y_frequencies_struct.json $folder/velocity_y_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/z_frequencies.json /hdd/gone_surfing_exports/medium_wave_left/velocity_z_frequencies_struct.json $folder/velocity_z_frequencies_struct_metadata.json
