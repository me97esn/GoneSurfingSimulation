"""
Export fluid surface height samples and normals to JSON files.

Usage:
    blender path/to/simulation.blend --background --python export_fluid_surface_to_3d_samples.py -- [start_frame] [end_frame] [output_dir] [step]

Example:
    blender ../3dmodels/breaking_waves_beach_break_2.blend --background --python export_fluid_surface_to_3d_samples.py -- 752 1325 /hdd/gone_surfing_exports/medium_wave_left 1
"""
import bpy
from mathutils import Vector
import os
import json
import sys

# Parse command-line arguments (after "--")
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

# Defaults
start_frame = int(argv[0]) if len(argv) > 0 else 752
end_frame = int(argv[1]) if len(argv) > 1 else 1325
output_directory = argv[2] if len(argv) > 2 else "/hdd/gone_surfing_exports/medium_wave_left"
step = int(argv[3]) if len(argv) > 3 else 1

print(f"Export Fluid Surface Samples")
print(f"  Start frame: {start_frame}")
print(f"  End frame: {end_frame}")
print(f"  Output dir: {output_directory}")
print(f"  Step size: {step}")

os.makedirs(output_directory, exist_ok=True)

target_object = bpy.data.objects['fluid_surface']
scn = bpy.context.scene

# Calculate mesh bounds at start frame
scn.frame_set(start_frame)
depsgraph = bpy.context.evaluated_depsgraph_get()
obj_eval = target_object.evaluated_get(depsgraph)
mesh = obj_eval.to_mesh()
matrix = target_object.matrix_world

# Get world-space bounding box
xs = [(matrix @ v.co).x for v in mesh.vertices]
ys = [(matrix @ v.co).y for v in mesh.vertices]

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)

start_trace_x = min_x
start_trace_y = min_y
x_length = max_x - min_x
y_length = max_y - min_y

obj_eval.to_mesh_clear()

print(f"  Mesh bounds: X[{min_x:.1f}, {max_x:.1f}] Y[{min_y:.1f}, {max_y:.1f}]")
print(f"  Sampling area: {x_length:.1f} x {y_length:.1f}")
print(f"  Grid size: {int(x_length/step)} x {int(y_length/step)} samples")

output_filename = "wave_samples.json"
output_filename_normals_x = "wave_normals_x.json"
output_filename_normals_y = "wave_normals_y.json"
output_filename_normals_z = "wave_normals_z.json"

def samples_skeleton():
    return {
        "step_size": step,
        "samples": [],
        "start_frame": start_frame,
        "end_frame": end_frame,
        "start_trace_x": start_trace_x,
        "start_trace_y": start_trace_y,
        "x_length": x_length,
        "y_length": y_length,
        "coordinates": []}

samples = samples_skeleton()
normals_x = samples_skeleton()
normals_y = samples_skeleton()
normals_z = samples_skeleton()

total_frames = end_frame - start_frame + 1
for i, frame in enumerate(range(start_frame, end_frame+1)):
    if i % 10 == 0:
        print(f"  Processing frame {frame} ({i+1}/{total_frames})")
    scn.frame_set(frame)
    frame_samples = []
    frame_coordinates = []
    frame_normals_x = []
    frame_normals_y = []
    frame_normals_z = []
    for x in range(int(samples["x_length"]/step)):
        row = []
        coordinates_row = []
        normals_row_x = []
        normals_row_y = []
        normals_row_z = []
        for y in range(int(samples["y_length"]/step)):
            ray_begin = Vector((samples["start_trace_x"]+step * x, samples["start_trace_y"]+step*y, 100))
            ray_end = Vector((samples["start_trace_x"]+step*x, samples["start_trace_y"]+step*y, -100))
            ray_begin_local = target_object.matrix_world.inverted() @ ray_begin
            ray_direction = ray_end - ray_begin
            ray_direction.normalize()
            hit, location, normals, index = target_object.ray_cast(ray_begin_local, ray_direction)
            normals.normalize()
            sample = location.z
            row.append(sample)
            coordinates_row.append([location.x, location.y])
            normals_row_x.append(normals.x)
            normals_row_y.append(normals.y)
            normals_row_z.append(normals.z)
        frame_samples.append(row)
        frame_coordinates.append(coordinates_row)
        frame_normals_x.append(normals_row_x)
        frame_normals_y.append(normals_row_y)
        frame_normals_z.append(normals_row_z)
    for d in [normals_x, normals_y, normals_z, samples]:
        d["coordinates"].append(frame_coordinates)
    samples["samples"].append(frame_samples)
    normals_x["samples"].append(frame_normals_x)
    normals_y["samples"].append(frame_normals_y)
    normals_z["samples"].append(frame_normals_z)

output_filepath = os.path.join(output_directory, output_filename)
file = open(output_filepath, "w")
file.write(json.dumps(samples))
file.close()

output_filepath_normals_x = os.path.join(output_directory, output_filename_normals_x)
file = open(output_filepath_normals_x, "w")
file.write(json.dumps(normals_x))
file.close()

output_filepath_normals_y = os.path.join(output_directory, output_filename_normals_y)
file = open(output_filepath_normals_y, "w")
file.write(json.dumps(normals_y))
file.close()

output_filepath_normals_z = os.path.join(output_directory, output_filename_normals_z)
file = open(output_filepath_normals_z, "w")
file.write(json.dumps(normals_z))
file.close()

print('written sampling files')
