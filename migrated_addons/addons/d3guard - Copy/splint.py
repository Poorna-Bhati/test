import time
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import math
from mathutils import Vector, Matrix, Color, Quaternion, kdtree
from mathutils.geometry import intersect_point_line
from bpy_extras import view3d_utils
from bpy.props import FloatProperty, BoolProperty, IntProperty, EnumProperty
import bgl
import blf
import random
from mesh_cut import edge_loops_from_bmedges, space_evenly_on_path, flood_selection_faces, flood_selection_faces_limit, grow_selection_to_find_face, grow_selection
from bmesh_fns import new_bmesh_from_bmelements
from common_utilities import bversion, showErrorMessage
#from . 
import odcutils
from segmentation.common.maths import intersect_path_plane
import bmesh_fns
from odcutils import offset_bmesh_edge_loop
import bgl_utils
import common_drawing
import common_utilities
import survey_utils
import undercut_utilities
#from . 
import full_arch_methods
from textbox import TextBox
from curve import CurveDataManager, PolyLineKnife
from common_utilities import space_evenly_on_path, get_settings
from mathutils.bvhtree import BVHTree
import splint_cache
import tracking
from common_drawing import outline_region

'''
https://occlusionconnections.com/gnm-optimized/which-occlusal-plane-do-you-undestand-dont-get-confused/
http://www.claytonchandds.com/pdf/ICCMO/AReviewOfTheOcclusalPlane.pdf
'''
class D3SPLINT_OT_link_selection_splint(bpy.types.Operator):
    ''''''
    bl_idname='d3splint.link_selection_splint'
    bl_label="Link Units to Splint"
    bl_options = {'REGISTER','UNDO'}
    
    clear = bpy.props.BoolProperty(name="Clear", description="Replace existing units with selected, \n else add selected to existing", default=False)
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        teeth = odcutils.tooth_selection(context)  #TODO:...make this poll work for all selected teeth...
        condition_1 = len(teeth) > 0
        implants = odcutils.implant_selection(context)  
        condition_2 = len(implants) > 0
        return condition_1 or condition_2
    
    def execute(self,context):
        settings = get_settings()
        dbg =settings.debug
        n = context.scene.odc_splint_index
        odc_splint = context.scene.odc_splints[n]
        full_arch_methods.link_selection_to_splint(context, odc_splint, debug=dbg)
        
        return {'FINISHED'}
    
class D3SPLINT_OT_splint_bone(bpy.types.Operator):
    '''
    Will assign the active object as the bone model
    Only use if making multi tissue support.  eg bone
    and teeth.
    '''
    bl_idname='d3splint.bone_model_set'
    bl_label="Splint Bone"
    bl_options = {'REGISTER','UNDO'}
    
    @classmethod
    def poll(cls, context):

        condition_1 = context.object
                
        return condition_1
    
    def execute(self,context):
        settings = get_settings()
        dbg =settings.debug
        n = context.scene.odc_splint_index
        
        if len(context.scene.odc_splints) != 0:
            
            odc_splint = context.scene.odc_splints[n]
            odc_splint.bone = context.object.name
            
        else:
            self.report({'WARNING'}, "there are not guides, bone will not be linked to a guide")
        
        
        return {'FINISHED'}

#class D3SPLINT_OT_splint_model(bpy.types.Operator):
#    '''
#    Will assign the active object as the  model to build
#    a splint on.  Needed if an object was not linked
#    when splint was planned
#    '''
#    bl_idname='d3splint.model_set'
#    bl_label="Set Splint Model"
#    bl_options = {'REGISTER','UNDO'}
    
#    @classmethod
#    def poll(cls, context):

#        condition_1 = context.object != None
              
#        return condition_1
    
#    def execute(self,context):
#        settings = get_settings()
#        dbg =settings.debug
#        n = context.scene.odc_splint_index
        
#        if len(context.scene.odc_splints) != 0:
            
#            odc_splint = context.scene.odc_splints[n]
#            odc_splint.model = context.object.name
            
#        else:
#            my_item = context.scene.odc_splints.add()        
#            my_item.name = 'Splint'
#            my_item.model = context.object.name
        
#        tracking.trackUsage("D3Splint:StartSplint")
#        return {'FINISHED'}    

class D3SPLINT_OT_splint_opposing(bpy.types.Operator):
    '''
    Will assign the active object as the  opposing model
    '''
    bl_idname='d3splint.splint_opposing_set'
    bl_label="Set Splint Opposing"
    bl_options = {'REGISTER','UNDO'}
    
    @classmethod
    def poll(cls, context):

        condition_1 = context.object
        condition_2 = len(context.scene.odc_splints)       
        return condition_1 and condition_2
    
    def execute(self,context):
        settings = get_settings()
        dbg =settings.debug
        n = context.scene.odc_splint_index
        
        
        if len(context.scene.odc_splints) != 0:
            odc_splint = context.scene.odc_splints[n]
            
            Model = bpy.data.objects.get(odc_splint.model)
            if not Model:
                self.report({'ERROR'}, "Please mark model first")
                return {'CANCELLED'}
            
            odc_splint.opposing = context.object.name
            
             
        else:
            self.report({'ERROR'}, "Please plan a splint first!")
            return {'CANCELLED'}
        
        
        return {'FINISHED'} 

    
class D3SPLINT_OT_splint_report(bpy.types.Operator):
    '''
    Will add a text object to the .blend file which tells
    the information about a surgical guide and it's various
    details.
    '''
    bl_idname='d3splint.splint_report'
    bl_label="Splint Report"
    bl_options = {'REGISTER','UNDO'}
    
    @classmethod
    def poll(cls, context):

        condition_1 = len(context.scene.odc_splints) > 0
        return condition_1
    
    def execute(self,context):

        sce = context.scene
        if 'Report' in bpy.data.texts:
            Report = bpy.data.texts['Report']
            Report.clear()
        else:
            Report = bpy.data.texts.new("Report")
    
    
        Report.write("Open Dental CAD Implant Guide Report")
        Report.write("\n")
        Report.write('Date and Time: ')
        Report.write(time.asctime())
        Report.write("\n")
    
        Report.write("There is/are %i guide(s)" % len(sce.odc_splints))
        Report.write("\n")
        Report.write("_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _")
        Report.write("\n")
        Report.write("\n")
    
        for splint in sce.odc_splints:
            imp_names = splint.implant_string.split(":")
            imp_names.pop(0)
            Report.write("Splint Name: " + splint.name)
            Report.write("\n")
            Report.write("Number of Implants: %i" % len(imp_names))
            Report.write("\n")
            Report.write("Implants: ")
            Report.write(splint.implant_string)
            Report.write("\n")
            
            
            for name in imp_names:
                imp = sce.odc_implants[name]
                Report.write("\n")
                Report.write("Implant: " + name + "\n")
                
                if imp.implant and imp.implant in bpy.data.objects:
                    implant = bpy.data.objects[imp.implant]
                    V = implant.dimensions
                    width = '{0:.{1}f}'.format(V[0], 2)
                    length = '{0:.{1}f}'.format(V[2], 2)
                    Report.write("Implant Dimensions: " + width + "mm x " + length + "mm")
                    Report.write("\n")
                    
                if imp.inner and imp.inner in bpy.data.objects:
                    inner = bpy.data.objects[imp.inner]
                    V = inner.dimensions
                    width = '{0:.{1}f}'.format(V[0], 2)
                    Report.write("Hole Diameter: " + width + "mm")
                    Report.write("\n")
                else:
                    Report.write("Hole Diameter: NO HOLE")    
                    Report.write("\n")
                    
                    
                if imp.outer and imp.outer in bpy.data.objects and imp.implant and imp.implant in bpy.data.objects:
                    implant = bpy.data.objects[imp.implant]
                    guide = bpy.data.objects[imp.outer]
                    v1 = implant.matrix_world.to_translation()
                    v2 = guide.matrix_world.to_translation()
                    V = v2 - v1
                    depth = '{0:.{1}f}'.format(V.length, 2)
                    print(depth)
                    Report.write("Cylinder Depth: " + depth + "mm")
                    Report.write("\n")
                else:
                    Report.write("Cylinder Depth: NO GUIDE CYLINDER \n")
                    
                if imp.sleeve and imp.sleeve in bpy.data.objects and imp.implant and imp.implant in bpy.data.objects:
                    implant = bpy.data.objects[imp.implant]
                    guide = bpy.data.objects[imp.sleeve]
                    v1 = implant.matrix_world.to_translation()
                    v2 = guide.matrix_world.to_translation()
                    V = v2 - v1
                    depth = '{0:.{1}f}'.format(V.length, 2)
                    Report.write("Sleeve Depth: " + depth + "mm")
                    Report.write("\n")
                else:
                    Report.write("Sleeve Depth: NO SLEEVE")    
                    Report.write("\n")
                    
            Report.write("_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _")
            Report.write("\n")
            Report.write("\n")
        
        return {'FINISHED'}
    
