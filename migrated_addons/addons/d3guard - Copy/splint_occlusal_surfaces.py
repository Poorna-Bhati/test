'''
Created on Dec 26, 2017

@author: Patrick
'''
import math
import random
import time
from collections import Counter
import numpy as np 

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bgl
import blf
import bmesh
from mathutils import Matrix, Vector, Color
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
from bpy_extras import view3d_utils
from bpy.props import BoolProperty, FloatProperty, IntProperty
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_vector_3d, region_2d_to_location_3d, region_2d_to_origin_3d

from common_drawing import draw_3d_points, draw_polyline_from_3dpoints, outline_region
from common_utilities import get_settings
from p_picker import PointPicker
from textbox import TextBox
from bmesh_curvature import points_within_radius, CuspWaterDroplet, vector_average,\
    curvature_on_mesh, calculate_plane

# Addon imports
from subtrees.metaballs.vdb_remesh import convert_vdb, read_bmesh

from submodules.pts_picker.operators.points_picker import VIEW3D_OT_points_picker
from submodules.pts_picker.addon_common.common import ui
from submodules.pts_picker.functions.common import showErrorMessage

from submodules.custom_sculpt_mode.operators import SCENE_OT_custom_sculpt_mode
from submodules.custom_sculpt_mode.addon_common.common import ui as sculpt_ui
from submodules.custom_sculpt_mode.functions.common.blender import apply_modifiers

import tracking



def get_bounds_vs(vs):
    """ brute force method for obtaining bounding box of list of vectors"""
    # initialize min and max
    min = Vector((math.inf, math.inf, math.inf))
    max = Vector((-math.inf, -math.inf, -math.inf))
    # calculate min and max verts
    for v in vs:
        if v.x > max.x:
            max.x = v.x
        elif v.x < min.x:
            min.x = v.x
        if v.y > max.y:
            max.y = v.y
        elif v.y < min.y:
            min.y = v.y
        if v.z > max.z:
            max.z = v.z
        elif v.z < min.z:
            min.z = v.z
    # set up bounding box list of coord lists
    bound_box = [[min.x, min.y, min.z],
                 [min.x, min.y, max.z],
                 [min.x, max.y, max.z],
                 [min.x, max.y, min.z],
                 [max.x, min.y, min.z],
                 [max.y, min.y, max.z],
                 [max.x, max.y, max.z],
                 [max.x, max.y, min.z]]
    return bound_box


