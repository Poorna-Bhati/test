'''
Created on Oct 11, 2015

@author: Patrick
'''

import time
import random

from bpy_extras import view3d_utils

from ..cookiecutter.cookiecutter import CookieCutter
from ..common import ui
from ..common.blender import show_error_message
from ..common.ui import Drawing

from segmentation.mark_curves.livecurves_datastructure import InputPoint, SplineSegment, CurveNode
from segmentation.common.ui import UI_Collapsible


class Livecurves_UI_Init():
    def ui_setup(self):
        self.instructions = {
            "basic": "A Maxillary and Mandibuar curve will help establish the occlusal plane, and provide a proposal for wax-rim placement",
            "objective": "Create a smooth arch form on the upper and lower jaw by left clicking sequentially along the model.  Usually the upper buccal cusps and the lower central fossa will nicely bound the lower cusp tips.  These curves will define the upper/facial and lower/lingual borders of the wax rim",
            "add": "Left-click on the model to add a new point",
            "add (extend)": "Left-click to add new a point connected to the selected point. The green line will visualize the new segments created",
            "add (insert)": "Left-click on a segment to insert a new a point. The green line will visualize the new segments created",
            "close loop": "Left-click on the outer hover ring of existing point to close a boundary loop",
            "select": "Left-click on a point to select it",
            "sketch": "Hold Shift + left-click and drag to sketch in a series of points",
            "sketch extend": "Hover near an existing point, Shift + Left-click and drag to sketch in a series of points",
            "delete": "Right-click on a point to remove it",
            "delete (disconnect)": "Ctrl + right-click will remove a point and its connected segments",
            "tweak": "left click, hold, and drag a point to move it",
            "tweak confirm": "Release to place point at cursor's location",
            "paint": "Left-click to paint",
            "paint extend": "Left-click inside and then paint outward from an existing patch to extend it",
            "paint greedy": "Painting from one patch into another will remove area from 2nd patch and add it to 1st",
            "paint mergey": "Painting from one patch into another will merge the two patches",
            "paint remove": "Right-click and drag to delete area from patch",
            "seed add": "Left-click within a boundary to indicate it as patch segment",
            "segmentation" : "Left-click on a patch to select it, then use the segmentation buttons to apply changes"
        }

        def mode_getter():
            return self._state
        def mode_setter(m):
            self.fsm_change(m)
        def mode_change():
            nonlocal precut_container#, segmentation_container, paint_radius
            m = self._state
            precut_container.visible = (m in {'spline', 'seed', 'region'})
            #paint_radius.visible = (m in {'region'})
            #no_options.visible = not (m in {'region'})
            #segmentation_container.visible = (m in {'segmentation'})
            #segmentation_tools.visible = False
        self.fsm_change_callback(mode_change)

        def radius_getter():
            return self.brush_radius
        def radius_setter(v):
            self.brush_radius = max(0.1, int(v*10)/10)
            if self.brush:
                self.brush.radius = self.brush_radius
                
        def rim_alpha_getter():
            ra = min(self.rim_alpha, 1.0)
            ra = max(ra, 0.01)  
            return ra
        
        def rim_alpha_setter(a):
            ra = min(a, 1.0)
            ra = max(ra, 0.01)
            self.rim_alpha = round(ra,2)
            self.set_rim_alpha()
        
        def rim_flare_getter():  
            return int(self.rim_flare)
        
        def rim_flare_setter(a):
            ra = min(a, 60)
            ra = max(ra, -60)  
            self.rim_flare = int(ra)
            #self.preview_rim()
             
        def rim_ap_getter():
            ra = min(self.rim_ap_spread, .95)
            ra = max(ra, .15)  
            return round(ra, 2)
        
        def rim_ap_setter(a):
            ra = min(a, .95)
            ra = max(ra, .15)  
            self.rim_ap_spread = round(ra, 2) 
            #self.preview_rim_HQ()
            
        def rim_anterior_proj_getter():
            ra = min(self.anterior_projection, 2.0)
            ra = max(ra, 0.0)  
            return round(ra, 2)
        
        def rim_anterior_proj_setter(a):
            ra = min(a, 2.0)
            ra = max(ra, 0.0)  
            self.anterior_projection = round(ra, 2)    
            #self.preview_rim_HQ()
        
        def rim_anterior_shift_getter():
            ra = min(self.anterior_shift, 5.0)
            ra = max(ra, -5.0)  
            return round(ra, 2)
        
        def rim_anterior_shift_setter(a):
            ra = min(a, 5.0)
            ra = max(ra, -5.0)  
            self.anterior_shift = round(ra, 2)    
            #self.preview_rim_HQ()
            
        def get_ap_segment():
            
            if self.ap_segment == 'FULL_RIM':
                return 'FULL'
            elif self.ap_segment == 'ANTERIOR_ONLY':
                return 'ANT'
            else:
                return 'POST'
            
        def set_ap_segment(a):
            if a == 'ANT':
                self.ap_segment = 'ANTERIOR_ONLY'
            elif a == 'POST':
                self.ap_segment = 'POSTERIOR_ONLY'
            else:
                self.ap_segment = 'FULL_RIM'
                
            self.preview_rim_HQ()
        # def compute_cut():
        #     # should this be a state instead?
        #     self.network_cutter.knife_geometry4()
        #     self.network_cutter.find_perimeter_edges()
        #     for patch in self.network_cutter.face_patches:
        #         patch.grow_seed(self.input_net.bme, self.network_cutter.boundary_edges)
        #         patch.color_patch()
        #     self.net_ui_context.bme.to_mesh(self.net_ui_context.ob.data)
        #     self.fsm_change('segmentation')

        win_tools = self.wm.create_window('Mark Curves Info', {'pos':7, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})

        precut_container = win_tools.add(ui.UI_Container())
        precut_container.rounded_background = True
        
        precut_tools = precut_container.add(ui.UI_Frame('Mark Curves Mode', fontsize=16))
        #precut_mode = precut_tools.add(ui.UI_Options(mode_getter, mode_setter))
        #precut_mode.add_option('Boundary Edit', value='spline', icon=ui.UI_Image('polyline.png', width=32, height=32))
        #precut_mode.add_option('Boundary > Region', value='seed', icon=ui.UI_Image('seed.png', width=32, height=32))
        #precut_mode.add_option('Region Paint', value='region', icon=ui.UI_Image('paint.png', width=32, height=32))
        precut_tools.add(ui.UI_Button('Mark Maxillary', self.set_max_mode, margin = 5))
        precut_tools.add(ui.UI_Button('Mark Mandibular', self.set_mand_mode, margin = 5))
        precut_tools.add(ui.UI_Button('Curves Only', self.set_2d_mode, margin = 5))
        #precut_tools.add(ui.UI_Button('Load Network', self.load_from_bmesh, margin = 5))
        
        #precut_tools.add(ui.UI_Button('Nudge Bad Segments', self.nudge_bad_segments, margin = 5))
        
                        
        container = precut_container.add(ui.UI_Frame('Tools', fontsize=16))
        #container.add(ui.UI_Button('Save Curves', self.save_splinenet_to_curves, margin=5))
        #container.add(ui.UI_Button('Preview Rim', self.toggle_preview_rim, margin=5))
        #container.add(ui.UI_Button('Show Shell', self.toggle_shell_viz, margin=5))
        #container.add(ui.UI_Button('Edit Rim', self.edit_rim_enter, margin=5))
        #container.add(ui.UI_Button('Cache Rim', self.cache_to_splines, margin=5))
        container.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=5))
        container.add(ui.UI_Button('Commit', self.done, margin=5))


        #segmentation_container = win_tools.add(ui.UI_Container())
        #segmentation_tools = segmentation_container.add(ui.UI_Frame('Segmentation Tools', fontsize=16))
        #segmentation_mode = segmentation_tools.add(ui.UI_Options(mode_getter, mode_setter))
        #segmentation_mode.add_option('Segmentation', value='segmentation', margin = 5)
        #seg_buttons = segmentation_tools.add(ui.UI_EqualContainer(margin=0,vertical=False))
        #segmentation_tools.add(ui.UI_Button('Delete', self.delete_active_patch, icon=ui.UI_Image('delete_patch32.png', width=32, height=32), margin=5))
        #segmentation_tools.add(ui.UI_Button('Separate', self.separate_active_patch, icon=ui.UI_Image('separate32.png', width=32, height=32),margin=5))
        #segmentation_tools.add(ui.UI_Button('Duplicate', self.duplicate_active_patch, icon=ui.UI_Image('duplicate32.png', width=32, height=32), margin=5))
        #seg_buttons.add(ui.UI_Button('Patch to VGroup', self.active_patch_to_vgroup, margin=5))

        #container = segmentation_container.add(ui.UI_Frame('Finalize', fontsize=16))
        #container.add(ui.UI_Button('Commit', self.done, margin=5))
        #container.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=5))


        info = self.wm.create_window('Live Curves Help', {'pos':9, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})
        #info.add(ui.UI_Label('Instructions', fontsize=16, align=0, margin=4))
        collapse = info.add(UI_Collapsible('Instructions          ',collapsed = False))
        self.inst_paragraphs = [collapse.add(ui.UI_Markdown('', min_size=(200,10))) for i in range(7)]
        for i in self.inst_paragraphs: i.visible = True
        #self.ui_instructions = info.add(ui.UI_Markdown('test', min_size=(200,200)))
        options = info.add(ui.UI_Frame('Rim Options', fontsize=16))
        rim_alpha = options.add(ui.UI_Number("Opacity", rim_alpha_getter, rim_alpha_setter, update_multiplier= .005))
        rim_flare = options.add(ui.UI_Number("Rim Flare", rim_flare_getter, rim_flare_setter, update_multiplier= 0.2))#, update_multiplier= .01))
        rim_ap_spread = options.add(ui.UI_Number("Rim AP Spread", rim_ap_getter, rim_ap_setter, update_multiplier = .0005))#, update_multiplier= .01))
        rim_aprojection = options.add(ui.UI_Number("Rim Extra Anterior", rim_anterior_proj_getter, rim_anterior_proj_setter, update_multiplier=.01))
        anterior_shift = options.add(ui.UI_Number("Anterior Shift", rim_anterior_shift_getter, rim_anterior_shift_setter, update_multiplier=.01))
        
        ap_amt = options.add(ui.UI_Options(get_ap_segment, set_ap_segment, label="", vertical=False))
        ap_amt.add_option("ANT")
        ap_amt.add_option("POST")
        ap_amt.add_option("FULL")
        
        hq_rim_button = options.add(ui.UI_Button('Calculate  Rim', self.preview_rim_HQ, margin=5))
        curved_plane_button= options.add(ui.UI_Button('Curved  Plane', self.preview_curved_plane, margin=5))
        flat_plane_button= options.add(ui.UI_Button('Flat  Plane', lambda:self.preview_curved_plane(mode = 'FLAT'), margin=5))
        
        toggle_shell_vis = options.add(ui.UI_Button('Hide/Show Shell', self.toggle_shell_vis, margin=5))
        toggle_max_vis = options.add(ui.UI_Button('Hide/Show Max', self.toggle_max_vis, margin=5))
        toggle_mand_vis = options.add(ui.UI_Button('Hide/Show Mand', self.toggle_mand_vis, margin=5))
        
        quick_fuse_rim_button = options.add(ui.UI_Button('Fuse Rim', self.fuse_rim_activate, margin=5))
        #vol_fuse_rim_button = options.add(ui.UI_Button('Fuse Rim', self.volume_rim_activate, margin=5))
        unfuse_rim_button = options.add(ui.UI_Button('Un-Fuse Rim', self.fuse_rim_deactivate, margin=5))
        #no_options = precut_options.add(ui.UI_Label('(none)', color=(1.00, 1.00, 1.00, 0.25)))
        
        
        self.set_ui_text_no_points()


    # XXX: Fine for now, but will likely be irrelevant in future
    def ui_text_update(self):
        '''
        updates the text in the info box
        '''
        self.set_ui_text_no_points()
        #if self._state == 'spline':
            #if self.input_net.is_empty:
            
            #elif self.input_net.num_points == 1:
            #    self.set_ui_text_1_point()
            #elif self.input_net.num_points > 1:
            #    self.set_ui_text_multiple_points()
            #if self.grabber and self.grabber.in_use:
            #    self.set_ui_text_grab_mode()

        #elif self._state == 'region':
        #    self.set_ui_text_paint()
        #elif self._state == 'seed':
        #    self.set_ui_text_seed_mode()

        #elif self._state == 'segmentation':
        #    self.set_ui_text_segmetation_mode()

        #else:
        #    self.reset_ui_text()

    # XXX: Fine for now, but will likely be irrelevant in future
    def set_ui_text_no_points(self):
        ''' sets the viewports text when no points are out '''
        self.reset_ui_text()
        self.inst_paragraphs[0].set_markdown(self.instructions['basic'])
        self.inst_paragraphs[1].set_markdown('Objective: ' + self.instructions['objective'])
        self.inst_paragraphs[2].set_markdown('- ' + self.instructions['add'])
        self.inst_paragraphs[3].set_markdown('- ' + self.instructions['tweak'])
        self.inst_paragraphs[4].set_markdown('- ' + self.instructions['add (insert)'])
        self.inst_paragraphs[5].set_markdown('- ' + self.instructions['delete'])

    def set_ui_text_1_point(self):
        ''' sets the viewports text when 1 point has been placed'''
        self.reset_ui_text()
        self.inst_paragraphs[0].set_markdown('A) ' + self.instructions['add (extend)'])
        self.inst_paragraphs[1].set_markdown('B) ' + self.instructions['delete'])
        self.inst_paragraphs[2].set_markdown('C) ' + self.instructions['sketch extend'])
        self.inst_paragraphs[3].set_markdown('C) ' + self.instructions['select'])
        self.inst_paragraphs[4].set_markdown('D) ' + self.instructions['tweak'])
        #self.inst_paragraphs[5].set_markdown('E) ' + self.instructions['add (disconnect)'])
        self.inst_paragraphs[6].set_markdown('F) ' + self.instructions['delete (disconnect)'])

        #self.inst_paragraphs[4].set_markdown('E) ' + self.instructions['add (disconnect)'])


    def set_ui_text_multiple_points(self):
        ''' sets the viewports text when there are multiple points '''
        self.reset_ui_text()
        self.inst_paragraphs[0].set_markdown('A) ' + self.instructions['add (extend)'])
        self.inst_paragraphs[1].set_markdown('B) ' + self.instructions['add (insert)'])
        self.inst_paragraphs[2].set_markdown('C) ' + self.instructions['delete'])
        self.inst_paragraphs[3].set_markdown('D) ' + self.instructions['delete (disconnect)'])
        self.inst_paragraphs[4].set_markdown('E) ' + self.instructions['sketch'])
        self.inst_paragraphs[5].set_markdown('F) ' + self.instructions['tweak'])
        self.inst_paragraphs[6].set_markdown('G) ' + self.instructions['close loop'])

    def set_ui_text_grab_mode(self):
        ''' sets the viewports text during general creation of line '''
        self.reset_ui_text()
        self.inst_paragraphs[0].set_markdown('A) ' + self.instructions['tweak confirm'])

    def set_ui_text_seed_mode(self):
        ''' sets the viewport text during seed selection'''
        self.reset_ui_text()
        self.inst_paragraphs[0].set_markdown('A) ' + self.instructions['seed add'])

    def set_ui_text_segmetation_mode(self):
        ''' sets the viewport text during seed selection'''
        self.reset_ui_text()
        self.inst_paragraphs[0].set_markdown('A) ' + self.instructions['segmentation'])

    def set_ui_text_paint(self):
        self.reset_ui_text()
        self.inst_paragraphs[0].set_markdown('A) ' + self.instructions['paint'])
        self.inst_paragraphs[1].set_markdown('B) ' + self.instructions['paint extend'])
        self.inst_paragraphs[2].set_markdown('C) ' + self.instructions['paint remove'])
        self.inst_paragraphs[3].set_markdown('D) ' + self.instructions['paint mergey'])

    def reset_ui_text(self):
        for inst_p in self.inst_paragraphs:
            inst_p.set_markdown('')