class D3SPLINT_OT_splint_subtract_holes(bpy.types.Operator):
    ''''''
    bl_idname='d3splint.splint_subtract_holes'
    bl_label="Subtract Splint Holes"
    bl_options = {'REGISTER','UNDO'}
    
    finalize = bpy.props.BoolProperty(default = True, name = "Finalize", description="Apply all modifiers to splint before adding guides?  may take longer, less risk of crashing")
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        #TODO..polling
        return True
    
    def execute(self,context):
        settings = get_settings()
        dbg =settings.debug
        n = context.scene.odc_splint_index
        odc_splint = context.scene.odc_splints[n]
        
        layers_copy = [layer for layer in context.scene.layers]
        context.scene.layers[0] = True
        
        if not odc_splint.splint:
            self.report({'ERROR'},'No splint model to add guide cylinders too')
        if dbg:
            start_time = time.time()
        
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        sce = context.scene
        bpy.ops.object.select_all(action='DESELECT')
        
        new_objs = []
        implants = []
        imp_list = odc_splint.implant_string.split(sep=":")
        for name in imp_list:
            implant = context.scene.odc_implants.get(name)
            if implant:
                implants.append(implant)
                
        for space in implants:
            if space.inner:
                Guide_Cylinder = bpy.data.objects[space.inner]
                Guide_Cylinder.hide = True
                new_data = Guide_Cylinder.to_mesh(sce,True, 'RENDER')
                new_obj = bpy.data.objects.new("temp_holes", new_data)
                new_obj.matrix_world = Guide_Cylinder.matrix_world
                new_objs.append(new_obj)
                sce.objects.link(new_obj)
                new_obj.select = True
        
        if len(new_objs):   
            sce.objects.active = new_objs[0]
            bpy.ops.object.join()
            
        else:
            return{'CANCELLED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        Splint = bpy.data.objects[odc_splint.splint]
        Splint.select = True
        Splint.hide = False
        sce.objects.active = Splint
        if self.finalize:
            for mod in Splint.modifiers:
                if mod.type in {'BOOLEAN', 'SHRINKWRAP'}:
                    if mod.type == 'BOOLEAN' and mod.object:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                    elif mod.type == 'SHRINKWRAP' and mod.target:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                else:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
        
        bool_mod = Splint.modifiers.new('OUTER','BOOLEAN')
        bool_mod.operation = 'DIFFERENCE'
        bool_mod.object = new_objs[0] #hopefully this is still the object?
        new_objs[0].hide = True   
        
        for i, layer in enumerate(layers_copy):
            context.scene.layers[i] = layer
        context.scene.layers[10] = True
        
        if dbg:
            finish = time.time() - start_time
            print("finished subtracting holes in %f seconds..boy that took a long time" % finish)
        
        return {'FINISHED'}
        
class D3SPLINT_OT_splint_subtract_sleeves(bpy.types.Operator):
    '''
    '''
    bl_idname='d3splint.splint_subtract_sleeves'
    bl_label="Subtract Splint Sleeves"
    bl_options = {'REGISTER','UNDO'}
    
    finalize = bpy.props.BoolProperty(default = True, name = "Finalize", description="Apply all modifiers to splint before adding guides?  may take longer, less risk of crashing")
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        #TODO..polling
        return True
    
    def execute(self,context):
        settings = get_settings()
        dbg =settings.debug
        n = context.scene.odc_splint_index
        odc_splint = context.scene.odc_splints[n]
        layers_copy = [layer for layer in context.scene.layers]
        context.scene.layers[0] = True
        
        if not odc_splint.splint:
            self.report({'ERROR'},'No splint model to add guide cylinders too')
        if dbg:
            start_time = time.time()
        
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        sce = context.scene
        bpy.ops.object.select_all(action='DESELECT')
        
        implants = []
        imp_list = odc_splint.implant_string.split(sep=":")
        for name in imp_list:
            implant = context.scene.odc_implants.get(name)
            if implant:
                implants.append(implant)
                
        new_objs = []
        for space in implants:
            if space.sleeve:
                Sleeve_Female = bpy.data.objects[space.sleeve]
                Sleeve_Female.hide = True
                new_data = Sleeve_Female.to_mesh(sce,True, 'RENDER')
                new_obj = bpy.data.objects.new("temp_holes", new_data)
                new_obj.matrix_world = Sleeve_Female.matrix_world
                new_objs.append(new_obj)
                sce.objects.link(new_obj)
                new_obj.select = True
        
        if len(new_objs):   
            sce.objects.active = new_objs[0]
            bpy.ops.object.join()
            
        else:
            return{'CANCELLED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        Splint = bpy.data.objects[odc_splint.splint]
        Splint.select = True
        Splint.hide = False
        sce.objects.active = Splint
        if self.finalize:
            for mod in Splint.modifiers:
                if mod.type in {'BOOLEAN', 'SHRINKWRAP'}:
                    if mod.type == 'BOOLEAN' and mod.object:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                    elif mod.type == 'SHRINKWRAP' and mod.target:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                else:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                    
        bool_mod = Splint.modifiers.new('Sleeves','BOOLEAN')
        bool_mod.operation = 'DIFFERENCE'
        bool_mod.object = new_objs[0] #hopefully this is still the object?
        new_objs[0].hide = True   
        
        for i, layer in enumerate(layers_copy):
            context.scene.layers[i] = layer
        context.scene.layers[11] = True
        
        if dbg:
            finish = time.time() - start_time
            print("finished subtracting Sleeves in %f seconds..boy that took a long time" % finish)
        
        return {'FINISHED'}
    
class D3SPLINT_OT_splint_add_guides(bpy.types.Operator):
    ''''''
    bl_idname='d3splint.splint_add_guides'
    bl_label="Merge Guide Cylinders to Splint"
    bl_options = {'REGISTER','UNDO'}
    
    finalize = bpy.props.BoolProperty(default = True, name = "Finalze",description="Apply all modifiers to splint before adding guides?  may take longer, less risk of crashing")
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        #TODO..polling
        if not len(context.scene.odc_splints): return False
        n = context.scene.odc_splint_index
        odc_splint = context.scene.odc_splints[n]
        imp_list = odc_splint.implant_string.split(sep=":")
        
        if len(imp_list) == 0: return False
        
        return True
    
    def execute(self,context):
        settings = get_settings()
        dbg = settings.debug
        n = context.scene.odc_splint_index
        odc_splint = context.scene.odc_splints[n]
        
        if not odc_splint.splint:
            self.report({'ERROR'},'No splint model to add guide cylinders too')
        if dbg:
            start_time = time.time()
        
        layers_copy = [layer for layer in context.scene.layers]
        context.scene.layers[0] = True
            
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        sce = context.scene
        bpy.ops.object.select_all(action='DESELECT')
        
        new_objs = []
        
        implants = []
        imp_list = odc_splint.implant_string.split(sep=":")
        for name in imp_list:
            implant = context.scene.odc_implants.get(name)
            if implant:
                implants.append(implant)
        for space in implants:
            if space.outer and space.outer in bpy.data.objects:
                Guide_Cylinder = bpy.data.objects[space.outer]
                Guide_Cylinder.hide = True
                new_data = Guide_Cylinder.to_mesh(sce,True, 'RENDER')
                new_obj = bpy.data.objects.new("temp_guide", new_data)
                new_obj.matrix_world = Guide_Cylinder.matrix_world
                new_objs.append(new_obj)
                sce.objects.link(new_obj)
                new_obj.select = True
        
        if len(new_objs):   
            sce.objects.active = new_objs[0]
            bpy.ops.object.join()
        else:
            return{'CANCELLED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        Splint = bpy.data.objects[odc_splint.splint]
        Splint.select = True
        Splint.hide = False
        sce.objects.active = Splint
        if self.finalize:
            for mod in Splint.modifiers:
                if mod.type in {'BOOLEAN', 'SHRINKWRAP'}:
                    if mod.type == 'BOOLEAN' and mod.object:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                    elif mod.type == 'SHRINKWRAP' and mod.target:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                else:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
        
        bool_mod = Splint.modifiers.new('OUTER','BOOLEAN')
        bool_mod.operation = 'UNION'
        bool_mod.object = new_objs[0] #hopefully this is still the object?
        new_objs[0].hide = True   
        
        for i, layer in enumerate(layers_copy):
            context.scene.layers[i] = layer
        context.scene.layers[11] = True
        
        if dbg:
            finish = time.time() - start_time
            print("finished merging guides in %f seconds..boy that took a long time" % finish)
        
        return {'FINISHED'}


def arch_crv_draw_callback_px(self, context):  
    self.crv.draw(context, three_d = False)
    self.help_box.draw()
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    outline_region(context.region,(r,g,b,1))  
    
def arch_crv_draw_callback_pv(self, context):
    self.crv.draw3d(context)
    
class D3SPLINT_OT_splint_mark_margin(bpy.types.Operator):
    """Draw a line along the limits of the splint"""
    bl_idname = "d3splint.draw_splint_margin"
    bl_label = "Mark Buccal Splint Limits"
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

        #after navigation filter, these are relevant events in this state
        if event.type == 'G' and event.value == 'PRESS':
            if self.crv.grab_initiate():
                return 'grab'
            else:
                #error, need to select a point
                return 'main'
        
        if event.type == 'MOUSEMOVE':
            self.crv.hover(context, event.mouse_region_x, event.mouse_region_y)    
            return 'main'
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            x, y = event.mouse_region_x, event.mouse_region_y
            self.crv.click_add_point(context, x,y)
            return 'main'
        
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            self.crv.click_delete_point(mode = 'mouse')
            return 'main'
        
        if event.type == 'X' and event.value == 'PRESS':
            self.crv.delete_selected(mode = 'selected')
            return 'main'
            
        if event.type == 'RET' and event.value == 'PRESS':
            if not self.crv.crv_data.splines[0].use_cyclic_u:
                showErrorMessage('You have not closed the loop, please click the first (YELLOW or BLUE) point to close the loop')
                return 'main'
            self.splint.splint_outline = True
            self.splint.ops_string += 'Draw Splint Margin:'
            return 'finish'
            
        elif event.type == 'ESC' and event.value == 'PRESS':
            return 'cancel' 

        return 'main'
    
    def modal_grab(self,context,event):
        # no navigation in grab mode
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            #confirm location
            self.crv.grab_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            self.crv.grab_cancel()
            return 'main'
        
        elif event.type == 'MOUSEMOVE':
            #update the b_pt location
            self.crv.grab_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
            return 'grab'
        
    def modal(self, context, event):
        context.area.tag_redraw()
        
        FSM = {}    
        FSM['main']    = self.modal_main
        FSM['grab']    = self.modal_grab
        FSM['nav']     = self.modal_nav
        
        nmode = FSM[self.mode](context, event)
        
        if nmode == 'nav': 
            return {'PASS_THROUGH'}
        
        if nmode in {'finish','cancel'}:
            #clean up callbacks
            context.space_data.show_manipulator = False
            context.space_data.transform_manipulators = {'TRANSLATE'}
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            bpy.types.SpaceView3D.draw_handler_remove(self._handle_pv, 'WINDOW')
            return {'FINISHED'} if nmode == 'finish' else {'CANCELLED'}
        
        if nmode: self.mode = nmode
        
        return {'RUNNING_MODAL'}

    def invoke(self,context, event):
        prefs = get_settings()
        self.splint = context.scene.odc_splints[0]   
        self.crv = None
        margin = self.splint.name + '_margin'
           
        if self.splint.model != '' and self.splint.model in bpy.data.objects:
            Model = bpy.data.objects[self.splint.model]
            for ob in bpy.data.objects:
                ob.select = False
                ob.hide = True
            Model.select = True
            Model.hide = False
            
            if Model.name + '_silhouette' in bpy.data.objects:
                Survey = bpy.data.objects.get(Model.name + '_silhouette')
                Survey.hide = False
                
            context.scene.objects.active = Model
            bpy.ops.view3d.viewnumpad(type = 'FRONT')
            bpy.ops.view3d.view_selected()
            context.space_data.show_manipulator = False
            context.space_data.transform_manipulators = {'TRANSLATE'}
            self.crv = CurveDataManager(context,snap_type ='OBJECT', snap_object = Model, shrink_mod = False, name = margin)
            self.crv.point_size, self.crv.point_color, self.crv.active_color = prefs.point_size, prefs.def_point_color, prefs.active_point_color
            
            
            self.crv.crv_obj.parent = Model
            
        else:
            self.report({'ERROR'}, "Need to mark the UpperJaw model first!")
            return {'CANCELLED'}
            
        self.splint.margin = self.crv.crv_obj.name
        
        #TODO, tweak the modifier as needed
        help_txt = "DRAW SPLINT MARGIN\n\n-  Start on one side of arch and sequentially work around to the other until you reach the first point you started with \n-  This curve will establish the boundary of the Splint\n-  Points will snap to model under mouse \n\n-Right click to delete a point \n-LeftClick to select (turns yellow) \n-G to grab the point and then LeftClick to place it \n- The first point will always be blue and needs to be clicked last to close the loop.\n-ENTER to confirm \n-ESC to cancel"
        self.help_box = TextBox(context,500,500,300,200,10,20,help_txt)
        self.help_box.snap_to_corner(context, corner = [1,1])
        self.mode = 'main'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(arch_crv_draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL')
        self._handle_pv = bpy.types.SpaceView3D.draw_handler_add(arch_crv_draw_callback_pv, (self, context), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self) 
        
        tracking.trackUsage("D3Splint:MarkOutline", None)
        return {'RUNNING_MODAL'}
     
def ispltmgn_draw_callback(self, context):  
    self.crv.draw(context)
    self.help_box.draw()
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    outline_region(context.region,(r,g,b,1))       
       
def plyknife_draw_callback(self, context):
    self.knife.draw(context)
    self.help_box.draw()
    if len(self.sketch):
        common_drawing.draw_polyline_from_points(context, self.sketch, (.3,.3,.3,.8), 2, "GL_LINE_SMOOTH")
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    outline_region(context.region,(r,g,b,1))  
   
class D3SPLINT_OT_survey_model(bpy.types.Operator):
    '''Calculates silhouette of object which surveys convexities AND concavities from the current view axis'''
    bl_idname = 'd3splint.view_silhouette_survey'
    bl_label = "Survey Model From View"
    bl_options = {'REGISTER','UNDO'}
    
    world = bpy.props.BoolProperty(default = True, name = "Use world coordinate for calculation...almost always should be true.")
    smooth = bpy.props.BoolProperty(default = True, name = "Smooth the outline.  Slightly less acuurate in some situations but more accurate in others.  Default True for best results")

    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        C0 = context.space_data.type == 'VIEW_3D'
        return  C0

    def execute(self, context):
        tracking.trackUsage("D3Splint:SurveyModelView",None)
        settings = get_settings()
        dbg = settings.debug
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        Model = bpy.data.objects.get(splint.model)
        if Model == None:
            self.report({'ERROR'},'Need to set the model first')
            return {'CANCELLED'}
        
        loc = Model.location
        view = context.space_data.region_3d.view_rotation * Vector((0,0,1))
        odcutils.silouette_brute_force(context, Model, view, self.world)
        #bme = survey_utils.silouette_brute_force(context, Model, view, self.world)
        
        #me = bpy.data.meshes.new('Insertion')
        #Axis = bpy
        
        
        #Make GP Data or Get GP Data
        #if not context.scene.grease_pencil:
        #    gp = bpy.data.grease_pencil.new("My GPencil")
        #    scene = context.scene
        #    scene.grease_pencil = gp

        #else:
        #    gp = context.scene.grease_pencil
            
            
        #Get GP Layer or Make GPLayrer
        #if 'Survey' not in gp.layers:
                
        #    layer = gp.layers.new("Survey", set_active=True)
        #else:
        #    layer = gp.layers['Survey']
            
            
        #clear existing frames
        #if len(layer.frames):
        #    for frame in layer.frames:
        #        frame.clear()
        
        #frame = layer.frames.new(context.scene.frame_current) # frame number 5

        #stroke = frame.strokes.new()
        #stroke.draw_mode = '3DSPACE' # either of ('SCREEN', '3DSPACE', '2DSPACE', '2DIMAGE')

        #start with vertex data
        #stroke.points.add(len(bme.verts)) # add 4 points
        #mx = Model.matrix_world
        #for i, v in enumerate(bme.verts):
        #    stroke.points[i].co = mx * v.co

        #bme.edges.ensure_lookup_table()
        #print('starting grease pencil data add')
        #start = time.time()
        #mx = Model.matrix_world
        #for ed in bme.edges:
        #    stroke = frame.strokes.new()
        #    stroke.draw_mode = '3DSPACE'
        #    stroke.points.add(2)
        #    stroke.points[0].co = mx * ed.verts[0].co
        #    stroke.points[1].co = mx * ed.verts[1].co
        
        
        #print('finished grease pencil data add')
        #print(time.time() - start)
        
        mxT = Matrix.Translation(loc)
        mxR = context.space_data.region_3d.view_rotation.to_matrix().to_4x4()
        
        if "Insertion Axis" in bpy.data.objects:
            ob = bpy.data.objects.get('Insertion Axis')
        else:
            ob = bpy.data.objects.new('Insertion Axis', None)
            ob.empty_draw_type = 'SINGLE_ARROW'
            ob.empty_draw_size = 20
            context.scene.objects.link(ob)
        
        bpy.ops.object.select_all(action = 'DESELECT')
        ob.parent = Model
        ob.matrix_world = mxT * mxR
        context.scene.objects.active = ob
        ob.select = True
        
        context.scene.cursor_location = ob.location
        bpy.ops.view3d.view_center_cursor()
        bpy.ops.view3d.viewnumpad(type = 'FRONT')
        bpy.ops.view3d.view_selected()
        
        context.space_data.transform_manipulators = {'ROTATE'}
        
        splint.insertion_path = True
        Model.lock_location[0], Model.lock_location[1], Model.lock_location[2] = True, True, True
        return {'FINISHED'}

class D3SPLINT_OT_blockout_model_meta(bpy.types.Operator):
    '''Calculates blockout undercut faces'''
    bl_idname = 'd3splint.meta_blockout_object'
    bl_label = "Meta Blockout Object From View"
    bl_options = {'REGISTER','UNDO'}
    
    world = bpy.props.BoolProperty(default = True, name = "Use world coordinate for calculation...almost always should be true.")
    #smooth = bpy.props.BoolProperty(default = True, name = "Smooth the outline.  Slightly less acuurate in some situations but more accurate in others.  Default True for best results")
    resolution = FloatProperty(default = 1.5, min = 0.5, max =3, description = 'Mesh resolution. Lower numbers are slower, bigger numbers less accurate')
    threshold = FloatProperty(default = .09, min = .001, max = .2, description = 'angle to blockout.  .09 is about 5 degrees, .17 is 10degrees.0001 no undercut allowed.')
    
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        return  True

    def invoke(self,context, evenet):
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        tracking.trackUsage("D3Splint:BlockoutUndercuts",None)
        settings = get_settings()
        dbg = settings.debug
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        Model = bpy.data.objects.get(splint.model)
        if Model == None:
            self.report({'ERROR'},'Need to set the model first')
            return {'CANCELLED'}
        
        if 'Insertion Axis' in bpy.data.objects:
            ob = bpy.data.objects.get('Insertion Axis')
            view_mx = ob.matrix_world.to_quaternion()
            view = view_mx * Vector((0,0,1))
            
        else:    
            view = context.space_data.region_3d.view_rotation * Vector((0,0,1))
        
        locs, radii = survey_utils.undercut_faces(context, Model, view, self.threshold, self.world)
        
        mx = Model.matrix_world
        
        meta_data = bpy.data.metaballs.new('Blockout Mesh')
        meta_obj = bpy.data.objects.new('Blockout Mesh', meta_data)
        meta_data.resolution = self.resolution
        meta_data.render_resolution = self.resolution
        context.scene.objects.link(meta_obj)
        
        
        i_mx = mx.inverted()
        view_local = i_mx.to_quaternion() * view
        view_local.normalize()
        for co, radius in zip(locs, radii):
            
            
            mb = meta_data.elements.new(type = 'CAPSULE')
            mb.co = 10 * (co - 2.2 * view_local)
            
            mb.size_x = 10 * 6 #TODO..raycast to find bottom?
            mb.radius = 10 * radius
            
            X = view_local
            Y = Vector((random.random(), random.random(), random.random()))
            Yprime = Y - Y.dot(X)*X
            Yprime.normalize()
            Z = X.cross(Yprime)
            
            #rotation matrix from principal axes
            T = Matrix.Identity(3)  #make the columns of matrix U, V, W
            T[0][0], T[0][1], T[0][2]  = X[0] ,Yprime[0],  Z[0]
            T[1][0], T[1][1], T[1][2]  = X[1], Yprime[1],  Z[1]
            T[2][0] ,T[2][1], T[2][2]  = X[2], Yprime[2],  Z[2]

            Rotation_Matrix = T.to_4x4()
            
            mb.rotation = Rotation_Matrix.to_quaternion()
        
        R = mx.to_quaternion().to_matrix().to_4x4()
        L = Matrix.Translation(mx.to_translation())
        S = Matrix.Scale(.1, 4)
           
        meta_obj.matrix_world =  L * R * S


        return {'FINISHED'}
    
    
    
class D3SPLINT_OT_survey_model_axis(bpy.types.Operator):
    '''Calculates silhouette of of model from the defined insertion axis arrow object'''
    bl_idname = 'd3splint.arrow_silhouette_survey'
    bl_label = "Survey Model From Axis"
    bl_options = {'REGISTER','UNDO'}
    
    world = bpy.props.BoolProperty(default = True, name = "Use world coordinate for calculation...almost always should be true.")
    smooth = bpy.props.BoolProperty(default = True, name = "Smooth the outline.  Slightly less acuurate in some situations but more accurate in others.  Default True for best results")

    @classmethod
    def poll(cls, context):
        
        return  True

    def execute(self, context):
        tracking.trackUsage("D3Splint:SurveyModelArrow",None)
        settings = get_settings()
        dbg = settings.debug
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        Model = bpy.data.objects.get(splint.model)
        if Model == None:
            self.report({'ERROR'},'Need to set the model first')
            return {'CANCELLED'}
        
        Axis = bpy.data.objects.get('Insertion Axis')
        if Axis == None:
            self.report({'ERROR'},'Need to set survey from view first, then adjust axis arrow if needed')
            return {'CANCELLED'}
        
        
        view = Axis.matrix_world.to_quaternion() * Vector((0,0,1))
        
        odcutils.silouette_brute_force(context, Model, view, self.world, self.smooth, debug = dbg)
        Axis.update_tag()
        context.scene.update()
        return {'FINISHED'}
    
     
class D3SPLINT_OT_splint_bezier_model(bpy.types.Operator):
    '''Calc a Splint/Tray from a model and a curve'''
    bl_idname = "d3splint.splint_from_curve"
    bl_label = "Calculate Bezier Splint"
    bl_options = {'REGISTER','UNDO'}

    #splint thickness
    thickness = bpy.props.FloatProperty(name="Thickness", description="Splint Thickness", default=2, min=.3, max=5, options={'ANIMATABLE'})
    
    #cleanup models afterward
    cleanup = bpy.props.BoolProperty(name="Cleanup", description="Apply Modifiers and cleanup models \n Do not use if planning bone support", default=True)
    
    @classmethod
    def poll(cls, context):
        if len(context.scene.odc_splints):
            settings = get_settings()
            dbg = settings.debug
            b = settings.behavior
            behave_mode = settings.behavior_modes[int(b)]
            if  behave_mode in {'ACTIVE','ACTIVE_SELECTED'} and dbg > 2:
                obs =  context.selected_objects
                cond_1 = len(obs) == 2
                ob_types = set([obs[0].type, obs[1].type])
                cond_2 = ('MESH' in ob_types) and ('CURVE' in ob_types)
                return cond_1 and cond_2
                
            else: #we know there are splints..we will determine active one later
                return context.mode == 'OBJECT'
        else:
            return False
            
        
    
    def execute(self, context):
        
            
        settings = get_settings()
        dbg = settings.debug
        
        #first, ensure all models are present and not deleted etc
        odcutils.scene_verification(context.scene, debug = dbg)      
        b = settings.behavior
        behave_mode = settings.behavior_modes[int(b)]
        
        settings = get_settings()
        dbg = settings.debug    
        [ob_sets, tool_sets, space_sets] = odcutils.scene_preserv(context, debug=dbg)
        
        #this is sneaky way of letting me test different things
        if behave_mode in {'ACTIVE','ACTIVE_SELECTED'} and dbg > 2:
            obs = context.selected_objects
            if obs[0].type == 'CURVE':
                model = obs[1]
                margin = obs[0]
            else:
                model = obs[0]
                margin = obs[1]
        
                exclude = ['name','teeth','implants','tooth_string','implant_string']
                splint = odcutils.active_odc_item_candidate(context.scene.odc_splints, obs[0], exclude)
        
        else:
            j = context.scene.odc_splint_index
            splint =context.scene.odc_splints[j]
            if splint.model in bpy.data.objects and splint.margin in bpy.data.objects:
                model = bpy.data.objects[splint.model]
                margin = bpy.data.objects[splint.margin]
            else:
                print('whoopsie...margin and model not defined or something is wrong')
                return {'CANCELLED'}
        
        
        layers_copy = [layer for layer in context.scene.layers]
        context.scene.layers[0] = True
        
        z = Vector((0,0,1))
        vrot= context.space_data.region_3d.view_rotation
        Z = vrot*z
        
        [Splint, Falloff, Refractory] = full_arch_methods.splint_bezier_step_1(context, model, margin, Z, self.thickness, debug=dbg)

        splint.splint = Splint.name #that's a pretty funny statement.
        
        if splint.bone and splint.bone in bpy.data.objects:
            mod = Splint.modifiers['Bone']
            mod.target = bpy.data.objects[splint.bone]
        
        if self.cleanup:
            context.scene.objects.active = Splint
            Splint.select = True
            
            for mod in Splint.modifiers:
                
                if mod.name != 'Bone':
                    if mod.type in {'BOOLEAN', 'SHRINKWRAP'}:
                        if mod.type == 'BOOLEAN' and mod.object:
                            bpy.ops.object.modifier_apply(modifier=mod.name)
                        elif mod.type == 'SHRINKWRAP' and mod.target:
                            bpy.ops.object.modifier_apply(modifier=mod.name)
                    else:
                        bpy.ops.object.modifier_apply(modifier=mod.name)

            context.scene.objects.unlink(Falloff)    
            Falloff.user_clear()
            bpy.data.objects.remove(Falloff)
            
            context.scene.objects.unlink(Refractory)
            Refractory.user_clear()
            bpy.data.objects.remove(Refractory)
            odcutils.scene_reconstruct(context, ob_sets, tool_sets, space_sets, debug=dbg)  
            
        else:
            odcutils.scene_reconstruct(context, ob_sets, tool_sets, space_sets, debug=dbg)  
            Falloff.hide = True
            Refractory.hide = True
                
        for i, layer in enumerate(layers_copy):
            context.scene.layers[i] = layer
        context.scene.layers[10] = True
          
        odcutils.material_management(context, context.scene.odc_splints, debug = dbg)
        odcutils.layer_management(context.scene.odc_splints, debug = dbg)   
        return {'FINISHED'}

class D3SPLINT_OT_splint_margin_trim(bpy.types.Operator):
    '''Cut a model with the margin line'''
    bl_idname = "d3splint.splint_model_trim"
    bl_label = "Splint Trim Full Margin"
    bl_options = {'REGISTER','UNDO'}

    smooth_iterations= bpy.props.IntProperty(name = 'Smooth', default = 5)
    @classmethod
    def poll(cls, context):
        return True
            
        
    
    def execute(self, context):
            
        settings = get_settings()
        j = context.scene.odc_splint_index
        splint =context.scene.odc_splints[j]
        if splint.model in bpy.data.objects and splint.margin in bpy.data.objects:
            Model = bpy.data.objects[splint.model]
            margin = bpy.data.objects[splint.margin]
        else:
            self.report({'ERROR'},'Margin and model not defined')
            return {'CANCELLED'}
        
        if not splint.landmarks_set:
            self.report({'ERROR'}, 'You must set landmarks to get an approximate mounting')
            return {'CANCELLED'}
        
        start = time.time()
        
        mx = margin.matrix_world
        
        new_me = margin.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        bme = bmesh.new()
        bme.from_mesh(new_me)
        
        if 'Margin Cut' not in bpy.data.objects:
            new_ob = bpy.data.objects.new('Margin Cut', new_me)
            context.scene.objects.link(new_ob)
        else:
            new_ob = bpy.data.objects.get('Margin Cut')
            new_ob.data = new_me
            
            
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        
        
        #right and left are consistent across upper and lower jaw
        verts_right = [v for v in bme.verts if (mx*v.co)[1] < 0.0]
        verts_left = [v for v in bme.verts if (mx*v.co)[1] >= 0.0]
        
        
        posterior_right_v = min(verts_right, key = lambda x: x.co[0])
        posterior_left_v = min(verts_left, key = lambda x: x.co[0])
        
        
        
        go = True
        iters = 0
        ed = posterior_right_v.link_edges[0]
        v = posterior_right_v
        verts_in_order = [v]
        while go and iters < 1000:
            iters += 1
            next_v = ed.other_vert(v)
            verts_in_order += [next_v]
            next_eds = [e for e in next_v.link_edges if e != ed]
            ed = next_eds[0]
            v = next_v
            
            if v == posterior_left_v:   
                break
            
        
        
        go = True
        iters = 0
        ed = posterior_right_v.link_edges[1]
        v = posterior_right_v
        verts_in_order1 = [v]
        while go and iters < 1000:
            iters += 1
            next_v = ed.other_vert(v)
            verts_in_order1 += [next_v]
            next_eds = [e for e in next_v.link_edges if e != ed]
            ed = next_eds[0]
            v = next_v
            
            if v == posterior_left_v:   
                break
        
        #trim off verts closer than 10mm from each posterior molar spot
        #hold onto them for later
        r_molar_verts0 = [posterior_right_v]
        rn_0 = 1
        for v in verts_in_order[1:]:
            r = v.co - posterior_right_v.co
            if r.length < 12:
                rn_0 += 1
                r_molar_verts0 += [v]
            else:
                break
                
        r_molar_verts1 = []
        rn_1 = 1
        for v in verts_in_order1[1:]:
            r = v.co - posterior_right_v.co
            if r.length < 12:
                rn_1 += 1
                r_molar_verts1 += [v]
            else:
                break
        verts_in_order = verts_in_order[rn_0:]
        verts_in_order1 = verts_in_order1[rn_1:]
        
        r_molar_verts1.reverse()
        r_molar_verts = r_molar_verts1 + r_molar_verts0
        
            
        l_molar_verts0 = [posterior_left_v]    
        ln_0 = 1
        for v in verts_in_order[-2::-1]:
            r = v.co - posterior_left_v.co
            if r.length < 12:
                ln_0 += 1
                l_molar_verts0 += [v]
            else:
                break
        
        l_molar_verts1 = []
        ln_1 = 1   
        for v in verts_in_order1[-2::-1]:
            r = v.co - posterior_left_v.co
            if r.length < 12:
                ln_1 += 1
                l_molar_verts1 += [v]
            else:
                break    
        
        verts_in_order = verts_in_order[:-ln_0]
        verts_in_order1 = verts_in_order1[:-ln_1]
        
        l_molar_verts0.reverse()
        l_molar_verts = l_molar_verts0 + l_molar_verts1
        
        #make new evenly spaced geometry
        l_molar_locs, eds = space_evenly_on_path([mx * v.co for v in l_molar_verts], [(0,1),(1,2)], 20)
        r_molar_locs, eds = space_evenly_on_path([mx * v.co for v in r_molar_verts], [(0,1),(1,2)], 20)
        
        arch0, eds0 = space_evenly_on_path([mx * v.co for v in verts_in_order], [(0,1),(1,2)], 100)
        arch1, eds1 = space_evenly_on_path([mx * v.co for v in verts_in_order1], [(0,1),(1,2)], 100)
        
        
        new_bme = bmesh.new()
        
        arch_0_vs = []
        for loc in arch0:
            arch_0_vs += [new_bme.verts.new(loc)]                                 
        
        arch_1_vs = []
        for loc in arch1:
            arch_1_vs += [new_bme.verts.new(loc)]
            
        l_molar_vs = []    
        for loc in l_molar_locs:
            l_molar_vs += [new_bme.verts.new(loc)]
        
        r_molar_vs = []    
        for loc in r_molar_locs:
            r_molar_vs += [new_bme.verts.new(loc)]
        
        new_bme.faces.new(l_molar_vs)
        new_bme.faces.new(r_molar_vs)
        
        arch_1_vs = [r_molar_vs[0]] + arch_1_vs + [l_molar_vs[-1]]
        arch_0_vs = [r_molar_vs[-1]] + arch_0_vs + [l_molar_vs[0]]
        
        for i in range(0,len(arch_1_vs)-1):
            a = arch_0_vs[i]
            b = arch_0_vs[i+1]
            d = arch_1_vs[i]
            c = arch_1_vs[i+1]
            new_bme.faces.new([a,b,c,d])
        #new_ob.matrix_world = margin.matrix_world
        
        perimeter_eds = [ed for ed in new_bme.edges if len(ed.link_faces) == 1]
        gdict = bmesh.ops.extrude_edge_only(new_bme, edges = perimeter_eds)
        new_bme.edges.ensure_lookup_table()
        newer_edges = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMEdge)]
        newer_verts = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)]
        offset_bmesh_edge_loop(new_bme, [ed.index for ed in newer_edges], Vector((0,0,1)), -2)
        for v in newer_verts:
            v.co[2] -= .5
        
        new_bme.to_mesh(new_me)
        bme.free()
        
        new_bme.verts.ensure_lookup_table()
        new_bme.faces.ensure_lookup_table()
        
        
        Master = bpy.data.objects.get(splint.model)
        #new_ob.parent = Master
        if not len(new_ob.constraints):
            cons = new_ob.constraints.new('CHILD_OF')
            cons.target = Master
            cons.inverse_matrix = Master.matrix_world.inverted()
            new_ob.hide = True
        
        bvh = BVHTree.FromBMesh(new_bme)
        
        
        for ob in bpy.data.objects:
            ob.select = False
        Master.select = True
        context.scene.objects.active = Master
        #bpy.ops.object.mode_set(mode = 'SCULPT')
        
        trimmed_bme = bmesh.new()
        trimmed_bme.from_mesh(Model.data)
        trimmed_bme.verts.ensure_lookup_table()
        
        mask = trimmed_bme.verts.layers.paint_mask.verify()
        
        for v in trimmed_bme.verts:
            v.select_set(False)
        for ed in trimmed_bme.edges:
            ed.select_set(False)
        for f in trimmed_bme.faces:
            f.select_set(False)
        
            
        long_eds = [ed for ed in trimmed_bme.edges if ed.calc_length() > 1]
        
        #adjacent face to the long edges:
        long_faces = set()
        for ed in long_eds:
            long_faces.update(ed.link_faces)
        
        long_verts = set()
        for f in long_faces:
            long_verts.update(f.verts[:])
        
        print('there are %i long verts' % len(long_verts))
        
        #first, long edges are often degenerate filling of faces
        
        #gdict = bmesh.ops.beautify_fill(trimmed_bme, faces = list(long_faces), edges = list(long_eds))
        
        #gdict = bmesh.ops.dissolve_limit(trimmed_bme, angle_limit = 1/180 * math.pi, verts = list(long_verts), edges = list(long_eds))
        
        #mask = trimmed_bme.verts.layers.paint_mask.verify()
        #print(gdict.keys())
        #then we will subdivide those remaining long edges
        #long_eds = set()
        #for f in gdict['region']:
        #for f in gdict['geom']:
            #if not isinstance(f, bmesh.types.BMFace): continue
        #    for ed in f.edges:
        #        if ed.calc_length() > 1:
        #            long_eds.add(ed)
        
        #for v in trimmed_bme.verts:
        #    if v in long_verts:
        #        v[mask] = 1.0
        #        v.select_set(True)
        #    else:
        #        v[mask] = 0
        
        for v in trimmed_bme.verts:
            if v in long_verts:
                v.select_set(True)
                v[mask] = 1.0
            else:
                v[mask] = 0.0
        for ed in long_eds:
            ed.select_set(True)
        interval_start = time.time()
        
        n_long = len(long_eds)
        iters = 0
        
        
        #def cut_edges_to_length(long_edges):
        #    print('cutting to length')
        #    vert_set = set()
        #    n_long = len(long_edges)
        #    n_cuts = 0
        #    while n_long and n_cuts < 10:
        #        gdict = bmesh.ops.subdivide_edges(trimmed_bme, edges = list(long_eds), cuts = 1)
        #    
                #faces associated with the subdivision
        #        new_edges = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMEdge)]
        #        new_verts = set([ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)])
                
        #        vert_set.update(new_verts)
        #        long_edges = [ed for ed in new_edges if ed.calc_length() > 1]
        #        n_cuts += 1
        #        n_long = len(long_edges)
                
        #    return vert_set
        
        while n_long > 5 and iters < 4:
                        
            #cleaning long edges
            iter_start = time.time()
            
            #cut long edges in half
            print('subdividing %i long edges' % len(long_eds))
            
            gdict = bmesh.ops.subdivide_edges(trimmed_bme, edges = long_eds, cuts = 1)
            non_tris = [f for f in trimmed_bme.faces if len(f.verts) > 3]
            bmesh.ops.triangulate(trimmed_bme, faces = non_tris)
            trimmed_bme.verts.ensure_lookup_table()
            trimmed_bme.edges.ensure_lookup_table()
            trimmed_bme.faces.ensure_lookup_table()
        
            long_eds = [ed for ed in trimmed_bme.edges if ed.calc_length() > 1]
            n_long = len(long_eds)
            iters += 1
            
            #vert_set = cut_edges_to_length(long_eds)
            
            #non_tri_faces = set()
            
            #for v in vert_set:
            #    if v.is_valid:
                    #non_tri_faces.update(v.link_faces[:])
            #faces associated with the subdivision
            #new_faces = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMFace)]
            #new_edges = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMEdge)]
            #new_verts = set([ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)])
                
            #triangulate the faces which were turned into quads or ngons by subdividion
            #non_tri_faces = [f for f in new_faces if len(f.verts) > 3]
            #print('triangulating %i faces' % len(non_tri_faces))
            #gdict = bmesh.ops.triangulate(trimmed_bme, faces = list(non_tri_faces))
            #tri_edges = gdict['edges']
            
            #long_eds = [ed for ed in tri_edges if ed.calc_length() > 1]
            

            
            #merge really short edges
            #short_connected_eds = []
            #for ed in new_edges + tri_edges:
            #    if ed.calc_length() < .05 and all([v in new_verts for v in ed.verts]):
            #        short_connected_eds += [ed]
            
            #print('there are %i short edges' % len(short_connected_eds))   
            #bmesh.ops.collapse(trimmed_bme, edges = short_connected_eds)
            
            #annoyingly find out which verts were removed by collapse...no return dictionary :-(
            #invalid_verts = [v for v in new_verts if not v.is_valid]
            #valid_verts = set(new_verts) - set(invalid_verts)
            
            #poke large area faces
            #big_faces = set()
            #new_non_tris = set()
            #for v in valid_verts:
            #    for f in v.link_faces:
            #        if len(f.verts) > 3:
            #            new_non_tris.add(f)
                        
            #print('there are now %i non tris' % len(new_non_tris))
            #gdict = bmesh.ops.triangulate(trimmed_bme, faces = list(new_non_tris))
            
            #for v in valid_verts:
            #    for f in v.link_faces:
            #        if f.calc_area() > .16:
            #            big_faces.add(f)                         
            #poke_dict = bmesh.ops.poke(trimmed_bme, faces = list(big_faces))
            
            #print(poke_dict.keys())
            
            #for v in poke_dict['verts']:
            #    valid_verts.add(v)
            #    v.select_set(True)
            
            #collapse any new short edges by poking
            #new_short_edges = set()
            #for v in valid_verts:
            #    for ed in v.link_edges:
            #        if ed.calc_length() < .05 and all([v in valid_verts for v in ed.verts]):
            #            new_short_edges.add(ed)
            
            #print('collapsing %i new short edges' % len(new_short_edges))
            #bmesh.ops.collapse(trimmed_bme, edges = list(new_short_edges))
            
            
            #invalid_verts = [v for v in valid_verts if not v.is_valid]
            #valid_verts.difference_update(invalid_verts)
            
            
            #long_eds = set()
            #for v in valid_verts:
            #    for ed in v.link_edges:
            #        if ed.calc_length() > .5:
            #            long_eds.add(ed)
            
            
            #iters += 1
            #n_long = len(long_eds)
        
        
        print('took %f seconds to subdivide long edges in %i iterations' % ((time.time() - interval_start), iters))
        
        
        to_keep = set()
        
        mx2 = Model.matrix_world
        #Z = mx.inverted().to_3x3() * Vector((0,0,1))
        if splint.jaw_type == 'MAXILLA':
            Z = Vector((0,0,1))
        else:
            Z = Vector((0,0,-1))
            
        for v in trimmed_bme.verts:
            a = mx2 * v.co
            
            res = bvh.ray_cast(a, Z, 20)
            if res[0] != None:
                #v.co = Vector((0,0,0))
                to_keep.add(v)
        
    
        above_faces = set()
        for f in trimmed_bme.faces:
            if all([v in to_keep for v in f.verts]):
                above_faces.add(f)
        
        
        border_eds = [ed for ed in trimmed_bme.edges if len([f for f in ed.link_faces if f in above_faces]) == 1]
        
        
        trimmed_bme.edges.ensure_lookup_table()
        loops = edge_loops_from_bmedges(trimmed_bme, [ed.index for ed in border_eds])
        
        if len(loops) > 1:
            
            below_faces = set(trimmed_bme.faces) - above_faces
            
            islands = []
            iters = 0
            while len(below_faces) and iters < 100:
                iters += 1
                seed = below_faces.pop()
                island = flood_selection_faces_limit(trimmed_bme, set([seed]), seed, below_faces, max_iters = 1000)
                islands += [island]
                below_faces.difference_update(island)
        
            print('There are %i islands in below verts' % len(islands))    
            
            for isl in islands:
                print('Island with %i faces' % len(isl))
                if len(isl) < 3000:
                    above_faces.update(isl)
        
            
        
        #above_faces.update(to_keep)
        
        for v in trimmed_bme.verts:
            v.select_set(False)
        for ed in trimmed_bme.edges:
            ed.select_set(False)
        for f in trimmed_bme.faces:
            f.select_set(False)
            
        for f in above_faces:
            to_keep.update(f.verts[:])
        

        to_delete = list(set(trimmed_bme.verts[:]) - set(to_keep))
        new_bme.free()
        
        
        def vert_neighbors(v):
            neigbors = set()
            for ed in v.link_edges:
                neigbors.update([ed.other_vert(v)])
            return neigbors
        
        expand_verts = set()
        exist_verts = set(to_keep)
        for v in exist_verts:
            expand_verts.update(vert_neighbors(v))
        
        expand_verts.difference_update(exist_verts)
        new_verts = expand_verts.copy()
        for i in range(0,3):
            newest_verts = set()
            for v in new_verts:
                newest_verts.update(vert_neighbors(v))
            
            newest_verts.difference_update(exist_verts)
            expand_verts.update(newest_verts)
            new_verts = newest_verts
        
        perim_fs = set()
        for v in expand_verts:
            perim_fs.update(v.link_faces[:])
            
        perim_strim_bme = new_bmesh_from_bmelements(perim_fs)
        
        
        
        if 'Perim Model' in bpy.data.objects:
            perim_ob  = bpy.data.objects.get('Perim Model')
            perim_me  = perim_ob.data
        else:
            
            perim_me = bpy.data.meshes.new('Perim Model')
            perim_ob = bpy.data.objects.new('Perim Model', perim_me)
            context.scene.objects.link(perim_ob)
        
            cons = perim_ob.constraints.new('COPY_TRANSFORMS')
            cons.target = bpy.data.objects.get(splint.model)
        perim_strim_bme.to_mesh(perim_me)
        perim_ob.hide = True
        
        print('deleting %i verts out of %i verts' % (len(to_delete), len(trimmed_bme.verts)))
        bmesh.ops.delete(trimmed_bme, geom = to_delete, context = 1)
  
        trimmed_bme.verts.ensure_lookup_table()
        trimmed_bme.faces.ensure_lookup_table()
        trimmed_bme.edges.ensure_lookup_table()
        trimmed_bme.verts.index_update()
        trimmed_bme.edges.index_update()
        trimmed_bme.faces.index_update()
        
        
        to_delete = []
        for v in trimmed_bme.verts:
            if len(v.link_edges) < 2:
                to_delete.append(v)
                
        print('deleting %i loose verts' % len(to_delete))
        bmesh.ops.delete(trimmed_bme, geom = to_delete, context = 1)
        trimmed_bme.verts.ensure_lookup_table()
        trimmed_bme.faces.ensure_lookup_table()
        trimmed_bme.edges.ensure_lookup_table()
        trimmed_bme.verts.index_update()
        trimmed_bme.edges.index_update()
        trimmed_bme.faces.index_update()
        
        
        ###################################################
        ######  Delete Nodes ##############################
        ###################################################
                
        eds = [ed for ed in trimmed_bme.edges if len(ed.link_faces) == 1]
        
        print('checking for special cases like node vertices etc')
        nodes = set()
        for ed in eds:
            for v in ed.verts:
                if len([ed for ed in v.link_edges if ed in eds]) > 2:
                    nodes.add(v)
        
        print('there are %i nodes' % len(nodes))
        nodes = list(nodes)
        bmesh.ops.delete(trimmed_bme, geom = nodes, context = 1)
        trimmed_bme.verts.ensure_lookup_table()
        trimmed_bme.faces.ensure_lookup_table()
        trimmed_bme.edges.ensure_lookup_table()
        
        #####################################################
        #######  Clean Small Islands  ########################
        #####################################################
        
        start = time.time()
        total_faces = set(trimmed_bme.faces[:])
        islands = []
        iters = 0
        while len(total_faces) and iters < 100:
            iters += 1
            seed = total_faces.pop()
            island = flood_selection_faces(trimmed_bme, {}, seed, max_iters = 10000)
            islands += [island]
            total_faces.difference_update(island)
            
        to_keep = set()
        for isl in islands:
            if len(isl) > 300:
                to_keep.update(isl)
        
        print('keeping %i faces' % len(to_keep))
        
        total_faces = set(trimmed_bme.faces[:])
        del_faces = total_faces - to_keep
        
        bmesh.ops.delete(trimmed_bme, geom = list(del_faces), context = 3)
        del_verts = []
        for v in trimmed_bme.verts:
            if all([f in del_faces for f in v.link_faces]):
                del_verts += [v]        
        bmesh.ops.delete(trimmed_bme, geom = del_verts, context = 1)
        
        
        del_edges = []
        for ed in trimmed_bme.edges:
            if len(ed.link_faces) == 0:
                del_edges += [ed]
        bmesh.ops.delete(trimmed_bme, geom = del_edges, context = 4)    
        finish = time.time()
        print('took %f seconds to clean islands' % (finish - start))
                  
        
        eds = [ed for ed in trimmed_bme.edges if len(ed.link_faces) == 1]
        
        
        gdict = bmesh.ops.extrude_edge_only(trimmed_bme, edges = eds)
        trimmed_bme.edges.ensure_lookup_table()
        new_edges = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMEdge)]
        trimmed_bme.verts.ensure_lookup_table()
        trimmed_bme.edges.ensure_lookup_table()
        trimmed_bme.verts.index_update()
        trimmed_bme.edges.index_update()
        trimmed_bme.faces.index_update()
        
        loops = edge_loops_from_bmedges(trimmed_bme, [ed.index for ed in new_edges])
        print('there are %i loops' % len(loops))
        for loop in loops:
            if len(loop) < 50: continue
            for vi in loop:
                v = trimmed_bme.verts[vi]
                if not v.is_valid:
                    print('invalid vert')
                    continue
                a = mx2 * trimmed_bme.verts[vi].co
                res = bvh.ray_cast(a, Z, 5)
                if res[0] != None:
                    v.co = mx2.inverted() * res[0]
        
        if 'Trimmed_Model' in bpy.data.objects:
            trimmed_obj = bpy.data.objects.get('Trimmed_Model')
            trimmed_model = trimmed_obj.data
        else:
            
            trimmed_model = bpy.data.meshes.new('Trimmed_Model')
            trimmed_obj = bpy.data.objects.new('Trimmed_Model', trimmed_model)
            context.scene.objects.link(trimmed_obj)
        
            cons = trimmed_obj.constraints.new('COPY_TRANSFORMS')
            cons.target = bpy.data.objects.get(splint.model)
        
        trimmed_bme.to_mesh(trimmed_model)
        trimmed_obj.matrix_world = mx2
        trimmed_bme.free()
        
        interval_start = time.time()
        context.scene.objects.active = trimmed_obj
        trimmed_obj.select = True
        trimmed_obj.hide = False
        bpy.ops.object.mode_set(mode = 'SCULPT')
        if not trimmed_obj.use_dynamic_topology_sculpting:
            bpy.ops.sculpt.dynamic_topology_toggle()
        context.scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
        context.scene.tool_settings.sculpt.constant_detail_resolution = 5.5
        bpy.ops.sculpt.detail_flood_fill()
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        print('took %f seconds to detail flood fill' % (time.time() - interval_start))
        trimmed_obj.hide = False
        
        
        ########################################
        ##### Leaving for Historical ###########
        ########################################            
        #trimmed_bme.verts.ensure_lookup_table()
        #quad_faces = set()
        #edges = set()
        #for i in range(6):        
        #    gdict = bmesh.ops.extrude_edge_only(trimmed_bme, edges = new_edges)
        #    trimmed_bme.edges.ensure_lookup_table()
        #    trimmed_bme.verts.ensure_lookup_table()
        #    new_verts = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)]
        #    new_edges = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMEdge)]
        #    new_faces = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMFace)]
            
        #    quad_faces.update(new_faces)
        #    edges.update(new_edges)
        #    for v in new_verts:
        #        v.co += .2 * Z
        
        #gdict = bmesh.ops.triangulate(trimmed_bme, faces = list(quad_faces))
        
        #edges.update(gdict['edges'])
        
        #subdiv_eds = []
        #for ed in edges:
        #    if ed.calc_length() > .2:
        #        subdiv_eds.append(ed)
        
        #print('subdividing %i long edges' % len(subdiv_eds))
        #bmesh.ops.subdivide_edges(trimmed_bme, edges = subdiv_eds, cuts = 1) 
        #loops = edge_loops_from_bmedges(trimmed_bme, [ed.index for ed in new_edges])
        #print('there are %i loops' % len(loops))
        #for loop in loops:
        #    if loop[0] != loop[-1]:continue
        #    loop.pop()
        #    f = [trimmed_bme.verts[i] for i in loop]
        #    trimmed_bme.faces.new(f)
            
        #
        #bmesh.ops.recalc_face_normals(trimmed_bme,faces = trimmed_bme.faces[:])
            
        #TODO, make small islands a bmesh util
        #clean loose verts
        #to_delete = []
        #for v in trimmed_bme.verts:
        #    if len(v.link_edges) < 2:
        #        to_delete.append(v)
                
        #print('deleting %i loose verts after extruding' % len(to_delete))
        #bmesh.ops.delete(trimmed_bme, geom = to_delete, context = 1)
        
        #trimmed_bme.verts.ensure_lookup_table()
        #trimmed_bme.edges.ensure_lookup_table()
        #trimmed_bme.faces.ensure_lookup_table()
        
        #delete edges without faces
        #to_delete = []
        #for ed in trimmed_bme.edges:
        #    if len(ed.link_faces) == 0:
        #        for v in ed.verts:
        #            if len(v.link_faces) == 0:
        #                to_delete.append(v)


        #to_delete = list(set(to_delete))
        #print('deleting %i edges without faces' % len(to_delete))
        #bmesh.ops.delete(trimmed_bme, geom = to_delete, context = 1)
                
        #trimmed_bme.verts.ensure_lookup_table()
        #trimmed_bme.edges.ensure_lookup_table()
        #trimmed_bme.faces.ensure_lookup_table()
              
        #if 'Based_Model' in bpy.data.objects:
        #    based_obj = bpy.data.objects.get('Based_Model')
        #    based_model = based_obj.data
        #else:
        #    based_model = bpy.data.meshes.new('Based_Model')
        #    based_obj = bpy.data.objects.new('Based_Model', based_model)
            
        #    based_obj.matrix_world = mx2
        #    context.scene.objects.link(based_obj)
                
        #    cons = based_obj.constraints.new('CHILD_OF')
        #    cons.target = Master
        #    cons.inverse_matrix = Master.matrix_world.inverted()
        
        
        #trimmed_bme.to_mesh(based_model)
        
        #interval_start = time.time()
        
        #context.scene.objects.active = based_obj
        #based_obj.select = True
        #based_obj.hide = False
        #bpy.ops.object.mode_set(mode = 'SCULPT')
        #if not based_obj.use_dynamic_topology_sculpting:
        #    bpy.ops.sculpt.dynamic_topology_toggle()
        #context.scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
        #context.scene.tool_settings.sculpt.constant_detail_resolution = 5.5
        #bpy.ops.sculpt.detail_flood_fill()
        #bpy.ops.object.mode_set(mode = 'OBJECT')
        
        #print('took %f seconds to detail flood fill' % (time.time() - interval_start))
        #interval_start = time.time()
        #if 'Displace' not in based_obj.modifiers:
        #    mod = based_obj.modifiers.new('Displace', type = 'DISPLACE')
        #    mod.mid_level = 0.85
        #    mod.strength = -1
        
        #print('took %f seconds to add modifier' % (time.time() - interval_start))
        #interval_start = time.time()
        
        Model.hide = True
        #based_obj.hide = False
        
        
        bme.free()
        new_bme.free()
        #trimmed_bme.free()
        #todo remove/delete to_mesh mesh
        splint.trim_upper = True
        splint.ops_string += 'Trim Model:'
        print('took %f finish up hiding and free bmeshes' % (time.time() - interval_start))
        interval_start = time.time()
        print('took %f seconds for entire operation' % (time.time() - start))
        return {'FINISHED'}
    
        
    
          
