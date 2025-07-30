'''
Created on Oct 8, 2015

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import time

from ..cookiecutter.cookiecutter import CookieCutter
from ..common import ui
from ..common.ui import Drawing

from .smargin_ui_init       import Polytrim_UI_Init
from .smargin_states        import Polytrim_States
from .smargin_ui_tools      import Polytrim_UI_Tools
from .smargin_ui_draw       import Polytrim_UI_Draw
from .smargin_datastructure import InputNetwork, NetworkCutter, SplineNetwork
#from ..common.utils import get_settings


#ModalOperator
class D3Splint_segmentation_margin(Polytrim_States, Polytrim_UI_Init, Polytrim_UI_Tools, Polytrim_UI_Draw, CookieCutter):
    ''' Cut Mesh Polytrim Modal Editor '''
    ''' Note: the functionality of this operator is split up over multiple base classes '''

    operator_id    = "d3splint.polytrim_margin"    # operator_id needs to be the same as bl_idname
                                            # important: bl_idname is mangled by Blender upon registry :(
    bl_idname      = "d3splint.polytrim_margin"
    bl_label       = "Splint Margin Polytrim"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_options = {'REGISTER','UNDO'}

    default_keymap = {
        # key: a human-readable label
        # val: a str or a set of strings representing the user action
        'action': {'LEFTMOUSE'},
        'sketch': {'SHIFT+LEFTMOUSE'},
        'select': {'LEFTMOUSE'},
        'connect': {'LEFTMOUSE'},
        'add point': {'LEFTMOUSE'},
        'add point (disconnected)': {'CTRL+LEFTMOUSE'},
        'cancel': {'ESC', 'RIGHTMOUSE'},
        'grab': 'G',
        'delete': {'RIGHTMOUSE'},
        'paint delete':{'CTRL+RIGHTMOUSE'},
        'delete (disconnect)': {'CTRL+RIGHTMOUSE'},
        'preview cut': 'C',
        'up': 'UP_ARROW',
        'down': 'DOWN_ARROW'
        # ... more
    }

    @classmethod
    def can_start(cls, context):
        ''' Called when tool is invoked to determine if tool can start '''
        if context.mode != 'OBJECT':
            #showErrorMessage('Object Mode please')
            return False
        
        if len(context.scene.odc_splints) == 0:
            return False
        
        splint = context.scene.odc_splints[0]
        
        if splint.model == '':
            #showErrorMessage('Need to Set Splint Model')
            return False
        if splint.model not in bpy.data.objects:
            #showErrorMessage('Splint Model has been removed')
            return False
        if 'Refractory Model' not in bpy.data.objects:
            return False
        
        if bpy.data.filepath == '':
            #enfore saving the file, in case crashes etc.
            return False
        return True

    def start_pre(self):  #allows feeding in of information for customization
        splint = self.context.scene.odc_splints[0]  #TODO..self.splint?
        self.load_ob_name = 'Splint Margin'  #name of object to cache margin into
        self.omodel_name = 'Refractory Model'  #object to actually draw on
        self.model_name = splint.model   #model to show beneath refractory
        
        self.done_prop = splint.margin_marked
        self.out_model_name = 'Shell Patch'
        self.ops_record = 'TrimModel:'
        
    def start(self):
        self.start_pre()
        
        bpy.ops.ed.undo_push()
        self.cursor_modal_set('CROSSHAIR')

        Model = bpy.data.objects.get(self.model_name)
        OModel = bpy.data.objects.get(self.omodel_name)
        
        for ob in bpy.data.objects:
            ob.select = False
            ob.hide = True
        
        OModel.select = True
        OModel.hide = False
        Model.select = False
        Model.hide = False
        
        if self.model_name + '_silhouette' in bpy.data.objects:
            Survey = bpy.data.objects.get(Model.name + '_silhouette')
            Survey.hide = False
        
                #vis settings
        
        
            
        self.context.scene.objects.active = OModel
        #self.context.scene.objects.active = Model
        bpy.ops.view3d.viewnumpad(type = 'FRONT')
        bpy.ops.view3d.view_selected()
        
        
        self.context.scene.render.engine = 'BLENDER_RENDER'
        self.context.space_data.show_manipulator = False
        self.context.space_data.viewport_shade = 'SOLID'  #TODO until smarter drawing
        self.context.space_data.show_textured_solid = False #TODO until smarter patch drawing
        self.context.space_data.show_backface_culling = True
        OModel.show_transparent = True
        
        
        
        #self.drawing = Drawing.get_instance()
        self.drawing.set_region(bpy.context.region, bpy.context.space_data.region_3d, bpy.context.window)
        self.mode_pos        = (0, 0)
        self.cur_pos         = (0, 0)
        self.mode_radius     = 0
        self.action_center   = (0, 0)

        
        
        self.net_ui_context = self.NetworkUIContext(self.context, geometry_mode = "NON_DESTRUCTIVE")

        self.hint_bad = False   #draw obnoxious things over the bad segments
        self.input_net = InputNetwork(self.net_ui_context)
        self.spline_net = SplineNetwork(self.net_ui_context)
        self.network_cutter = NetworkCutter(self.input_net, self.net_ui_context)
        self.sketcher = self.SketchManager(self.input_net, self.spline_net, self.net_ui_context, self.network_cutter)
        self.grabber = self.GrabManager(self.input_net, self.net_ui_context, self.network_cutter)
        self.brush = None
        self.brush_radius = 1.5
        
        self.check_depth = 0
        self.last_bad_check = time.time()
        
        self.seed_iterations = 10000
        #get from preferences or override
        #TODO maybe have a "preferences" within the segmentation operator
        #self.spline_preview_tess = prefs.spline_preview_tess
        #self.sketch_fit_epsilon = prefs.sketch_fit_epsilon
        #self.patch_boundary_fit_epsilon =  prefs.patch_boundary_fit_epsilon
        #self.spline_tessellation_epsilon = prefs.spline_tessellation_epsilon

        self.ui_setup()
        self.fsm_setup()
        self.window_state_overwrite(show_only_render=False, hide_manipulator=True)
        self.load_from_bmesh()  #check for existing
    def end(self):
        ''' Called when tool is ending modal '''
        self.header_text_set()
        self.cursor_modal_restore()

    def update(self):
        pass
    
    
def register():
    bpy.utils.register_class(D3Splint_segmentation_margin)
    
     
def unregister():
    bpy.utils.unregister_class(D3Splint_segmentation_margin)