class D3Splint_automatic_opposing_surface(bpy.types.Operator):
    """Semi Automatic and User Guided occlusal plane generator"""
    bl_idname = "d3splint.watershed_cusp_surface_finder"
    bl_label = "Automatic Opposing Cusp Surface"

    
    def draw_callback_water_drops(self, context):
        
        mx = self.ob.matrix_world
        
        draw_3d_points(context, [self.com], (1,.1,1,.5), 6)
        if not self.consensus_generated:
            for droplet in self.drops:
                vs = [mx * self.bme.verts[i].co for i in droplet.ind_path]
            
                #draw_3d_points(context, vs, (.2,.3,.8,1), 2)
                draw_3d_points(context, [vs[-1]], (1,.3,.3,1), 3)
                #draw_3d_points(context, [vs[0]], (.3,1,.3,1), 4)
        
        if self.consensus_generated:
            
            vs = [mx * self.bme.verts[i].co for i in self.consensus_list]
            draw_3d_points(context, vs, (.2,.8,.8,1), 5)
            
        if self.sorted_by_value:
            vs = [mx * self.bme.verts[i].co for i in self.best_verts]
            draw_3d_points(context, vs, (.8,.8,.2,1), 3)
        
        
        if len(self.clipped_verts):
            vs = [mx * v for v in self.clipped_verts]
            draw_3d_points(context, vs, (1,.3,1,1), 4)
            
            
        if len(self.bez_curve):
            vs = [mx * v for v in self.bez_curve]
            draw_polyline_from_3dpoints(context, vs, (.2,1,.2,1), 3)
            draw_3d_points(context, vs, (.2,1,.2,1), 5)
        #if len(self.polyline):
            #draw_polyline_from_3dpoints(context, self.polyline, (1,1,.2,1), 2)
            
        #    for i, v in enumerate(self.polyline):
        #        msg = str(i)
        #        draw_3d_text(context, v, msg, 20)
                         
    def roll_droplets(self,context):
        count_rolling = 0
        for drop in self.drops:
            #if self.splint.jaw_type == 'MANDIBLE':
            if not drop.peaked:
                drop.roll_uphill()
                count_rolling += 1
            #else:
            #    if not drop.settled:
            #        drop.roll_downhill()
            #        count_rolling += 1
                
        return count_rolling

    def build_concensus(self,context):
        
        list_inds = [drop.dn_vert.index for drop in self.drops]
        vals = [drop.dnH for drop in self.drops]
        
        
        unique = set(list_inds)
        unique_vals = [vals[list_inds.index(ind)] for ind in unique]
        
        
        print('there are %i droplets' %len(list_inds))
        print('ther are %i unique maxima' % len(unique))
    
        best = Counter(list_inds)
        
        consensus_tupples = best.most_common(self.consensus_count)
        self.consensus_list = [tup[0] for tup in consensus_tupples]
        self.consensus_dict = {}  #throw it all away?
        
        #map consensus to verts.  Later we will merge into this dict
        for tup in consensus_tupples:
            self.consensus_dict[tup[0]] = tup[1]
            
        #print(self.consensus_list)
        self.consensus_generated = True
        
    
    def sort_by_value(self,context):
        
        list_inds = [drop.dn_vert.index for drop in self.drops]
        vals = [drop.dnH for drop in self.drops]
        
        
        unique_inds = list(set(list_inds))
        unique_vals = [vals[list_inds.index(ind)] for ind in unique_inds]
        
        bme_inds_by_val = [i for (v,i) in sorted(zip(unique_vals, unique_inds))]
        self.best_verts = bme_inds_by_val[0:self.consensus_count]
        self.sorted_by_value = True
    
    
    def merge_close_consensus_points(self):
        '''
        cusps usually aren't closer than 2mm
        actually we aren't merging, we just toss the one with less votes
        '''
        
        #consensus list is sorted with most voted for locations first
        #start at back of list and work forward
        to_remove = []
        new_verts = []
        l_co = [self.bme.verts[i].co for i in self.consensus_list]
        N = len(l_co)
        for i, pt in enumerate(l_co):
            
            #if i in to_remove:
            #    continue
            
            ds, inds, vs = points_within_radius(pt, l_co, 7)
            
            if len(vs):
                new_co = Vector((0,0,0))
                for v in vs:
                    new_co += v
                new_co += pt
                new_co *= 1/(len(vs) + 1)
            else:
                new_co = pt
                
            new_verts.append(new_co)
                        
            for j in inds:
                if j > i:
                    to_remove.append(j)  
               
            
        to_remove = list(set(to_remove))
        to_remove.sort(reverse = True)
        
        print('removed %i too close consensus points' % len(to_remove))
        print(to_remove)
        for n in to_remove:
            l_co.pop(n)
            
        
        
        self.clipped_verts = new_verts
        
        return
        
    def fit_cubic_consensus_points(self):
        '''
        let i's be indices in the actual bmesh
        let j's be arbitrary list comprehension indices
        let n's be the incidices in our consensus point lists range 0,len(consensus_list)
        '''
        
        pass
    
        '''
        l_co = self.clipped_verts
        
        
        com, no = calculate_plane(l_co)  #an easy way to estimate occlusal plane
        no.normalize()
        
        
        #neigbors = set(l_co)
        box = bbox(l_co)
        
        diag = (box[1]-box[0])**2 + (box[3]-box[2])**2 + (box[5]-box[4])**2
        diag = math.pow(diag,.5)
        
        #neighbor_path = [neighbors.pop()]
        
        #establish a direction
        #n, v, d  = closest_point(neighbor_path[0], list(neighbors))
        #if d < .2 * diag:
        #    neighbor_path.append(v)
        
        #ended = Fase
        #while len(neighbors) and not ended:   
        #   n, v, d  = closest_point(neighbor_path[0], list(neighbors)
        
        #flattened spokes
        rs = [v - v.dot(no)*v - com for v in l_co]
        
        R0 = rs[random.randint(0,len(rs)-1)]
        
        theta_dict = {}
        thetas = []
        for r, v in zip(rs,l_co):
            angle = r.angle(R0)
            
            if r != R0:
                rno = r.cross(R0)
                if rno.dot(no) < 0:
                    angle *= -1
                    angle += 2 * math.pi
            
            theta_dict[round(angle,4)] = v
            thetas.append(round(angle,4))
        
        print(thetas)
        thetas.sort()
        print(thetas)
        diffs = [thetas[i]-thetas[i-1] for i in range(0,len(thetas))]
        n = diffs.index(max(diffs)) # -1
        theta_shift = thetas[n:] + thetas[:n]
        
        self.polyline = [theta_dict[theta] for theta in theta_shift]
        #inds_in_order = [theta_dict[theta] for theta in thetas]
        #self.polyline = [l_co[i] for i in inds_in_order]
        
        self.com = com

        l_bpts = cubic_bezier_fit_points(self.polyline, 1, depth=0, t0=0, t3=1, allow_split=True, force_split=False)
        self.bez_curve = []
        N = 20
        for i,bpts in enumerate(l_bpts):
            t0,t3,p0,p1,p2, p3 = bpts
            

            new_pts = [cubic_bezier_blend_t(p0,p1,p2,p3,i/N) for i in range(0,N)]
            
            self.bez_curve.extend(new_pts)  
    '''         

    def invoke(self,context, event):
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        if splint.jaw_type == 'MAXILLA':
            opposing = splint.get_mandible()
        else:
            opposing = splint.get_maxilla()
        
        #models need to be fairly mounted with local Z alligned to occluasl plane
        
        ob = bpy.data.objects.get(opposing)
        
        if not ob:
            self.report({'ERROR'},'Opposing object not indicated')
            return {'CANCELLED'}
    
        self.ob = ob  
        self.bme = bmesh.new()
        self.bme.from_mesh(ob.data)
        self.bme.verts.ensure_lookup_table()
        self.bme.faces.ensure_lookup_table()
        
        print("starting curvature calclation")
        start = time.time()
        if 'max_curve' not in self.bme.verts.layers.float:
            curvature_on_mesh(self.bme)
        
        print('tootk %f seconds to put curvature' % (time.time() - start))
        curv_id = self.bme.verts.layers.float['max_curve']
        
        #let's roll 10000 water droplets
        #sample = 10000 / len(self.bme.verts)
        #rand_sample = list(set([random.randint(0,len(self.bme.verts)-1) for i in range(math.floor(sample * len(self.bme.verts)))]))
        #sel_verts = [self.bme.verts[i] for i in rand_sample]
        
        sel_verts = random.sample(self.bme.verts[:], 10000)
        
        
        
        if splint.jaw_type == 'MANDIBLE':
            pln_no = Vector((0,0,1))
        else:
            pln_no = Vector((0,0,-1))
        
        pln_pt = Vector((0,0,0)) - 10 * pln_no
        
        self.drops = [CuspWaterDroplet(v, pln_pt, pln_no, curv_id) for v in sel_verts]
        
        self.consensus_count = 20
        self.consensus_list = []
        self.consensus_dict = {}
        self.consensus_generated = False
        self.bez_curve = []
        self.polyline = []
        self.clipped_verts = []
        self.com = self.ob.location
        
        
        self.best_verts = []
        self.sorted_by_value = False
        
        self._handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_water_drops, (context,), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
    
        return {'RUNNING_MODAL'}
    
    def modal(self,context,event):
        context.area.tag_redraw()
        
        if event.type == 'RET' and event.value == 'PRESS':
            for drop in self.drops:
                for i in drop.ind_path:
                    self.bme.verts[i].select = True
            
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self.bme.to_mesh(self.ob.data)
            self.bme.free()
            
            return {'FINISHED'}
          
        
        
        elif event.type == 'Q' and event.value == 'PRESS':
            n_rolling = self.roll_droplets(context)
            
            iters = 0
            while n_rolling > 5 and iters < 400:
                n_rolling = self.roll_droplets(context)
                iters += 1
                
            if iters >= 399:
                print('too much rolling')    
            
            self.consensus_count = 20    
            self.build_concensus(context)
            
            l_co = [self.bme.verts[i].co for i in self.consensus_list]
            test_no = vector_average([self.bme.verts[i].normal for i in self.consensus_list])
            test_no.normalize()
            pt, pno = calculate_plane(l_co)
            
            
            if pno.dot(test_no) < 0:
                pno *= -1
            
            self.pln_pt = pt - 5*pno
            self.pln_no = pno
                
            mx = self.ob.matrix_world
            imx = mx.inverted()
            no_mx = mx.transposed().inverted().to_3x3()
            
            
            Z = no_mx * pno
            loc = mx * pt - 5 * Z
            
            ob_y = no_mx * Vector((0,1,0))
            X = ob_y.cross(Z)
            Y = Z.cross(X)
            
            Z.normalize()
            Y.normalize()
            X.normalize()
            
            wmx = Matrix.Identity(4)
            wmx[0][0], wmx[1][0], wmx[2][0] = X[0], X[1], X[2]
            wmx[0][1], wmx[1][1], wmx[2][1] = Y[0], Y[1], Y[2]
            wmx[0][2], wmx[1][2], wmx[2][2] = Z[0], Z[1], Z[2]
            wmx[0][3], wmx[1][3], wmx[2][3] = loc[0], loc[1], loc[2]
            
            #circ_bm = bmesh.new()
            #bmesh.ops.create_circle(circ_bm, cap_ends = True, cap_tris = False, segments = 10, diameter = .5 *min(context.object.dimensions) + .5 *max(context.object.dimensions))
            
            # Finish up, write the bmesh into a new mesh
            #me = bpy.data.meshes.new("Occlusal Plane")
            #circ_bm.to_mesh(me)
            #circ_bm.free()

            # Add the mesh to the scene
            #scene = bpy.context.scene
            #obj = bpy.data.objects.new("Object", me)
            #scene.objects.link(obj)
            #obj.matrix_world = wmx
            return {'RUNNING_MODAL'}
        
        
        elif event.type == 'W' and event.value == 'PRESS':
            curv_id = self.bme.verts.layers.float['max_curve']
            
            start = time.time()
            cut_geom = self.bme.faces[:] + self.bme.verts[:] + self.bme.edges[:]
            bmesh.ops.bisect_plane(self.bme, geom = cut_geom, dist = .000001, plane_co = self.pln_pt, plane_no = self.pln_no, use_snap_center = False, clear_outer=False, clear_inner=True)
            self.bme.verts.ensure_lookup_table()
            self.bme.faces.ensure_lookup_table()
            
            
            rand_sample = list(set([random.randint(0,len(self.bme.verts)-1) for i in range(math.floor(.2 * len(self.bme.verts)))]))
            self.drops = [CuspWaterDroplet(self.bme.verts[i], self.pln_pt, self.pln_no, curv_id) for i in rand_sample]
            dur = time.time() - start
            print('took %f seconds to cut the mesh and generate drops' % dur)
            
            start = time.time()
            n_rolling = self.roll_droplets(context)
            iters = 0
            while n_rolling > 10 and iters < 100:
                n_rolling = self.roll_droplets(context)
                iters += 1
            
            self.consensus_count = 80
            self.build_concensus(context)
            
            dur = time.time() - start
            print('took %f seconds to roll the drops' % dur)
            return {'RUNNING_MODAL'}
               
        elif event.type == 'UP_ARROW' and event.value == 'PRESS':
            n_rolling = self.roll_droplets(context)
            
            iters = 0
            while n_rolling > 10 and iters < 100:
                n_rolling = self.roll_droplets(context)
                iters += 1
            return {'RUNNING_MODAL'}
        
        
        elif event.type == 'LEFT_ARROW' and event.value == 'PRESS':
            self.consensus_count -= 5
            self.build_concensus(context)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'RIGHT_ARROW' and event.value == 'PRESS':
            self.consensus_count += 5
            self.build_concensus(context)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'C' and event.value == 'PRESS':
            self.build_concensus(context) 
            return {'RUNNING_MODAL'}
        
        elif event.type == 'M' and event.value == 'PRESS':
            self.merge_close_consensus_points()
            return {'RUNNING_MODAL'}
            
        elif event.type == 'B' and event.value == 'PRESS' and self.consensus_generated:
            self.fit_cubic_consensus_points()
            return {'RUNNING_MODAL'}
            
        elif event.type == 'S' and event.value == 'PRESS':
            self.sort_by_value(context)
            return {'RUNNING_MODAL'}
                   
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self.bme.to_mesh(self.ob.data)
            self.bme.free()
            return {'CANCELLED'}
        else:
            return {'PASS_THROUGH'}
        

