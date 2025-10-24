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

# Normal-based resolution thresholds (FR-31)
# Resolution is determined by the steepness of the normal (angle from vertical)
# cos(angle_from_vertical) = abs(normal.z)
low_res_threshold = 0.95  # Close to vertical (< ~18 degrees) - use low resolution (2x step)
medium_res_threshold = 0.7  # Moderate slope (< ~45 degrees) - use medium resolution (1x step)
# Steeper than medium_res_threshold - use high resolution (0.5x step)

# Steep normal threshold for sideways ray casting (FR-18)
steep_normal_threshold = 0.866  # cos(30 degrees) - angles steeper than 30 degrees from vertical
# Sideways ray casting directions (FR-26): can include '-x', 'x', '-y', 'y'
steep_ray_directions = ['x', '-x', 'y', '-y']  # Configurable list of directions

# Maximum scale limit for all samples (FR-17, FR-20)
max_scale = 4

# Minimum cosine between normal and ray direction to avoid near-perpendicular samples (FR-30)
# Samples with cos < this value will be skipped to prevent excessively large scales
min_cos_trace = 0.6  # 50 degrees from perpendicular, limits scale to 4.0 before max_scale clamp

# Arrays to store all frames by direction (FR-32)
frames_data_by_direction = {
    'vertical': [],
    'x': [],
    '-x': [],
    'y': [],
    '-y': []
}

