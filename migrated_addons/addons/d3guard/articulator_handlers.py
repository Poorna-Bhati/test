'''
Created on Feb 4, 2018

@author: Patrick
'''
import math
import time

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bgl
import blf
from mathutils import Vector, Matrix, Quaternion
from bpy_extras import view3d_utils
import common_drawing

from bpy.app.handlers import persistent




articulator_app_handle = None
articulator_draw_handle = None
articulator_draw_data = dict()



def articulator_draw(dummy, context):
    if 'Articulator' not in context.scene.objects: return
    Art = context.scene.objects['Articulator']
    if Art.hide == True: return
    
    global articulator_draw_data
    
    region = context.region  
    rv3d = context.space_data.region_3d
        
    lcp_loc = articulator_draw_data['LCP']
    rcp_loc = articulator_draw_data['RCP']
    inc_loc = articulator_draw_data['INC'] 
    r_arm_mid = articulator_draw_data['r_arm_mid'] 
    l_arm_mid = articulator_draw_data['l_arm_mid']
    balkwill_angle = articulator_draw_data['balkwill_angle']
    R_len = articulator_draw_data['R_len']
    L_len = articulator_draw_data['L_len']
    
    common_drawing.draw_polyline_from_3dpoints(context, [lcp_loc, inc_loc], (.1,.8,.1,.5), 2, 'GL_LINE_STRIP')
    common_drawing.draw_polyline_from_3dpoints(context, [rcp_loc, inc_loc], (.1,.8,.1,.5), 2, 'GL_LINE_STRIP')
    
    bgl.glColor4f(.8,.8,.8,1)
    blf.size(0, 24, 72)
    vector2d = view3d_utils.location_3d_to_region_2d(region, rv3d, r_arm_mid)
    blf.position(0, vector2d[0], vector2d[1], 0)
    blf.draw(0, str(R_len)[0:4])
    
    vector2d = view3d_utils.location_3d_to_region_2d(region, rv3d, l_arm_mid)
    blf.position(0, vector2d[0], vector2d[1], 0)
    blf.draw(0, str(L_len)[0:4])
    
    inc_vector = inc_loc.normalized()
    angle_vec  = inc_vector.lerp(Vector((1,0,0)), .5)
    angle_position = 15 * angle_vec
    
    
    msg = str(balkwill_angle)[0:4] + ' deg'
    dimension = blf.dimensions(0, msg)
    
    vector2d = view3d_utils.location_3d_to_region_2d(region, rv3d, angle_position)
    blf.position(0, vector2d[0], vector2d[1] - .5 * dimension[1], 0)
    blf.draw(0, msg)
    
    
    #msg = str(articulator_draw_data['total_translation'])[0:4]
    #transform_position = inc_loc + articulator_draw_data['trans_vector']
    #vector2d = view3d_utils.location_3d_to_region_2d(region, rv3d, transform_position)
    #blf.position(0, vector2d[0], vector2d[1], 0)
    #blf.draw(0, msg)
    
    

def articulator_visibility(Art):
    
    
    hide = Art.hide
    
    elements = ['Bottom Element', 
                'LCP', 
                'RCP', 
                'Top Element', 
                'R Condyle Path Block',
                'L Condyle Path Block',
                'R Condyle',
                'L Condyle',
                'Guide Table']
    
    for ele in elements:
        ob = bpy.data.objects.get(ele)
        if ob:
            ob.hide = hide
            
