import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 4.54
bpy.context.camera.sensor_height = 3.42
bpy.context.camera.lens = 3.85
bpy.context.camera.sensor_fit = 'HORIZONTAL'