import os
import json
import bpy
from mathutils import Vector

target_object = bpy.data.objects['fluid_surface']
# High resolution boundary mesh (FR-11) - applies to horizontal steep sampling only
high_res_boundary = bpy.data.objects.get('High_resolution_boundary')
start_frame = 752
end_frame = 1325
# end_frame = 754
scn = bpy.context.scene
base_step = 4  # Base step size for medium resolution
# output_directory = "/home/emil/workspace/GoneSurfingScripts"
output_directory = "/hdd/gone_surfing_exports/medium_wave_left"
output_filename = "ocean-points-data.json"

# Steep normal thresholds (FR-18, FR-38)
# For horizontal ray casting: determines which samples to capture with sideways rays
steep_normal_threshold_horizontal = 0.7  # cos(60 degrees) - angles steeper than 60 degrees from vertical
# For vertical sampling: determines which samples to skip (handled by horizontal instead)
steep_normal_threshold_vertical = 0.55 
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
min_step_multiplier = 0.5  # Highest resolution: base_step * 0.5 (high resolution)
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
# Track samples per direction and per resolution
stats_by_direction = {
    'vertical': {'total': 0, 'high': 0, 'medium': 0, 'low': 0},
    'x': {'total': 0, 'steep': 0},
    '-x': {'total': 0, 'steep': 0},
    'y': {'total': 0, 'steep': 0},
    '-y': {'total': 0, 'steep': 0}
}
total_samples_written = 0
total_top_1_percent_samples = 0

def is_steep_normal(normal, threshold):
    """Check if normal is steep enough based on threshold (FR-18, FR-38)"""
    z_axis = Vector((0, 0, 1))
    cos_angle = abs(normal.dot(z_axis))
    return cos_angle < threshold

def is_point_in_boundary(point):
    """Check if a point is within the High_resolution_boundary mesh (FR-11)
    Used for horizontal steep sampling only"""
    if high_res_boundary is None:
        return True  # If no boundary mesh, allow all points

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