def landmarks_draw_callback(self, context):  
    self.crv.draw(context)
    self.help_box.draw()    
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    outline_region(context.region,(r,g,b,1))  
    
    
class D3SPLINT_OT_splint_manual_auto_surface(bpy.types.Operator):
    """Help make a nice flat plane"""
    bl_idname = "d3splint.splint_manual_flat_plane"
    bl_label = "Define Occlusal Contacts"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls,context):
        return True
    
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

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            x, y = event.mouse_region_x, event.mouse_region_y
            self.crv.click_add_point(context, x,y, label = None)
            return 'main'
        
            
        #if event.type == 'MOUSEMOVE':
        #    self.crv.hover(context, event.mouse_region_x, event.mouse_region_y)   
        #TODO, right click to delete misfires
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            self.crv.hover(context, event.mouse_region_x, event.mouse_region_y)
            self.crv.click_delete_point()
            self.crv.selected = -1
            self.crv.hovered = [None, None]
            return 'main'
            
        if event.type == 'RET' and event.value == 'PRESS':
            self.finish(context)
            return 'finish'
            
        elif event.type == 'ESC' and event.value == 'PRESS':
            return 'cancel' 

        return 'main'
    
        
    def modal(self, context, event):
        context.area.tag_redraw()
        
        FSM = {}    
        FSM['main']    = self.modal_main
        FSM['nav']     = self.modal_nav
        
        nmode = FSM[self.mode](context, event)
        
        if nmode == 'nav': 
            return {'PASS_THROUGH'}
        
        if nmode in {'finish','cancel'}:
            #context.space_data.show_manipulator = True
            
            if nmode == 'finish':
                context.space_data.transform_manipulators = {'TRANSLATE', 'ROTATE'}
            else:
                context.space_data.transform_manipulators = {'TRANSLATE'}
            #clean up callbacks
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'} if nmode == 'finish' else {'CANCELLED'}
        
        if nmode: self.mode = nmode
        
        return {'RUNNING_MODAL'}

    def invoke(self,context, event):
        n = context.scene.odc_splint_index
        self.splint = context.scene.odc_splints[n]    
        
        if self.splint.jaw_type == 'MANDIBLE':
            model = self.splint.get_maxilla()
        else:
            model = self.splint.get_mandible()
        
        
        if model == '' or model not in bpy.data.objects:
            self.report({'ERROR'}, "Need to mark the Upper and Lower model first!")
            return {'CANCELLED'}
            
        
        context.scene.frame_set(0)
        context.scene.frame_set(0)
        Model = bpy.data.objects[model]
            
        for ob in bpy.data.objects:
            ob.select = False
            
            if ob != Model:
                ob.hide = True
        Model.select = True
        Model.hide = False
        context.scene.objects.active = Model
        
        if self.splint.jaw_type == 'MAXILLA':
            bpy.ops.view3d.viewnumpad(type = 'TOP')
        
        else:
            bpy.ops.view3d.viewnumpad(type = 'BOTTOM')
        
        bpy.ops.view3d.view_selected()
        self.crv = PointPicker(context,snap_type ='OBJECT', snap_object = Model)
        context.space_data.show_manipulator = False
        context.space_data.transform_manipulators = {'TRANSLATE'}
        v3d = bpy.context.space_data
        v3d.pivot_point = 'MEDIAN_POINT'
        
        
        #TODO, tweak the modifier as needed
        help_txt = "Designate Posterior Contacts\n LeftClick on posterior cusp tips that will have light contact in CR/MIP bite \n Right click on a point to delete it \n A smooth surface will be generated between all ponts \n This surface will then be used to slice off the posterior rim"
        self.help_box = TextBox(context,500,500,300,200,10,20,help_txt)
        self.help_box.snap_to_corner(context, corner = [1,1])
        self.mode = 'main'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(landmarks_draw_callback, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self) 
        return {'RUNNING_MODAL'}

    def finish(self, context):
        #ray cast the entire grid into
        
        if 'Posterior Plane' in bpy.data.objects:
            Plane = bpy.data.objects['Posterior Plane']
            Plane.hide = False
                
        else:
            me = bpy.data.meshes.new('Posterior Plane')
            Plane = bpy.data.objects.new('Posterior Plane', me)
            context.scene.objects.link(Plane)
        
        
        pbme = bmesh.new()
        pbme.verts.ensure_lookup_table()
        pbme.edges.ensure_lookup_table()
        pbme.faces.ensure_lookup_table()
        bmesh.ops.create_grid(pbme, x_segments = 200, y_segments = 200, size = 39.9)
        pbme.to_mesh(Plane.data)
        
        pt, pno = calculate_plane(self.crv.b_pts)
        
        if self.splint.jaw_type == 'MANDIBLE':
            Zw = Vector((0,0,-1))
            Xw = Vector((1,0,0))
            Yw = Vector((0,-1,1))
            
        else:
            Zw = Vector((0,0,1))
            Xw = Vector((1,0,0))
            Yw = Vector((0,1,0))
            
        Z = pno
        Z.normalize()
        
        if Zw.dot(Z) < 0:
            Z *= -1
            
        Y = Z.cross(Xw)
        X = Y.cross(Z)
            
        
        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
        
        R = R.to_4x4()
        T = Matrix.Translation(pt - 5 * Z)
        
        Plane.matrix_world = T * R
    
        pmx = Plane.matrix_world
        ipmx = pmx.inverted()
        
        bme_pln = bmesh.new()
        bme_pln.from_mesh(Plane.data)
        bme_pln.verts.ensure_lookup_table()
        bme_pln.edges.ensure_lookup_table()
        bme_pln.faces.ensure_lookup_table()
        bvh = BVHTree.FromBMesh(bme_pln)
        
        
        #we are going to raycast the user world coordinate points
        #into a grid, and identify all points in the grid from the local Z direction
        #Then we will store the local location of the user picked coordinate in a dictionary
        key_verts = {}
        
        for loc in self.crv.b_pts:

            res = bvh.ray_cast(ipmx * loc, -Z, 30)
            if res[0] != None:
                
                f = bme_pln.faces[res[2]]
                for v in f.verts:
                    key_verts[v] = ipmx * loc
                    v.select_set(True)
                
                continue
            
            res = bvh.ray_cast(ipmx * loc, Z, 30)
            if res[0] != None:
                
                f = bme_pln.faces[res[2]]
                for v in f.verts:
                    key_verts[v] = ipmx * loc
                    v.select_set(True)
                
                continue
        
        #bme_pln.to_mesh(Plane.data)
        #bme_pln.free()
        #return
        kdtree = KDTree(len(key_verts))
        for v in key_verts.keys():
            kdtree.insert(v.co, v.index)
        
        kdtree.balance()
        
        #raycast  the shell if we can
        raycast_shell = False
        if 'Splint Shell' in bpy.data.objects:
            shell = bpy.data.objects.get('Splint Shell')
            bvh_shell = BVHTree.FromObject(shell, context.scene)
            mx_shell = shell.matrix_world
            imx_shell = mx_shell.inverted()
            Z_shell = imx_shell.to_3x3()*Z
            raycast_shell = True
            
        
        right_side = set()
        left_side = set()
        ray_casted = set()
        
        to_delete = set()
        
        for v in bme_pln.verts:
            if v in key_verts:
                v.co[2] = key_verts[v][2]
               
                if v.co[1] > 0:
                    left_side.add(v)
                else:
                    right_side.add(v)
                continue
                
            results = kdtree.find_range(v.co, .5)
            if len(results):
                N = len(results)
                r_total = 0
                v_new = Vector((0,0,0))
                for res in results:
                    r_total += 1/res[2]
                    v_new += (1/res[2]) * key_verts[bme_pln.verts[res[1]]]
                        
                v_new *= 1/r_total
                v.co[2] = v_new[2]
                if v.co[1] > 0:
                    left_side.add(v)
                else:
                    right_side.add(v)
                continue
                        
            results = kdtree.find_range(v.co, 6)
            if len(results):
                N = len(results)
                r_total = 0
                v_new = Vector((0,0,0))
                for res in results:
                    r_total += (1/res[2])**2
                    v_new += ((1/res[2])**2) * key_verts[bme_pln.verts[res[1]]]
                        
                v_new *= 1/r_total
                v.co[2] = v_new[2]
                if v.co[1] > 0:
                    left_side.add(v)
                else:
                    right_side.add(v)
                continue
            
            loc, no, index, d = bvh_shell.ray_cast(imx_shell * pmx * v.co, Z_shell)
            if loc:
                
                ray_casted.add(v)
                results = kdtree.find_n(v.co, 4)
                N = len(results)
                r_total = 0
                v_new = Vector((0,0,0))
                for res in results:
                    r_total += (1/res[2])**2
                    v_new += ((1/res[2])**2) * key_verts[bme_pln.verts[res[1]]]
                        
                v_new *= 1/r_total
                v.co[2] = v_new[2]
                continue

        total_verts = ray_casted | left_side | right_side
        
        ant_left = max(left_side, key = lambda x: x.co[0])
        ant_right = max(right_side, key = lambda x: x.co[0])
        
        new_verts = set()
        dilation_verts = set()  
        for v in total_verts:
            for ed in v.link_edges:
                v_new = ed.other_vert(v)
                if v_new in total_verts or v_new in new_verts: 
                    continue
                else:
                    new_verts.add(v_new)
                    
        print('adding %i new verts' % len(new_verts))
        
        
        total_verts.update(new_verts)
        dilation_verts.update(new_verts)
        
        #for v in ray_casted:
        #    if v.co[1] > 0:
        #        if v.co[0] > ant_left.co[0]:
        #            to_delete.add(v)
        #    else:
        #        if v.co[0] > ant_right.co[0]:
        #            to_delete.add(v)
        
        #print('added %i ray_casted' % len(ray_casted))
        #total_verts = ray_casted | left_side | right_side
        #total_verts.difference_update(to_delete)       
        
        #new_verts = set()   
        #for v in total_verts:
        #    for ed in v.link_edges:
        #        v_new = ed.other_vert(v)
        #        if v_new in total_verts: continue
                
        #        if v_new.co[1] > 0 and v_new.co[0] < ant_left.co[0]:
        #            if v in to_delete:
        #                new_verts.add(v)
        #        if v_new.co[1] <= 0 and v_new.co[0] < ant_right.co[0]:
        #            if v in to_delete:
        #                new_verts.add(v)   
        
        #to_delete.difference_update(new_verts)
        
        #print('adding %i new verts' % len(new_verts))   
        for j in range(0,3):
            newer_verts = set()  
            for v in new_verts:
                for ed in v.link_edges:
                    v_new = ed.other_vert(v)
                    if v_new in total_verts or v_new in newer_verts:
                        continue
                     
                    newer_verts.add(v_new)
                    
            
                       
            total_verts.update(newer_verts)
            dilation_verts.update(newer_verts)
            new_verts = newer_verts
        
        to_delete = set(bme_pln.verts[:]) - total_verts
        
        #filter out anteior dilation
        for v in dilation_verts:
            
            if v.co[1] > 0 and v.co[0] > ant_left.co[0]:
                to_delete.add(v)
                continue
            if v.co[1] <= 0 and v.co[0] > ant_right.co[0]:
                to_delete.add(v)
                continue
                
             
            results = kdtree.find_n(v.co, 4)
            N = len(results)
            r_total = 0
            v_new = Vector((0,0,0))
            for res in results:
                r_total += (1/res[2])**2
                v_new += ((1/res[2])**2) * key_verts[bme_pln.verts[res[1]]]
                        
            v_new *= 1/r_total
            v.co[2] = v_new[2]
            
        #filter out anteior dilation
        for v in ray_casted:
            if v.co[1] > 0 and v.co[0] > ant_left.co[0]:
                to_delete.add(v)
                continue
            if v.co[1] <= 0 and v.co[0] > ant_right.co[0]:
                to_delete.add(v)
                continue
                            
        bmesh.ops.delete(bme_pln, geom = list(to_delete), context = 1)
        bme_pln.to_mesh(Plane.data)
        Plane.data.update()
        
        smod = Plane.modifiers.new('Smooth', type = 'SMOOTH')
        smod.iterations = 5
        smod.factor = 1
        
        self.splint.ops_string += 'Mark Posterior Cusps:'
        #tracking.trackUsage("D3Splint:SplintManualSurface",None)

