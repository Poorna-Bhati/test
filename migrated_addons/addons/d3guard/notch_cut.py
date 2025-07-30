import math
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import bgl
import blf

import time
from curve import LineDrawer
from textbox import TextBox
import tracking

from mathutils import Vector, Matrix, Quaternion, Color
from odcutils import get_com_bme
import common_drawing
from common_drawing import outline_region
from common_utilities import get_settings
from bpy_extras import view3d_utils
import odcutils


from bracket_placement import BracketDataManager
from dual_elements import generate_bmesh_elastic_button
from bmesh_fns import join_bmesh



def generate_bmesh_elastic_notch2(length, tip_diameter, base_width, depth, bend):
    bme = bmesh.new()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    T = Matrix.Translation(Vector((0,length - tip_diameter/2, 0)))
    #R = Matrix.Rotation(-math.pi/2, 4, 'Z')
    geom = bmesh.ops.create_circle(bme, cap_ends = True, cap_tris = True, segments = 24, diameter = tip_diameter/2, matrix = T)
    
    to_delete = geom['verts'][8:19]
    non_sub_edges =  set(bme.edges[:])
    bmesh.ops.delete(bme, geom = to_delete, context = 1)
    
    top_center = geom['verts'][0]
    top_right = geom['verts'][19]
    top_left = geom['verts'][7]
    bottom_left = bme.verts.new(Vector((-base_width/2, 0, 0)))
    bottom_center = bme.verts.new(Vector((0, 0, 0)))
    bottom_right = bme.verts.new(Vector((base_width/2, 0, 0)))
    
    f1 = bme.faces.new((top_right, top_center, bottom_center, bottom_right))
    f2 = bme.faces.new((top_center, top_left, bottom_left, bottom_center))
    
    sub_edges = list(set(bme.edges[:]) - non_sub_edges)
    bmesh.ops.subdivide_edges(bme, edges = sub_edges, cuts = 4)
    
    
    #curve the cut based on Z height
    
    for v in bme.verts:
        factor = (v.co[1]/length)**2
        Rmx = Matrix.Rotation(-factor * 10/180 * math.pi, 4, 'Z')
        delta = Rmx * Vector((0,v.co[1], 0)) - v.co
        
        #v.co = Rmx * v.co - delta + factor * Vector((bend, 0, 0))
        v.co +=  factor * Vector((bend, 0, 0))   
    
    
    g_dict = bmesh.ops.extrude_face_region(bme, geom = bme.faces[:])
    vs = [ele for ele in g_dict['geom'] if isinstance(ele, bmesh.types.BMVert)]
    for v in vs:
        v.co -= Vector((0,0,depth))
        
    
    bme.transform(Matrix.Translation(Vector((0,-length/2,0.25 * depth))))
    bmesh.ops.recalc_face_normals(bme, faces = bme.faces[:])
    #add a semi circle at tip
    #make it a face
    #add base verts
    #subdivide it
    #bend it
    #extrude it
    
    return bme

