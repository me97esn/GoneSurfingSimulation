import bpy
import os

# Configuration
start_frame = 752
end_frame = 753  # Just test 2 frames
output_dir = "/hdd/gone_surfing_exports/medium_wave_left/white_water"

print("\n=== TESTING BLENDER EXPORT ===")

# List all objects
print("\nAvailable objects:")
for obj in bpy.data.objects:
    print(f"  - {obj.name} (type: {obj.type})")

# Try to find white water object
white_water_objects = ['whitewater_foam', 'foam', 'Foam', 'whitewater', 'Whitewater']
white_water_obj = None

for obj_name in white_water_objects:
    if obj_name in bpy.data.objects:
        white_water_obj = bpy.data.objects[obj_name]
        print(f"\n✓ Found white water object: {white_water_obj.name}")
        break

if white_water_obj is None:
    print("\n✗ ERROR: Could not find white water object!")
    exit(1)

# Check the object at a specific frame
bpy.context.scene.frame_set(752)
depsgraph = bpy.context.evaluated_depsgraph_get()
obj_eval = white_water_obj.evaluated_get(depsgraph)

if obj_eval.type == 'MESH':
    mesh = obj_eval.to_mesh()
    print(f"Vertex count at frame 752: {len(mesh.vertices)}")
    obj_eval.to_mesh_clear()
else:
    print(f"Object type is not MESH: {obj_eval.type}")

# Now try exporting a single frame
print("\n=== Attempting to export frame 752 ===")
bpy.ops.object.select_all(action='DESELECT')
white_water_obj.select_set(True)
bpy.context.view_layer.objects.active = white_water_obj

output_file = os.path.join(output_dir, "test_752.obj")
print(f"Output file: {output_file}")

try:
    bpy.ops.wm.obj_export(
        filepath=output_file,
        export_selected_objects=True,
        export_animation=False,
        forward_axis='X',
        up_axis='Z'
    )
    print(f"✓ Export successful!")

    # Check file size
    if os.path.exists(output_file):
        size = os.path.getsize(output_file)
        print(f"  File size: {size} bytes")

        # Count vertices in exported file
        with open(output_file, 'r') as f:
            vertex_count = sum(1 for line in f if line.startswith('v '))
        print(f"  Vertices in exported file: {vertex_count}")
    else:
        print(f"✗ File was not created!")
except Exception as e:
    print(f"✗ Export failed: {e}")
