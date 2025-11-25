"""
Export wave animation as chunked OBJ meshes at multiple quality levels.
This script is designed to be run inside Blender (via command line).
"""
import bpy
import os
import sys
import bmesh
from mathutils import Vector

# Get command-line arguments passed after --
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []

if len(argv) < 4:
    print("Error: Missing required arguments")
    print("Usage: blender file.blend --background --python export_waves_display.py -- <start_frame> <end_frame> <output_base_dir> <quality_levels_csv>")
    print("Example: blender file.blend --background --python export_waves_display.py -- 752 868 /hdd/exports 0.05,0.04,0.03,0.02,0.01")
    sys.exit(1)

start_frame = int(argv[0])
end_frame = int(argv[1])
output_base_dir = argv[2]
quality_levels = [float(x) for x in argv[3].split(',')]

print(f"="*60)
print(f"WAVE DISPLAY EXPORT")
print(f"="*60)
print(f"Start frame: {start_frame}")
print(f"End frame: {end_frame}")
print(f"Output base directory: {output_base_dir}")
print(f"Quality levels (decimate ratios): {quality_levels}")
print(f"="*60)

# Configuration
CHUNKS_X = 3  # Split 3 times along longest axis
CHUNKS_Y = 8  # Split 8 times along second longest axis
FLUID_SURFACE_NAME = 'fluid_surface'
BOOL_BOUNDARY_NAME = 'BoolBoundary'

def get_mesh_bounds(obj):
    """Get the bounding box of a mesh object in world space"""
    if len(obj.data.vertices) == 0:
        return None

    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_x = min(c.x for c in bbox_corners)
    max_x = max(c.x for c in bbox_corners)
    min_y = min(c.y for c in bbox_corners)
    max_y = max(c.y for c in bbox_corners)
    min_z = min(c.z for c in bbox_corners)
    max_z = max(c.z for c in bbox_corners)

    return {
        'min': Vector((min_x, min_y, min_z)),
        'max': Vector((max_x, max_y, max_z)),
        'size': Vector((max_x - min_x, max_y - min_y, max_z - min_z))
    }

def split_mesh_into_chunks(obj, chunks_x, chunks_y):
    """
    Split mesh into chunks using boolean operations.
    Returns list of chunk objects with their grid positions.
    """
    bounds = get_mesh_bounds(obj)
    if not bounds:
        return []

    # Determine which axes to split (longest and second longest)
    size = bounds['size']
    axes = [(size.x, 'x', 0), (size.y, 'y', 1), (size.z, 'z', 2)]
    axes.sort(reverse=True, key=lambda x: x[0])

    # Longest axis gets CHUNKS_X splits, second longest gets CHUNKS_Y
    primary_axis = axes[0][1]  # 'x', 'y', or 'z'
    secondary_axis = axes[1][1]

    print(f"  Splitting along {primary_axis} ({chunks_x} chunks) and {secondary_axis} ({chunks_y} chunks)")

    # Calculate chunk dimensions
    primary_idx = axes[0][2]
    secondary_idx = axes[1][2]

    primary_min = bounds['min'][primary_idx]
    primary_max = bounds['max'][primary_idx]
    secondary_min = bounds['min'][secondary_idx]
    secondary_max = bounds['max'][secondary_idx]

    primary_size = (primary_max - primary_min) / chunks_x
    secondary_size = (secondary_max - secondary_min) / chunks_y

    chunks = []

    for i in range(chunks_x):
        for j in range(chunks_y):
            # Calculate bounds for this chunk
            p_start = primary_min + i * primary_size
            p_end = primary_min + (i + 1) * primary_size
            s_start = secondary_min + j * secondary_size
            s_end = secondary_min + (j + 1) * secondary_size

            # Create a duplicate of the object for this chunk
            chunk_obj = obj.copy()
            chunk_obj.data = obj.data.copy()
            bpy.context.collection.objects.link(chunk_obj)

            # Add boolean modifiers to isolate this chunk
            # We'll use cube primitives as cutters

            # Create bounding box for this chunk
            # Note: This is a simplified approach - in production you might want
            # to use actual boolean operations with cube meshes

            chunks.append({
                'object': chunk_obj,
                'grid_x': i,
                'grid_y': j,
                'bounds': {
                    primary_axis: (p_start, p_end),
                    secondary_axis: (s_start, s_end)
                }
            })

    return chunks

