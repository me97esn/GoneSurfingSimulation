"""
Post-export script to create seamless blended meshes from already-exported OBJ files.

Replicates the verified workflow:
1. Import OBJ chunks for primary frame at origin with Z=90° rotation
2. Import OBJ chunks for adjacent frame at tiling position with Z=90° rotation
3. Blend primary frame edges toward adjacent frame heights
4. Trim primary frame meshes to original bounds + 7%
5. Export preserving original file structure (separate OBJ files per chunk group)

Usage:
    blender --background --python post_export_seamless_blend.py -- \
        --input-dir /hdd/gone_surfing_exports/medium_wave_left/chunks_ratio_0_03 \
        --output-dir /hdd/gone_surfing_exports/medium_wave_left/seamless \
        --start-frame 886 \
        --end-frame 1078 \
        --frame-offset 95 \
        --tiling-x 123.4486 \
        --tiling-y -59.6493
"""
import bpy
import bmesh
from mathutils import Vector
import math
import os
import sys
import argparse
import glob
import time

# Blending parameters
BLEND_WIDTH = 15.0
EXTRA_WIDTH_PERCENT = 0.07  # 7%


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def get_height_at_position(mesh_objs, x, y, search_radius=5.0):
    heights = []
    weights = []
    for obj in mesh_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_xy = math.sqrt((world_pos.x - x)**2 + (world_pos.y - y)**2)
            if dist_xy < search_radius:
                weight = 1.0 / (dist_xy + 0.1)
                heights.append(world_pos.z)
                weights.append(weight)
    if heights:
        total_weight = sum(weights)
        return sum(h * w for h, w in zip(heights, weights)) / total_weight
    return None


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def import_frame(input_dir, frame, location, z_rotation=1.5708):
    """Import OBJ chunks for a frame with given location and Z rotation.
    Does NOT apply transforms - keeps them as object transforms."""
    pattern = os.path.join(input_dir, f"*_mesh_{frame}.obj")
    obj_files = sorted(glob.glob(pattern))
    imported = []
    for obj_file in obj_files:
        bpy.ops.wm.obj_import(filepath=obj_file)
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                obj.rotation_euler.x = 0
                obj.rotation_euler.y = 0
                obj.rotation_euler.z = z_rotation
                obj.location = location
                imported.append(obj)
    return imported


def blend_mesh_edges(primary_objs, adjacent_objs, blend_width=BLEND_WIDTH):
    """Blend primary frame edges toward adjacent frame heights. Does not join meshes."""
    max_x_primary = -float('inf')
    min_x_adjacent = float('inf')

    for obj in primary_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            max_x_primary = max(max_x_primary, (matrix @ v.co).x)

    for obj in adjacent_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            min_x_adjacent = min(min_x_adjacent, (matrix @ v.co).x)

    print(f"  Gap: primary max X={max_x_primary:.2f}, adjacent min X={min_x_adjacent:.2f}, "
          f"gap={min_x_adjacent - max_x_primary:.2f}")

    modified = 0
    for obj in primary_objs:
        matrix = obj.matrix_world
        matrix_inv = matrix.inverted()
        for v in obj.data.vertices:
            world_pos = matrix @ v.co
            dist_from_edge = max_x_primary - world_pos.x
            if dist_from_edge < blend_width:
                blend_factor = 1.0 - (dist_from_edge / blend_width)
                smooth_factor = smoothstep(blend_factor)
                target_height = get_height_at_position(
                    adjacent_objs, min_x_adjacent, world_pos.y, search_radius=10.0)
                if target_height is not None:
                    overlap_target_x = min_x_adjacent + blend_width * 0.3
                    new_x = world_pos.x + (overlap_target_x - world_pos.x) * smooth_factor
                    new_z = world_pos.z + (target_height - world_pos.z) * smooth_factor * 0.7
                    v.co = matrix_inv @ Vector((new_x, world_pos.y, new_z))
                    modified += 1
        obj.data.update()
    print(f"  Blended {modified} vertices")


def trim_mesh(obj, min_x, max_x):
    """Trim a single mesh to X bounds by removing vertices outside."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    matrix = obj.matrix_world
    verts_to_delete = [v for v in bm.verts
                       if (matrix @ v.co).x < min_x or (matrix @ v.co).x > max_x]
    deleted = len(verts_to_delete)
    if verts_to_delete:
        bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return deleted


def get_file_groups(objs, frame):
    """Group mesh objects by their original file structure.
    chunk_0_0 and chunk_2_0 go in 0_0_mesh_<frame>.obj
    chunk_1_0 goes in 1_0_mesh_<frame>.obj"""
    groups = {'0_0': [], '1_0': []}
    for obj in objs:
        name = obj.name
        if 'chunk_0_0' in name or 'chunk_2_0' in name:
            groups['0_0'].append(obj)
        elif 'chunk_1_0' in name:
            groups['1_0'].append(obj)
        else:
            # Fallback
            groups['0_0'].append(obj)
    return groups


def reset_object_transforms(objects):
    """Reset object transforms to identity before export.
    The OBJ exporter writes local-space v.co values. Since blending writes
    results back to local space via matrix_inv, v.co is already in the
    original OBJ coordinate space. Zeroing the object transform ensures
    the exporter writes these local coords directly."""
    for obj in objects:
        if obj.type == 'MESH':
            obj.location = (0, 0, 0)
            obj.rotation_euler = (0, 0, 0)
            obj.data.update()


def export_obj_with_objects(filepath, objects):
    """Export specific objects to an OBJ file."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.wm.obj_export(
        filepath=filepath,
        export_selected_objects=True,
        export_materials=False,
        export_uv=False,
        export_normals=True,
        forward_axis='Y',
        up_axis='Z'
    )


