'''
Created on Jul 7, 2018

@author: Patrick
'''
import time
import math

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix, Color
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d
import odcutils
from common_utilities import bversion, get_settings, showErrorMessage
from common_drawing import outline_region
from textbox import TextBox
from survey_utils import bme_undercut_faces
from vertex_color_utils import bmesh_color_bmfaces, add_volcolor_material_to_obj

from segmentation.cookiecutter.cookiecutter import CookieCutter
from segmentation.common import ui
from segmentation.common.blender import show_blender_popup


def pick_axis_draw_callback(self, context):  
    self.help_box.draw()
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    outline_region(context.region,(r,g,b,1))
    
class D3SPLINT_OT_live_insertion_axis(bpy.types.Operator):
    """Pick Insertin Axis by viewing model from occlusal"""
    bl_idname = "d3splint.live_insertion_axis"
    bl_label = "Pick Insertion Axis"
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

        if event.type in {'NUMPAD_1', 'NUMPAD_3', "NUMPAD_7"} and event.value == 'PRESS':
            return 'nav'
              
        if "ARROW" in event.type and event.value == 'PRESS':
            self.rotate_arrow(context, event)
            return 'main'
        if event.type == 'LEFTMOUSE'  and event.value == 'PRESS':
            x, y = event.mouse_region_x, event.mouse_region_y
            res = self.click_model(context, x, y)
            if res:
                self.preview_direction(context)
            return 'main'
        
        if event.type == 'P' and event.value == 'PRESS':
            self.preview_direction(context)
            return 'main'
          
        if event.type == 'RET' and event.value == 'PRESS':
            self.finish(context)
            return 'finish'
            
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
            #context.space_data.show_manipulator = True
            
            #if nmode == 'finish':
            #    context.space_data.transform_manipulators = {'TRANSLATE', 'ROTATE'}
            #else:
            #    context.space_data.transform_manipulators = {'TRANSLATE'}
            #clean up callbacks
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'} if nmode == 'finish' else {'CANCELLED'}
        
        if nmode: self.mode = nmode
        
        return {'RUNNING_MODAL'}

    def invoke(self,context, event):
        
        if len(context.scene.odc_splints) == 0:
            self.report({'ERROR'}, "Need to mark splint and opposing models first")
            return {'CANCELLED'}
        n = context.scene.odc_splint_index
        self.splint = context.scene.odc_splints[n]    
        self.previewed = False
        
        max_model = self.splint.get_maxilla()
        mand_model = self.splint.get_mandible()
        
        if self.splint.jaw_type == 'MANDIBLE':
            Model = bpy.data.objects.get(mand_model)
            
        else:
            Model = bpy.data.objects.get(max_model)
     
        for ob in bpy.data.objects:
            ob.select = False
            ob.hide = True
        Model.select = True
        Model.hide = False
        context.scene.objects.active = Model
        
        add_volcolor_material_to_obj(Model, 'Undercut')
        
        #view a presumptive occlusal axis
        if self.splint.jaw_type == 'MAXILLA':
            bpy.ops.view3d.viewnumpad(type = 'BOTTOM')
        else:
            bpy.ops.view3d.viewnumpad(type = 'TOP')
            
        
        #add in a insertin axis direction
        loc = odcutils.get_bbox_center(Model, world = True)
        view = context.space_data.region_3d.view_rotation * Vector((0,0,1))    
        mxT = Matrix.Translation(loc)
        mxR = context.space_data.region_3d.view_rotation.to_matrix().to_4x4()
        
        if "Insertion Axis" in bpy.data.objects:
            ins_ob = bpy.data.objects.get('Insertion Axis')
            
        else:
            ins_ob = bpy.data.objects.new('Insertion Axis', None)
            ins_ob.empty_draw_type = 'SINGLE_ARROW'
            ins_ob.empty_draw_size = 20
            context.scene.objects.link(ins_ob)
        
        ins_ob.hide = False
        ins_ob.parent = Model
        ins_ob.matrix_world = mxT * mxR
        
        self.ins_ob = ins_ob
        
        #get bmesh data to process
        self.bme = bmesh.new()
        self.bme.from_mesh(Model.data)
        self.bme.verts.ensure_lookup_table()
        self.bme.edges.ensure_lookup_table()
        self.bme.faces.ensure_lookup_table()
        
        self.model = Model
        
        bpy.ops.view3d.view_selected()
        context.space_data.viewport_shade = 'SOLID'
        context.space_data.show_textured_solid = True
        
        #TODO, tweak the modifier as needed
        help_txt = "Pick Insertion Axis\n\n-  Position your viewing direction looking onto the model\n-  LEFT CLICK on the model\n-  You can then rotate and pan your view to assess the undercuts.  This process can be repeated until the desired insertion axis is chosen.\n\nADVANCED USE\n\n-  Use LEFT_ARROW, RIGHT_ARROW, UP_ARROW and DOWN_ARROW to accurately alter the axis.  Holding SHIFT while pressing the ARROW keys will alter the axis by 0.5 degrees.\nPress ENTER when finished"
        self.help_box = TextBox(context,500,500,300,200,10,20,help_txt)
        self.help_box.snap_to_corner(context, corner = [1,1])
        self.mode = 'main'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(pick_axis_draw_callback, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        
        prefs = get_settings()
        r,g,b = prefs.undercut_color
        self.ucolor = Color((r,g,b))
    
    
    
        return {'RUNNING_MODAL'}

    def rotate_arrow(self, context, event):
        loc = Matrix.Translation(self.ins_ob.matrix_world.to_translation())
        rot_base = self.ins_ob.matrix_world.to_3x3()
        
        r_model = self.model.matrix_world.to_quaternion()
        
        
        if event.type == "UP_ARROW":
            axis = r_model * Vector((0,1,0))
        if event.type == "DOWN_ARROW":
            axis = r_model * Vector((0,-1,0))
        if event.type == "LEFT_ARROW":
            axis = r_model * Vector((1,0,0))
        if event.type == "RIGHT_ARROW":        
            axis = r_model * Vector((-1,0,0))
            
        
        if event.shift:
            ang = .5 * math.pi/180
        else:
            ang = 2.5*math.pi/180
        
        rot = Matrix.Rotation(ang, 3, axis)
        self.ins_ob.matrix_world = loc * (rot * rot_base).to_4x4()
        
        view = self.ins_ob.matrix_world.to_quaternion() * Vector((0,0,1))
        view_local = self.model.matrix_world.inverted().to_quaternion() * view
        fs_undercut = bme_undercut_faces(self.bme, view_local)
        vcolor_data = self.bme.loops.layers.color['Undercut']
        bmesh_color_bmfaces(self.bme.faces[:], vcolor_data, Color((1,1,1)))
        bmesh_color_bmfaces(fs_undercut, vcolor_data, self.ucolor)
        self.bme.to_mesh(self.model.data)
        return
    
    def click_model(self,context,x, y):
        region = context.region
        rv3d = context.region_data
        coord = x, y
        ray_max = 10000
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * ray_max)

        imx = self.model.matrix_world.inverted()
        
        result, loc, normal, idx = self.model.ray_cast(imx * ray_origin, imx * ray_target - imx*ray_origin)

        return result
    
    def preview_direction(self, context):
        
        start = time.time()
        view = context.space_data.region_3d.view_rotation * Vector((0,0,1))
        mx = self.model.matrix_world
        i_mx = mx.inverted()
        view_local = i_mx.to_quaternion() * view
        fs_undercut = bme_undercut_faces(self.bme, view_local)
        print('there are %i undercts' % len(fs_undercut))
        vcolor_data = self.bme.loops.layers.color['Undercut']
        bmesh_color_bmfaces(self.bme.faces[:], vcolor_data, Color((1,1,1)))
        bmesh_color_bmfaces(fs_undercut, vcolor_data, self.ucolor)
        self.bme.to_mesh(self.model.data)
        finish = time.time()
        print('took %s to detect undercuts' % str(finish - start)[0:4])
        
        loc = odcutils.get_bbox_center(self.model, world = True)
        mxT = Matrix.Translation(loc)
        mxR = context.space_data.region_3d.view_rotation.to_matrix().to_4x4()
        self.ins_ob.matrix_world = mxT * mxR
        
        self.previewed = True
        return
        
    def finish(self, context):
        
        loc = odcutils.get_bbox_center(self.model, world = True)
        ins_ob = bpy.data.objects.get('Insertion Axis')
        view = ins_ob.matrix_world.to_quaternion() * Vector((0,0,1))
        
        #view = context.space_data.region_3d.view_rotation * Vector((0,0,1))
        odcutils.silouette_brute_force(context, self.model, view, True)
        survey = bpy.data.objects.get(self.model.name + '_silhouette')
        mx = survey.matrix_world
        survey.parent = self.model
        survey.matrix_world = mx
        survey.hide_select = True
        #mxT = Matrix.Translation(loc)
        #mxR = context.space_data.region_3d.view_rotation.to_matrix().to_4x4()
        
        #if "Insertion Axis" in bpy.data.objects:
        #    ob = bpy.data.objects.get('Insertion Axis')
        #    ob.hide = False
        #else:
        #    ob = bpy.data.objects.new('Insertion Axis', None)
        #    ob.empty_draw_type = 'SINGLE_ARROW'
        #    ob.empty_draw_size = 20
        #    context.scene.objects.link(ob)
        
        bpy.ops.object.select_all(action = 'DESELECT')
        #ob.parent = self.model
        #ob.matrix_world = mxT * mxR
        context.scene.objects.active = self.model
        self.model.select = True
        
        #context.scene.cursor_location = loc
        #bpy.ops.view3d.view_center_cursor()
        #bpy.ops.view3d.viewnumpad(type = 'FRONT')
        #bpy.ops.view3d.view_selected()
        
        #context.space_data.transform_manipulators = {'ROTATE'}
        
        for i, mat in enumerate(self.model.data.materials):
            if mat.name == 'Undercut':
                break
        self.model.data.materials.pop(i, update_data = True)
        context.space_data.show_textured_solid = False
        self.splint.insertion_path = True
        self.model.lock_location[0], self.model.lock_location[1], self.model.lock_location[2] = True, True, True
        


