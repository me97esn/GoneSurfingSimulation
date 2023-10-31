"Run this script from within Blender, after the mesh has been selected."
start_frame = 752
end_frame = 1325
result_folder = '/hdd/gone_surfing_exports/medium_wave_left/waves_display_high_res_smaller_domain'

scn = bpy.context.scene
for frame in range(start_frame, end_frame+1):
    scn.frame_set(frame)
    filepath = '{0}/mesh_{1}.x3d'.format(result_folder, '%06d' % frame)
    # filepath = '{0}/waves_display_{1}.x3d'.format(result_folder, '%06d' % frame)
    bpy.ops.export_scene.x3d(use_selection=True, use_normals=True,filepath=filepath, axis_forward='Z', axis_up='Y', use_mesh_modifiers=True)