class D3SPLINT_OT_splint_subtract_posterior_surface(bpy.types.Operator):
    """Subtract Posterior Surface from Shell"""
    bl_idname = "d3splint.subtract_posterior_surface"
    bl_label = "Subtract Posterior Surface from Shell"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    #sculpt to
    sculpt_to = bpy.props.BoolProperty(default = False, description = "Not only remove but pull some of the shell down to touch")
    snap_limit = bpy.props.FloatProperty(default = 2.0, min = .25, max = 5.0, description = "Max distance the shell will snap to")
    remesh = bpy.props.BoolProperty(default = True, description = "Not only remove but pull some of the shell down to touch")
    @classmethod
    def poll(cls, context):
        if 'Posterior Plane' not in bpy.data.objects: return False
        return True
    
    def execute(self, context):
        
        if not len(context.scene.odc_splints):
            self.report({'ERROR'}, 'Need to start a splint by setting model first')
            return {'CANCELLED'}
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        Model = bpy.data.objects.get(splint.model)
        Shell = bpy.data.objects.get('Splint Shell')
        Plane = bpy.data.objects.get('Posterior Plane')

        
        if Shell == None:
            self.report({'ERROR'}, 'Need to calculate splint shell first')
            return {'CANCELLED'}
        if Plane == None:
            self.report({'ERROR'}, 'Need to generate functional surface first')
            return {'CANCELLED'}
        
        if len(Shell.modifiers):
            old_data = Shell.data
            new_data = Shell.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
            
            Shell.modifiers.clear() 
            Shell.data = new_data
            bpy.data.meshes.remove(old_data)
        
        if "Minimum Thickness" in bpy.data.objects:
            MinModel = bpy.data.objects.get("Minimum Thickness")
        else:
            MinModel = None
            
        old_mode = context.mode
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
                
        high_verts = []
        bme = bmesh.new()
        bme.from_mesh(Plane.data)
        bme.verts.ensure_lookup_table()
        
        if MinModel:
            bvh  = BVHTree.FromObject(MinModel, context.scene)
        else:
            bvh  = BVHTree.FromObject(Model, context.scene)
        
        mx_p = Plane.matrix_world
        imx_p = mx_p.inverted()
        
        mx_m = Model.matrix_world
        imx_m = mx_m.inverted()
        
        mx_s = Shell.matrix_world
        imx_s = mx_s.inverted()
        
        if splint.jaw_type == 'MAXILLA':
            Z = Vector((0,0,1))
        else:
            Z = Vector((0,0,-1))
            
        for v in bme.verts:
            ray_orig = mx_p * v.co
            ray_target = mx_p * v.co - 5 * Z
            ray_target2 = mx_p * v.co + .8 * Z
            
            loc, no, face_ind, d = bvh.ray_cast(imx_m * ray_orig, imx_m * ray_target - imx_m*ray_orig, 5)
        
            if loc:
                high_verts += [v]
                if MinModel:
                    v.co = imx_p * mx_m * loc
                else:
                    v.co = imx_p * (mx_m * loc - 0.8 * Z)
            else:
                loc, no, face_ind, d = bvh.ray_cast(imx_m * ray_orig, imx_m * ray_target2 - imx_m*ray_orig, .8)
                if loc:
                    high_verts += [v]
                    v.co = imx_p * (mx_m * loc - 0.8 * Z)
        
        if len(high_verts):
            self.report({'WARNING'}, 'Sweep surface intersected upper model, corrected it for you!')
            
            mat = bpy.data.materials.get("Bad Material")
            if mat is None:
                # create material
                mat = bpy.data.materials.new(name="Bad Material")
                mat.diffuse_color = Color((1,.3, .3))
        
                Plane.data.materials.append(mat)
            
            for v in high_verts:
                for f in v.link_faces:
                    f.material_index = 1
            bme.to_mesh(Plane.data)
            
        
        print('We did the ray casting for the model')
        bme.free()
        Plane.data.update()
        context.scene.update()
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        

        #Do a manual ray cast to the underlying data...use BVH in future?
        sbme = bmesh.new()
        sbme.from_mesh(Shell.data)
        sbme.verts.ensure_lookup_table()
        
        print('got the shell data')
        n_ray_casted = 0
        for v in sbme.verts:
            ray_orig = mx_s * v.co
            ray_target = mx_s * ( v.co + 5 * Z )
            ray_target2 = mx_s * (v.co - self.snap_limit * Z)
            ok, loc, no, face_ind = Plane.ray_cast(imx_p * ray_orig, imx_p * ray_target - imx_p*ray_orig)
            
            if ok:
                v.co = imx_s * (mx_p * loc)
                n_ray_casted += 1
                
            if self.sculpt_to:
                if abs(v.normal.dot(Z)) < .2: continue
                
                
                ok, loc, no, face_ind = Plane.ray_cast(imx_p * ray_orig, imx_p * ray_target2 - imx_p*ray_orig, distance = self.snap_limit)
                if ok:
                    v.co = imx_s * (mx_p * loc)
                    n_ray_casted += 1
                    
        sbme.to_mesh(Shell.data)
        Shell.data.update()
                
        Plane.hide = True
        Shell.hide = False
        Model.hide = False
        
        if self.remesh:
            context.scene.objects.active = Shell
            Shell.select = True
            bpy.ops.object.mode_set(mode = 'SCULPT')
            if not Shell.use_dynamic_topology_sculpting:
                bpy.ops.sculpt.dynamic_topology_toggle()
            context.scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
            context.scene.tool_settings.sculpt.constant_detail_resolution = 2
            bpy.ops.sculpt.detail_flood_fill()
            bpy.ops.object.mode_set(mode = 'OBJECT')
        
        
        if old_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = old_mode)
        
        splint.ops_string += 'SubtractPosteriorSurface:'
        splint.subtract_posterior_surface = True
        return {'FINISHED'}


args_dict = {}
args_dict['TOP'] = 'Splint Shell_MAX'
args_dict['BOTTOM'] = 'Splint Shell_MAND'
args_dict['SURFACE'] = 'Inter Arch Surface'

