import os
import json
import bpy
from mathutils import Vector

# Configuration
target_object = bpy.data.objects['fluid_surface']
start_frame = 752
end_frame = 1325
scn = bpy.context.scene
output_directory = "/hdd/gone_surfing_exports/medium_wave_left"
output_filename = "ocean-points-data-simple.json"

# Sampling configuration
sample_x = 50.0  # Fixed x position to sample along
start_y = -280
end_y = 170
step_size = 0.1  # High resolution step size

# Maximum scale limit
max_scale = 4
# Minimum cosine between normal and ray direction
min_cos_trace = 0.6

# Store all frames
frames_data = []

# Statistics
total_samples_written = 0

print(f"Starting simple export: sampling along x={sample_x} from y={start_y} to y={end_y} with step={step_size}")

for frame in range(start_frame, end_frame + 1):
    scn.frame_set(frame)

    frame_data = {
        "Name": f"Frame_{frame}",
        "Positions": [],
        "Normals": [],
        "Scales": []
    }

    # Calculate number of samples
    y_length = end_y - start_y
    num_samples = int(y_length / step_size) + 1

    # Sample along the single line
    for y_idx in range(num_samples):
        y_pos = start_y + step_size * y_idx

        # Perform vertical raycast
        ray_begin = Vector((sample_x, y_pos, 100))
        ray_end = Vector((sample_x, y_pos, -100))
        ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
        ray_direction = ray_end - ray_begin
        ray_direction.normalize()
        hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)

        if not hit:
            continue

        normals.normalize()

        # Skip samples too perpendicular to ray direction
        cos_trace = abs(normals.dot(ray_direction))
        if cos_trace < min_cos_trace:
            continue

        # Store position
        frame_data["Positions"].append({
            "X": float(location.x),
            "Y": float(location.y),
            "Z": float(location.z)
        })

        # Store normal
        frame_data["Normals"].append({
            "X": float(normals.x),
            "Y": float(normals.y),
            "Z": float(normals.z)
        })

        frame_data["Scales"].append(1.0)

        total_samples_written += 1

    frames_data.append(frame_data)
    print(f"Processed frame {frame}: {len(frame_data['Positions'])} samples")

# Write output file
output_filepath = os.path.join(output_directory, output_filename)
with open(output_filepath, "w") as file:
    json.dump(frames_data, file, indent=2)

print("\n" + "="*60)
print("EXPORT COMPLETED!")
print("="*60)
print(f"Output file: {output_filename}")
print(f"Total frames: {len(frames_data)}")
print(f"Total samples written: {total_samples_written}")
print(f"Average samples per frame: {total_samples_written / len(frames_data):.1f}")
print(f"Sampling configuration:")
print(f"  - X position: {sample_x}")
print(f"  - Y range: {start_y} to {end_y}")
print(f"  - Step size: {step_size}")
print("="*60)
