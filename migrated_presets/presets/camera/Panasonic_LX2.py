import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 8.5
bpy.context.camera.sensor_height = 4.78
bpy.context.camera.sensor_fit = 'HORIZONTAL'