class D3DUAL_OT_appliance_subtract_surface(bpy.types.Operator):
    """Subtract Opposing"""
    bl_idname = "d3dual.subtract_occlusal_surface"
    bl_label = "Subtract Surface from Shell"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    #sculpt to
    sculpt_to = bpy.props.BoolProperty(default = False, description = "Not only remove but pull some of the shell down to touch")
    snap_limit = bpy.props.FloatProperty(default = 2.0, min = .25, max = 5.0, description = "Max distance the shell will snap to")
    remesh = bpy.props.BoolProperty(default = True, description = "Remesh Afterward")
    
    operations = ['TOP_FROM_BOTTOM', 'BOTTOM_FROM_TOP', 'SURFACE_FROM_TOP', 'SURFACE_FROM_BOTTOM', 'SURFACE_FROM_BOTH']
    mode_items = []
    for m in operations:
        mode_items += [(m, m, m)]
        
    operation = bpy.props.EnumProperty(name = 'Subtract Mode', items = mode_items, default = 'SURFACE_FROM_BOTH') 
    
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_props_dialog(self, width = 300)
    
    
    def execute(self, context):
        
        if not len(context.scene.odc_splints):
            self.report({'ERROR'}, 'Need to start a splint by setting model first')
            return {'CANCELLED'}
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        
        
        args = self.operation.split('_FROM_')
        
        subtrahend = args[0]
        minuend = args[1]
        models = []
        
        Opposing = bpy.data.objects.get(args_dict[subtrahend])
        
        if minuend != 'BOTH':
            models = [bpy.data.objects.get(args_dict[minuend])]
        else:
            models = [bpy.data.objects.get(args_dict['TOP']),
                      bpy.data.objects.get(args_dict['BOTTOM'])
                      ] 
        
        
        
        if None in models:
            self.report({'ERROR'}, 'Need to calculate splint shell first')
            return {'CANCELLED'}
        
      
        if Opposing == None:
            self.report({'ERROR'}, '{} is missing'.format(subtrahend))
            return {'CANCELLED'}
            
        
        bme = bmesh.new()
        bme.from_mesh(Opposing.data) #no modifiers
        bvh = BVHTree.FromBMesh(bme)
        
        for Shell in models:
            if len(Shell.modifiers):
                old_data = Shell.data
                new_data = Shell.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
                
                for mod in Shell.modifiers:
                    Shell.modifiers.remove(mod)
                
                Shell.data = new_data
                bpy.data.meshes.remove(old_data)
            
            old_mode = context.mode
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode = 'OBJECT')
            bme = bmesh.new()
            bme.from_mesh(Opposing.data)
            bme.verts.ensure_lookup_table()
            
            
            
            mx_p = Opposing.matrix_world
            imx_p = mx_p.inverted()
            
            mx_s = Shell.matrix_world
            imx_s = mx_s.inverted()
            
            if 'MAX' in Shell.name:
                Z = Vector((0,0,1))
            else:
                Z = Vector((0,0,-1))
                
    
            #Do a manual ray cast to the underlying data...use BVH in future?
            sbme = bmesh.new()
            sbme.from_mesh(Shell.data)
            sbme.verts.ensure_lookup_table()
            
            print('got the shell data')
            n_ray_casted = 0
            for v in sbme.verts:
                ray_orig = mx_s * v.co
                ray_target = mx_s * ( v.co + 5 * Z )
                ray_target2 = mx_s * (v.co - self.snap_limit * Z)
                loc, no, face_ind, d = bvh.ray_cast(imx_p * ray_orig, imx_p * ray_target - imx_p*ray_orig)
                
                if loc:
                    v.co = imx_s * (mx_p * loc)
                    n_ray_casted += 1
                    
                if self.sculpt_to:
                    if abs(v.normal.dot(Z)) < .2: continue
                    
                    
                    loc, no, face_ind, d = bvh.ray_cast(imx_p * ray_orig, imx_p * ray_target2 - imx_p*ray_orig, distance = self.snap_limit)
                    if loc:
                        v.co = imx_s * (mx_p * loc)
                        n_ray_casted += 1
              
            verts, tris, quads = read_bmesh(sbme)
            vdb_base = convert_vdb(verts, tris, quads, .2)  
            isosurface = 0.0  #self.iso
            adaptivity = 0.0  #self.adapt
            isosurface *= vdb_base.transform.voxelSize()[0]            
            ve, tr, qu = vdb_base.convertToPolygons(isosurface, (adaptivity/100.0)**2)
            
            bm = bmesh.new()
            for co in ve.tolist():
                bm.verts.new(co)
    
            bm.verts.ensure_lookup_table()    
            bm.faces.ensure_lookup_table()    
    
            for face_indices in tr.tolist() + qu.tolist():
                bm.faces.new(tuple(bm.verts[index] for index in reversed(face_indices)))
    
            bm.normal_update()
            bm.to_mesh(Shell.data)
            bm.free()
            sbme.free()
            Shell.data.update()
            Shell.hide = False
                
        #Opposing.hide = True
        

        
        
        if context.mode != old_mode:
            bpy.ops.object.mode_set(mode = old_mode)
            
            
        splint.ops_string += 'Subtract {}:'.format(self.operation)
        #tracking.trackUsage("D3DUAL:MIPBite", param = None, background = True)
        return {'FINISHED'}
    
class D3DUAL_OT_transform_arch_surface(bpy.types.Operator):
    """Transform Inter Arch Surface"""
    bl_idname = "d3dual.transform_arch_surface"
    bl_label = "Adjust Inter Arch Surface"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return "Inter Arch Surface" in bpy.data.objects

    
    def execute(self, context):
        
        for ob in bpy.data.objects:
            ob.select = False
            
        plane = bpy.data.objects.get('Inter Arch Surface')
        plane.select = True
        plane.hide = False
        context.scene.objects.active = plane
        
        context.space_data.show_manipulator = True
        context.space_data.transform_manipulators = {'TRANSLATE', 'ROTATE'}
        
        
        
        return {'FINISHED'}
    
    
    
