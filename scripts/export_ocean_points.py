import os
import json
import bpy
import math
from mathutils import Vector

target_object = bpy.data.objects['fluid_surface']
start_frame = 752
end_frame = 1325
# end_frame = 754
scn = bpy.context.scene
step = 4 # Distance between traced points
# output_directory = "/home/emil/workspace/GoneSurfingScripts"
output_directory = "/hdd/gone_surfing_exports/medium_wave_left"
output_filename = "ocean-points-data.json"

# Array to store all frames
frames_data = []

for frame in range(start_frame, end_frame + 1):
    scn.frame_set(frame)
    frame_data = {
        "Name": f"Frame_{frame}",
        "Positions": [],
        "Normals": [],
        "Scales": []
    }
    for x in range(int(160 / step)):
        for y in range(int(450 / step)):
            start_trace_x = -60
            start_trace_y = -280
            ray_begin = Vector((start_trace_x + step * x, start_trace_y + step * y, 100))
            ray_end = Vector((start_trace_x + step * x, start_trace_y + step * y, -100))
            ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
            ray_direction = ray_end - ray_begin
            ray_direction.normalize()
            hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)
            normals.normalize()

            # Calculate cosine of angle between normal and Z-axis (0, 0, 1)
            # This gives you how "upward" the surface is (1.0 = flat horizontal, 0.0 = vertical)
            z_axis = Vector((0, 0, 1))
            cos_z = normals.dot(z_axis)

            frame_data["Positions"].append({
                "X": float(location.x),
                "Y": float(location.y),
                "Z": float(location.z)
            })

            # Convert normal vector to rotation angles in degrees
            # X = Roll (rotation around X-axis)
            # Y = Pitch (rotation around Y-axis)
            # Z = Yaw (rotation around Z-axis)

            # Yaw (Z): rotation around Z-axis (horizontal angle)
            yaw = math.atan2(normals.y, normals.x) * 180.0 / math.pi

            # Pitch (Y): rotation around Y-axis (up/down tilt)
            horizontal_length = math.sqrt(normals.x**2 + normals.y**2)
            pitch = math.atan2(normals.z, horizontal_length) * 180.0 / math.pi

            # Roll (X): For a surface normal, roll is typically 0
            roll = 0.0

            frame_data["Normals"].append({
                "X": float(roll),   # Roll
                "Y": float(pitch),  # Pitch
                "Z": float(yaw)     # Yaw
            })
            scale = 1
            if(cos_z != 0):
                scale = 1/float(cos_z)
            else:
                scale = 10000
            frame_data["Scales"].append(scale)

    frames_data.append(frame_data)
    print("Processed frame:", frame)
output_filepath=os.path.join(output_directory,output_filename)
with open(output_filepath, "w") as file:
    json.dump(frames_data, file, indent=2)
print("Export completed successfully.")