class D3Splint_OT_cookie_insertion_axis(CookieCutter):
    """ Pick Insertion Axis """
    operator_id    = "d3splint.pick_insertion_axis_2"
    bl_idname      = "d3splint.pick_insertion_axis_2"
    bl_label       = "Pick Insertion Axis 2"
    bl_description = "Choose the insertion axis direction"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"

    default_keymap = {
        "commit": {"RET"},
        "cancel": {"ESC"},
    }

    @classmethod
    def can_start(cls, context):
        """ Start only splint started and model indicated"""
        
        if len(context.scene.odc_splints) == 0:
            return False
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]    
        max_model = splint.get_maxilla()
        mand_model = splint.get_mandible()
       
        if max_model != '' or mand_model != '':
            return True
        else:
            return False
        
    def initialize_visualization(self):
        for ob in self.context.scene.objects:
            ob.hide = True
        
        self.model.select = True
        self.model.hide = False
        self.context.scene.objects.active = self.model

        self.ins_ob.hide = False
        #add_volcolor_material_to_obj(self.model, 'Undercut')
        
        #view a presumptive occlusal axis
        if self.jaw_mode == 'Max':
            bpy.ops.view3d.viewnumpad(type = 'BOTTOM')
        else:
            bpy.ops.view3d.viewnumpad(type = 'TOP')
        
        self.context.space_data.show_manipulator = False
        self.context.space_data.viewport_shade = 'SOLID'
        self.context.space_data.show_textured_solid = True
        
    def get_or_create_insertion_axis(self):
        
        #add in a insertin axis direction
        loc = odcutils.get_bbox_center(self.model, world = True)
        view = self.context.space_data.region_3d.view_rotation * Vector((0,0,1))    
        mxT = Matrix.Translation(loc)
        
        if self.jaw_mode == 'Max':
            mxR = Matrix.Rotation(math.pi, 4, 'X')
        else:
            mxR = Matrix.Identity(4)
            #mxR = self.context.space_data.region_3d.view_rotation.to_matrix().to_4x4()
        
        
        
        if self.jaw_mode + " Insertion Axis" in bpy.data.objects:
            ins_ob = bpy.data.objects.get(self.jaw_mode + ' Insertion Axis')
            
        else:
            ins_ob = bpy.data.objects.new(self.jaw_mode + ' Insertion Axis', None)
            ins_ob.empty_draw_type = 'SINGLE_ARROW'
            ins_ob.empty_draw_size = 20
            self.context.scene.objects.link(ins_ob)
        
        ins_ob.hide = False
        ins_ob.parent = self.model
        ins_ob.matrix_world = mxT * mxR
        
        return ins_ob
        
    
    def get_bmesh_data(self):
        #get bmesh data to process
        bme = bmesh.new()
        bme.from_mesh(self.model.data)
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        
        return bme
    
    
    def start_pre(self):
        self.jaw_mode = 'Max'
        max_model = self.splint.get_maxilla()
        Model = bpy.data.objects.get(max_model)
        add_volcolor_material_to_obj(Model, 'Undercut')
        Model.hide = False
        self.model = Model
        
    
        
    def start(self):
        """ initialization function """
        bpy.context.scene.frame_set(0)
        bpy.context.scene.frame_set(0)
        bpy.ops.ed.undo_push()  # push current state to undo
        
        
        self.context = bpy.context
        n = self.context.scene.odc_splint_index
        self.splint = self.context.scene.odc_splints[n]    
        
        
        self.start_pre()
        
        self.ins_ob = self.get_or_create_insertion_axis()
        self.bme = self.get_bmesh_data()
        
        prefs = get_settings()
        
        # initialize vars
        self.previewed = False
        self.tweak_angle = 1.5
        r,g,b = prefs.undercut_color
        self.ucolor = Color((r,g,b))
        
        #set view
        self.initialize_visualization()
        
        self.start_ui()
        bpy.ops.ed.undo_push()
        #self.header_text_set("Insertion Axis")
        #self.manipulator_hide()

    def commit_button(self):
        if self.can_commit():
            self.done()
            
        return
    def end_commit(self):
        """ Commit changes to mesh! """
        loc = odcutils.get_bbox_center(self.model, world = True)
        ins_ob = bpy.data.objects.get(self.jaw_mode + ' Insertion Axis')
        view = ins_ob.matrix_world.to_quaternion() * Vector((0,0,1))
        
        #view = context.space_data.region_3d.view_rotation * Vector((0,0,1))
        odcutils.silouette_brute_force(self.context, self.model, view, True)
        bpy.ops.object.select_all(action = 'DESELECT')
        self.context.scene.objects.active = self.model
        self.model.select = True
        
        for i, mat in enumerate(self.model.data.materials):
            if mat.name == 'Undercut':
                break
        self.model.data.materials.pop(i, update_data = True)
        
        print(len(self.model.material_slots))
        model_mat = bpy.data.materials.get('Model Mat')
        self.model.data.materials.append(model_mat)
        self.model.material_slots[0].material = model_mat
        
        
        survey = bpy.data.objects.get(self.model.name + '_silhouette')
        mx = survey.matrix_world
        survey.parent = self.model
        survey.matrix_world = mx
        survey.hide_select = True
        
        
        self.context.space_data.show_textured_solid = False
        
        if self.jaw_mode == 'Max':
            self.splint.max_insertion_complete = True
        else:
            self.splint.mand_insertion_complete = True
            
        self.splint.ops_string += 'PickInsertionAxis {}:'.format(self.jaw_mode)
        
        self.model.lock_location[0], self.model.lock_location[1], self.model.lock_location[2] = True, True, True
        self.model.lock_rotations_4d = True
        self.model.lock_rotation[0] = True
        self.model.lock_rotation[1] = True
        self.model.lock_rotation[2] = True
        self.model.lock_rotation_w = True
        
        bpy.ops.view3d.viewnumpad(type = 'RIGHT')
        
        #bpy.ops.ed.undo_push()
        #self.context.header_text_set() done
        
        #create the optimized model
        #print('SHOWIN POPUP')
        #show_blender_popup("Please wait 10 to 30 seconds while Optimized Model is calculated", "Optimzed Model Calculating", icon = 'INFO')
        #bpy.ops.d3splint.optimized_model()

    def end_cancel(self):
        """ Cancel changes """
        bpy.ops.ed.undo()   # undo geometry hide

    def end(self):
        """ Restore everything, because we're done """
        #self.manipulator_restore()
        #self.header_text_restore()
        #self.cursor_modal_restore()
        return

    def update(self):
        """ Check if we need to update any internal data structures """
        pass
    
    
    
    def top_view(self):
                #view a presumptive occlusal axis
        if self.jaw_mode == 'Max':
            bpy.ops.view3d.viewnumpad(type = 'BOTTOM')
        else:
            bpy.ops.view3d.viewnumpad(type = 'TOP')
        
    def front_view(self):
        bpy.ops.view3d.viewnumpad(type = 'RIGHT')
        
    def right_view(self):
        bpy.ops.view3d.viewnumpad(type = 'FRONT')
        
    def left_view(self):
        bpy.ops.view3d.viewnumpad(type = 'BACK')
        
    def insert_view(self):
        mx = self.ins_ob.matrix_world
        q = mx.to_quaternion()
        self.context.space_data.region_3d.view_rotation = q
    
            

    def start_ui(self):
        self.instructions = {
            "basic": "Position your view to match the desired path of insertion for the splint",
            "objective": "Choose a path that creates even amounts of undercut bilaterally",
            "capture": "Use the 'Capture View' button to store the view direction as the path of insertion",
            "assess": "After 'Capture View', inspect from different angles",
            "adjust": "Use the tweak buttons to adjust the path of insertion in small increments",
            "commit": "When satisfactory path of insertion has been achieved, press the 'Commit' button"
        }
        
        #TOOLS Window
        win_tools = self.wm.create_window('Insertion Axis Tools', {'pos':7, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})

        tools_container = win_tools.add(ui.UI_Container())
        tools_container.rounded_background = True
        
        actual_tools = tools_container.add(ui.UI_Frame('View Capature', fontsize=14))
        cview = actual_tools.add(ui.UI_Button('Capture View', self.capture_view, bgcolor = (.4, .8, .4, .9), margin = 3))
        
        tweak_tools = tools_container.add(ui.UI_Frame('Tweak Direction', fontsize=14))
        tweak_tools.add(ui.UI_Button('Tweak Anterior', self.tweak_anterior, margin = 3))
        tweak_tools.add(ui.UI_Button('Tweak Posterior', self.tweak_posterior, margin = 3))
        tweak_tools.add(ui.UI_Button('Tweak Right', self.tweak_right, margin = 3))
        tweak_tools.add(ui.UI_Button('Tweak Left', self.tweak_left, margin = 3))
        
        tweak_tools = tools_container.add(ui.UI_Frame('Finish', fontsize=14))
        tweak_tools.add(ui.UI_Button('Commit', self.commit_button, margin = 3))
        tweak_tools.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin = 3))
        
        
        
        #HELP AND OPTIOND WINDO
        info = self.wm.create_window('Insertion Axis Help', {'pos':9, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})
        #info.add(ui.UI_Label('Instructions', fontsize=16, align=0, margin=4))
        collapse = info.add(ui.UI_Collapsible('Instructions          ',collapsed = False))
        self.inst_paragraphs = [collapse.add(ui.UI_Markdown('', min_size=(200,10))) for i in range(7)]
        
        self.inst_paragraphs[0].set_markdown(self.instructions['basic'])
        self.inst_paragraphs[1].set_markdown('Objective: ' + self.instructions['objective'])
        self.inst_paragraphs[2].set_markdown('- ' + self.instructions['capture'])
        self.inst_paragraphs[3].set_markdown('- ' + self.instructions['assess'])
        self.inst_paragraphs[4].set_markdown('- ' + self.instructions['adjust'])
        self.inst_paragraphs[5].set_markdown('- ' + self.instructions['commit'])
        
        
        for i in self.inst_paragraphs: i.visible = True
        
        #self.ui_instructions = info.add(ui.UI_Markdown('test', min_size=(200,200)))
        options = info.add(ui.UI_Frame('View Helpers', fontsize=14))
        options.add(ui.UI_Button('Top View', self.top_view, margin = 3))
        options.add(ui.UI_Button('Right View', self.right_view, margin = 3))
        options.add(ui.UI_Button('Left View', self.left_view, margin = 3))
        options.add(ui.UI_Button('Front View', self.front_view, margin = 3))
        options.add(ui.UI_Button('Insertion View', self.insert_view, margin = 3))
    
    
    def update_undercut_shadow(self):
        view = self.ins_ob.matrix_world.to_quaternion() * Vector((0,0,1))
        view_local = self.model.matrix_world.inverted().to_quaternion() * view
        fs_undercut = bme_undercut_faces(self.bme, view_local)
        vcolor_data = self.bme.loops.layers.color['Undercut']
        bmesh_color_bmfaces(self.bme.faces[:], vcolor_data, Color((1,1,1)))
        bmesh_color_bmfaces(fs_undercut, vcolor_data, self.ucolor)
        self.bme.to_mesh(self.model.data)
        
    def tweak_anterior(self):
        loc = Matrix.Translation(self.ins_ob.matrix_world.to_translation())
        rot_base = self.ins_ob.matrix_world.to_3x3()
        r_model = self.model.matrix_world.to_quaternion()
        
        if self.jaw_mode == 'Max':
            axis = r_model * Vector((-1,0,0))
        else:
            axis = r_model * Vector((1,0,0))
        
        ang = self.tweak_angle * math.pi/180    
        rot = Matrix.Rotation(ang, 3, axis)
        self.ins_ob.matrix_world = loc * (rot * rot_base).to_4x4()
        self.update_undercut_shadow()
       
    def tweak_posterior(self):
        loc = Matrix.Translation(self.ins_ob.matrix_world.to_translation())
        rot_base = self.ins_ob.matrix_world.to_3x3()
        r_model = self.model.matrix_world.to_quaternion()
        if self.jaw_mode == 'Max':
            axis = r_model * Vector((1,0,0))
        else:
            axis = r_model * Vector((-1,0,0))
        ang = self.tweak_angle * math.pi/180    
        rot = Matrix.Rotation(ang, 3, axis)
        self.ins_ob.matrix_world = loc * (rot * rot_base).to_4x4()
        self.update_undercut_shadow()
        
    def tweak_left(self):
        loc = Matrix.Translation(self.ins_ob.matrix_world.to_translation())
        rot_base = self.ins_ob.matrix_world.to_3x3()
        r_model = self.model.matrix_world.to_quaternion()
        
        if self.jaw_mode == 'Max':
            axis = r_model * Vector((0,-1,0))
        else:
            axis = r_model * Vector((0,1,0))
        
        ang = self.tweak_angle * math.pi/180    
        rot = Matrix.Rotation(ang, 3, axis)
        self.ins_ob.matrix_world = loc * (rot * rot_base).to_4x4()
        self.update_undercut_shadow()
        
    def tweak_right(self):
        loc = Matrix.Translation(self.ins_ob.matrix_world.to_translation())
        rot_base = self.ins_ob.matrix_world.to_3x3()
        r_model = self.model.matrix_world.to_quaternion()
        
        if self.jaw_mode == 'Max':
            axis = r_model * Vector((0,1,0))
        else:
            axis = r_model * Vector((0,-1,0))
            
        ang = self.tweak_angle * math.pi/180    
        rot = Matrix.Rotation(ang, 3, axis)
        self.ins_ob.matrix_world = loc * (rot * rot_base).to_4x4()
        self.update_undercut_shadow()
        
    def capture_view(self):
        start = time.time()
        view = self.context.space_data.region_3d.view_rotation * Vector((0,0,1))
        mx = self.model.matrix_world
        i_mx = mx.inverted()
        view_local = i_mx.to_quaternion() * view
        loc = odcutils.get_bbox_center(self.model, world = True)
        mxT = Matrix.Translation(loc)
        mxR = self.context.space_data.region_3d.view_rotation.to_matrix().to_4x4()
        self.ins_ob.matrix_world = mxT * mxR
        
        self.update_undercut_shadow()
        self.previewed = True
    
    def can_commit(self):
        if not self.previewed:
            showErrorMessage('You must press the capture view button to finish!')
            return False
        else:
            return True
            
               
    @CookieCutter.FSM_State("main")
    def modal_main(self):
        #self.cursor_modal_set("CROSSHAIR")

        #if self.actions.pressed("commit"):   
        #    self.end_commit()
        #    return

        if self.actions.pressed("cancel"):
            self.done(cancel=True)
            return
        
        
