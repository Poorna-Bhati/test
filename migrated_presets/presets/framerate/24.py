import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.scene.render.fps = 24
bpy.context.scene.render.fps_base = 1