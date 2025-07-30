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

from .wax_curve_datastructure import InputNetwork, InputPoint, InputSegment, SplineSegment, CurveNode

import bgl
from ..common.utils import get_settings

from bpy_extras import view3d_utils
from mathutils import Vector, kdtree, Color, Matrix
from mathutils.geometry import intersect_point_line, intersect_line_plane
from mathutils.bvhtree import BVHTree
from ..bmesh_fns import grow_selection, edge_loops_from_bmedges_old, flood_selection_by_verts, flood_selection_edge_loop, ensure_lookup
from ..common.maths import space_evenly_on_path, intersect_path_plane
from ..common.bezier import CubicBezierSpline
from ..common.simplify import simplify_RDP
from ..common.maths import get_path_length



class WaxCurve_UI_Tools():
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
        def __init__(self, context, model):
            self.context = context
            
            #### I DONT KNOW THAT THIS NEEDS TO GO IN NET UI CONTEXT ####
            self.model = model
            

            self.target = 'MODEL'  #Or None 
            self.target_dict = {}
            
            context.scene.render.engine = 'BLENDER_RENDER'
            context.space_data.show_manipulator = False
            context.space_data.viewport_shade = 'SOLID'  #TODO until smarter drawing
            context.space_data.show_textured_solid = False #TODO until smarter patch drawing
            #context.space_data.show_backface_culling = True
        
            #TODO, make this a dictionary!
            self.model_bvh = BVHTree.FromObject(model, context.scene)
            self.rim_bvh = None
            
            self.model_mx, self.model_imx = get_matrices(self.model) 
            self.model_mx_norm = self.model_imx.transposed().to_3x3() #local directions to global
            self.model_imx_norm = self.model_imx.to_3x3() #global direction to local
            
            #self.mand_mx, self.mand_imx = get_matrices(self.mand_model) 
            #self.mand_mx_norm = self.mand_imx.transposed().to_3x3() #local directions to global
            #self.mand_imx_norm = self.mand_imx.to_3x3()
            
            
            self.mouse_loc = None

            self.hovered_mesh = {}

            # TODO: Organize everything below this
            self.selected = None
            self.snap_element = None
            self.connect_element = None
            #self.closest_ep = None
            self.hovered_near = [None, -1]

        #TODO, dictionaries!?
        def get_target_matrices(self):
            #if self.target == 'MODEL':
            return self.model_mx, self.model_imx, self.model_mx_norm, self.model_imx_norm
            #elif self.target == 'MAND':
            #    return self.mand_mx, self.mand_imx, self.mand_mx_norm, self.mand_imx_norm
        
        def get_target_matrices_by_name(self, target):
            #if target == 'MODEL':
            return self.model_mx, self.model_imx, self.model_mx_norm, self.model_imx_norm
            #elif target == 'MAND':
            #    return self.mand_mx, self.mand_imx, self.mand_mx_norm, self.mand_imx_norm
   
        def get_target_bvh(self):
            
            if self.target == 'MODEL':
                return self.model_bvh
            #elif self.target == 'MAND':
            #    return self.mand_bvh
            #elif self.target == 'RIM':
            #    return self.rim_bvh
            else:
                return self.model_bvh
            
        def is_hovering_mesh(self): 
            if self.hovered_mesh: return self.hovered_mesh["face index"] != -1
            return False
        

        def closest_world_loc(self, loc, model = 'MODEL'):
            
            if model == 'MODEL':
                local_loc = self.model_imx * loc
                loc, no, face_ind, d =  self.model_bvh.find_nearest(local_loc)
                if loc:
                    return self.model_mx * loc
            #else:
            #    local_loc = self.mand_imx * loc
            #    loc, no, face_ind, d =  self.mand_bvh.find_nearest(local_loc)
                
            #    if loc:
            #        return self.mand_mx * loc
            
        

        def update(self, mouse_loc):
            self.mouse_loc = mouse_loc
            self.ray_cast_mouse()

            #self.nearest_non_man_loc()

        def ray_cast_mouse(self):
            view_vector, ray_origin, ray_target= get_view_ray_data(self.context, self.mouse_loc)
            
            if self.target == 'MODEL':
                loc, no, face_ind = ray_cast_bvh(self.model_bvh, self.model_imx, ray_origin, ray_target, None)
            elif self.target == 'MAND':
                loc, no, face_ind = ray_cast_bvh(self.mand_bvh, self.mand_imx, ray_origin, ray_target, None)
            
            else: 
                self.hovered_mesh = {}
                return
                
            if face_ind == None:    
                self.hovered_mesh = {}
                return
            
            else:
                if self.target == 'MODEL':
                    self.hovered_mesh["world loc"] = self.model_mx * loc
                else:
                    self.hovered_mesh["world loc"] = self.mand_mx * loc
                self.hovered_mesh["local loc"] = loc
                self.hovered_mesh["normal"] = no
                self.hovered_mesh["face index"] = face_ind
                self.hovered_mesh["view"] = view_vector
              
        
    def set_visualization(self, mode = 'MODEL'):
        if mode == 'MODEL':
            model_trans = False
           
        #elif mode == 'MAND':
        #    max_trans = True
        #    mand_trans = False
        #elif mode == 'BOTH':
        #    max_trans = False
        #    mand_trans = False
        elif mode == 'NONE':
            model_trans = True

        self.model.hide = False
        self.model.show_transparent = model_trans
        self.wax_obj.show_transparent = True
        
    def set_visualization_end(self):
        self.model.show_transparent = False
        self.wax_obj.show_transparent = False
        
        #rim = bpy.data.objects.get("Wax Rim")
        #if rim:
        #    rim.show_transparent = False
            
    def set_model_mode(self):
        self.net_ui_context.target = 'MODEL'
        self.set_visualization(mode = 'MODEL')
        #bpy.ops.view3d.viewnumpad(type = 'BOTTOM')
        
    #def set_mand_mode(self):
    #    self.net_ui_context.target = 'MAND'
    #    self.set_visualization(mode = 'MAND')
    #    bpy.ops.view3d.viewnumpad(type = 'TOP')
    
    
    def set_wax_alpha(self):
        alpha = self.wax_alpha
        mat = bpy.data.materials.get("Wax Material")
        if not mat: return
        mat.alpha = alpha
        return
        
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
        
        seg = self.net_ui_context.hovered_near[1]
        n0, n1 = seg.n0, seg.n1 
        
        if self.net_ui_context.target != None:
            p = self.add_point(p2d)
        else:
            context = self.context
            mid = .5 * (n0.world_loc + n1.world_loc)
            real_mid =  view3d_utils.region_2d_to_location_3d(context.region, context.region_data, self.actions.mouse, mid)
            target = self.net_ui_context.target_dict[n0]
            mx, imx, mxno, imxno = self.net_ui_context.get_target_matrices_by_name(target)
            p = self.spline_net.create_point(real_mid, imx * real_mid, Vector((0,0,1)), -1)
            self.net_ui_context.target_dict[p] = target  #<< Make sure we keep this point sorted
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
    
    def remove_meta_data(self):
        
        if 'Meta Wax' in bpy.data.objects:
            meta_obj = bpy.data.objects.get('Meta Wax')
            md = meta_obj.data
        
            bpy.data.objects.remove(meta_obj)
            bpy.data.metaballs.remove(md)
    
        if 'Wax Blobs' in bpy.data.objects:
       
            wax_obj = bpy.data.objects.get('Wax Blobs')
            wd = wax_obj.data
            bpy.data.objects.remove(wax_obj)
            bpy.data.meshes.remove(wd)
            
        
    
    def get_wax_material(self):
        mat = bpy.data.materials.get("Wax Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Wax Material")
            mat.diffuse_color = Color((.8, .4, .4))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .85
    
        return mat
            
                
    def make_wax_base(self, context):
        if 'Meta Wax' in bpy.data.objects:
            meta_obj = bpy.data.objects.get('Meta Wax')
            meta_data = meta_obj.data
        else:
            meta_data = bpy.data.metaballs.new('Meta Wax')
            meta_obj = bpy.data.objects.new('Meta Wax', meta_data)
            meta_data.resolution = .4
            meta_data.render_resolution = 1
            context.scene.objects.link(meta_obj)
        if 'Wax Blobs' not in bpy.data.objects:
            bone_me = bpy.data.meshes.new('Wax Blobs')
            bone_obj = bpy.data.objects.new('Wax Blobs', bone_me)
            context.scene.objects.link(bone_obj)
            smod = bone_obj.modifiers.new('Smooth', type = 'SMOOTH')
            smod.iterations = 10
        else:
            bone_obj = bpy.data.objects.get('Wax Blobs')
            bone_me = bone_obj.data
            
        meta_obj.hide = True
        bone_obj.hide = False
        mat = self.get_wax_material()
        bone_obj.data.materials.append(mat)
        meta_obj.data.materials.append(mat)
        bone_obj.material_slots[0].material = mat
        #meta_obj.matrix_world = context.object.matrix_world  #NOPE LIVES IN WORLD SPACE
        #bone_obj.matrix_world = context.object.matrix_world
        
        return bone_obj, meta_obj
    
    def clear_meta_wax(self):
        if 'Meta Wax' not in bpy.data.objects: return
        meta_obj = bpy.data.objects.get('Meta Wax')
        meta_data = meta_obj.data
        self.context.scene.objects.unlink(meta_obj)
        bpy.data.objects.remove(meta_obj)
        bpy.data.metaballs.remove(meta_data)
        
        
    def tessellate_cycles(self, cycle_data, stepsize):
        '''
        #TODO, handle closed and open cycles
        '''
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

            if ips[0] in segs[-1].points:  #this means cyclic
                pts = segs[-1].draw_tessellation.copy()
                if ips[0] == seg.n0:  #remmeber we are going back to the starting poin 
                    pts.reverse()
                    
                raw_tess_cyc += pts
            
            L = get_path_length(raw_tess_cyc)
            n_tess = int(max(3, L/stepsize))
            v_final, eds = space_evenly_on_path(raw_tess_cyc, [(0,1),(1,2)], n_tess)
            tess_cycles += [v_final]
            
        return tess_cycles
    
    
       
    def preview_rim_ball(self):
        
        ip_cycles, seg_cycles = self.spline_net.find_network_open_cycles()
        closed_cycles, closed_segs = self.spline_net.find_network_cycles()
        
        #get an even tesselation
        cycle_data = zip(ip_cycles+ closed_cycles, seg_cycles + closed_segs)
        tess_cycles = self.tessellate_cycles(cycle_data, self.blob_spacing)
        
        
        meta_data = self.meta_obj.data
        
        Z = Vector((0,0,1))  #todo, possibly best fit plane?
        
        total_mbs = len(meta_data.elements)
        n_mbs = 0
        for cyc in tess_cycles:
            for loc in cyc:
                #recyle metaballs
                if n_mbs > total_mbs -1:
                    mb = meta_data.elements.new(type = 'BALL')
                else:
                    mb = meta_data.elements[n_mbs]
                    mb.type = 'BALL'     
                mb.co = loc
                mb.radius = self.blob_size
                
                n_mbs += 1
                
        if n_mbs < total_mbs:
            remove_mbs = [meta_data.elements[n] for n in range(n_mbs,total_mbs)]
            for mb in remove_mbs:
                meta_data.elements.remove(mb)
        #if self.bar == None:
        #    self.bar = BezierBar(self.spline_net, new_ob)   
        #    self.bar.from_paths_uniform_nodes([ub,lb,ll,ul])
        self.update_wax_obj(self.context)
        return
    
    
    def preview_rim_cube(self):
        
        ip_cycles, seg_cycles = self.spline_net.find_network_open_cycles()
        closed_cycles, closed_segs = self.spline_net.find_network_cycles()
        
        #get an even tesselation
        cycle_data = zip(ip_cycles+ closed_cycles, seg_cycles + closed_segs)
        tess_cycles = self.tessellate_cycles(cycle_data, self.blob_spacing)
        
        
        meta_data = self.meta_obj.data
        
        Zworld = Vector((0,0,1))  #todo, possibly best fit plane
        
        mx, imx, mxno, imxno = self.net_ui_context.get_target_matrices()
        bvh = self.net_ui_context.get_target_bvh()
        
        total_mbs = len(meta_data.elements)
        n_mbs = 0
        for cyc in tess_cycles:
            for i, loc in enumerate(cyc):
                
                #generate our matrix which
                T = Matrix.Identity(3)
                #X is determiend by direction along curve
                if i == 0:
                    X = cyc[i+1] - cyc[i]   
                elif i == len(cyc) - 1:
                    X = cyc[i] - cyc[i-1]
                else:
                    X = cyc[i+1] - cyc[i-1]
                    
                X.normalize()
                 
                if self.cube_flat_side == 'NORMAL':
                    snap, normal, ind, d = bvh.find_nearest(imx * loc)
                    Y = mxno * normal
                    Z = X.cross(Y)
                    X_c   = Y.cross(Z)
                    
                else:
                    Z= Zworld
                    Y = Z.cross(X)
                    X_c = Y.cross(Z) #X corrected
            
                
                T.col[0] = X_c
                T.col[1] = Y
                T.col[2] = Z
                quat = T.to_quaternion()
            
               
                #recyle metaballs
                if n_mbs > total_mbs -1:
                    mb = meta_data.elements.new(type = 'CUBE')
                else:
                    mb = meta_data.elements[n_mbs]
                    mb.type = 'CUBE'
                

                mb.co = loc
                mb.radius = self.blob_radius #cubes are handled differently
                mb.size_z = self.blob_z
                mb.size_y = self.blob_y
                mb.size_x = self.blob_x
                mb.rotation = quat
                n_mbs += 1
                
        if n_mbs < total_mbs:
            remove_mbs = [meta_data.elements[n] for n in range(n_mbs,total_mbs)]
            for mb in remove_mbs:
                meta_data.elements.remove(mb)
                
        #if self.bar == None:
        #    self.bar = BezierBar(self.spline_net, new_ob)   
        #    self.bar.from_paths_uniform_nodes([ub,lb,ll,ul])
        
        self.update_wax_obj(self.context)
    
        
        return
    
    def get_preview_meta_res(self):
        
        if self.meta_preset == 'HIGH':
            return 0.1
        elif self.meta_preset == 'MEDIUM':
            return 0.4
        elif self.meta_preset == 'LOW':
            return 0.8
        elif self.meta_preset == 'FINAL':
            return self.final_meta_resolution
            
    def preview_rim(self):
        
        
        self.meta_obj.data.resolution = self.get_preview_meta_res()
        if self.blob_type == 'BALL':
            self.preview_rim_ball()
        else:
            self.preview_rim_cube()
            
            
            
            
            
            
    def update_wax_obj(self,context):
        
        context.scene.update()
        temp_me = self.meta_obj.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        old_me = self.wax_obj.data
        self.wax_obj.data = temp_me
        self.wax_obj.data.update()
        mat = self.get_wax_material()
        temp_me.materials.append(mat)
        bpy.data.meshes.remove(old_me)
        
        
         
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
        
        curve = bpy.data.objecst.get('Wax Curve')
        if not curve: return
        
        mx = curve.matrix_world
        view = Vector((0,0,1))
        
        
        
        #Add in Maxillary Points   
        prev_pnt = None
        for spline in curve.data.splines:
            new_pts = []
            new_segs = []
        
            for bp in spline.bezier_points:
                loc = mx * bp.co
                local_loc = loc
                new_pnt = CurveNode(loc, local_loc, view, face_ind = -1)
                self.net_ui_context.target_dict[new_pnt] = 'MAX'
                new_pts.append(new_pnt)
                self.spline_net.points.append(new_pnt)
                if prev_pnt:
                    seg = SplineSegment(prev_pnt,new_pnt)
                    self.spline_net.segments.append(seg)
                    new_segs.append(seg)
                prev_pnt = new_pnt
             
            if spline.use_cyclic_u:
                seg = SplineSegment(new_pts[0], new_pts[-1])   
                
            for node in new_pts:
                node.calc_handles()
            for seg in new_segs:
                seg.calc_bezier()
                seg.tessellate()
                seg.is_inet_dirty = True
            
    def save_splinenet_to_curves(self):
        open_ip_cycles, open_seg_cycles = self.spline_net.find_network_open_cycles()
        closed_ip_cycles, closed_seg_cycles = self.spline_net.find_network_cycles()
        
        if "Wax Curve" in bpy.data.objects:
            wax_ob = bpy.data.objects.get("Wax Curve")
            #clear old spline data, dont remove items from list while iterating over it
            wax_spline_data = wax_ob.data
            splines = [s for s in wax_spline_data.splines]
            for s in splines:
                wax_spline_data.splines.remove(s)
        else:
            wax_spline_data = bpy.data.curves.new("Wax Curve", "CURVE")
            wax_spline_data.dimensions = '3D'
            wax_ob = bpy.data.objects.new("Wax Curve", wax_spline_data)
            bpy.context.scene.objects.link(wax_ob)
            wax_ob.parent = self.model
            wax_ob.matrix_world = self.model.matrix_world
        
        imx_max = wax_ob.matrix_world.inverted()
        
        for cycle in open_ip_cycles:
            
            spline = wax_spline_data.splines.new('BEZIER')
            spline.bezier_points.add(count = len(cycle) - 1)
            
            for i, node in enumerate(cycle):
                bpt = spline.bezier_points[i]
                bpt.handle_right_type = 'AUTO'
                bpt.handle_left_type = 'AUTO'
                bpt.co = imx_max * node.world_loc
                 
    
        for cycle in closed_ip_cycles:
            spline = wax_spline_data.splines.new('BEZIER')
            spline.use_cyclic_u = True
            spline.bezier_points.add(count = len(cycle) - 1)
            for i, node in enumerate(cycle):
                bpt = spline.bezier_points[i]
                bpt.handle_right_type = 'AUTO'
                bpt.handle_left_type = 'AUTO'
                bpt.co = imx_max * node.world_loc
                 
                 
    def end_commit_post(self):  #use this to subclass
        pass 
    
    def end_commit(self):
        
        #save curves
        self.save_splinenet_to_curves()
        
        #set visualization
        self.set_visualization_end()
        
        #cleaunup metaball object
        self.clear_meta_wax()
        
        self.end_commit_post()
        
        bpy.ops.ed.undo_push()
        print('end commit')
        
        
    def end_cancel(self):
        
        self.set_visualization_end()
        print('end cancel')
        #remove the patch material from the object
        