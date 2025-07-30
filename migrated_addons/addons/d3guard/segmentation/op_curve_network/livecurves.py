'''
Created on Oct 8, 2015

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement

from ..cookiecutter.cookiecutter import CookieCutter
from ..common import ui
from ..common.ui import Drawing

from segmentation.op_curve_network.livecurves_ui_init       import Livecurves_UI_Init
from segmentation.op_curve_network.livecurves_states        import Livecurves_States
from segmentation.op_curve_network.livecurves_ui_tools      import Livecurves_UI_Tools
from segmentation.op_curve_network.livecurves_ui_draw       import Livecurves_UI_Draw
from segmentation.op_curve_network.livecurves_datastructure import SplineNetwork

#from ..common.utils import get_settings


#ModalOperator
class D3Splint_generic_curves(Livecurves_States, Livecurves_UI_Init, Livecurves_UI_Tools, Livecurves_UI_Draw, CookieCutter):
    ''' Simple 3D Curve Network '''
    ''' Note: the functionality of this operator is split up over multiple base classes '''

    operator_id    = "d3splint.mark_curves_generic"    # operator_id needs to be the same as bl_idname
                                            # important: bl_idname is mangled by Blender upon registry :(
    bl_idname      = "d3splint.mark_curves_generic"
    bl_label       = "Mark Generic Curves"
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
        
        
        return True

    def start_pre(self, context):
        #override to customize this tool
        return
    
    def start(self):
        self.cursor_modal_set('CROSSHAIR')

        #self.drawing = Drawing.get_instance()
        self.drawing.set_region(bpy.context.region, bpy.context.space_data.region_3d, bpy.context.window)
        self.mode_pos        = (0, 0)
        self.cur_pos         = (0, 0)
        self.mode_radius     = 0
        self.action_center   = (0, 0)

        self.obs = [ob for ob in bpy.data.objects if ob.hide == False and ob.select == True]
        
        self.set_visualization()  #TODO, what is this
        
        self.target = 'SURFACE'
        
        #DATASTRUCTURE INSTANCES
        self.net_ui_context = self.NetworkUIContext(self.context, obs = self.obs)
        self.spline_net = SplineNetwork(self.net_ui_context)
        self.sketcher = self.SketchManager(self.spline_net, self.net_ui_context)
        self.grabber = self.GrabManager(self.net_ui_context)
        
        
        self.snap_tessellation = True
        
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
    
    
def register():
    bpy.utils.register_class(D3Splint_generic_curves)
    
     
def unregister():
    bpy.utils.unregister_class(D3Splint_generic_curves)