class D3SPLINT_OT_splint_margin_detail(bpy.types.Operator):
    '''Use dyntopo sculpt to add/remove detail at margin'''
    bl_idname = "d3splint.splint_margin_detail"
    bl_label = "Splint Margin Detail Bezier Splint"
    bl_options = {'REGISTER','UNDO'}

    #splint thickness
    detail = bpy.props.FloatProperty(name="Detail", description="Edge length detail", default=.8, min=.025, max=1, options={'ANIMATABLE'})
    
    
    @classmethod
    def poll(cls, context):
        return True
            
    def execute(self, context):
        
            
        settings = get_settings()
        dbg = settings.debug
        
        
        #first, ensure all models are present and not deleted etc
        odcutils.scene_verification(context.scene, debug = dbg)      
        b = settings.behavior
        behave_mode = settings.behavior_modes[int(b)]
        
        settings = get_settings()
        dbg = settings.debug    
        
        j = context.scene.odc_splint_index
        splint =context.scene.odc_splints[j]
        if splint.model in bpy.data.objects and splint.margin in bpy.data.objects:
            model = bpy.data.objects[splint.model]
            margin = bpy.data.objects[splint.margin]
        else:
            print('whoopsie...margin and model not defined or something is wrong')
            return {'CANCELLED'}
        
        for ob in context.scene.objects:
            ob.select = False
        
        
        bme = bmesh.new()
        bme.from_mesh(model.data)
        bme.normal_update()
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        bvh = BVHTree.FromBMesh(bme)
        
        model.hide = False
        model.select = True
        context.scene.objects.active = model
        
        margin_mesh = margin.to_mesh(context.scene, True, 'PREVIEW')
        mx = margin.matrix_world
        mx2 = model.matrix_world
        
        imx = mx2.inverted()
        
        #try to do it in object space?  But what about 
        margin_path = [imx * mx * v.co for v in margin_mesh.vertices]
        

        
        margin_stroke, stroke_eds = space_evenly_on_path(margin_path, [(0,1),(1,2)], 200)
        
        margin_snaps = [bvh.find_nearest(v) for v in margin_stroke]
        #find_nearest returns (location, normal, index, distance)
        
        
        #new_bme = bmesh.new()
        #new_bme.verts.ensure_lookup_table()
        #new_verts = []
        #for co in margin_stroke:
        #    new_bme.verts.new(co)  
        #new_me = bpy.data.meshes.new('Sculpt Stroke')
        #new_ob = bpy.data.objects.new('Sculpt Stroke', new_me)
        #new_bme.to_mesh(new_me)
        #context.scene.objects.link(new_ob)
        #new_bme.free()
        
            
        bpy.ops.object.mode_set(mode = 'SCULPT')
        if not model.use_dynamic_topology_sculpting:
            bpy.ops.sculpt.dynamic_topology_toggle()
        
        scene = context.scene
        paint_settings = scene.tool_settings.unified_paint_settings
        paint_settings.use_locked_size = True
        paint_settings.unprojected_radius = 1
        brush = bpy.data.brushes['Clay']
        scene.tool_settings.sculpt.brush = brush
        scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
        scene.tool_settings.sculpt.constant_detail = self.detail * 100  #play with this value
        
        brush.strength = 0.0  #we only want to retopologize, not actually sculpt anything
        
        #brush.stroke_method = 'SPACE' 

        
        screen = bpy.context.window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for reg in area.regions:
                    if reg.type == 'WINDOW':
                        break
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        break    
                break
        
        override = bpy.context.copy()
        override['area'] = area
        override['region'] = reg
        override['space_data'] = space
        override['region_data'] = space.region_3d
        override['active_object'] = model
        override['object'] = model
        override['sculpt_object'] = model
        
        no_mx = model.matrix_world.inverted().transposed().to_3x3()
        for i, co in enumerate(margin_stroke):
            
            snap = margin_snaps[i]
            
            f = bme.faces[snap[2]]
    
            Z = no_mx * f.normal
            Y = no_mx * (f.verts[0].co - co)
            Y.normalize()
            X = Y.cross(Z)
            
            #rotation matrix from principal axes
            T = Matrix.Identity(3)  #make the columns of matrix U, V, W
            T[0][0], T[0][1], T[0][2]  = X[0] ,Y[0],  Z[0]
            T[1][0], T[1][1], T[1][2]  = X[1], Y[1],  Z[1]
            T[2][0] ,T[2][1], T[2][2]  = X[2], Y[2],  Z[2]

            Rotation_Matrix = T.to_4x4()
            
            space.region_3d.view_rotation = Rotation_Matrix.to_quaternion()
            space.region_3d.view_location = mx2 * co
            mouse = view3d_utils.location_3d_to_region_2d(reg, space.region_3d, mx2 * co)
            stroke = [{"name": "my_stroke",
                        "mouse" : (mouse[0], mouse[1]),
# [Blender 4.4] Warning: 'pen_flip' parameter removed from painting operators.

                        "is_start": True,
                        "location": (co[0], co[1], co[2]),
                        "pressure": 1,
                        "size" : 20,
                        "time": 1},
                      
                       {"name": "my_stroke",
                        "mouse" : (mouse[0], mouse[1]),
# [Blender 4.4] Warning: 'pen_flip' parameter removed from painting operators.

                        "is_start": False,
                        "location": (co[0], co[1], co[2]),
                        "pressure": 1,
                        "size" : 20,
                        "time": 1}]

            bpy.ops.sculpt.brush_stroke(override, stroke=stroke, mode='NORMAL', ignore_background_click=False)
        
        
        #for view in ['LEFT','RIGHT','TOP','FRONT', 'BACK']:
        #    bpy.ops.view3d.viewnumpad(type = view)
        #    
            
        #    bpy_stroke = []
        #    for i, co in enumerate(margin_stroke):
        
        #       mouse = view3d_utils.location_3d_to_region_2d(reg, space.region_3d, mx2 * co)
        #     
        #       if mouse[0] < 0 or mouse[1] < 0:  #TODO, what about outside the area?  
        #           space.region_3d.view_location = mx2 * co
        #           space.region_3d.update()
        #           mouse = view3d_utils.location_3d_to_region_2d(reg, space.region_3d, mx2 * co)
                
        #        if i == 0:
        #            start = True
        #        else:
        #            start = False
        #        ele = {"name": "my_stroke",
        #                "mouse" : (mouse[0], mouse[1]),
