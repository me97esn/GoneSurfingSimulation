import bpy
import os

print("\n=== CHECKING WHITE WATER CACHE AND VISIBILITY ===")

# Find the FLIP domain
flip_domain = None
for obj in bpy.data.objects:
    if 'Flip Domain' in obj.name:
        flip_domain = obj
        print(f"\nFound FLIP domain: {flip_domain.name}")
        break

if flip_domain:
    # Get the FLIP fluid properties
    if hasattr(flip_domain, 'flip_fluid'):
        ff = flip_domain.flip_fluid
        print(f"FLIP Fluid type: {ff.object_type}")

        if ff.object_type == 'TYPE_DOMAIN':
            domain = ff.domain
            print(f"\nWhitewater simulation enabled: {domain.whitewater.enable_whitewater_simulation}")
            print(f"Whitewater visibility in viewport: {domain.surface.whitewater_view_settings_mode}")
            print(f"Whitewater visibility in render: {domain.surface.whitewater_render_settings_mode}")
            print(f"Cache path: {domain.cache.get_cache_abspath()}")

            # Check mesh cache settings
            print(f"\nMesh cache settings:")
            print(f"  Foam mesh mode: {domain.whitewater.foam_mesh_mode}")
            print(f"  Bubble mesh mode: {domain.whitewater.bubble_mesh_mode}")
            print(f"  Spray mesh mode: {domain.whitewater.spray_mesh_mode}")
            print(f"  Dust mesh mode: {domain.whitewater.dust_mesh_mode}")

# Check white water objects
print("\n=== WHITE WATER OBJECTS ===")
ww_objects = ['whitewater_foam', 'whitewater_bubble', 'whitewater_spray', 'whitewater_dust']

for obj_name in ww_objects:
    if obj_name in bpy.data.objects:
        obj = bpy.data.objects[obj_name]
        print(f"\n{obj_name}:")
        print(f"  Type: {obj.type}")
        print(f"  Hide viewport: {obj.hide_viewport}")
        print(f"  Hide render: {obj.hide_render}")

        # Check modifiers
        if len(obj.modifiers) > 0:
            print(f"  Modifiers:")
            for mod in obj.modifiers:
                print(f"    - {mod.name} ({mod.type})")
                if mod.type == 'MESH_CACHE':
                    print(f"      File path: {mod.filepath}")
                    print(f"      File format: {mod.cache_format}")

        # Check at frame 752
        bpy.context.scene.frame_set(752)
        depsgraph = bpy.context.evaluated_depsgraph_get()

        # Try to get mesh data
        try:
            obj_eval = obj.evaluated_get(depsgraph)
            if obj_eval.type == 'MESH':
                mesh = obj_eval.to_mesh()
                print(f"  Vertices at frame 752: {len(mesh.vertices)}")
                obj_eval.to_mesh_clear()
        except Exception as e:
            print(f"  Error getting mesh: {e}")

# Check cache directory
cache_dir = "/hdd/flip_fluid_cache/flip_fluid_cache_8"
if os.path.exists(cache_dir):
    print(f"\n=== CACHE DIRECTORY: {cache_dir} ===")

    # Check for whitewater cache files
    ww_cache_dir = os.path.join(cache_dir, "bakefiles", "whitewater")
    if os.path.exists(ww_cache_dir):
        print(f"Whitewater cache exists: {ww_cache_dir}")

        # List some files
        files = os.listdir(ww_cache_dir)
        print(f"Number of files: {len(files)}")
        if files:
            print(f"Sample files: {files[:5]}")
    else:
        print(f"No whitewater cache found at: {ww_cache_dir}")
else:
    print(f"\nCache directory does not exist: {cache_dir}")
