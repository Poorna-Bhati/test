'''
Created on Oct 8, 2015

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement

from ..cookiecutter.cookiecutter import CookieCutter
from ..common import ui
from ..common.ui import Drawing

from .wax_curve_ui_init       import WaxCurve_UI_Init
from .wax_curve_states        import WaxCurve_States
from .wax_curve_ui_tools      import WaxCurve_UI_Tools
from .wax_curve_ui_draw       import WaxCurve_UI_Draw
from .wax_curve_datastructure import SplineNetwork

#from ..common.utils import get_settings


#ModalOperator
class D3Splint_live_wax_curves(WaxCurve_States, WaxCurve_UI_Init, WaxCurve_UI_Tools, WaxCurve_UI_Draw, CookieCutter):
    ''' Cut Mesh Polytrim Modal Editor '''
    ''' Note: the functionality of this operator is split up over multiple base classes '''

    operator_id    = "d3splint.wax_live_curves"    # operator_id needs to be the same as bl_idname
                                            # important: bl_idname is mangled by Blender upon registry :(
    bl_idname      = "d3splint.wax_live_curves" 
    bl_label       = "Draw Wax Curves"
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
        #self.cursor_modal_set('CROSSHAIR')

        #self.drawing = Drawing.get_instance()
        self.drawing.set_region(bpy.context.region, bpy.context.space_data.region_3d, bpy.context.window)
        self.mode_pos        = (0, 0)
        self.cur_pos         = (0, 0)
        self.mode_radius     = 0
        self.action_center   = (0, 0)

    
        self.model = self.context.object
        self.wax_obj, self.meta_obj = self.make_wax_base(self.context)
        
        self.set_visualization()
        self.live_rim_preview = False
    
        #DATASTRUCTURE INSTANCES
        self.net_ui_context = self.NetworkUIContext(self.context, self.model)
        self.spline_net = SplineNetwork(self.net_ui_context)
        self.sketcher = self.SketchManager(self.spline_net, self.net_ui_context)
        self.grabber = self.GrabManager(self.net_ui_context)
        
        
        
        #SETTINGS
        self.brush_radius = 1.0
        self.wax_alpha = 0.85
        self.snap_all = False
        
        self.operation = 'JOIN'  #JOIN, SUBTRACT, FREE
        self.blob_type = 'BALL'  #CUBE
        
        #ball settings
        self.blob_size = 2.0  #controls the radius of balls
        
        #cube settings
        self.cube_flat_side = 'NORMAL'  #or NORMAL
        self.blob_x = .5
        self.blob_z = .5
        self.blob_y = .5
        self.blob_radius = .75  #controls the corner radius of cubes
        
        self.blob_spacing = 0.25
        self.final_meta_resolution = 0.4
        
        
        self.meta_preset = 'MEDIUM'  #HIGH 0.1, MEDIUM 0.4, LOW 0.8, 'FINAL'
        
        #self.load_splinenet_from_curves()
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
    bpy.utils.register_class(D3Splint_live_wax_curves)
    
     
def unregister():
    bpy.utils.unregister_class(D3Splint_live_wax_curves)