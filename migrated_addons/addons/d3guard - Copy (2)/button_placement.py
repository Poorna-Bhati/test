'''
Created on May 1, 2018

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import math
import blf
import bgl
import numpy as np

from mathutils import Vector, Matrix, Color, Quaternion
from mathutils.bvhtree import BVHTree
from bpy_extras import view3d_utils
from common_utilities import bversion
import common_drawing
import bgl_utils
from mesh_cut import cross_section_seed_ver1, bound_box
from textbox import TextBox
from odcutils import obj_list_from_lib, obj_from_lib, get_settings


from bracket_placement import BracketDataManager
from dual_elements import generate_bmesh_elastic_button

from subtrees.geometry_utils.transformations import r_matrix_from_principal_axes

def generate_bmesh_elastic_hook(width,
                                total_length,
                                hook_height,
                                base_length,
                                base_height):
      
    bme = bmesh.new()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    
    v0 = bme.verts.new(Vector((0, -width/2, 0)))
    v1 = bme.verts.new(Vector((0, width/2, 0)))
    v2 = bme.verts.new(Vector((base_length, width/2, 0)))
    v3 = bme.verts.new(Vector((base_length, -width/2, 0)))
    
    
    v4 = bme.verts.new(Vector((0, -width/2, base_height)))
    v5 = bme.verts.new(Vector((0, width/2, base_height)))
    v6 = bme.verts.new(Vector((base_length, width/2, base_height)))
    v7 = bme.verts.new(Vector((base_length, -width/2, base_height)))
    
    v8 = bme.verts.new(Vector((0, -width/2, base_height + hook_height)))
    v9 = bme.verts.new(Vector((0, width/2, base_height + hook_height)))
    v10 = bme.verts.new(Vector((base_length, width/2, base_height + hook_height)))
    v11 = bme.verts.new(Vector((base_length, -width/2, base_height + hook_height)))
    
    
    
    v12 = bme.verts.new(Vector((total_length, -width/2, base_height)))
    v13 = bme.verts.new(Vector((total_length, width/2, base_height)))
    v14 = bme.verts.new(Vector((total_length, width/2, base_height + hook_height)))
    v15 = bme.verts.new(Vector((total_length, -width/2, base_height + hook_height)))
    
    
    f0 = bme.faces.new((v0, v1, v2, v3))
    f1 = bme.faces.new((v1, v0, v4, v5))
    f2 = bme.faces.new((v0, v3, v7, v4))
    f3 = bme.faces.new((v3, v2, v6, v7))
    f4 = bme.faces.new((v2, v1, v5, v6))
    
    f5 = bme.faces.new((v5, v4, v8, v9))
    f6 = bme.faces.new((v4, v7, v11, v8))
    f7 = bme.faces.new((v6, v5, v9, v10))
    
    f8 = bme.faces.new((v8, v11, v10, v9))
    #f5 = bme.faces.new(())
    
    f9 = bme.faces.new((v7, v12, v15, v11))
    f10 = bme.faces.new((v6, v13, v12, v7))
    f11 = bme.faces.new((v13, v6, v10, v14))
    f12 = bme.faces.new((v15, v14, v10, v11))
    
    f13 = bme.faces.new((v12, v13, v14, v15))
    
    
    
    #bevel the back corneer
    ed_corner = [ed for ed in v8.link_edges if ed.other_vert(v8) == v9][0]
    
    #bmesh.ops.bevel(bme, geom = [v8, v9, ed_corner], segments = 1 , offset = 1.5, offset_type =0 , profile = .5)

    bmesh.ops.subdivide_edges(bme, edges = bme.edges[:], cuts = 1, use_grid_fill = True)
    
    for v in bme.verts:
        if v.co[0] < .001 and v.co[2] > base_height + hook_height - .01:
            v.co += Vector((.5, 0, -.5))
            
            
    for v in bme.verts:
        v.co -= Vector((base_length/2, 0, 1))
    #bpy.app.debug = True
    return bme

def bracket_placement_draw_callback(self, context):  
    
    self.help_box.draw()
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    common_drawing.outline_region(context.region,(r,g,b,1))
    
    if self.nearest_notch:
        l0 = self.nearest_notch.matrix_world.to_translation()
        l1 = self.bracket_manager.bracket_obj.matrix_world.to_translation()
        R_len = (l0 - l1).length
        mid = .5 * (l0 + l1)
        
        common_drawing.draw_polyline_from_3dpoints(context, [l0, l1], (.1,.8,.1,.5), 4, 'GL_LINE_STRIP')
        
        bgl.glColor4f(.8,.8,.8,1)
        blf.size(0, 24, 72)
        vector2d = view3d_utils.location_3d_to_region_2d(context.region, context.space_data.region_3d, mid)
        blf.position(0, vector2d[0], vector2d[1], 0)
        blf.draw(0, str(R_len)[0:4])
    return    
      
class D3DUAL_OT_place_button(bpy.types.Operator):
    """Place Bracket on surface of selected object"""
    bl_idname = "d3dual.elastic_button_place"
    bl_label = "Place Elastic Button"
    bl_options = {'REGISTER', 'UNDO'}
    

    @classmethod
    def poll(cls, context):
        if context.mode == "OBJECT" and context.object != None:
            return True
        else:
            return False
        
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

        if event.type == 'G' and event.value == 'PRESS':# and self.bracket_slicer:
            #self.bracket_slicer.prepare_slice()
            return 'grab'
        
        if event.type == 'T' and event.value == 'PRESS':# and self.bracket_slicer:
            #self.bracket_slicer.prepare_slice()
            return 'torque'
        
        if event.type == 'R' and event.value == 'PRESS':# and self.bracket_slicer:
            #self.bracket_slicer.prepare_slice()
            return 'rotate'
        
        if event.type == 'S' and event.value == 'PRESS':# and self.bracket_slicer:
            #self.bracket_slicer.prepare_slice()
            return 'tip'
        
        if event.type == 'MOUSEMOVE':  
            return 'main'
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            x, y = event.mouse_region_x, event.mouse_region_y
            self.bracket_manager.place_bracket(context, x,y)
            return 'finish'
                               
        if event.type == 'RET' and event.value == 'PRESS':
            #if self.bracket_slicer:
                #self.bracket_slicer.cache_slice_to_grease(context)
                
            return 'finish'
            
        elif event.type == 'ESC' and event.value == 'PRESS':
            del_obj = self.bracket_manager.bracket_obj
            context.scene.objects.unlink(del_obj)
            bpy.data.objects.remove(del_obj)
            return 'cancel' 

        return 'main'
    
    def modal_torque(self,context,event):
        # no navigation in grab mode
        
        if event.type in {'LEFTMOUSE','RET','ENTER'} and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            #self.bracket_slicer.slice_cancel()
            return 'main'
        
        #elif event.type == 'MOUSEMOVE':
            #update the b_pt location
        #    self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
        #    return 'torque'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'UP_ARROW','DOWN_ARROW'}:
            self.bracket_manager.torque_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'torque'
    
    def modal_rotate(self,context,event):
        # no navigation in grab mode
        
        if event.type in {'LEFTMOUSE','RET','ENTER'} and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            #self.bracket_slicer.slice_cancel()
            return 'main'
        
        #commented out, no longer want to move the mouse
        #elif event.type == 'MOUSEMOVE':
            #update the b_pt location
        #    self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
        #    return 'rotate'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'LEFT_ARROW','RIGHT_ARROW'}:
            self.bracket_manager.rotate_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'rotate'
        
        else:
            return 'rotate'
    
    def modal_tip(self,context,event):
    # no navigation in grab mode
        
        if event.type in {'LEFTMOUSE','RET','ENTER'} and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            #self.bracket_slicer.slice_cancel()
            return 'main'
        
        #commented out, no longer want to move the mouse
        #elif event.type == 'MOUSEMOVE':
            #update the b_pt location
        #    self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
        #    return 'rotate'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'LEFT_ARROW','RIGHT_ARROW'}:
            self.bracket_manager.spin_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'tip'
        
        else:
            return 'tip'
    def modal_start(self,context,event):
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'finish'
        
        elif event.type == 'MOUSEMOVE':
            x, y = event.mouse_region_x, event.mouse_region_y
            if self.started == False:
                
                res = self.bracket_manager.place_bracket(context, x,y, normal = False)   
                if res:
                    self.started = True
                    
                    
                    loc = self.bracket_manager.bracket_obj.matrix_world.to_translation()
                    if loc[0] > 0: #left side
                        if self.target == 'MAX':
                            Z = Vector((1, 0, 0))
                            X = Vector((0,-1, 0))
                            Y = Vector((0, 0,-1))
                        
                        else:
                            Z = Vector((1, 0, 0))
                            X = Vector((0,1, 0))
                            Y = Vector((0, 0,1))
                    else: #right side
                        if self.target == 'MAX':
                            Z = Vector((-1, 0, 0))
                            X = Vector((0,- 1, 0))
                            Y = Vector((0, 0, 1))
                        
                        else:
                            Z = Vector((-1, 0, 0))
                            X = Vector((0,1, 0))
                            Y = Vector((0, 0,-1))
                    
                    R = r_matrix_from_principal_axes(X, Y, Z).to_4x4()
                    T = Matrix.Translation(loc)   
                    self.bracket_manager.bracket_obj.matrix_world = T * R
                    self.nearest_notch = self.find_nearest_notch()
                    
            else:
                self.bracket_manager.place_bracket(context, x,y, normal = False, lock_x = False)
                
                if self.nearest_notch:
                    print('doing some alignment')
                    
                
            #self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
            return 'start'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'UP_ARROW','DOWN_ARROW'}:
            self.bracket_manager.spin_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'start'
        
        elif event.type == "RIGTMOUSE" and event.value == 'PRESS':
            del_obj = self.bracket_manager.bracket_obj
            context.scene.objects.unlink(del_obj)
            bpy.data.objects.remove(del_obj)
            return 'cancel'
        
        else:
            return 'start'
           
    def modal_grab(self,context,event):
        # no navigation in grab mode
        #uses the slicer to manage the grab
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            #self.bracket_slicer.slice_cancel()
            return 'main'
        
        elif event.type == 'MOUSEMOVE':
            #update the b_pt location
            #self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
            return 'grab'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'UP_ARROW','DOWN_ARROW'}:
            self.bracket_manager.spin_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'grab'
      
    def modal(self, context, event):
        context.area.tag_redraw()
        
        FSM = {}
        FSM['start']   = self.modal_start
        FSM['main']    = self.modal_main
        FSM['rotate']    = self.modal_rotate
        FSM['grab']   = self.modal_grab
        FSM['torque']  = self.modal_torque
        FSM['tip']  = self.modal_tip
        FSM['nav']     = self.modal_nav
        
        nmode = FSM[self.mode](context, event)
        
        if nmode == 'nav': 
            return {'PASS_THROUGH'}
        
        if nmode in {'finish','cancel'}:
            #clean up callbacks
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            context.space_data.show_manipulator = True
            bpy.ops.d3dual.enable_button_visualization()
            return {'FINISHED'} if nmode == 'finish' else {'CANCELLED'}
        
        if nmode: self.mode = nmode
        
        return {'RUNNING_MODAL'}
    
    def find_nearest_notch(self):
        
        if not len(self.notches): return None
        
        notch = self.bracket_manager.bracket_obj
        loc = notch.matrix_world.to_translation()
        
        if abs(loc[0]) < .01:
            print('too close to midline')
            return None
        
        def dist(other_notch):
            return (other_notch.matrix_world.to_translation() - loc).length
        
        
        nearest_notch = min(self.notches, key = dist)
        
        loc_2 = nearest_notch.matrix_world.to_translation()
        
        if loc_2[0] * loc[0] < 0:
            print('different jaw sides')
            #only check for notches on the same side of jaw
            return None
        
        return nearest_notch
    
    
    def invoke(self, context, event):
        

        settings = get_settings()

        snap_ob = context.object
        
        if 'Button' in snap_ob.name:
            self.report({'ERROR'}, 'It looks like you have a button selected, right click on a model or shell then place button')
            return {'CANCELLED'}
        
        bpy.ops.d3dual.stop_button_visualization()
        
        if "Button Mat" not in bpy.data.materials:
            a_mat = bpy.data.materials.new('Button Mat')
            a_mat.diffuse_color = Color((0,.8,.4))
            #mat.diffuse_intensity = 1
            #mat.emit = .8
        else:
            a_mat = bpy.data.materials.get('Button Mat')
          
        self.notches =  [ob for ob in bpy.data.objects if "Button" in ob.name] 
        print('There are %i buttons' % len(self.notches))
        self.nearest_notch = None
        
        me = bpy.data.meshes.new("Elastic Button")
        ob = bpy.data.objects.new("Elastic Button", me)
        context.scene.objects.link(ob)
        
        ob.parent = context.object
        if 'MAND' in snap_ob.name:
            print('Spinning the attachment')
            self.target = 'MAND'
        else:
            self.target = 'MAX'
            #mx = Matrix.Rotation(math.pi, 4, 'Z')  #spin it 180 before snapping?
            #ob.matrix_world = mx
        #ob.location = context.scene.cursor_location    
        me.materials.append(a_mat)
        
        
        if 'MAND' in snap_ob.name:
            base_height = settings.def_button_base_height + 2 # TODO default mandibular stalk
        else:
            base_height = settings.def_button_base_height
            
        bme_b = generate_bmesh_elastic_button(base_diameter = settings.def_button_base_diameter,
                                              base_height = base_height,
                                              stalk_diameter = settings.def_button_stalk_diameter,
                                              stalk_height = settings.def_button_stalk_height,
                                              button_minor = settings.def_button_minor,
                                              button_major = settings.def_button_major,
                                              button_height = settings.def_button_thickness,
                                              base_curvature_x = .3,
                                              base_curvature_y = .2,
                                              base_torque = 0)
            
                       
        bme_b.to_mesh(me)
        bme_b.free()
        
        
            
        #set ID props        
        ob['base_diameter'] =  settings.def_button_base_diameter
        ob['base_heigt'] = base_height
        ob['stalk_diameter'] = settings.def_button_stalk_diameter
        ob['stalk_height'] = settings.def_button_stalk_height
        ob['button_major'] = settings.def_button_major
        ob['button_minor'] =  settings.def_button_minor
        ob['button_height'] =  settings.def_button_thickness
        ob['base_curvature_x'] = .3
        ob['base_curvature_y'] = .2
        ob['base_torque'] = 0
        ob['constrain_length'] = settings.def_button_constrain_length #VERY IMPROTAT
        
        #set attachment properties
        ob['d3d_a_type'] = 'simple_attachment'
        ob['csg_number'] = 0
        ob['csg_op'] = 'UNION'
        if 'MAX' in context.object.name:
            ob['target'] = 'MAX'
        else: # 'MAND' in context.object.name:
            ob['target'] = 'MAND'
        
        mod = ob.modifiers.new('Subsurf', type = 'SUBSURF')
        mod.levels = 2
        
        self.bracket_manager = BracketDataManager(context,snap_type ='OBJECT', 
                                                      snap_object = snap_ob, 
                                                      name = 'Elastic', 
                                                      bracket = ob)
        self.bracket_slicer = None
        
        for obj in bpy.data.objects:
            obj.select = False
            
        ob.select = True
        context.scene.objects.active = ob
        context.space_data.show_manipulator = False
        context.space_data.transform_manipulators = {'TRANSLATE', 'ROTATE'}
        context.space_data.transform_orientation = 'LOCAL'
        
        help_txt = "ELASTIC BUTTON PLACEMENT\n\nLeft Click on model to place button/bracket  \n-Use Scroll Wheel to spin before clicking"
        self.help_box = TextBox(context,500,500,300,200,10,20,help_txt)
        self.help_box.snap_to_corner(context, corner = [1,1])
        self.help_box.format_and_wrap_text()
        self.mode = 'start'
        self.started = False
        self._handle = bpy.types.SpaceView3D.draw_handler_add(bracket_placement_draw_callback, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
class D3Dual_OT_place_elastic_hook(bpy.types.Operator):
    """Place Elastic Hook on surface of selected object"""
    bl_idname = "d3dual.elastic_hook_place"
    bl_label = "Place Elastic Hook"
    bl_options = {'REGISTER', 'UNDO'}
    

    @classmethod
    def poll(cls, context):
        if context.mode == "OBJECT" and context.object != None:
            return True
        else:
            return False
        
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

        if event.type == 'G' and event.value == 'PRESS':# and self.bracket_slicer:
            #self.bracket_slicer.prepare_slice()
            return 'grab'
        
        if event.type == 'T' and event.value == 'PRESS':# and self.bracket_slicer:
            #self.bracket_slicer.prepare_slice()
            return 'torque'
        
        if event.type == 'R' and event.value == 'PRESS':# and self.bracket_slicer:
            #self.bracket_slicer.prepare_slice()
            return 'rotate'
        
        if event.type == 'S' and event.value == 'PRESS':# and self.bracket_slicer:
            #self.bracket_slicer.prepare_slice()
            return 'tip'
        
        if event.type == 'MOUSEMOVE':  
            return 'main'
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            x, y = event.mouse_region_x, event.mouse_region_y
            self.bracket_manager.place_bracket(context, x,y)
            return 'finish'
                               
        if event.type == 'RET' and event.value == 'PRESS':
            #if self.bracket_slicer:
                #self.bracket_slicer.cache_slice_to_grease(context)
                
            return 'finish'
            
        elif event.type == 'ESC' and event.value == 'PRESS':
            del_obj = self.bracket_manager.bracket_obj
            context.scene.objects.unlink(del_obj)
            bpy.data.objects.remove(del_obj)
            return 'cancel' 

        return 'main'
    
    def modal_torque(self,context,event):
        # no navigation in grab mode
        
        if event.type in {'LEFTMOUSE','RET','ENTER'} and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            #self.bracket_slicer.slice_cancel()
            return 'main'
        
        #elif event.type == 'MOUSEMOVE':
            #update the b_pt location
        #    self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
        #    return 'torque'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'UP_ARROW','DOWN_ARROW'}:
            self.bracket_manager.torque_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'torque'
    
    def modal_rotate(self,context,event):
        # no navigation in grab mode
        
        if event.type in {'LEFTMOUSE','RET','ENTER'} and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            #self.bracket_slicer.slice_cancel()
            return 'main'
        
        #commented out, no longer want to move the mouse
        #elif event.type == 'MOUSEMOVE':
            #update the b_pt location
        #    self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
        #    return 'rotate'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'LEFT_ARROW','RIGHT_ARROW'}:
            self.bracket_manager.rotate_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'rotate'
        
        else:
            return 'rotate'
    
    def modal_tip(self,context,event):
    # no navigation in grab mode
        
        if event.type in {'LEFTMOUSE','RET','ENTER'} and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            #self.bracket_slicer.slice_cancel()
            return 'main'
        
        #commented out, no longer want to move the mouse
        #elif event.type == 'MOUSEMOVE':
            #update the b_pt location
        #    self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
        #    return 'rotate'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'LEFT_ARROW','RIGHT_ARROW'}:
            self.bracket_manager.spin_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'tip'
        
        else:
            return 'tip'
    def modal_start(self,context,event):
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'finish'
        
        elif event.type == 'MOUSEMOVE':
            x, y = event.mouse_region_x, event.mouse_region_y
            if self.started == False:
                
                res = self.bracket_manager.place_bracket(context, x,y, normal = True)
                
                if res:
                    self.started = True
                    self.nearest_notch = self.find_nearest_notch()
                    
                    loc = self.bracket_manager.bracket_obj.matrix_world.to_translation()
                    if loc[0] > 0: #left side
                        if self.target == 'MAX':
                            Z = Vector((1, 0, 0))
                            X = Vector((0,-1, 0))
                            Y = Vector((0, 0,-1))
                        
                        else:
                            Z = Vector((1, 0, 0))
                            X = Vector((0,1, 0))
                            Y = Vector((0, 0,1))
                    else: #right side
                        if self.target == 'MAX':
                            Z = Vector((-1, 0, 0))
                            X = Vector((0,- 1, 0))
                            Y = Vector((0, 0, 1))
                        
                        else:
                            Z = Vector((-1, 0, 0))
                            X = Vector((0,1, 0))
                            Y = Vector((0, 0,-1))
                    
                    R = r_matrix_from_principal_axes(X, Y, Z).to_4x4()
                    T = Matrix.Translation(loc)   
                    self.bracket_manager.bracket_obj.matrix_world = T * R
                    
            else:
                self.bracket_manager.place_bracket(context, x,y, normal = True, lock_x = True)
                self.nearest_notch = self.find_nearest_notch()
            #self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
            return 'start'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'UP_ARROW','DOWN_ARROW'}:
            self.bracket_manager.spin_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'start'
        
        elif event.type == "RIGTMOUSE" and event.value == 'PRESS':
            del_obj = self.bracket_manager.bracket_obj
            context.scene.objects.unlink(del_obj)
            bpy.data.objects.remove(del_obj)
            return 'cancel'
        
        else:
            return 'start'
           
    def modal_grab(self,context,event):
        # no navigation in grab mode
        #uses the slicer to manage the grab
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            #confirm location
            #self.bracket_slicer.slice_confirm()
            return 'main'
        
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            #put it back!
            #self.bracket_slicer.slice_cancel()
            return 'main'
        
        elif event.type == 'MOUSEMOVE':
            #update the b_pt location
            #self.bracket_slicer.slice_mouse_move(context,event.mouse_region_x, event.mouse_region_y)
            return 'grab'
        
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'UP_ARROW','DOWN_ARROW'}:
            self.bracket_manager.spin_event(event.type, event.shift)
            #self.bracket_slicer.slice()
            return 'grab'
      
    def modal(self, context, event):
        context.area.tag_redraw()
        
        FSM = {}
        FSM['start']   = self.modal_start
        FSM['main']    = self.modal_main
        FSM['rotate']    = self.modal_rotate
        FSM['grab']   = self.modal_grab
        FSM['torque']  = self.modal_torque
        FSM['tip']  = self.modal_tip
        FSM['nav']     = self.modal_nav
        
        nmode = FSM[self.mode](context, event)
        
        if nmode == 'nav': 
            return {'PASS_THROUGH'}
        
        if nmode in {'finish','cancel'}:
            #clean up callbacks
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            context.space_data.show_manipulator = True
            return {'FINISHED'} if nmode == 'finish' else {'CANCELLED'}
        
        if nmode: self.mode = nmode
        
        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):

        settings = get_settings()

        snap_ob = context.object
        
        if 'Hook' in snap_ob.name:
            self.report({'ERROR'}, 'It looks like you have a button selected, right click on a model or shell then place button')
            return {'CANCELLED'}
        
        if "Button Mat" not in bpy.data.materials:
            a_mat = bpy.data.materials.new('Button Mat')
            a_mat.diffuse_color = Color((0,.8,.4))
            #mat.diffuse_intensity = 1
            #mat.emit = .8
        else:
            a_mat = bpy.data.materials.get('Button Mat')
          
        me = bpy.data.meshes.new("Elastic Hook")
        ob = bpy.data.objects.new("Elastic Hook", me)
        context.scene.objects.link(ob)
        
        ob.parent = context.object
        ob.location = context.scene.cursor_location    
        me.materials.append(a_mat)
          
        bme_b = generate_bmesh_elastic_hook(width =2.0, 
                                            total_length = 5.0, 
                                            hook_height = 2.0, 
                                            base_length = 3.0, 
                                            base_height = 3.0)
            
                       
        bme_b.to_mesh(me)
        bme_b.free()
        
        #set ID props        
        ob['width'] =  2.0
        ob['total_length'] = 5.0
        ob['hook_height'] = 2.0
        ob['base_length'] = 3.0
        ob['base_height'] = 3.0
        
        
        if 'MAND' in snap_ob.name:
            Mx = Matrix.Rotation(math.pi, 4, 'Z')
            me.transform(Mx)
            
        mod = ob.modifiers.new('Subsurf', type = 'SUBSURF')
        mod.levels = 2
        
        self.bracket_manager = BracketDataManager(context,snap_type ='OBJECT', 
                                                      snap_object = snap_ob, 
                                                      name = 'Elastic', 
                                                      bracket = ob)
        self.bracket_slicer = None
        
        for obj in bpy.data.objects:
            obj.select = False
            
        ob.select = True
        context.scene.objects.active = ob
        context.space_data.show_manipulator = False
        context.space_data.transform_manipulators = {'TRANSLATE', 'ROTATE'}
        context.space_data.transform_orientation = 'LOCAL'
        
        help_txt = "ELASTIC BUTTON PLACEMENT\n\nLeft Click on model to place button/bracket  \n-Use Scroll Wheel to spin before clicking"
        self.help_box = TextBox(context,500,500,300,200,10,20,help_txt)
        self.help_box.snap_to_corner(context, corner = [1,1])
        self.help_box.format_and_wrap_text()
        self.mode = 'start'
        self.started = False
        self._handle = bpy.types.SpaceView3D.draw_handler_add(bracket_placement_draw_callback, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}    

class D3Dual_OT_align_button_pair(bpy.types.Operator):
    """Align two buttons"""
    bl_idname = "d3dual.button_alignment"
    bl_label = "Align Buttons"
    bl_options = {'REGISTER', 'UNDO'}
    

    @classmethod
    def poll(cls, context):
        if not context.object: return False
        if 'Button' not in context.object.name: return False
        return True
    
    def execute(self, context):
        
        b0 = context.object
        
        b1 = find_other_button_match(b0)
        if b1 == None:
            return {'CANCELLED'}
        
        mx0 = b0.matrix_world
        q0 = mx0.to_quaternion()
        
        mx1 = b1.matrix_world
        q1 = mx1.to_quaternion()
        
        z0 = q0 * Vector((0,0,1))
        z1 = q1 * Vector((0,0,1))
        
        if abs(z0.dot(z1) - 1) < .001:
            print('already aligned')
            return {'FINISHED'}
        
        
        axis = z0.cross(z1)
        angle = z0.angle(z1)
        r_fix = Matrix.Rotation(-angle, 4, axis)
        
        orig_loc, orig_rot, orig_scale = mx1.decompose()
        T = Matrix.Translation(orig_loc)
        R = orig_rot.to_matrix().to_4x4()
        
        b1.matrix_world = T * r_fix * R
        
        return {'FINISHED'}
        
class D3Dual_OT_align_button_pair_connection(bpy.types.Operator):
    """Align two buttons"""
    bl_idname = "d3dual.button_alignment_connection"
    bl_label = "Align Button Connection"
    bl_options = {'REGISTER', 'UNDO'}
    

    @classmethod
    def poll(cls, context):
        if not context.object: return False
        if 'Button' not in context.object.name: return False
        return True
    
    def execute(self, context):
        
        b0 = context.object
        
        b1 = find_other_button_match(b0)
        if b1 == None:
            return {'CANCELLED'}
        
        mx0 = b0.matrix_world
        q0 = mx0.to_quaternion()
        t0 = mx0.to_translation()
        
        
        mx1 = b1.matrix_world
        q1 = mx1.to_quaternion()
        t1 = mx1.to_translation()
        
        x0, x1 = q0 * Vector((1,0,0)), q1 * Vector((1,0,0))
        y0, y1 = q0 * Vector((0,1,0)), q1 * Vector((0,1,0))
        z0, z1 = q0 * Vector((0,0,1)), q1 * Vector((0,0,1))
        
        
        vec_connect = t1 - t0
        vec_connect.normalize()
        
        
        #Method 1, tips pointed exactly away from each other
        #z0 = z0 - z0.dot(vec_connect) * vec_connect
        #x0 = -vec_connect
        #y0 = z0.cross(x0)
        
        #z1 = z1 - z1.dot(vec_connect) * vec_connect
        #x1 = vec_connect
        #y1 = z1.cross(x1)
        #Rmx0 = r_matrix_from_principal_axes(x0, y0, z0).to_4x4()
        #Rmx1 = r_matrix_from_principal_axes(x1, y1, z1).to_4x4()
        #method 2 attempt to preserve the tip direction
        z_avg = .5 * z0 + .5*z1
        z_avg = z_avg - z_avg.dot(vec_connect) * vec_connect
        z_avg.normalize()
        
        #cross everyoen into perpendicular
        y0 = z_avg.cross(x0)
        y0.normalize()
        x0 = y0.cross(z_avg)
        x0.normalize()
        
        y1 = z_avg.cross(x1)
        y1.normalize()
        x1 = y1.cross(z_avg)
        x1.normalize()
        
        
        Rmx0 = r_matrix_from_principal_axes(x0, y0, z_avg).to_4x4()
        Rmx1 = r_matrix_from_principal_axes(x1, y1, z_avg).to_4x4()
        
        
        b0.matrix_world = Matrix.Translation(t0) * Rmx0
        b1.matrix_world = Matrix.Translation(t1) * Rmx1
        
        return {'FINISHED'}
      
class D3Dual_OT_enforce_button_length(bpy.types.Operator):
    """Enforce button distance"""
    bl_idname = "d3dual.enforce_button_distance"
    bl_label = "Enforce Button Distance"
    bl_options = {'REGISTER', 'UNDO'}
    

    @classmethod
    def poll(cls, context):
        if not context.object: return False
        if 'Button' not in context.object.name: return False
        return True
    
    def execute(self, context):
        
        b0 = context.object
        
        b1 = find_other_button_match(b0)
        if b1 == None:
            return {'CANCELLED'}
        
        mx0 = b0.matrix_world
        mx1 = b1.matrix_world
        
        
        t0, t1 = mx0.to_translation(), mx1.to_translation()
        R = t1 - t0
        R.normalize()
        
        b1.location = t0 + 20 * R
        
        #then snap to target?
        return {'FINISHED'}
 
 
 #some globgal variables to keep around


button_pairs = {}
last_values = {}
do_update_rotation = {}
do_update_translation = {}

   
    
def find_other_button_match(b_ob):
    '''
    doens't work if more than 2 buttons on each side
    '''
    buttons = [ob for ob in bpy.data.objects if 'Button' in ob.name]
    b_set = set(buttons)
    
    global button_pairs
    
    if b_ob in button_pairs.keys():
        b = button_pairs[b_ob]
 
        if b.name in bpy.data.objects:
            return b
        else:
            del button_pairs[b_ob]
            
    else:
        for b in buttons:
            if b == b_ob: continue
        
            loc = b.matrix_world.to_translation()
            loc2 = b_ob.matrix_world.to_translation()    
            
            if loc2[0] * loc[0] < 0:
                print('different jaw sides')
                #only check for notches on the same side of jaw
                continue
            
            else:
                button_pairs[b_ob] = b
                button_pairs[b] = b_ob
                return b
        
    return None



def constrain_button_relationship(b0):
    '''
    complex fancy way to align these buttons to each other
    '''
    
    b1 = find_other_button_match(b0)
    
    if not b1: return
    if not b0.get('constrain_length'): return
    
    global last_values
    global do_update_rotation
    global do_update_translation
    
    if b0 not in last_values.keys() or b1 not in last_values.keys():
        last_values[b0] = b0.matrix_world.copy()
        last_values[b1] = b1.matrix_world.copy()
        return
    
    if (b0.matrix_world.to_translation() - last_values[b0].to_translation()).length < .001:
        print('nothing moved')
        
        if np.allclose(b0.matrix_world, last_values[b0]):
            print('we did rotate b0 last frame so dont mess  with it this frame')
            last_values[b0] = b0.matrix_world.copy()
            return
        
        else:
            do_update_rotation = True
        
        
    
    d = b0.get('constrain_length')
    
    mx0 = b0.matrix_world
    q0 = mx0.to_quaternion()
    
    T0, R0, S0 = mx0.decompose()
    #slice out Z axis before converting to 4x4
    X0 = q0 * Vector((1,0,0))
    Y0 = q0 * Vector((0,1,0))
    Z0 = q0 * Vector((0,0,1))
    R0 = R0.to_matrix().to_4x4()

    #decompose the matrix
    mx1 = b1.matrix_world
    q1 = mx1.to_quaternion()
    T1, R1, orig_scale = mx1.decompose()
    X1 = q1 * Vector((1,0,0))
    Y1 = q1 * Vector((0,1,0))
    Z1 = q1 * Vector((0,0,1))
    R1 =  R1.to_matrix().to_4x4()
     
    mx_last = last_values[b0]
    T0_last = mx_last.to_translation()
    
    if T1[2] < T0[2]:    
        dt = T0 - T0_last - (T0- T0_last).dot(Z0) * Z0  #first, control any bodily translation of button 0 (controller) not in the in and out direction
    else:
        dt = T0 - T0_last
    
    last_rad = T1 - T0_last
    last_rad.normalize()
    
    vec_connect = T1 - T0
    vec_connect.normalize()
    
    if dt.length > .001:
        
        #push the object in the direction moved along the existing distance between them
        if T1[2] < T0[2]: #only make the bottom follow the top
            #dt is handled inside of T0 which reflects new position
            T1 = T0 + d * last_rad #corrected position to constraint length
            
        else:  #we are moving the lower so snap it
            T0 = T1 - d * vec_connect
    

    #THIS METHOD FLATTONS THE Z against the line connectin them
    #but does not twist the tips to align
    z_avg = Z0 
    z_avg = z_avg - z_avg.dot(vec_connect) * vec_connect
    z_avg.normalize()
        
    #cross everyoen into perpendicular
    Y0 = z_avg.cross(X0)
    Y0.normalize()
    X0 = Y0.cross(z_avg)
    X0.normalize()
        
    Y1 = z_avg.cross(X1)
    Y1.normalize()
    X1 = Y1.cross(z_avg)
    X1.normalize()
    
        
        
    Rmx0 = r_matrix_from_principal_axes(X0, Y0, z_avg).to_4x4()
    Rmx1 = r_matrix_from_principal_axes(X1, Y1, z_avg).to_4x4()
        
    
    #THIS METHOD LOCKS THE X TO POINT AWAY FROM EACH OTHER  
        
    #now correct rotate around Z0 to point the nub away from the other button
    #X0 = -vec_connect  #the direction pointing away from the other button
    #X0 = X0 - X0.dot(Z0) * Z0
    #X0.normalize()
    #Y0 = Z0.cross(X0)
    
    #Z0 = Z0 - Z0.dot(X0) * X0  #take the X component out of Z
    #Z0.normalize()
    
    #by constraining them to bein same plane, and point away from each other
    #X1 = vec_connect  #the direction pointing away from the other button
    #X1 = X1 - X1.dot(Z0) * Z0
    #X1.normalize()
    #Y1 = Z0.cross(X1)
    #R0 = r_matrix_from_principal_axes(X0, Y0, Z0).to_4x4()    
    #R1 = r_matrix_from_principal_axes(X1, Y1, Z0).to_4x4()
    
    if do_update_rotation:
        mxw0 =  Matrix.Translation(T0) * Rmx0
        b0.matrix_world =mxw0
    
    mxw1 = Matrix.Translation(T1) * Rmx1
    b1.matrix_world = mxw1
    
    
    last_values[b0] = b0.matrix_world.copy()
    
    
    #if we need snappint to surface, then let constraints handle that!

def register():
    bpy.utils.register_class(D3DUAL_OT_place_button)
    bpy.utils.register_class(D3Dual_OT_align_button_pair)
    bpy.utils.register_class(D3Dual_OT_enforce_button_length)
    bpy.utils.register_class(D3Dual_OT_align_button_pair_connection)
    
    #bpy.utils.register_class( D3Dual_OT_place_elastic_hook)
    
def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_place_button)
    bpy.utils.unregister_class(D3Dual_OT_align_button_pair)
    bpy.utils.unregister_class(D3Dual_OT_enforce_button_length)
    bpy.utils.unregister_class(D3Dual_OT_align_button_pair_connection)
    #bpy.utils.unregister_class(D3Dual_OT_place_elastic_hook)
    