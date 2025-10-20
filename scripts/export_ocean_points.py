import os
import json
import bpy
from mathutils import Vector
import math

target_object = bpy.data.objects['fluid_surface']
start_frame = 752
end_frame = 1325
# end_frame = 754
scn = bpy.context.scene
step = 4
# output_directory = "/home/emil/workspace/GoneSurfingScripts"
output_directory = "/hdd/gone_surfing_exports/medium_wave_left"
output_filename = "ocean-points-data.json"

# Array to store all frames
frames_data = []

def perform_raycast(x_pos, y_pos):
    """Perform a raycast at the given x, y position and return hit location"""
    ray_begin = Vector((x_pos, y_pos, 100))
    ray_end = Vector((x_pos, y_pos, -100))
    ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
    ray_direction = ray_end - ray_begin
    ray_direction.normalize()
    hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)
    return location

def calculate_normal_from_plane(center_loc, prev_loc, next_loc):
    """Calculate normal from a plane touching three points along the Y axis"""
    # Calculate the normal by creating a plane from the three points
    # The plane is rotated around the X axis (perpendicular to Y direction)

    # Vector from center to next point (in Y direction)
    vec_to_next = next_loc - center_loc
    # Vector from prev to center point (in Y direction)
    vec_from_prev = center_loc - prev_loc

    # Average the two vectors to get a direction along Y
    y_direction = (vec_to_next + vec_from_prev).normalized()

    # Create a normal that's perpendicular to the Y direction
    # and points generally upward (positive Z component)
    # The normal should be in the XZ plane (perpendicular to Y)

    # Calculate the slope in the XZ plane
    delta_y = vec_to_next.y
    delta_z = vec_to_next.z

    if abs(delta_y) > 0.0001:
        # Calculate angle of rotation around X axis
        # Normal in XZ plane perpendicular to the surface slope
        angle = math.atan2(delta_z, delta_y)
        normal = Vector((0, -math.sin(angle), math.cos(angle)))
    else:
        # If no Y movement, normal points straight up
        normal = Vector((0, 0, 1))

    normal.normalize()
    return normal

for frame in range(start_frame, end_frame + 1):
    scn.frame_set(frame)
    frame_data = {
        "Name": f"Frame_{frame}",
        "Positions": [],
        "Normals": [],
        "Scales": []
    }
    i = 0
    for x in range(int(160 / step)):
        for y in range(int(450 / step)):
            i+=1
            start_trace_x = -60
            start_trace_y = -280

            # Main raycast at current position
            current_x = start_trace_x + step * x
            current_y = start_trace_y + step * y
            location = perform_raycast(current_x, current_y)

            # Additional raycasts for normal calculation
            # Raycast halfway to previous point in Y direction
            prev_y = current_y - step / 2
            prev_location = perform_raycast(current_x, prev_y)

            # Raycast halfway to next point in Y direction
            next_y = current_y + step / 2
            next_location = perform_raycast(current_x, next_y)

            # Calculate normal from the three points
            normals = calculate_normal_from_plane(location, prev_location, next_location)

            # Calculate cosine of angle between normal and Z-axis (0, 0, 1)
            # This gives you how "upward" the surface is (1.0 = flat horizontal, 0.0 = vertical)
            z_axis = Vector((0, 0, 1))
            cos_z = normals.dot(z_axis)

            frame_data["Positions"].append({
                "X": float(location.x),
                "Y": float(location.y),
                "Z": float(location.z)
            })
            frame_data["Normals"].append({
                "X": float(normals.x),
                "Y": float(normals.y),
                "Z": float(normals.z)
            })

            scale = 1
            if(cos_z != 0):
                scale = 1/float(cos_z)
            else:
                scale = 10000
            frame_data["Scales"].append(scale)
    frames_data.append(frame_data)
    print(f"Processed frame {frame}")
output_filepath=os.path.join(output_directory,output_filename)
with open(output_filepath, "w") as file:
    json.dump(frames_data, file, indent=2)
print("Export completed!")
