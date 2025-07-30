import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 27.90
bpy.context.camera.sensor_height = 18.60
bpy.context.camera.sensor_fit = 'HORIZONTAL'