def generate_bmesh_elastic_notch3(length, tip_diameter, base_width, depth, bend, tab_width):
    
    
    bme = bmesh.new()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    #replace 2 with spacer TODO
    Tl = Matrix.Translation(Vector((-(tab_width + base_width)/2,length - tip_diameter/2, 0)))
    Tr = Matrix.Translation(Vector(((tab_width + base_width)/2,length - tip_diameter/2, 0)))
    #R = Matrix.Rotation(-math.pi/2, 4, 'Z')
    geom_l = bmesh.ops.create_circle(bme, cap_ends = True, cap_tris = True, segments = 24, diameter = tip_diameter/2, matrix = Tl)
    geom_r = bmesh.ops.create_circle(bme, cap_ends = True, cap_tris = True, segments = 24, diameter = tip_diameter/2, matrix = Tr)
    
    to_delete = geom_l['verts'][8:19] + geom_r['verts'][8:19]
    non_sub_edges =  set(bme.edges[:])
    bmesh.ops.delete(bme, geom = to_delete, context = 1)
    
    top_r_center = geom_r['verts'][0]
    top_r_right = geom_r['verts'][19]
    top_r_left = geom_r['verts'][7]
    
    top_l_center = geom_l['verts'][0]
    top_l_right = geom_l['verts'][19]
    top_l_left = geom_l['verts'][7]
    
    #TODO replace 1 with 1/2 spacer
    bottom_l_left = bme.verts.new(Vector((-(base_width + tab_width/2), 0, 0)))
    bottom_l_center = bme.verts.new(Vector((-(base_width/2 + tab_width/2), 0, 0)))
    bottom_l_right = bme.verts.new(Vector((-tab_width/2, 0, 0)))
    
    bottom_r_right = bme.verts.new(Vector((tab_width/2 + base_width, 0, 0)))
    bottom_r_center = bme.verts.new(Vector((tab_width/2 + base_width/2, 0, 0)))
    bottom_r_left = bme.verts.new(Vector((tab_width/2, 0, 0)))

    f1r = bme.faces.new((top_r_right, top_r_center, bottom_r_center, bottom_r_right))
    f2r = bme.faces.new((top_r_center, top_r_left, bottom_r_left, bottom_r_center))

    f1l = bme.faces.new((top_l_right, top_l_center, bottom_l_center, bottom_l_right))
    f2l = bme.faces.new((top_l_center, top_l_left, bottom_l_left, bottom_l_center))
    
    base_r = bme.verts.new(Vector((tab_width/2 + base_width, -2, 0)))
    base_l = bme.verts.new(Vector((-tab_width/2 + -base_width, -2, 0)))                   
    
    f3 = bme.faces.new((base_r, bottom_r_right, bottom_r_center, bottom_r_left, bottom_l_right, bottom_l_center, bottom_l_left, base_l))
    
    non_sub_edges.update(f3.edges[:])
                      
    sub_edges = list(set(bme.edges[:]) - non_sub_edges)
    bmesh.ops.subdivide_edges(bme, edges = sub_edges, cuts = 4)
    
    
    #curve the cut based on Z height
    
    for v in bme.verts:
        factor = (v.co[1]/length)**2
        Rmx = Matrix.Rotation(-factor * 10/180 * math.pi, 4, 'Z')
        delta = Rmx * Vector((0,v.co[1], 0)) - v.co
        
        #v.co = Rmx * v.co - delta + factor * Vector((bend, 0, 0))
        v.co +=  factor * Vector((bend, 0, 0))   
    
    
    g_dict = bmesh.ops.extrude_face_region(bme, geom = bme.faces[:])
    vs = [ele for ele in g_dict['geom'] if isinstance(ele, bmesh.types.BMVert)]
    for v in vs:
        v.co -= Vector((0,0,depth))
        
    
    vl = min(bme.verts, key = lambda x: (x.co - Vector((-tab_width/2, 0, 0))).length)
    vr = min(bme.verts, key = lambda x: (x.co - Vector((tab_width/2, 0, 0))).length)
    
    vl_depth = min(bme.verts, key = lambda x: (x.co - Vector((-tab_width/2, 0, -depth))).length)
    vr_depth = min(bme.verts, key = lambda x: (x.co - Vector((tab_width/2, 0, -depth))).length)
    
    bme.transform(Matrix.Translation(Vector((0,-length/2,0.25 * depth))))
    bmesh.ops.recalc_face_normals(bme, faces = bme.faces[:])
    
    
    b_ed_r = [ed for ed in vr.link_edges if ed.other_vert(vr) == vr_depth]
    b_ed_l = [ed for ed in vl.link_edges if ed.other_vert(vl) == vl_depth]
    
    bevel_geom = b_ed_r + b_ed_l + [vl, vl_depth, vr, vr_depth]
    bmesh.ops.bevel(bme, geom = bevel_geom, offset = .5, offset_type = 1, segments = 4, profile = .5)
    #bevel the tab corners
    
    
    #add a semi circle at tip
    #make it a face
    #add base verts
    #subdivide it
    #bend it
    #extrude it
    
    return bme
    
def update_elastic_notch(self, context):
    if self.hold_update:
        return
    
    ob = context.object
    me = ob.data
    
    bme_b = generate_bmesh_elastic_notch3(length = self.length,
                                            tip_diameter = self.tip_diameter,
                                            base_width = self.base_width,
                                            depth = self.depth,
                                            bend = self.bend,
                                            tab_width= self.tab_width)
                      
    #set ID props        
    ob['length'] =  self.length
    ob['tip_diameter'] = self.tip_diameter
    ob['base_width'] = self.base_width
    ob['tab_width'] = self.tab_width
    ob['depth'] = self.depth
    ob['bend'] = self.bend
        
    bme_b.to_mesh(me)
    #update the mesh so it redraws
    me.update()

    bme_b.free()
    
    return

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

