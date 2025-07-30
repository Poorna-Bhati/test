import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
op = bpy.context.active_operator

op.radius = 0.4
op.arc_div = 8
op.lin_div = 0
op.size = (1.5, 3.0, 1.0)
op.div_type = 'ALL'