class D3SPLINT_OT_cookie_cutter_points(VIEW3D_OT_points_picker):
    """ Click on the posterior contacts """
    bl_idname = "d3splint.mark_posterior_contacts"
    bl_label = "Mark Posterior Contacts"
    bl_description = "Indicate points to generate a smooth surface to subtract"

    #############################################
    # overwriting functions from wax drop

    @classmethod
    def can_start(cls, context):
        """ Start only if editing a mesh """
        
        return True

    def start_pre(self):
        n = self.context.scene.odc_splint_index
        self.splint = self.context.scene.odc_splints[n]    
        
        if self.splint.jaw_type == 'MANDIBLE':
            model = self.splint.get_maxilla()
        else:
            model = self.splint.get_mandible()
        
        
        if model == '' or model not in bpy.data.objects:
            self.report({'ERROR'}, "Need to mark the Upper and Lower model first!")
            return {'CANCELLED'}
            
        
        self.context.scene.frame_set(0)
        self.context.scene.frame_set(0)
        Model = bpy.data.objects[model]
            
        for ob in bpy.data.objects:
            ob.select = False
            
            if ob != Model:
                ob.hide = True
        Model.select = True
        Model.hide = False
        self.context.scene.objects.active = Model
        
        if self.splint.jaw_type == 'MAXILLA':
            bpy.ops.view3d.viewnumpad(type = 'TOP')
        
        else:
            bpy.ops.view3d.viewnumpad(type = 'BOTTOM')
        
    
        self.plane_calced_successfully = False
        
        
    def next(self):
        
        if len(self.b_pts) < 5:
            showErrorMessage("You have not marked enough points to calculate a plane!")
            return
        
        if not self.plane_calced_successfully:
            showErrorMessage("Add points until a posterior surface appears")
            return
        
        self.done()
        
            
        
    def end_commit(self):
        """ Commit changes to mesh! """
        
        print('setting mark posterior contacts true')
        n = bpy.context.scene.odc_splint_index
        splint = bpy.context.scene.odc_splints[n]      
        splint.mark_post_contact = True  
        
        
        bpy.ops.d3splint.posterior_surface_trimmer("INVOKE_DEFAULT")
        shell = bpy.data.objects.get('Splint Shell')
        if shell:
            shell.show_transparent = False
        
        
        return

                
                  
    def getLabel(self, idx):
        return "P %(idx)s" % locals()

    # def ui_setup(self):
    #     # UI Box functionality
    #     # NONE!
    #
    #     # Instructions
    #     self.instructions = {
    #         "add": "Press left-click to add or select a point",
    #         "grab": "Hold left-click on a point and drag to move it along the surface of the mesh",
    #         "remove": "Press 'ALT' and left-click to remove a point",
    #     }
    #
    #     # Help Window
    #     info = self.wm.create_window('Points Picker Help', {'pos':9, 'movable':True})#, 'bgcolor':(0.30, 0.60, 0.30, 0.90)})
    #     info.add(ui.UI_Label('Instructions', align=0, margin=4))
    #     self.inst_paragraphs = [info.add(ui.UI_Markdown('', min_size=(200,10))) for i in range(3)]
    #     #for i in self.inst_paragraphs: i.visible = False
    #     self.set_ui_text()
    #
    #     # Tools Window
    #     win_tools = self.wm.create_window('Points Picker Tools', {'pos':7, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})
    #     segmentation_container = win_tools.add(ui.UI_Container())
    #     segmentation_container.add(ui.UI_Button('Set Replacement Point', self.set_replacement_point, align=0))
    #     segmentation_container.add(ui.UI_Button('Commit', self.done, align=0))
    #     segmentation_container.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), align=0))

    #############################################
    # additional functions



    def get_matrix_world_for_point(self, pt):
       
        if pt.label == "Replacement Point":
            #Z = pt.view_direction * Vector((0,0,1))  #TODO until pt.view_direction is not a quaternion
            Z = -pt.view_direction
        else:
            Z = pt.surface_normal
           
        x_rand = Vector((random.random(), random.random(), random.random()))
        x_rand.normalize()

        if abs(x_rand.dot(Z)) > .9:
            x_rand = Vector((random.random(), random.random(), random.random()))
            x_rand.normalize()
        X = x_rand - x_rand.dot(Z) * Z
        X.normalize()

        Y = Z.cross(X)

        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
        R = R.to_4x4()

        if pt.label == "Replacement Point":
            T = Matrix.Translation(pt.location + 2 * Z)
        else:
            T = Matrix.Translation(pt.location)

        return T * R
    #############################################

    def move_point_post(self, pt):
        
        if len(self.b_pts) < 5: return
        bbox = get_bounds_vs([p.location for p in self.b_pts])          
        dims = Vector(bbox[6]) - Vector(bbox[0])
        
        if not all([dims[i] > 10 for i in range(0,2)]):
            print(dims)
            return
        
        self.calc_plane()

    def calc_plane(self):
        
        if len(self.b_pts) < 3: return
        
        
        bbox = get_bounds_vs([p.location for p in self.b_pts])          
        dims = Vector(bbox[6]) - Vector(bbox[0])
        
        if not all([dims[i] > 10 for i in range(0,2)]):
            print(dims)
            showErrorMessage('Need large distribution of points')
            return
        
        pt, pno = calculate_plane([p.location for p in self.b_pts])
        
            
        if 'Posterior Plane' in bpy.data.objects:
            Plane = bpy.data.objects['Posterior Plane']
            Plane.hide = False
            Plane.modifiers.clear()
                
        else:
            me = bpy.data.meshes.new('Posterior Plane')
            Plane = bpy.data.objects.new('Posterior Plane', me)
            self.context.scene.objects.link(Plane)
        
        Plane.show_transparent = True
        
        mat = bpy.data.materials.get("Blockout Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Blockout Material")
            mat.diffuse_color = Color((0.8, .1, .1))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
        
        if mat.name not in Plane.data.materials:
            Plane.data.materials.append(mat)
            
        pbme = bmesh.new()
        pbme.verts.ensure_lookup_table()
        pbme.edges.ensure_lookup_table()
        pbme.faces.ensure_lookup_table()
        bmesh.ops.create_grid(pbme, x_segments = 200, y_segments = 200, size = 39.9)
        pbme.to_mesh(Plane.data)
        
        
        
        if self.splint.jaw_type == 'MANDIBLE':
            Zw = Vector((0,0,-1))
            Xw = Vector((1,0,0))
            Yw = Vector((0,-1,1))
            
        else:
            Zw = Vector((0,0,1))
            Xw = Vector((1,0,0))
            Yw = Vector((0,1,0))
            
        Z = pno
        Z.normalize()
        
        if Zw.dot(Z) < 0:
            Z *= -1
            
        Y = Z.cross(Xw)
        X = Y.cross(Z)
            
        
        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
        
        R = R.to_4x4()
        T = Matrix.Translation(pt - 5 * Z)
        
        Plane.matrix_world = T * R
    
        pmx = Plane.matrix_world
        ipmx = pmx.inverted()
        
        bme_pln = bmesh.new()
        bme_pln.from_mesh(Plane.data)
        bme_pln.verts.ensure_lookup_table()
        bme_pln.edges.ensure_lookup_table()
        bme_pln.faces.ensure_lookup_table()
        bvh = BVHTree.FromBMesh(bme_pln)
        
        
        #we are going to raycast the user world coordinate points
        #into a grid, and identify all points in the grid from the local Z direction
        #Then we will store the local location of the user picked coordinate in a dictionary
        key_verts = {}
        
        for loc in [pt.location for pt in self.b_pts]:

            res = bvh.ray_cast(ipmx * loc, -Z, 30)
            if res[0] != None:
                
                f = bme_pln.faces[res[2]]
                for v in f.verts:
                    key_verts[v] = ipmx * loc
                    v.select_set(True)
                
                continue
            
            res = bvh.ray_cast(ipmx * loc, Z, 30)
            if res[0] != None:
                
                f = bme_pln.faces[res[2]]
                for v in f.verts:
                    key_verts[v] = ipmx * loc
                    v.select_set(True)
                
                continue
        
        #bme_pln.to_mesh(Plane.data)
        #bme_pln.free()
        #return
        kdtree = KDTree(len(key_verts))
        for v in key_verts.keys():
            kdtree.insert(v.co, v.index)
        
        kdtree.balance()
        
        #raycast  the shell if we can  #TODO cache the BVH
        raycast_shell = False
        if 'Splint Shell' in bpy.data.objects:
            shell = bpy.data.objects.get('Splint Shell')
            bvh_shell = BVHTree.FromObject(shell, self.context.scene)
            mx_shell = shell.matrix_world
            imx_shell = mx_shell.inverted()
            Z_shell = imx_shell.to_3x3()*Z
            raycast_shell = True
            
        
        right_side = set()
        left_side = set()
        ray_casted = set()
        to_delete = set()
        for v in bme_pln.verts:
            if v in key_verts:  #categorize into left and right
                v.co[2] = key_verts[v][2]
               
                if v.co[1] > 0:
                    left_side.add(v)
                else:
                    right_side.add(v)
                continue
                
            results = kdtree.find_range(v.co, .5)  #if within .5mm of a user clicked point
            if len(results):
                N = len(results)
                r_total = 0
                v_new = Vector((0,0,0))
                for res in results:
                    r_total += 1/res[2]
                    v_new += (1/res[2]) * key_verts[bme_pln.verts[res[1]]]  #interpolate by average
                        
                v_new *= 1/r_total
                v.co[2] = v_new[2]
                if v.co[1] > 0:
                    left_side.add(v)
                else:
                    right_side.add(v)
                continue
                        
            results = kdtree.find_range(v.co, 6)
            if len(results):  #if within 6mm of key vertices
                N = len(results)
                r_total = 0
                v_new = Vector((0,0,0))
                for res in results:
                    r_total += (1/res[2])**2
                    v_new += ((1/res[2])**2) * key_verts[bme_pln.verts[res[1]]]  #interpolate with blended square falloff
                        
                v_new *= 1/r_total
                v.co[2] = v_new[2]
                if v.co[1] > 0:
                    left_side.add(v)
                else:
                    right_side.add(v)
                continue
            
            
            #if we are not within 6mm of a key point, then we will ray cast to make sure we are below the shlle
            #and if so, blend the z value of the 4 nearest key points
            loc, no, index, d = bvh_shell.ray_cast(imx_shell * pmx * v.co, Z_shell)
            if loc:
                
                ray_casted.add(v)  #keep track of who we ray casted
                results = kdtree.find_n(v.co, 4)
                N = len(results)
                r_total = 0
                v_new = Vector((0,0,0))
                for res in results:
                    r_total += (1/res[2])**2
                    v_new += ((1/res[2])**2) * key_verts[bme_pln.verts[res[1]]]
                        
                v_new *= 1/r_total
                v.co[2] = v_new[2]
                continue

        total_verts = ray_casted | left_side | right_side
        
           
        if len(right_side) == 0 or  len(left_side) == 0:
            Plane.hide = True
            pbme.free()
            return
        
        ant_right = max(right_side, key = lambda x: x.co[0])
        medial_right = max(right_side, key = lambda x:x.co[1])
        
        ant_left = max(left_side, key = lambda x: x.co[0])   #x axis (v.co[0]) point toward anterior
        medial_left = min(left_side, key = lambda x: x.co[1])  #y axis (v.co[1] poinst from right (negative) to left (positive)
        #filter out the anterior portion often picked up by ray casting the splint
        omit_medial = set()
        for v in ray_casted:
            #filter out medial dilation greater than 2mm
            if v.co[1] <= 0 and v.co[1] > medial_right.co[1] + 2:
                omit_medial.add(v)
                continue
            if v.co[1] >= 0 and v.co[1] < medial_left.co[1] - 2:
                omit_medial.add(v)
                continue
        
        total_verts.difference_update(omit_medial)    
        
        new_verts = set()
        dilation_verts = set()  
        for v in total_verts:
            for ed in v.link_edges:
                v_new = ed.other_vert(v)
                if v_new in total_verts or v_new in new_verts: 
                    continue
                else:
                    new_verts.add(v_new)
                    
        print('adding %i new verts' % len(new_verts))
        
        
        total_verts.update(new_verts)
        dilation_verts.update(new_verts)
        
        #print('adding %i new verts' % len(new_verts))   
        for j in range(0,3):
            newer_verts = set()  
            for v in new_verts:
                for ed in v.link_edges:
                    v_new = ed.other_vert(v)
                    if v_new in total_verts or v_new in newer_verts:
                        continue
                     
                    newer_verts.add(v_new)
                    
            
                       
            total_verts.update(newer_verts)
            dilation_verts.update(newer_verts)
            new_verts = newer_verts
        
        to_delete = set(bme_pln.verts[:]) - total_verts
        
        
        for v in dilation_verts:
            #filter out anterior dilation
            if v.co[1] > 0 and v.co[0] > ant_left.co[0]:
                to_delete.add(v)
                continue
            if v.co[1] <= 0 and v.co[0] > ant_right.co[0]:
                to_delete.add(v)
                continue
            
            results = kdtree.find_n(v.co, 4)  #blend the dilation verts to nearest key points
            N = len(results)
            r_total = 0
            v_new = Vector((0,0,0))
            for res in results:
                r_total += (1/res[2])**2
                v_new += ((1/res[2])**2) * key_verts[bme_pln.verts[res[1]]]
                        
            v_new *= 1/r_total
            v.co[2] = v_new[2]
            
        #filter out anteior dilation
        for v in ray_casted:
            if v.co[1] > 0 and v.co[0] > ant_left.co[0]:
                to_delete.add(v)
                continue
            if v.co[1] <= 0 and v.co[0] > ant_right.co[0]:
                to_delete.add(v)
                continue
                            
        bmesh.ops.delete(bme_pln, geom = list(to_delete), context = 1)
        bme_pln.to_mesh(Plane.data)
        Plane.data.update()
        
        smod = Plane.modifiers.new('Smooth', type = 'SMOOTH')
        smod.iterations = 5
        smod.factor = 1 
    
        self.plane_calced_successfully = True  
    ####  Enhancing UI ############
    
    def ui_setup_post(self):
        
        #####  Hide Existing UI Elements  ###
        self.info_panel.visible = False
        self.tools_panel.visible = False
        
        
        self.info_panel = self.wm.create_window('Occlusal Surface Help',
                                                {'pos':9,
                                                 'movable':True,
                                                 'bgcolor':(0.50, 0.50, 0.50, 0.90)})

        collapse_container = self.info_panel.add(ui.UI_Collapsible('Instructions     ', collapsed=False))
        self.inst_paragraphs = [collapse_container.add(ui.UI_Markdown('', min_size=(100,10), max_size=(250, 50))) for i in range(6)]
        
        self.new_instructions = {
            
            "Add": "Left click on the cusps to mark posterior contacts",
            "Grab": "Hold left-click on a point and drag to move it along the surface of the mesh",
            "Remove": "Right Click to remove a point",
            "Plane": "After enough points are clicked, a preview of the posterior plane will automatically appear"
        }
        
        for i,val in enumerate(['Add', 'Grab', 'Remove', "Plane"]):
            self.inst_paragraphs[i].set_markdown(chr(65 + i) + ") " + self.new_instructions[val])

        
        
        self.win_obvious_instructions = self.wm.create_window('Mark Posterior Contacts', {'pos':8, "vertical":False, "padding":15, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.5), 'border_color':(0.50, 0.50, 0.50, 0.9), "border_width":4.0})
        self.win_obvious_instructions.hbf_title.fontsize = 20
        
        win_next_back = self.wm.create_window(None, {'pos':2, "vertical":False, "padding":15, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.0), 'border_color':(0.50, 0.50, 0.50, 0.9), "border_width":4.0})
        next_back_container = win_next_back.add(ui.UI_Container(vertical = False, background = (0.50, 0.50, 0.50, 0.90)))
        #next_back_frame = next_back_container.add(ui.UI_Frame('', vertical = False, equal = True, separation = 4))#, background = (0.50, 0.50, 0.50, 0.90)))
            
        #back_button = next_back_container.add(ui.UI_Button('Back', mode_backer, margin = 10))
        #back_button.label.fontsize = 20
            
        #cancel_button = next_back_frame.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=0))
        cancel_button = next_back_container.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=10))
        cancel_button.label.fontsize = 20
        calc_plane_button = next_back_container.add(ui.UI_Button('Next', self.next, margin = 10))
        calc_plane_button.label.fontsize = 20
        
        #next_button = next_back_frame.add(ui.UI_Button('Next', mode_stepper, margin = 0))
        
        
        self.set_ui_text()

