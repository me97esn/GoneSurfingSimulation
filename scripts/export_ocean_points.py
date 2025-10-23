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

# Height difference threshold for high res samples (FR-9)
max_height_difference = 0.12  # Configurable threshold in units

# Steep normal threshold for sideways ray casting (FR-18)
steep_normal_threshold = 0.5  # cos(60 degrees) - angles steeper than 60 degrees from vertical
# Sideways ray casting direction: 'x' for sideways, 'y' for front-to-back (FR-18)
steep_ray_direction = 'y'  # Configurable: 'x' or 'y'

# Maximum scale limit for all samples (FR-17, FR-20)
max_scale = 3.0

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

def is_steep_normal(normal):
    """Check if normal is steep enough for sideways ray casting (FR-18)"""
    z_axis = Vector((0, 0, 1))
    cos_angle = abs(normal.dot(z_axis))
    return cos_angle < steep_normal_threshold

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

    # Calculate 99th percentile for FR-16 (highest 1% threshold)
    all_heights = []
    for row in all_raycasts:
        for raycast in row:
            if raycast['hit']:
                all_heights.append(raycast['location'].z)
    all_heights.sort()
    percentile_99_index = int(len(all_heights) * 0.99)
    height_threshold_top_1_percent = all_heights[percentile_99_index] if all_heights else float('inf')

    # FR-18 & FR-23: Process steep normals with sideways ray casting over entire model
    steep_samples_processed = set()  # Track which grid positions have steep samples
    if steep_ray_direction == 'x':
        # Ray casting in X direction (sideways)
        for y in range(int(y_length / step)):
            for z_pos in range(-5, 105, 1):  # Scan through height range
                ray_y = start_trace_y + step * y
                ray_begin = Vector((-60, ray_y, z_pos))
                ray_end = Vector((100, ray_y, z_pos))
                ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
                ray_direction_vec = ray_end - ray_begin
                ray_direction_vec.normalize()
                hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction_vec)

                if hit and is_steep_normal(normals):
                    normals.normalize()
                    location_world = target_object.matrix_world @ location

                    # Check if this is in high-res boundary or top 1% for high-res sampling (FR-23)
                    is_in_boundary = is_point_in_boundary(location_world)
                    is_top_1 = location.z >= height_threshold_top_1_percent
                    current_step = step / 2 if (is_in_boundary or is_top_1) else step

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
                    # FR-19, FR-20: Calculate scale for steep samples
                    z_axis = Vector((0, 0, 1))
                    cos_z = normals.dot(z_axis)
                    normal_scale = 1 / float(abs(cos_z)) if cos_z != 0 else max_scale
                    step_scale = current_step / step
                    combined_scale = step_scale * normal_scale
                    combined_scale = min(combined_scale, max_scale)  # FR-20
                    frame_data["Scales"].append(combined_scale)
                    total_samples_written += 1

                    # Mark grid position as having steep sample
                    grid_x = int((location.x - start_trace_x) / step)
                    grid_y = int((location.y - start_trace_y) / step)
                    steep_samples_processed.add((grid_x, grid_y))
    else:  # steep_ray_direction == 'y'
        # Ray casting in Y direction (front-to-back)
        for x in range(int(x_length / step)):
            for z_pos in range(-5, 105, 1):  # Scan through height range
                ray_x = start_trace_x + step * x
                ray_begin = Vector((ray_x, -280, z_pos))
                ray_end = Vector((ray_x, 170, z_pos))
                ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
                ray_direction_vec = ray_end - ray_begin
                ray_direction_vec.normalize()
                hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction_vec)

                if hit and is_steep_normal(normals):
                    normals.normalize()
                    location_world = target_object.matrix_world @ location

                    # Check if this is in high-res boundary or top 1% for high-res sampling (FR-23)
                    is_in_boundary = is_point_in_boundary(location_world)
                    is_top_1 = location.z >= height_threshold_top_1_percent
                    current_step = step / 2 if (is_in_boundary or is_top_1) else step

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
                    # FR-19, FR-20: Calculate scale for steep samples
                    z_axis = Vector((0, 0, 1))
                    cos_z = normals.dot(z_axis)
                    normal_scale = 1 / float(abs(cos_z)) if cos_z != 0 else max_scale
                    step_scale = current_step / step
                    combined_scale = step_scale * normal_scale
                    combined_scale = min(combined_scale, max_scale)  # FR-20
                    frame_data["Scales"].append(combined_scale)
                    total_samples_written += 1

                    # Mark grid position as having steep sample
                    grid_x = int((location.x - start_trace_x) / step)
                    grid_y = int((location.y - start_trace_y) / step)
                    steep_samples_processed.add((grid_x, grid_y))

    # Second pass: check height differences and handle samples (FR-9, FR-12, FR-13, FR-16)
    for x in range(int(x_length / step)):
        for y in range(int(y_length / step)):
            raycast_data = all_raycasts[x][y]
            location = raycast_data['location']
            normals = raycast_data['normals']

            # FR-18: Skip if this sample has a steep normal (handled by sideways ray casting)
            if is_steep_normal(normals):
                continue

            current_height = location.z
            needs_high_res = False

            # Convert location to world coordinates for boundary check
            location_world = target_object.matrix_world @ location

            # Check if point is in high resolution boundary
            in_high_res_boundary = is_point_in_boundary(location_world)

            # FR-16: Check if sample is in the highest 1%
            is_top_1_percent = current_height >= height_threshold_top_1_percent

            # FR-21: Skip this sample if outside boundary (will be handled by low-res sampling)
            # But still process samples at boundary intersections to maintain coverage
            if not in_high_res_boundary and not is_top_1_percent:
                # Check if this position aligns with the lower resolution grid (double step size)
                if x % 2 != 0 or y % 2 != 0:
                    continue  # Skip this sample for now, will be handled by lower-res logic

            # Only apply height difference checking within high resolution boundary (FR-11)
            if in_high_res_boundary:
                # Check height difference with previous sample in X axis (FR-9)
                if x > 0:
                    prev_height = all_raycasts[x - 1][y]['location'].z
                    if abs(current_height - prev_height) > max_height_difference:
                        needs_high_res = True

                # Check height difference with next sample in X axis (FR-9)
                if not needs_high_res and x < int(x_length / step) - 1:
                    next_height = all_raycasts[x + 1][y]['location'].z
                    if abs(current_height - next_height) > max_height_difference:
                        needs_high_res = True

            # FR-16: Also use high resolution for highest 1% of samples
            if is_top_1_percent:
                needs_high_res = True

            # Determine the current step size based on location and conditions
            # FR-12 & FR-15: Resample with half step size for high-difference areas
            if needs_high_res:
                # Sample with half step in both x and y directions
                # FR-15: Center the high-res grid so blocks align perfectly with low-res grid
                half_step = step / 2
                quarter_step = step / 4
                for dx in [-quarter_step, quarter_step]:
                    for dy in [-quarter_step, quarter_step]:
                        ray_x = start_trace_x + step * x + dx
                        ray_y = start_trace_y + step * y + dy
                        ray_begin = Vector((ray_x, ray_y, 100))
                        ray_end = Vector((ray_x, ray_y, -100))
                        ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
                        ray_direction = ray_end - ray_begin
                        ray_direction.normalize()
                        hit, loc, norm, index = target_object.ray_cast(ray_begin_local, ray_direction)

                        if hit:
                            norm.normalize()
                            frame_data["Positions"].append({
                                "X": float(loc.x),
                                "Y": float(loc.y),
                                "Z": float(loc.z)
                            })
                            frame_data["Normals"].append({
                                "X": float(norm.x),
                                "Y": float(norm.y),
                                "Z": float(norm.z)
                            })
                            # FR-13 & FR-14: Store step size scale multiplied by normal-based scale
                            z_axis = Vector((0, 0, 1))
                            cos_z = norm.dot(z_axis)
                            normal_scale = 1 / float(cos_z) if cos_z != 0 else max_scale
                            step_scale = 0.5  # half_step / step
                            combined_scale = step_scale * normal_scale
                            # FR-17: Limit scale to maximum of 3.0
                            combined_scale = min(combined_scale, max_scale)
                            frame_data["Scales"].append(combined_scale)
                            total_samples_written += 1
                total_samples_skipped += 1  # Count original sample as skipped
            else:
                # Determine step scale based on location
                # FR-21 & FR-22: Lower resolution outside boundary
                if not in_high_res_boundary and not is_top_1_percent:
                    current_step_scale = 2.0  # Double step size outside boundary
                else:
                    current_step_scale = 1.0  # Normal step size

                # Add the sample with appropriate step size
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
                # FR-13, FR-14, FR-22: Store step size scale multiplied by normal-based scale
                z_axis = Vector((0, 0, 1))
                cos_z = normals.dot(z_axis)
                normal_scale = 1 / float(cos_z) if cos_z != 0 else max_scale
                combined_scale = current_step_scale * normal_scale
                # FR-17: Limit scale to maximum of 3.0
                combined_scale = min(combined_scale, max_scale)
                frame_data["Scales"].append(combined_scale)
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
