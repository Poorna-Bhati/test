import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 12.52
bpy.context.camera.sensor_height = 7.41
bpy.context.camera.sensor_fit = 'HORIZONTAL'