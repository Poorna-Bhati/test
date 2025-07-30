import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 5.76
bpy.context.camera.sensor_height = 4.29
bpy.context.camera.lens = 2.77

bpy.context.camera.sensor_fit = 'AUTO'