def export_chunks_for_frame(fluid_surface, frame, quality_ratio, output_dir, chunks_x, chunks_y, fixed_chunk_bounds):
    """Export all chunks for a single frame at specified quality using fixed world coordinates"""
    # Set the current frame
    bpy.context.scene.frame_set(frame)

    # Get or create a working copy of the fluid surface
    work_obj = fluid_surface.copy()
    work_obj.data = fluid_surface.data.copy()
    bpy.context.collection.objects.link(work_obj)
    bpy.context.view_layer.objects.active = work_obj

    # FR-2: Add boolean modifier (difference with BoolBoundary)
    bool_boundary = bpy.data.objects.get(BOOL_BOUNDARY_NAME)
    if bool_boundary:
        bool_mod = work_obj.modifiers.new(name="Boolean", type='BOOLEAN')
        bool_mod.operation = 'DIFFERENCE'
        bool_mod.object = bool_boundary
        print(f"  Added Boolean modifier with {BOOL_BOUNDARY_NAME}")
    else:
        print(f"  Warning: {BOOL_BOUNDARY_NAME} not found, skipping boolean modifier")

    # FR-3: Add decimate modifier
    decimate_mod = work_obj.modifiers.new(name="Decimate", type='DECIMATE')
    decimate_mod.decimate_type = 'COLLAPSE'
    decimate_mod.ratio = quality_ratio
    print(f"  Added Decimate modifier with ratio {quality_ratio}")

    # Apply modifiers
    bpy.context.view_layer.objects.active = work_obj
    work_obj.select_set(True)

    # Apply modifiers by converting to mesh
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = work_obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(eval_obj)
    final_obj = bpy.data.objects.new(f"processed_{frame}", mesh)
    bpy.context.collection.objects.link(final_obj)

    # FR-4 & FR-5: Split into chunks and export using fixed world coordinates (FR-10)
    bounds = get_mesh_bounds(final_obj)
    if not bounds:
        print(f"  Warning: No geometry for frame {frame}")
        # Cleanup
        bpy.data.objects.remove(work_obj)
        bpy.data.objects.remove(final_obj)
        return

    # FR-10: Use fixed chunk boundaries calculated from start_frame
    primary_idx = fixed_chunk_bounds['primary_idx']
    secondary_idx = fixed_chunk_bounds['secondary_idx']
    primary_min = fixed_chunk_bounds['primary_min']
    primary_max = fixed_chunk_bounds['primary_max']
    secondary_min = fixed_chunk_bounds['secondary_min']
    secondary_max = fixed_chunk_bounds['secondary_max']
    chunk_primary = fixed_chunk_bounds['chunk_primary']
    chunk_secondary = fixed_chunk_bounds['chunk_secondary']

    # Export each chunk
    os.makedirs(output_dir, exist_ok=True)

    for i in range(chunks_x):
        for j in range(chunks_y):
            # Calculate bounds for this chunk
            p_start = primary_min + i * chunk_primary
            p_end = primary_min + (i + 1) * chunk_primary
            s_start = secondary_min + j * chunk_secondary
            s_end = secondary_min + (j + 1) * chunk_secondary

            # Create bounding box planes for this chunk
            # We'll use bisect to create clean straight edges
            bm = bmesh.new()
            bm.from_mesh(final_obj.data)

            # Apply world transform to bmesh
            bm.transform(final_obj.matrix_world)

            # Create plane normals and points for bisecting
            # Bisect along primary axis (min)
            plane_no_p_min = Vector([0, 0, 0])
            plane_no_p_min[primary_idx] = 1.0
            plane_co_p_min = Vector([0, 0, 0])
            plane_co_p_min[primary_idx] = p_start

            # Bisect along primary axis (max)
            plane_no_p_max = Vector([0, 0, 0])
            plane_no_p_max[primary_idx] = -1.0
            plane_co_p_max = Vector([0, 0, 0])
            plane_co_p_max[primary_idx] = p_end

            # Bisect along secondary axis (min)
            plane_no_s_min = Vector([0, 0, 0])
            plane_no_s_min[secondary_idx] = 1.0
            plane_co_s_min = Vector([0, 0, 0])
            plane_co_s_min[secondary_idx] = s_start

            # Bisect along secondary axis (max)
            plane_no_s_max = Vector([0, 0, 0])
            plane_no_s_max[secondary_idx] = -1.0
            plane_co_s_max = Vector([0, 0, 0])
            plane_co_s_max[secondary_idx] = s_end

            # FR-11: Perform bisect operations to cut the mesh at chunk boundaries
            # This creates clean straight edges
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_p_min, plane_no=plane_no_p_min, clear_outer=True)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_p_max, plane_no=plane_no_p_max, clear_outer=True)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_s_min, plane_no=plane_no_s_min, clear_outer=True)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_s_max, plane_no=plane_no_s_max, clear_outer=True)

            # FR-12: Remove downward-facing faces (faces with normal.z < 0)
            # Ensure normals are calculated
            bm.normal_update()

            # Find faces with downward-pointing normals
            faces_to_remove = []
            for face in bm.faces:
                # Check if face normal points downward (negative Z component)
                if face.normal.z < 0:
                    faces_to_remove.append(face)

            # Remove downward-facing faces
            bmesh.ops.delete(bm, geom=faces_to_remove, context='FACES')

            print(f"    Chunk ({i},{j}): Removed {len(faces_to_remove)} downward-facing faces")

            # Create chunk mesh
            chunk_mesh = bpy.data.meshes.new(f"chunk_{i}_{j}_{frame}")
            bm.to_mesh(chunk_mesh)
            bm.free()

            chunk_obj = bpy.data.objects.new(f"chunk_{i}_{j}_{frame}", chunk_mesh)
            bpy.context.collection.objects.link(chunk_obj)

            # Export chunk as OBJ
            chunk_filename = f"{i}_{j}_mesh_{frame}.obj"
            chunk_filepath = os.path.join(output_dir, chunk_filename)

            # Select only this chunk
            bpy.ops.object.select_all(action='DESELECT')
            chunk_obj.select_set(True)
            bpy.context.view_layer.objects.active = chunk_obj

            # Export OBJ
            bpy.ops.wm.obj_export(
                filepath=chunk_filepath,
                export_selected_objects=True,
                export_animation=False,
                forward_axis='X',
                up_axis='Z',
                apply_modifiers=True
            )

            # Cleanup chunk object
            bpy.data.objects.remove(chunk_obj)
            bpy.data.meshes.remove(chunk_mesh)

    # Cleanup
    bpy.data.objects.remove(work_obj)
    bpy.data.objects.remove(final_obj)

    print(f"  Exported {chunks_x * chunks_y} chunks for frame {frame}")

