import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.camera.sensor_width = 32
bpy.context.camera.sensor_height = 18
bpy.context.camera.sensor_fit = 'AUTO'