# [Blender 4.4] Warning: 'pen_flip' parameter removed from painting operators.

        #                "is_start": start,
        #                "location": (co[0], co[1], co[2]),
        #                "pressure": 1,
        #                "size" : 20,
        #                "time": 1}
        #        
        #        bpy_stroke.append(ele)
        #    
                
        #    bpy.ops.sculpt.brush_stroke(override, stroke=bpy_stroke, mode='NORMAL', ignore_background_click=False)
        
        bme.free()
        del bvh
        bpy.ops.object.mode_set(mode = 'OBJECT')
        return {'FINISHED'}






def convex_mand_draw_callback(self, context):  
    self.crv.draw(context)
    self.help_box.draw()   
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    outline_region(context.region,(r,g,b,1))  
    
class D3SPLINT_OT_convexify_model(bpy.types.Operator):
    """Click along embrasures to make model locally convex"""
    bl_idname = "d3splint.convexify_lower"
    bl_label = "Convexify Lower Model"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls,context):
        return True

    method1 = EnumProperty(
        description="First Boolean Method",
        items=(("BMESH", "Bmesh", "Faster/More Errors"),
               ("CARVE", "Carve", "Slower/Less Errors")),
        default = "BMESH")
    
    
    method2 = EnumProperty(
        description="Second Boolean Method",
        items=(("BMESH", "Bmesh", "Faster/More Errors"),
               ("CARVE", "Carve", "Slower/Less Errors")),
        default = "CARVE")
    
    
    def make_cubes(self, context):
        
        Z = Vector((0,0,1))
        
        convex_obs = []
        for i in range(0,len(self.crv.b_pts) - 2):
            
            vi = self.crv.b_pts[i]
            vi_p1 = self.crv.b_pts[i+1]
            vi_p2 = self.crv.b_pts[i+2]
            
            l_0 = .5 * (vi + vi_p1)
            
            l_1 = .5 * (vi_p1 + vi_p2)


            #we want a box that spans vi to vi+1
            tan_0 = vi_p1 - vi
            
            #and a box that spans from the midpoint to the midpoint of the next one
            tan_1 = l_1 - l_0
            
            y0 = tan_0.normalized()
            y1 = tan_1.normalized()
            
            x0 = Z.cross(y0)
            x1 = Z.cross(y1)
            
            z_rh0 = x0.cross(y0)
            z_rh1 = x1.cross(y1)
            
            loc_0 = l_0
            loc_1 = vi_p1 
            
            
            T0 = Matrix.Translation(loc_0)
            T1 = Matrix.Translation(loc_1)
            
            R0 = Matrix.Identity(3)
            R0.col[0] = x0
            R0.col[1] = y0
            R0.col[2] = z_rh0
            
            R1 = Matrix.Identity(3)
            R1.col[0] = x1
            R1.col[1] = y1
            R1.col[2] = z_rh1
            
            S0 = Matrix.Identity(3)
            S0[0][0], S0[1][1], S0[2][2] = 14, .93 * tan_0.length, 5
            
            S1 = Matrix.Identity(3)
            S1[0][0], S1[1][1], S1[2][2] = 14, .93 * tan_1.length, 5
            
            
            
            new_me0 = bpy.data.meshes.new('CHull')
            new_ob0 = bpy.data.objects.new('CHull', new_me0)
            
            new_me1 = bpy.data.meshes.new('CHull')
            new_ob1 = bpy.data.objects.new('CHull', new_me1)
            
            context.scene.objects.link(new_ob0)
            context.scene.objects.link(new_ob1)
            
            new_ob0.parent = self.model
            new_ob1.parent = self.model
            
            
            bme = bmesh.new()
            bmesh.ops.create_cube(bme, size = 1)
            bme.to_mesh(new_me0)
            bme.to_mesh(new_me1)
            
            new_ob0.matrix_world = T0 * R0.to_4x4() * S0.to_4x4()
            new_ob1.matrix_world = T1 * R1.to_4x4() * S1.to_4x4()
            
            mod0 = new_ob0.modifiers.new('Boolean', type = 'BOOLEAN')
            mod0.object = self.model
            mod0.solver = self.method1
        
            mod1 = new_ob1.modifiers.new('Boolean', type = 'BOOLEAN')
            mod1.object = self.model
            mod1.solver = self.method1
            
            convex_obs += [new_ob0, new_ob1]
        
        #do the final box
        vi = self.crv.b_pts[-2]
        vi_p1 = self.crv.b_pts[-1]
        
        l_0 = .5 * (vi + vi_p1)
        #we want a box that spans vi to vi+1
        tan_0 = vi_p1 - vi
        y0 = tan_0.normalized()
        
        x0 = Z.cross(y0)
        z_rh0 = x0.cross(y0)
        loc_0 = l_0

        T0 = Matrix.Translation(loc_0)

        R0 = Matrix.Identity(3)
        R0.col[0] = x0
        R0.col[1] = y0
        R0.col[2] = z_rh0
        
        
        S0 = Matrix.Identity(3)
        S0[0][0], S0[1][1], S0[2][2] = 12, .93 * tan_0.length, 5
        

        new_me0 = bpy.data.meshes.new('CHull')
        new_ob0 = bpy.data.objects.new('CHull', new_me0)

        context.scene.objects.link(new_ob0)
        new_ob0.parent = self.model
        
        bme = bmesh.new()
        bmesh.ops.create_cube(bme, size = 1)
        bme.to_mesh(new_me0)

        #transform data...may speed up booleans
        new_ob0.matrix_world = T0 * R0.to_4x4() * S0.to_4x4()

        
        mod0 = new_ob0.modifiers.new('Boolean', type = 'BOOLEAN')
        mod0.object = self.model
        #mod0.operation = 'INTERSECTION'  default
        convex_obs += [new_ob0]
        
        
        
        start = time.time()
        #now convert them all to convex hulls:
        for ob in convex_obs:
            bme = bmesh.new()
            bme.from_object(ob, context.scene, deform = True)
            out_geom = bmesh.ops.convex_hull(bme, input = bme.verts[:], use_existing_faces = True)
            unused_geom = out_geom['geom_interior']
            
            del_v = [ele for ele in unused_geom if isinstance(ele, bmesh.types.BMVert)]
            del_e = [ele for ele in unused_geom if isinstance(ele, bmesh.types.BMEdge)]
            del_f = [ele for ele in unused_geom if isinstance(ele, bmesh.types.BMFace)]
            
            #these must go
            bmesh.ops.delete(bme, geom = del_v, context = 1)
            #bmesh.ops.delete(bme, geom = del_e, context = )
            bmesh.ops.delete(bme, geom = del_f, context = 5)
            #then we need to remove internal faces that got enclosed in

            bad_eds = [ed for ed in bme.edges if len(ed.link_faces) != 2]
            print("there are %i bad eds" % len(bad_eds))
            
            eds_zero_face = [ed for ed in bad_eds if len(ed.link_faces) == 0]
            eds_one_face = [ed for ed in bad_eds if len(ed.link_faces) == 1]
            eds_three_face = [ed for ed in bad_eds if len(ed.link_faces) == 3]
            eds_other = [ed for ed in bad_eds if len(ed.link_faces) > 3]
            
            #bmesh.ops.delete(bme, geom = del_e, context = )
            bmesh.ops.delete(bme, geom = eds_zero_face, context = 2)
            
            ob.modifiers.remove(ob.modifiers[0])
            bme.to_mesh(ob.data)
            
            mod = ob.modifiers.new('Remesh', type = 'REMESH')
            mod.mode = 'SMOOTH'
            mod.octree_depth = 5
            bme.free()
            
            bme = bmesh.new()
            bme.from_object(ob, context.scene, deform = True)
            ob.modifiers.remove(ob.modifiers[0])
            bme.to_mesh(ob.data)
            bme.free()
            

        finish = time.time()
        print('took %f seconds to do the initial hulls' % (finish-start))
        
        
        return {'finish'}
    
        base_ob = convex_obs.pop(0)
        convex_obs.remove(base_ob)
        context.scene.objects.active = base_ob
        base_ob.select = True
        start = time.time()
        for i,ob in enumerate(convex_obs):
            print('boolean %i  out of %i' % (i, len(convex_obs)))
            bme = bmesh.new()
            bme.from_object(ob, context.scene, deform = True)
            ob.modifiers.remove(ob.modifiers[0])
            bme.to_mesh(ob.data)
            bme.free()
            
            name = 'Bool' + str(i)
            mod = base_ob.modifiers.new(name, type = 'BOOLEAN')
            mod.solver = self.method2
            mod.operation = 'UNION'
            mod.object = ob
            
            #bpy.ops.object.modifier_apply(modifier = name)
        context.scene.update()
        new_mesh = base_ob.to_mesh(context.scene, apply_modifiers = True,settings = 'PREVIEW')
        new_ob = bpy.data.objects.new('Convex Object', new_mesh)
        new_ob.matrix_world = base_ob.matrix_world
        context.scene.objects.link(new_ob)
            
        finish = time.time()
        print('took %f seconds to do the boolean joining of hulls' % (finish-start))
        
        #final_mesh = base_ob.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        #final_ob = bpy.data.objects.new('Convex Lower', final_mesh)
        #context.scene.objects.link(final_ob)
        start = time.time()
        bpy.ops.object.select_all(action = 'DESELECT')
        base_ob.select = True
        base_ob.select = True
        for ob in convex_obs:
            ob.select = True
        context.scene.objects.active = ob    
        bpy.ops.object.delete()    
        
        finish = time.time()
        print('took %f seconds to delete temp objects' % (finish-start))
        
        return 'finish'
            
            
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

        #after navigation filter, these are relevant events in this state
        if event.type == 'G' and event.value == 'PRESS':
            if self.crv.grab_initiate():
                return 'grab'
            else:
                #error, need to select a point
                return 'main'
        
        if event.type == 'MOUSEMOVE':
            self.crv.hover(context, event.mouse_region_x, event.mouse_region_y)    
            return 'main'
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            x, y = event.mouse_region_x, event.mouse_region_y
            self.crv.click_add_point(context, x,y)
            return 'main'
        
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            self.crv.click_delete_point(mode = 'mouse')
            return 'main'
        
        if event.type == 'X' and event.value == 'PRESS':
            self.crv.delete_selected(mode = 'selected')
            return 'main'
            
        if event.type == 'RET' and event.value == 'PRESS':
            self.make_cubes(context)
            return 'finish'
            
        elif event.type == 'ESC' and event.value == 'PRESS':
            return 'cancel' 

        return 'main'
    
    def modal_grab(self,context,event):
        # no navigation in grab mode
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            #confirm location
            self.crv.grab_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            self.crv.grab_cancel()
            return 'main'
        
        elif event.type == 'MOUSEMOVE':
            #update the b_pt location
            self.crv.grab_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
            return 'grab'
        
    def modal(self, context, event):
        context.area.tag_redraw()
        
        FSM = {}    
        FSM['main']    = self.modal_main
        FSM['grab']    = self.modal_grab
        FSM['nav']     = self.modal_nav
        
        nmode = FSM[self.mode](context, event)
        
        if nmode == 'nav': 
            return {'PASS_THROUGH'}
        
        if nmode in {'cancel', 'finish'}:
            context.space_data.show_manipulator = True
            context.space_data.transform_manipulators = {'TRANSLATE'}
            #clean up callbacks
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}
        

        if nmode: self.mode = nmode
        
        return {'RUNNING_MODAL'}

    def invoke(self,context, event):
        prefs = get_settings()
        n = context.scene.odc_splint_index
        self.splint = context.scene.odc_splints[n]
        self.crv = None
        margin = "Embrasures"
           
        if self.splint.opposing != '' and self.splint.opposing in bpy.data.objects:
            Model = bpy.data.objects[self.splint.opposing]
            self.model = Model
            
            for ob in bpy.data.objects:
                ob.select = False
                if ob.parent and ob.parent.name == Model.name:
                    if 'CHull' in ob.name:
                        ob.hide = False
                    else:
                        ob.hide = True
                else:
                    ob.hide = True
                
            Model.select = True
            Model.hide = False
            context.scene.objects.active = Model
            bpy.ops.view3d.viewnumpad(type = 'TOP')
            bpy.ops.view3d.view_selected()
            self.crv = CurveDataManager(context,snap_type ='OBJECT', 
                                        snap_object = Model, 
                                        shrink_mod = False, 
                                        name = margin,
                                        cyclic = 'FALSE')
            self.crv.crv_obj.parent = Model
            self.crv.crv_obj.hide = True
            self.crv.point_size, self.crv.point_color, self.crv.active_color = prefs.point_size, prefs.def_point_color, prefs.active_point_color
            
            context.space_data.show_manipulator = False
            context.space_data.transform_manipulators = {'TRANSLATE'}
        else:
            self.report({'ERROR'}, "Need to set the Opposing Model first!")
            return {'CANCELLED'}
            
        
        #self.splint.occl = self.crv.crv_obj.name
        
        #TODO, tweak the modifier as needed
        help_txt = "DRAW EMBRASURE POINTS\n\nLeft Click on the terminal marginal ridge and at each embrasure \n Points will snap to objects under mouse \n Right click to delete a point n\ G to grab  \n ENTER to confirm \n ESC to cancel"
        self.help_box = TextBox(context,500,500,300,200,10,20,help_txt)
        self.help_box.snap_to_corner(context, corner = [1,1])
        self.mode = 'main'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(convex_mand_draw_callback, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self) 
        
        tracking.trackUsage("D3Splint:Convexify",None)

        return {'RUNNING_MODAL'}
    
