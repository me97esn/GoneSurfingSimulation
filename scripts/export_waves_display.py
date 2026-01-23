"""
Export wave animation as chunked OBJ meshes at multiple quality levels.
This script is designed to be run inside Blender (via command line).

Includes seamless edge blending for infinite wave tiling.
"""
import bpy
import os
import sys
import bmesh
import time
import math
from mathutils import Vector

# Get command-line arguments passed after --
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []

if len(argv) < 4:
    print("Error: Missing required arguments")
    print("Usage: blender file.blend --background --python export_waves_display.py -- <start_frame> <end_frame> <output_base_dir> <quality_levels_csv> [skip_existing] [frame_offset] [reference_mesh]")
    print("Example: blender file.blend --background --python export_waves_display.py -- 752 868 /hdd/exports 0.05,0.04,0.03,0.02,0.01 skip -95 1_0_mesh_903_reference")
    sys.exit(1)

start_frame = int(argv[0])
end_frame = int(argv[1])
output_base_dir = argv[2]
quality_levels = [float(x) for x in argv[3].split(',')]
skip_existing = argv[4] if len(argv) > 4 else 'skip'
frame_offset = int(argv[5]) if len(argv) > 5 else -95
reference_mesh_name = argv[6] if len(argv) > 6 else '1_0_mesh_903_reference'

# Seamless blending configuration
BLEND_WIDTH_PERCENT = 3.0  # Width of blend zone as percentage of mesh extent

print(f"="*60)
print(f"WAVE DISPLAY EXPORT (with seamless blending)")
print(f"="*60)
print(f"Start frame: {start_frame}")
print(f"End frame: {end_frame}")
print(f"Output base directory: {output_base_dir}")
print(f"Quality levels (decimate ratios): {quality_levels}")
print(f"Skip existing files: {skip_existing}")
print(f"Frame offset for blending: {frame_offset}")
print(f"Reference mesh: {reference_mesh_name}")
print(f"Blend width: {BLEND_WIDTH_PERCENT}%")
print(f"="*60)

# Configuration
CHUNKS_X = 3  # Split 3 times along longest axis
CHUNKS_Y = 1  # Split 1 time along second longest axis
FLUID_SURFACE_NAME = 'fluid_surface'
BOOL_BOUNDARY_NAME = 'BoolBoundary'


def smoothstep(t):
    """Smooth interpolation function (ease-in-out)"""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def get_reference_mesh_offset(reference_mesh_name):
    """Get the position offset from the reference mesh"""
    ref_obj = bpy.data.objects.get(reference_mesh_name)
    if ref_obj:
        return ref_obj.location.copy()
    else:
        print(f"  Warning: Reference mesh '{reference_mesh_name}' not found")
        return None


