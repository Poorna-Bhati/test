import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 6.97
bpy.context.camera.sensor_height = 3.92
bpy.context.camera.sensor_fit = 'HORIZONTAL'