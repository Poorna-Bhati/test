import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 24.33
bpy.context.camera.sensor_height = 12.83
bpy.context.camera.sensor_fit = 'HORIZONTAL'