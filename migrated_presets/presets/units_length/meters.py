import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
scene = bpy.context.scene

scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0