# Statistics tracking (FR-10)
total_samples_written = 0
total_samples_skipped = 0
# Track samples per resolution
samples_low_res = 0
samples_medium_res = 0
samples_high_res = 0

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
    # FR-32: Separate data structures for each ray direction
    frame_data_by_direction = {
        'vertical': {
            "Name": f"Frame_{frame}",
            "Positions": [],
            "Normals": [],
            "Scales": []
        },
        'x': {
            "Name": f"Frame_{frame}",
            "Positions": [],
            "Normals": [],
            "Scales": []
        },
        '-x': {
            "Name": f"Frame_{frame}",
            "Positions": [],
            "Normals": [],
            "Scales": []
        },
        'y': {
            "Name": f"Frame_{frame}",
            "Positions": [],
            "Normals": [],
            "Scales": []
        },
        '-y': {
            "Name": f"Frame_{frame}",
            "Positions": [],
            "Normals": [],
            "Scales": []
        }
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

    # FR-18, FR-23, FR-26: Process steep normals with sideways ray casting from multiple directions
    steep_samples_processed = set()  # Track which grid positions have steep samples

    for direction in steep_ray_directions:
        if direction == 'x':
            # Ray casting in +X direction (left to right)
            frame_data = frame_data_by_direction['x']  # FR-32: Use direction-specific data
            # FR-28: Use high resolution for steep sampling (step/2)
            high_res_step = step / 2
            for y in range(int(y_length / high_res_step)):
                for z_pos in range(-5, 105, 1):  # Scan through height range
                    ray_y = start_trace_y + high_res_step * y
                    ray_begin = Vector((-60, ray_y, z_pos))
                    ray_end = Vector((100, ray_y, z_pos))
                    ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
                    ray_direction_vec = ray_end - ray_begin
                    ray_direction_vec.normalize()
                    hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction_vec)

                    if hit and is_steep_normal(normals):
                        normals.normalize()
                        location_world = target_object.matrix_world @ location
                        # Transform normal to world space
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        # FR-28: Steep sampling always uses high resolution (step/2)
                        current_step = step / 2

                        # FR-30: Skip samples too perpendicular to ray direction
                        cos_trace = abs(normals_world.dot(ray_direction_vec))
                        if cos_trace < min_cos_trace:
                            continue  # Skip this sample

                        frame_data["Positions"].append({
                            "X": float(location_world.x),
                            "Y": float(location_world.y),
                            "Z": float(location_world.z)
                        })
                        frame_data["Normals"].append({
                            "X": float(normals_world.x),
                            "Y": float(normals_world.y),
                            "Z": float(normals_world.z)
                        })
                        # FR-19, FR-20, FR-28, FR-29: Calculate scale for steep samples
                        # Use cos between normal and trace direction (not z-axis)
                        # cos_trace already calculated above using normals_world
                        normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                        step_scale = 0.5  # Always high-res: current_step / step = (step/2) / step = 0.5
                        combined_scale = step_scale * normal_scale
                        combined_scale = min(combined_scale, max_scale)  # FR-20
                        frame_data["Scales"].append(combined_scale)
                        total_samples_written += 1
                        samples_high_res += 1  # FR-10, FR-28: Steep samples always high-res

                        # Mark grid position as having steep sample
                        grid_x = int((location_world.x - start_trace_x) / step)
                        grid_y = int((location_world.y - start_trace_y) / step)
                        steep_samples_processed.add((grid_x, grid_y))

        elif direction == '-x':
            # Ray casting in -X direction (right to left)
            frame_data = frame_data_by_direction['-x']  # FR-32: Use direction-specific data
            # FR-28: Use high resolution for steep sampling (step/2)
            high_res_step = step / 2
            for y in range(int(y_length / high_res_step)):
                for z_pos in range(-5, 105, 1):  # Scan through height range
                    ray_y = start_trace_y + high_res_step * y
                    ray_begin = Vector((100, ray_y, z_pos))
                    ray_end = Vector((-60, ray_y, z_pos))
                    ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
                    ray_direction_vec = ray_end - ray_begin
                    ray_direction_vec.normalize()
                    hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction_vec)

                    if hit and is_steep_normal(normals):
                        normals.normalize()
                        location_world = target_object.matrix_world @ location
                        # Transform normal to world space
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        # FR-28: Steep sampling always uses high resolution (step/2)
                        current_step = step / 2

                        # FR-30: Skip samples too perpendicular to ray direction
                        cos_trace = abs(normals_world.dot(ray_direction_vec))
                        if cos_trace < min_cos_trace:
                            continue  # Skip this sample

                        frame_data["Positions"].append({
                            "X": float(location_world.x),
                            "Y": float(location_world.y),
                            "Z": float(location_world.z)
                        })
                        frame_data["Normals"].append({
                            "X": float(normals_world.x),
                            "Y": float(normals_world.y),
                            "Z": float(normals_world.z)
                        })
                        # FR-19, FR-20, FR-28, FR-29: Calculate scale for steep samples
                        # Use cos between normal and trace direction (not z-axis)
                        # cos_trace already calculated above using normals_world
                        normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                        step_scale = 0.5  # Always high-res: current_step / step = (step/2) / step = 0.5
                        combined_scale = step_scale * normal_scale
                        combined_scale = min(combined_scale, max_scale)  # FR-20
                        frame_data["Scales"].append(combined_scale)
                        total_samples_written += 1
                        samples_high_res += 1  # FR-10, FR-28: Steep samples always high-res

                        # Mark grid position as having steep sample
                        grid_x = int((location_world.x - start_trace_x) / step)
                        grid_y = int((location_world.y - start_trace_y) / step)
                        steep_samples_processed.add((grid_x, grid_y))

        elif direction == 'y':
            # Ray casting in +Y direction (back to front)
            frame_data = frame_data_by_direction['y']  # FR-32: Use direction-specific data
            # FR-28: Use high resolution for steep sampling (step/2)
            high_res_step = step / 2
            for x in range(int(x_length / high_res_step)):
                for z_pos in range(-5, 105, 1):  # Scan through height range
                    ray_x = start_trace_x + high_res_step * x
                    ray_begin = Vector((ray_x, -280, z_pos))
                    ray_end = Vector((ray_x, 170, z_pos))
                    ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
                    ray_direction_vec = ray_end - ray_begin
                    ray_direction_vec.normalize()
                    hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction_vec)

                    if hit and is_steep_normal(normals):
                        normals.normalize()
                        location_world = target_object.matrix_world @ location
                        # Transform normal to world space
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        # FR-28: Steep sampling always uses high resolution (step/2)
                        current_step = step / 2

                        # FR-30: Skip samples too perpendicular to ray direction
                        cos_trace = abs(normals_world.dot(ray_direction_vec))
                        if cos_trace < min_cos_trace:
                            continue  # Skip this sample

                        frame_data["Positions"].append({
                            "X": float(location_world.x),
                            "Y": float(location_world.y),
                            "Z": float(location_world.z)
                        })
                        frame_data["Normals"].append({
                            "X": float(normals_world.x),
                            "Y": float(normals_world.y),
                            "Z": float(normals_world.z)
                        })
                        # FR-19, FR-20, FR-28, FR-29: Calculate scale for steep samples
                        # Use cos between normal and trace direction (not z-axis)
                        # cos_trace already calculated above using normals_world
                        normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                        step_scale = 0.5  # Always high-res: current_step / step = (step/2) / step = 0.5
                        combined_scale = step_scale * normal_scale
                        combined_scale = min(combined_scale, max_scale)  # FR-20
                        frame_data["Scales"].append(combined_scale)
                        total_samples_written += 1
                        samples_high_res += 1  # FR-10, FR-28: Steep samples always high-res

                        # Mark grid position as having steep sample
                        grid_x = int((location_world.x - start_trace_x) / step)
                        grid_y = int((location_world.y - start_trace_y) / step)
                        steep_samples_processed.add((grid_x, grid_y))

        elif direction == '-y':
            # Ray casting in -Y direction (front to back)
            frame_data = frame_data_by_direction['-y']  # FR-32: Use direction-specific data
            # FR-28: Use high resolution for steep sampling (step/2)
            high_res_step = step / 2
            for x in range(int(x_length / high_res_step)):
                for z_pos in range(-5, 105, 1):  # Scan through height range
                    ray_x = start_trace_x + high_res_step * x
                    ray_begin = Vector((ray_x, 170, z_pos))
                    ray_end = Vector((ray_x, -280, z_pos))
                    ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
                    ray_direction_vec = ray_end - ray_begin
                    ray_direction_vec.normalize()
                    hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction_vec)

                    if hit and is_steep_normal(normals):
                        normals.normalize()
                        location_world = target_object.matrix_world @ location
                        # Transform normal to world space
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        # FR-28: Steep sampling always uses high resolution (step/2)
                        current_step = step / 2

                        # FR-30: Skip samples too perpendicular to ray direction
                        cos_trace = abs(normals_world.dot(ray_direction_vec))
                        if cos_trace < min_cos_trace:
                            continue  # Skip this sample

                        frame_data["Positions"].append({
                            "X": float(location_world.x),
                            "Y": float(location_world.y),
                            "Z": float(location_world.z)
                        })
                        frame_data["Normals"].append({
                            "X": float(normals_world.x),
                            "Y": float(normals_world.y),
                            "Z": float(normals_world.z)
                        })
                        # FR-19, FR-20, FR-28, FR-29: Calculate scale for steep samples
                        # Use cos between normal and trace direction (not z-axis)
                        # cos_trace already calculated above using normals_world
                        normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                        step_scale = 0.5  # Always high-res: current_step / step = (step/2) / step = 0.5
                        combined_scale = step_scale * normal_scale
                        combined_scale = min(combined_scale, max_scale)  # FR-20
                        frame_data["Scales"].append(combined_scale)
                        total_samples_written += 1
                        samples_high_res += 1  # FR-10, FR-28: Steep samples always high-res

                        # Mark grid position as having steep sample
                        grid_x = int((location.x - start_trace_x) / step)
                        grid_y = int((location.y - start_trace_y) / step)
                        steep_samples_processed.add((grid_x, grid_y))

    # Second pass: process vertical samples (FR-31, FR-32)
    frame_data = frame_data_by_direction['vertical']  # FR-32: Use direction-specific data for vertical rays
    for x in range(int(x_length / step)):
        for y in range(int(y_length / step)):
            raycast_data = all_raycasts[x][y]
            location = raycast_data['location']
            normals = raycast_data['normals']

            # FR-18: Skip if this sample has a steep normal (handled by sideways ray casting)
            if is_steep_normal(normals):
                continue

            current_height = location.z

            # Convert location to world coordinates for boundary check
            location_world = target_object.matrix_world @ location

            # Check if point is in high resolution boundary
            in_high_res_boundary = is_point_in_boundary(location_world)

            # FR-16: Check if sample is in the highest 1%
            is_top_1_percent = current_height >= height_threshold_top_1_percent

            # FR-31: Determine resolution based on normal steepness
            # cos(angle_from_vertical) = abs(normal.z)
            normal_z_abs = abs(normals.z)

            # Determine required resolution based on normal steepness
            if normal_z_abs >= low_res_threshold:
                # Nearly flat surface - low resolution
                required_resolution = 'low'  # 2x step
            elif normal_z_abs >= medium_res_threshold:
                # Moderate slope - medium resolution
                required_resolution = 'medium'  # 1x step
            else:
                # Steep slope - high resolution
                required_resolution = 'high'  # 0.5x step

            # FR-11: Within high resolution boundary, always use at least medium resolution
            if in_high_res_boundary and required_resolution == 'low':
                required_resolution = 'medium'

            # FR-16, FR-33: Highest 1% use extra-high resolution
            if is_top_1_percent:
                required_resolution = 'extra_high'

            # FR-34: Check if we need boundary samples to prevent gaps
            # Check neighbors to see if there's a resolution change
            needs_boundary_sample = False
            if required_resolution == 'low':
                # Check if any neighbors use higher resolution
                for nx in [max(0, x-1), min(int(x_length/step)-1, x+1)]:
                    for ny in [max(0, y-1), min(int(y_length/step)-1, y+1)]:
                        if nx == x and ny == y:
                            continue
                        neighbor_raycast = all_raycasts[nx][ny]
                        neighbor_normals = neighbor_raycast['normals']
                        if is_steep_normal(neighbor_normals):
                            continue
                        neighbor_height = neighbor_raycast['location'].z
                        neighbor_world = target_object.matrix_world @ neighbor_raycast['location']
                        neighbor_in_boundary = is_point_in_boundary(neighbor_world)
                        neighbor_is_top = neighbor_height >= height_threshold_top_1_percent
                        neighbor_z_abs = abs(neighbor_normals.z)

                        # Determine neighbor resolution
                        if neighbor_z_abs >= low_res_threshold:
                            neighbor_res = 'low'
                        elif neighbor_z_abs >= medium_res_threshold:
                            neighbor_res = 'medium'
                        else:
                            neighbor_res = 'high'

                        if neighbor_in_boundary and neighbor_res == 'low':
                            neighbor_res = 'medium'
                        if neighbor_is_top:
                            neighbor_res = 'extra_high'

                        # If neighbor uses higher resolution, we need boundary samples
                        if neighbor_res != 'low':
                            needs_boundary_sample = True
                            break
                    if needs_boundary_sample:
                        break

            # Check if this sample aligns with the current grid position
            if required_resolution == 'low' and not needs_boundary_sample:
                # Low res: only sample every other grid point
                if x % 2 != 0 or y % 2 != 0:
                    continue
            elif required_resolution == 'low' and needs_boundary_sample:
                # FR-34: Use medium resolution at boundaries to prevent gaps
                required_resolution = 'medium'

            # Determine the current step size based on required resolution
            # FR-31, FR-33: Resolution determined by normal steepness or top 1%
            if required_resolution == 'extra_high':
                # FR-33: Extra high resolution for top 1% - even denser sampling
                # Sample at step/4 resolution (16 samples per grid cell)
                extra_high_step = step / 4
                eighth_step = step / 8
                for dx in [-3*eighth_step, -eighth_step, eighth_step, 3*eighth_step]:
                    for dy in [-3*eighth_step, -eighth_step, eighth_step, 3*eighth_step]:
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
                            # FR-30: Skip samples too perpendicular to ray direction
                            cos_trace = abs(norm.dot(ray_direction))
                            if cos_trace < min_cos_trace:
                                continue  # Skip this sample

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
                            # FR-33: Extra high resolution scale
                            # Use cos between normal and trace direction
                            normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                            step_scale = 0.25  # extra_high_step / step = (step/4) / step = 0.25
                            combined_scale = step_scale * normal_scale
                            combined_scale = min(combined_scale, max_scale)
                            frame_data["Scales"].append(combined_scale)
                            total_samples_written += 1
                            samples_high_res += 1  # FR-10: Track as high resolution
                total_samples_skipped += 1  # Count original sample as skipped
            elif required_resolution == 'high':
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
                            # FR-30: Skip samples too perpendicular to ray direction
                            cos_trace = abs(norm.dot(ray_direction))
                            if cos_trace < min_cos_trace:
                                continue  # Skip this sample

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
                            # FR-13, FR-14, FR-29: Store step size scale multiplied by normal-based scale
                            # Use cos between normal and trace direction
                            normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                            step_scale = 0.5  # half_step / step
                            combined_scale = step_scale * normal_scale
                            # FR-17: Limit scale to maximum of 3.0
                            combined_scale = min(combined_scale, max_scale)
                            frame_data["Scales"].append(combined_scale)
                            total_samples_written += 1
                            samples_high_res += 1  # FR-10: Track high resolution samples
                total_samples_skipped += 1  # Count original sample as skipped
            else:
                # Medium or low resolution - sample at current grid position
                # FR-31: Resolution determined by normal steepness
                if required_resolution == 'low':
                    current_step_scale = 2.0  # Double step size for low resolution
                else:  # medium resolution
                    current_step_scale = 1.0  # Normal step size

                # FR-30: Check if sample is too perpendicular to ray direction
                # Use cos between normal and trace direction (downward for vertical rays)
                vertical_ray_direction = Vector((0, 0, -1))
                cos_trace = abs(normals.dot(vertical_ray_direction))
                if cos_trace < min_cos_trace:
                    continue  # Skip this sample

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
                # FR-13, FR-14, FR-22, FR-29: Store step size scale multiplied by normal-based scale
                normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                combined_scale = current_step_scale * normal_scale
                combined_scale = min(combined_scale, max_scale)
                frame_data["Scales"].append(combined_scale)
                total_samples_written += 1
                # FR-10: Track samples by resolution
                if required_resolution == 'low':
                    samples_low_res += 1
                else:  # medium
                    samples_medium_res += 1

    # FR-32: Append frame data for each direction
    for direction in ['vertical', 'x', '-x', 'y', '-y']:
        frames_data_by_direction[direction].append(frame_data_by_direction[direction])
    print(f"Processed frame {frame}")

# FR-32: Write separate output files for each direction
for direction in ['vertical', 'x', '-x', 'y', '-y']:
    # Create filename based on direction
    direction_filename = f"ocean-points-data-{direction}.json"
    output_filepath = os.path.join(output_directory, direction_filename)
    with open(output_filepath, "w") as file:
        json.dump(frames_data_by_direction[direction], file, indent=2)
    print(f"Written {len(frames_data_by_direction[direction])} frames to {direction_filename}")

# Print statistics (FR-10)
total_samples = total_samples_written + total_samples_skipped
skip_percentage = (total_samples_skipped / total_samples * 100) if total_samples > 0 else 0

print("Export completed!")
print(f"Total samples written: {total_samples_written}")
print(f"  - Low resolution (2x step): {samples_low_res}")
print(f"  - Medium resolution (1x step): {samples_medium_res}")
print(f"  - High resolution (0.5x step): {samples_high_res}")
print(f"Samples skipped: {total_samples_skipped}")
print(f"Percentage skipped: {skip_percentage:.2f}%")
