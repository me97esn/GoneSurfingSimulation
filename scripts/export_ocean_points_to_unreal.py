import os
import json
from mathutils import Vector

# Configuration
target_object = bpy.data.objects['fluid_surface']
start_frame = 752
end_frame = 1325
# end_frame = 754
scn = bpy.context.scene
step = 1
# output_directory = "/home/emil/workspace/GoneSurfingScripts"
output_directory = "/hdd/gone_surfing_exports/medium_wave_left"
output_filename = "ocean-points-data.json"

# Sampling parameters
start_trace_x = -60
start_trace_y = -280
x_length = 160
y_length = 450

# Initialize the frames list
frames_data = []

print(f"Exporting ocean surface data from frame {start_frame} to {end_frame}...")

# Process each frame
for frame in range(start_frame, end_frame + 1):
    scn.frame_set(frame)

    # Frame data structure matching Unreal format
    frame_entry = {
        "Name": f"Frame_{frame}",
        "Positions": [],
        "Normals": []
    }

    # Sample all points on the surface
    for x in range(int(x_length / step)):
        for y in range(int(y_length / step)):
            # Create ray for raycasting
            ray_begin = Vector((start_trace_x + step * x, start_trace_y + step * y, 100))
            ray_end = Vector((start_trace_x + step * x, start_trace_y + step * y, -100))
            ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
            ray_direction = ray_end - ray_begin
            ray_direction.normalize()

            # Cast ray to find surface intersection
            hit, location, normal, index = target_object.ray_cast(ray_begin_local, ray_direction)

            if hit:
                # Normalize the normal vector
                normal.normalize()

                # Add position to the frame data
                frame_entry["Positions"].append({
                    "X": location.x,
                    "Y": location.y,
                    "Z": location.z
                })

                # Add normal to the frame data
                frame_entry["Normals"].append({
                    "X": normal.x,
                    "Y": normal.y,
                    "Z": normal.z
                })

    frames_data.append(frame_entry)

    # Progress indicator
    if (frame - start_frame + 1) % 10 == 0:
        print(f"Processed {frame - start_frame + 1} / {end_frame - start_frame + 1} frames")

# Write the output file
output_filepath = os.path.join(output_directory, output_filename)
with open(output_filepath, "w") as file:
    json.dump(frames_data, file, indent="\t")

print(f"Successfully written ocean points data to {output_filepath}")
print(f"Total frames: {len(frames_data)}")
print(f"Points per frame: {len(frames_data[0]['Positions']) if frames_data else 0}")