def calculate_distance_based_step_multiplier(y_pos, peak_y_positions, base_step):
    """
    FR-35, FR-39, FR-40: Calculate step multiplier based on distance from highest peaks
    Asymmetric distribution around peak:
    - High (finest): ~4 samples in +y, ~1 samples in -y direction
    - Medium resolution: ~2 rows in both directions
    - Low resolution: beyond that

    FR-40: Add boundary samples at resolution transitions to prevent gaps

    Returns a step multiplier between min_step_multiplier (0.5) and max_step_multiplier (2.0)
    """
    if not peak_y_positions:
        # No peaks found, use maximum (lowest) resolution
        return max_step_multiplier

    # Find nearest peak and signed distance (positive = +y direction, negative = -y direction)
    nearest_peak_y = min(peak_y_positions, key=lambda peak_y: abs(y_pos - peak_y))
    signed_distance = y_pos - nearest_peak_y  # Positive = +y, Negative = -y

    # FR-39: Define resolution zones based on distance from peak
    # Resolution levels: 0.5 (high/finest), 1.0 (medium), 2.0 (low)

    if signed_distance >= 0:
        # Positive y direction (ahead of peak)
        high_samples = 4  # Renamed from ridge_samples, now uses 0.5× resolution
        medium_samples = 2

        # Calculate zone extents, ensuring they align with their resolution grids
        # Each zone extent must be a multiple of its resolution step to ensure alignment
        high_step = base_step * min_step_multiplier  # 0.5×
        medium_step = base_step * 1.0

        high_extent = high_samples * high_step
        medium_extent = high_extent + medium_samples * medium_step

        # FR-40: Add boundary samples - one extra row at each transition
        # Boundaries extend the higher resolution into the next zone
        high_boundary = high_extent + high_step
        medium_boundary = medium_extent + medium_step

        if signed_distance < high_extent:
            return min_step_multiplier  # 0.5 - finest resolution (high)
        elif signed_distance < high_boundary:
            return min_step_multiplier  # 0.5 - boundary sample (high into medium)
        elif signed_distance < medium_extent:
            return 1.0  # Medium resolution
        elif signed_distance < medium_boundary:
            return 1.0  # Medium resolution - boundary sample (medium into low)
        else:
            return max_step_multiplier  # 2.0 - low resolution
    else:
        # Negative y direction (behind peak)
        high_samples = 1  # Renamed from ridge_samples, now uses 0.5× resolution
        medium_samples = 2

        # Calculate zone extents, ensuring they align with their resolution grids
        high_step = base_step * min_step_multiplier  # 0.5×
        medium_step = base_step * 1.0

        high_extent = high_samples * high_step
        medium_extent = high_extent + medium_samples * medium_step

        # FR-40: Add boundary samples - one extra row at each transition
        high_boundary = high_extent + high_step
        medium_boundary = medium_extent + medium_step

        abs_distance = abs(signed_distance)
        if abs_distance < high_extent:
            return min_step_multiplier  # 0.5 - finest resolution (high)
        elif abs_distance < high_boundary:
            return min_step_multiplier  # 0.5 - boundary sample (high into medium)
        elif abs_distance < medium_extent:
            return 1.0  # Medium resolution
        elif abs_distance < medium_boundary:
            return 1.0  # Medium resolution - boundary sample (medium into low)
        else:
            return max_step_multiplier  # 2.0 - low resolution

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
    num_top_1_percent = 0
    for sample in coarse_samples:
        if sample['height'] >= height_threshold_top_1_percent:
            peak_y_positions.add(sample['y_pos'])
            num_top_1_percent += 1

    peak_y_positions = sorted(list(peak_y_positions))
    total_top_1_percent_samples += num_top_1_percent
    print(f"Frame {frame}: Found {len(peak_y_positions)} peak y-positions at threshold {height_threshold_top_1_percent:.2f}, {num_top_1_percent} samples in top 1%")

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

                    if hit and is_steep_normal(normals, steep_normal_threshold_horizontal):  # FR-38: Only steep samples
                        normals.normalize()
                        location_world = target_object.matrix_world @ location
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        # FR-11: Only capture steep samples within boundary
                        if not is_point_in_boundary(location_world):
                            continue

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
                        stats_by_direction['x']['total'] += 1
                        stats_by_direction['x']['steep'] += 1

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

                    if hit and is_steep_normal(normals, steep_normal_threshold_horizontal):
                        normals.normalize()
                        location_world = target_object.matrix_world @ location
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        # FR-11: Only capture steep samples within boundary
                        if not is_point_in_boundary(location_world):
                            continue

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
                        stats_by_direction['-x']['total'] += 1
                        stats_by_direction['-x']['steep'] += 1

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

                    if hit and is_steep_normal(normals, steep_normal_threshold_horizontal):
                        normals.normalize()
                        location_world = target_object.matrix_world @ location
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        # FR-11: Only capture steep samples within boundary
                        if not is_point_in_boundary(location_world):
                            continue

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
                        stats_by_direction['y']['total'] += 1
                        stats_by_direction['y']['steep'] += 1

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

                    if hit and is_steep_normal(normals, steep_normal_threshold_horizontal):
                        normals.normalize()
                        location_world = target_object.matrix_world @ location
                        normals_world = (target_object.matrix_world.to_3x3() @ normals).normalized()

                        # FR-11: Only capture steep samples within boundary
                        if not is_point_in_boundary(location_world):
                            continue

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
                        stats_by_direction['-y']['total'] += 1
                        stats_by_direction['-y']['steep'] += 1

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

            # FR-35, FR-39: Calculate resolution at this position based on distance from peaks
            step_multiplier = calculate_distance_based_step_multiplier(
                y_pos, peak_y_positions, base_step
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
            if is_steep_normal(normals, steep_normal_threshold_vertical):
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

            # Track statistics by resolution
            stats_by_direction['vertical']['total'] += 1
            if step_multiplier == min_step_multiplier:
                stats_by_direction['vertical']['high'] += 1  # 0.5× is now the finest
            elif step_multiplier == 1.0:
                stats_by_direction['vertical']['medium'] += 1
            elif step_multiplier == max_step_multiplier:
                stats_by_direction['vertical']['low'] += 1

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
print("\n" + "="*60)
print("EXPORT COMPLETED!")
print("="*60)
print(f"\nTotal samples written across all directions: {total_samples_written}")
print(f"Total samples in highest 1%: {total_top_1_percent_samples}")

print("\n" + "-"*60)
print("STATISTICS PER FILE/DIRECTION:")
print("-"*60)

# Vertical file statistics
print(f"\nFile: ocean-points-data-vertical.json")
print(f"  Total samples: {stats_by_direction['vertical']['total']}")
print(f"  Samples per resolution:")
print(f"    - High (0.5× step):    {stats_by_direction['vertical']['high']:,}")
print(f"    - Medium (1.0× step):  {stats_by_direction['vertical']['medium']:,}")
print(f"    - Low (2.0× step):     {stats_by_direction['vertical']['low']:,}")

# Horizontal files statistics
for direction in ['x', '-x', 'y', '-y']:
    print(f"\nFile: ocean-points-data-{direction}.json")
    print(f"  Total samples: {stats_by_direction[direction]['total']}")
    print(f"  Samples per resolution:")
    print(f"    - Steep samples (0.25× step): {stats_by_direction[direction]['steep']:,}")

print("\n" + "="*60)