# Main execution
# Get the fluid surface object
fluid_surface = bpy.data.objects.get(FLUID_SURFACE_NAME)
if not fluid_surface:
    print(f"Error: Object '{FLUID_SURFACE_NAME}' not found!")
    sys.exit(1)

print(f"\nFound fluid surface: {fluid_surface.name}")

# FR-10: Calculate fixed chunk boundaries from start_frame
print(f"\n{'='*60}")
print(f"FR-10: Calculating fixed world coordinate chunk boundaries from frame {start_frame}")
print(f"{'='*60}")

# Set to start frame
bpy.context.scene.frame_set(start_frame)

# Create temporary processed object to get bounding box
temp_obj = fluid_surface.copy()
temp_obj.data = fluid_surface.data.copy()
bpy.context.collection.objects.link(temp_obj)
bpy.context.view_layer.objects.active = temp_obj

# Add boolean modifier if available
bool_boundary = bpy.data.objects.get(BOOL_BOUNDARY_NAME)
if bool_boundary:
    bool_mod = temp_obj.modifiers.new(name="Boolean", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = bool_boundary

# Add decimate modifier (using first quality level for boundary calculation)
decimate_mod = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
decimate_mod.decimate_type = 'COLLAPSE'
decimate_mod.ratio = quality_levels[0]

# Apply modifiers
bpy.context.view_layer.objects.active = temp_obj
temp_obj.select_set(True)
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_obj = temp_obj.evaluated_get(depsgraph)
temp_mesh = bpy.data.meshes.new_from_object(eval_obj)
temp_final = bpy.data.objects.new("temp_bounds", temp_mesh)
bpy.context.collection.objects.link(temp_final)

# Get bounds from start frame
bounds = get_mesh_bounds(temp_final)
if not bounds:
    print(f"Error: No geometry in start frame {start_frame}")
    sys.exit(1)

# Determine longest and second-longest axes
size = bounds['size']
axes_sorted = [(size.x, 'x', 0), (size.y, 'y', 1), (size.z, 'z', 2)]
axes_sorted.sort(reverse=True, key=lambda x: x[0])

primary_idx = axes_sorted[0][2]
secondary_idx = axes_sorted[1][2]
primary_axis_name = axes_sorted[0][1]
secondary_axis_name = axes_sorted[1][1]

primary_min = bounds['min'][primary_idx]
primary_max = bounds['max'][primary_idx]
secondary_min = bounds['min'][secondary_idx]
secondary_max = bounds['max'][secondary_idx]

chunk_primary = (primary_max - primary_min) / CHUNKS_X
chunk_secondary = (secondary_max - secondary_min) / CHUNKS_Y

# Store fixed chunk boundaries
fixed_chunk_bounds = {
    'primary_idx': primary_idx,
    'secondary_idx': secondary_idx,
    'primary_min': primary_min,
    'primary_max': primary_max,
    'secondary_min': secondary_min,
    'secondary_max': secondary_max,
    'chunk_primary': chunk_primary,
    'chunk_secondary': chunk_secondary
}

print(f"Chunk grid aligned to {primary_axis_name}-axis (longest) × {secondary_axis_name}-axis (second longest)")
print(f"Primary axis ({primary_axis_name}): {primary_min:.2f} to {primary_max:.2f}, chunk size: {chunk_primary:.2f}")
print(f"Secondary axis ({secondary_axis_name}): {secondary_min:.2f} to {secondary_max:.2f}, chunk size: {chunk_secondary:.2f}")
print(f"These boundaries will be used for ALL frames to ensure consistent chunk positions")

# Cleanup temporary objects
bpy.data.objects.remove(temp_obj)
bpy.data.objects.remove(temp_final)
bpy.data.meshes.remove(temp_mesh)

# FR-6, FR-7, FR-8: Process each quality level
for quality_idx, quality_ratio in enumerate(quality_levels):
    quality_name = f"ratio_{str(quality_ratio).replace('.', '_')}"

    if quality_idx == 0:
        # First quality level uses specific folder names
        if quality_ratio == 0.05:
            quality_folder = "chunks_epic_resolution"
        elif quality_ratio == 0.04:
            quality_folder = "chunks_higher_resolution"
        else:
            quality_folder = f"chunks_{quality_name}"
    else:
        quality_folder = f"chunks_{quality_name}"

    output_dir = os.path.join(output_base_dir, quality_folder)

    print(f"\n{'-'*60}")
    print(f"Processing quality level {quality_idx + 1}/{len(quality_levels)}: ratio={quality_ratio}")
    print(f"Output directory: {output_dir}")
    print(f"{'-'*60}")

    # FR-6: Process each frame
    for frame in range(start_frame, end_frame + 1):
        print(f"\nFrame {frame}:")
        export_chunks_for_frame(fluid_surface, frame, quality_ratio, output_dir, CHUNKS_X, CHUNKS_Y, fixed_chunk_bounds)

        if frame % 10 == 0:
            print(f"  Progress: {frame - start_frame + 1}/{end_frame - start_frame + 1} frames")

print(f"\n{'='*60}")
print(f"EXPORT COMPLETE!")
print(f"{'='*60}")
print(f"Processed {len(quality_levels)} quality levels")
print(f"Processed {end_frame - start_frame + 1} frames")
print(f"Total chunks per frame: {CHUNKS_X * CHUNKS_Y}")
print(f"{'='*60}")
