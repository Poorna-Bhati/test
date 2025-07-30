import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
track = bpy.context.edit_movieclip.tracking.tracks.active

track.color = (1.0, 0.0, 1.0)
track.use_custom_color = True