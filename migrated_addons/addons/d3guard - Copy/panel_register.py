'''
Created on Mar 7, 2020

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
from odcutils import get_settings

class VIEW3D_PT_D3DualArchRegister(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="TOOLS"
    bl_category = "Dental"
    bl_label = "Register Your Product"
    bl_context = ""
    
    def draw(self, context):

        sce = bpy.context.scene
        layout = self.layout
        prefs = get_settings()
        
        
        row = layout.row()
        row.label(text = "Register D3DualArch")
        #row = layout.row()
        #row.operator("wm.url_open", text = "", icon="INFO").url = "https://www.sleepsolutionsbyross.com/oral-appliances"

            
        row = layout.row()
        row.operator( "d3tool.services_get_token", text = 'Log In')
                
                
#class VIEW3D_PT_ProductNotPurchase(bpy.types.Panel):
#    bl_space_type = "VIEW_3D"
#    bl_region_type="TOOLS"
#    bl_category = "Dental"
#    bl_label = "Purchase This Product"
#    bl_context = ""
    
#    def draw(self, context):
#
#        sce = bpy.context.scene
##        layout = self.layout
 #       prefs = get_settings()
        
        
#        row = layout.row()
#        row.label(text = "Purchase D3DualArch")
        #row = layout.row()
#        row.operator("wm.url_open", text = "", icon="INFO").url = "https://www.sleepsolutionsbyross.com/oral-appliances"

            
        #row = layout.row()
        #row.operator( "d3tool.com_test_login", text = 'Log In')
               
        
def register():
    bpy.utils.register_class(VIEW3D_PT_D3DualArchRegister)
    
def unregister():
    bpy.utils.register_class(VIEW3D_PT_D3DualArchRegister)