import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 23.1
bpy.context.camera.sensor_height = 15.4
bpy.context.camera.sensor_fit = 'HORIZONTAL'