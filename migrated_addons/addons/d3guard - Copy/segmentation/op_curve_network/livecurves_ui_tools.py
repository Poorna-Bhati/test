'''
Created on Oct 10, 2015

@author: Patrick
#vertex_group
https://blender.stackexchange.com/questions/75223/finding-vertices-in-a-vertex-group-using-blenders-python-api
'''
import bmesh
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import time
import math
import random

import splint_cache

from ..bmesh_fns import edge_loops_from_bmedges_old, ensure_lookup, new_bmesh_from_bmelements
from ..common.utils import get_matrices
from ..common.rays import get_view_ray_data, ray_cast, ray_cast_path, ray_cast_bvh

from segmentation.op_curve_network.livecurves_datastructure import InputNetwork, InputPoint, InputSegment, SplineSegment, CurveNode, BezierBar

import bgl
import odcutils
from common_utilities import get_settings, showErrorMessage

from bpy_extras import view3d_utils
from mathutils import Vector, kdtree, Color, Matrix
from mathutils.geometry import intersect_point_line, intersect_line_plane
from mathutils.bvhtree import BVHTree
from ..bmesh_fns import grow_selection, edge_loops_from_bmedges_old, flood_selection_by_verts, flood_selection_edge_loop, ensure_lookup
from ..common.maths import space_evenly_on_path, intersect_path_plane
from ..common.bezier import CubicBezierSpline
from ..common.simplify import simplify_RDP
from segmentation.common.blender import show_error_message