class D3SPLINT_OT_join_convex(bpy.types.Operator):
    """Attempt to logically smooth and convexify the lower model"""
    bl_idname = "d3splint.join_convex_lower"
    bl_label = "Join Convex Elements"
    bl_options = {'REGISTER', 'UNDO'}
    
    method = EnumProperty(
        description="Method for joinin hulls",
        items=(("SIMPLE", "Join Intersect", "Fastest/Non Manifold/No Errors"),
               ("BOOL_BMESH", "Boolean BMesh", "Slower/Manifold/Some Errors"),
               ("BOOL_CARVE", "Boolean Carve", "Slowest/Manifold/Less Errors")),

        default = "SIMPLE")
    
    
    partial_shrink = BoolProperty(description = 'Copy some of the original model shape', default = True)
    shrink_fact = FloatProperty(name = 'Shrink Factor', default = 0.3, min = 0, max = .8)
    join_to_model = BoolProperty(description = 'Join Convex Object with Lower Model', default = True)
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def invoke(self,context,event):

        return context.window_manager.invoke_props_dialog(self)
        
    def execute(self, context):
        
        
        if len(context.scene.odc_splints) == 0:
            self.report({'ERROR'}, "need to start a splint first")
            return {'CANCELLED'}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        Opposing = bpy.data.objects.get(splint.opposing)
        if not Opposing:
            self.report({'ERROR'}, "need to set opposing model")
            return {'CANCELLED'}
        
        conv_obs = []
        for ob in context.scene.objects:
            if ob.parent and ob.parent == Opposing and 'CHull' in ob.name:
                conv_obs += [ob]
                
        conv_obs.sort(key = lambda x: x.name)
        
        print([ob.name for ob in conv_obs])

        if self.method == 'SIMPLE':
            
            for ob in conv_obs:
                ob.hide = False
            
            bpy.ops.object.select_all(action = 'DESELECT')
            for ob in conv_obs:
                ob.select = True
            context.scene.objects.active = conv_obs[0]
            mx = conv_obs[0].matrix_world
            imx = mx.inverted()
            mx_norm = imx.transposed().to_3x3() #local directions to global
            imx_norm = imx.to_3x3() #global direction to local
            
            bpy.ops.object.join()
            
            #Delete all the internal and lower
            bme = bmesh.new()
            bme.from_mesh(context.object.data)
            bme.verts.ensure_lookup_table()
            
            bvh = BVHTree.FromBMesh(bme)
            
            to_delete = set()
            for v in bme.verts:
                start = v.co + .001 * Vector((0,0,-1))
                hit = bvh.ray_cast(start, Vector((0,0,-1)), 10)
                if hit[0]:
                    to_delete.add(v)
                    
            del_fs = []       
            for f in bme.faces:
                if all([v in to_delete for v in f.verts]):
                    del_fs += [f]
                    
            bmesh.ops.delete(bme, geom = del_fs, context = 5)
            
            bme.to_mesh(context.object.data)        
            bme.free()
            
            if self.partial_shrink:
                if 'Shrink' not in context.object.vertex_groups:
                    vg = context.object.vertex_groups.new(name = 'Shrink')
                else:
                    vg = context.object.vertex_groups['Shrink']
                #make all members, weight at 0    
                vg.add([i for i in range(0,len(context.object.data.vertices))], self.shrink_fact, type = 'REPLACE')
                
                mod = context.object.modifiers.new('Shrink', type = 'SHRINKWRAP')
                mod.vertex_group = 'Shrink'
                mod.target = Opposing
                
                bme = bmesh.new()
                bme.from_object(context.object, context.scene, deform = True)
                
                context.object.modifiers.remove(mod)
                bme.to_mesh(context.object.data)
                bme.free()
                
            if self.join_to_model:
                context.scene.objects.active = Opposing
                Opposing.select = True
                bpy.ops.object.join()     
                      
        return {'FINISHED'}

