import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
op = bpy.context.active_operator

op.radius = 0.25
op.arc_div = 8
op.lin_div = 0
op.size = (2.0, 2.0, 2.0)
op.div_type = 'CORNERS'