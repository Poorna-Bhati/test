import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 4.68
bpy.context.camera.sensor_height = 2.633
bpy.context.camera.sensor_fit = 'HORIZONTAL'