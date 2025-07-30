import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 22.2
bpy.context.camera.sensor_height = 14.7
bpy.context.camera.sensor_fit = 'HORIZONTAL'