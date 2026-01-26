"""
Render before/after images of the seamless blend test.
"""
import bpy
import os

OUTPUT_DIR = '/tmp/seamless_test'

def setup_camera():
    """Set up camera to view both meshes and the seam area."""
    # Create camera if it doesn't exist
    cam_data = bpy.data.cameras.new(name='TestCam')
    cam_obj = bpy.data.objects.new('TestCamera', cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    return cam_obj


def render_image(filepath, resolution=(1920, 1080)):
    """Render current scene to an image."""
    bpy.context.scene.render.resolution_x = resolution[0]
    bpy.context.scene.render.resolution_y = resolution[1]
    bpy.context.scene.render.resolution_percentage = 100
    bpy.context.scene.render.filepath = filepath
    bpy.context.scene.render.image_settings.file_format = 'PNG'

    # Use workbench for fast preview
    bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
    bpy.context.scene.display.shading.light = 'STUDIO'
    bpy.context.scene.display.shading.color_type = 'MATERIAL'

    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {filepath}")


def main():
    # Load the seamless test blend file
    blend_path = os.path.join(OUTPUT_DIR, 'seamless_998_903.blend')
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    print("Setting up camera...")
    cam = setup_camera()

    # Find the seamless mesh
    seamless_obj = None
    for obj in bpy.data.objects:
        if 'seamless' in obj.name.lower() and obj.type == 'MESH':
            seamless_obj = obj
            break

    if not seamless_obj:
        print("ERROR: No seamless mesh found!")
        return

    print(f"Found seamless mesh: {seamless_obj.name}")

    # Get mesh bounds
    xs = [v.co.x for v in seamless_obj.data.vertices]
    ys = [v.co.y for v in seamless_obj.data.vertices]
    zs = [v.co.z for v in seamless_obj.data.vertices]
    center_x = (min(xs) + max(xs)) / 2
    center_y = (min(ys) + max(ys)) / 2
    center_z = (min(zs) + max(zs)) / 2

    print(f"Mesh bounds: X[{min(xs):.1f}, {max(xs):.1f}] Y[{min(ys):.1f}, {max(ys):.1f}] Z[{min(zs):.1f}, {max(zs):.1f}]")
    print(f"Mesh center: ({center_x:.1f}, {center_y:.1f}, {center_z:.1f})")

    # Detect seam location from mesh bounds
    # The seam is where X values transition (around X=100 for X-axis blending)
    seam_x = (min(xs) + max(xs)) / 2  # Approximate seam center

    # Add material for visibility
    mat = bpy.data.materials.new(name="SeamlessMat")
    mat.diffuse_color = (0.2, 0.5, 0.8, 1.0)  # Blue-ish water color
    seamless_obj.data.materials.append(mat)

    # Hide all other mesh objects
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj != seamless_obj:
            obj.hide_render = True
            obj.hide_viewport = True

    # Render from angles that show the seam area (X ~ seam_x)
    angles = [
        # Looking at seam from front (negative Y direction)
        ("seam_front", (seam_x, center_y - 200, center_z + 100), (0.6, 0, 0)),
        # Looking at seam from side (positive X direction, looking along Y)
        ("seam_side", (seam_x - 100, center_y, center_z + 80), (0.8, 0, -0.5)),
        # Top-down view centered on seam
        ("seam_top", (seam_x, center_y, center_z + 300), (0, 0, 0)),
        # Angled view showing seam transition
        ("seam_angle", (seam_x + 50, center_y - 150, center_z + 100), (0.7, 0, 0.3)),
    ]

    for name, loc, rot in angles:
        cam.location = loc
        cam.rotation_euler = rot
        output_path = os.path.join(OUTPUT_DIR, f"seamless_{name}.png")
        render_image(output_path)

    print("\nRendering complete!")
    print(f"Images saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