class D3Splint_OT_posterior_plane_trimmer(SCENE_OT_custom_sculpt_mode):
    """  """
    bl_idname = "d3splint.posterior_surface_trimmer"
    bl_label = "Trim Posterior Surface"
    bl_description = "paint the surface to remove unwanted excess"

    #############################################
    # overwriting functions from Wax Dropper submodule

    
    def can_start(self):
        if 'Posterior Plane' in bpy.data.objects:
            return True
        else:
            return False
        
    def start_pre(self):
        ob = bpy.data.objects.get('Posterior Plane')
        ob.hide = False
        ob.select = True
        bpy.context.scene.objects.active = ob
        self.shell_alpha = .8
        
    def start_post(self):
        
        
        n = bpy.context.scene.odc_splint_index
        self.splint = self.context.scene.odc_splints[n]
        
        
        shell = bpy.data.objects.get('Splint Shell')
        apply_modifiers(shell)
        
        self.obj = bpy.data.objects.get('Posterior Plane')
        self.painted_verts = list()

        scn = bpy.context.scene
        paint_settings = scn.tool_settings.unified_paint_settings
        paint_settings.use_locked_size = True
        paint_settings.unprojected_radius = 1.5
        brush = bpy.data.brushes['Mask']
        brush.strength = 2
        brush.stroke_method = 'SPACE'
        scn.tool_settings.sculpt.brush = brush
        scn.tool_settings.sculpt.use_symmetry_x = False
        scn.tool_settings.sculpt.use_symmetry_y = False
        scn.tool_settings.sculpt.use_symmetry_z = False
        bpy.ops.brush.curve_preset(shape='MAX')
        
        if not self.obj.use_dynamic_topology_sculpting:
            bpy.ops.sculpt.dynamic_topology_toggle()

    def end_commit(self):
        
        print('setting mark posterior contacts true')
        n = bpy.context.scene.odc_splint_index
        splint = bpy.context.scene.odc_splints[n]      
        splint.mark_post_contact = True  
        
        
        shell = bpy.data.objects.get('Splint Shell')
        shell.show_transparent = False
        self.context.space_data.show_backface_culling = False
        if 'Posterior Cut' in shell.modifiers:
            do_posterior_cut = True
        else:
            do_posterior_cut = False
            
        if 'Dynamic Cut' in shell.modifiers:
            do_dynamic_cut = True
        else:
            do_dynamic_cut = False
            
        shell.modifiers.clear()
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        if do_posterior_cut:
            bpy.ops.d3splint.subtract_posterior_surface()
        if do_dynamic_cut:
            bpy.ops.d3splint.splint_subtract_surface()
    
        
    def set_ui_text(self):
        """ sets the viewport text """
        self.reset_ui_text()
        for i,val in enumerate(['Paint', 'Delete', 'Preview']):
            self.inst_paragraphs[i].set_markdown(chr(65 + i) + ") " + self.instructions[val])

    def reset_ui_text(self):
        """ clears the viewport text """
        for inst_p in self.inst_paragraphs:
            inst_p.set_markdown('')

    def set_shell_alpha(self):
        alpha = self.shell_alpha
        mat2 = bpy.data.materials.get("Splint Material")
        if mat2:
            mat2.alpha = alpha
        
        shell = bpy.data.objects.get('Splint Shell')
        if shell:
            if self.shell_alpha > .9:           
                shell.show_transparent = False
                self.context.space_data.show_backface_culling = True
            else:
                shell.show_transparent = True
                self.context.space_data.show_backface_culling = False
        
    def ui_setup(self):
        # instructions
        self.instructions = {
            "Paint": "Leftclick and drag to paint regions of surface to delete",
            "Delete": "Use Delete button to remove painted region",
            "Preview": "Use the preview cuts and visibility buttons to examine result on splint occlusal surface"
        }

        # UI Box functionality
        
        #Sliders for sculpt
        def radius_setter(r):
            r = min(5.0, r)
            r = max(0.25, r)
            r = round(r, 2)
            paint_settings = self.context.scene.tool_settings.unified_paint_settings
            paint_settings.unprojected_radius = r
            
        def radius_getter():
            paint_settings = self.context.scene.tool_settings.unified_paint_settings
            r = paint_settings.unprojected_radius
            return round(r,2)
        

        def pos_neg_setter(r):
            brush = bpy.data.brushes['Mask']
            
            if r == 'ADD':
                brush.direction = 'ADD'
            elif r == 'SUBTRACT':
                brush.direction = 'SUBTRACT'
            else:
                pass
            return
        
        def pos_neg_getter():
            brush = bpy.data.brushes['Mask']
            return brush.direction
        
        
        def model_vis_setter(r):
            model = bpy.data.objects.get(self.splint.model)
            if not model: return
            if r == True:
                model.hide = False
            else:
                model.hide = True
                
        def model_vis_getter():
            model = bpy.data.objects.get(self.splint.model)
            if not model: return False
            else: return model.hide == False
        
        
        
        def shell_vis_setter(r):
            shell = bpy.data.objects.get('Splint Shell')
            if not shell: return
            if r == True:
                shell.hide = False
            else:
                shell.hide = True
                
        def shell_vis_getter():
            shell = bpy.data.objects.get('Splint Shell')
            if not shell: return False
            else: return shell.hide == False
                
        def surf_vis_setter(r):
            surf = bpy.data.objects.get('Dynamic Occlusal Surface')
            if not surf: return
            if r == True:
                surf.hide = False
            else:
                surf.hide = True
                
        def surf_vis_getter():
            surf = bpy.data.objects.get('Dynamic Occlusal Surface')
            if not surf: return False
            else: return surf.hide == False
            
        
        def opposing_vis_setter(r):
            model = bpy.data.objects.get(self.splint.opposing)
            if not model: return
            if r == True:
                model.hide = False
            else:
                model.hide = True
                
        def opposing_vis_getter():
            model = bpy.data.objects.get(self.splint.opposing)
            if not model: return False
            else: return model.hide == False
        
        
        def prev_post_cut(r):
            shell = bpy.data.objects.get('Splint Shell')
            surf = bpy.data.objects.get('Posterior Plane')
            if not shell: return False
            if not surf: return False
            
            mod = shell.modifiers.get("Posterior Cut")
            if (mod == None) and (r == True):
                mod = shell.modifiers.new("Posterior Cut", type = "SHRINKWRAP")
                mod.wrap_method = 'PROJECT'
                mod.use_project_z = True
                mod.use_positive_direction = self.splint.jaw_type == 'MAXILLA'
                mod.target = surf
            elif r == False and mod != None:
                mod.show_viewport = False
                
            elif r == True and mod != None:
                mod.show_viewport = True
                
        def prev_post_get():
            shell = bpy.data.objects.get('Splint Shell')
            if not shell: return False
            
            mod = shell.modifiers.get("Posterior Cut")
            if not mod: return False
            if mod:
                return mod.show_viewport
                 
        def prev_dyn_cut(r):
            shell = bpy.data.objects.get('Splint Shell')
            surf = bpy.data.objects.get('Dynamic Occlusal Surface')
            if not shell: return False
            if not surf: return False
            
            mod = shell.modifiers.get("Dynamic Cut")
            if (mod == None) and (r == True):
                mod = shell.modifiers.new("Dynamic Cut", type = "SHRINKWRAP")
                mod.wrap_method = 'PROJECT'
                mod.use_project_z = True
                mod.use_positive_direction = self.splint.jaw_type == 'MAXILLA'
                mod.target = surf
            elif r == False and mod != None:
                mod.show_viewport = False
                
            elif r == True and mod != None:
                mod.show_viewport = True
                
        def prev_dyn_get():
            shell = bpy.data.objects.get('Splint Shell')
            if not shell: return False
            
            mod = shell.modifiers.get("Dynamic Cut")
            if not mod: return False
            if mod:
                return mod.show_viewport
            
        def shell_alpha_getter():
            ra = min(self.shell_alpha, 1.0)
            ra = max(ra, 0.01)  
            return ra
        
        def shell_alpha_setter(a):
            ra = min(a, 1.0)
            ra = max(ra, 0.01)
            self.shell_alpha = round(ra,2)
            self.set_shell_alpha()
            
                    
        # UPPER LEFT WINDOW, mode setters and commit/cancel buttons
        self.sculpt_tools_panel = self.wm.create_window('Trim Surface', {'pos':7, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})
        sculpt_presets_container = self.sculpt_tools_panel.add(sculpt_ui.UI_Container()) # TODO: make this rounded
        #preset_frame = sculpt_presets_container.add(ui.UI_Frame('Sculpt Brush Presets'))
        #smooth_button = preset_frame.add(ui.UI_Button('Smooth', self.smooth_brush, align=0))
        #fill_button = preset_frame.add(ui.UI_Button('Fill', self.fill_brush, align=0))
        #clay_strip = preset_frame.add(ui.UI_Button('Clay Strip', self.clay_brush, align=0))
        
        radius_and_strength = sculpt_presets_container.add(sculpt_ui.UI_Frame('Brush Size'))
        radius_and_strength.add(sculpt_ui.UI_Number("Brush Size", radius_getter, radius_setter))
        brush_mode = sculpt_presets_container.add(sculpt_ui.UI_Options(pos_neg_getter, pos_neg_setter, separation=0))
        brush_mode.add_option('PAINT', value='ADD')
        brush_mode.add_option('ERASE', value='SUBTRACT')
        
        delete_button = sculpt_presets_container.add(sculpt_ui.UI_Button('Delete Painted', self.delete_painted))
        
        win_next_back = self.wm.create_window(None, {'pos':2, "vertical":False, "padding":15, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.0), 'border_color':(0.50, 0.50, 0.50, 0.9), "border_width":4.0})
        next_back_container = win_next_back.add(sculpt_ui.UI_Container(vertical = False, background = (0.50, 0.50, 0.50, 0.90)))
        #next_button = next_back_container.add(ui.UI_Button('Next', mode_stepper, margin = 10))
        #next_button.label.fontsize = 20
        self.cancel_button = next_back_container.add(sculpt_ui.UI_Button('Cancel', lambda:self.done(cancel=True), align=0))
        self.commit_button = next_back_container.add(sculpt_ui.UI_Button('Commit', self.done, align=0))
        self.commit_button.label.fontsize = 20
        self.cancel_button.label.fontsize = 20
        
        #####################################
        ### Collapsible Help and Options   ##
        #####################################
        self.info_panel = self.wm.create_window('Occlusal Surface Help',
                                                {'pos':9,
                                                 'movable':True,
                                                 'bgcolor':(0.50, 0.50, 0.50, 0.90)})

        collapse_container = self.info_panel.add(sculpt_ui.UI_Collapsible('Instructions     ', collapsed=False))
        self.inst_paragraphs = [collapse_container.add(sculpt_ui.UI_Markdown('', min_size=(100,10), max_size=(250, 20))) for i in range(4)]
        
        visibility_container = self.info_panel.add(sculpt_ui.UI_Container())
        visibility_frame = visibility_container.add(sculpt_ui.UI_Frame('Surface Visibility'))
        visibility_frame.add(sculpt_ui.UI_Checkbox2('Model', model_vis_getter, model_vis_setter))
        visibility_frame.add(sculpt_ui.UI_Checkbox2('Splint Shell', shell_vis_getter, shell_vis_setter))
        visibility_frame.add(sculpt_ui.UI_Number("Shell Opacity", shell_alpha_getter, shell_alpha_setter, update_multiplier= .005))
        visibility_frame.add(sculpt_ui.UI_Checkbox2('Dyn Surface', surf_vis_getter, surf_vis_setter))
        visibility_frame.add(sculpt_ui.UI_Checkbox2('Opposing Model', opposing_vis_getter, opposing_vis_setter))
        
        #ops_container = self.info_panel.add(sculpt_ui.UI_Container())
        #ops_frame = ops_container.add(sculpt_ui.UI_Frame('Preview Cuts'))
        #ops_frame.add(sculpt_ui.UI_Checkbox2('Preview Cut Post', prev_post_get, prev_post_cut))
        #ops_frame.add(sculpt_ui.UI_Checkbox2('Preview Cut Dyn', prev_dyn_get, prev_dyn_cut))
        
        self.set_ui_text()
        
        
    def delete_painted(self):
        last_mode = bpy.context.mode
        bpy.ops.object.mode_set(mode='OBJECT')

        obj = bpy.context.active_object

        bme = bmesh.new()
        bme.from_mesh(obj.data)

        mask = bme.verts.layers.paint_mask.verify()

        delete = [v for v in bme.verts if v[mask] > 0]
        bmesh.ops.delete(bme, geom=delete, context=1)

        bme.to_mesh(obj.data)
        bme.free()
        obj.data.update()
        bpy.ops.object.mode_set(mode = last_mode)

                
