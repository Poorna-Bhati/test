'''
Created on Aug 15, 2017
@author: Patrick

This module contains functions that are used to mark and set
landmarks on the casts.  For example marking splint boundaries
midine etc.
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import uuid
import time

from textbox import TextBox
from mathutils import Vector, Matrix, Color
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d

from common_utilities import bversion, get_settings
from odcutils import get_bbox_center
from common_drawing import outline_region
import tracking


def pick_model_callback(self, context):
    self.help_box.draw()
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    outline_region(context.region,(r,g,b,1))  
    

class D3DUAL_OT_pick_maxilla(bpy.types.Operator):
    """Left Click on maxillary model"""
    bl_idname = "d3dual.pick_maxilla"
    bl_label = "Pick Maxillary Model"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls,context):
        return True
    
    def modal_nav(self, event):
        events_nav = {'MIDDLEMOUSE', 'WHEELINMOUSE','WHEELOUTMOUSE', 'WHEELUPMOUSE','WHEELDOWNMOUSE'} #TODO, better navigation, another tutorial
        handle_nav = False
        handle_nav |= event.type in events_nav

        if handle_nav: 
            return 'nav'
        return ''
    
    def modal_main(self,context,event):
        # general navigation
        nmode = self.modal_nav(event)
        if nmode != '':
            return nmode  #stop here and tell parent modal to 'PASS_THROUGH'

        
        if event.type == 'MOUSEMOVE':
            self.hover_scene(context, event.mouse_region_x, event.mouse_region_y)    
            return 'main'
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            
            return self.pick_model(context)
        
            
        elif event.type == 'ESC' and event.value == 'PRESS':
            return 'cancel' 

        return 'main'
    


    def modal(self, context, event):
        context.area.tag_redraw()
        
        FSM = {}    
        FSM['main']    = self.modal_main
        FSM['nav']     = self.modal_nav
        
        nmode = FSM[self.mode](context, event)
        
        if nmode == 'nav': 
            return {'PASS_THROUGH'}
        
        if nmode in {'finish','cancel'}:
            #clean up callbacks
            context.window.cursor_modal_restore()
            context.area.header_text_set()
            context.user_preferences.themes[0].view_3d.outline_width = self.outline_width
        
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'} if nmode == 'finish' else {'CANCELLED'}
        
        if nmode: self.mode = nmode
        
        return {'RUNNING_MODAL'}

    def hover_scene(self,context,x, y):
        scene = context.scene
        region = context.region
        rv3d = context.region_data
        coord = x, y
        ray_max = 10000
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * ray_max)

        if bversion() <= '002.076.000':
            result, ob, mx, loc, normal = scene.ray_cast(ray_origin, ray_target)
        else:
            result, loc, normal, idx, ob, mx = scene.ray_cast(ray_origin, ray_target)

        if result:
            self.ob = ob
            self.ob_preview = ob.name
            context.area.header_text_set(ob.name)
            
            for obj in context.scene.objects:
                if obj != ob:
                    obj.select = False
                else:
                    obj.select = True
        
        else:
            self.ob = None
            self.ob_preview = 'None'
            context.area.header_text_set('None')
            for ob in context.scene.objects:
                ob.select = False
            if context.object:
                context.scene.objects.active = None
    
    def pick_model(self, context):
        
        prefs = get_settings()
        if self.ob == None:
            return 'main'
        
        n = context.scene.odc_splint_index
        if len(context.scene.odc_splints) != 0:
            odc_splint = context.scene.odc_splints[n]
            odc_splint.max_model = self.ob.name
            odc_splint.max_model_set = True
            odc_splint.ops_string  += "PickMaxModel:"
        else:
            my_item = context.scene.odc_splints.add()        
            my_item.name = 'Splint'
            my_item.max_model = self.ob.name
            my_item.max_model_set = True
            my_item.ops_string  += "PickMaxModel:"
            my_item.case_id = str(uuid.uuid4())
            my_item.start_time = time.time()
            
        if "Model Mat" not in bpy.data.materials:
            mat = bpy.data.materials.new('Model Mat')
            mat.diffuse_color = prefs.def_model_color
            mat.diffuse_intensity = 1
            mat.emit = .8
            mat.use_transparency = True
            mat.alpha = .5
        else:
            mat = bpy.data.materials.get('Model Mat')
        
        # Assign it to object
        if self.ob.data.materials:
            # assign to 1st material slot
            self.ob.data.materials[0] = mat
        else:
            # no slots
            self.ob.data.materials.append(mat)
        
        #create an empty to store the original origin of the data
        if (self.ob.name + "orig_origin") not in bpy.data.objects:
            recovery_ob = bpy.data.objects.new(self.ob.name + "orig_origin", None)
            context.scene.objects.link(recovery_ob)
            recovery_ob.parent = self.ob
            recovery_ob.matrix_world = self.ob.matrix_world.copy()  #why?
            print(self.ob.matrix_world)
            context.scene.update()
        
        bb_center = get_bbox_center(self.ob)
        T = Matrix.Translation(bb_center)
        iT = T.inverted()
        
        child_mx = {}
        for child in self.ob.children:
            child_mx[child] = child.matrix_world.copy()
            
        self.ob.data.transform(iT)
        self.ob.matrix_world *= T
        
        for child in self.ob.children:
            child.matrix_world = child_mx[child]
        #for child in self.ob.children:
        #    child.matrix_world *= iT
            
        print(self.ob.matrix_world)
        
        tracking.trackUsage("D3DUAL:StartCase", None)
        return 'finish'
            
    def invoke(self,context, event):
        
        self.report({'WARNING'}, 'By Continuuing, you certify this is for non-clinial, educational or training purposes')
        
        self.outline_width = context.user_preferences.themes[0].view_3d.outline_width
        context.user_preferences.themes[0].view_3d.outline_width = 4
        
        self.ob_preview = 'None'
        context.window.cursor_modal_set('EYEDROPPER')
        
        #hide the stupid grid floor
        context.space_data.show_floor = False
        context.space_data.show_axis_x = False
        context.space_data.show_axis_y = False
        
        #TODO, tweak the modifier as needed
        help_txt = "Pick Model\n\n Hover over objects in the scene \n left click on the maxillary model\n ESC to cancel"
        self.help_box = TextBox(context,500,500,300,200,10,20,help_txt)
        self.help_box.snap_to_corner(context, corner = [1,1])
        self.mode = 'main'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(pick_model_callback, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self) 
        
        
        return {'RUNNING_MODAL'} 
    
class D3DUAL_OT_pick_mandible(bpy.types.Operator):
    """Left Click on Model to mark the mandibular model"""
    bl_idname = "d3dual.pick_mandible"
    bl_label = "Pick Mandible"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls,context):
        if len(context.scene.odc_splints) == 0:
            return False
        return True
    
    def modal_nav(self, event):
        events_nav = {'MIDDLEMOUSE', 'WHEELINMOUSE','WHEELOUTMOUSE', 'WHEELUPMOUSE','WHEELDOWNMOUSE'} #TODO, better navigation, another tutorial
        handle_nav = False
        handle_nav |= event.type in events_nav

        if handle_nav: 
            return 'nav'
        return ''
    
    def modal_main(self,context,event):
        # general navigation
        nmode = self.modal_nav(event)
        if nmode != '':
            return nmode  #stop here and tell parent modal to 'PASS_THROUGH'

        
        if event.type == 'MOUSEMOVE':
            self.hover_scene(context, event.mouse_region_x, event.mouse_region_y)    
            return 'main'
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            
            return self.pick_model(context)
        
            
        elif event.type == 'ESC' and event.value == 'PRESS':
            return 'cancel' 

        return 'main'
    


    def modal(self, context, event):
        context.area.tag_redraw()
        
        FSM = {}    
        FSM['main']    = self.modal_main
        FSM['nav']     = self.modal_nav
        
        nmode = FSM[self.mode](context, event)
        
        if nmode == 'nav': 
            return {'PASS_THROUGH'}
        
        if nmode in {'finish','cancel'}:
            #clean up callbacks
            context.window.cursor_modal_restore()
            context.area.header_text_set()
            context.user_preferences.themes[0].view_3d.outline_width = self.outline_width
        
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'} if nmode == 'finish' else {'CANCELLED'}
        
        if nmode: self.mode = nmode
        
        return {'RUNNING_MODAL'}

    def hover_scene(self,context,x, y):
        scene = context.scene
        region = context.region
        rv3d = context.region_data
        coord = x, y
        ray_max = 10000
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * ray_max)

        if bversion() <= '002.076.000':
            result, ob, mx, loc, normal = scene.ray_cast(ray_origin, ray_target)
        else:
            result, loc, normal, idx, ob, mx = scene.ray_cast(ray_origin, ray_target)

        if result:
            self.ob = ob
            self.ob_preview = ob.name
            context.area.header_text_set(ob.name)
            
            for obj in context.scene.objects:
                if obj != ob:
                    obj.select = False
                else:
                    obj.select = True
        
        else:
            self.ob = None
            self.ob_preview = 'None'
            context.area.header_text_set('None')
            for ob in context.scene.objects:
                ob.select = False
            if context.object:
                context.scene.objects.active = None
    
    def pick_model(self, context):
        prefs = get_settings()
        if self.ob == None:
            return 'main'
            
        n = context.scene.odc_splint_index
        odc_splint = context.scene.odc_splints[n]
        
        if self.ob.name == odc_splint.max_model:
            self.report({'WARNING'}, 'Cant set the opposing as the master model')
            return 'main'
        
        odc_splint.mand_model = self.ob.name
        odc_splint.mand_model_set = True
        odc_splint.ops_string  += "PickMandModel:" 
        if "Opposing Mat" not in bpy.data.materials:
            mat = bpy.data.materials.new('Opposing Mat')
            mat.diffuse_color = prefs.def_opposing_color
            mat.diffuse_intensity = 1
            mat.emit = 0.0
            mat.specular_intensity = 0.0
        else:
            mat = bpy.data.materials.get('Opposing Mat')
        
        # Assign it to object
        if self.ob.data.materials:
            # assign to 1st material slot
            self.ob.data.materials[0] = mat
        else:
            # no slots
            self.ob.data.materials.append(mat) 
        
        bb_center = get_bbox_center(self.ob)
        T = Matrix.Translation(bb_center)
        iT = T.inverted()
        
        self.ob.data.transform(iT)
        self.ob.matrix_world *= T
            
        #tracking.trackUsage("D3Splint:SetOpposing")
        return 'finish'
            
    def invoke(self,context, event):
        
        if not len(context.scene.odc_splints):
            self.report({'ERROR'}, 'Need to set master model first')
            return('CANCELLED')
        
        
        n = context.scene.odc_splint_index
        odc_splint = context.scene.odc_splints[n]
        
        Model = bpy.data.objects.get(odc_splint.max_model)
        if not Model:
            self.report({'ERROR'}, 'Need to set master model first')
            return('CANCELLED')
        
        self.outline_width = context.user_preferences.themes[0].view_3d.outline_width
        context.user_preferences.themes[0].view_3d.outline_width = 4
        
        self.ob_preview = 'None'
        context.window.cursor_modal_set('EYEDROPPER')
        
        #TODO, tweak the modifier as needed
        help_txt = "Pick Model\n\n Hover over objects and left click on maxillary model\n ESC to cancel"
        self.help_box = TextBox(context,500,500,300,200,10,20,help_txt)
        self.help_box.snap_to_corner(context, corner = [1,1])
        self.mode = 'main'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(pick_model_callback, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self) 
        return {'RUNNING_MODAL'} 
        

           
def register():

    bpy.utils.register_class(D3DUAL_OT_pick_maxilla)
    bpy.utils.register_class(D3DUAL_OT_pick_mandible)

     
def unregister():

    bpy.utils.unregister_class(D3DUAL_OT_pick_maxilla)
    bpy.utils.unregister_class(D3DUAL_OT_pick_mandible)

    
if __name__ == "__main__":
    register()