def process_frame(input_dir, output_dir, frame, adjacent_frame, tiling_pos):
    """Process a single frame: import, blend, trim, export with original file structure."""
    frame_start = time.time()
    print(f"\n{'='*60}")
    print(f"Frame {frame} (adjacent: {adjacent_frame})")
    print(f"{'='*60}")

    clear_scene()

    # Import primary frame at origin
    primary_objs = import_frame(input_dir, frame, (0, 0, 0))
    if not primary_objs:
        print(f"  ERROR: No meshes found for frame {frame}")
        return False

    # Import adjacent frame at tiling position
    adjacent_objs = import_frame(input_dir, adjacent_frame, tiling_pos)
    if not adjacent_objs:
        print(f"  ERROR: No meshes found for frame {adjacent_frame}")
        return False

    print(f"  Imported {len(primary_objs)} primary + {len(adjacent_objs)} adjacent meshes")

    # Get primary X bounds before blending
    all_xs = []
    for obj in primary_objs:
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            all_xs.append((matrix @ v.co).x)
    original_min_x = min(all_xs)
    original_max_x = max(all_xs)

    # Blend
    blend_mesh_edges(primary_objs, adjacent_objs, blend_width=BLEND_WIDTH)

    # Trim
    original_width = original_max_x - original_min_x
    extra_width = original_width * EXTRA_WIDTH_PERCENT
    trim_min_x = original_min_x
    trim_max_x = original_max_x + extra_width

    for obj in primary_objs:
        deleted = trim_mesh(obj, trim_min_x, trim_max_x)
        if deleted > 0:
            print(f"  Trimmed {obj.name}: {deleted} vertices removed")

    # Reset transforms so exported OBJ matches input orientation
    reset_object_transforms(primary_objs)

    # Export preserving file structure
    file_groups = get_file_groups(primary_objs, frame)
    for prefix, objs in file_groups.items():
        if objs:
            output_path = os.path.join(output_dir, f"{prefix}_mesh_{frame}.obj")
            export_obj_with_objects(output_path, objs)

    elapsed = time.time() - frame_start
    print(f"  Done in {elapsed:.1f}s")
    return True


def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description='Post-export seamless blending')
    parser.add_argument('--input-dir', required=True, help='Input directory with exported OBJs')
    parser.add_argument('--output-dir', required=True, help='Output directory for seamless meshes')
    parser.add_argument('--start-frame', type=int, required=True, help='Start frame number')
    parser.add_argument('--end-frame', type=int, required=True, help='End frame number')
    parser.add_argument('--frame-offset', type=int, required=True,
                        help='Frame offset for adjacent mesh (positive)')
    parser.add_argument('--tiling-x', type=float, required=True, help='X position for tiling')
    parser.add_argument('--tiling-y', type=float, default=0.0, help='Y position for tiling')
    parser.add_argument('--tiling-z', type=float, default=0.0, help='Z position for tiling')
    parser.add_argument('--single-frame', type=int, help='Process only this frame (for testing)')

    args = parser.parse_args(argv)
    os.makedirs(args.output_dir, exist_ok=True)

    tiling_pos = (args.tiling_x, args.tiling_y, args.tiling_z)

    print(f"Post-Export Seamless Blend")
    print(f"{'='*60}")
    print(f"Input:  {args.input_dir}")
    print(f"Output: {args.output_dir}")
    print(f"Frames: {args.start_frame} - {args.end_frame}")
    print(f"Frame offset: {args.frame_offset}")
    print(f"Tiling position: {tiling_pos}")
    print(f"Blend width: {BLEND_WIDTH}")
    print(f"Extra width: {EXTRA_WIDTH_PERCENT*100:.0f}%")

    if args.single_frame is not None:
        frames = [args.single_frame]
    else:
        frames = list(range(args.start_frame, args.end_frame + 1))

    total_start = time.time()
    success_count = 0
    fail_count = 0

    for i, frame in enumerate(frames):
        # Calculate adjacent frame with wrapping
        adjacent_frame = frame + args.frame_offset
        if adjacent_frame > args.end_frame:
            adjacent_frame = args.start_frame + (adjacent_frame - args.end_frame - 1)
        elif adjacent_frame < args.start_frame:
            adjacent_frame = args.end_frame - (args.start_frame - adjacent_frame - 1)

        print(f"\n[{i+1}/{len(frames)}] ", end="")

        try:
            if process_frame(args.input_dir, args.output_dir, frame, adjacent_frame, tiling_pos):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1

    total_elapsed = time.time() - total_start
    hours = int(total_elapsed // 3600)
    minutes = int((total_elapsed % 3600) // 60)
    seconds = int(total_elapsed % 60)

    print(f"\n{'='*60}")
    print(f"Complete! {success_count} succeeded, {fail_count} failed")
    print(f"Total time: {hours}h {minutes}m {seconds}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
