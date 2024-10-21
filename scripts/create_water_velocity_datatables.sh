#! /bin/bash


# I am creating data files for wave height in two ways: one with jittery waves and one with stable waves. The jittery should only be used to help in placing the water velocities, while the stable should be used for the actual wave height. The axis are different in these two files.

folder=/hdd/gone_surfing_exports/medium_wave_left
tmp_folder=/hdd/gone_surfing_exports/medium_wave_left/tmp
tmp_folder_samples=/hdd/gone_surfing_exports/medium_wave_left/tmp_samples

# tmp_folder=/tmp/medium_wave_left_water_velocities
# tmp_folder_samples=/tmp/medium_wave_left_water_velocities_samples

mkdir -p $folder
mkdir -p $tmp_folder
mkdir -p $tmp_folder_samples

#######################################################
# Here starts the handling of sample files created in blender using flip fluids bobj files
# I can't use this for the wave height, since there are not only vertices at the surface. For fft to work,
# there should be evenly spread samples at the surface only. 
# But I can use this for the velocity data, since the velocity is only available at the surface in Flip Fluids.
#######################################################
start_frame=752
# end_frame=800
end_frame=1325
step_size=2

# Read the blur data files from blender/flip fluids, and convert them to human readable json
# Split into multiple calls since nodejs runs out of memory
# num_of_files_per_chunk=50
# for (( k = $start_frame; k < end_frame+$num_of_files_per_chunk; k+=$num_of_files_per_chunk)); do
#   local_start_frame=$k
#   local_end_frame=$((k+num_of_files_per_chunk))
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

# python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/dx-per-frame-example.json dx 50
#
# python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/dx-per-frame.json dx $step_size
# python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/dy-per-frame.json dy $step_size
# python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/dz-per-frame.json dz $step_size
# z is only used for debugging and placing the velocity data in the correct position
python3 interpolate_to_evenly_spread_samples.py $tmp_folder $tmp_folder_samples/z-per-frame.json height $step_size

# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/dx-per-frame.json $tmp_folder_samples/dx-frequencies.json 
# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/dy-per-frame.json $tmp_folder_samples/dy-frequencies.json
# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/dz-per-frame.json $tmp_folder_samples/dz-frequencies.json

# python3 convert_samples_to_same_format_as_frequencies.py $tmp_folder_samples/dx-per-frame-example.json $tmp_folder_samples/dx-samples-example-f-format.json 
# python3 convert_samples_to_same_format_as_frequencies.py $tmp_folder_samples/dx-per-frame.json $tmp_folder_samples/dx-samples.json 
# python3 convert_samples_to_same_format_as_frequencies.py $tmp_folder_samples/dy-per-frame.json $tmp_folder_samples/dy-samples.json
# python3 convert_samples_to_same_format_as_frequencies.py $tmp_folder_samples/dz-per-frame.json $tmp_folder_samples/dz-samples.json
python3 convert_samples_to_same_format_as_frequencies.py $tmp_folder_samples/z-per-frame.json $tmp_folder_samples/z-samples.json

# z is only used for debugging and placing the velocity data in the correct position
# python3 convert_samples_to_frequency_domain.py $tmp_folder_samples/z-per-frame.json $tmp_folder_samples/z-frequencies.json
#
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/dx-frequencies.json $folder/dx_frequencies_struct.json $folder/dx_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/dy-frequencies.json $folder/dy_frequencies_struct.json $folder/dy_frequencies_struct_metadata.json
# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/dz-frequencies.json $folder/dz_frequencies_struct.json $folder/dz_frequencies_struct_metadata.json
#
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/dx-frequencies.json $folder/dx_frequencies_struct.json $folder/dx_frequencies_struct_metadata.json 100
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/dy-frequencies.json $folder/dy_frequencies_struct.json $folder/dy_frequencies_struct_metadata.json 100
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/dz-frequencies.json $folder/dz_frequencies_struct.json $folder/dz_frequencies_struct_metadata.json 100

# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/dx-samples-example-f-format.json $folder/dx_samples_example_struct.json $folder/dx_samples_example_struct_metadata.json 100
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/dx-samples.json $folder/dx_samples_struct.json $folder/dx_samples_struct_metadata.json 10
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/dy-samples.json $folder/dy_samples_struct.json $folder/dy_samples_struct_metadata.json 10
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/dz-samples.json $folder/dz_samples_struct.json $folder/dz_samples_struct_metadata.json 10
node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/z-samples.json $folder/z_samples_struct_for_debugging.json $folder/z_samples_struct_metadata_for_debugging.json 10


# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/z-frequencies.json $folder/z_frequencies_for_debugging_struct.json $folder/z_frequencies_for_debugging_struct_metadata.json

#######################################################
# Here starts the handling of sample files created in blender using ray trace.
# This is used for the wave height, since the samples are evenly spread at the surface. But there is no velocity data.
# This is also used for the wave normals, since the normals are not available in the flip fluids data but available in the ray trace data. 
#######################################################


# python3 convert_samples_to_frequency_domain.py $folder/wave_samples.json $tmp_folder_samples/height_frequencies.json 
# python3 convert_samples_to_same_format_as_frequencies.py $folder/wave_samples.json $tmp_folder_samples/height_samples.json

# python3 convert_samples_to_frequency_domain.py $folder/wave_normals_x.json $tmp_folder_samples/wave_normals_x_frequencies.json 
# python3 convert_samples_to_same_format_as_frequencies.py $folder/wave_normals_x.json $tmp_folder_samples/wave_normals_x_samples.json

# python3 convert_samples_to_frequency_domain.py $folder/wave_normals_y.json $tmp_folder_samples/wave_normals_y_frequencies.json
# python3 convert_samples_to_same_format_as_frequencies.py $folder/wave_normals_y.json $tmp_folder_samples/wave_normals_y_samples.json

# python3 convert_samples_to_frequency_domain.py $folder/wave_normals_z.json $tmp_folder_samples/wave_normals_z_frequencies.json
# python3 convert_samples_to_same_format_as_frequencies.py $folder/wave_normals_z.json $tmp_folder_samples/wave_normals_z_samples.json

# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/height_frequencies.json $folder/height_frequencies_struct.json $folder/height_frequencies_struct_metadata.json
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/height_samples.json $folder/height_samples_struct.json $folder/height_samples_struct_metadata.json 100

# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/wave_normals_x_frequencies.json $folder/wave_normals_x_frequencies_struct.json $folder/wave_normals_x_frequencies_struct_metadata.json
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/wave_normals_x_samples.json $folder/wave_normals_x_samples_struct.json $folder/wave_normals_x_samples_struct_metadata.json 10

# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/wave_normals_y_frequencies.json $folder/wave_normals_y_frequencies_struct.json $folder/wave_normals_y_frequencies_struct_metadata.json
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/wave_normals_y_samples.json $folder/wave_normals_y_samples_struct.json $folder/wave_normals_y_samples_struct_metadata.json 10

# node convert_frequencies_json_to_ue4_datatable_format.js $tmp_folder_samples/wave_normals_z_frequencies.json $folder/wave_normals_z_frequencies_struct.json $folder/wave_normals_z_frequencies_struct_metadata.json
# node convert_from_frequency_format_to_ue4_datatable_format.js $tmp_folder_samples/wave_normals_z_samples.json $folder/wave_normals_z_samples_struct.json $folder/wave_normals_z_samples_struct_metadata.json 10
