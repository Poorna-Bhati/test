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


from ..bmesh_fns import edge_loops_from_bmedges_old, ensure_lookup, new_bmesh_from_bmelements
from ..common.utils import get_matrices
from ..common.rays import get_view_ray_data, ray_cast, ray_cast_path, ray_cast_bvh

from .smargin_datastructure import InputNetwork, InputPoint, InputSegment, SplineSegment, CurveNode, BezierBar

import bgl
from bpy_extras import view3d_utils
from mathutils import Vector, kdtree, Color
from mathutils.geometry import intersect_point_line, intersect_line_plane
from mathutils.bvhtree import BVHTree
from ..bmesh_fns import grow_selection, edge_loops_from_bmedges_old, flood_selection_by_verts, flood_selection_edge_loop, ensure_lookup
from ..common.maths import space_evenly_on_path, intersect_path_plane
from ..common.bezier import CubicBezierSpline
from ..common.simplify import simplify_RDP
from ..geodesic import geodesic_walk

class Polytrim_UI_Tools():
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
            mx, imx, mx_norm, imx_norm = self.net_ui_context.get_target_matrices()
            bvh = self.net_ui_context.get_target_bvh()
                
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
            mx, imx, mx_norm, imx_norm = self.net_ui_context.get_target_matrices()
            bvh = self.net_ui_context.get_target_bvh()
    
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
                print(n)
                               
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
                        
        
                    self.snap_splines()
        
        def move_grab_point_2D(self, context, mouse_loc):
            x, y = mouse_loc
            
            #get mouse position at depth of the extrusion midpoint
            mouse_projected = view3d_utils.region_2d_to_location_3d(context.region, context.region_data, (x,y), self.backup_data["world_loc"])
            mx, imx, mx_no, imx_no = self.net_ui_context.get_target_matrices()
            
            self.grab_point.world_loc = mouse_projected
            self.grab_point.local_loc = imx * mouse_projected


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
            return None
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
                    if snap: snap_pts += [snap]
            
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
        def __init__(self, context, max_model, mand_model):
            self.context = context
            
            #### I DONT KNOW THAT THIS NEEDS TO GO IN NET UI CONTEXT ####
            self.max_model = max_model
            self.mand_model = mand_model

            self.target = 'MAX'  #Or MAND and in fiture or RIM 
            self.target_dict = {}
            
            context.scene.render.engine = 'BLENDER_RENDER'
            context.space_data.show_manipulator = False
            context.space_data.viewport_shade = 'SOLID'  #TODO until smarter drawing
            context.space_data.show_textured_solid = False #TODO until smarter patch drawing
            context.space_data.show_backface_culling = True
        
            #TODO, make this a dictionary!
            self.max_bvh = BVHTree.FromObject(max_model, context.scene)
            self.mand_bvh = BVHTree.FromObject(mand_model, context.scene)
            self.rim_bvh = None
            
            self.max_mx, self.max_imx = get_matrices(self.max_model) 
            self.max_mx_norm = self.max_imx.transposed().to_3x3() #local directions to global
            self.max_imx_norm = self.max_imx.to_3x3() #global direction to local
            
            self.mand_mx, self.mand_imx = get_matrices(self.mand_model) 
            self.mand_mx_norm = self.mand_imx.transposed().to_3x3() #local directions to global
            self.mand_imx_norm = self.mand_imx.to_3x3()
            
            
            self.mouse_loc = None

            self.hovered_mesh = {}

            # TODO: Organize everything below this
            self.selected = None
            self.snap_element = None
            self.connect_element = None
            #self.closest_ep = None
            self.hovered_near = [None, -1]

   
        def get_target_matrices(self):
            if self.target == 'MAX':
                return self.max_mx, self.max_imx, self.max_mx_norm, self.max_imx_norm
            else:
                return self.mand_mx, self.mand_imx, self.mand_mx_norm, self.mand_imx_norm
        
        def get_target_bvh(self):
            
            if self.target == 'MAX':
                return self.max_bvh
            elif self.target == 'MAND':
                return self.mand_bvh
            elif self.target == 'RIM':
                return self.rim_bvh
                
        def is_hovering_mesh(self): 
            if self.hovered_mesh: return self.hovered_mesh["face index"] != -1
            return False
        

        def closest_world_loc(self, loc, model = 'MAX'):
            
            if model == 'MAX':
                local_loc = self.max_imx * loc
                loc, no, face_ind, d =  self.max_bvh.find_nearest(local_loc)
                if loc:
                    return self.max_mx * loc
            else:
                local_loc = self.mand_imx * loc
                loc, no, face_ind, d =  self.mand_bvh.find_nearest(local_loc)
                
                if loc:
                    return self.mand_mx * loc
            
        

        def update(self, mouse_loc):
            self.mouse_loc = mouse_loc
            self.ray_cast_mouse()

            #self.nearest_non_man_loc()

        def ray_cast_mouse(self):
            view_vector, ray_origin, ray_target= get_view_ray_data(self.context, self.mouse_loc)
            
            if self.target == 'MAX':
                loc, no, face_ind = ray_cast_bvh(self.max_bvh, self.max_imx, ray_origin, ray_target, None)
            else:
                loc, no, face_ind = ray_cast_bvh(self.mand_bvh, self.mand_imx, ray_origin, ray_target, None)
            
            if face_ind == None: self.hovered_mesh = {}
            
            else:
                if self.target == 'MAX':
                    self.hovered_mesh["world loc"] = self.max_mx * loc
                else:
                    self.hovered_mesh["world loc"] = self.mand_mx * loc
                self.hovered_mesh["local loc"] = loc
                self.hovered_mesh["normal"] = no
                self.hovered_mesh["face index"] = face_ind
                self.hovered_mesh["view"] = view_vector
              
        
    def set_visualization(self, mode = 'MAX'):
        if mode == 'MAX':
            max_trans = False
            mand_trans = True
        elif mode == 'MAND':
            max_trans = True
            mand_trans = False
        elif mode == 'BOTH':
            max_trans = False
            mand_trans = False
        elif mode == 'NONE':
            max_trans = True
            mand_trans = True
                
        self.max_model.hide = False
        self.mand_model.hide = False
        
        self.max_model.show_transparent = max_trans
        self.mand_model.show_transparent = mand_trans
        
    
    def set_max_mode(self):
        self.net_ui_context.target = 'MAX'
        self.set_visualization(mode = 'MAX')
        
    def set_mand_mode(self):
        self.net_ui_context.target = 'MAND'
        self.set_visualization(mode = 'MAND')
    
    def set_2d_mode(self):    
        self.net_ui_context.target = None
        self.set_visualization(mode = 'NONE')
    
    
        
    def add_spline(self, endpoint0, endpoint1):
        assert endpoint0.is_endpoint and endpoint1.is_endpoint  #NO nodes with genus > 2
        
        assert endpoint0 in self.net_ui_context.target_dict
        assert endpoint1 in self.net_ui_context.target_dict
        
        if self.net_ui_context.target_dict[endpoint0] != self.net_ui_context.target_dict[endpoint1]:
            return
        
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
        mx, imx, mx_n, imx_n = self.net_ui_context.get_target_matrices()
        p = self.spline_net.create_point(mx * loc, loc, view, ind)
        self.net_ui_context.target_dict[p] = self.net_ui_context.target
        return p
    
    def insert_spline_point(self, p2d):
        p = self.add_point(p2d)
        if not p: return None
        seg = self.net_ui_context.hovered_near[1]
        n0, n1 = seg.n0, seg.n1   
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
        if curve_point in self.net_ui_context.target_dict:
            self.net_ui_context.target_dict.remove(curve_point)
            
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

    
    def toggle_preview_rim(self):
        self.live_rim_preview = self.live_rim_preview == False
        if self.live_rim_preview:
            self.preview_rim()
    
    def get_rim_object(self):
        if 'Wax Rim' not in bpy.data.objects:
            me = bpy.data.meshes.new('Wax Rim')
            new_ob = bpy.data.objects.new('Wax Rim', me)
            bpy.context.scene.objects.link(new_ob)
            new_ob.show_transparent = True
            
            mat = bpy.data.materials.get("Splint Material")
            if mat is None:
            # create material
                mat = bpy.data.materials.new(name="Splint Material")
                mat.diffuse_color = Color((.2, .4, .5))
                mat.use_transparency = True
                mat.transparency_method = 'Z_TRANSPARENCY'
                mat.alpha = .4
        
            new_ob.data.materials.append(mat)
            
            #displace modifier?
            
            bmod = new_ob.modifiers.new('Bevel', type = 'BEVEL')
            bmod.offset_type = 'WIDTH'
            bmod.limit_method = 'ANGLE'
            bmod.width = 1.0
            bmod.segments = 4
            bmod.profile = 0.25
            
            dmod = new_ob.modifiers.new('Displace', type = 'DISPLACE')
            dmod.strength = 1.5

        else:
            new_ob = bpy.data.objects.get('Wax Rim')
            new_ob.hide = False
            new_ob.show_transparent = True
        
        return new_ob
    
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
    
    
    def max_mand_to_bar_paths(self, Z, max_path, mand_path):
        #later, these will be spit out into new curves in a live bar object
        centroid, tangents, ub, ul, ll, lb = [], [], [], [], [], []
        
        for i in range(0, len(max_path)):
            
            v0_0 = max_path[i]
            if i > 0 and i < len(max_path)-1:
                v0_p1 = max_path[i+1]
                v0_m1 = max_path[i-1]    
                tan_vect = v0_p1 - v0_m1
                
            if i == 0:
                v0_p1 = max_path[i+1]
                tan_vect = v0_p1 - v0_0
            elif i == len(max_path) -1:
                v0_m1 = max_path[i-1]
                tan_vect = v0_0 - v0_m1
                
            tan_vect.normalize()
            
            #make sure we have plane intersection within 20mm
            mand_point = intersect_path_plane(mand_path, v0_0, tan_vect)
            
            if mand_point:
                mid = .5 * (mand_point + v0_0)
                diag = v0_0 - mand_point
                
                reflection = Z.cross(tan_vect)
                
                diag_reflect = diag - 2 * diag.dot(reflection) * reflection
                
                ll += [mand_point]
                ub += [v0_0]
                ul += [mid + .5 * diag_reflect]
                lb += [mid - .5 * diag_reflect]
                centroid += [mid]
                tangents += [tan_vect]
        #check direction/winding
        #ub, lb, ll, ul = CCW winding when going from right to left around the arch
        #ub, ul, ll, lb  = CCW winding when going from left to right around the arch
        ig = lb[0] - ub[0]
        bl = ll[0] - lb[0]
        tan_p = ig.cross(bl)
        
        if tan_p.dot(tangents[0]) < 0:
            ll.reverse()
            ub.reverse()
            ul.reverse()
            lb.reverse()
            centroid.reverse()
            tangents.reverse()
            tangents = [-1 * t for t in tangents]
                
        return centroid, tangents, ub, ul, ll, lb
    
        
    def preview_rim(self, spline_res = 80):
        if not self.live_rim_preview:
            ob = bpy.data.objects.get('Wax Rim')
            if ob:
                ob.hide = True  
            return
        
        #once we have converted to a rim
        if self.bar != None:
            self.bar.tessellate_bar()
            return
        
        new_ob = self.get_rim_object()
        bme = bmesh.new()
        ip_cycles, seg_cycles = self.spline_net.find_network_open_cycles()
        
        if len(ip_cycles) != 2: return
        
        #get an even tesselation
        cycle_data = zip(ip_cycles, seg_cycles)
        tess_cycles = self.tessellate_cycles(cycle_data, spline_res)
        
        #do make sure the endpoints are aligned
        if (tess_cycles[0][0] - tess_cycles[1][0]).length > (tess_cycles[0][0] - tess_cycles[1][-1]).length:
            tess_cycles[1].reverse()
        
        
        
        if tess_cycles[0][0][2] > tess_cycles[1][0][2]:
            max_path, mand_path = tess_cycles[0], tess_cycles[1]
        else:
            max_path, mand_path = tess_cycles[1], tess_cycles[0]
        
        Z = Vector((0,0,1))  #todo, possibly best fit plane?
        
        centroid, tangents, ub, ul, ll, lb = self.max_mand_to_bar_paths(Z, max_path, mand_path)
            
        bvs3 = [bme.verts.new(v) for v in ub]
        bvs2 = [bme.verts.new(v) for v in lb]
        bvs1 = [bme.verts.new(v) for v in ll]
        bvs0 = [bme.verts.new(v) for v in ul]
            
    
        N = len(bvs0)
          
        #end caps
        bme.faces.new((bvs0[0], bvs1[0], bvs2[0], bvs3[0]))
        bme.faces.new((bvs3[N-1],bvs2[N-1], bvs1[N-1], bvs0[N-1]))
                
         
        for j in range(0,N-1):
            bme.faces.new((bvs0[j], bvs0[j+1], bvs1[j+1], bvs1[j]))  
            bme.faces.new((bvs1[j], bvs1[j+1], bvs2[j+1], bvs2[j]))  
            bme.faces.new((bvs2[j], bvs2[j+1], bvs3[j+1], bvs3[j]))  
            bme.faces.new((bvs3[j], bvs3[j+1], bvs0[j+1], bvs0[j]))
        bme.to_mesh(new_ob.data)
        bme.free()
        
        #if self.bar == None:
        #    self.bar = BezierBar(self.spline_net, new_ob)   
        #    self.bar.from_paths_uniform_nodes([ub,lb,ll,ul])
        return
    
    
    
    def edit_rim_enter(self):
        '''
        no going back after this!
        '''
        new_ob = self.get_rim_object()
        bme = bmesh.new()
        ip_cycles, seg_cycles = self.spline_net.find_network_open_cycles()
        
        if len(ip_cycles) != 2: return
        
        #get an even tesselation
        cycle_data = zip(ip_cycles, seg_cycles)
        tess_cycles = self.tessellate_cycles(cycle_data, 80)
        
        #make sure the endpoints are aligned
        if (tess_cycles[0][0] - tess_cycles[1][0]).length > (tess_cycles[0][0] - tess_cycles[1][-1]).length:
            tess_cycles[1].reverse()
        
        #check which is the maxillary vs mandibular spline
        if tess_cycles[0][0][2] > tess_cycles[1][0][2]:
            max_path, mand_path = tess_cycles[0], tess_cycles[1]
        else:
            max_path, mand_path = tess_cycles[1], tess_cycles[0]
        
        #generate 4 vert paths, do plane intersections to make sure
        #the ends are aligned, check winding etc.
        Z = Vector((0,0,1))  #todo, possibly best fit plane?
        centroid, tangents, ub, ul, ll, lb = self.max_mand_to_bar_paths(Z, max_path, mand_path)
        
        #create a bar object
        if self.bar == None:
            self.bar = BezierBar(self.spline_net, new_ob)   
        
        #write out the max and mand curves to blender data!
        #parent them to max and mand object
        self.spline_net.points = []
        self.spline_net.segments = []
        
        self.bar.from_paths_uniform_nodes([ub,lb,ll,ul])
        self.bar.tessellate_bar()
        
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
        mx, imx, mx_no, imx_no = self.net_ui_context.get_target_matrices()
        bvh = self.net_ui_context.get_target_bvh()
        
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

        loc = mx * loc      # transform loc to world
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
        mx, imx, mx_no, imx_no = self.net_ui_context.get_target_matrices()
        bvh = self.net_ui_context.get_target_bvh()
        
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
        
    def load_from_bar_object(self):
        '''
        '''
        
        
    def end_commit(self):
        print('end commit')
        
        
    def end_cancel(self):
        print('end cancel')
        #remove the patch material from the object
        