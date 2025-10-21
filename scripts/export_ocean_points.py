import os
import json
import bpy
from mathutils import Vector

target_object = bpy.data.objects['fluid_surface']
# High resolution boundary mesh (FR-11)
high_res_boundary = bpy.data.objects.get('High_resolution_boundary')
start_frame = 752
end_frame = 1325
# end_frame = 754
scn = bpy.context.scene
step = 4
# output_directory = "/home/emil/workspace/GoneSurfingScripts"
output_directory = "/hdd/gone_surfing_exports/medium_wave_left"
output_filename = "ocean-points-data.json"

# Height difference threshold for skipping samples (FR-9)
max_height_difference = 0.2  # Configurable threshold in units

# Array to store all frames
frames_data = []

# Statistics tracking (FR-10)
total_samples_written = 0
total_samples_skipped = 0

def is_point_in_boundary(point):
    """Check if a point is within the High_resolution_boundary mesh (FR-11)"""
    if high_res_boundary is None:
        return False

    # Convert point to local space of the boundary mesh
    point_local = high_res_boundary.matrix_world.inverted() @ point

    # Use ray casting to determine if point is inside the mesh
    # Cast a ray from the point in the +Z direction
    ray_direction = Vector((0, 0, 1))
    hit, location, normal, index = high_res_boundary.ray_cast(point_local, ray_direction)

    # If we hit the mesh, we're inside if the normal points away from our direction
    if hit:
        # Check if we're below the hit point (inside the mesh)
        if point_local.z < location.z:
            return True

    # Also cast in -Z direction to be more robust
    ray_direction = Vector((0, 0, -1))
    hit, location, normal, index = high_res_boundary.ray_cast(point_local, ray_direction)
    if hit:
        if point_local.z > location.z:
            return True

    return False

for frame in range(start_frame, end_frame + 1):
    scn.frame_set(frame)
    frame_data = {
        "Name": f"Frame_{frame}",
        "Positions": [],
        "Normals": [],
        "Scales": []
    }

    start_trace_x = -60
    start_trace_y = -280
    x_length = 160
    y_length = 450

    # First pass: collect all raycast data for this frame
    all_raycasts = []
    for x in range(int(x_length / step)):
        row_raycasts = []
        for y in range(int(y_length / step)):
            ray_begin = Vector((start_trace_x + step * x, start_trace_y + step * y, 100))
            ray_end = Vector((start_trace_x + step * x, start_trace_y + step * y, -100))
            ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
            ray_direction = ray_end - ray_begin
            ray_direction.normalize()
            hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)
            normals.normalize()
            row_raycasts.append({
                'location': location,
                'normals': normals,
                'hit': hit
            })
        all_raycasts.append(row_raycasts)

    # Second pass: check height differences and add valid samples (FR-9)
    for x in range(int(x_length / step)):
        for y in range(int(y_length / step)):
            raycast_data = all_raycasts[x][y]
            location = raycast_data['location']
            normals = raycast_data['normals']
            current_height = location.z
            skip_sample = False

            # Convert location to world coordinates for boundary check
            location_world = target_object.matrix_world @ location

            # Only apply height difference checking within high resolution boundary (FR-11)
            if is_point_in_boundary(location_world):
                # Check height difference with previous sample in X axis (FR-9)
                if x > 0:
                    prev_height = all_raycasts[x - 1][y]['location'].z
                    if abs(current_height - prev_height) > max_height_difference:
                        skip_sample = True

                # Check height difference with next sample in X axis (FR-9)
                if not skip_sample and x < int(x_length / step) - 1:
                    next_height = all_raycasts[x + 1][y]['location'].z
                    if abs(current_height - next_height) > max_height_difference:
                        skip_sample = True

            if skip_sample:
                total_samples_skipped += 1
                continue

            # Calculate cosine of angle between normal and Z-axis (0, 0, 1)
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
            if cos_z != 0:
                scale = 1 / float(cos_z)
            else:
                scale = 10000
            frame_data["Scales"].append(scale)
            total_samples_written += 1

    frames_data.append(frame_data)
    print(f"Processed frame {frame}")
output_filepath = os.path.join(output_directory, output_filename)
with open(output_filepath, "w") as file:
    json.dump(frames_data, file, indent=2)

# Print statistics (FR-10)
total_samples = total_samples_written + total_samples_skipped
skip_percentage = (total_samples_skipped / total_samples * 100) if total_samples > 0 else 0

print("Export completed!")
print(f"Samples written: {total_samples_written}")
print(f"Samples skipped: {total_samples_skipped}")
print(f"Percentage skipped: {skip_percentage:.2f}%")
