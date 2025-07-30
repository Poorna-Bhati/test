import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 15.81
bpy.context.camera.sensor_height = 8.88
bpy.context.camera.sensor_fit = 'HORIZONTAL'