def apply_seamless_blending(work_obj, fluid_surface, current_frame, frame_offset, reference_offset, blend_axis_idx, blend_width_percent):
    """
    Apply seamless edge blending to mesh vertices BEFORE decimation.

    Since the simulation mesh has consistent vertex topology across frames,
    we can blend vertices by index (no spatial matching needed).

    Args:
        work_obj: The working mesh object to modify (current frame)
        fluid_surface: The original fluid surface object
        current_frame: Current frame number
        frame_offset: Frame offset to adjacent mesh (e.g., -95)
        reference_offset: Position offset from reference mesh
        blend_axis_idx: Axis index to blend along (0=x, 1=y, 2=z)
        blend_width_percent: Width of blend zone as percentage
    """
    # Get target frame (the frame that will be placed adjacent)
    # frame_offset is negative, so target_frame = current_frame + (-95) = earlier frame
    target_frame = current_frame + frame_offset

    print(f"  Seamless blending: frame {current_frame} edges toward frame {target_frame}")

    # Store current frame
    original_frame = bpy.context.scene.frame_current

    # Get current frame's mesh data (already in work_obj)
    current_mesh = work_obj.data
    current_verts = [v.co.copy() for v in current_mesh.vertices]

    # Get mesh bounds along blend axis
    axis_values = [v[blend_axis_idx] for v in current_verts]
    mesh_min = min(axis_values)
    mesh_max = max(axis_values)
    mesh_extent = mesh_max - mesh_min
    blend_width = mesh_extent * (blend_width_percent / 100.0)

    # Calculate blend zones
    # Positive edge (max value) - blends toward mesh in positive direction
    positive_blend_start = mesh_max - blend_width
    # Negative edge (min value) - blends toward mesh in negative direction
    negative_blend_end = mesh_min + blend_width

    print(f"    Mesh bounds on axis {blend_axis_idx}: [{mesh_min:.2f}, {mesh_max:.2f}]")
    print(f"    Blend width: {blend_width:.2f} ({blend_width_percent}%)")
    print(f"    Positive edge blend zone: [{positive_blend_start:.2f}, {mesh_max:.2f}]")
    print(f"    Negative edge blend zone: [{mesh_min:.2f}, {negative_blend_end:.2f}]")

    # Set to target frame and get target mesh vertices
    bpy.context.scene.frame_set(target_frame)

    # Get evaluated mesh at target frame
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = fluid_surface.evaluated_get(depsgraph)
    target_mesh = eval_obj.to_mesh()

    if len(target_mesh.vertices) != len(current_verts):
        print(f"    Warning: Vertex count mismatch! Current: {len(current_verts)}, Target: {len(target_mesh.vertices)}")
        print(f"    Skipping seamless blending for this frame")
        eval_obj.to_mesh_clear()
        bpy.context.scene.frame_set(original_frame)
        return

    # Get target vertices with world transform applied
    target_matrix = eval_obj.matrix_world
    target_verts = [(target_matrix @ v.co) for v in target_mesh.vertices]

    # Determine offset direction based on reference mesh position
    ref_axis_offset = reference_offset[blend_axis_idx]
    if ref_axis_offset < 0:
        # Reference mesh is in negative direction
        mesh_offset_negative = ref_axis_offset
        mesh_offset_positive = -ref_axis_offset
    else:
        mesh_offset_positive = ref_axis_offset
        mesh_offset_negative = -ref_axis_offset

    print(f"    Reference offset on blend axis: {ref_axis_offset:.2f}")
    print(f"    Offset for positive edge: {mesh_offset_positive:.2f}")
    print(f"    Offset for negative edge: {mesh_offset_negative:.2f}")

    # Apply blending
    blended_positive = 0
    blended_negative = 0

    # Get current mesh world matrix for vertex positions
    current_matrix = work_obj.matrix_world

    for i, vert in enumerate(current_mesh.vertices):
        # Get world position
        world_pos = current_matrix @ vert.co
        axis_pos = world_pos[blend_axis_idx]

        # Check positive edge blend zone
        if axis_pos >= positive_blend_start:
            blend_factor = (axis_pos - positive_blend_start) / blend_width if blend_width > 0 else 0
            smooth_factor = smoothstep(blend_factor)

            # Target position: target vertex's negative edge + positive offset
            # We want the minimum (negative edge) of the target mesh, offset to positive direction
            target_pos = target_verts[i].copy()
            target_pos[blend_axis_idx] += mesh_offset_positive

            # Blend in world space
            new_world_pos = world_pos.lerp(target_pos, smooth_factor)

            # Convert back to local space
            vert.co = current_matrix.inverted() @ new_world_pos
            blended_positive += 1

        # Check negative edge blend zone
        elif axis_pos <= negative_blend_end:
            blend_factor = (negative_blend_end - axis_pos) / blend_width if blend_width > 0 else 0
            smooth_factor = smoothstep(blend_factor)

            # Target position: target vertex's positive edge + negative offset
            target_pos = target_verts[i].copy()
            target_pos[blend_axis_idx] += mesh_offset_negative

            # Blend in world space
            new_world_pos = world_pos.lerp(target_pos, smooth_factor)

            # Convert back to local space
            vert.co = current_matrix.inverted() @ new_world_pos
            blended_negative += 1

    print(f"    Blended {blended_positive} vertices on positive edge, {blended_negative} on negative edge")

    # Cleanup
    eval_obj.to_mesh_clear()

    # Restore original frame
    bpy.context.scene.frame_set(original_frame)

    # Update mesh
    current_mesh.update()

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

