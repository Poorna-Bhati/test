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

from .wax_curve_datastructure import InputPoint, SplineSegment, CurveNode



class WaxCurve_UI_Init():
    def ui_setup(self):
        self.instructions = {
            "basic": "Draw curves on the object and virtual wax will follow",
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

        #Options and Settings        
        def shape_getter():
            return self.blob_type
        
        
        def shape_setter(m):
            if m in {'BALL', 'CUBE'}:
                self.blob_type = m
            else:
                self.blob_type = 'BALL'

            self.preview_rim() #TODO "update_wax"

        def cube_align_getter():
            return self.cube_flat_side
        
        
        def cube_align_setter(m):
            if m in {'Z', 'NORMAL'}:
                self.cube_flat_side = m
            else:
                self.cube_flat_side = 'Z'

            self.preview_rim() #TODO "update_wax"
        
        def radius_getter():
            return self.brush_radius
        def radius_setter(v):
            self.brush_radius = max(0.1, int(v*10)/10)
            if self.brush:
                self.brush.radius = self.brush_radius
        
        def wax_radius_getter():
            return self.blob_size
            
        def wax_radius_setter(v):
            self.blob_size = max(0.25, v)
            self.blob_size = min(self.blob_size, 5.0)
            self.preview_rim()
            
        def wax_alpha_getter():
            ra = min(self.wax_alpha, 1.0)
            ra = max(ra, 0.01)  
            return ra
        
        def wax_alpha_setter(a):
            ra = min(a, 1.0)
            ra = max(ra, 0.01)
            self.wax_alpha = round(ra,2)
            self.set_wax_alpha()
            
            
        def blob_spacing_getter():
            ra = min(self.blob_spacing, 5.0)
            ra = max(ra, 0.05)  
            return ra
        
        def blob_spacing_setter(a):
            ra = min(a, 5.0)
            ra = max(ra, 0.05)
            self.blob_spacing = round(ra,2)
            self.preview_rim()
            
        
        def blob_z_getter():
            return self.blob_z
            
        def blob_z_setter(v):
            bz = max(0.25, v)
            bz = min(bz, 5.0)
            self.blob_z = round(bz,2)
            self.preview_rim()
        
        def blob_y_getter():
            return self.blob_y
            
        def blob_y_setter(v):
            by = max(0.25, v)
            by = min(by, 5.0)
            self.blob_y = round(by,2)
            self.preview_rim()
        
        def res_getter():
            return self.meta_preset
        def res_setter(v):
            if v in {'HIGH','MEDIUM','LOW',"FINAL"}:
                self.meta_preset = v
            
            else:
                self.meta_preset = 'MEDIUM'    
            
            self.preview_rim()
        
        
        def meta_res_getter(): 
            return self.final_meta_resolution
            
        def meta_res_setter(v):
            by = max(0.05, v)
            by = min(by, 1.5)
            self.final_meta_resolution = round(by,2)
            self.preview_rim()
            
                  
        # def compute_cut():
        #     # should this be a state instead?
        #     self.network_cutter.knife_geometry4()
        #     self.network_cutter.find_perimeter_edges()
        #     for patch in self.network_cutter.face_patches:
        #         patch.grow_seed(self.input_net.bme, self.network_cutter.boundary_edges)
        #         patch.color_patch()
        #     self.net_ui_context.bme.to_mesh(self.net_ui_context.ob.data)
        #     self.fsm_change('segmentation')

        win_tools = self.wm.create_window('Wax Curves Info', {'pos':7, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})

        precut_container = win_tools.add(ui.UI_Container())
        precut_container.rounded_background = True
        
        precut_tools = precut_container.add(ui.UI_Frame('Mark Curves Mode', fontsize=16))
        #precut_mode = precut_tools.add(ui.UI_Options(mode_getter, mode_setter))
        #precut_mode.add_option('Boundary Edit', value='spline', icon=ui.UI_Image('polyline.png', width=32, height=32))
        #precut_mode.add_option('Boundary > Region', value='seed', icon=ui.UI_Image('seed.png', width=32, height=32))
        #precut_mode.add_option('Region Paint', value='region', icon=ui.UI_Image('paint.png', width=32, height=32))
        precut_tools.add(ui.UI_Button('Snap to Model', self.set_model_mode, margin = 5))
        precut_tools.add(ui.UI_Button('Free Curves', self.set_2d_mode, margin = 5))
        #precut_tools.add(ui.UI_Button('Load Network', self.load_from_bmesh, margin = 5))
        
        precut_mode = precut_tools.add(ui.UI_Options(shape_getter, shape_setter))
        precut_mode.add_option('Sphere', value='BALL')
        precut_mode.add_option('Cubes', value='CUBE') #icon=ui.UI_Image('seed.png', width=32, height=32))
        
        
        meta_res = precut_tools.add(ui.UI_Options(res_getter, res_setter))
        meta_res.add_option('LOW', value='LOW')
        meta_res.add_option('MEDIUM', value='MEDIUM')
        meta_res.add_option('HIGH', value='HIGH')
        meta_res.add_option('FINAL', value='FINAL')
        
        
        cube_mode = precut_tools.add(ui.UI_Options(cube_align_getter, cube_align_setter))
        cube_mode.add_option('Z Up', value='Z')
        cube_mode.add_option('Surface', value='NORMAL') #icon=ui.UI_Image('seed.png', width=32, height=32))
        #precut_tools.add(ui.UI_Button('Nudge Bad Segments', self.nudge_bad_segments, margin = 5))
        
                        
        container = precut_container.add(ui.UI_Frame('Tools', fontsize=16))
        #container.add(ui.UI_Button('Save Curves', self.save_splinenet_to_curves, margin=5))
        #container.add(ui.UI_Button('Preview Rim', self.toggle_preview_rim, margin=5))
        #container.add(ui.UI_Button('Edit Rim', self.edit_rim_enter, margin=5))
        #container.add(ui.UI_Button('Cache Rim', self.cache_to_splines, margin=5))
        container.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=5))
        container.add(ui.UI_Button('Finish', self.done, margin=5))


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


        info = self.wm.create_window('Wax Curves Help', {'pos':9, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})
        #info.add(ui.UI_Label('Instructions', fontsize=16, align=0, margin=4))
        collapse = info.add(ui.UI_Collapsible('Instructions          ',collapsed = False))
        self.inst_paragraphs = [collapse.add(ui.UI_Markdown('', min_size=(200,10))) for i in range(7)]
        for i in self.inst_paragraphs: i.visible = True
        #self.ui_instructions = info.add(ui.UI_Markdown('test', min_size=(200,200)))
        options = info.add(ui.UI_Frame('Options', fontsize=16))
        rim_alpha = options.add(ui.UI_Number("Wax Opacity", wax_alpha_getter, wax_alpha_setter, update_multiplier= .005))
        drop_radius = options.add(ui.UI_Number("Droplet Radius", wax_radius_getter, wax_radius_setter, update_multiplier= .05))
        drop_spacing = options.add(ui.UI_Number("Droplet Spacing", blob_spacing_getter, blob_spacing_setter, update_multiplier= .1))
        
        drop_z = options.add(ui.UI_Number("Cube Z", blob_z_getter, blob_z_setter, update_multiplier= .05))
        drop_y = options.add(ui.UI_Number("Cube Y", blob_y_getter, blob_y_setter, update_multiplier= .05))
        #no_options = precut_options.add(ui.UI_Label('(none)', color=(1.00, 1.00, 1.00, 0.25)))
        
        meta_res = options.add(ui.UI_Number("Wax Resolution", meta_res_getter, meta_res_setter, update_multiplier= .1))
        
        
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