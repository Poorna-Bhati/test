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

from .holemargin_datastructure import InputPoint, SplineSegment, CurveNode


class Polytrim_UI_Init():
    def ui_setup(self):
        self.instructions = {
            "add": "Left-click on the model to add a new point in the splint margin outline",
            "add (extend)": "Left-click to add new a point connected to the selected point. The green line will visualize the new segments created",
            "add (insert)": "Left-click on a segment to insert a new a point. The green line will visualize the new segments created",
            "close loop": "Left-click on the outer hover ring of existing point to close a boundary loop",
            "select": "Left-click on a point to select it",
            "sketch": "Hold Shift + left-click and drag to sketch a line",
            "sketch extend": "Hover near an existing point, Shift + Left-click and drag to sketch extend the outline",
            "delete": "Right-click on a point to remove it",
            "delete (disconnect)": "Ctrl + right-click will remove a point and its connected segments",
            "tweak": "left click and drag a point to move it",
            "tweak confirm": "Release to place point at cursor's location",
            "paint": "Left-click to paint",
            "paint extend": "Left-click inside and then paint outward from an existing patch to extend it",
            "paint greedy": "Painting from one patch into another will remove area from 2nd patch and add it to 1st",
            "paint mergey": "Painting from one patch into another will merge the two patches",
            "paint remove": "Right-click and drag to delete area from patch",
            "seed add": "Left-click within a boundary to indicate it as the interior of the splint",
            "seed result": "The region inside the boundary will be assigned  random color and fill the entire boundary. If the colored area overflows the boundary, go back to previous step and alter your margin or cancel and check for tunnels",
            "segmentation" : "Ensure the cut is clean all the way around, if not, go back and tweak margin slightly"
        }


        def end_it():
            self.done()
            return {'FINISH'}
        
        def mode_backer():
            if self._state == 'spline':
                return
            elif self._state == 'seed':
                self.seed_to_spline()  #manually clean out some things
                self.fsm_change('spline')     
            else:
                return
            
            #elif self._state == 'segmentation':
            #    self.segmentation_to_spline()
            #    self.fsm_change('spline') 
            #    self.load_from_bmesh()  
            #else:
            #    return
            
            
        def mode_stepper():
            if self._state == 'spline':
                self.fsm_change('seed')
                self.context.space_data.show_textured_solid = True
                self.net_ui_context.ob.show_transparent = False
            elif self._state == 'seed':
                self.done()
            else:
                pass    
                #self.fsm_change('segmentation')     
            #elif self._state == 'segmentation':
            #    self.done()  
            #else:
            #    pass
            
        def mode_getter():
            return self._state
        def mode_setter(m):
            self.fsm_change(m)
        def mode_change_update_menus():
            nonlocal win_obvious_instructions, no_options, connect_eps, find_problems, grow_region
            
            m = self._state
            
            no_options.visible = m == 'segmentation'
            connect_eps.visible = m == 'spline'
            find_problems.visible = m == 'spline'
            grow_region.visible = m == 'seed'
            
            if m == 'spline':
                win_obvious_instructions.hbf_title.set_label('Draw the Perimeter of the Holes')
            elif m == 'seed':
                win_obvious_instructions.hbf_title.set_label('Pick Interior Region of Splint')
            #elif m == 'segmentation':
            #    win_obvious_instructions.hbf_title.set_label('Confirm That Trimming Was Successful')
            
            
            self.ui_text_update()
            #paint_radius.visible = (m in {'region'})
            #no_options.visible = not (m in {'region'})
            #segmentation_container.visible = (m in {'segmentation'})
            #segmentation_tools.visible = False
        self.fsm_change_callback(mode_change_update_menus)
        

        def radius_getter():
            return self.brush_radius
        def radius_setter(v):
            self.brush_radius = max(0.1, int(v*10)/10)
            if self.brush:
                self.brush.radius = self.brush_radius

        # def compute_cut():
        #     # should this be a state instead?
        #     self.network_cutter.knife_geometry4()
        #     self.network_cutter.find_perimeter_edges()
        #     for patch in self.network_cutter.face_patches:
        #         patch.grow_seed(self.input_net.bme, self.network_cutter.boundary_edges)
        #         patch.color_patch()
        #     self.net_ui_context.bme.to_mesh(self.net_ui_context.ob.data)
        #     self.fsm_change('segmentation')

        win_obvious_instructions = self.wm.create_window('Draw the Perimeter of the Hole Region', {'pos':8, "vertical":False, "padding":15, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.5), 'border_color':(0.50, 0.50, 0.50, 0.9), "border_width":4.0})
        win_obvious_instructions.hbf_title.fontsize = 20
        
        win_next_back = self.wm.create_window(None, {'pos':2, "vertical":False, "padding":15, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.0), 'border_color':(0.50, 0.50, 0.50, 0.9), "border_width":4.0})
        next_back_container = win_next_back.add(ui.UI_Container(vertical = False, background = (0.50, 0.50, 0.50, 0.90)))
        #next_back_frame = next_back_container.add(ui.UI_Frame('', vertical = False, equal = True, separation = 4))#, background = (0.50, 0.50, 0.50, 0.90)))
        
        back_button = next_back_container.add(ui.UI_Button('Back', mode_backer, margin = 10))
        back_button.label.fontsize = 20
        
        #cancel_button = next_back_frame.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=0))
        cancel_button = next_back_container.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=10))
        cancel_button.label.fontsize = 20
        #next_button = next_back_frame.add(ui.UI_Button('Next', mode_stepper, margin = 0))
        next_button = next_back_container.add(ui.UI_Button('Next', mode_stepper, margin = 10))
        next_button.label.fontsize = 20
        
        
        
        
        win_tools = self.wm.create_window('Hole Margin', {'pos':1, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})
        precut_container = win_tools.add(ui.UI_Container())
        precut_container.rounded_background = True
        precut_tools = precut_container.add(ui.UI_Frame('Tools', fontsize=16))
        precut_tools.add(ui.UI_Button('Plate', self.make_patch_plates, margin = 5))
        
        
        
        #precut_mode = precut_tools.add(ui.UI_Options(mode_getter, mode_setter))
        #precut_mode.add_option('Boundary Edit', value='spline', icon=ui.UI_Image('polyline.png', width=32, height=32))
        #precut_mode.add_option('Boundary > Region', value='seed', icon=ui.UI_Image('seed.png', width=32, height=32))
        #precut_mode.add_option('Region Paint', value='region', icon=ui.UI_Image('paint.png', width=32, height=32))
        
        #precut_tools.add(ui.UI_Button('Next', mode_stepper, margin = 5))
        #precut_tools.add(ui.UI_Button('Connect Endpoints', self.connect_close_endpoints, margin = 5))
        #precut_tools.add(ui.UI_Button('Split Bad Segements', self.split_bad_spline_segments, margin = 5))
        #precut_tools.add(ui.UI_Button('Find Orphans', self.find_calc_orphans, margin = 5))
        #precut_tools.add(ui.UI_Button('Load Network', self.load_from_bmesh, margin = 5))
        
        #precut_tools.add(ui.UI_Button('Nudge Bad Segments', self.nudge_bad_segments, margin = 5))
        
                        
        #container = precut_container.add(ui.UI_Frame('Cut Tools', fontsize=16))
        
        #container.add(ui.UI_Button('Compute Cut', lambda:self.fsm_change('segmentation'), icon=ui.UI_Image('divide32.png', width=32, height=32), margin=5))
        #container.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=5))


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


        info = self.wm.create_window('Hole Margin Help', {'pos':9, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})
        #info.add(ui.UI_Label('Instructions', fontsize=16, align=0, margin=4))
        collapse = info.add(ui.UI_Collapsible('Instructions          ',collapsed = False))
        self.inst_paragraphs = [collapse.add(ui.UI_Markdown('', min_size=(200,10))) for i in range(7)]
        #for i in self.inst_paragraphs: i.visible = False
        #self.ui_instructions = info.add(ui.UI_Markdown('test', min_size=(200,200)))
        precut_options = info.add(ui.UI_Frame('Functions and Options', fontsize=16))
        #paint_radius = precut_options.add(ui.UI_Number("Paint radius", radius_getter, radius_setter))
        no_options = precut_options.add(ui.UI_Label('(none)', color=(1.00, 1.00, 1.00, 0.25)))
        connect_eps = precut_options.add(ui.UI_Button('Connect Endpoints', self.connect_close_endpoints, margin = 5))
        find_problems = precut_options.add(ui.UI_Button('Show Problems', self.find_problems, margin = 5))
        grow_region = precut_options.add(ui.UI_Button('Grow Region', self.regrow_regions, margin = 5))
        self.set_ui_text_no_points()


    # XXX: Fine for now, but will likely be irrelevant in future
    def ui_text_update(self):
        '''
        updates the text in the info box
        '''
        if self._state == 'spline':
            if self.input_net.is_empty:
                self.set_ui_text_no_points()
            elif self.input_net.num_points == 1:
                self.set_ui_text_1_point()
            elif self.input_net.num_points > 1:
                self.set_ui_text_multiple_points()
            elif self.grabber and self.grabber.in_use:
                self.set_ui_text_grab_mode()

        elif self._state == 'region':
            self.set_ui_text_paint()
        elif self._state == 'seed':
            self.set_ui_text_seed_mode()

        elif self._state == 'segmentation':
            self.set_ui_text_segmetation_mode()

        else:
            self.reset_ui_text()

    # XXX: Fine for now, but will likely be irrelevant in future
    def set_ui_text_no_points(self):
        ''' sets the viewports text when no points are out '''
        self.reset_ui_text()
        self.inst_paragraphs[0].set_markdown('A) ' + self.instructions['add'])
        self.inst_paragraphs[1].set_markdown('B) ' + self.instructions['sketch'])

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
        self.inst_paragraphs[1].set_markdown('- ' + self.instructions['seed result'])

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