def export_chunks_for_frame(fluid_surface, frame, quality_ratio, output_dir, chunks_x, chunks_y, fixed_chunk_bounds, skip_existing_files=True, blend_config=None):
    """Export all chunks for a single frame at specified quality using fixed world coordinates"""
    # Check if all chunks for this frame already exist
    # For 3x1 configuration: we export 2 files (0_0 contains chunks 0&2, 1_0 is middle chunk)
    if skip_existing_files:
        all_chunks_exist = True
        # Check for combined chunk file (0_0) and middle chunk file (1_0)
        for j in range(chunks_y):
            chunk_0_filename = f"0_{j}_mesh_{frame}.obj"
            chunk_1_filename = f"1_{j}_mesh_{frame}.obj"
            chunk_0_filepath = os.path.join(output_dir, chunk_0_filename)
            chunk_1_filepath = os.path.join(output_dir, chunk_1_filename)
            if not os.path.exists(chunk_0_filepath) or not os.path.exists(chunk_1_filepath):
                all_chunks_exist = False
                break

        if all_chunks_exist:
            print(f"  Frame {frame}: All chunks already exist, skipping")
            return

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

    # Apply seamless blending BEFORE decimation (if configured)
    if blend_config and blend_config.get('enabled', False):
        # Apply boolean modifier first to get the correct mesh shape
        bpy.context.view_layer.objects.active = work_obj
        work_obj.select_set(True)
        if bool_boundary and "Boolean" in work_obj.modifiers:
            # Ensure modifier is enabled before applying
            bool_mod = work_obj.modifiers["Boolean"]
            bool_mod.show_viewport = True
            bool_mod.show_render = True
            bpy.ops.object.modifier_apply(modifier="Boolean")
            print(f"  Applied Boolean modifier for blending")

        # Apply seamless blending to the mesh vertices
        apply_seamless_blending(
            work_obj=work_obj,
            fluid_surface=fluid_surface,
            current_frame=frame,
            frame_offset=blend_config['frame_offset'],
            reference_offset=blend_config['reference_offset'],
            blend_axis_idx=blend_config['blend_axis_idx'],
            blend_width_percent=blend_config['blend_width_percent']
        )

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

    # Debug: Show actual mesh bounds vs fixed chunk boundaries
    print(f"  Fixed chunk boundaries: primary [{primary_min:.2f}, {primary_max:.2f}], secondary [{secondary_min:.2f}, {secondary_max:.2f}]")
    print(f"  Current mesh bounds: min={bounds['min']}, max={bounds['max']}")
    print(f"  Mesh world matrix: {final_obj.matrix_world}")

    # FR-12: Remove the flat bottom created by the boolean modifier
    # This removes only nearly-horizontal downward-facing faces (the cut plane bottom)
    # while preserving the underside of breaking waves (which have varied normals)
    print(f"  FR-12: Removing flat bottom plane created by boolean modifier")
    bm_full = bmesh.new()
    bm_full.from_mesh(final_obj.data)

    # Recalculate normals to ensure they're correct
    bmesh.ops.recalc_face_normals(bm_full, faces=bm_full.faces)
    bm_full.normal_update()

    # Count faces before removal
    total_faces_before = len(bm_full.faces)

    # Find faces that are nearly horizontal and pointing downward
    # These are the flat bottom faces created by the boolean modifier
    # Breaking wave undersides will have varied normals (not purely vertical)
    faces_to_remove = []
    HORIZONTAL_THRESHOLD = -0.95  # Normal Z must be less than -0.95 (nearly straight down)

    for face in bm_full.faces:
        # Only remove faces that are nearly perfectly horizontal and pointing down
        # This preserves curved/angled surfaces like wave undersides
        if face.normal.z < HORIZONTAL_THRESHOLD:
            faces_to_remove.append(face)

    # Remove the flat bottom faces
    bmesh.ops.delete(bm_full, geom=faces_to_remove, context='FACES')

    # Count faces after removal
    total_faces_after = len(bm_full.faces)

    print(f"  Removed {len(faces_to_remove)} nearly-horizontal bottom faces (before: {total_faces_before}, after: {total_faces_after})")

    # Update the mesh with cleaned geometry
    bm_full.to_mesh(final_obj.data)
    bm_full.free()
    final_obj.data.update()

    # Export each chunk
    os.makedirs(output_dir, exist_ok=True)

    # Calculate adjusted chunk boundaries for 3x1 configuration:
    # - Middle chunk (i=1): 20% bigger
    # - Side chunks (i=0, i=2): 10% smaller each
    # Total size remains the same: -0.1 + 1.2 + (-0.1) = 1.0
    total_primary_size = primary_max - primary_min
    original_chunk_size = total_primary_size / chunks_x  # Each chunk was 1/3

    # New sizes (as fractions of total):
    # Chunk 0: 1/3 - 10% = 1/3 * 0.9 = 0.3
    # Chunk 1: 1/3 + 20% = 1/3 * 1.2 = 0.4
    # Chunk 2: 1/3 - 10% = 1/3 * 0.9 = 0.3
    chunk_sizes = [
        original_chunk_size * 0.9,  # Chunk 0: 10% smaller
        original_chunk_size * 1.2,  # Chunk 1: 20% bigger
        original_chunk_size * 0.9   # Chunk 2: 10% smaller
    ]

    # Calculate cumulative boundaries
    chunk_boundaries = [primary_min]
    for size in chunk_sizes:
        chunk_boundaries.append(chunk_boundaries[-1] + size)

    print(f"  Adjusted chunk boundaries: {chunk_boundaries}")
    print(f"  Chunk 0 size: {chunk_sizes[0]:.2f} (90% of original)")
    print(f"  Chunk 1 size: {chunk_sizes[1]:.2f} (120% of original)")
    print(f"  Chunk 2 size: {chunk_sizes[2]:.2f} (90% of original)")

    for i in range(chunks_x):
        for j in range(chunks_y):
            # Use adjusted boundaries for primary axis
            p_start = chunk_boundaries[i]
            p_end = chunk_boundaries[i + 1]
            s_start = secondary_min + j * chunk_secondary
            s_end = secondary_min + (j + 1) * chunk_secondary

            # Create bounding box planes for this chunk
            # We'll use bisect to create clean straight edges
            bm = bmesh.new()
            bm.from_mesh(final_obj.data)

            # Apply world transform to bmesh
            bm.transform(final_obj.matrix_world)

            print(f"    Chunk ({i},{j}): Initial faces: {len(bm.faces)}, verts: {len(bm.verts)}")

            # Create plane normals and points for bisecting
            # For min boundaries: normal points inward (positive direction), keeps geometry >= p_start
            # For max boundaries: normal points inward (negative direction), keeps geometry <= p_end

            # Bisect along primary axis (min) - keep everything >= p_start
            plane_no_p_min = Vector([0, 0, 0])
            plane_no_p_min[primary_idx] = -1.0  # Normal points in negative direction, clear_outer removes < p_start
            plane_co_p_min = Vector([0, 0, 0])
            plane_co_p_min[primary_idx] = p_start

            # Bisect along primary axis (max) - keep everything <= p_end
            plane_no_p_max = Vector([0, 0, 0])
            plane_no_p_max[primary_idx] = 1.0  # Normal points in positive direction, clear_outer removes > p_end
            plane_co_p_max = Vector([0, 0, 0])
            plane_co_p_max[primary_idx] = p_end

            # Bisect along secondary axis (min) - keep everything >= s_start
            plane_no_s_min = Vector([0, 0, 0])
            plane_no_s_min[secondary_idx] = -1.0
            plane_co_s_min = Vector([0, 0, 0])
            plane_co_s_min[secondary_idx] = s_start

            # Bisect along secondary axis (max) - keep everything <= s_end
            plane_no_s_max = Vector([0, 0, 0])
            plane_no_s_max[secondary_idx] = 1.0
            plane_co_s_max = Vector([0, 0, 0])
            plane_co_s_max[secondary_idx] = s_end

            # FR-11: Perform bisect operations to cut the mesh at chunk boundaries
            # This creates clean straight edges
            print(f"    Chunk ({i},{j}): Bisecting primary min at {p_start:.2f}")
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_p_min, plane_no=plane_no_p_min, clear_outer=True)
            print(f"    Chunk ({i},{j}): After primary min bisect: faces={len(bm.faces)}, verts={len(bm.verts)}")

            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_p_max, plane_no=plane_no_p_max, clear_outer=True)
            print(f"    Chunk ({i},{j}): After primary max bisect: faces={len(bm.faces)}, verts={len(bm.verts)}")

            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_s_min, plane_no=plane_no_s_min, clear_outer=True)
            print(f"    Chunk ({i},{j}): After secondary min bisect: faces={len(bm.faces)}, verts={len(bm.verts)}")

            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=plane_co_s_max, plane_no=plane_no_s_max, clear_outer=True)
            print(f"    Chunk ({i},{j}): After secondary max bisect: faces={len(bm.faces)}, verts={len(bm.verts)}")

            # Create chunk mesh
            chunk_mesh = bpy.data.meshes.new(f"chunk_{i}_{j}_{frame}")
            bm.to_mesh(chunk_mesh)
            bm.free()

            chunk_obj = bpy.data.objects.new(f"chunk_{i}_{j}_{frame}", chunk_mesh)
            bpy.context.collection.objects.link(chunk_obj)

            # Store chunk objects for later export
            if i == 0:
                chunk_0_obj = chunk_obj
                chunk_0_mesh = chunk_mesh
            elif i == 1:
                # Export middle chunk (i=1) immediately as separate file
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
            elif i == 2:
                # Combine chunk 0 and chunk 2 into a single file
                chunk_filename = f"0_{j}_mesh_{frame}.obj"
                chunk_filepath = os.path.join(output_dir, chunk_filename)

                # Select both chunk 0 and chunk 2
                bpy.ops.object.select_all(action='DESELECT')
                chunk_0_obj.select_set(True)
                chunk_obj.select_set(True)
                bpy.context.view_layer.objects.active = chunk_0_obj

                # Export both chunks together
                bpy.ops.wm.obj_export(
                    filepath=chunk_filepath,
                    export_selected_objects=True,
                    export_animation=False,
                    forward_axis='X',
                    up_axis='Z',
                    apply_modifiers=True
                )

                # Cleanup both chunk objects
                bpy.data.objects.remove(chunk_0_obj)
                bpy.data.meshes.remove(chunk_0_mesh)
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