def articulator_metrics_callback(scene):
    if 'Articulator' not in scene.objects: return
    
    Art = scene.objects['Articulator']
    
    global articulator_draw_data
    
    if 'Hide' not in articulator_draw_data:
        articulator_draw_data['Hide'] = Art.hide
    
    if articulator_draw_data['Hide'] != Art.hide:  #changed the visibility
        articulator_visibility(Art)
        articulator_draw_data['Hide'] = Art.hide
        
    if Art.hide == True: return
    
    
    LCP = bpy.data.objects.get('L Condyle')
    RCP = bpy.data.objects.get('R Condyle')
    Incial = bpy.data.objects.get('Incisal')
    
    
    if  not ((LCP != None) and (RCP != None) and (Incial != None)):
        
        return
    
    lcp_loc = LCP.matrix_world.to_translation()
    rcp_loc = RCP.matrix_world.to_translation()
    inc_loc = Incial.matrix_world.to_translation()
    
    r_arm = rcp_loc - inc_loc
    l_arm = lcp_loc - inc_loc
    
    r_arm_mid = .5 * (inc_loc + rcp_loc)  
    l_arm_mid = .5 * (inc_loc + lcp_loc)
    
    Z_balkwill = l_arm.cross(r_arm)
    Z_balkwill.normalize()
    
    balkwill_angle = Z_balkwill.angle(Vector((0,0,1))) * 180 / math.pi
    
    R_len = r_arm.length
    L_len = l_arm.length
    
    articulator_draw_data['LCP'] = lcp_loc
    articulator_draw_data['RCP'] = rcp_loc
    articulator_draw_data['INC'] = inc_loc
    articulator_draw_data['r_arm_mid'] = r_arm_mid
    articulator_draw_data['l_arm_mid'] = l_arm_mid
    articulator_draw_data['balkwill_angle'] = balkwill_angle
    articulator_draw_data['R_len'] = R_len
    articulator_draw_data['L_len'] = L_len
 
    v_condyle = RCP.matrix_world.to_quaternion()  * Vector((1,0,0)) 
    v_condyle = v_condyle - v_condyle.dot(Vector((1,0,0))) * Vector((1,0,0))
    v_condyle.normalize()

    
    if not len(scene.odc_splints): return
    n = scene.odc_splint_index
    splint = scene.odc_splints[n]
    
    mand = splint.get_mandible()
    
    Mand = bpy.data.objects.get(mand)
    
    if Mand == None: return
    
    initial_orientation = bpy.data.objects.get('Mandibular Orientation')
    mx_i = initial_orientation.matrix_world
    articulator_draw_data['initial_orientation'] = mx_i
    
    
    mx_w = Mand.matrix_world  #.copy()
          
    trans = mx_w.to_translation() - mx_i.to_translation()
    L = trans.length
        
    articulator_draw_data['trans_vector'] = trans
    articulator_draw_data['total_translation'] = L
      
    qi = mx_i.to_quaternion()
    qf = mx_w.to_quaternion()
        
    r_diff = qi.rotation_difference(qf)    
    euler = r_diff.to_euler()
    
    hinge_opening = 180 * euler[0]/math.pi  #rotation about x axis
    lateral_deviation = 180 * euler[2]/math.pi
    
    articulator_draw_data['hinge_opening'] = hinge_opening
    articulator_draw_data['lateral_deviation'] = lateral_deviation
    
   
class D3Splint_OT_enable_articulator_visualizations(bpy.types.Operator):
    '''
    Will add some GUI features which help visualize articulator values
    '''
    bl_idname='d3splint.enable_articulator_visualizations'
    bl_label="Enable Articulator Visualization"

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        #add a textbox to display information.  attach it to this
        #add a persisetent callback on scene update
        #which monitors the status of the ODC
        
        #clear previous handlers
        clear_articulator_handlers()
        global articulator_app_handle
        articulator_app_handle = bpy.app.handlers.scene_update_post.append(articulator_metrics_callback) #pre
        
        global articulator_draw_data
        articulator_draw_data.clear()
                
        global articulator_draw_handle
        articulator_draw_handle = bpy.types.SpaceView3D.draw_handler_add(articulator_draw, (self, context), 'WINDOW', 'POST_PIXEL')
        
        
        return {'FINISHED'}

class D3Splint_OT_stop_articulator_visualizations(bpy.types.Operator):
    '''
    Remove Articulator Draw Overlay
    '''
    bl_idname='d3splint.stop_articulator_visualization'
    bl_label="Stop Articulator Visualization"

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):

        clear_articulator_handlers()
        
        return {'FINISHED'}
    
    
def clear_articulator_handlers():
    
    global articulator_app_handle
    global articulator_draw_handle        
    if articulator_draw_handle:
        bpy.types.SpaceView3D.draw_handler_remove(articulator_draw_handle, 'WINDOW')
        articulator_draw_handle = None
        
        handlers = [hand.__name__ for hand in bpy.app.handlers.frame_change_pre]
        
        if articulator_metrics_callback.__name__ in handlers:
            bpy.app.handlers.scene_update_pre.remove(articulator_metrics_callback)
        
 
def register():
    bpy.utils.register_class(D3Splint_OT_enable_articulator_visualizations)
    bpy.utils.register_class(D3Splint_OT_stop_articulator_visualizations)
    
def unregister():
    bpy.utils.unregister_class(D3Splint_OT_enable_articulator_visualizations)
    bpy.utils.unregister_class(D3Splint_OT_stop_articulator_visualizations)
    clear_articulator_handlers()       
    