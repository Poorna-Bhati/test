import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
bpy.context.fluid.settings.viscosity_base = 2.0
bpy.context.fluid.settings.viscosity_exponent = 3