class D3Splint_OT_max_insertion_axis(D3Splint_OT_cookie_insertion_axis):
    """ Pick Insertion Axis """
    operator_id    = "d3dual.pick_insertion_axis_max"
    bl_idname      = "d3dual.pick_insertion_axis_max"
    bl_label       = "Maxillary Insertion Axis"
    
    
    @classmethod
    def can_start(cls, context):
        """ Start only splint started and model indicated"""
        
        if len(context.scene.odc_splints) == 0:
            return False
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]    
        max_model = splint.get_maxilla()
        Model = bpy.data.objects.get(max_model)
        return Model != None

    def start_pre(self):
        self.jaw_mode = 'Max'
        max_model = self.splint.get_maxilla()
        Model = bpy.data.objects.get(max_model)
        add_volcolor_material_to_obj(Model, 'Undercut')
        Model.hide = False
        self.model = Model
        return 

class D3Splint_OT_mand_insertion_axis(D3Splint_OT_cookie_insertion_axis):
    """ Pick Insertion Axis """
    operator_id    = "d3dual.pick_insertion_axis_mand"
    bl_idname      = "d3dual.pick_insertion_axis_mand"
    bl_label       = "Mandibular Insertion Axis"
    
    
    @classmethod
    def can_start(cls, context):
        """ Start only splint started and model indicated"""
        
        if len(context.scene.odc_splints) == 0:
            return False
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]    
        max_model = splint.get_maxilla()
        Model = bpy.data.objects.get(max_model)
        return Model != None
    
    def start_pre(self):
        self.jaw_mode = 'Mand'
        mand_model = self.splint.get_mandible()
        Model = bpy.data.objects.get(mand_model)
        add_volcolor_material_to_obj(Model, 'Undercut')
        Model.hide = False
        self.model = Model
     
                     
def register():
    bpy.utils.register_class(D3Splint_OT_max_insertion_axis)
    bpy.utils.register_class(D3Splint_OT_mand_insertion_axis)

def unregister():
    bpy.utils.unregister_class(D3Splint_OT_max_insertion_axis)
    bpy.utils.unregister_class(D3Splint_OT_mand_insertion_axis)