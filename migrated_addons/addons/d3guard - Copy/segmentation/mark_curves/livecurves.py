'''
Created on Oct 8, 2015

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement

from ..cookiecutter.cookiecutter import CookieCutter
from ..common import ui
from ..common.ui import Drawing

from segmentation.mark_curves.livecurves_ui_init       import Livecurves_UI_Init
from segmentation.mark_curves.livecurves_states        import Livecurves_States
from segmentation.mark_curves.livecurves_ui_tools      import Livecurves_UI_Tools
from segmentation.mark_curves.livecurves_ui_draw       import Livecurves_UI_Draw
from segmentation.mark_curves.livecurves_datastructure import SplineNetwork

#from ..common.utils import get_settings


class D3DUAL_OT_clear_curves(bpy.types.Operator):
    """C;ear the occlusal cirves for a fresh start"""
    bl_idname = "d3dual.clear_occlusal_curves"
    bl_label = "Clear Occlusal Curves"
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
        
        
        if "Occlusal Curve Max" in bpy.data.objects:
            max_ob = bpy.data.objects.get("Occlusal Curve Max")
            #clear old spline data, dont remove items form list while iterating over it
            max_spline_data = max_ob.data
            splines = [s for s in max_spline_data.splines]
            for s in splines:
                max_spline_data.splines.remove(s)
                
            bpy.data.objects.remove(max_ob)
            bpy.data.curves.remove(max_spline_data) 
     
        if "Occlusal Curve Mand" in bpy.data.objects:
            mand_ob = bpy.data.objects.get("Occlusal Curve Mand")
            mand_spline_data = mand_ob.data
            splines = [s for s in mand_ob.data.splines]
            for s in splines:
                mand_spline_data.splines.remove(s)
        

            bpy.data.objects.remove(mand_ob)
            bpy.data.curves.remove(mand_spline_data)  
            
        splint.arch_curves_complete = False
        return {'FINISHED'}

#ModalOperator
class D3DUAL_live_curves(Livecurves_States, Livecurves_UI_Init, Livecurves_UI_Tools, Livecurves_UI_Draw, CookieCutter):
    ''' Cut Mesh Polytrim Modal Editor '''
    ''' Note: the functionality of this operator is split up over multiple base classes '''

    operator_id    = "d3dual.mark_occlusal_curves"   # operator_id needs to be the same as bl_idname
                                            # important: bl_idname is mangled by Blender upon registry :(
    bl_idname      = "d3dual.mark_occlusal_curves"
    bl_label       = "Mark Ocussal Curves"
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
        
        if splint.max_model == '':
            #showErrorMessage('Need to Set Splint Model')
            return False
        
        if splint.mand_model == '':
            #showErrorMessage('Need to Set Splint Model')
            return False
        
        if splint.max_model not in bpy.data.objects or splint.mand_model not in bpy.data.objects:
            #showErrorMessage('Splint Model has been removed')
            return False
        
        max = splint.get_maxilla()
        if max not in bpy.data.objects:
            return False
        mand = splint.get_mandible()
        if mand not in bpy.data.objects:
            return False

        #if bpy.data.filepath == '':
        #    return False
        
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
        self.splint = splint
        
        
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
        
        bpy.ops.view3d.viewnumpad(type = 'BOTTOM')
        bpy.ops.view3d.view_selected()
        
        #DATASTRUCTURE INSTANCES
        self.net_ui_context = self.NetworkUIContext(self.context, MaxModel, MandModel)
        self.spline_net = SplineNetwork(self.net_ui_context)
        self.sketcher = self.SketchManager(self.spline_net, self.net_ui_context)
        self.grabber = self.GrabManager(self.net_ui_context)
        
        #SETTINGS
        self.brush_radius = 1.0
        self.rim_alpha = 0.4
        
        #SETTINGS TO PASS TO HQ RIM TOOL
        self.rim_ap_spread = 0.3
        self.rim_flare = 0
        self.width_offset = 0.1
        self.thickness_offset = 0.1
        self.anterior_projection = 0.0
        self.anterior_shift = 0.0
        self.ap_segment = 'FULL_RIM'
        
        
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
    bpy.utils.register_class(D3DUAL_live_curves)
    bpy.utils.register_class(D3DUAL_OT_clear_curves)
    
     
def unregister():
    bpy.utils.unregister_class(D3DUAL_live_curves)
    bpy.utils.unregister_class(D3DUAL_OT_clear_curves)