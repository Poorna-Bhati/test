'''
Created on Oct 8, 2015

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement

from ..cookiecutter.cookiecutter import CookieCutter
from ..common import ui
from ..common.ui import Drawing

from .livecurves_ui_init       import Livecurves_UI_Init
from .livecurves_states        import Livecurves_States
from .livecurves_ui_tools      import Livecurves_UI_Tools
from .livecurves_ui_draw       import Livecurves_UI_Draw
from .livecurves_datastructure import SplineNetwork

#from ..common.utils import get_settings


#ModalOperator
class D3MODEL_removable_dies(Livecurves_States, Livecurves_UI_Init, Livecurves_UI_Tools, Livecurves_UI_Draw, CookieCutter):
    ''' Removable Deis'''
    ''' Note: the functionality of this operator is split up over multiple base classes '''

    operator_id    = "d3model.mark_die_margins"    # operator_id needs to be the same as bl_idname
                                            # important: bl_idname is mangled by Blender upon registry :(
    bl_idname      = "d3model.mark_die_margins"
    bl_label       = "Mark Die Margins"
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
        if context.object == None:
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

        self.model = bpy.context.object
        
        
        self.expected_dies = [ob for ob in self.model.children if "Die" in ob.name]
        
        
        #DATASTRUCTURE INSTANCES
        self.net_ui_context = self.NetworkUIContext(self.context, self.model)
        self.spline_net = SplineNetwork(self.net_ui_context)
        self.sketcher = self.SketchManager(self.spline_net, self.net_ui_context)
        self.grabber = self.GrabManager(self.net_ui_context)
        
        #SETTINGS
        #self.brush_radius = 1.0
        #self.rim_alpha = 0.4
        
        #SETTINGS TO PASS TO HQ RIM TOOL
        #self.rim_ap_spread = 0.3
        #self.rim_flare = 0
        #self.width_offset = 0.1
        #self.thickness_offset = 0.1
        #self.anterior_projection = 0.0
        #self.anterior_shift = 0.0
        #self.ap_segment = 'FULL_RIM'
        
        
        self.load_splinenet_from_curves()
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
    