def register():
    #bpy.utils.register_class(D3SPLINT_OT_splint_manual_auto_surface)
    #bpy.utils.register_class(D3SPLINT_OT_splint_subtract_posterior_surface)
    bpy.utils.register_class(D3DUAL_OT_appliance_subtract_surface)
    bpy.utils.register_class(D3DUAL_OT_transform_arch_surface)
    #bpy.utils.register_class(D3SPLINT_OT_cookie_cutter_points)
    #bpy.utils.register_class(D3Splint_OT_posterior_plane_trimmer)
    
def unregister():
    #bpy.utils.unregister_class(D3SPLINT_OT_splint_manual_auto_surface) 
    #bpy.utils.unregister_class(D3SPLINT_OT_splint_subtract_posterior_surface)
    bpy.utils.unregister_class(D3DUAL_OT_appliance_subtract_surface)
    bpy.utils.unregister_class(D3DUAL_OT_transform_arch_surface)
    #bpy.utils.unregister_class(D3SPLINT_OT_cookie_cutter_points)

# ---- Perplexity API Suggested Migrations ----
In Blender 4.4, the old property registration style using direct assignment to bpy.props (e.g., bpy.props.BoolProperty) is deprecated. Properties should now be defined as class annotations using Python's type hinting and the bpy.props module. Here is the corrected code block for Blender 4.4+:

```python
import bpy

class MyOperator(bpy.types.Operator):
    # Use class annotations for properties in Blender 2.80+ (including 4.4)
    sculpt_to: bpy.props.BoolProperty(
        default=False,
        description="Not only remove but pull some of the shell down to touch"
    )
    snap_limit: bpy.props.FloatProperty(
        default=2.0,
        min=0.25,
        max=5.0,
        description="Max distance the shell will snap to"
    )
    remesh: bpy.props.BoolProperty(
        default=True,
        description="Remesh Afterward"
    )
    operation: bpy.props.EnumProperty(
        name='Subtract Mode',
        items=mode_items,
        default='SURFACE_FROM_BOTH'
    )
```

**Key changes:**
- Use class-level annotations (e.g., `sculpt_to: bpy.props.BoolProperty(...)`) instead of assigning properties to variables.
- Do not assign properties directly to variables outside of a class.
- Remove duplicate property definitions.

This is the required and supported way to define custom properties for operators and panels in Blender 4.4[1].
