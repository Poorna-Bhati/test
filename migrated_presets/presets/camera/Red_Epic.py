import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 30.0
bpy.context.camera.sensor_height = 15.0
bpy.context.camera.sensor_fit = 'HORIZONTAL'