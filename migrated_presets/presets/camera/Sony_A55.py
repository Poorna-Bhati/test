import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 23.4
bpy.context.camera.sensor_height = 15.6
bpy.context.camera.sensor_fit = 'HORIZONTAL'