class D3Sleep_OT_place_notch(bpy.types.Operator):
    """Place Elastic Hook on surface of selected object"""
    bl_idname = "d3sleep.elastic_notch_place"
    bl_label = "Place Elastic Notch"
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
    
    def find_nearest_notch(self):
        
        if not len(self.notches): return None
        
        notch = self.bracket_manager.bracket_obj
        loc = notch.matrix_world.to_translation()
        
        def dist(other_notch):
            return (other_notch.matrix_world.to_translation() - loc).length
        
        
        nearest_notch = min(self.notches, key = dist)
        
        loc_2 = nearest_notch.matrix_world.to_translation()
        
        if loc_2[1] * loc[1] < 0:
            #only check for notches on the same side of jaw
            return None
        
        return nearest_notch
        
        
    def invoke(self, context, event):

        settings = get_settings()

        snap_ob = context.object
        
        if 'Shell' not in snap_ob.name:
            self.report({'ERROR'},'Must pick a Shell Object to place notch in')
            return {'CANCELLED'}
        
        if hasattr(context.scene, "odc_splints"):
            if len(context.scene.odc_splints) > 0:
                splint = context.scene.odc_splints[0]
                splint.ops_string += "Place Notch " + " onto " + snap_ob.name + ":"
                
                
        if len(snap_ob.modifiers):
            old_mesh = snap_ob.data
            # settings for to_mesh
            apply_modifiers = True
            settings = 'PREVIEW'
            new_mesh = snap_ob.to_mesh(context.scene, apply_modifiers, settings)

            # object will still have modifiers, remove them
            snap_ob.modifiers.clear()
            
            # assign the new mesh to obj.data 
            snap_ob.data = new_mesh
            
            # remove the old mesh from the .blend
            bpy.data.meshes.remove(old_mesh)
            
            
        if 'Notch' in snap_ob.name:
            self.report({'ERROR'}, 'It looks like you have a notch selected, select a model or shell then place button')
            return {'CANCELLED'}
        
        if "Button Mat" not in bpy.data.materials:
            a_mat = bpy.data.materials.new('Button Mat')
            a_mat.diffuse_color = Color((0,.8,.4))
            #mat.diffuse_intensity = 1
            #mat.emit = .8
        else:
            a_mat = bpy.data.materials.get('Button Mat')
        
        
        self.notches =  [ob for ob in bpy.data.objects if "Notch" in ob.name] 
        self.nearest_notch = None
        
        me = bpy.data.meshes.new("Elastic Notch")
        ob = bpy.data.objects.new("Elastic Notch", me)
        context.scene.objects.link(ob)
        
        ob.parent = context.object
        ob.location = context.scene.cursor_location    
        me.materials.append(a_mat)
        
          
        #bme_b = generate_bmesh_elastic_notch(width =4.0, 
        #                                    total_length =6.0, 
        #                                    hook_height = 2.0, 
        #                                    base_length = 2.0, 
        #                                    base_height = 4.0)
            
        #r_x_90 = Matrix.Rotation(math.pi/2, 4, 'X')
        #bme_b.transform(r_x_90)               
        #bme_b.to_mesh(me)
        #bme_b.free()
        
        
        bme_b = generate_bmesh_elastic_notch3(length = 3, tip_diameter = .75, base_width = 1.0, depth = 3, bend = 0, tab_width=1.75)
        #extrude it out slightly move it downward so it exits the surface
        
        
        
        bme_b.to_mesh(me)
        bme_b.free()
        
        #set ID props        
        ob['length'] =  3.0
        ob['tip_diameter'] = .75
        ob['base_width'] = 1.0
        ob['depth'] = 3.0
        ob['bend'] = 0.0
        ob['tab_width'] = 1.75
        
        #mod = ob.modifiers.new('Subsurf', type = 'SUBSURF')
        #mod.levels = 2
        
        self.bracket_manager = BracketDataManager(context,snap_type ='OBJECT', 
                                                      snap_object = snap_ob, 
                                                      name = 'Notch', 
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
    
class D3SPLINT_OT_update_elastic_notch(bpy.types.Operator):
    """Edit an elastic notch"""
    bl_idname = "d3splint.elastic_notch_edit"
    bl_label = "Edit Elastic Notch"
    bl_options = {'REGISTER', 'UNDO'}
    
    hold_update =  bpy.props.BoolProperty(default = True, description = 'Pause auto update')
    bend = bpy.props.FloatProperty(default = 0, description = 'bend', min = -3.0, max = 3.0, update = update_elastic_notch)
    length = bpy.props.FloatProperty(default = 5, description = 'length of notch', update = update_elastic_notch)
    tip_diameter = bpy.props.FloatProperty(default = .75, description = 'tip diameter', update = update_elastic_notch)
    base_width = bpy.props.FloatProperty(default = 1.25, description = 'base width of notch', update = update_elastic_notch)
    depth = bpy.props.FloatProperty(default = 4, description = 'depth of cut', update = update_elastic_notch)
    tab_width = bpy.props.FloatProperty(default = 1.75, description = 'tab width', update = update_elastic_notch)
    #mode =   bpy.props.EnumProperty(name = 'New or Modify', items = (('RIGHT', 'RIGHT','RIGHT'),('LEFT','LEFT','LEFT')), defualt = 'RIGHT')                            
    @classmethod
    def poll(cls, context):
        if not context.object: return False
        if 'Notch' in context.object.name:
            return True
        
        return False
    
    def invoke(self, context, event):
        
        ob = context.object
        
        self.bend = ob['bend']
        self.base_width = ob['base_width']
        self.length = ob['length']
        self.tip_diameter = ob['tip_diameter']
        self.depth = ob['depth']
        self.tab_width = ob['tab_width']
        
        self.hold_update = False
        
        return context.window_manager.invoke_props_dialog(self)
        
    def execute(self, context):
        
        update_elastic_notch(self, context)
        
        self.hold_update = True
        
        return {'FINISHED'}     



class D3SPLINT_OT_cut_elastic_notches(bpy.types.Operator):
    """Fuse elastic buttons to their snapped object"""
    bl_idname = "d3splint.elastic_notch_cut"
    bl_label = "Cut Elastic Notches"
    bl_options = {'REGISTER', 'UNDO'}
    
    
                          
    @classmethod
    def poll(cls, context):
        #if not context.object: return False
        #if 'Ramp' in context.object.name:
        #    return True
        
        return True
        
    def execute(self, context):
        
        buttons = [ob for ob in bpy.data.objects if 'Elastic Notch' in ob.name]
        if hasattr(context.scene, "odc_splints"):
            if len(context.scene.odc_splints) > 0:
                splint = context.scene.odc_splints[0]
                splint.ops_string += "CutAllNotches:"
                
        for b in buttons:
            p = b.parent
            if not p: continue
            
            mod = p.modifiers.get(b.name)
            if mod == None:
                mod = p.modifiers.new(b.name, type = 'BOOLEAN')
                
            mod.operation = 'DIFFERENCE'
            mod.object = b
            b.hide = True
            
        return {'FINISHED'}
    
    
def register():
    bpy.utils.register_class(D3Sleep_OT_place_notch)
    bpy.utils.register_class(D3SPLINT_OT_update_elastic_notch)
    bpy.utils.register_class(D3SPLINT_OT_cut_elastic_notches)
    
    
def unregister():
    bpy.utils.unregister_class(D3Sleep_OT_place_notch)
    bpy.utils.unregister_class(D3SPLINT_OT_update_elastic_notch)
    bpy.utils.unregister_class(D3SPLINT_OT_cut_elastic_notches)

 

# ---- Perplexity API Suggested Migrations ----
To migrate your property definitions from Blender 2.79 to **Blender 4.4**, you must use the new `bpy.props` API, which now requires properties to be defined as class annotations using Python's `typing` module and the `: bpy.props.*Property(...)` syntax. The old assignment style is deprecated.

Here is the corrected code block for Blender 4.4+:

```python
import bpy
from bpy.props import BoolProperty, FloatProperty

class MyPropertyGroup(bpy.types.PropertyGroup):
    hold_update: BoolProperty(
        default=True,
        description='Pause auto update'
    )
    bend: FloatProperty(
        default=0,
        description='bend',
        min=-3.0,
        max=3.0,
        update=update_elastic_notch
    )
    length: FloatProperty(
        default=5,
        description='length of notch',
        update=update_elastic_notch
    )
    tip_diameter: FloatProperty(
        default=0.75,
        description='tip diameter',
        update=update_elastic_notch
    )
    base_width: FloatProperty(
        default=1.25,
        description='base width of notch',
        update=update_elastic_notch
    )
    depth: FloatProperty(
        default=4,
        description='depth of cut',
        update=update_elastic_notch
    )
    tab_width: FloatProperty(
        default=1.75,
        description='tab width',
        update=update_elastic_notch
    )
```

**Key changes:**
- Use **type annotations** (`:`) instead of assignment (`=`) for property definitions inside classes.
- Properties must be defined inside a class derived from `bpy.types.PropertyGroup`.
- Register your property group and assign it to a data block (e.g., `bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyPropertyGroup)`).

This is the Blender 4.4+ compatible way to define custom properties[3][4].