# Set up seamless blending configuration
print(f"\n{'='*60}")
print(f"Setting up seamless blending")
print(f"{'='*60}")

blend_config = None
reference_offset = get_reference_mesh_offset(reference_mesh_name)
if reference_offset:
    # Determine blend axis from reference mesh (largest offset component)
    abs_offsets = [abs(reference_offset.x), abs(reference_offset.y), abs(reference_offset.z)]
    blend_axis_idx = abs_offsets.index(max(abs_offsets))
    axis_names = ['x', 'y', 'z']

    print(f"Reference mesh '{reference_mesh_name}' found at position: {reference_offset}")
    print(f"Blend axis (largest offset): {axis_names[blend_axis_idx]} (offset: {reference_offset[blend_axis_idx]:.2f})")

    blend_config = {
        'enabled': True,
        'frame_offset': frame_offset,
        'reference_offset': reference_offset,
        'blend_axis_idx': blend_axis_idx,
        'blend_width_percent': BLEND_WIDTH_PERCENT
    }
    print(f"Seamless blending ENABLED")
else:
    print(f"Warning: Reference mesh '{reference_mesh_name}' not found")
    print(f"Seamless blending DISABLED - edges will not be blended")

# Convert skip_existing string to boolean
skip_existing_files = (skip_existing.lower() == 'skip')

