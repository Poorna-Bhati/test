'''
Created on Feb 4, 2018

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bgl
import blf
from mathutils import Vector, Matrix, Quaternion
from bpy_extras import view3d_utils
import common_drawing

from bpy.app.handlers import persistent
import math



button_app_handle = None
button_draw_handle = None
button_draw_data = []

button_constraint_handle = None
constraint_active = False



from button_placement import constrain_button_relationship

def button_draw(dummy, context):
    
    if not context.object: return
    if 'Button' not in context.object.name: return
    
    global button_draw_data
    
    for l0, l1, d in button_draw_data:
    
        R_len = (l0 - l1).length
        mid = .5 * (l0 + l1)
        
        common_drawing.draw_polyline_from_3dpoints(context, [l0, l1], (.1,.8,.1,.5), 4, 'GL_LINE_STRIP')
        
        bgl.glColor4f(.8,.8,.8,1)
        blf.size(0, 24, 72)
        vector2d = view3d_utils.location_3d_to_region_2d(context.region, context.space_data.region_3d, mid)
        blf.position(0, vector2d[0], vector2d[1], 0)
        blf.draw(0, str(R_len)[0:4])
        

    return
    
            
def button_metrics_callback(scene):
    
    if scene.objects.active == None: return
    if 'Button' not in scene.objects.active.name: return
    
    global button_draw_data
    
    #do this stuff first, hopefully not a locking blender type situation
    #constrain_button_relationship(scene.objects.active)
    
    #find all pairs of buttons and notches
    buttons = [ob for ob in bpy.data.objects if 'Button' in ob.name]
    b_set = set(buttons)
    
    pairs = []
    while len(b_set):
        b = b_set.pop()
        loc = b.matrix_world.to_translation()
        
        other_b = min(b_set, key = lambda x: (x.matrix_world.to_translation() - loc).length)
            
        loc2 = other_b.matrix_world.to_translation()
        if loc2[0] * loc[0] < 0:
            print('different jaw sides')
            #only check for notches on the same side of jaw
            continue
        
        else:
            b_set.remove(other_b)
            pairs.append((loc, loc2, (loc - loc2).length))
    
    button_draw_data = pairs     
    
    
    return
        


def button_constraint_callback(scene):
    
    if scene.objects.active == None: return
    if 'Button' not in scene.objects.active.name: return
    
    global button_draw_data
    
    #do this stuff first, hopefully not a locking blender type situation
    constrain_button_relationship(scene.objects.active)
    
    
    return

 
class D3DUAL_OT_enable_button_visualizations(bpy.types.Operator):
    '''
    Will add some GUI features which help visualize articulator values
    '''
    bl_idname='d3dual.enable_button_visualization'
    bl_label="Enable Button Visualization"

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        #add a textbox to display information.  attach it to this
        #add a persisetent callback on scene update
        #which monitors the status of the ODC
        
        #clear previous handlers
        clear_button_handlers()
        global button_app_handle
        button_app_handle = bpy.app.handlers.scene_update_post.append(button_metrics_callback)
        
        global button_draw_data
        button_draw_data.clear()
                
        global button_draw_handle
        button_draw_handle = bpy.types.SpaceView3D.draw_handler_add(button_draw, (self, context), 'WINDOW', 'POST_PIXEL')
        
        
        return {'FINISHED'}
    
    
class D3DUAL_OT_enable_button_contraints(bpy.types.Operator):
    '''
    Will add some GUI features which help visualize articulator values
    '''
    bl_idname='d3dual.enable_button_constraints'
    bl_label="Enable Button Constraints"

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        #add a textbox to display information.  attach it to this
        #add a persisetent callback on scene update
        #which monitors the status of the ODC
        
        #clear previous handlers
        clear_constraint_handlers()
        global button_constraint_handle
        global constraint_active
        
        button_constraint_handle = bpy.app.handlers.scene_update_post.append(button_constraint_callback)
        constraint_active = True
        
        return {'FINISHED'}
    
    
class D3DUAL_OT_clear_button_contraints(bpy.types.Operator):
    '''
    Will add some GUI features which help visualize articulator values
    '''
    bl_idname='d3dual.clear_button_constraints'
    bl_label="Clear Button Constraints"

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        #add a textbox to display information.  attach it to this
        #add a persisetent callback on scene update
        #which monitors the status of the ODC
        
        #clear previous handlers
        clear_constraint_handlers()
        
        
        return {'FINISHED'}

class D3DUAL_OT_stop_button_visualizations(bpy.types.Operator):
    '''
    Remove button Draw Overlay
    '''
    bl_idname='d3dual.stop_button_visualization'
    bl_label="Stop Button Visualization"

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):

        clear_button_handlers()
        
        return {'FINISHED'}
    
    
def clear_button_handlers():
    
    global button_app_handle
    global button_draw_handle
         
    if button_draw_handle:
        bpy.types.SpaceView3D.draw_handler_remove(button_draw_handle, 'WINDOW')
        button_draw_handle = None
        
        handlers = [hand.__name__ for hand in bpy.app.handlers.scene_update_post]
        
        if button_metrics_callback.__name__ in handlers:
            bpy.app.handlers.scene_update_post.remove(button_metrics_callback)
    
    
        
                
def clear_constraint_handlers():
    global constraint_active
 
    handlers = [hand.__name__ for hand in bpy.app.handlers.scene_update_post]
    if button_constraint_callback.__name__ in handlers:
        bpy.app.handlers.scene_update_post.remove(button_constraint_callback)
        
    constraint_active = False
    
    
def register():
    bpy.utils.register_class(D3DUAL_OT_enable_button_visualizations)
    bpy.utils.register_class(D3DUAL_OT_stop_button_visualizations)
    bpy.utils.register_class(D3DUAL_OT_clear_button_contraints)
    bpy.utils.register_class(D3DUAL_OT_enable_button_contraints)
    
def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_enable_button_visualizations)
    bpy.utils.unregister_class(D3DUAL_OT_stop_button_visualizations)
    bpy.utils.unregister_class(D3DUAL_OT_clear_button_contraints)
    bpy.utils.unregister_class(D3DUAL_OT_enable_button_contraints)   
    