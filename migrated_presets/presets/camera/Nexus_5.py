import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 4.5
bpy.context.camera.sensor_height = 3.37
bpy.context.camera.lens = 3.91
bpy.context.camera.sensor_fit = 'HORIZONTAL'