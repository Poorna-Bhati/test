'''
https://blender.stackexchange.com/questions/44061/is-there-a-blender-python-ui-code-to-draw-a-horizontal-line-or-vertical-space/44064#44064

'''

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import os
from common_utilities import get_settings

from panels import articulator_panel, stored_positions_panel
import button_draw_handler

class VIEW3D_PT_D3SplintAssitant(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="TOOLS"
    bl_category = "Dental"
    bl_label = "Dual Arch Panel"
    bl_context = ""

    def draw(self, context):
        sce = bpy.context.scene
        layout = self.layout
        
        #split = layout.split()
        #row = layout.row()

        #row.operator("wm.url_open", text = "Wiki", icon="INFO").url = "https://www.sleepsolutionsbyross.com/oral-appliances"
        #row.operator("wm.url_open", text = "Tutorials", icon="ERROR").url = "https://www.sleepsolutionsbyross.com/oral-appliances"
        #row.operator("wm.url_open", text = "Forum", icon="QUESTION").url = "https://www.sleepsolutionsbyross.com/oral-appliances"
        

        row = layout.row()
        row.label(text = "Save/Checkpoints")
        row = layout.row()
        col = row.column()
        col.operator("wm.save_as_mainfile", text = "Save").copy = False
        col.operator("wm.splint_saveincremental", text = "Save Checkpoint")
        
        
class VIEW3D_PT_D3SplintProperties(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="TOOLS"
    bl_category = "Dental"
    bl_label = "Appliance Properties Panel"
    bl_context = ""

    def draw(self, context):
        sce = bpy.context.scene
        layout = self.layout
        
        #split = layout.split()
        row = layout.row()
        
        if len(sce.odc_splints):
            n = sce.odc_splint_index
            splint = sce.odc_splints[n]
        else:
            return
        
        box = layout.box()
        box.label('Splint Properties')
        
        if not hasattr(context.scene , "odc_splints"):
            col = box.column()
            col.label('ERROR with addon installation', icon = 'ERROR')
            return
        elif len(context.scene.odc_splints) == 0:
            row = box.row()
            col = row.column()
            
            
        #    col.prop(prefs, 'default_jaw_type', text = '')
        #    col.prop(prefs, 'default_workflow_type', text = '')
        else:
            if len(context.scene.odc_splints):
                n = context.scene.odc_splint_index
                splint =context.scene.odc_splints[n]
                
                row = box.row()
                
                #col.label('Jaw Type')
                #col = row.column()
                row = box.row() 
                row.label('Max Shel Thickness: {:.2f}mm'.format(splint.max_shell_thickness))
                
                row = box.row() 
                row.label('Mand Shel Thickness: {:.2f}mm'.format(splint.mand_shell_thickness))
                
                row = box.row() 
                row.label('Max Offset: {:.2f}mm'.format(splint.max_passive_value))
                row = box.row() 
                row.label('Mand Offset: {:.2f}mm'.format(splint.mand_passive_value))
                
                
                row = box.row() 
                row.label('Max Undercut: {:.2f}mm'.format(splint.max_undercut_value))
                row = box.row() 
                row.label('Mand Undercut: {:.2f}mm'.format(splint.mand_undercut_value))
                
                
                #col.prop(splint, 'max_shell_thickness')
                #col.prop(splint, 'mand_shell_thickness')
                #col.prop(splint, 'max_passive_value')
                #col.prop(splint, 'mand_passive_value')
                #col.prop(splint, 'max_undercut_value')
                #col.prop(splint, 'mand_undercut_value')
            
                #col.prop(splint, 'workflow_type')
            
            
            else:
                splint = None
 
class VIEW3D_PT_D3DualArticulator(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="UI"
    bl_category = "Articulator"
    bl_label = "Dual Arch Articulator"
    bl_context = "" 
    
    
    
    def draw(self, context):
        sce = bpy.context.scene
        layout = self.layout
        prefs = get_settings()
        
        if len(sce.odc_splints):
            n = sce.odc_splint_index
            splint = sce.odc_splints[n]
        else:
            splint = None 
            
        articulator_panel.draw_articulator_tools(layout, show_data = True)    
        
        box = layout.box()
        stored_positions_panel.draw_store_positions(layout, box, splint)      


def vis_name_trans(row, obj, label):
    row.prop(obj, "hide", text = label,  icon = "RADIOBUT_ON" if obj.hide else "RADIOBUT_OFF")
    
class VIEW3D_PT_D3DualVisHelp(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="UI"
    #bl_category = "Visualization Help"
    bl_label = "Visualization Help"
    bl_context = "" 
    
    
    
    def draw(self, context):
        sce = bpy.context.scene
        layout = self.layout
        prefs = get_settings()
        
        if len(sce.odc_splints):
            n = sce.odc_splint_index
            splint = sce.odc_splints[n]
        else:
            splint = None 
        
        row = layout.row()
        MaxModel = bpy.data.objects.get(splint.get_maxilla())
        if MaxModel:
            vis_name_trans(row, MaxModel, "Maxilla")
            
        MandModel = bpy.data.objects.get(splint.get_mandible())
        if MandModel:
            vis_name_trans(row, MandModel, "Mandible")
            
        row = layout.row()
        MaxModel = bpy.data.objects.get('Splint Shell_MAX')
        if MaxModel:
            vis_name_trans(row, MaxModel, "Max Shell")
            
        MandModel = bpy.data.objects.get('Splint Shell_MAND')
        if MandModel:
            vis_name_trans(row, MandModel, "Mand Shell")
        
        Articulator = bpy.data.objects.get('Articulator')
        if Articulator:
            row = layout.row()
            row.operator("d3dual.show_hide_articulator", text = "Articulator", icon = 'RESTRICT_VIEW_ON' if Articulator.hide else 'RESTRICT_VIEW_OFF').hide = Articulator.hide == False
        
        
        row = layout.row()
        row.label('Attachments')
        row = layout.row()
        row.operator('d3dual.show_all_attachments', text = '', icon = 'RESTRICT_VIEW_OFF')
        row.operator('d3dual.hide_all_attachments', text = '', icon = 'RESTRICT_VIEW_ON')
        #max_model
        #mand_model
        
        #max_shell
        #mand_model
        
        #attachments
        
        
        
          
class VIEW3D_PT_D3DualArch(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="TOOLS"
    bl_category = "Dental"
    bl_label = "Dual Arch Design"
    bl_context = ""
    
    def draw(self, context):

        sce = bpy.context.scene
        layout = self.layout
        prefs = get_settings()
        
        if len(sce.odc_splints):
            n = sce.odc_splint_index
            splint = sce.odc_splints[n]
        else:
            splint = None
        #split = layout.split()

        #row = layout.row()
        #row.label(text="By Patrick Moore and others...")
        #row.operator("wm.url_open", text = "", icon="QUESTION").url = "https://sites.google.com/site/blenderdental/contributors"
        
        row = layout.row()
        row.label(text = "Import Assets")
        #row = layout.row()
        #row.operator("wm.url_open", text = "", icon="INFO").url = "https://www.sleepsolutionsbyross.com/oral-appliances"

        if not hasattr(context.scene , "odc_splints"):
            return

        else:
            if len(context.scene.odc_splints):
                n = context.scene.odc_splint_index
                splint =context.scene.odc_splints[n]
    
            else:
                splint = None
            
            #row = box.row()
            #col = row.column()
            #col.label('Jaw Type')
            #col = row.column()
            #col.prop(splint, 'jaw_type', text = '')
            #col.prop(splint, 'workflow_type', text = '')
            
        row = layout.row()
        row.operator("import_mesh.stl", text = 'Import STL Models')
                
        
        if splint and splint.max_model_set: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        row = layout.row()
        row.operator("d3dual.pick_maxilla", text = "Set Max Model", icon = ico)
        
        if not splint: return
        
        if splint and splint.mand_model_set: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        row = layout.row()
        row.operator("d3dual.pick_mandible", text = "Set Mand Model", icon = ico)
        
        
        
        row = layout.row()
        row.label('Facial Scan Import (Optional)')
        
        row = layout.row()
        row.operator("d3dual.import_face_obj", text = 'Import OBJ Models')
        
        if splint and splint.face_model_set: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        row = layout.row()
        row.operator("d3dual.pick_face_model", text = "Set Face Model", icon = ico)
        
        
        if splint and splint.facial_landmarks_set: 
            ico = 'CHECKBOX_HLT'
        elif splint and splint.face_model_set:
            ico = 'CHECKBOX_DEHLT'  
        else:
            ico = 'NONE'
            
        row = layout.row()
        row.operator("d3dual.mark_facial_landmarks", text = "Set Face Landmarks", icon = ico)        
        
        
        row = layout.row()
        row.label('Dental Landmarks')
        if splint and splint.landmarks_set: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        row = layout.row()
        row.operator("d3dual.mark_landmarks_cookie", text = "Set Landmarks", icon = ico)
        
        
        articulator_panel.draw_articulator_tools(layout, show_data = True)
        
        if splint and splint.max_insertion_complete: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        row = layout.row()
        col = row.column()    
        col.operator("d3dual.pick_insertion_axis_max", text = "Survey Max Model (View)", icon = ico)
        #col.operator("d3splint.arrow_silhouette_survey", text = "Survey Max Model (Arrow)")
        
        if splint and splint.mand_insertion_complete: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
            
        col.operator("d3dual.pick_insertion_axis_mand", text = "Survey Mand Model (View)", icon = ico)
        #col.operator("d3splint.arrow_silhouette_survey", text = "Survey Mand Model (Arrow)")
        
        row = layout.row()
        row.label('Fit and Retention')
        
        row = layout.row()
        col = row.column()
        if splint and splint.max_refractory_model_complete: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        
        col.operator('d3dual.refractory_model_max', text = "Max Refractory Model", icon = ico)

        if splint and splint.mand_refractory_model_complete: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        
        col.operator('d3dual.refractory_model_mand', text = "Mand Refractory Model", icon = ico)
        
        #FORCE SAVE!
        if bpy.data.filepath == '':
            box = layout.box()
            row = box.row()
            row.operator("wm.save_as_mainfile", text = "Save to Continue").copy = False
            return
    
    
        row = layout.row()
        row.label('Shell Boundaries')
        
        
        #if  not (prefs.use_alpha_tools and prefs.use_poly_cut):
        if splint and splint.max_splint_outline: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        row = layout.row()
        row.operator("d3dual.mark_max_margin", text = "Max Splint Margin", icon = ico)
        row.operator("d3splint.clear_margin", text = "", icon = "CANCEL").target = 'MAX'
        
        if splint and splint.mand_splint_outline: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        row = layout.row()
        row.operator("d3dual.mark_mand_margin", text = "Mand Splint Margin", icon = ico)
        row.operator("d3splint.clear_margin", text = "", icon = "CANCEL").target = 'MAND'   
                
        row = layout.row()
        row.label('Shell Construction')
        
        row = layout.row()
        col = row.column()
        
        if splint and splint.max_shell_complete: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        col.operator("d3splint.create_splint_shell", text = "Create Max Shell", icon = ico).jaw_mode = 'MAX'
        
        
        if splint and splint.mand_shell_complete: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        #col = row.column()
        col.operator("d3splint.create_splint_shell", text = "Create Mand Shell", icon = ico).jaw_mode = 'MAND'
        
        row = layout.row()
        row.label('Curves/Rim/Planes')
        
        row = layout.row()
        
        if splint and splint.arch_curves_complete: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'
        row.operator("d3dual.mark_occlusal_curves", text = "Mark Occlusal Curves", icon = ico)
        row.operator("d3dual.clear_occlusal_curves", text = "", icon = "CANCEL")
        
        row = layout.row()
        col = row.column()
        col.operator("d3dual.v_join_rim", text = 'Join Rim to Shell')
        col.operator("dual.metav_blockout_shell", text = "Blockout Large Concavities")
        col.operator("d3dual.transform_arch_surface", text = "Adjust Surface")
        col.operator("d3dual.subtract_occlusal_surface", text = "Subtract Inter-Arch SUrface")
        
        #if splint and splint.mand_shell_complete: 
        #    ico = 'CHECKBOX_HLT'
        #else:
        #    ico = 'CHECKBOX_DEHLT'
        #col = row.column()
        #col.operator("d3splint.create_splint_shell", text = "Create Mand Shell", icon = ico).jaw_mode = 'MAND'
        
        #row = layout.row()
        #row.label('Visualization Helpers')
        #row = layout.row()
        #row.label('Show Shells')
        #row = layout.row()
        #row.operator("d3dual.attach_view_presets", text = "T").mode = "T/T"
        #row.operator("d3dual.attach_view_presets", text = "B").mode = "B/B"
        #row.operator("d3dual.attach_view_presets", text = "A").mode = "A/A"
        
        #row = layout.row()
        #row.label('Show Models')
        #row = layout.row()
        #row.operator("d3dual.attach_view_presets", text = "t").mode = "t/T"
        #row.operator("d3dual.attach_view_presets", text = "b").mode = "b/B"
        #row.operator("d3dual.attach_view_presets", text = "a").mode = "a/B"
        
        row = layout.row()
        row.label('Paint Operators')
        row = layout.row()
        col = row.column()
        col.operator("d3dual.enter_sculpt_paint_mask", text = 'Paint Selected Shell')
        col.operator("d3dual.sculpt_mask_qhull_raw", text = 'Painted to Convex')
        col.operator("d3dual.sculpt_mask_flat_pad", text = 'Painted to Flat')
        if context.mode == 'SCULPT':
            col.operator("object.mode_set", text = 'Finish Painting')
            
        col.operator("d3dual.remesh_shell", text = "Remesh")
        
        row = layout.row()
        row.label('Sculpt Operators')
        row = layout.row()
        col = row.column()
        col.operator("d3splint.splint_start_sculpt", text = 'Sculpt Selected Shell')
        if context.mode == 'SCULPT':
            col.operator("object.mode_set", text = 'Finish Sculpting')
                    
        #row = layout.row()
        #row.label('Ramp Creation Tools')

        #row = layout.row()
        #col = row.column()
        #if splint and splint.ramps_generated: 
        #    ico = 'CHECKBOX_HLT'
        #else:
        #    ico = 'CHECKBOX_DEHLT'
        #col.operator("d3splint.sleep_element_landmarks", text = "Sleep Ramp Landmarks", icon = ico)
        #col.operator("d3splint.ross_sleep_element_modify", text = "Modify Selected Ramp")
        #col.operator("d3splint.trim_shell_to_ramp", text = "Trim Selected Shell")
        
        #col = row.column()
        #if splint and splint.ramp_array_generated: 
        #    ico = 'CHECKBOX_HLT'
        #else:
        #    ico = 'CHECKBOX_DEHLT'
        #col.operator("d3splint.ross_sleep_element_array", text = "Make Ramps Array", icon = ico)
        
        #row = layout.row()
        #row.label('Button Creation Tools')
        
        #row = layout.row()
        #col = row.column()
        #col.operator("d3dual.elastic_notch_place", text = "Place Elastic Notch")
        #col.operator("d3splint.elastic_notch_edit", text = "Edit Selected Notch")
        #col.operator("d3splint.elastic_notch_cut", text = "Cut All Notches")
        #col.operator("d3splint.finalize_all_notches", text = "Finalize All Notches")
        
        row = layout.row()
        row.label('Butttons Creation Tools')
        
        row = layout.row()
        
        if button_draw_handler.button_draw_handle == None:
            row.operator('d3dual.enable_button_visualization', text = '', icon = 'RESTRICT_VIEW_OFF')
        else:
            row.operator('d3dual.stop_button_visualization', text = '',  icon = 'RESTRICT_VIEW_ON')
        
        if not button_draw_handler.constraint_active:
            row.operator('d3dual.enable_button_constraints', text = '',  icon = 'LOCKED')
        else:
            row.operator('d3dual.clear_button_constraints', text = '',  icon = 'UNLOCKED')
        #contrain button orientations on/off tool with lock/unlock icon
        
        #if context.object != None and context.object.get('constrain_length'):
        #    row = layout.row()
        #    row.prop(context.object, "constrain_length")
            #can row.prop show ID props?
            
        row = layout.row()
        col = row.column()
        col.operator("d3dual.elastic_button_place", text = "Place Elastic Button")
        #col.operator("d3dual.elastic_hook_place", text = "Place Elastic Hook")
        col.operator("d3splint.elastic_button_edit", text = "Edit Selected Button")
        col.operator("d3dual.enforce_button_distance", text = "Enforce Button Distance")
        col.operator("d3dual.button_alignment_connection", text = "Align Button Connection")
        #col.operator("d3splint.elastic_button_fuse", text = "Fuse All Buttons")  #repalced by attachment engine
            
        row = layout.row()
        row.label('Premade Attachments')
        
        row = layout.row()
        row.prop(prefs, "attachment_lib")
        row = layout.row()
        row.prop(prefs, "attachment_ob")
        
        
        row = layout.row()
        row.operator('d3dual.show_all_attachments', text = '', icon = 'RESTRICT_VIEW_OFF')
        row.operator('d3dual.hide_all_attachments', text = '', icon = 'RESTRICT_VIEW_ON')
        row = layout.row()
        col = row.column()
        col.operator("d3dual.place_attachment", text = "Place Custom Attachment")
        col.operator("d3dual.snap_attachment_to_surface", text = "Snap Selected Attachment")
        col.operator("d3dual.remove_attachment", text = "Remove Custom Attachment")
        col.operator("d3dual.csg_attachment_elements", text = 'Merge Attachments')
         
        row = layout.row()
        row.label(text = 'Add Text to Object')
        
        row = layout.row()
        col = row.column()
        col.prop(prefs, "d3_model_label_stencil_font", text = 'Choose Font')
        col.prop(prefs, "d3_model_label", text = '')
        col.prop(prefs, "d3_model_label_depth", text = 'Text Depth')
        row = layout.row()
        row.operator("d3splint.stencil_text", text = 'Stencil Text Label')
        row = layout.row()
        row.operator("d3tool.remesh_and_emboss_text", text = 'Emboss All Labels onto Object')
        row = layout.row()
        row.operator("d3splint.splint_finalize_labels", text = 'Finalize Label Modifiers')
       
        
        row = layout.row()
        row.label('Validation and Sculpting')
        row = layout.row()
        col = row.column()

        col.operator("d3splint.splint_check_thickness", text = "Check Shell Thickness")
        if context.mode == 'OBJECT':
            col.operator("d3splint.splint_start_sculpt", text = "Sculpt Selected Shell")
        elif context.mode == 'SCULPT':
            col.operator('object.mode_set', text = 'Finish Sculpt').mode = 'OBJECT'


        row = layout.row()
        row.label('Finalize and Export')
        
        row = layout.row()
        col = row.column()
        if splint and splint.finalize_splint_max: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'

        col.operator("d3dual.finish_booleans", text = "Finalize Max Shell", icon = ico).jaw_mode = 'MAX'
        
        if splint and splint.finalize_splint_mand: 
            ico = 'CHECKBOX_HLT'
        else:
            ico = 'CHECKBOX_DEHLT'    
        col.operator("d3dual.finish_booleans", text = "Finalize Mand Shell", icon = ico).jaw_mode = 'MAND'
        
        col.operator("d3dual.finish_booleans_monoblock")
       
        #col.operator("d3splint.remove_finalized_loose_parts", text = "Remove Loose Parts")
        col.operator("d3dual.appliance_report", text = 'Create Design Report')
        
        #col.operator("d3splint.splint_finish_booleans3", text = "Finalize The Splint", icon = ico).jaw_mode = 'MAX'
        
        #if splint and splint.finalize_mand_splint: 
        #    ico = 'CHECKBOX_HLT'
        #else:
        #    ico = 'CHECKBOX_DEHLT'
        
        #col.operator("d3splint.splint_finish_booleans3", text = "Finalize The Splint", icon = ico).jaw_mode = 'MAND'
        
        
        #col.operator("d3splint.splint_clean_islands", text = "Remove Small Parts")
       
        #col.operator("d3guard.splint_cork_boolean", text = "Finalize Splint (CORK EGINE)")
        col.operator("d3dual.export_appliance_stl", text = "Export Appliance STLs")
       
        
        
        
          
class VIEW3D_PT_D3SplintModels(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="TOOLS"
    bl_category = "Dental"
    bl_label = "Model Operations"
    bl_context = ""
    
    def draw(self, context):
        prefs = get_settings()
        sce = bpy.context.scene
        layout = self.layout
        
        row = layout.row()
        row.label(text = "Model Operators")
        row.operator("wm.url_open", text = "", icon="INFO").url = "https://d3tool.com/knowledge-base/"
          
        if context.object != None:
            row = layout.row()
            txt = context.object.name
            row.label(text = "Selected Model: " + txt)
        
        else:
            row = layout.row()
            row.label(text = "Please Select a Model")
            
        row = layout.row()
        row.label('Sculpt/Paint Mode Tools')
        row = layout.row()
        col = row.column()    
        col.operator("d3splint.enter_sculpt_paint_mask", text = "Paint Model")
        col.operator("paint.mask_flood_fill", text = "Clear Paint").mode = 'VALUE'
        col.operator("d3splint.delete_sculpt_mask", text = "Delete Painted") #defaults to .value = 0
        col.operator("d3splint.close_paint_hole", text = 'Close Paint Hole')
        col.operator("d3splint.delete_sculpt_mask_inverse", text = "Keep Only Painted")

        if context.mode == 'SCULPT':
            col.operator("object.mode_set", text = 'Finish Sculpt/Paint')
        
        
        row = layout.row()
        row.label('Tooth Library Objects')
        
        row = layout.row()
        row.prop(prefs, "tooth_lib")
        row = layout.row()
        row.prop(prefs, "tooth_lib_ob")
        
        row = layout.row()
        row.operator("d3dual.place_lib_tooth")
        
        row = layout.row()
        row.operator("d3dual.simple_join_teeth_to_models")
        
        row = layout.row()
        row.operator("d3dual.boolean_join_teeth_to_models")
        
        
        row = layout.row()
        row.label('Fixing and Cleaning Operators')
        
        row = layout.row()
        row.operator("d3model.remesh_and_decimate", text = "Auto Remesh")
        
        row = layout.row()
              
        #col.operator("d3splint.simple_offset_surface", text = "Simple Offset")
        
        row.prop(prefs, "d3_model_auto_fill_small")
        row.prop(prefs, "d3_model_max_hole_size")
        
        row = layout.row()
        col = row.column()
        col.operator("d3model.mesh_repair", text = "Fix Holes and Islands")
        col.operator("d3splint.delete_islands", text = "Delete Loose Parts")
        col.operator("d3splint.ragged_edges", text = "Remove Ragged Edges")
        
        row = layout.row()
        row.label('Open Model Cutting')
        row = layout.row()
        col = row.column()
        col.operator("d3splint.splint_plane_cut", text = "Plane Cut Open Model").cut_method = "SURFACE"
        
        row = layout.row()
        row.label('Close Model Cutting')
        row = layout.row()
        
        col = row.column()
        col.operator("d3splint.splint_plane_cut", text = "Plane Cut Closed Model").cut_method = "SOLID"
        
        col.operator("d3splint.splint_pause_plane_cuts", text = "De-Activate Cuts")
        col.operator("d3splint.splint_activate_plane_cuts", text = "Re-Activate Cuts")
        col.operator("d3splint.splint_finalize_plane_cuts", text = "Apply All Cuts")
        
        row = layout.row()
        row.label('Base and Thickness Operators')
        row = layout.row()
        col = row.column()
        col.operator("d3splint.simple_base", text = "Simple Base")            
        #col.operator("d3splint.model_wall_thicken", text = 'Hollow Model')
        col.operator("d3splint.model_wall_thicken2", text = 'Hollow Model')
        col.operator("d3tool.model_vertical_base", text = 'Vertical Base')
        
        row = layout.row()
        row.label('Batch Processing')
        row = layout.row()
        col = row.column()
        
        col.operator("d3splint.batch_process_plane_cuts", text = 'Batch Plane Cuts')
        
        
class VIEW3D_PT_D3SplintModelText(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="TOOLS"
    bl_category = "Dental"
    bl_label = "Model Text Embossing"
    bl_context = ""
    
    def draw(self, context):
        sce = bpy.context.scene
        layout = self.layout
        prefs = get_settings()
         
        row = layout.row()
        row.label(text = "Model Labelling")
        #row.operator("wm.url_open", text = "", icon="INFO").url = "https://github.com/patmo141/odc_public/wiki"
          
        if context.object != None:
            row = layout.row()
            txt = context.object.name
            row.label(text = "Selected Model: " + txt)
        
        else:
            row = layout.row()
            row.label(text = "Please Select a Model")
            
            #row = layout.row()
            #row.label(text = 'SVG Image Workflow')
        
        row = layout.row()
        row.label(text = 'Add Text to Object')
        
        row = layout.row()
        col = row.column()
        col.prop(prefs, "d3_model_label", text = '')
        col.prop(prefs, "d3_model_label_depth", text = 'Text Depth')
        row = layout.row()
        row.operator("d3splint.stencil_text", text = 'Stencil Text Label')
        row = layout.row()
        row.operator("d3tool.remesh_and_emboss_text", text = 'Emboss All Labels onto Object')
        row = layout.row()
        row.operator("d3splint.splint_finalize_labels", text = 'Finalize Label Modifiers')
        
def register():

    
    bpy.utils.register_class(VIEW3D_PT_D3SplintAssitant)
    bpy.utils.register_class(VIEW3D_PT_D3SplintProperties)
    bpy.utils.register_class(VIEW3D_PT_D3DualArch)
    bpy.utils.register_class(VIEW3D_PT_D3SplintModels)
    bpy.utils.register_class(VIEW3D_PT_D3SplintModelText)
    bpy.utils.register_class(VIEW3D_PT_D3DualArticulator)
    bpy.utils.register_class(VIEW3D_PT_D3DualVisHelp)
    
    #bpy.utils.register_module(__name__)
    
def unregister():

    
    bpy.utils.unregister_class(VIEW3D_PT_D3DualArch)
    
    #bpy.utils.unregister_class(VIEW3D_PT_ODCDentures)
    bpy.utils.unregister_class(VIEW3D_PT_D3SplintModels)
    bpy.utils.unregister_class(VIEW3D_PT_D3SplintModelText)
if __name__ == "__main__":
    register()