class Livecurves_UI_Tools():
    '''
    Functions/classes helpful with user interactions in polytrim
    '''

    class SketchManager():
        '''
        UI tool for managing sketches made by user.
        * Intermediary between polytrim_states and Network
        '''
        def __init__(self, spline_net, net_ui_context):
            self.sketch = []
            self.spline_net = spline_net
            self.net_ui_context = net_ui_context
            self.stroke_smoothing = 0.75  # 0: no smoothing. 1: no change
            self.sketch_curpos = (0, 0)
            self.bez_data = []
            
        def has_locs(self): return len(self.sketch) > 0
        has_locs = property(has_locs)

        def get_locs(self): return self.sketch

        def reset(self): self.sketch = []

        def add_loc(self, x, y):
            ''' Add's a screen location to the sketch list '''
            self.sketch.append((x,y))

        def smart_add_loc(self, x, y):
            ''' Add's a screen location to the sketch list based on smart stuff '''
            (lx, ly) = self.sketch[-1]
            ss0,ss1 = self.stroke_smoothing ,1-self.stroke_smoothing  #First data manipulation
            self.sketch += [(lx*ss0+x*ss1, ly*ss0+y*ss1)]

        def is_good(self):
            ''' Returns whether the sketch attempt should/shouldn't be added to the InputNetwork '''
            # checking to see if sketch functionality shouldn't happen
            if len(self.sketch) < 5 and self.net_ui_context.ui_type == 'DENSE_POLY': return False
            return True

        def finalize(self, context, start_pnt, end_pnt=None):
            ''' takes sketch data and adds it into the data structures '''

            print('Finalizing sketching', start_pnt, end_pnt)
            if not isinstance(end_pnt, InputPoint) or isinstance(end_pnt, CurveNode):
                end_pnt = None
            if not isinstance(start_pnt, InputPoint) or isinstance(start_pnt, CurveNode):
                prev_pnt = None
            else:
                prev_pnt = start_pnt

            
            sketch_3d = []
            other_data = []
            #mx, imx, mx_norm, imx_norm = self.net_ui_context.get_target_matrices()
            #bvh = self.net_ui_context.get_target_bvh()
            bvh = self.net_ui_context.bvh
            mx, imx = Matrix.Identity(4), Matrix.Idneity(4) 
             
                
            for pt in self.sketch:
                view_vector, ray_origin, ray_target = get_view_ray_data(context, pt)  #a location and direction in WORLD coordinates
                    #loc, no, face_ind =  ray_cast(self.net_ui_context.ob,self.net_ui_context.imx, ray_origin, ray_target, None)  #intersects that ray with the geometry
                loc, no, face_ind =  ray_cast_bvh(bvh,imx, ray_origin, ray_target, None)
                if face_ind != None:
                        sketch_3d += [mx * loc]
                        other_data += [(loc, view_vector, face_ind)]

            feature_inds = simplify_RDP(sketch_3d, .25)  #TODO, sketch threshold

            new_points = []
            new_segs = []
            for ind in feature_inds:
                if not prev_pnt:
                    if self.spline_net.num_points == 1: new_pnt = self.spline_net.points[0]
                    else: new_pnt = start_pnt
                else:
                    loc3d = sketch_3d[ind]
                    loc, view_vector, face_ind = other_data[ind]
                    new_pnt = self.spline_net.create_point(loc3d, loc, view_vector, face_ind)
                    new_points += [new_pnt]
                if prev_pnt:
                    print(prev_pnt)
                    seg = SplineSegment(prev_pnt,new_pnt)
                    self.spline_net.segments.append(seg)
                    new_segs += [seg]
                    #self.network_cutter.precompute_cut(seg)
                    #seg.make_path(self.net_ui_context.bme, self.input_net.bvh, self.net_ui_context.mx, self.net_ui_context.imx)
                prev_pnt = new_pnt
            if end_pnt:
                if end_pnt == prev_pnt:
                    print('connecting the same point to itself in sketch finalize')
                seg = SplineSegment(prev_pnt,end_pnt)
                self.spline_net.segments.append(seg)
                new_segs += [seg]
            for p in new_points:
                p.calc_handles()
            for seg in new_segs:
                seg.calc_bezier()
                seg.tessellate()
                seg.tessellate_IP_error(.1)


        def finalize_bezier(self, context):
            
            stroke3d = []
            #mx, imx, mx_norm, imx_norm = self.net_ui_context.get_target_matrices()
            #bvh = self.net_ui_context.get_target_bvh()
    
            bvh = self.net_ui_context.bvh
            mx, imx = Matrix.Identity(4), Matrix.Identity(4) 
            
            for ind in range(0, len(self.sketch) , 5):
                pt_screen_loc = self.sketch[ind]  #in screen space
                view_vector, ray_origin, ray_target = get_view_ray_data(context, pt_screen_loc)  #a location and direction in WORLD coordinates
                loc, no, face_ind =  ray_cast_bvh(bvh,imx, ray_origin, ray_target, None)
                if face_ind != None:
                    stroke3d += [mx * loc]
                    
            #print(stroke3d)
            cbs = CubicBezierSpline.create_from_points([stroke3d], .05)
            cbs.tessellate_uniform(lambda p,q:(p-q).length, split=20)
            L = cbs.approximate_totlength_tessellation()
            n = L/2  #2mm spacing long strokes?
            #print(cbs.tessellation)
            
            self.bez_data = []
            for btess in cbs.tessellation:
                self.bez_data += [pt.as_vector() for i,pt,d in btess]

    class GrabManager():
        '''
        UI tool for managing input point grabbing/moving made by user.
        * Intermediary between polytrim_states and Network
        '''
        def __init__(self, net_ui_context):
            self.net_ui_context = net_ui_context
            self.grab_point = None
            self.original_point = None
            self.backup_data = {}
        def in_use(self): return self.grab_point != None
        in_use = property(in_use)

        def initiate_grab_point(self):
            self.grab_point = self.net_ui_context.selected
            self.backup_data =  self.grab_point.duplicate_data()

        def move_grab_point(self,context,mouse_loc):
            ''' Moves location of point'''
            d = self.net_ui_context.hovered_mesh
            n = self.net_ui_context.hovered_near
            
            if d and self.grab_point:
                #print(n)
                               
                self.grab_point.set_values(d["world loc"], d["local loc"], d["view"], d["face index"])
                #self.grab_point.bmface = self.input_net.bme.faces[d["face index"]]
                self.grab_point.seed_geom = None  #we have ensure it's not a non manifold
                self.grab_point.bmedge = None #unused, but will in future
                
                
                #update bezier preview and snap to surface
                if isinstance(self.grab_point, CurveNode):
                    self.grab_point.calc_handles()
                    for seg in self.grab_point.link_segments:
                        seg.is_inet_dirty = True
                        node = seg.other_point(self.grab_point)
                        node.calc_handles()
                        node.update_splines()
        
        def move_grab_point_2D(self, context, mouse_loc):
            x, y = mouse_loc
            
            #get mouse position at depth of the extrusion midpoint
            mouse_projected = view3d_utils.region_2d_to_location_3d(context.region, context.region_data, (x,y), self.backup_data["world_loc"])
            #mx, imx, mx_no, imx_no = self.net_ui_context.get_target_matrices()
            
            self.grab_point.world_loc = mouse_projected
            self.grab_point.local_loc = mouse_projected  #local locs are useless for this


            if isinstance(self.grab_point, CurveNode):
                self.grab_point.calc_handles()
                for seg in self.grab_point.link_segments:
                    seg.is_inet_dirty = True
                    node = seg.other_point(self.grab_point)
                    node.calc_handles()
                    node.update_splines()
                            
            #calculate the delta vector
            #local_delta = imx * mouse_projected - imx * self.new_geom_point

            #update bmverts position
            #for v in self.extrude_verts:
            #    v.co = self.extrude_origins[v] + local_delta
                
            #how costly is this to do live? We will find out
            #self.bme.to_mesh(self.ob.data)
            #self.ob.data.update()
                        
        def snap_splines(self):
            #no longer need to to this!
            #return None
            #moving one point affects 4 splines
            
            # -----(n-2)========(n-1)=======N========(n+1)=========(n+2)------
            
            segs = set()
            for seg in self.grab_point.link_segments:
                segs.add(seg)
                if not seg.other_point(self.grab_point): continue
                p_other = seg.other_point(self.grab_point)
                for seg1 in p_other.link_segments:
                    segs.add(seg1)
                    
            for update_seg in segs:
                snap_pts = []
                for loc in update_seg.draw_tessellation:
                    snap = self.net_ui_context.closest_world_loc(loc)
                    if snap: snap_pts += [snap[0]]
            
                update_seg.draw_tessellation = snap_pts
                        
        def grab_cancel(self):
            ''' returns variables to their status before grab was initiated '''
            if not self.grab_point: return
            for key in self.backup_data:
                setattr(self.grab_point, key, self.backup_data[key])
            
            if isinstance(self.grab_point, CurveNode):
                self.grab_point.calc_handles()
                for seg in self.grab_point.link_segments:
                    seg.is_inet_dirty = False
                    node = seg.other_point(self.grab_point)
                    node.calc_handles()
                    node.update_splines()
                         
            self.grab_point = None #TODO BROKEN
            return

        def finalize(self, context):
            ''' sets new variables based on new location '''
            if not self.grab_point: return
            
            self.net_ui_context.selected.calc_handles()
            for seg in self.net_ui_context.selected.link_segments:
                node = seg.other_point(self.net_ui_context.selected)
                node.calc_handles()
                node.update_splines()
                  
            self.grab_point = None
            return

    class NetworkUIContext():
        '''
        UI tool for storing data depending on where mouse is located
        * Intermediary between polytrim_states and Network
        '''
        def __init__(self, context, obs):
            self.context = context
            
            #### build mapped BVH limited to just objects we want####
            #lookup mapping back to orig objects/
            
            cumulative_bme = bmesh.new()
            cumulative_bme.verts.ensure_lookup_table()
            cumulative_bme.edges.ensure_lookup_table()
            cumulative_bme.faces.ensure_lookup_table()
            
            self.newface2objface = {}
            self.newface2obj = {}
            self.mx_dict = {}
            
            self.target = 'SURFACE'
            for ob in obs:
                
                mx = ob.matrix_world
                imx = mx.inverted()
                mx_norm = imx.transposed().to_3x3()
                imx_norm = imx.to_3x3()
                 
                 
                self.mx_dict[ob] = (mx, imx, mx_norm, imx_norm)
            
                n_faces = len(cumulative_bme.faces)
                n_verts = len(cumulative_bme.verts)
                cumulative_bme.from_mesh(ob.data)
                
                #transform the verts just added
                for v in cumulative_bme.verts[n_verts:]:
                    v.co = mx * v.co
                    
                for i in range(n_faces, len(cumulative_bme.faces)):
                    self.newface2obj[i] = ob  #map the new_face indices to the original object
                    self.newface2objface[i] = i - n_faces  #map the new_face indexes to the object face indices?
            
            self.bvh = BVHTree.FromBMesh(cumulative_bme)
                    
            context.scene.render.engine = 'BLENDER_RENDER'
            context.space_data.show_manipulator = False
            context.space_data.viewport_shade = 'SOLID'  #TODO until smarter drawing
            context.space_data.show_textured_solid = False #TODO until smarter patch drawing
            context.space_data.show_backface_culling = True
            self.mouse_loc = None
            self.hovered_mesh = {}

            # TODO: Organize everything below this
            self.selected = None
            self.snap_element = None
            self.connect_element = None
            #self.closest_ep = None
            self.hovered_near = [None, -1]

           
        def is_hovering_mesh(self): 
            if self.hovered_mesh: return self.hovered_mesh["face index"] != -1
            return False
        

        def closest_world_loc(self, loc):
            '''
            just a wrapper for bvh.find-nearest
            '''
            
            loc, no, face_ind, d =  self.bvh.find_nearest(loc)
            if loc:
                return loc, no, face_ind, self.newface2obj[face_ind], self.newface2objface[face_ind]
            
            
        def update(self, mouse_loc):
            self.mouse_loc = mouse_loc
            self.ray_cast_mouse()

            #self.nearest_non_man_loc()

        def ray_cast_mouse(self):
            view_vector, ray_origin, ray_target= get_view_ray_data(self.context, self.mouse_loc)
            
            if self.target == 'SURFACE':
        
                loc, no, face_ind = ray_cast_bvh(self.bvh, Matrix.Identity(4), ray_origin, ray_target, None)
    
            else: 
                self.hovered_mesh = {}
                return
                
            if face_ind == None:    
                self.hovered_mesh = {}
                return
            
            else:
                
                self.hovered_mesh["world loc"] = loc  #we do raycasting in world space BVH now
                self.hovered_mesh["local loc"] = loc  #TODO ignore the local loc
                self.hovered_mesh["normal"] = no
                self.hovered_mesh["face index"] = face_ind
                self.hovered_mesh["object"] = self.newface2obj[face_ind]
                self.hovered_mesh["obj face"] = self.newface2objface[face_ind]
                self.hovered_mesh["view"] = view_vector
              
      
    def snap_node(self, curve_node):  
    
        segs = set()
        for seg in curve_node.link_segments:
            segs.add(seg)
            if not seg.other_point(curve_node): continue
            p_other = seg.other_point(curve_node)
            for seg1 in p_other.link_segments:
                segs.add(seg1)
                
        for update_seg in segs:
            snap_pts = []
            for loc in update_seg.draw_tessellation:
                snap = self.net_ui_context.closest_world_loc(loc)
                if snap: snap_pts += [snap[0]]
        
            update_seg.draw_tessellation = snap_pts
            
                
    def set_visualization(self, mode = 'SOLID'):
        
        if mode == 'SOLID':
            for ob in self.obs:
                ob.show_transparent = False
        
        elif mode == 'FREE':
            for ob in self.obs:
                ob.show_transparent = True
        
        return
        
    def set_2d_mode(self):    
        self.net_ui_context.target = None
        self.set_visualization(mode = 'NONE')
    
    def add_spline(self, endpoint0, endpoint1):
        assert endpoint0.is_endpoint and endpoint1.is_endpoint  #NO nodes with genus > 2
        
        #assert endpoint0 in self.net_ui_context.target_dict
        #assert endpoint1 in self.net_ui_context.target_dict
        
        #if self.net_ui_context.target_dict[endpoint0] != self.net_ui_context.target_dict[endpoint1]:
        #    return
        
        if endpoint0 == endpoint1:
            print('connecting an endpoint to iteslf in def add_splint')
        
        seg = SplineSegment(endpoint0, endpoint1)
        self.spline_net.segments.append(seg)
        
        endpoint0.calc_handles()
        endpoint1.calc_handles()
            
        endpoint0.update_splines()
        endpoint1.update_splines()
        
        return seg

    def add_point(self, p2d):
        if self.net_ui_context.hovered_mesh == {}: return None
        
        data = self.net_ui_context.hovered_mesh
        loc, view, ind = data["local loc"], data["view"], data["face index"]
        #mx, imx, mx_n, imx_n = self.net_ui_context.get_target_matrices()
        p = self.spline_net.create_point(loc, loc, view, ind)
        #p = self.spline_net.create_point(mx * loc, loc, view, ind)
        
        #self.net_ui_context.target_dict[p] = self.net_ui_context.target
        return p
    
    def insert_spline_point(self, p2d):
        
        seg = self.net_ui_context.hovered_near[1]
        n0, n1 = seg.n0, seg.n1 
        
        #target = self.net_ui_context.target_dict[n0]
        #make sure we are
        
        if self.net_ui_context.target != None:
            #if target != self.net_ui_context.target: return None #we are hoving the wrong curve!
            p = self.add_point(p2d)
        else:
            context = self.context
            mid = .5 * (n0.world_loc + n1.world_loc)
            real_mid =  view3d_utils.region_2d_to_location_3d(context.region, context.region_data, self.actions.mouse, mid)
            
            #mx, imx, mxno, imxno = self.net_ui_context.get_target_matrices_by_name(target)
            p = self.spline_net.create_point(real_mid, real_mid, Vector((0,0,1)), -1)
            #p = self.spline_net.create_point(real_mid, imx * real_mid, Vector((0,0,1)), -1)
            
            
            #self.net_ui_context.target_dict[p] = target  #<< Make sure we keep this point sorted
        if not p: return None
        
          
        self.spline_net.insert_point(p, seg)
        for node in [n0, p, n1]:
            node.calc_handles()
        #n00 ----- n0 ------ p ------ n1-----n11 
        for node in [n0, n1]:  #because n0 and n1 connect to p,  this updates 4 splines
            node.update_splines()
        return p
                
    def click_delete_spline_point(self, mode = 'mouse', disconnect=False):
        '''
        removes point from the spline
        '''
        
        if self.net_ui_context.hovered_near[0] != 'POINT': return
        curve_point = self.net_ui_context.hovered_near[1]  #CurveNode

        #Remove CurveNode from SplineNetwork
        connected_points = self.spline_net.remove_point(curve_point, disconnect)  #returns the new points on either side, connected or not
    
        for node in connected_points:  #need all point handles updated first, becuae of how auto handles use neighboring points
            node.calc_handles()   
        for node in connected_points:  #this actually doubly updaes the middle segment, but it's just bez interp, no cutting
            node.update_splines()
        
        self.net_ui_context.selected = None        
        #if curve_point in self.net_ui_context.target_dict:
        #    self.net_ui_context.target_dict.remove(curve_point)
            
    def closest_endpoint(self, pt3d):
        def dist3d(point):
            return (point.world_loc - pt3d).length

        endpoints = [ip for ip in self.input_net.points if ip.is_endpoint]
        if len(endpoints) == 0: return None

        return min(endpoints, key = dist3d)
    
    # TODO: Make this a NetworkUIContext function
    def closest_spline_endpoint(self, pt3d):
        def dist3d(point):
            return (point.world_loc - pt3d).length

        endpoints = [ip for ip in self.spline_net.points if ip.is_endpoint]
        if len(endpoints) == 0: return None

        return min(endpoints, key = dist3d)
    
    # TODO: Also NetworkUIContext function
    def closest_endpoints(self, pt3d, n_points):
        #in our application, at most there will be 100 endpoints?
        #no need for accel structure here
        n_points = max(0, n_points)

        endpoints = [ip for ip in self.input_net.points if ip.is_endpoint] #TODO self.endpoints?

        if len(endpoints) == 0: return None
        n_points = min(n_points, len(endpoints))

        def dist3d(point):
            return (point.world_loc - pt3d).length

        endpoints.sort(key = dist3d)

        return endpoints[0:n_points+1]

    def closest_spline_endpoints(self, pt3d, n_points):
        #in our application, at most there will be 100 endpoints?
        #no need for accel structure here
        n_points = max(0, n_points)

        endpoints = [ip for ip in self.spline_net.points if ip.is_endpoint] #TODO self.endpoints?
        if len(endpoints) == 0: return []
        n_points = min(n_points, len(endpoints))

        def dist3d(point): return (point.world_loc - pt3d).length

        endpoints.sort(key = dist3d)
        return endpoints[0:n_points+1]

    # TODO: NetworkUIContext??
    def closest_point_3d_linear(self, seg, pt3d):
        '''
        will return the closest point on a straigh line segment
        drawn between the two input points
       
        If the 3D point is not within the infinite cylinder defined
        by 2 infinite disks placed at each input point and orthogonal
        to the vector between them, will return None
       
       
       
        A_pt3d              B_pt3d
          .                    .
          |                    |              
          |                    |              
          |                    |               
          |       ip0._________x_________.ip1   
         
         
         A_pt3d will return None, None.  B_pt3d will return 3d location at orthogonal intersection and the distance
         
         else, will return a tupple (location of intersection, %along line from ip0 to ip1
         
         happens in the world coordinates
       
        '''

        if isinstance(seg, SplineSegment):
            intersect3d = intersect_point_line(pt3d, seg.n0.world_loc, seg.n1.world_loc)
        else:
            intersect3d = intersect_point_line(pt3d, seg.ip0.world_loc, seg.ip1.world_loc)

        if intersect3d == None: return (None, None)

        dist3d = (intersect3d[0] - pt3d).length

        if  (intersect3d[1] < 1) and (intersect3d[1] > 0):
            return (intersect3d[0], dist3d)

        return (None, None)
    
    
    def tessellate_cycles(self, cycle_data, tess_res):
        
        tess_cycles = []
        for ips, segs in cycle_data:
            raw_tess_cyc = []
            for i in range(0, len(ips)-1):
                ip = ips[i]
                seg = segs[i]
                
                pts = seg.draw_tessellation.copy()
                if ip == seg.n1:
                    pts.reverse()
                    
                raw_tess_cyc += pts

            v_final, eds = space_evenly_on_path(raw_tess_cyc, [(0,1),(1,2)], tess_res)
            tess_cycles += [v_final]
        return tess_cycles
    
    
    
        
    def hover(self, select_radius = 15, snap_radius = 35): #TDOD, these radii are pixels? Shoudl they be settings?
        '''
        finds points/edges/etc that are near ,mouse
         * hovering happens in mixed 3d and screen space, 20 pixels thresh for points, 30 for edges 40 for non_man
        '''

        # TODO: update self.hover to use Accel2D?
        mouse = self.actions.mouse
        context = self.context

        mx, imx = get_matrices(self.net_ui_context.ob)
        loc3d_reg2D = view3d_utils.location_3d_to_region_2d
        # ray tracing
        view_vector, ray_origin, ray_target = get_view_ray_data(context, mouse)
        #loc, no, face_ind = ray_cast(self.net_ui_context.ob, imx, ray_origin, ray_target, None)
        loc, no, face_ind = ray_cast_bvh(self.net_ui_context.bvh, imx, ray_origin, ray_target, None)
        self.net_ui_context.snap_element = None
        self.net_ui_context.connect_element = None

        if self.input_net.is_empty:
            self.net_ui_context.hovered_near = [None, -1]
            self.net_ui_context.nearest_non_man_loc()
            return
        
        if face_ind == -1 or face_ind == None: 
            self.net_ui_context.closest_ep = None
            return
        else: self.net_ui_context.closest_ep = self.closest_endpoint(mx * loc)

        #find length between vertex and mouse
        def dist(v):
            if v == None:
                print('v off screen')
                return 100000000
            diff = v - Vector(mouse)
            return diff.length

        #find length between 2 3d points
        def dist3d(v3):
            if v3 == None:
                return 100000000
            delt = v3 - self.net_ui_context.ob.matrix_world * loc
            return delt.length

        #closest_3d_loc = min(self.input_net.world_locs, key = dist3d)
        closest_ip = min(self.input_net.points, key = lambda x: dist3d(x.world_loc))
        pixel_dist = dist(loc3d_reg2D(context.region, context.space_data.region_3d, closest_ip.world_loc))

        if pixel_dist  < select_radius:
            #print('point is hovered_near')
            #print(pixel_dist)
            self.net_ui_context.hovered_near = ['POINT', closest_ip]  #TODO, probably just store the actual InputPoint as the 2nd value?
            self.net_ui_context.snap_element = None
            return

        elif pixel_dist >= select_radius and pixel_dist < snap_radius:
            #print('point is within snap radius')
            #print(pixel_dist)
            if closest_ip.is_endpoint:
                self.net_ui_context.snap_element = closest_ip

                #print('This is the close loop scenario')
                closest_endpoints = self.closest_endpoints(self.net_ui_context.snap_element.world_loc, 2)

                #print('these are the 2 closest endpoints, one should be snap element itself')
                #print(closest_endpoints)
                if closest_endpoints == None:
                    #we are not quite hovered_near but in snap territory
                    return

                if len(closest_endpoints) < 2:
                    #print('len of closest endpoints not 2')
                    return

                self.net_ui_context.connect_element = closest_endpoints[1]

            return


        if self.input_net.num_points == 1:  #why did we do this? Oh because there are no segments.
            self.net_ui_context.hovered_near = [None, -1]
            self.net_ui_context.snap_element = None
            return

        ##Check distance between ray_cast point, and segments
        distance_map = {}
        for seg in self.input_net.segments:  #TODO, may need to decide some better naming and better heirarchy
  
            close_loc, close_d = self.closest_point_3d_linear(seg, self.net_ui_context.ob.matrix_world * loc)
            if close_loc  == None:
                distance_map[seg] = 10000000
                continue

            distance_map[seg] = close_d

        if self.input_net.segments:
            closest_seg = min(self.input_net.segments, key = lambda x: distance_map[x])

            a = loc3d_reg2D(context.region, context.space_data.region_3d, closest_seg.ip0.world_loc)
            b = loc3d_reg2D(context.region, context.space_data.region_3d, closest_seg.ip1.world_loc)

            if a and b:  #if points are not on the screen, a or b will be None
                intersect = intersect_point_line(Vector(mouse).to_3d(), a.to_3d(),b.to_3d())
                dist = (intersect[0].to_2d() - Vector(mouse)).length_squared
                bound = intersect[1]
                if (dist < select_radius**2) and (bound < 1) and (bound > 0):
                    self.net_ui_context.hovered_near = ['EDGE', closest_seg]
                    return

        ## Multiple points, but not hovering over edge or point.
        self.net_ui_context.hovered_near = [None, -1]

    def hover_spline(self, select_radius=12, snap_radius=24): #TODO, these radii are pixels? Should they be settings?
        '''
        finds points/edges/etc that are near ,mouse
         * hovering happens in mixed 3d and screen space, 20 pixels thresh for points, 30 for edges 40 for non_man
        '''

        self.net_ui_context.snap_element    = None
        self.net_ui_context.connect_element = None
        self.net_ui_context.hovered_near    = [None, -1]
        self.net_ui_context.hovered_dist2D  = float('inf')
        self.net_ui_context.closest_ep      = None

        # TODO: update self.hover to use Accel2D?
        mouse = self.actions.mouse
        mouse_vec = Vector(mouse)
        context = self.context

        #mx, imx, mx_no, imx_no = self.net_ui_context.get_target_matrices()
        #bvh = self.net_ui_context.get_target_bvh()
        
        bvh = self.net_ui_context.bvh
        mx, imx = Matrix.Identity(4), Matrix.Identity(4) 
            
        
        loc3d_reg2D = view3d_utils.location_3d_to_region_2d

        if self.spline_net.is_empty:
            # no points to be near
            return

        # ray tracing
        view_vector, ray_origin, ray_target = get_view_ray_data(context, mouse)
        #loc, no, face_ind = ray_cast(self.net_ui_context.ob, imx, ray_origin, ray_target, None)
        loc,_,face_ind = ray_cast_bvh(bvh, imx, ray_origin, ray_target, None)

        # bail if we did not hit the source
        if face_ind == -1 or face_ind == None: return

        #loc = mx * loc      # transform loc to world
        self.net_ui_context.closest_ep = self.closest_spline_endpoint(loc)

        # find length between vertex and mouse
        def dist(v): return (v - mouse_vec).length if v else float('inf')
        # find length between 2 3d points
        def dist3d(v3): return (v3 - loc).length if v3 else float('inf')

        #closest_3d_loc = min(self.spline_net.world_locs, key = dist3d)
        closest_ip = min(self.spline_net.points, key = lambda x: dist3d(x.world_loc))
        pixel_dist = dist(loc3d_reg2D(context.region, context.space_data.region_3d, closest_ip.world_loc))

        if pixel_dist < select_radius:
            # the mouse is hovering over a point
            #if self.net_ui_context.target != self.net_ui_context.target_dict[closest_ip]:
            #    return
            self.net_ui_context.hovered_near = ['POINT', closest_ip]  #TODO, probably just store the actual InputPoint as the 2nd value?
            self.net_ui_context.hovered_dist2D = pixel_dist
            return

        if select_radius <= pixel_dist < snap_radius:
            # the mouse is near a point (just outside of hovering)
            if closest_ip.is_endpoint:
                # only care about endpoints at this moment
                self.net_ui_context.snap_element = closest_ip
                self.net_ui_context.hovered_dist2D = pixel_dist
                #print('This is the close loop scenario')
                closest_endpoints = self.closest_spline_endpoints(self.net_ui_context.snap_element.world_loc, 2)
                # bail if we did not find at least two nearby endpoints
                if len(closest_endpoints) < 2: return
                self.net_ui_context.hovered_near = ['POINT CONNECT', closest_ip]
                self.net_ui_context.connect_element = closest_endpoints[1]
            return

        # bail if there are only one num_points (no segments)
        if self.spline_net.num_points == 1: return
        
        
        ##Check distance between ray_cast point, and linear appox of segments
        #TODO, do tesselated segments
        distance_map = {}
        
        for seg in self.spline_net.segments:  #TODO, may need to decide some better naming and better hierarchy
            close_loc, close_d = self.closest_point_3d_linear(seg, loc)
            distance_map[seg] = close_d if close_loc else float('inf')

        
        closest_seg = min(self.spline_net.segments, key = lambda x: distance_map[x])

        a = loc3d_reg2D(context.region, context.space_data.region_3d, closest_seg.n0.world_loc)
        b = loc3d_reg2D(context.region, context.space_data.region_3d, closest_seg.n1.world_loc)

        if a and b:  #if points are not on the screen, a or b will be None
            intersect = intersect_point_line(mouse_vec.to_3d(), a.to_3d(),b.to_3d())
            dist = (intersect[0].to_2d() - mouse_vec).length_squared
            bound = intersect[1]
            if (dist < select_radius**2) and (bound < 1) and (bound > 0):
                #spline_seg = closest_seg.parent_spline
                
                #check target of nodes to make sure corret model is hovered
                n0, n1 = closest_seg.n0, closest_seg.n1
                #if self.net_ui_context.target != None:
                #    if self.net_ui_context.target != self.net_ui_context.target_dict[n0]:
                #        return
                
                
                if n0.view.dot(view_vector) < 0 and n1.view.dot(view_vector) < 0:
                    return
            
                
                self.net_ui_context.hovered_near = ['EDGE', closest_seg]
                return
        
        
        
        ##Check distance between ray_cast point, and segments
        #distance_map = {}
        #notice InputNet not SplineNet!  We could also check against BMFaceMap for the cut data
        #for seg in self.input_net.segments:  #TODO, may need to decide some better naming and better hierarchy
        #    close_loc, close_d = self.closest_point_3d_linear(seg, loc)
        #    distance_map[seg] = close_d if close_loc else float('inf')

        #if self.input_net.segments:
        #    closest_seg = min(self.input_net.segments, key = lambda x: distance_map[x])

        #    a = loc3d_reg2D(context.region, context.space_data.region_3d, closest_seg.ip0.world_loc)
        #    b = loc3d_reg2D(context.region, context.space_data.region_3d, closest_seg.ip1.world_loc)

        #    if a and b:  #if points are not on the screen, a or b will be None
        #        intersect = intersect_point_line(mouse_vec.to_3d(), a.to_3d(),b.to_3d())
        #        dist = (intersect[0].to_2d() - mouse_vec).length_squared
        #        bound = intersect[1]
        #        if (dist < select_radius**2) and (bound < 1) and (bound > 0):
        #            spline_seg = closest_seg.parent_spline
        #            self.net_ui_context.hovered_near = ['EDGE', spline_seg]
        #            return
        #

    def hover_spline2d(self, select_radius=12, snap_radius=24): #TODO, these radii are pixels? Should they be settings?
        '''
        finds points/edges/etc that are near ,mouse
         * hovering happens in mixed 3d and screen space, 20 pixels thresh for points, 30 for edges 40 for non_man
        '''

        self.net_ui_context.snap_element    = None
        self.net_ui_context.connect_element = None
        self.net_ui_context.hovered_near    = [None, -1]
        self.net_ui_context.hovered_dist2D  = float('inf')
        self.net_ui_context.closest_ep      = None

        # TODO: update self.hover to use Accel2D?
        mouse = self.actions.mouse
        mouse_vec = Vector(mouse)
        context = self.context
        #mx, imx, mx_no, imx_no = self.net_ui_context.get_target_matrices()
        #bvh = self.net_ui_context.get_target_bvh()
        
        loc3d_reg2D = view3d_utils.location_3d_to_region_2d

        if self.spline_net.is_empty:
            # no points to be near
            return
        # find length between vertex and mouse
        def dist(v): return (v - mouse_vec).length if v else float('inf')
        # find length between 2 3d points
        
        #closest_3d_loc = min(self.spline_net.world_locs, key = dist3d)
        #closest_ip = min(self.spline_net.points, key = lambda x: dist3d(x.world_loc))
        closest_ip = min(self.spline_net.points, key = lambda x: dist(loc3d_reg2D(context.region, context.space_data.region_3d, x.world_loc)))
        pixel_dist = dist(loc3d_reg2D(context.region, context.space_data.region_3d, closest_ip.world_loc))

        if pixel_dist < select_radius:
            # the mouse is hovering over a point
            self.net_ui_context.hovered_near = ['POINT', closest_ip]  #TODO, probably just store the actual InputPoint as the 2nd value?
            self.net_ui_context.hovered_dist2D = pixel_dist
            return


        ##Check distance between ray_cast point, and linear appox of segments
        #TODO, do tesselated segments
        
        
        distance_map = {}
        for seg in self.spline_net.segments:
            a = loc3d_reg2D(context.region, context.space_data.region_3d, seg.n0.world_loc)
            b = loc3d_reg2D(context.region, context.space_data.region_3d, seg.n1.world_loc)

            if a and b:  #if points are not on the screen, a or b will be None
                intersect = intersect_point_line(mouse_vec.to_3d(), a.to_3d(),b.to_3d())
                dist = (intersect[0].to_2d() - mouse_vec).length_squared
                bound = intersect[1]
                if (bound < 1) and (bound > 0):
                    #spline_seg = closest_seg.parent_spline
                    distance_map[seg] = dist
    
                else:
                    distance_map[seg] = float('inf')
                    
        if not len(distance_map):
            self.net_ui_context.hovered_near = [None, -1]
            return    
        closest_seg = min(self.spline_net.segments, key = lambda x: distance_map[x])
        dist = distance_map[closest_seg]
        if (dist < snap_radius**2):   
            self.net_ui_context.hovered_near = ['EDGE', closest_seg]
        
        
        
    def cache_to_splines(self):
        
        if self.bar == None: return
        
        self.bar.cache_rim_object()
        
        
    def cache_to_bmesh(self):
        return #TODO
    
        bme_cache = bmesh.new()
        node_to_bmv = {}
        
        #edge_id = bme_cache.verts.layers.int.new('edgepoint')
        
        edgepoints = set()
        for node in self.spline_net.points:
            
            bmv = bme_cache.verts.new(node.world_loc)
            bmv.normal = node.view
            node_to_bmv[node] = bmv
            
            if node.is_edgepoint():
                edgepoints.add(bmv)
            #    bmv[edge_id] = 1
            #else:
            #    bmv[edge_id] = 0
        for seg in self.spline_net.segments:
            bmv0 = node_to_bmv[seg.n0]
            bmv1 = node_to_bmv[seg.n1]
            
            bme_cache.edges.new((bmv0, bmv1))
            
        if 'Splint Margin' not in bpy.data.objects:
            margin_me = bpy.data.meshes.new('Splint Margin')
            margin_ob = bpy.data.objects.new('Splint Margin', margin_me)
            bpy.context.scene.objects.link(margin_ob)
            
            edge_point_group = margin_ob.vertex_groups.new('edgpoints')
            
        else:
            margin_ob = bpy.data.objects.get('Splint Margin')
            margin_me = margin_ob.data
            edge_point_group = margin_ob.vertex_groups.get('edgpoints')
        
        margin_ob.hide = True
        bme_cache.verts.ensure_lookup_table()
        bme_cache.verts.index_update()
        
            
        bme_cache.to_mesh(margin_me)
        edgepoint_inds = [bmv.index for bmv in edgepoints]
        edge_point_group.remove([i for i in range(0, len(bme_cache.verts))])
        edge_point_group.add(edgepoint_inds, 1, type = 'REPLACE')
        bme_cache.free()
        
    
    def load_splinenet_from_curves(self):
        
        return
        
        max_curve = bpy.data.objects.get('Occlusal Curve Max')
        mand_curve = bpy.data.objects.get('Occlusal Curve Mand')
        
        if  max_curve == None or mand_curve == None: return
        
        mx_max = max_curve.matrix_world
        mx_mand = mand_curve.matrix_world
        view = Vector((0,0,1))
        
        new_pts = []
        new_segs = []
        
        #Add in Maxillary Points   
        prev_pnt = None
        for bp in max_curve.data.splines[0].bezier_points:
            loc = mx_max * bp.co
            local_loc = loc
            new_pnt = CurveNode(loc, local_loc, view, face_ind = -1)
            #self.net_ui_context.target_dict[new_pnt] = 'MAX'
            new_pts.append(new_pnt)
            self.spline_net.points.append(new_pnt)
            if prev_pnt:
                seg = SplineSegment(prev_pnt,new_pnt)
                self.spline_net.segments.append(seg)
                new_segs.append(seg)
            prev_pnt = new_pnt
        
        #Add in Mandibular Points
        prev_pnt = None
        for bp in mand_curve.data.splines[0].bezier_points:
            loc = mx_mand * bp.co
            local_loc = loc
            new_pnt = CurveNode(loc, local_loc, view, face_ind = -1)
            #self.net_ui_context.target_dict[new_pnt] = 'MAND'
            new_pts.append(new_pnt)
            self.spline_net.points.append(new_pnt)
            if prev_pnt:
                seg = SplineSegment(prev_pnt,new_pnt)
                self.spline_net.segments.append(seg)
                new_segs.append(seg)
            prev_pnt = new_pnt
            
                
        for node in new_pts:
            node.calc_handles()
        for seg in new_segs:
            seg.calc_bezier()
            seg.tessellate()
            seg.is_inet_dirty = True
            
    def save_splinenet_to_curves(self):
        ip_cycles, seg_cycles = self.spline_net.find_network_open_cycles()
        
        if len(ip_cycles) != 2: return
        
        
        #do make sure the endpoints are aligned
        if (ip_cycles[0][0].world_loc - ip_cycles[1][0].world_loc).length > (ip_cycles[0][0].world_loc - ip_cycles[1][-1].world_loc).length:
            ip_cycles[0].reverse()
        
        #determin who is top and bottom        
        if ip_cycles[0][0].world_loc[2] > ip_cycles[1][0].world_loc[2]:
            max_path, mand_path = ip_cycles[0], ip_cycles[1]
        else:
            max_path, mand_path = ip_cycles[1], ip_cycles[0]
        
        
        if "Occlusal Curve Max" in bpy.data.objects:
            max_ob = bpy.data.objects.get("Occlusal Curve Max")
            #clear old spline data, dont remove items form list while iterating over it
            max_spline_data = max_ob.data
            splines = [s for s in max_spline_data.splines]
            for s in splines:
                max_spline_data.splines.remove(s)
        else:
            max_spline_data = bpy.data.curves.new("Occlusal Curve Max", "CURVE")
            max_ob = bpy.data.objects.new("Occlusal Curve Max", max_spline_data)
            bpy.context.scene.objects.link(max_ob)
            max_ob.parent = self.net_ui_context.max_model
            max_ob.matrix_world = self.net_ui_context.max_model.matrix_world
        
        if "Occlusal Curve Mand" in bpy.data.objects:
            mand_ob = bpy.data.objects.get("Occlusal Curve Mand")
            mand_spline_data = mand_ob.data
            splines = [s for s in mand_ob.data.splines]
            for s in splines:
                mand_spline_data.splines.remove(s)
        else:
            mand_spline_data = bpy.data.curves.new("Occlusal Curve Mand", "CURVE")
            mand_ob = bpy.data.objects.new("Occlusal Curve Mand", mand_spline_data)
            bpy.context.scene.objects.link(mand_ob)
            mand_ob.parent = self.net_ui_context.mand_model
            mand_ob.matrix_world = self.net_ui_context.mand_model.matrix_world
            
        spline = mand_spline_data.splines.new('BEZIER')
        spline.bezier_points.add(count = len(mand_path) - 1)
        imx_mand = mand_ob.matrix_world.inverted()
        for i, node in enumerate(mand_path):
            bpt = spline.bezier_points[i]
            bpt.handle_right_type = 'AUTO'
            bpt.handle_left_type = 'AUTO'
            bpt.co = imx_mand * node.world_loc
            
        spline = max_spline_data.splines.new('BEZIER')
        spline.bezier_points.add(count = len(max_path) - 1)
        imx_max = max_ob.matrix_world.inverted()
        for i, node in enumerate(max_path):
            bpt = spline.bezier_points[i]
            bpt.handle_right_type = 'AUTO'
            bpt.handle_left_type = 'AUTO'
            bpt.co = imx_max * node.world_loc
                 
    
    
    def splinenet_to_occlusal_plane(self):
        ip_cycles, seg_cycles = self.spline_net.find_network_open_cycles()
        
        if len(ip_cycles) != 2: return
        
        
        #do make sure the endpoints are aligned
        if (ip_cycles[0][0].world_loc - ip_cycles[1][0].world_loc).length > (ip_cycles[0][0].world_loc - ip_cycles[1][-1].world_loc).length:
            ip_cycles[0].reverse()
        
        #determin who is top and bottom        
        if ip_cycles[0][0].world_loc[2] > ip_cycles[1][0].world_loc[2]:
            max_path, mand_path = ip_cycles[0], ip_cycles[1]
        else:
            max_path, mand_path = ip_cycles[1], ip_cycles[0]
        
        if self.splint.jaw_type == 'MAXILLA':
            vs = [node.world_loc for node in mand_path]
            Z_normal = Vector((0,0,1))
            Follow = bpy.data.objects.get(self.splint.get_maxilla())
        else:
            vs = [node.world_loc for node in max_path]
            Z_normal = Vector((0,0,-1))
            Follow = bpy.data.objects.get(self.splint.get_mandible())
        
        
        Zfit = odcutils.calculate_plane(vs, itermax = 500, debug = False)
        X = Vector((1,0,0))
        center = Vector((0,0,0))
        for v in vs:
            center += 1/len(vs) * v
            
        if Zfit.dot(Z_normal) < 0:
            Zfit *= -1
        
        Y = Zfit.cross(X)
        Xfit = Y.cross(Zfit)
           
        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = Xfit[0] ,Y[0],  Zfit[0]
        R[1][0], R[1][1], R[1][2]  = Xfit[1], Y[1],  Zfit[1]
        R[2][0] ,R[2][1], R[2][2]  = Xfit[2], Y[2],  Zfit[2]
        
        R = R.to_4x4()
        T = Matrix.Translation(center - 4 * Zfit)
        
        bme = bmesh.new()
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        bmesh.ops.create_grid(bme, x_segments = 200, y_segments = 200, size = 39.9)
            
        if 'Dynamic Occlusal Surface' not in bpy.data.objects:
            
            me = bpy.data.meshes.new('Dynamic Occlusal Surface')
            bme.to_mesh(me)
            plane_obj = bpy.data.objects.new('Dynamic Occlusal Surface', me)
            plane_obj.matrix_world = T * R
        
            mat = bpy.data.materials.get("Plane Material")
            if mat is None:
                # create material
                mat = bpy.data.materials.new(name="Plane Material")
                mat.diffuse_color = Color((0.8, 1, .9))
            
            plane_obj.data.materials.append(mat)
            bpy.context.scene.objects.link(plane_obj)
            plane_obj.hide = True
        else:
            plane_obj = bpy.data.objects.get('Dynamic Occlusal Surface')
            plane_obj.matrix_world = T * R
            
        bme.free()
         
        
        if Follow != None:
            for cons in plane_obj.constraints:
                    if cons.type == 'CHILD_OF':
                        plane_obj.constraints.remove(cons)
            
            cons = plane_obj.constraints.new('CHILD_OF')
            cons.target = Follow
            cons.inverse_matrix = Follow.matrix_world.inverted()
            

        bme.free()
        
        
        
    def end_commit(self):
        
        prefs = get_settings()
        self.context.space_data.show_backface_culling = False

        #save curves
        self.save_splinenet_to_curves()
  
        bpy.ops.ed.undo_push()
        print('end commit')
        
        
    def end_cancel(self):
        
        return
        
        #self.set_visualization_end()
        
        #potentiall do an undo_push