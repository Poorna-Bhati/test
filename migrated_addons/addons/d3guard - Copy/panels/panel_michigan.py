'''
Created on Mar 24, 2019

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bg_status
from common_utilities import get_settings



def draw_michgian_panel_background(layout, splint):
    
    prefs = get_settings()
    
    row = layout.row()
    row.label('Initial Mounting and Articulation')
    row = layout.row()
    col = row.column()
    
    if 'Articulator' not in bpy.context.scene.objects:
        ico = 'CHECKBOX_DEHLT'
        col.operator("d3splint.generate_articulator", text = "Create Articulator", icon = ico)
    elif not splint.articulator_made:
        ico = 'CHECKBOX_DEHLT'        
        col.operator("d3splint.generate_articulator", text = "Set Articulator Values", icon = ico)

    col.operator("d3splint.generate_articulator", text = "Set Articulator Values")
        
    #col.operator("d3splint.splint_mount_articulator", text = "Mount on Articulator")

    row = layout.row()
    col = row.column()

    col.operator("d3splint.open_pin_on_articulator", text = "Change Pin Setting" )
    col.operator("d3splint.recover_mounting_relationship", text = "Recover Mounting" )
    
    
    row = layout.row()
    #survery, #margin, #curves
    if splint and splint.insertion_path: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
        
    #col.operator("d3splint.view_silhouette_survey", text = "Survey Model (View)", icon = ico)
    #col.operator("d3splint.arrow_silhouette_survey", text = "Survey Model (Arrow)")
    row.operator("d3splint.pick_insertion_axis_2", text = "Survey Model", icon = ico)
    
    
    #FORCE SAVE!
    if bpy.data.filepath == '':
        box = layout.box()
        row = box.row()
        row.operator("wm.save_as_mainfile", text = "Save to Continue").copy = False
        return

    row = layout.row()
    if splint and splint.refractory_model: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    #row.operator("d3splint.refractory_model", text = "Refractory Model", icon = ico)
    row.operator('d3splint.refractory_model_4', text = "Refractory Model", icon = ico)
    
    row = layout.row()
    row.label('Splint Boundaries')
    row.operator("wm.url_open", text = "", icon="INFO").url = "https://youtu.be/SphJcXG4CpU"
      
    if splint and splint.trim_upper: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
        
    row = layout.row()
    row.operator("d3splint.polytrim_margin", text = "Mark Splint Outline", icon = ico)
    row.operator("d3splint.clear_margin", text = "", icon = "CANCEL")    

    row = layout.row()
    row.label('Occlusal Curves')
    
    if splint and splint.curve_max and splint.curve_mand:
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    row = layout.row()
    row.operator("d3splint.mark_occlusal_curves", text = "Mark Occlusal Curves", icon = ico)
    
    #bg box
    box = layout.box()
    row = box.row()
    row.label('Background Operations')
    row.operator("d3splint.bg_job_director", text = "", icon = "PLAY")
    row.operator("d3splint.stop_bg_job_director", text = "", icon = "CANCEL")
    row.operator("wm.url_open", text = "", icon="INFO").url =  "https://d3tool.com/knowledge-base/background-processing/"
    
    #row = box.row()
    #col = row.column()
    
    row = box.row()
    if splint and splint.splint_shell: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
        
    if bg_status.shell_start and not bg_status.shell_complete:
        row.label('Shell in Progress', icon = ico)
    else:
        row.operator("d3splint.create_splint_shell", text = "Splint Shell", icon = ico)
    
    
    
    row = box.row()
    if splint and splint.min_thick: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    if bg_status.min_thick_start and not bg_status.min_thick_complete:
        row.label('Min Thick in Progress', icon = ico)
    else:
        row.operator("d3splint.splint_minimum_thickness", text = "Minimum Thickness Shell", icon = ico)
    
    
    row = box.row()
    if splint and splint.refractory_model: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    
    if bg_status.refractory_start and not bg_status.refractory_complete:
        row.label("Refractory in progress", icon = ico)
    else:
        #row.operator("d3splint.refractory_model", text = "Refractory Model", icon = ico)
        row.operator('d3splint.refractory_model_4', text = "Refractory Model", icon = ico)
    row = box.row()
    if splint and splint.dynamic_surface: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'

    if bg_status.dyn_surface_start and not bg_status.dyn_surface_complete:
        row.label('Dyn Surface in Progress', icon = ico)
    
    else:
        op_props = row.operator("d3splint.splint_animate_articulator", text = "Generate Functional Surface", icon = ico)
        op_props.mode = 'FULL_ENVELOPE'
        op_props.relax_ramp_length = .5 
        op_props.range_of_motion  =  7
        op_props.use_relax = True
        op_props.resolution = 20
    
    
    row = layout.row()
    col = row.column()
    #manual interactions
    if splint and splint.wax_rim_calc: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    
    col.operator("d3splint.splint_rim_from_dual_curves", text = "Splint Wax Rim", icon = ico)
    
    if splint and splint.wax_rim_fuse: 
        ico = 'CHECKBOX_HLT'
    elif splint.wax_rim_calc and not splint.wax_rim_fuse:
        ico = 'CHECKBOX_DEHLT'
    else:
        ico = 'NONE'

    col.operator("d3splint.v_join_rim", text = "Fuse Rim to Shell", icon = ico)
    
    
    row = layout.row()
    row.label('Shape Refinement Tools')
    row = layout.row()
    
    row = layout.row()
    row.prop(prefs, "auto_remesh_smooth", text = '')
    row.operator("d3splint.remesh_smooth_inflate", text = 'Remesh/Smooth')
    
    row = layout.row()
    row.prop(prefs, "auto_blockout", text = '')
    row.operator("d3splint.metav_blockout_shell", text = 'Blockout Large Concavities')
    
    row = layout.row()
    
    row.operator("d3splint.auto_sculpt_concavities", text = 'Auto Sculpt Concavities')
    row = layout.row()
    row.operator("d3splint.v_correct_minimum_thickness", text = 'Correct to Minimum Thickness')
    
    row = layout.row()
    row.label('Manual Sculpt and Refinement')
    
    if bpy.context.mode == 'OBJECT':
        row = layout.row()
        row.operator("d3splint.splint_start_sculpt", text = "Go to Sculpt")
    
    if bpy.context.mode == 'SCULPT': #TODO other checks for sculpt object and stuff
        
        paint_settings = bpy.context.scene.tool_settings.unified_paint_settings
        sculpt_settings = bpy.context.tool_settings.sculpt
        row= layout.row()
        col = row.column()
        col.template_ID_preview(sculpt_settings, "brush", new="brush.add", rows=3, cols=8)
        
        
        brush = sculpt_settings.brush
        row = layout.row()
        row.prop(brush, "stroke_method")
    
        
        row = layout.row()
        row.operator("object.mode_set", text = 'Finish Paint/Sculpt')
        
        
    row = layout.row()
    row.label('Occlusion tools')
    row = layout.row()
    col = row.column()
    if splint and splint.mark_post_contact: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
        
    col.operator( "d3splint.mark_posterior_contacts", text = "Mark Posterior Contacts", icon = ico)
    
    if splint and splint.subtract_posterior_surface: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'    
    col.operator("d3splint.subtract_posterior_surface", text = 'Subtract Posterior Plane', icon = ico)
    
    row = layout.row()
    col = row.column()
    
    
    if splint and splint.dynamic_surface: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    op_props = col.operator("d3splint.splint_animate_articulator", text = "Generate Functional Surface", icon = ico)
    op_props.mode = 'FULL_ENVELOPE'
    op_props.relax_ramp_length = .5 
    op_props.range_of_motion  =  7
    op_props.use_relax = True
    op_props.resolution = 20
    
    if splint and splint.subtract_dynamic_surface: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    col.operator("d3splint.splint_subtract_surface", text = "Subtract Functional Surface", icon = ico)
    
    row = layout.row()
    col = row.column()
    col.operator("d3splint.subtract_opposing_model", text = 'Grind MIP')
    
    row = layout.row()
    row.operator("d3ual.articulator_mode_set", text = "Articulator Mode")
    row = layout.row()
    row.operator("d3splint.dynamic_paint_occlusion", text = "Occlusion On")
    row.operator("d3splint.stop_dynamic_paint_occlusion", text = "Occlusion Off")
    
    #finalize
    row = layout.row()
    row.label('Finalization')
    
    row = layout.row()
    col = row.column()
    if splint and splint.finalize_splint: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    
    col.operator("d3splint.splint_finish_booleans3", text = "Finalize The Splint", icon = ico)
    col.operator("d3splint.splint_clean_islands", text = "Remove Small Parts")
   
    #col.operator("d3guard.splint_cork_boolean", text = "Finalize Splint (CORK EGINE)")
    col.operator("d3splint.splint_report", text = "Generate Report")
    col.operator("d3splint.export_splint_stl", text = "Export Splint STL")
    #col.operator("d3splint.auto_check_model", text = "Auto Plane Cut Model")
    
    row = layout.row()
    row.label('Start Again on Opposing?')
    
    row = layout.row()
    col = row.column()
    col.operator("d3splint.plan_splint_on_opposing", text = "Plan Opposing Splint")
    
    
def draw_michigan_panel_standard(layout, splint):
    
    row = layout.row()
    row.label('Initial Mounting and Articulation')
    row = layout.row()
    col = row.column()
    if 'Articulator' not in bpy.context.scene.objects:
        ico = 'CHECKBOX_DEHLT'
        col.operator("d3splint.generate_articulator", text = "Create Articulator", icon = ico)
    elif not splint.articulator_made:
        ico = 'CHECKBOX_DEHLT'        
        col.operator("d3splint.generate_articulator", text = "Set Articulator Values", icon = ico)

    col.operator("d3splint.generate_articulator", text = "Set Articulator Values")

    row = layout.row()
    col = row.column()

    col.operator("d3splint.open_pin_on_articulator", text = "Change Pin Setting" )
    col.operator("d3splint.recover_mounting_relationship", text = "Recover Mounting" )
    
    
    row = layout.row()
    row.label('Survey and HoC')
    row = layout.row()
    row.operator("d3splint.view_presets", text = "Upper View").mode = "U/O"
    row.operator("d3splint.view_presets", text = "Lower View").mode = "L/O"
    row = layout.row()
    col = row.column()
    
    if splint and splint.insertion_path: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
        
    #col.operator("d3splint.view_silhouette_survey", text = "Survey Model (View)", icon = ico)
    #col.operator("d3splint.arrow_silhouette_survey", text = "Survey Model (Arrow)")
    col.operator("d3splint.pick_insertion_axis_2", text = "Survey Model", icon = ico)
    
    box = layout.box()
    
    if bpy.data.filepath == '':
        ico = 'CHECKBOX_DEHLT'
    else:
        ico = 'CHECKBOX_HLT'
    row = box.row()
    row.operator("wm.save_as_mainfile", text = "Save!!", icon = ico).copy = False
    
    row = layout.row()
    if splint and splint.refractory_model: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    
    #col.operator("d3splint.refractory_model", text = "Refractory Model", icon = ico)
    row.operator('d3splint.refractory_model_4', text = "Refractory Model", icon = ico)
    
    row = layout.row()
    row.label('Splint Boundaries')
    row.operator("wm.url_open", text = "", icon="INFO").url = "https://youtu.be/SphJcXG4CpU"
      
    if splint and splint.trim_upper: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
        

    row = layout.row()
    row.operator("d3splint.polytrim_margin", text = "Mark Splint Outline", icon = ico)
    row.operator("d3splint.clear_margin", text = "", icon = "CANCEL")
    
    row = layout.row()
    row.label('Shell Construction')
    
    row = layout.row()
    col = row.column()
    
    if splint and splint.splint_shell: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    col.operator("d3splint.create_splint_shell", text = "Splint Shell", icon = ico)
    
    if splint and splint.min_thick: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    col.operator("d3splint.splint_minimum_thickness", text = "Minimum Thickness Shell", icon = ico)
    
    
    
    row = layout.row()
    row.label('Occlusal Curves')
    
    if splint and splint.curve_max and splint.curve_mand:
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    row = layout.row()
    row.operator("d3splint.mark_occlusal_curves", text = "Mark Occlusal Curves", icon = ico)
    
    #row = layout.row()
    #row.operator("d3splint.bg_functional_surface", text = "BG Dynamic Surface")
    
    

    row = layout.row()
    col = row.column()
    if splint and "MakeRim" in splint.ops_string: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    col.operator("d3splint.splint_rim_from_dual_curves", text = "Splint Wax Rim", icon = ico)
    
    if splint and splint.wax_rim_fuse: 
        ico = 'CHECKBOX_HLT'
    elif splint.wax_rim_calc and not splint.wax_rim_fuse:
        ico = 'CHECKBOX_DEHLT'
    else:
        ico = 'NONE'
    col.operator("d3splint.v_join_rim", text = "Fuse Rim to Shell", icon = ico)
    
    row = layout.row()
    row.label('Shape Refinement Tools')
    row = layout.row()
    col = row.column()
    col.operator("d3splint.remesh_smooth_inflate", text = 'Remesh/Smooth')
    col.operator("d3splint.metav_blockout_shell", text = 'Blockout Large Concavities')
    col.operator("d3splint.auto_sculpt_concavities", text = 'Auto Sculpt Concavities')
    col.operator("d3splint.v_correct_minimum_thickness", text = 'Correct to Minimum Thickness')
    
    
    if bpy.context.mode == 'OBJECT':
        row = layout.row()
        row.operator("d3splint.splint_start_sculpt", text = "Go to Sculpt")
    
    if bpy.context.mode == 'SCULPT': #TODO other checks for sculpt object and stuff
        
        paint_settings = bpy.context.scene.tool_settings.unified_paint_settings
        sculpt_settings = bpy.context.tool_settings.sculpt
        row= layout.row()
        col = row.column()
        col.template_ID_preview(sculpt_settings, "brush", new="brush.add", rows=3, cols=8)
        
        
        brush = sculpt_settings.brush
        row = layout.row()
        row.prop(brush, "stroke_method")
    
        
        row = layout.row()
        row.operator("object.mode_set", text = 'Finish Paint/Sculpt')
        
        
    row = layout.row()
    row.label('Occlusion tools')
    row = layout.row()
    col = row.column()
    if splint and splint.mark_post_contact: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
        
    col.operator( "d3splint.mark_posterior_contacts", text = "Mark Posterior Contacts", icon = ico)
    
    if splint and splint.subtract_posterior_surface: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'    
    col.operator("d3splint.subtract_posterior_surface", text = 'Subtract Posterior Plane', icon = ico)
    
    row = layout.row()
    col = row.column()
    
    if splint and splint.dynamic_surface: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    op_props = col.operator("d3splint.splint_animate_articulator", text = "Generate Functional Surface", icon = ico)
    op_props.mode = 'FULL_ENVELOPE'
    op_props.relax_ramp_length = .5 
    op_props.range_of_motion  =  7
    op_props.use_relax = True
    op_props.resolution = 20
    
    if splint and splint.subtract_dynamic_surface: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    col.operator("d3splint.splint_subtract_surface", text = "Subtract Functional Surface", icon = ico)
    
    row = layout.row()
    col = row.column()
    col.operator("d3splint.subtract_opposing_model", text = 'Grind MIP')
    
    row = layout.row()
    row.operator("d3dual.articulator_mode_set", text = "Articulator Mode")
    row = layout.row()
    row.operator("d3splint.dynamic_paint_occlusion", text = "Occlusion On")
    row.operator("d3splint.stop_dynamic_paint_occlusion", text = "Occlusion Off")
    
    row = layout.row()
    row.label('Manual Sculpt and Refinement')
    
    

    #finalize
    row = layout.row()
    row.label('Finalization')
    
    row = layout.row()
    col = row.column()
    if splint and splint.finalize_splint: 
        ico = 'CHECKBOX_HLT'
    else:
        ico = 'CHECKBOX_DEHLT'
    
    col.operator("d3splint.splint_finish_booleans3", text = "Finalize The Splint", icon = ico)
    col.operator("d3splint.splint_clean_islands", text = "Remove Small Parts")
   
    #col.operator("d3guard.splint_cork_boolean", text = "Finalize Splint (CORK EGINE)")
    col.operator("d3splint.splint_report", text = "Generate Report")
    col.operator("d3splint.export_splint_stl", text = "Export Splint STL")
    #col.operator("d3splint.auto_check_model", text = "Auto Plane Cut Model")
    
    row = layout.row()
    row.label('Start Again on Opposing?')
    
    row = layout.row()
    col = row.column()
    col.operator("d3splint.plan_splint_on_opposing", text = "Plan Opposing Splint")
    
    
    
    