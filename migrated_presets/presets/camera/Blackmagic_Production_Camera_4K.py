import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 21.12
bpy.context.camera.sensor_height = 11.88
bpy.context.camera.sensor_fit = 'HORIZONTAL'