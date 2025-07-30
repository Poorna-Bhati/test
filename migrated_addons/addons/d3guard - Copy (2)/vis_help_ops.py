'''
Created on Sep 27, 2020

@author: Patrick
'''


import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement


class D3DUAL_OT_vis_help_op_1(bpy.types.Operator):
    '''Calculates a blocked out and offset model for mandible'''
    bl_idname = 'd3dual.vis_help_op_1'
    bl_label = "Hide All Non-Essential Models"
    bl_options = {'REGISTER','UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        return  True
    
    
    def execute(self, context):
        
        print('dunno')