class D3SPLINT_OT_splint_add_rim_curve(bpy.types.Operator):
    """Create Meta Wax Rim from selected bezier curve"""
    bl_idname = "d3splint.splint_rim_from_curve"
    bl_label = "Create Rim from Curve"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    segments = IntProperty(default = 60, description = 'Resolution of the wax elements')
    posterior_width = FloatProperty(default = 4, description = 'Width of posterior rim')
    anterior_width = FloatProperty(default = 4, description = 'Width of anterior rim')
    thickness = FloatProperty(default = 2, description = 'Height of  rim')
    
    
    flare = IntProperty(default = 0, min = -90, max = 90, description = 'Angle off of world Z')
    meta_type = EnumProperty(name = 'Meta Type', items = [('CUBE','CUBE','CUBE'), 
                                                          ('ELLIPSOID', 'ELLIPSOID','ELLIPSOID')], default = 'CUBE')
    @classmethod
    def poll(cls, context):
        
        if not context.object:
            return False
        
        if context.object.type != 'CURVE':
            return False
        
        return True
    
    def execute(self, context):
            
        crv_obj = context.object
        crv_data = crv_obj.data
        mx = crv_obj.matrix_world
        imx = mx.inverted()
        
        
        if 'Meta Wax' in bpy.data.objects:
            meta_obj = bpy.data.objects.get('Meta Wax')
            meta_data = meta_obj.data
            meta_mx = meta_obj.matrix_world
            
        else:
            meta_data = bpy.data.metaballs.new('Meta Wax')
            meta_obj = bpy.data.objects.new('Meta Wax', meta_data)
            meta_data.resolution = .4
            meta_data.render_resolution = .4
            context.scene.objects.link(meta_obj)
            meta_mx = meta_obj.matrix_world
        
        meta_imx = meta_mx.inverted()
            
        me = crv_obj.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        bme = bmesh.new()
        bme.from_mesh(me)
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        
        loops = edge_loops_from_bmedges(bme, [ed.index for ed in bme.edges])
            
        
        vs0 = [bme.verts[i].co for i in loops[0]]
        
        
        vs_even_0, eds0 = space_evenly_on_path(vs0, [(0,1),(1,2)], self.segments)
        
        
        Z = mx.inverted().to_3x3() * Vector((0,0,1))
        Z.normalize()
            
        for i in range(1,len(vs_even_0)-1):
            
            #factor that tapers end to middle to end
            blend = -abs((i-self.segments/2)/(self.segments/2))+1
            
            v0_0 = vs_even_0[i]
            v0_p1 = vs_even_0[i+1]
            v0_m1 = vs_even_0[i-1]

            
           
            
            X = v0_p1 - v0_m1
            X.normalize()
            
            Qrot = Quaternion(X, math.pi/180 * self.flare)
            Zprime = Qrot * Z
            
            Y = Zprime.cross(X)
            X_c = Y.cross(Zprime) #X corrected
            
            T = Matrix.Identity(3)
            T.col[0] = X_c
            T.col[1] = Y
            T.col[2] = Zprime
            quat = T.to_quaternion()
            
            loc = mx * v0_0
            
            
            mb = meta_data.elements.new(type = self.meta_type)
            mb.size_y = .5 *  (blend*self.anterior_width + (1-blend)*self.posterior_width)
            mb.size_z = self.thickness
            mb.size_x = 1.5
            mb.rotation = quat
            mb.stiffness = 2
            mb.co = meta_imx * loc
            
        
        
        context.scene.update()
        #me = meta_obj.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        #new_ob = bpy.data.objects.new('Flat Plane', me)
        #context.scene.objects.link(new_ob)
        #new_ob.matrix_world = mx

        #context.scene.objects.unlink(meta_obj)
        #bpy.data.objects.remove(meta_obj)
        #bpy.data.metaballs.remove(meta_data)
        
        mat = bpy.data.materials.get("Splint Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Splint Material")
            mat.diffuse_color = get_settings().def_splint_color
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
        
        if mat.name not in meta_obj.data.materials:
            meta_obj.data.materials.append(mat)
        
        bme.free()
        #todo remove/delete to_mesh mesh
  
        return {'FINISHED'}

    
    def invoke(self, context, event):

        return context.window_manager.invoke_props_dialog(self)




class D3SPLINT_OT_clear_margin(bpy.types.Operator):
    """Cear the margin line for a fresh start"""
    bl_idname = "d3splint.clear_margin"
    bl_label = "Clear Splint Margin"
    bl_options = {'REGISTER', 'UNDO'}
    
    target = EnumProperty(name = "Target", items = (('MAX','MAX','MAX'), ('MAND','MAND','MAND')), default = 'MAX')

    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def execute(self, context):
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        if self.target == 'MAX':
            prefix = 'Max '
        else:
            prefix = 'Mand '
        margin = prefix + "Margin"
        if margin not in context.scene.objects:
            self.report({'ERROR'}, "Need to mark splint margin first!")
            return {'CANCELLED'}
            
        Margin = bpy.data.objects.get(margin)
        me = Margin.data
        
        bpy.data.objects.remove(Margin)
        bpy.data.meshes.remove(me)  
            
        splint.margin = ''
        splint.splint_outline = False
        
        return {'FINISHED'}
        
        

    
class D3SPLINT_OT_splint_mount_on_articulator(bpy.types.Operator):
    """Mount models on articulator"""
    bl_idname = "d3splint.splint_mount_articulator"
    bl_label = "Mount in Articulator"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def execute(self, context):
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        opposing = splint.opposing
        Model = bpy.data.objects.get(opposing)
        
        if not Model:
            self.report({'ERROR'},"Please use Add Arcon Articulator function")
            return {'CANCELLED'}
        
        Articulator = bpy.data.objects.get('Articulator')
        if Articulator == None:
            self.report({'ERROR'},"Please use Add Arcon Articulator function")
            return {'CANCELLED'}
        
        tracking.trackUsage("D3Splint:MountOnArticulator",None)
            
        cons = Model.constraints.new(type = 'CHILD_OF')
        cons.target = Articulator
        cons.subtarget = 'Mandibular Bow'
        
        mx = Articulator.matrix_world * Articulator.pose.bones['Mandibular Bow'].matrix
        cons.inverse_matrix = mx.inverted()
        
        #write the lower jaw BVH to cache for fast ray_casting
        bme = bmesh.new()
        bme.from_mesh(Model.data)    
        bvh = BVHTree.FromBMesh(bme)
        splint_cache.write_mesh_cache(Model, bme, bvh)
        
        return {'FINISHED'}



        
class D3SPLINT_OT_splint_join_rim(bpy.types.Operator):
    """Join Rim to Shell"""
    bl_idname = "d3splint.splint_join_rim"
    bl_label = "Join Shell to Rim"
    bl_options = {'REGISTER', 'UNDO'}
    
    override = BoolProperty(default = False, name = 'Override Fuse Again')
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    
    
    def invoke(self, context, event):
        n = context.scene.odc_splint_index
        self.splint = context.scene.odc_splints[n]
        self.override = False  #always force user to override
        
        if self.splint.wax_rim_fuse:
            return context.window_manager.invoke_props_dialog(self, 500)
        else:
            return self.execute(context)
            
        
        
    def execute(self, context):
        
        if self.splint.wax_rim_fuse and not self.override:
            self.report({'ERROR'}, "You have already fused!  Did you mean to fuse again or did fusion fail?")
            return {'CANCELLED'}
        
        Shell = bpy.data.objects.get('Splint Shell')
        Rim = bpy.data.objects.get('Wax Rim')
        
        if Shell == None:
            self.report({'ERROR'}, 'Need to calculate splint shell first')
            return {'CANCELLED'}
        if Rim == None:
            self.report({'ERROR'}, 'Need to calculate rim first')
            return {'CANCELLED'}
        
        tracking.trackUsage("D3Splint:JoinRim",None)
        
        if 'Join Rim' in Shell.modifiers:
            bool_mod = Shell.modifiers.get('Join Rim')
            
        else:
            bool_mod = Shell.modifiers.new('Join Rim', type = 'BOOLEAN')
        
        bool_mod.operation = 'UNION'
        bool_mod.object = Rim
        Rim.hide = True
        Shell.hide = False    
        bool_mod.show_viewport = True
                
        
        self.splint.wax_rim_fuse = True
        self.splint.ops_string += 'JoinRim:' 
        return {'FINISHED'}

    def draw(self,context):
        
        layout = self.layout
        
        #row = layout.row()
        #row.label(text = "%i metaballs will be added" % self.n_verts)
        
        #if self.n_verts > 10000:
        #    row = layout.row()
        #    row.label(text = "WARNING, THIS SEEMS LIKE A LOT")
        #    row = layout.row()
        #    row.label(text = "Consider CANCEL/decimating more or possible long processing time")
        if self.splint.wax_rim_fuse:
            row = layout.row()
            row.label('You have already fused the rim!')
            row = layout.row()
            row.label('If you are intentionally fusing an additional rim, select override')
            row = layout.row()
            row.prop(self, "override")
            row = layout.row()
            row.label('Otherwise cancel, and check knowledge base for rim fusing failure!')
            
        #row = layout.row()
        #row.operator(self.bl_idname, "OK").context = "EXEC_DEFAULT"
      
        
        
        #row = layout.row()
        #row.prop(self, "show_advanced")
        
        #if self.show_advanced:
        #    row = layout.row()
        #    row.prop(self, "resolution")
