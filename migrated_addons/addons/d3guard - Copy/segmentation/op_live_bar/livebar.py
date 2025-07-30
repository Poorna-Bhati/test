'''
Created on Oct 8, 2015

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement

from ..cookiecutter.cookiecutter import CookieCutter
from ..common import ui
from ..common.ui import Drawing

from .smargin_ui_init       import Polytrim_UI_Init
from .smargin_states        import Polytrim_States
from .smargin_ui_tools      import Polytrim_UI_Tools
from .smargin_ui_draw       import Polytrim_UI_Draw
from .smargin_datastructure import SplineNetwork

#from ..common.utils import get_settings


#ModalOperator
class D3Splint_live_rim(Polytrim_States, Polytrim_UI_Init, Polytrim_UI_Tools, Polytrim_UI_Draw, CookieCutter):
    ''' Cut Mesh Polytrim Modal Editor '''
    ''' Note: the functionality of this operator is split up over multiple base classes '''

    operator_id    = "d3splint.live_rim_generator"    # operator_id needs to be the same as bl_idname
                                            # important: bl_idname is mangled by Blender upon registry :(
    bl_idname      = "d3splint.live_rim_generator"
    bl_label       = "Generate Live Rim"
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
        
        splint = context.scene.odc_splints[0]
        
        if splint.model == '':
            #showErrorMessage('Need to Set Splint Model')
            return False
        if splint.model not in bpy.data.objects:
            #showErrorMessage('Splint Model has been removed')
            return False
        
        max = splint.get_maxilla()
        if max not in bpy.data.objects:
            return False
        mand = splint.get_mandible()
        if mand not in bpy.data.objects:
            return False

        return True

    def start(self):
        self.cursor_modal_set('CROSSHAIR')

        #self.drawing = Drawing.get_instance()
        self.drawing.set_region(bpy.context.region, bpy.context.space_data.region_3d, bpy.context.window)
        self.mode_pos        = (0, 0)
        self.cur_pos         = (0, 0)
        self.mode_radius     = 0
        self.action_center   = (0, 0)

        #prefs = get_settings()
        splint = self.context.scene.odc_splints[0]
        
        max = splint.get_maxilla()
        MaxModel = bpy.data.objects.get(max)
        mand = splint.get_mandible()
        MandModel = bpy.data.objects.get(mand)
        
        self.max_model = MaxModel
        self.mand_model = MandModel
        
        self.bar = None
        
        for ob in bpy.data.objects:
            ob.hide = True
        self.set_visualization()
        
        self.live_rim_preview = False
                
        bpy.context.scene.objects.active = MaxModel
        MaxModel.select = True
        
        bpy.ops.view3d.viewnumpad(type = 'FRONT')
        bpy.ops.view3d.view_selected()
        
        self.net_ui_context = self.NetworkUIContext(self.context, MaxModel, MandModel)

        self.spline_net = SplineNetwork(self.net_ui_context)
        
        self.sketcher = self.SketchManager(self.spline_net, self.net_ui_context)
        self.grabber = self.GrabManager(self.net_ui_context)
        self.brush_radius = 1.0
        
        #get from preferences or override
        #TODO maybe have a "preferences" within the segmentation operator
        #self.spline_preview_tess = prefs.spline_preview_tess
        #self.sketch_fit_epsilon = prefs.sketch_fit_epsilon
        #self.patch_boundary_fit_epsilon =  prefs.patch_boundary_fit_epsilon
        #self.spline_tessellation_epsilon = prefs.spline_tessellation_epsilon

        self.ui_setup()
        self.fsm_setup()
        self.window_state_overwrite(show_only_render=False, hide_manipulator=True)
        #self.load_from_bmesh()  #check for existing
    def end(self):
        ''' Called when tool is ending modal '''
        self.header_text_set()
        self.cursor_modal_restore()

    def update(self):
        pass
    
    
def register():
    bpy.utils.register_class(D3Splint_live_rim)
    
     
def unregister():
    bpy.utils.unregister_class(D3Splint_live_rim)