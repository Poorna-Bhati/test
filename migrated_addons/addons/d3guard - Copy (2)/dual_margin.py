'''
Created on Feb 12, 2020

@author: Patrick
'''

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from segmentation.op_splint_margin.smargin import D3Splint_segmentation_margin


class D3DualArch_mark_max_margin(D3Splint_segmentation_margin):
    """ Draw the maxillary margin """
    operator_id = "d3dual.mark_max_margin"
    bl_idname = "d3dual.mark_max_margin"
    bl_label = "Mark Maxillary Margin"
    bl_description = "Draw the perimeter of the maxillary splint shell"
    
    
    #override
    @classmethod
    def can_start(cls, context):
        ''' Called when tool is invoked to determine if tool can start '''
        if context.mode != 'OBJECT':
            #showErrorMessage('Object Mode please')
            return False
        
        if len(context.scene.odc_splints) == 0:
            return False
        
        splint = context.scene.odc_splints[0]
        
        if splint.max_model == '':
            #showErrorMessage('Need to Set Splint Model')
            return False
        if splint.max_model not in bpy.data.objects:
            #showErrorMessage('Splint Model has been removed')
            return False
        if 'Max Refractory Model' not in bpy.data.objects:
            return False
        
        if bpy.data.filepath == '':
            #enfore saving the file, in case crashes etc.
            return False
        return True
    
    
    #override this
    def start_pre(self):
        splint = bpy.context.scene.odc_splints[0]
        self.load_ob_name = 'Max Margin'
        self.omodel_name = 'Max Refractory Model'
        self.model_name = splint.max_model
        self.out_model_name = 'Max Patch'
        self.done_prop = "max_splint_outline"
        self.ops_record = 'Trim Max:'
        
class D3DualArch_mark_mand_margin(D3Splint_segmentation_margin):
    """ Draw the mandibular margin """
    operator_id = "d3dual.mark_mand_margin"
    bl_idname = "d3dual.mark_mand_margin"
    bl_label = "Mark Mandibular Margin"
    bl_description = "Draw the perimeter of the mandubular splint shell"
    
    
    #override
    @classmethod
    def can_start(cls, context):
        ''' Called when tool is invoked to determine if tool can start '''
        if context.mode != 'OBJECT':
            #showErrorMessage('Object Mode please')
            return False
        
        if len(context.scene.odc_splints) == 0:
            return False
        
        splint = context.scene.odc_splints[0]
        
        if splint.max_model == '':
            #showErrorMessage('Need to Set Splint Model')
            return False
        if splint.max_model not in bpy.data.objects:
            #showErrorMessage('Splint Model has been removed')
            return False
        if 'Mand Refractory Model' not in bpy.data.objects:
            return False
        
        if bpy.data.filepath == '':
            #enfore saving the file, in case crashes etc.
            return False
        return True
    
    
    #override this
    def start_pre(self):
        splint = bpy.context.scene.odc_splints[0]
        self.load_ob_name = 'Mand Margin'
        self.omodel_name = 'Mand Refractory Model'
        self.model_name = splint.mand_model
        self.done_prop = "mand_splint_outline"
        
        self.out_model_name = 'Mand Patch'
        self.ops_record = 'Trim Mand:'
        
        
def register():
    bpy.utils.register_class(D3DualArch_mark_max_margin)
    bpy.utils.register_class(D3DualArch_mark_mand_margin)

def unregister():
    bpy.utils.unregister_class(D3DualArch_mark_max_margin)
    bpy.utils.unregister_class(D3DualArch_mark_mand_margin)
        