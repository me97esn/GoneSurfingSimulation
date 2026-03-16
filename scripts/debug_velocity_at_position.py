"""
Debug script to check velocity sampling at a specific Blender position.
This helps diagnose coordinate transformation issues.
"""

import bpy
import os
import struct
from mathutils import Vector
from mathutils.kdtree import KDTree

def read_bobj(filepath):
    """Read positions from .bobj file."""
    with open(filepath, 'rb') as f:
        num_vertices = struct.unpack('<I', f.read(4))[0]
        data = struct.unpack(f'<{num_vertices * 3}f', f.read(num_vertices * 12))
    return [(data[i*3], data[i*3+1], data[i*3+2]) for i in range(num_vertices)]


# Configuration
frame = 934  # Actual frame from game
target_blender_x = 85.00  # From debug sphere
target_blender_y = 356.85

# Paths
cache_folder = "D:\\flip_fluid_cache\\flip_fluid_cache_8\\bakefiles"
bobj_path = os.path.join(cache_folder, f"{frame:06d}.bobj")
blur_path = os.path.join(cache_folder, f"blur{frame:06d}.bobj")

# Get objects
fluid_surface = bpy.data.objects.get("fluid_surface")
flip_domain = bpy.data.objects.get("Flip Domain.001")

if not flip_domain:
    flip_domain = bpy.data.objects.get("Flip_Domain")

print(f"\\n{'='*80}")
print(f"DEBUG: Velocity sampling at Blender position ({target_blender_x}, {target_blender_y})")
print(f"{'='*80}")

if fluid_surface:
    print(f"\\nfluid_surface location: {fluid_surface.location}")
else:
    print(f"\\nWARNING: fluid_surface object not found!")

if flip_domain:
    print(f"FLIP domain location: {flip_domain.location}")
else:
    print(f"WARNING: FLIP domain object not found!")

# Read FLIP particles
print(f"\\nReading FLIP particles from frame {frame}...")
positions = read_bobj(bobj_path)
velocities = read_bobj(blur_path)

print(f"Loaded {len(positions)} particles")

# Show particle position range (in FLIP domain local space)
x_coords = [p[0] for p in positions]
y_coords = [p[1] for p in positions]
print(f"Particle X range (FLIP local): [{min(x_coords):.2f}, {max(x_coords):.2f}]")
print(f"Particle Y range (FLIP local): [{min(y_coords):.2f}, {max(y_coords):.2f}]")

# Transform to world space
flip_domain_loc = flip_domain.location if flip_domain else Vector((0, 0, 0))
print(f"\\nTransforming particles to world space using offset: ({flip_domain_loc.x:.2f}, {flip_domain_loc.y:.2f}, {flip_domain_loc.z:.2f})")

tree = KDTree(len(positions))
for i, p in enumerate(positions):
    world_x = p[0] + flip_domain_loc.x
    world_y = p[1] + flip_domain_loc.y
    tree.insert((world_x, world_y, 0.0), i)
tree.balance()

# Show transformed particle range
x_world = [p[0] + flip_domain_loc.x for p in positions]
y_world = [p[1] + flip_domain_loc.y for p in positions]
print(f"Particle X range (world): [{min(x_world):.2f}, {max(x_world):.2f}]")
print(f"Particle Y range (world): [{min(y_world):.2f}, {max(y_world):.2f}]")

# Sample at target position
fluid_surface_loc = fluid_surface.location if fluid_surface else Vector((0, 0, 0))
print(f"\\nSampling at Blender data position: ({target_blender_x}, {target_blender_y})")
print(f"fluid_surface location: ({fluid_surface_loc.x:.2f}, {fluid_surface_loc.y:.2f}, {fluid_surface_loc.z:.2f})")

# Transform target position to world space
target_world_x = target_blender_x + fluid_surface_loc.x
target_world_y = target_blender_y + fluid_surface_loc.y

print(f"Target world position: ({target_world_x:.2f}, {target_world_y:.2f})")

# Find nearest particle
_co, idx, dist = tree.find((target_world_x, target_world_y, 0.0))

print(f"\\nNearest particle:")
print(f"  Index: {idx}")
print(f"  Distance: {dist:.4f}")
print(f"  Particle position (FLIP local): ({positions[idx][0]:.2f}, {positions[idx][1]:.2f}, {positions[idx][2]:.2f})")
print(f"  Particle position (world): ({positions[idx][0] + flip_domain_loc.x:.2f}, {positions[idx][1] + flip_domain_loc.y:.2f}, {positions[idx][2] + flip_domain_loc.z:.2f})")
print(f"  Velocity: ({velocities[idx][0]:.6f}, {velocities[idx][1]:.6f}, {velocities[idx][2]:.6f})")

# Find nearest 10 particles
print(f"\\n10 nearest particles:")
for i in range(min(10, len(positions))):
    _co, idx, dist = tree.find_n((target_world_x, target_world_y, 0.0), i+1)[-1]
    vmag = (velocities[idx][0]**2 + velocities[idx][1]**2 + velocities[idx][2]**2)**0.5
    print(f"  {i+1:2d}. idx={idx:5d} dist={dist:6.2f} pos_local=({positions[idx][0]:7.2f},{positions[idx][1]:7.2f}) vel_mag={vmag:.5f}")

print(f"\\n{'='*80}")
