import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 4.8
bpy.context.camera.sensor_height = 3.6
bpy.context.camera.lens = 4.20
bpy.context.camera.sensor_fit = 'HORIZONTAL'