# Initialize timing variables
total_frames_to_export = (end_frame - start_frame + 1) * len(quality_levels)
current_frame_index = 0
frame_times = []
overall_start_time = time.time()

# FR-6, FR-7, FR-8: Process each quality level
for quality_idx, quality_ratio in enumerate(quality_levels):
    quality_name = f"ratio_{str(quality_ratio).replace('.', '_')}"
    quality_folder = f"chunks_{quality_name}"
    output_dir = os.path.join(output_base_dir, quality_folder)

    print(f"\n{'-'*60}")
    print(f"Processing quality level {quality_idx + 1}/{len(quality_levels)}: ratio={quality_ratio}")
    print(f"Output directory: {output_dir}")
    print(f"{'-'*60}")

    # FR-6: Process each frame
    for frame in range(start_frame, end_frame + 1):
        frame_start_time = time.time()

        print(f"\nFrame {frame}:")
        export_chunks_for_frame(fluid_surface, frame, quality_ratio, output_dir, CHUNKS_X, CHUNKS_Y, fixed_chunk_bounds, skip_existing_files, blend_config)

        # Calculate time for this frame
        frame_duration = time.time() - frame_start_time
        frame_times.append(frame_duration)
        current_frame_index += 1

        # Calculate and display time estimate
        if len(frame_times) > 0:
            avg_time_per_frame = sum(frame_times) / len(frame_times)
            frames_remaining = total_frames_to_export - current_frame_index
            estimated_seconds_remaining = avg_time_per_frame * frames_remaining

            # Format time estimate
            hours = int(estimated_seconds_remaining // 3600)
            minutes = int((estimated_seconds_remaining % 3600) // 60)
            seconds = int(estimated_seconds_remaining % 60)

            elapsed_seconds = time.time() - overall_start_time
            elapsed_hours = int(elapsed_seconds // 3600)
            elapsed_minutes = int((elapsed_seconds % 3600) // 60)
            elapsed_secs = int(elapsed_seconds % 60)

            print(f"  Frame completed in {frame_duration:.1f}s")
            print(f"  Progress: {current_frame_index}/{total_frames_to_export} frames ({100*current_frame_index/total_frames_to_export:.1f}%)")
            print(f"  Elapsed: {elapsed_hours}h {elapsed_minutes}m {elapsed_secs}s")
            print(f"  Estimated time remaining: {hours}h {minutes}m {seconds}s")

print(f"\n{'='*60}")
print(f"EXPORT COMPLETE!")
print(f"{'='*60}")
print(f"Processed {len(quality_levels)} quality levels")
print(f"Processed {end_frame - start_frame + 1} frames per quality level")
print(f"Total chunks per frame: {CHUNKS_X * CHUNKS_Y}")
print(f"Total frames exported: {current_frame_index}")

# Calculate and display total time
total_elapsed = time.time() - overall_start_time
total_hours = int(total_elapsed // 3600)
total_minutes = int((total_elapsed % 3600) // 60)
total_seconds = int(total_elapsed % 60)
print(f"Total time: {total_hours}h {total_minutes}m {total_seconds}s")
print(f"{'='*60}")
