import os
import json
import bpy
from mathutils import Vector

target_object = bpy.data.objects['fluid_surface']
start_frame = 752
end_frame = 1325
# end_frame = 754
scn = bpy.context.scene
base_step = 4  # Base step size for medium resolution
# output_directory = "/home/emil/workspace/GoneSurfingScripts"
output_directory = "/hdd/gone_surfing_exports/medium_wave_left"
output_filename = "ocean-points-data.json"

# Steep normal threshold for sideways ray casting (FR-18, FR-38)
steep_normal_threshold = 0.866  # cos(30 degrees) - angles steeper than 30 degrees from vertical
# Sideways ray casting directions (FR-26): can include '-x', 'x', '-y', 'y'
steep_ray_directions = ['x', '-x', 'y', '-y']  # Configurable list of directions

# Maximum scale limit for all samples (FR-17, FR-20)
max_scale = 4

# Minimum cosine between normal and ray direction to avoid near-perpendicular samples (FR-30)
# Samples with cos < this value will be skipped to prevent excessively large scales
min_cos_trace = 0.6  # 50 degrees from perpendicular, limits scale to 4.0 before max_scale clamp

# FR-35: Distance-based resolution configuration
# Resolution decreases with distance from highest points
# Highest resolution at peaks, lowest at y edges
min_step_multiplier = 0.25  # Highest resolution: base_step * 0.25
max_step_multiplier = 2.0   # Lowest resolution: base_step * 2.0

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

def is_steep_normal(normal):
    """Check if normal is steep enough for sideways ray casting (FR-18, FR-38)"""
    z_axis = Vector((0, 0, 1))
    cos_angle = abs(normal.dot(z_axis))
    return cos_angle < steep_normal_threshold

