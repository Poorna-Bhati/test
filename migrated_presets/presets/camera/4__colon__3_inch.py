import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 17.31
bpy.context.camera.sensor_height = 12.98
bpy.context.camera.sensor_fit = 'HORIZONTAL'