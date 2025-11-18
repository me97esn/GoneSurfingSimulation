#! /bin/bash

folder=/hdd/gone_surfing_exports/medium_wave_left
tmp_folder=/hdd/gone_surfing_exports/medium_wave_left/tmp

mkdir -p $folder
mkdir -p $tmp_folder

#######################################################
# Here starts the handling of sample files created in blender using flip fluids bobj files
# I can't use this for the wave height, since there are not only vertices at the surface. For fft to work,
# there should be evenly spread samples at the surface only. 
# But I can use this for the velocity data, since the velocity is only available at the surface in Flip Fluids.
#######################################################
start_frame=905
end_frame=1101

# Read the blur data files from blender/flip fluids, and convert them to human readable json
# Split into multiple calls since nodejs runs out of memory
num_of_files_per_chunk=5
for (( k = $start_frame; k < end_frame+$num_of_files_per_chunk; k+=$num_of_files_per_chunk)); do
  local_start_frame=$k
  local_end_frame=$((k+num_of_files_per_chunk))
  if [ $k -gt $end_frame ]; then
    local_start_frame=$end_frame
    local_end_frame=$end_frame
  fi
  if [ $local_end_frame -gt $end_frame ]; then
    local_end_frame=$end_frame
  fi
  echo "Creating water velocity datatable for frames $local_start_frame to $local_end_frame"
  node -max-old-space-size=32768 create_water_velocity_datatable.js $tmp_folder $local_start_frame $local_end_frame
done