def calculate_distance_based_step_multiplier(y_pos, peak_y_positions, y_length):
    """
    FR-35: Calculate step multiplier based on distance from highest peaks
    Highest resolution at peaks, gradually decreasing toward y edges
    Along the x-axis at peak height, maintain highest resolution

    Returns a step multiplier between min_step_multiplier and max_step_multiplier
    """
    if not peak_y_positions:
        # No peaks found, use maximum (lowest) resolution
        return max_step_multiplier

    # Find distance to nearest peak in y direction
    min_distance_to_peak = min(abs(y_pos - peak_y) for peak_y in peak_y_positions)

    # Normalize distances
    # At the peak: min_distance_to_peak = 0, use min_step_multiplier (highest res)
    # At edges: distance_from_edge = 0, use max_step_multiplier (lowest res)
    # Gradual transition in between

    # Use distance from peak as primary factor
    # Peak region extends to about 20% of y_length
    peak_region_size = y_length * 0.2

    if min_distance_to_peak < peak_region_size:
        # In peak region: interpolate from min to mid resolution
        t = min_distance_to_peak / peak_region_size
        step_mult = min_step_multiplier + (1.0 - min_step_multiplier) * t
    else:
        # Outside peak region: interpolate based on distance from edges
        # Distance from peak region boundary
        distance_from_peak_region = min_distance_to_peak - peak_region_size
        remaining_distance = (y_length / 2.0) - peak_region_size

        if remaining_distance > 0:
            t = min(distance_from_peak_region / remaining_distance, 1.0)
            step_mult = 1.0 + (max_step_multiplier - 1.0) * t
        else:
            step_mult = max_step_multiplier

    return step_mult

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

    # FR-35: First pass - sample at base resolution to find highest 1%
    coarse_samples = []
    coarse_step = base_step
    for x_idx in range(int(x_length / coarse_step) + 1):
        for y_idx in range(int(y_length / coarse_step) + 1):
            x_pos = start_trace_x + coarse_step * x_idx
            y_pos = start_trace_y + coarse_step * y_idx
            ray_begin = Vector((x_pos, y_pos, 100))
            ray_end = Vector((x_pos, y_pos, -100))
            ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
            ray_direction = ray_end - ray_begin
            ray_direction.normalize()
            hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)

            if hit:
                normals.normalize()
                coarse_samples.append({
                    'x_idx': x_idx,
                    'y_idx': y_idx,
                    'x_pos': x_pos,
                    'y_pos': y_pos,
                    'location': location,
                    'normals': normals,
                    'height': location.z
                })

    # Calculate 99th percentile (FR-16, FR-35)
    all_heights = [s['height'] for s in coarse_samples]
    all_heights.sort()
    percentile_99_index = int(len(all_heights) * 0.99)
    height_threshold_top_1_percent = all_heights[percentile_99_index] if all_heights else float('inf')

    # FR-35: Find y positions of highest 1% samples
    # These define the "peak line" along x-axis
    peak_y_positions = set()
    for sample in coarse_samples:
        if sample['height'] >= height_threshold_top_1_percent:
            peak_y_positions.add(sample['y_pos'])

    peak_y_positions = sorted(list(peak_y_positions))
    print(f"Frame {frame}: Found {len(peak_y_positions)} peak y-positions at threshold {height_threshold_top_1_percent:.2f}")

    # FR-18, FR-26, FR-28: Process steep normals with sideways ray casting
    frame_data = None
    for direction in steep_ray_directions:
        if direction == 'x':
            frame_data = frame_data_by_direction['x']
            # Ray casting in +X direction (left to right)
            # FR-28: Use high resolution for steep sampling
            high_res_step = base_step / 4  # FR-33: Extra high resolution for steep
            for y in range(int(y_length / high_res_step) + 1):
                for z_pos in range(-5, 105, 1):
                    ray_y = start_trace_y + high_res_step * y
                    ray_begin = Vector((-60, ray_y, z_pos))
                    ray_end = Vector((100, ray_y, z_pos))
                    ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
                    ray_direction_vec = ray_end - ray_begin
                    ray_direction_vec.normalize()
                    hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction_vec)

                    if hit and is_steep_normal(normals):  # FR-38: Only steep samples
                        normals.normalize()
                        location_world = target_object.matrix_world @ location
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        # FR-30: Skip samples too perpendicular to ray direction
                        cos_trace = abs(normals_world.dot(ray_direction_vec))
                        if cos_trace < min_cos_trace:
                            continue

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
                        # FR-29, FR-37: Calculate scale using trace direction
                        normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                        step_scale = high_res_step / base_step
                        combined_scale = step_scale * normal_scale
                        combined_scale = min(combined_scale, max_scale)
                        frame_data["Scales"].append(combined_scale)
                        total_samples_written += 1

        elif direction == '-x':
            frame_data = frame_data_by_direction['-x']
            high_res_step = base_step / 4
            for y in range(int(y_length / high_res_step) + 1):
                for z_pos in range(-5, 105, 1):
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
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        cos_trace = abs(normals_world.dot(ray_direction_vec))
                        if cos_trace < min_cos_trace:
                            continue

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
                        normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                        step_scale = high_res_step / base_step
                        combined_scale = step_scale * normal_scale
                        combined_scale = min(combined_scale, max_scale)
                        frame_data["Scales"].append(combined_scale)
                        total_samples_written += 1

        elif direction == 'y':
            frame_data = frame_data_by_direction['y']
            high_res_step = base_step / 4
            for x in range(int(x_length / high_res_step) + 1):
                for z_pos in range(-5, 105, 1):
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
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        cos_trace = abs(normals_world.dot(ray_direction_vec))
                        if cos_trace < min_cos_trace:
                            continue

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
                        normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                        step_scale = high_res_step / base_step
                        combined_scale = step_scale * normal_scale
                        combined_scale = min(combined_scale, max_scale)
                        frame_data["Scales"].append(combined_scale)
                        total_samples_written += 1

        elif direction == '-y':
            frame_data = frame_data_by_direction['-y']
            high_res_step = base_step / 4
            for x in range(int(x_length / high_res_step) + 1):
                for z_pos in range(-5, 105, 1):
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
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        cos_trace = abs(normals_world.dot(ray_direction_vec))
                        if cos_trace < min_cos_trace:
                            continue

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
                        normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
                        step_scale = high_res_step / base_step
                        combined_scale = step_scale * normal_scale
                        combined_scale = min(combined_scale, max_scale)
                        frame_data["Scales"].append(combined_scale)
                        total_samples_written += 1

    # FR-35: Vertical sampling with distance-based resolution
    # Sample with variable resolution based on distance from peaks
    # FR-36: Ensure alignment and no gaps by using a fine base grid
    frame_data = frame_data_by_direction['vertical']

    # Use finest resolution as base grid to ensure no gaps (FR-36)
    finest_step = base_step * min_step_multiplier

    for x_fine in range(int(x_length / finest_step) + 1):
        for y_fine in range(int(y_length / finest_step) + 1):
            x_pos = start_trace_x + finest_step * x_fine
            y_pos = start_trace_y + finest_step * y_fine

            # FR-35: Calculate resolution at this position based on distance from peaks
            step_multiplier = calculate_distance_based_step_multiplier(
                y_pos, peak_y_positions, y_length
            )
            local_step = base_step * step_multiplier

            # FR-36: Only sample at positions that align with the local resolution
            # Check if this fine grid position aligns with the local step
            x_offset = x_pos - start_trace_x
            y_offset = y_pos - start_trace_y

            # Check alignment: position should be on a grid point for the local resolution
            x_aligned = abs(x_offset % local_step) < finest_step * 0.5 or abs(x_offset % local_step - local_step) < finest_step * 0.5
            y_aligned = abs(y_offset % local_step) < finest_step * 0.5 or abs(y_offset % local_step - local_step) < finest_step * 0.5

            if not (x_aligned and y_aligned):
                continue  # Skip positions that don't align with local resolution

            # Perform raycast
            ray_begin = Vector((x_pos, y_pos, 100))
            ray_end = Vector((x_pos, y_pos, -100))
            ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
            ray_direction = ray_end - ray_begin
            ray_direction.normalize()
            hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)

            if not hit:
                continue

            normals.normalize()

            # FR-38: Skip samples with steep normals (handled by horizontal raycasts)
            if is_steep_normal(normals):
                continue

            # FR-30: Skip samples too perpendicular to ray direction
            cos_trace = abs(normals.dot(ray_direction))
            if cos_trace < min_cos_trace:
                continue

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
            # FR-37: Scale adjusted by both normal and step size
            normal_scale = 1 / float(cos_trace) if cos_trace != 0 else max_scale
            step_scale = step_multiplier
            combined_scale = step_scale * normal_scale
            combined_scale = min(combined_scale, max_scale)
            frame_data["Scales"].append(combined_scale)
            total_samples_written += 1

    # FR-32: Append frame data for each direction
    for direction in ['vertical', 'x', '-x', 'y', '-y']:
        frames_data_by_direction[direction].append(frame_data_by_direction[direction])
    print(f"Processed frame {frame}")

# FR-32: Write separate output files for each direction
for direction in ['vertical', 'x', '-x', 'y', '-y']:
    direction_filename = f"ocean-points-data-{direction}.json"
    output_filepath = os.path.join(output_directory, direction_filename)
    with open(output_filepath, "w") as file:
        json.dump(frames_data_by_direction[direction], file, indent=2)
    print(f"Written {len(frames_data_by_direction[direction])} frames to {direction_filename}")

# Print statistics (FR-10)
print("Export completed!")
print(f"Total samples written: {total_samples_written}")
