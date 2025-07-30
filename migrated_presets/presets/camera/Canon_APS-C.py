import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 22.3
bpy.context.camera.sensor_height = 14.9
bpy.context.camera.sensor_fit = 'HORIZONTAL'