class D3SPLINT_OT_splint_subtract_surface(bpy.types.Operator):
    """Subtract functions surface from Shell"""
    bl_idname = "d3splint.splint_subtract_surface"
    bl_label = "Subtract Surface from Shell"
    bl_options = {'REGISTER', 'UNDO'}
    
    method = EnumProperty(
        description="First Boolean Method",
        items=(("BMESH", "Bmesh", "Faster/More Errors"),
               ("CARVE", "Carve", "Slower/Less Errors"),
               ("PROJECTION", "Projection", "Fastest/Least Errors")),
        default = "PROJECTION")
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        if len(context.scene.odc_splints) == 0: return False
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        if not splint.dynamic_surface: return False
        return True
    
    def execute(self, context):
        
        if not len(context.scene.odc_splints):
            self.report({'ERROR'}, 'Need to start a splint by setting model first')
            return {'CANCELLED'}
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        Model = bpy.data.objects.get(splint.model)
        Shell = bpy.data.objects.get('Splint Shell')
        Plane = bpy.data.objects.get('Dynamic Occlusal Surface')

        if Shell == None:
            self.report({'ERROR'}, 'Need to calculate splint shell first')
            return {'CANCELLED'}
        if Plane == None:
            self.report({'ERROR'}, 'Need to generate functional surface first')
            return {'CANCELLED'}
        
        tracking.trackUsage("D3Splint:SubtractSurface",None)
        
        old_mode = context.mode
        if old_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
        
        if len(Shell.modifiers):
            Shell.select = True
            Shell.hide = False
            context.scene.objects.active = Shell
            
            for mod in Shell.modifiers:
                bpy.ops.object.modifier_apply(modifier = mod.name)
                
                
        high_verts = []
        bme = bmesh.new()
        bme.from_mesh(Plane.data)
        bme.verts.ensure_lookup_table()
        
        mx_p = Plane.matrix_world
        imx_p = mx_p.inverted()
        
        mx_s = Model.matrix_world
        imx_s = mx_s.inverted()
        
        if splint.jaw_type == 'MAXILLA':
            Z = Vector((0,0,1))
        else:
            Z = Vector((0,0,-1))
            
            
        for v in bme.verts:
            ray_orig = mx_p * v.co
            ray_target = mx_p * v.co - 5 * Z
            ray_target2 = mx_p * v.co + .8 * Z
            
            ok, loc, no, face_ind = Model.ray_cast(imx_s * ray_orig, imx_s * ray_target - imx_s*ray_orig)
        
            if ok:
                high_verts += [v]
                v.co = imx_p * (mx_s * loc - 0.8 * Z)
            else:
                ok, loc, no, face_ind = Model.ray_cast(imx_s * ray_orig, imx_s * ray_target2 - imx_s*ray_orig, distance = 0.8)
                if ok:
                    high_verts += [v]
                    v.co = imx_p * (mx_s * loc - 0.8 * Z)
        
        if len(high_verts):
            self.report({'WARNING'}, 'Sweep surface intersected upper model, corrected it for you!')
            
            mat = bpy.data.materials.get("Bad Material")
            if mat is None:
                # create material
                mat = bpy.data.materials.new(name="Bad Material")
                mat.diffuse_color = Color((1,.3, .3))
        
                Plane.data.materials.append(mat)
            
            for v in high_verts:
                for f in v.link_faces:
                    f.material_index = 1
            bme.to_mesh(Plane.data)
        
           
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        if self.method in {'CARVE', 'BMESH'}:
            bool_mod = Shell.modifiers.new('Subtract Surface', type = 'BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.solver = self.method
            bool_mod.object = Plane
        
        else:
            
            bvh = BVHTree.FromBMesh(bme)
            
            mx_p = Plane.matrix_world
            imx_p = mx_p.inverted()
            
            mx_s = Shell.matrix_world
            imx_s = mx_s.inverted()
            
            sbme = bmesh.new()
            sbme.from_mesh(Shell.data)
            sbme.verts.ensure_lookup_table()
            
            if splint.jaw_type == 'MAXILLA':
                Z = Vector((0,0,1))
            else:
                Z = Vector((0,0,-1))
            
            
            n_ray_casted = 0
            for v in sbme.verts:
                ray_orig = mx_s * v.co
                ray_target = mx_s * ( v.co + 5 * Z )
                
                loc, no, face_ind, d= bvh.ray_cast(imx_p * ray_orig, imx_p * ray_target - imx_p*ray_orig)
                
                if loc:
                    v.co = imx_s * (mx_p * loc)
                    n_ray_casted += 1
                    
          
            sbme.to_mesh(Shell.data)
            Shell.data.update()
            sbme.free()
        Plane.hide = True
        Shell.hide = False
        
        if old_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = old_mode)
            
        splint.subtract_dynamic_surface = True    
        splint.ops_string += 'SubtractSurface:'
        return {'FINISHED'}
    

    
        


class D3SPLINT_OT_meta_splint_surface(bpy.types.Operator):
    """Create Offset Surface from mesh"""
    bl_idname = "d3splint.splint_offset_shell"
    bl_label = "Create Splint Outer Surface"
    bl_options = {'REGISTER', 'UNDO'}
    
    radius = FloatProperty(default = 1.5, min = .6, max = 4, description = 'Thickness of splint', name = 'Thickness')
    #show_advanced = BoolProperty(default = False, description = 'If using Splint module for experimentation or other workflows')
    resolution = FloatProperty(default = .4, min = .1, max = 2.0, description = 'Small values result in more dense meshes and longer processing times, but may be needed for experimental workflows')
    finalize = BoolProperty(default = False, description = 'Will convert meta to mesh and remove meta object')
    
    @classmethod
    def poll(cls, context):
        if "Shell Patch" in bpy.data.objects:
            return True
        else:
            return False
        
    def execute(self, context):
        
        #fit data from inputs to outputs with metaball
        #r_final = .901 * r_input - 0.0219
        
        #rinput = 1/.901 * (r_final + .0219)
        
        
        R_prime = 1/.901 * (self.radius + .0219)
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        self.bme = bmesh.new()
        ob = bpy.data.objects.get('Shell Patch')
        self.bme.from_object(ob, context.scene)
        self.bme.verts.ensure_lookup_table()
        self.bme.edges.ensure_lookup_table()
        mx = ob.matrix_world
        
        meta_data = bpy.data.metaballs.new('Splint Shell')
        meta_obj = bpy.data.objects.new('Meta Splint Shell', meta_data)
        meta_data.resolution = self.resolution
        meta_data.render_resolution = self.resolution
        context.scene.objects.link(meta_obj)
        
        perimeter_edges = [ed for ed in self.bme.edges if len(ed.link_faces) == 1]
        perim_verts = set()
        for ed in perimeter_edges:
            perim_verts.update([ed.verts[0], ed.verts[1]])
            
        perim_verts = list(perim_verts)
        stroke = [v.co for v in perim_verts]
        print('there are %i non man verts' % len(stroke))                                          
        kd = kdtree.KDTree(len(stroke))
        for i in range(0, len(stroke)-1):
            kd.insert(stroke[i], i)
        kd.balance()
        perim_set = set(perim_verts)
        for v in self.bme.verts:
            if v in perim_set: 
                continue
            
            loc, ind, r = kd.find(v.co)
            
            if r and r < .8 * R_prime:
                
                mb = meta_data.elements.new(type = 'BALL')
                mb.co = v.co #+ #(R_prime - r) * v.normal
                mb.radius = .5 * r
                #mb = meta_data.elements.new(type = 'ELLIPSOID')
                #mb.size_z = .45 * r
                #mb.size_y = .45 * self.radius
                #mb.size_x = .45 * self.radius
                #mb.co = v.co
                
                #X = v.normal
                #Y = Vector((0,0,1)).cross(X)
                #Z = X.cross(Y)
                
                #rotation matrix from principal axes
                #T = Matrix.Identity(3)  #make the columns of matrix U, V, W
                #T[0][0], T[0][1], T[0][2]  = X[0] ,Y[0],  Z[0]
                #T[1][0], T[1][1], T[1][2]  = X[1], Y[1],  Z[1]
                #T[2][0] ,T[2][1], T[2][2]  = X[2], Y[2],  Z[2]
    
                #Rotation_Matrix = T.to_4x4()
    
                #mb.rotation = Rotation_Matrix.to_quaternion()
                
            elif r and r < 0.2 * R_prime:
                continue
            else:
                mb = meta_data.elements.new(type = 'BALL')
                mb.radius = R_prime
                mb.co = v.co
            
        meta_obj.matrix_world = mx
        
        context.scene.update()
        me = meta_obj.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        
        mat = bpy.data.materials.get("Splint Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Splint Material")
            mat.diffuse_color = get_settings().def_splint_color
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        if 'Splint Shell' not in bpy.data.objects:
            new_ob = bpy.data.objects.new('Splint Shell', me)
            context.scene.objects.link(new_ob)
            new_ob.matrix_world = mx
            
            cons = new_ob.constraints.new('COPY_TRANSFORMS')
            cons.target = bpy.data.objects.get(splint.model)
            
            
            
            new_ob.data.materials.append(mat)
            
            mod = new_ob.modifiers.new('Smooth', type = 'SMOOTH')
            mod.iterations = 1
            mod.factor = .5
        else:
            new_ob = bpy.data.objects.get('Splint Shell')
            new_ob.data = me
            new_ob.data.materials.append(mat)
            
            to_remove = []
            for mod in new_ob.modifiers:
                if mod.name in {'Remove Teeth', 'Passive Fit'}:
                    to_remove += [mod]
                
            for mod in to_remove:
                new_ob.modifiers.remove(mod)
            
        context.scene.objects.unlink(meta_obj)
        bpy.data.objects.remove(meta_obj)
        bpy.data.metaballs.remove(meta_data)
        
        self.bme.free() 
        tracking.trackUsage("D3Splint:OffsetShell",self.radius)   
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        splint.splint_shell = True
        splint.ops_string += 'Splint Shell:'
        return {'FINISHED'}
    
    def invoke(self, context, event):
        settings = get_settings()
        self.radius = settings.def_shell_thickness
        return context.window_manager.invoke_props_dialog(self)
        #return context.window_manager.invoke_props_popup(self, event)
    
    def draw(self,context):
        
        layout = self.layout
        
        #row = layout.row()
        #row.label(text = "%i metaballs will be added" % self.n_verts)
        
        #if self.n_verts > 10000:
        #    row = layout.row()
        #    row.label(text = "WARNING, THIS SEEMS LIKE A LOT")
        #    row = layout.row()
        #    row.label(text = "Consider CANCEL/decimating more or possible long processing time")
        
        row = layout.row()
        row.prop(self, "radius")
        
        #row = layout.row()
        #row.prop(self, "show_advanced")
        
        #if self.show_advanced:
        #    row = layout.row()
        #    row.prop(self, "resolution")
        


                
class D3SPLINT_OT_meta_splint_passive_spacer(bpy.types.Operator):
    """Create Meta Offset Surface discs on verts, good for thin offsets .075 to 1mm"""
    bl_idname = "d3splint.splint_passive_spacer"
    bl_label = "Create Splint Spacer"
    bl_options = {'REGISTER', 'UNDO'}
    
    radius = FloatProperty(default = .12 , min = .01, max = 1, description = 'Thickness of Offset', name = 'Thickness')
    resolution = FloatProperty(default = 1.5, description = 'Mesh resolution. 1.5 seems ok?')
    scale = FloatProperty(default = 10, description = 'Scale up to make it better')
    
    @classmethod
    def poll(cls, context):
        if "Trimmed_Model" in bpy.data.objects:
            return True
        else:
            return False
        
    def execute(self, context):
        start = time.time()
        interval_start = start
        
        self.bme = bmesh.new()
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        ob0 = bpy.data.objects.get(splint.model)
        ob1 = bpy.data.objects.get('Trimmed_Model')
        ob2 = bpy.data.objects.get('Perim Model')
        
        if not ob0:
            self.report({'ERROR'}, 'Where is your master model!?')
            return {'CANCELLED'}
        
        if not ob1:
            self.report({'ERROR'}, 'Must trim the upper model first')
            return {'CANCELLED'}
        if not ob2:
            self.report({'ERROR'}, 'Must trim the upper model first')
            return {'CANCELLED'}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        splint.passive_value = self.radius
        
        self.bme = bmesh.new()
        self.bme.from_object(ob1, context.scene)  #this object should have a displace modifier
        self.bme.verts.ensure_lookup_table()
        
        bme2 = bmesh.new()
        bme2.from_object(ob2, context.scene)
        bme2.verts.ensure_lookup_table()
        bme2.normal_update()
        
        for v in self.bme.verts: 
            v.co -= .15 * v.normal
        
        for v in bme2.verts:
            v.co -= .16 * v.normal
            
                
        self.bme.normal_update()
        
        
        mx = ob1.matrix_world
        
        meta_data = bpy.data.metaballs.new('Passive Spacer')
        meta_obj = bpy.data.objects.new('Meta Surface Spacer', meta_data)
        meta_data.resolution = self.resolution
        meta_data.render_resolution = self.resolution
        context.scene.objects.link(meta_obj)
        
        n_elipse = 0
        n_ball = 0    
        for v in self.bme.verts[:] + bme2.verts[:]:
            if not len(v.link_edges): continue
            co = v.co
            R = .5 * max([ed.calc_length() for ed in v.link_edges])
            
            
            if True:  ## R > .25 * self.radius:
                n_elipse += 1
                Z = v.normal 
                Z.normalize()
                
                mb = meta_data.elements.new(type = 'ELLIPSOID')
                mb.co = self.scale * co
                mb.size_x = self.scale * R
                mb.size_y = self.scale * R
                mb.size_z = self.scale * (self.radius - .025 + .15)  #surface is pre negatively offset by .15
                
                v_other = v.link_edges[0].other_vert(v)
                x_prime = v_other.co - v.co
                x_prime.normalize()
                Y = Z.cross(x_prime)
                X = Y.cross(Z)
                
                #rotation matrix from principal axes
                T = Matrix.Identity(3)  #make the columns of matrix U, V, W
                T[0][0], T[0][1], T[0][2]  = X[0] ,Y[0],  Z[0]
                T[1][0], T[1][1], T[1][2]  = X[1], Y[1],  Z[1]
                T[2][0] ,T[2][1], T[2][2]  = X[2], Y[2],  Z[2]
    
                Rotation_Matrix = T.to_4x4()
                
                mb.rotation = Rotation_Matrix.to_quaternion()
            else:
                n_ball += 1
                mb = meta_data.elements.new(type = 'BALL')
                mb.co = self.scale * co
                mb.radius = self.scale * (self.radius - .025 + .151)  #base mesh is pre-offset by .15


        print('finished adding metaballs at %f' % (time.time() - start))   
        print('added %i elipses and %i balls' % (n_elipse, n_ball))
            
        R = mx.to_quaternion().to_matrix().to_4x4()
        L = Matrix.Translation(mx.to_translation())
        S = Matrix.Scale(1/self.scale, 4)
           
        meta_obj.matrix_world =  L * R * S
        
        print('transformed the meta ball object %f' % (time.time() - start))
        context.scene.update()
        print('updated the scene %f' % (time.time() - start))
        

        me = meta_obj.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        
        if 'Passive Spacer' in bpy.data.objects:
            new_ob = bpy.data.objects.get('Passive Spacer')
            old_data = new_ob.data
            new_ob.data = me
            old_data.user_clear()
            bpy.data.meshes.remove(old_data)
        else:
            new_ob = bpy.data.objects.new('Passive Spacer', me)
            context.scene.objects.link(new_ob)
        
        new_ob.matrix_world = L * R * S
        mat = bpy.data.materials.get("Spacer Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Spacer Material")
            mat.diffuse_color = Color((0.8, .5, .1))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
        
        if len(new_ob.material_slots) == 0:
            new_ob.data.materials.append(mat)
        
        interval_start = time.time()
        if 'Smooth' not in new_ob.modifiers:
            mod = new_ob.modifiers.new('Smooth', type = 'SMOOTH')
            mod.factor = 1
            mod.iterations = 4
        
        else:
            mod = new_ob.modifiers.get('Smooth')
            
        context.scene.objects.active = new_ob
        new_ob.select = True
        bpy.ops.object.modifier_apply(modifier = 'Smooth')
        
        print('Took %f seconds to smooth BMesh' % (time.time() - interval_start))
        interval_start = time.time()
        
                
        mx = new_ob.matrix_world
        imx = mx.inverted()
        bme = bmesh.new()
        bme.from_object(new_ob, context.scene)
        bme.verts.ensure_lookup_table()
        
        mx_check = ob0.matrix_world
        imx_check = mx_check.inverted()
        bme_check = bmesh.new()
        bme_check.from_mesh(ob0.data)
        bme_check.verts.ensure_lookup_table()
        bme_check.edges.ensure_lookup_table()
        bme_check.faces.ensure_lookup_table()
        bvh = BVHTree.FromBMesh(bme_check)
        
        
        boundary_inds = set()
        for ed in bme_check.edges:
            if len(ed.link_faces) == 1:
                for v in ed.verts:
                    for f in v.link_faces:
                        boundary_inds.add(f.index)
        
        bme_check.free()
        

        
        print('Took %f seconds to initialize BMesh and build BVH' % (time.time() - interval_start))
        interval_start = time.time()
            
        n_corrected = 0
        n_normal = 0
        n_loc = 0
        n_too_far = 0
        n_boundary = 0
        for v in bme.verts:
            #check the distance in trimmed model space
            co = imx_check * mx * v.co
            loc, no, ind, d = bvh.find_nearest(co)
            
            if not loc: continue
            
            if d < self.radius:
                if ind in boundary_inds:
                    n_boundary += 1
                    continue
                n_corrected += 1
                R = co - loc
                
                R.normalize()
                
                if R.dot(no) > 0:
                    delta = self.radius - d + .002
                    co += delta * R
                    n_loc += 1
                else:
                    co = loc + (self.radius + .002) * no
                    n_normal += 1
                    
                v.co = imx * mx_check * co
                v.select_set(True)
            
            elif d > self.radius and d < (self.radius + .05):
                co = loc + (self.radius + .002) * no
                n_too_far += 1
                
            else:
                v.select_set(False)        
        print('corrected %i verts too close offset' % n_corrected)
        print('corrected %i verts using normal method' % n_normal)
        print('corrected %i verts using location method' % n_loc)
        print('corrected %i verts using too far away' % n_too_far)
        print('ignored %i verts clsoe to trim boundary' % n_boundary)
        
        print('Took %f seconds to correct verts' % (time.time() - interval_start))
        interval_start = time.time()
        for mod in new_ob.modifiers:
            new_ob.modifiers.remove(mod)
        
        Master = bpy.data.objects.get(splint.model)
        if 'Child Of' not in new_ob.constraints:
            
            cons = new_ob.constraints.new('CHILD_OF')
            cons.target = Master
            cons.inverse_matrix = Master.matrix_world.inverted()
         
        context.scene.objects.unlink(meta_obj)
        bpy.data.objects.remove(meta_obj)
        bpy.data.metaballs.remove(meta_data)
        
        self.bme.free()
        #deselect, hide etc to show result
        bpy.ops.object.select_all(action = 'DESELECT')
        for ob in context.scene.objects:
            ob.hide = True
        
        Master.hide = False
        
        if 'Blokcout Wax' in bpy.data.objects:
            bwax = bpy.data.objects.get('Blockout Wax')
            bwax.hide = False
            
        bme.to_mesh(new_ob.data)
        bme.free()
        new_ob.hide = False    
        context.scene.objects.active = new_ob
        new_ob.select = True
        
        print('processed in %f seconds' % (time.time() - start))
        bpy.ops.view3d.viewnumpad(type = 'RIGHT')
        tracking.trackUsage("D3Splint:PassiveOffset",str(self.radius)[0:3])
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        splint.passive_offset = True
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        settings = get_settings()
        self.radius = settings.def_passive_radius
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self,context):
        
        layout = self.layout
        
        row = layout.row()
        row.prop(self, "radius")
        #row.prop(self,"resolution")
        #row.prop(self,"scale")


