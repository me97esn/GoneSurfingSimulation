"""
Export FLIP Fluids whitewater particles directly from cache files.
This bypasses the need for Blender to load the mesh cache.
"""
import os
import struct

# Configuration
start_frame = 752
end_frame = 1325
output_dir = "/hdd/gone_surfing_exports/medium_wave_left/white_water"
cache_dir = "/hdd/flip_fluid_cache/flip_fluid_cache_8/bakefiles"

print(f"\n=== EXPORTING WHITEWATER FROM FLIP CACHE ===")
print(f"Cache dir: {cache_dir}")
print(f"Output dir: {output_dir}")
print(f"Frame range: {start_frame} to {end_frame}")

# Create output directory
os.makedirs(output_dir, exist_ok=True)

def read_wwp_file(filepath):
    """Read a FLIP Fluids whitewater particle (.wwp) file."""
    particles = []

    try:
        with open(filepath, 'rb') as f:
            # Read header
            # WWP format: https://github.com/rlguy/Blender-FLIP-Fluids/wiki/Particle-Data-File-Format

            # Read number of particles (4 bytes, unsigned int)
            num_particles_bytes = f.read(4)
            if len(num_particles_bytes) < 4:
                return particles

            num_particles = struct.unpack('I', num_particles_bytes)[0]

            print(f"  Reading {num_particles} particles from {os.path.basename(filepath)}")

            # Each particle is 3 floats (x, y, z) = 12 bytes
            for i in range(num_particles):
                particle_data = f.read(12)
                if len(particle_data) < 12:
                    break

                x, y, z = struct.unpack('fff', particle_data)
                particles.append((x, y, z))

        return particles
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return []

# Process each frame
exported_count = 0
for frame in range(start_frame, end_frame + 1):
    # Construct cache file path
    cache_file = os.path.join(cache_dir, f"foam{frame:06d}.wwp")

    if not os.path.exists(cache_file):
        print(f"Frame {frame}: Cache file not found: {cache_file}")
        continue

    # Read particles from cache
    particles = read_wwp_file(cache_file)

    if not particles:
        print(f"Frame {frame}: No particles found")
        continue

    # Write OBJ file
    output_file = os.path.join(output_dir, f"{frame:06d}.obj")

    with open(output_file, 'w') as f:
        f.write("# Whitewater foam particles\n")
        f.write(f"# Frame {frame}\n")
        f.write(f"# Particle count: {len(particles)}\n")
        f.write("o whitewater_foam\n")

        # Write vertices
        for x, y, z in particles:
            f.write(f"v {x} {y} {z}\n")

    exported_count += 1

    if frame % 50 == 0 or frame == start_frame:
        print(f"Frame {frame}: Exported {len(particles)} particles to {output_file}")

print(f"\n✓ Export complete!")
print(f"  Frames exported: {exported_count}")
print(f"  Output directory: {output_dir}")