class D3SPLINT_OT_meta_splint_passive_spacer_refine(bpy.types.Operator):
    """Check the spacer for bind points and correct them"""
    bl_idname = "d3splint.passive_spacer_correct"
    bl_label = "Refine Splint Spacer"
    bl_options = {'REGISTER', 'UNDO'}
    

    @classmethod
    def poll(cls, context):
        if "Trimmed_Model" in bpy.data.objects:
            return True
        else:
            return False
        
    def execute(self, context):
        start = time.time()
        self.bme = bmesh.new()
        ob = bpy.data.objects.get('Passive Spacer')
        ob1 = bpy.data.objects.get('Trimmed_Model')
        
        if not ob:
            self.report({'ERROR'}, 'Must Create Passive Spacer First')
            return {'CANCELLED'}
        
        
        start = time.time()
        interval_start = start
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        r = splint.passive_value
        
        mx = ob.matrix_world
        imx = mx.inverted()
        bme = bmesh.new()
        bme.from_object(ob, context.scene)
        bme.verts.ensure_lookup_table()
        
        bme_check = bmesh.new()
        bme_check.from_mesh(ob1.data)
        bme_check.verts.ensure_lookup_table()
        bme_check.edges.ensure_lookup_table()
        bme_check.faces.ensure_lookup_table()
        bvh = BVHTree.FromBMesh(bme_check)
        
        
        
        boundary_inds = set()
        for ed in bme_check.edges:
            if len(ed.link_faces) == 1:
                for v in ed.verts:
                    for f in v.link_faces:
                        boundary_inds.add(f.index)
        
        bme_check.free()
        
        mx_check = ob1.matrix_world
        imx_check = mx_check.inverted()
        
        print('Took %f seconds to initialize BMesh and build BVH' % (time.time() - interval_start))
        interval_start = time.time()
            
        n_corrected = 0
        n_normal = 0
        n_loc = 0
        n_boundary = 0
        for v in bme.verts:
            #check the distance in trimmed model space
            co = imx_check * mx * v.co
            loc, no, ind, d = bvh.find_nearest(co)
            
            if not loc: continue
            
            if d < r:
                if ind in boundary_inds:
                    n_boundary += 1
                    continue
                n_corrected += 1
                R = co - loc
                
                R.normalize()
                
                if R.dot(no) > 0:
                    delta = r - d + .002
                    co += delta * R
                    n_loc += 1
                else:
                    co = loc + (r + .002) * no
                    n_normal += 1
                    
                v.co = imx * mx_check * co
                v.select_set(True)
            
            elif d > r and d < (r + .01):
                co = loc + (r + .002) * no
                n_normal += 1
                
            else:
                v.select_set(False)        
        print('corrected %i verts too close offset' % n_corrected)
        print('corrected %i verts using normal method' % n_normal)
        print('corrected %i verts using location method' % n_loc)
        print('ignored %i verts clsoe to trim boundary' % n_boundary)
        
        print('Took %f seconds to correct verts' % (time.time() - interval_start))
        interval_start = time.time()
        for mod in ob.modifiers:
            ob.modifiers.remove(mod)
            
        bme.to_mesh(ob.data)
        bme.free()
        print('Took %f seconds to update the object data' % (time.time() - interval_start))
        interval_start = time.time()
        
        print('Took %f seconds to do the whole thing' % (time.time() - start))
        interval_start = time.time()  
         
        return {'FINISHED'}
    
         
class D3SPLINT_OT_splint_go_sculpt(bpy.types.Operator):
    '''Enter sculpt mode with good settings to start sculpting'''
    bl_idname = "d3splint.splint_start_sculpt"
    bl_label = "Sculpt Selected Shell"
    bl_options = {'REGISTER','UNDO'}

    #splint thickness
    detail = bpy.props.FloatProperty(name="Detail", description="Edge length detail", default=.8, min=.025, max=1, options={'ANIMATABLE'})
    
    
    @classmethod
    def poll(cls, context):
        if not context.object: return False
        if "Splint Shell" not in context.object.name: return False
        return True
            
    def execute(self, context):
        
        if not len(context.scene.odc_splints):
            self.report({'ERROR'},'You need to plan a splint')
            return {'CANCELLED'}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
           
        Shell = context.object # bpy.data.objects.get('Splint Shell')
        if Shell == None:
            self.report({'ERROR'},"Need a splint shell first")
            return {'CANCELLED'}
        
        #tracking.trackUsage("D3Splint:GoSculpt",None)
        splint.ops_string += "Go to Sculpt:"
        
        Shell.hide = False
        Shell.select = True
        #context.scene.objects.active = Shell
        
        #TODO, use faster method
        for mod in Shell.modifiers:
            me = context.object.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
            old_me = Shell.data
            Shell.modifiers.clear()
            Shell.data = me
            bpy.data.meshes.remove(old_me)
            #bpy.ops.object.modifier_apply(modifier = mod.name)

        if 'Minimum Thickness' in bpy.data.objects:
            min_ob = bpy.data.objects.get('Minimum Thickness')
            min_ob.hide = False
            
             
        bpy.ops.object.mode_set(mode = 'SCULPT')
        if not Shell.use_dynamic_topology_sculpting:
            bpy.ops.sculpt.dynamic_topology_toggle()
        
        scene = context.scene
        paint_settings = scene.tool_settings.unified_paint_settings
        paint_settings.use_locked_size = True
        paint_settings.unprojected_radius = 3
        brush = bpy.data.brushes['Scrape/Peaks']
        scene.tool_settings.sculpt.brush = brush
        scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
        
        
        if bversion() < '002.079.000':
            scene.tool_settings.sculpt.constant_detail = 50
        else:
            scene.tool_settings.sculpt.constant_detail_resolution = 3
        
        scene.tool_settings.sculpt.use_symmetry_x = False
        scene.tool_settings.sculpt.use_symmetry_y = False
        scene.tool_settings.sculpt.use_symmetry_z = False
        brush.strength = .6
        
        for b in bpy.data.brushes:
            b.use_frontface = True
        #brush.stroke_method = 'SPACE' 

        
        return {'FINISHED'}
    
                             
def register():
    #bpy.utils.register_class(D3SPLINT_OT_splint_model)
    bpy.utils.register_class(D3SPLINT_OT_splint_opposing)
    
    bpy.utils.register_class(D3SPLINT_OT_survey_model)
    bpy.utils.register_class(D3SPLINT_OT_survey_model_axis)
    bpy.utils.register_class(D3SPLINT_OT_blockout_model_meta)
    
    bpy.utils.register_class(D3SPLINT_OT_splint_mark_margin)
    bpy.utils.register_class(D3SPLINT_OT_clear_margin)
    bpy.utils.register_class(D3SPLINT_OT_convexify_model)
    bpy.utils.register_class(D3SPLINT_OT_join_convex)
    
    bpy.utils.register_class(D3SPLINT_OT_splint_margin_trim)
    
    bpy.utils.register_class(D3SPLINT_OT_meta_splint_surface)
    bpy.utils.register_class(D3SPLINT_OT_meta_splint_passive_spacer)
    bpy.utils.register_class(D3SPLINT_OT_meta_splint_passive_spacer_refine)
    
    bpy.utils.register_class(D3SPLINT_OT_splint_mount_on_articulator)
    
    
    #bpy.utils.register_class(D3SPLINT_OT_splint_subtract_surface)
    bpy.utils.register_class(D3SPLINT_OT_splint_go_sculpt)
    #bpy.utils.register_class(D3SPLINT_OT_splint_open_pin_on_articulator)
    #Experimental
    #bpy.utils.register_class(D3SPLINT_OT_splint_margin_detail)
    #bpy.utils.register_class(D3SPLINT_OT_splint_margin_trim)
    
    
    #Old from ODC Splints
    #bpy.utils.register_class(D3SPLINT_OT_blockout_model)
    #bpy.utils.register_class(D3SPLINT_OT_link_selection_splint)
    #bpy.utils.register_class(D3SPLINT_OT_splint_bezier_model)
    #bpy.utils.register_class(D3SPLINT_OT_splint_add_guides)
    #bpy.utils.register_class(D3SPLINT_OT_splint_subtract_holes)
    #bpy.utils.register_class(D3SPLINT_OT_mesh_trim_polyline)
    #bpy.utils.register_class(D3SPLINT_OT_splint_report)
    #bpy.utils.register_class(D3SPLINT_OT_splint_subtract_sleeves)
    #bpy.utils.register_class(D3SPLINT_OT_splint_bone)
    #bpy.utils.register_class(D3SPLINT_OT_initiate_arch_curve)
    
    
    #bpy.utils.register_module(__name__)
    
def unregister():
    #bpy.utils.unregister_class(D3SPLINT_OT_splint_model)
    bpy.utils.unregister_class(D3SPLINT_OT_splint_opposing)
    
    bpy.utils.unregister_class(D3SPLINT_OT_survey_model)
    bpy.utils.unregister_class(D3SPLINT_OT_survey_model_axis)
    bpy.utils.unregister_class(D3SPLINT_OT_blockout_model_meta)
    
    bpy.utils.unregister_class(D3SPLINT_OT_splint_mark_margin)
    bpy.utils.unregister_class(D3SPLINT_OT_clear_margin)
    bpy.utils.unregister_class(D3SPLINT_OT_convexify_model)
    bpy.utils.unregister_class(D3SPLINT_OT_join_convex)

    bpy.utils.unregister_class(D3SPLINT_OT_splint_margin_trim)

    bpy.utils.unregister_class(D3SPLINT_OT_meta_splint_surface)
    bpy.utils.unregister_class(D3SPLINT_OT_meta_splint_passive_spacer)
    bpy.utils.unregister_class(D3SPLINT_OT_meta_splint_passive_spacer_refine)
    bpy.utils.unregister_class(D3SPLINT_OT_splint_add_rim)
    
    #bpy.utils.unregister_class(D3SPLINT_OT_splint_join_rim)
    
    bpy.utils.unregister_class(D3SPLINT_OT_splint_mount_on_articulator)
    
   
    bpy.utils.unregister_class(D3SPLINT_OT_splint_subtract_surface)
    bpy.utils.unregister_class(D3SPLINT_OT_splint_go_sculpt)
    
    
    #bpy.utils.unregister_class(D3SPLINT_OT_splint_open_pin_on_articulator)

if __name__ == "__main__":
    register()

# ---- Perplexity API Suggested Migrations ----
To migrate your **BoolProperty** definitions to Blender 4.4, you must define them as class attributes inside a class derived from `bpy.types.PropertyGroup` (or another Blender RNA class), or attach them to Blender types (like `bpy.types.Scene`) during registration. The old style of assigning properties to variables directly is deprecated.

Below is the **corrected code block** for Blender 4.4, assuming you want to define these as part of a custom PropertyGroup:

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    clear: bpy.props.BoolProperty(
        name="Clear",
        description="Replace existing units with selected, \n else add selected to existing",
        default=False
    )
    finalize: bpy.props.BoolProperty(
        name="Finalize",
        description="Apply all modifiers to splint before adding guides?  may take longer, less risk of crashing",
        default=True
    )
    world: bpy.props.BoolProperty(
        name="Use world coordinate for calculation...almost always should be true.",
        default=True
    )
    smooth: bpy.props.BoolProperty(
        name="Smooth the outline.  Slightly less acuurate in some situations but more accurate in others.  Default True for best results",
        default=True
    )

# Register the property group and add it to the scene
def register():
    bpy.utils.register_class(MyProperties)
    bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyProperties)

def unregister():
    del bpy.types.Scene.my_props
    bpy.utils.unregister_class(MyProperties)
```

**Key changes:**
- Properties are now defined as class attributes with a colon (`:`) and not assigned to variables.
- Use a `PropertyGroup` to group related properties.
- Register the property group and attach it to a Blender type (e.g., `Scene`) using a `PointerProperty`[4].

**Note:**  
- Remove duplicate or misspelled property definitions (e.g., multiple `finalize` and `world`).
- If you want to add these properties directly to `Scene` or another type, do so in the `register()` function, not as standalone variables[4].

This code is compatible with Blender 4.4 and follows current API conventions.
Here are the corrected property definitions for Blender 4.4. In Blender 2.8 and later, including 4.4, property definitions must be assigned as class attributes inside a class derived from bpy.types.PropertyGroup, bpy.types.Operator, or similar, not as standalone variables. The options argument is also deprecated for most property types.

Below is the updated code block for use inside a class (e.g., a PropertyGroup):

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    thickness: bpy.props.FloatProperty(
        name="Thickness",
        description="Splint Thickness",
        default=2.0,
        min=0.3,
        max=5.0
    )
    cleanup: bpy.props.BoolProperty(
        name="Cleanup",
        description="Apply Modifiers and cleanup models \nDo not use if planning bone support",
        default=True
    )
    smooth_iterations: bpy.props.IntProperty(
        name='Smooth',
        default=5
    )
    detail: bpy.props.FloatProperty(
        name="Detail",
        description="Edge length detail",
        default=0.8,
        min=0.025,
        max=1.0
    )
```

**Key changes:**
- Properties are now defined as class attributes with a colon (`:`) instead of assignment (`=`).
- The `options` argument is removed, as it is no longer supported for these property types.
- Only one definition for `detail` is included (duplicate removed).
- All numeric literals use floats where appropriate (e.g., `2.0` instead of `2`).

To register this property group, use:

```python
bpy.utils.register_class(MyProperties)
bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyProperties)
```

This is the Blender 4.4 compatible way to define and register custom properties.
