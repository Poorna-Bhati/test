'''
A couple of helper classes for curves
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bgl
import bmesh
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_line, intersect_line_plane
from mathutils.bvhtree import BVHTree
from bpy_extras import view3d_utils
 
import bgl_utils
import common_drawing
import common_drawing_view
from mesh_cut import cross_section_2seeds_ver1, path_between_2_points, grow_selection_to_find_face, flood_selection_faces
import math
import random
import time
from common_utilities import bversion
import blf


class PolyLineKnife(object):
    '''
    A class which manages user placed points on an object to create a
    poly_line, adapted to the objects surface.
    '''
    def __init__(self,context, cut_object, ui_type = 'DENSE_POLY'):   
        self.cut_ob = cut_object
        self.bme = bmesh.new()
        self.bme.from_mesh(cut_object.data)
        self.bme.verts.ensure_lookup_table()
        self.bme.edges.ensure_lookup_table()
        self.bme.faces.ensure_lookup_table()
        
        self.bvh = BVHTree.FromBMesh(self.bme)
        
        self.cyclic = False
        self.pts = []
        self.cut_pts = []  #local points
        self.normals = []
        self.face_map = []
        self.face_changes = []
        self.new_cos = []
        self.ed_map = []
        self.ed_pcts = {}
        
        self.face_chain = set()  #all faces crossed by the cut curve
        if ui_type not in {'SPARSE_POLY','DENSE_POLY', 'BEZIER'}:
            self.ui_type = 'SPARSE_POLY'
        else:
            self.ui_type = ui_type
                
        self.selected = -1
        self.hovered = [None, -1]
        
        self.grab_undo_loc = None
        self.mouse = (None, None)
        
        #keep up with these to show user
        self.bad_segments = []
        self.split = False
        self.face_seed = None
    
        
        
    def reset_vars(self):
        '''
        TODOD, parallel workflow will make this obsolete
        '''
        self.cyclic = False
        self.pts = []
        self.cut_pts = []  #local points
        self.normals = []
        self.face_map = []
        self.face_changes = []
        self.new_cos = []
        self.ed_map = []
        self.ed_pcts = {}
        
        self.face_chain = set()  #all faces crossed by the cut curve
                
        self.selected = -1
        self.hovered = [None, -1]
        
        self.grab_undo_loc = None
        self.mouse = (None, None)
        
        #keep up with these to show user
        self.bad_segments = []
        self.face_seed = None
        
    def grab_initiate(self):
        if self.selected != -1:
            self.grab_undo_loc = self.pts[self.selected]
            return True
        else:
            return False
       
    def grab_mouse_move(self,context,x,y):
        region = context.region
        rv3d = context.region_data
        coord = x, y
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * 1000)

        mx = self.cut_ob.matrix_world
        imx = mx.inverted()
        if bversion() < '002.077.000':
            loc, no, face_ind = self.cut_ob.ray_cast(imx * ray_origin, imx * ray_target)
        else:
            ok, loc, no, face_ind = self.cut_ob.ray_cast(imx * ray_origin, imx * ray_target - imx*ray_origin)
        
        if face_ind == -1:        
            self.grab_cancel()  
        else:
            self.pts[self.selected] = mx * loc
            self.cut_pts[self.selected] = loc
            self.normals[self.selected] = no
            self.face_map[self.selected] = face_ind
        
    def grab_cancel(self):
        self.pts[self.selected] = self.grab_undo_loc
        return
    
    def grab_confirm(self):
        self.grab_undo_loc = None
        return
               
    def click_add_point(self,context,x,y):
        '''
        x,y = event.mouse_region_x, event.mouse_region_y
        
        this will add a point into the bezier curve or
        close the curve into a cyclic curve
        '''
        region = context.region
        rv3d = context.region_data
        coord = x, y
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * 1000)
        mx = self.cut_ob.matrix_world
        imx = mx.inverted()

        if bversion() < '002.077.000':
            loc, no, face_ind = self.cut_ob.ray_cast(imx * ray_origin, imx * ray_target)
        else:
            ok, loc, no, face_ind = self.cut_ob.ray_cast(imx * ray_origin, imx * ray_target - imx*ray_origin)
            
        if face_ind == -1: 
            self.selected = -1
            return
        
        if self.hovered[0] == None:  #adding in a new point
            self.pts += [mx * loc]
            self.cut_pts += [loc]
            self.normals += [no]
            self.face_map += [face_ind]
            self.selected = len(self.pts) -1
                
        if self.hovered[0] == 'POINT':
            self.selected = self.hovered[1]
            if self.hovered[1] == 0:  #clicked on first bpt, close loop
                self.cyclic = self.cyclic == False
            return
         
        elif self.hovered[0] == 'EDGE':  #cut in a new point
            self.pts.insert(self.hovered[1]+1, mx * loc)
            self.cut_pts.insert(self.hovered[1]+1, loc)
            self.normals.insert(self.hovered[1]+1, no)
            self.face_map.insert(self.hovered[1]+1, face_ind)
            self.selected = self.hovered[1] + 1
            return
    
    def click_delete_point(self, mode = 'mouse'):
        if mode == 'mouse':
            if not self.hovered[0] == 'POINT': return
            self.pts.pop(self.hovered[1])
            self.cut_pts.pop(self.hovered[1])
            self.normals.pop(self.hovered[1])
            self.face_map.pop(self.hovered[1])
        
        else:
            if self.selected == -1: return
            self.pts.pop(self.selected)
            self.cut_pts.pop(self.selected)
            self.normals.pop(self.selected)
            self.face_map.pop(self.selected)

    def hover(self,context,x,y):
        '''
        hovering happens in screen space, 20 pixels thresh for points, 30 for edges
        '''
        self.mouse = Vector((x, y))
        if len(self.pts) == 0:
            return

        def dist(v):
            diff = v - Vector((x,y))
            return diff.length
        
        loc3d_reg2D = view3d_utils.location_3d_to_region_2d
        screen_pts =  [loc3d_reg2D(context.region, context.space_data.region_3d, pt) for pt in self.pts]
        closest_point = min(screen_pts, key = dist)
        
        if (closest_point - Vector((x,y))).length  < 20:
            self.hovered = ['POINT',screen_pts.index(closest_point)]
            return

        if len(self.pts) < 2: 
            self.hovered = [None, -1]
            return
                    
        for i in range(0,len(self.pts)):   
            a  = loc3d_reg2D(context.region, context.space_data.region_3d,self.pts[i])
            next = (i + 1) % len(self.pts)
            b = loc3d_reg2D(context.region, context.space_data.region_3d,self.pts[next])
            
            if b == 0 and not self.cyclic:
                self.hovered = [None, -1]
                return
            
            if a and b:
                intersect = intersect_point_line(Vector((x,y)).to_3d(), a.to_3d(),b.to_3d()) 
                if intersect:
                    dist = (intersect[0].to_2d() - Vector((x,y))).length_squared
                    bound = intersect[1]
                    if (dist < 900) and (bound < 1) and (bound > 0):
                        self.hovered = ['EDGE',i]
                        return
                    
        self.hovered = [None, -1]
            
    def snap_poly_line(self):
        '''
        only needed if processing an outside mesh
        '''
        locs = []
        self.face_map = []
        self.normals = []
        self.face_changes = []
        mx = self.cut_ob.matrix_world
        imx = mx.inverted()
        for i, v in enumerate(self.pts):
            if bversion() < '002.077.000':
                loc, no, ind, d = self.bvh.find(imx * v)
            else:
                loc, no, ind, d = self.bvh.find_nearest(imx * v)
            
            self.face_map.append(ind)
            self.normals.append(no)
            locs.append(loc)
            if i > 0:
                if ind != self.face_map[i-1]:
                    self.face_changes.append(i-1)
            
            #do double check for the last point
            if i == len(self.pts) - 1:
                if ind != self.face_map[0] :
                    self.face_changes.append(i)      
        self.cut_pts = locs

    def click_seed_select(self, context, x, y):
        
        region = context.region
        rv3d = context.region_data
        coord = x, y
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * 1000)
        mx = self.cut_ob.matrix_world
        imx = mx.inverted()
        if bversion() < '002.077.000':
            loc, no, face_ind = self.cut_ob.ray_cast(imx * ray_origin, imx * ray_target)
        else:
            ok, loc, no, face_ind = self.cut_ob.ray_cast(imx * ray_origin, imx * ray_target - imx*ray_origin)
        if face_ind != -1:
            self.face_seed = face_ind
            print('face selected!!')
            return True
            
        else:
            self.face_seed = None
            print('face not selected')
            return False
                     
    def make_cut(self):
            
        mx = self.cut_ob.matrix_world
        imx = mx.inverted()
        print('cutting!')
        self.new_cos = []
        self.ed_map = []
        
        self.face_chain = set()
        self.snap_poly_line()
        self.bad_segments = []
        
        print('there are %i cut points' % len(self.cut_pts))
        print('there are %i face changes' % len(self.face_changes))
        for m, ind in enumerate(self.face_changes):
            print('\n')
            
            if ind == len(self.face_changes) - 1 and not self.cyclic:
                'not cyclic, we are done'
                break
            
            
            n_p1 = (m + 1) % len(self.face_changes)
            ind_p1 = self.face_changes[n_p1]
            
            print('walk on edge pair %i, %i' % (m, n_p1))
            print('original faces in mesh %i, %i' % (self.face_map[ind], self.face_map[ind_p1]))
            
            f0 = self.bme.faces[self.face_map[ind]]
            f1 = self.bme.faces[self.face_map[ind_p1]]
            
            no0 = self.normals[ind]
            no1 = self.normals[ind_p1]
    
            surf_no = no0.lerp(no1, 0.5)  #must be a better way.
            
            
            #normal method 1
            e_vec = self.cut_pts[ind_p1] - self.cut_pts[ind]
            
            
            #normal method 2
            #v0 = self.cut_pts[ind] - self.cut_pts[ind-1]
            #v0.normalize()
            #v1 = self.cut_pts[ind + 1] - self.cut_pts[ind]
            #v1.normalize()
            
            #ang = v0.angle(v1, 0)
            #if ang > 1 * math.pi/180:
            #    curve_no = v0.cross(v1)
            #    cut_no = e_vec.cross(curve_no)
                
            #else: #method 2 using surface normal
            cut_no = e_vec.cross(surf_no)
                
            cut_pt = .5*self.cut_pts[ind_p1] + 0.5*self.cut_pts[ind]
    
            #find the shared edge
            cross_ed = None
            for ed in f0.edges:
                if f1 in ed.link_faces:
                    cross_ed = ed
                    break
            
            #if no shared edge, need to cut across to the next face    
            if not cross_ed:
                
                if self.face_changes.index(ind) != 0:
                    p_face = self.bme.faces[self.face_map[ind-1]]
                else:
                    p_face = None
                
                print('LINE WALK METHOD')
                vs = []
                epp = .0000000001
                use_limit = True
                attempts = 0
                while epp < .0001 and not len(vs) and attempts <= 5:
                    attempts += 1
                    vs, eds, eds_crossed, faces_crossed, error = path_between_2_points(self.bme, 
                                                             self.bvh, 
                                                             mx, 
                                                             self.cut_pts[ind], self.cut_pts[ind_p1], 
                                                             max_tests = 10000, debug = True, 
                                                             prev_face = p_face,
                                                             use_limit = use_limit)
                    if len(vs) and error == 'LIMIT_SET':
                        vs = []
                        use_limit = False
                        print('Limit was too limiting, relaxing that consideration')
                        
                    elif len(vs) == 0 and error == 'EPSILON':
                        print('Epsilon was too small, relaxing epsilon')
                        epp *= 10
                    elif len(vs) == 0 and error:
                        print("too bad, couldn't adjust")
                        break
                
                if not len(vs):
                    print('\n')
                    print('CUTTING METHOD')
                    
                    vs = []
                    epp = .0000000001
                    use_limit = True
                    attempts = 0
                    while epp < .0001 and not len(vs) and attempts <= 10:
                        attempts += 1
                        vs, eds, eds_crossed, faces_crossed, error = cross_section_2seeds_ver1(self.bme, mx, 
                                                        cut_pt, cut_no, 
                                                        f0.index,self.cut_pts[ind],
                                                        f1.index, self.cut_pts[ind_p1],
                                                        max_tests = 10000, debug = True, prev_face = p_face,
                                                        epsilon = epp)
                        if len(vs) and error == 'LIMIT_SET':
                            vs = []
                            use_limit = False
                        elif len(vs) == 0 and error == 'EPSILON':
                            epp *= 10
                        elif len(vs) == 0 and error:
                            print('too bad, couldnt adjust')
                            break
                        
                if len(vs):
                    for v,ed in zip(vs,eds_crossed):
                        self.new_cos.append(v)
                        self.ed_map.append(ed)
                        
                    self.face_chain.update(faces_crossed)
                        
                    if ind == len(self.face_changes) - 1:
                        print('THis is the loop closing segment.  %i' % len(vs))
                else:
                    self.bad_segments.append(ind)
                    print('cut failure!!!')
                continue
            
            p0 = cross_ed.verts[0].co
            p1 = cross_ed.verts[1].co
            v = intersect_line_plane(p0,p1,cut_pt,cut_no)
            if v:
                self.new_cos.append(v)
                self.ed_map.append(cross_ed)

    def calc_ed_pcts(self):
        '''
        not used utnil bmesh.ops uses the percentage index
        '''
        if not len(self.ed_map) and len(self.new_cos): return
        
        self.ed_pcts = {}
        for v, ed in zip(self.new_cos, self.ed_map):
            
            v0 = ed.verts[0].co
            v1 = ed.verts[1].co
            
            ed_vec = v1 - v0
            L = ed_vec.length
            
            cut_vec = v - v0
            l = cut_vec.length
            
            pct = l/L
            self.ed_pcts[ed] = pct
            
    def find_select_inner_faces(self):
        if not self.face_seed: return
        if len(self.bad_segments): return
        f0 = self.bme.faces[self.face_seed]
        inner_faces = flood_selection_faces(self.bme, set(), f0, max_iters=1000)
        
        for f in self.bme.faces:
            f.select_set(False)
        for f in inner_faces:
            f.select_set(True)
                 
    def confirm_cut_to_mesh(self):
        new_verts = []
        new_bmverts = []
        new_edges = []
        
        self.calc_ed_pcts()
        ed_set = set(self.ed_map)
        if len(self.ed_map) != len(set(self.ed_map)):  #doubles in ed dictionary
            seen = set()
            new_eds = []
            new_cos = []
            removals = []

            for i, ed in enumerate(self.ed_map):
                if ed not in seen and not seen.add(ed):
                    new_eds += [ed]
                    new_cos += [self.new_cos[i]]
                else:
                    removals.append(i)
            
            print(removals)
            
            self.ed_map = new_eds
            self.new_cos = new_cos
            
            
        start = time.time()
        print('bisecting edges')
        geom =  bmesh.ops.bisect_edges(self.bme, edges = self.ed_map,cuts = 1,edge_percents = self.ed_pcts)
        new_bmverts = [ele for ele in geom['geom_split'] if isinstance(ele, bmesh.types.BMVert)]

        #can't be that easy can it?
        for v, co in zip(new_bmverts, self.new_cos):
            v.co = co
            
        finish = time.time()
        print('Took %f seconds' % (finish-start))
        start = finish    
        ed_geom = bmesh.ops.connect_verts(self.bme, verts = new_bmverts, faces_exclude = [], check_degenerate = False)
        new_edges = ed_geom['edges']
        
        finish = time.time()
        print('took %f seconds' % (finish-start))
        
        start = finish
        
        print('splitting new edges')
        self.bme.verts.ensure_lookup_table()
        self.bme.edges.ensure_lookup_table()
        bmesh.ops.split_edges(self.bme, edges = new_edges, verts = [], use_verts = False) 
        
        self.bme.verts.ensure_lookup_table()
        self.bme.edges.ensure_lookup_table()
        self.bme.faces.ensure_lookup_table()
        finish = time.time()
        print('took %f seconds' % (finish-start))
        self.split = True
        
    def split_geometry(self):
        if not (self.split and self.face_seed): return
        
        self.find_select_inner_faces()
        
        self.bme.to_mesh(self.cut_ob.data)
        bpy.ops.object.mode_set(mode ='EDIT')
        bpy.ops.mesh.separate(type = 'SELECTED')
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        #EXPENSIVE!!
        #self.bme = bmesh.new()
        #self.bme.from_mesh(self.cut_ob.data)
        #self.bme.verts.ensure_lookup_table()
        #self.bme.edges.ensure_lookup_table()
        #self.bme.faces.ensure_lookup_table()
        #self.bvh = BVHTree.FromBMesh(self.bme)
        #self.reset_vars()
          
    def replace_segment(self,start,end,new_locs):
        #http://stackoverflow.com/questions/497426/deleting-multiple-elements-from-a-list
        return
                
    def draw(self,context):
        if len(self.pts) == 0: return
        
        if self.cyclic and len(self.pts):
            common_drawing.draw_polyline_from_3dpoints(context, self.pts + [self.pts[0]], (.1,.2,1,.8), 2, 'GL_LINE_STRIP')
        
        else:
            common_drawing.draw_polyline_from_3dpoints(context, self.pts, (.1,.2,1,.8), 2, 'GL_LINE')
        
        if self.ui_type != 'DENSE_POLY':    
            bgl_utils.draw_3d_points(context,self.pts, 3)
            bgl_utils.draw_3d_points(context,[self.pts[0]], 8, color = (1,1,0,1))
            
        else:
            common_drawing.draw_3d_points(context,self.pts,(1,1,1,1),4) 
            bgl_utils.draw_3d_points(context,[self.pts[0]], 4, color = (1,1,0,1))
        
        
        if self.selected != -1 and len(self.pts) >= self.selected + 1:
            bgl_utils.draw_3d_points(context,[self.pts[self.selected]], 8, color = (0,1,1,1))
                
        if self.hovered[0] == 'POINT':
            bgl_utils.draw_3d_points(context,[self.pts[self.hovered[1]]], 8, color = (0,1,0,1))
     
        elif self.hovered[0] == 'EDGE':
            loc3d_reg2D = view3d_utils.location_3d_to_region_2d
            a = loc3d_reg2D(context.region, context.space_data.region_3d, self.pts[self.hovered[1]])
            next = (self.hovered[1] + 1) % len(self.pts)
            b = loc3d_reg2D(context.region, context.space_data.region_3d, self.pts[next])
            common_drawing.draw_polyline_from_points(context, [a,self.mouse, b], (0,.2,.2,.5), 2,"GL_LINE_STRIP")  

        if self.face_seed:
            #TODO direct bmesh face drawing util
            vs = self.bme.faces[self.face_seed].verts
            bgl_utils.draw_3d_points(context,[self.cut_ob.matrix_world * v.co for v in vs], 4, color = (1,1,.1,1))
            
            
        if len(self.new_cos):
            bgl_utils.draw_3d_points(context,[self.cut_ob.matrix_world * v for v in self.new_cos], 6, color = (.2,.5,.2,1))
        if len(self.bad_segments):
            for ind in self.bad_segments:
                m = self.face_changes.index(ind)
                m_p1 = (m + 1) % len(self.face_changes)
                ind_p1 = self.face_changes[m_p1]
                common_drawing.draw_polyline_from_3dpoints(context, [self.cut_pts[ind], self.cut_pts[ind_p1]], (1,.1,.1,1), 4, 'GL_LINE')
                                                                     
class CurveDataManager(object):
    '''
    a helper class for interactive editing of Blender bezier curve
    data object
    '''
    def __init__(self,context,snap_type ='SCENE', snap_object = None, shrink_mod = False, name = 'Outline', cyclic = 'OPTIONAL'):
        '''
        will create a new bezier object, with all auto
        handles. Links it to scene
        '''
        

        self.name = name
        
        if name in bpy.data.objects:
            self.crv_obj = bpy.data.objects.get(name)
            self.crv_obj.hide = False
            self.crv_data = self.crv_obj.data
            
            mx = self.crv_obj.matrix_world
            self.b_pts = [mx * bpt.co for bpt in self.crv_data.splines[0].bezier_points]
            if len(self.b_pts):
                self.started = True
            
            self.cyclic = cyclic
            #self.crv_data.splines[0].use_cyclic_u
            
            
                
        else:
            self.crv_data = bpy.data.curves.new(name,'CURVE')
            self.crv_data.splines.new('BEZIER')
            self.crv_data.splines[0].bezier_points[0].handle_left_type = 'AUTO'
            self.crv_data.splines[0].bezier_points[0].handle_right_type = 'AUTO'
            self.crv_data.dimensions = '3D'
            self.crv_obj = bpy.data.objects.new(name,self.crv_data)
            context.scene.objects.link(self.crv_obj)
            
            self.cyclic = cyclic
            self.started = False  #the initial curve data has 1 bezier pt, however the users hasn't clicked anything yet, use this to reconcile until self.b_pts = crv.spline.bezier_points
            self.b_pts = []  #vectors representing locations of be
        
        self.snap_type = snap_type  #'SCENE' 'OBJECT'
        self.snap_ob = snap_object
        
        if snap_object and shrink_mod:
            mod = self.crv_obj.modifiers.new('Wrap','SHRINKWRAP')
            mod.target = snap_object
            mod.use_keep_above_surface = True
            #mod.use_apply_on_spline = True
        
        
        self.selected = -1
        self.hovered = [None, -1]
        
        self.grab_undo_loc = None
        self.mouse = (None, None)
    
        self.point_size = 8
        self.point_color = (.9, .1, .1)
        self.active_color = (.8, .8, .2)
        
    def grab_initiate(self):
        if self.selected != -1:
            self.grab_undo_loc = self.b_pts[self.selected]
            return True
        
        else:
            return False
    
    def grab_mouse_move(self,context,x,y):
        region = context.region
        rv3d = context.region_data
        coord = x, y
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * 1000)
        
        crv_mx = self.crv_obj.matrix_world
        i_crv_mx = crv_mx.inverted()  
        
        
        hit = False
        if self.snap_type == 'SCENE':
            
            mx = Matrix.Identity(4) #scene ray cast returns world coords
            if bversion() < '002.077.000':
                res, obj, omx, loc, no = context.scene.ray_cast(ray_origin, ray_target)
            else:
                res, loc, no, ind, obj, omx = context.scene.ray_cast(ray_origin, view_vector)
            
            if res:
                hit = True
        
            else:
                #cast the ray into a plane a
                #perpendicular to the view dir, at the last bez point of the curve
                hit = True
                view_direction = rv3d.view_rotation * Vector((0,0,-1))
                plane_pt = self.grab_undo_loc
                loc = intersect_line_plane(ray_origin, ray_target,plane_pt, view_direction)
                
        elif self.snap_type == 'OBJECT':
            mx = self.snap_ob.matrix_world
            imx = mx.inverted()
            
            if bversion() < '002.077.000':
                loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target)
                if face_ind != -1:
                    hit = True
            else:
                ok, loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target - imx*ray_origin)
                if ok:
                    hit = True
   
        if not hit:
            self.grab_cancel()
            
        else:
            local_loc = i_crv_mx * mx * loc
            self.crv_data.splines[0].bezier_points[self.selected].co = local_loc
            self.b_pts[self.selected] = mx * loc
        
    def grab_cancel(self):
        crv_mx = self.crv_obj.matrix_world
        i_crv_mx = crv_mx.inverted()  
        
        old_co =  i_crv_mx * self.grab_undo_loc
        self.crv_data.splines[0].bezier_points[self.selected].co = old_co
        self.b_pts[self.selected] = old_co
        return
    
    def grab_confirm(self):
        self.grab_undo_loc = None
        return
               
    def click_add_point(self,context,x,y):
        '''
        x,y = event.mouse_region_x, event.mouse_region_y
        
        this will add a point into the bezier curve or
        close the curve into a cyclic curve
        '''
        region = context.region
        rv3d = context.region_data
        coord = x, y
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * 1000)
        
        crv_mx = self.crv_obj.matrix_world
        i_crv_mx = crv_mx.inverted()  
        
        
        hit = False
        if self.snap_type == 'SCENE':
            mx = Matrix.Identity(4)  #loc is given in world loc...no need to multiply by obj matrix
            if bversion() < '002.077.000':
                res, obj, omx, loc, no = context.scene.ray_cast(ray_origin, ray_target)  #changed in 2.77
            else:
                res, loc, no, ind, obj, omx = context.scene.ray_cast(ray_origin, view_vector)
                
            hit = res
            if not hit:
                #cast the ray into a plane a
                #perpendicular to the view dir, at the last bez point of the curve
            
                view_direction = rv3d.view_rotation * Vector((0,0,-1))
            
                if len(self.b_pts):
                    if self.hovered[0] == 'EDGE':
                        plane_pt = self.b_pts[self.hovered[1]]
                    else:
                        plane_pt = self.b_pts[-1]
                else:
                    plane_pt = context.scene.cursor_location
                loc = intersect_line_plane(ray_origin, ray_target,plane_pt, view_direction)
                hit = True
        
        elif self.snap_type == 'OBJECT':
            mx = self.snap_ob.matrix_world
            imx = mx.inverted()
            
            if bversion() < '002.077.000':
                loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target)
                if face_ind != -1:
                    hit = True
            else:
                ok, loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target - imx*ray_origin)
                if ok:
                    hit = True
            
            if face_ind != -1:
                hit = True
        
        if not hit: 
            self.selected = -1
            return
        
        if self.hovered[0] == None:  #adding in a new point
            if self.started:
                self.crv_data.splines[0].bezier_points.add(count = 1)
                bp = self.crv_data.splines[0].bezier_points[-1]
                bp.handle_right_type = 'AUTO'
                bp.handle_left_type = 'AUTO'
                bp.co =i_crv_mx* mx * loc
                self.b_pts.append(mx * loc)
                
            else:
                print('adding a new point!')
                self.started = True
                delta = i_crv_mx *mx * loc - self.crv_data.splines[0].bezier_points[0].co
                bp = self.crv_data.splines[0].bezier_points[0]
                bp.co += delta
                bp.handle_left += delta
                bp.handle_right += delta  
                self.b_pts.append(mx * loc) 
          
        if self.hovered[0] == 'POINT':
            self.selected = self.hovered[1]
            if self.hovered[1] == 0:  #clicked on first bpt, close loop
                
                print('The first point was clicked')
                print(self.cyclic)
                if self.cyclic in {'MANDATORY','OPTIONAL'}:
                    self.crv_data.splines[0].use_cyclic_u = self.crv_data.splines[0].use_cyclic_u == False
            return

            
        elif self.hovered[0] == 'EDGE':  #cut in a new point
            self.b_pts.insert(self.hovered[1]+1, mx * loc)
            self.update_blender_curve_data()   
            return
    
    def click_delete_point(self, mode = 'mouse'):
        if mode == 'mouse':
            if not self.hovered[0] == 'POINT': return
            if self.started == False: return
            
            if len(self.b_pts) == 0:
                print('We have a big problem!?')
                return
            elif len(self.b_pts) == 1:
                print('removing the only point!')
                self.started = False
                
                self.b_pts.pop()  #len(self.b_pts) now = 0 and len(crv_data.splines[0].bezier_points) = 1
                
                
                bp = self.crv_data.splines[0].bezier_points[0]
                bp.co = Vector((0,0,0))
                bp.handle_left = Vector((1,0,0))
                bp.handle_right = Vector((-1,0,0))
                self.hovered = self.hovered = [None, -1]
                self.selected = -1
                return
            
            else:
                self.b_pts.pop(self.hovered[1])
                self.update_blender_curve_data()
                self.hovered = self.hovered = [None, -1]
                self.selected = -1
        
        else:
            if self.selected == -1: return
            if self.started == False: return
            
            if len(self.b_pts) == 0:
                print('We have a big problem!?')
                return
            
            elif len(self.b_pts) == 1:
                self.started = False
                
                self.b_pts.pop()  #len(self.b_pts) now = 0 and len(crv_data.splines[0].bezier_points) = 1
                
                
                bp = self.crv_data.splines[0].bezier_points[0]
                bp.co = Vector((0,0,0))
                bp.handle_left = Vector((1,0,0))
                bp.handle_right = Vector((-1,0,0))
                
                return
            
            else:
                self.b_pts.pop(self.selected)
                self.selected = -1
                self.update_blender_curve_data()
                          
    def update_blender_curve_data(self):
        #this may crash blender
        crv_data = bpy.data.curves.new(self.name,'CURVE')
        crv_data.splines.new('BEZIER')
        crv_data.dimensions = '3D'
        #set any matrix stuff here
        crv_mx = self.crv_obj.matrix_world
        icrv_mx = crv_mx.inverted()
        
        bp = crv_data.splines[0].bezier_points[0]
        delta = icrv_mx * self.b_pts[0] - bp.co
        bp.co += delta
        bp.handle_left += delta
        bp.handle_right += delta
        bp.handle_right_type = 'AUTO'
        bp.handle_left_type = 'AUTO'
        
        for i in range(1,len(self.b_pts)):
            crv_data.splines[0].bezier_points.add(count = 1)
            bp = crv_data.splines[0].bezier_points[i]
            bp.co = icrv_mx * self.b_pts[i]
            bp.handle_right_type = 'AUTO'
            bp.handle_left_type = 'AUTO'
        
        crv_data.splines[0].use_cyclic_u = self.crv_data.splines[0].use_cyclic_u
        self.crv_obj.data = crv_data
        self.crv_data.user_clear()
        bpy.data.curves.remove(self.crv_data)
        self.crv_data = crv_data
        
    def hover(self,context,x,y):
        '''
        hovering happens in mixed 3d and screen space.  It's a mess!
        '''
        
        if len(self.b_pts) == 0:
            return
        
        region = context.region
        rv3d = context.region_data
        self.mouse = Vector((x, y))
        coord = x, y
        loc3d_reg2D = view3d_utils.location_3d_to_region_2d
        
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * 1000)
        
        if self.snap_type == 'OBJECT':
            mx = self.snap_ob.matrix_world
            imx = mx.inverted()
        
            if bversion() < '002.077.000':
                loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target)
                if face_ind == -1: 
                    #do some shit
                    pass
            else:
                res, loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target - imx * ray_origin)
                if not res:
                    #do some shit
                    pass
        elif self.snap_type == 'SCENE':
            
            mx = Matrix.Identity(4) #scene ray cast returns world coords
            if bversion() < '002.077.000':
                res, obj, omx, loc, no = context.scene.ray_cast(ray_origin, ray_target)
            else:
                res, loc, no, ind, obj, omx = context.scene.ray_cast(ray_origin, view_vector)
                
                    
        def dist(v):
            diff = v - Vector((x,y))
            return diff.length
        
        def dist3d(v3):
            if v3 == None:
                return 100000000
            delt = v3 - mx * loc
            return delt.length
        
        closest_3d_point = min(self.b_pts, key = dist3d)
        screen_dist = dist(loc3d_reg2D(context.region, context.space_data.region_3d, closest_3d_point))
        
        if screen_dist  < 20:
            self.hovered = ['POINT',self.b_pts.index(closest_3d_point)]
            return
        
        if len(self.b_pts) < 2: 
            self.hovered = [None, -1]
            return
        
        line_inters3d = []
            
        for i in range(0,len(self.b_pts)):
            
            nexti = (i + 1) % len(self.b_pts)
            if next == 0 and not self.cyclic:
                self.hovered = [None, -1]
                return
               
            
            intersect3d = intersect_point_line(mx * loc, self.b_pts[i], self.b_pts[nexti])
            
            if intersect3d != None:
                dist3d = (intersect3d[0] - loc).length
                bound3d = intersect3d[1]
                if  (bound3d < 1) and (bound3d > 0):
                    line_inters3d += [dist3d]
                    #print('intersect line3d success')
                else:
                    line_inters3d += [1000000]
            else:
                line_inters3d += [1000000]
                
                
            i = line_inters3d.index(min(line_inters3d))
            nexti = (i + 1) % len(self.b_pts)  
       
            a  = loc3d_reg2D(context.region, context.space_data.region_3d,self.b_pts[i])
            b = loc3d_reg2D(context.region, context.space_data.region_3d,self.b_pts[nexti])
            
            if a and b:
                intersect = intersect_point_line(Vector((x,y)).to_3d(), a.to_3d(),b.to_3d())      
                dist = (intersect[0].to_2d() - Vector((x,y))).length_squared
                bound = intersect[1]
                if (dist < 400) and (bound < 1) and (bound > 0):
                    self.hovered = ['EDGE', i]        
                    return
                 
            self.hovered = [None, -1]
        
    def draw(self,context, three_d = True):
        if len(self.b_pts) == 0: return
        if three_d:
            bgl_utils.draw_3d_points(context,self.b_pts, self.point_size, (self.point_color[0],self.point_color[1],self.point_color[2],1))
            
        #bgl_utils.draw_3d_points(context,[self.b_pts[0]], self.point_size, color = (self.point_color[0],self.point_color[1],self.point_color[2],1))
        
        if self.selected != -1:
            if self.selected == 0:
                col = (.2, .2, .8, 1)
            else:
                col = (self.active_color[0],self.active_color[1],self.active_color[2],1)
            bgl_utils.draw_3d_points(context,[self.b_pts[self.selected]], self.point_size, color = col)
                
        if self.hovered[0] == 'POINT':
            
            if self.hovered[1] > len(self.b_pts) - 1:
                print('hovered is out of date')
                
            else:
                if self.hovered[1] == 0:
                    col = (.2, .2, .8, 1)
                else:
                    col = (self.active_color[0],self.active_color[1],self.active_color[2],1)
                
                bgl_utils.draw_3d_points(context,[self.b_pts[self.hovered[1]]], self.point_size, color = col)
     
        elif self.hovered[0] == 'EDGE':
            loc3d_reg2D = view3d_utils.location_3d_to_region_2d
            a = loc3d_reg2D(context.region, context.space_data.region_3d, self.b_pts[self.hovered[1]])
            next = (self.hovered[1] + 1) % len(self.b_pts)
            b = loc3d_reg2D(context.region, context.space_data.region_3d, self.b_pts[next])
            common_drawing.draw_polyline_from_points(context, [a,self.mouse, b], (0,.2,.2,.5), 2,"GL_LINE_STRIP")
            
    def draw3d(self,context):
        #ADAPTED FROM POLYSTRIPS John Denning @CGCookie and Taylor University
        if len(self.b_pts) == 0: return
        
        region,r3d = context.region,context.space_data.region_3d
        view_dir = r3d.view_rotation * Vector((0,0,-1))
        view_loc = r3d.view_location - view_dir * r3d.view_distance
        if r3d.view_perspective == 'ORTHO': view_loc -= view_dir * 1000.0
        
        bgl.glEnable(bgl.GL_POINT_SMOOTH)
        bgl.glDepthRange(0.0, 1.0)
        bgl.glEnable(bgl.GL_DEPTH_TEST)
        
        
        
        def set_depthrange(near=0.0, far=1.0, points=None):
            if points and len(points) and view_loc:
                d2 = min((view_loc-p).length_squared for p in points)
                d = math.sqrt(d2)
                d2 /= 10.0
                near = near / d2
                far = 1.0 - ((1.0 - far) / d2)
            if r3d.view_perspective == 'ORTHO':
                far *= 0.9999
            near = max(0.0, min(1.0, near))
            far = max(near, min(1.0, far))
            bgl.glDepthRange(near, far)
            #bgl.glDepthRange(0.0, 0.5)
            
        def draw3d_points(context, points, color, size):
            #if type(points) is types.GeneratorType:
            #    points = list(points)
            if len(points) == 0: return
            bgl.glColor4f(*color)
            bgl.glPointSize(size)
            set_depthrange(0.0, 0.997, points)
            bgl.glBegin(bgl.GL_POINTS)
            for coord in points: bgl.glVertex3f(*coord)
            bgl.glEnd()
            bgl.glPointSize(1.0)
            

        bgl.glLineWidth(1)
        bgl.glDepthRange(0.0, 1.0)
        
        draw3d_points(context, [self.b_pts[0]], (.2,.2,.8,1), self.point_size)
        if len(self.b_pts) > 1:
            draw3d_points(context, self.b_pts[1:], (self.point_color[0],self.point_color[1],self.point_color[2],1), self.point_size)
        
        bgl.glLineWidth(1)
        bgl.glDepthRange(0.0, 1.0)
        


class LineDrawer(object):
    '''
    a helper class for drawing 2D lines in the view and extracting 3D infomration from it
    '''
    def __init__(self,context,snap_type ='SCENE', snap_object = None):
        '''
        will create a new bezier object, with all auto
        handles. Links it to scene
        '''
        
        self.screen_pts = []  #list of 2, 2D vectors
        
        self.snap_type = snap_type  #'SCENE' 'OBJECT'
        self.snap_ob = snap_object
        
        self.over_object = False  #determines if mouse is on the object or not
        
        self.selected = -1
        self.hovered = [None, -1]
        
        self.box_coords = []
        
        self.grab_undo_loc = None
        self.mouse = (None, None)
    
        self.point_size = 8
        self.point_color = (.9, .1, .1)
        self.active_color = (.8, .8, .2)
        
        live_draw = True
        
    def grab_initiate(self):
        if self.selected != -1:
            self.grab_undo_loc = self.screen_pts[self.selected]
            return True
        
        else:
            return False
    
    def grab_mouse_move(self,context,x,y):
        region = context.region
        rv3d = context.region_data
        coord = x, y
        self.screen_pts[self.selected] = Vector((x,y))
        
    def grab_cancel(self):
        old_co = self.grab_undo_loc
        self.screen_pts[self.selected] = old_co
        return
    
    def grab_confirm(self):
        self.grab_undo_loc = None
        return
    
    def ray_cast_ob(self, context, x, y):
        region = context.region
        rv3d = context.region_data
        coord = x, y
        mx = self.snap_ob.matrix_world
        imx = mx.inverted()
        
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * 1000)
        
        if bversion() < '002.077.000':
            loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target)
            if face_ind == -1:
                return None
            else:
                return mx * loc

        else:
            res, loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target - imx * ray_origin)
            
            if not res:
                return None
            else:
                return mx * loc
            
    def click_add_point(self,context,x,y):
        '''
        x,y = event.mouse_region_x, event.mouse_region_y
        
        this will add a point into the bezier curve or
        close the curve into a cyclic curve
        '''
        region = context.region
        rv3d = context.region_data
        coord = x, y
        
        if len(self.screen_pts) >= 2:
            if self.hovered[0] == 'POINT':
                self.selected = self.hovered[1]
            
                return 'SELECT'
            else:
                return None
        
        else:
            self.screen_pts.append(Vector((x,y)))
            return 'ADD POINT'
        
    def click_delete_point(self, mode = 'mouse'):
        if mode == 'mouse':
            if not self.hovered[0] == 'POINT': return
            if self.started == False: return
            
            if len(self.b_pts) == 0:
                print('We have a big problem!?')
                return
            elif len(self.b_pts) == 1:
                print('removing the only point!')
                self.started = False
                
                self.b_pts.pop()  #len(self.b_pts) now = 0 and len(crv_data.splines[0].bezier_points) = 1
                
                
                bp = self.crv_data.splines[0].bezier_points[0]
                bp.co = Vector((0,0,0))
                bp.handle_left = Vector((1,0,0))
                bp.handle_right = Vector((-1,0,0))
                self.hovered = self.hovered = [None, -1]
                self.selected = -1
                return
            
            else:
                self.b_pts.pop(self.hovered[1])
                self.update_blender_curve_data()
                self.hovered = self.hovered = [None, -1]
                self.selected = -1
        
        else:
            if self.selected == -1: return
            if self.started == False: return
            
            if len(self.b_pts) == 0:
                print('We have a big problem!?')
                return
            
            elif len(self.b_pts) == 1:
                self.started = False
                
                self.b_pts.pop()  #len(self.b_pts) now = 0 and len(crv_data.splines[0].bezier_points) = 1
                
                
                bp = self.crv_data.splines[0].bezier_points[0]
                bp.co = Vector((0,0,0))
                bp.handle_left = Vector((1,0,0))
                bp.handle_right = Vector((-1,0,0))
                
                return
            
            else:
                self.b_pts.pop(self.selected)
                self.selected = -1
                self.update_blender_curve_data()
                          
    
    def calc_matrix(self, context, depth = 'SURFACE'):
        '''
        -if depth is Surface, it will ray_cast the object and place it there
        -if depth is 'BOUNDS' it will place the matrix with translation at the
        midpoint of the user drawn line at the depth of the bbox center
        '''
        region = context.region
        rv3d = context.region_data
        
        if len(self.screen_pts) != 2: return None
        
        mouse = self.mouse
        mid = .5 * (self.screen_pts[0] + self.screen_pts[1])
        #Z = view3d_utils.region_2d_to_vector_3d(region, rv3d, mid)
        
        mouse_v = mouse - mid
        
        
        Y = (rv3d.view_rotation * Vector((0,0,1))).normalized()
        
        x_view_world = rv3d.view_rotation * Vector((1,0,0))
        y_view_world = rv3d.view_rotation * Vector((0,1,0))
        
        user_x = self.screen_pts[0] - self.screen_pts[1]
        user_x.normalize()
        
        #the world vector of the line on the screen
        user_world_x = user_x[0] * x_view_world + user_x[1] * y_view_world
        mouse_world = mouse_v[0] * x_view_world + mouse_v[1] * y_view_world
        mouse_world.normalize()
        
        X = user_world_x
        
        Z = X.cross(Y)
        Z.normalize
        
        
        if Z.dot(mouse_world) < 0:
            Z = -1 * Z
            X = -1 * X
            
        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
        R = R.to_4x4()
        
        if depth == 'SURFACE':
            view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, mid)
            ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mid)
            ray_target = ray_origin + (view_vector * 1000)
        
            mx = self.snap_ob.matrix_world
            imx = mx.inverted()
        
        
            res, loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target - imx * ray_origin)
            if not res:
                
                local_bbox_center = 0.125 * sum((Vector(b) for b in self.snap_ob.bound_box), Vector())
                global_bbox_center = self.snap_ob.matrix_world * local_bbox_center
                v_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, mid, global_bbox_center)
                T = Matrix.Translation(v_3d)
                
            else:
                T = Matrix.Translation(mx * loc)      
        else:
            local_bbox_center = 0.125 * sum((Vector(b) for b in self.snap_ob.bound_box), Vector())
            global_bbox_center = self.snap_ob.matrix_world * local_bbox_center
            v_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, mid, global_bbox_center)
            T = Matrix.Translation(v_3d)
                   
        
        return T * R

    def calc_line_limits(self, context):
        region = context.region
        rv3d = context.region_data
        
        if len(self.screen_pts) != 2: return None
        
        mouse = self.mouse
        mid_screen = .5 * (self.screen_pts[0] + self.screen_pts[1])
        mouse_v = mouse - mid_screen

        
        #x direction of the user drawn line
        user_x_screen = self.screen_pts[0] - self.screen_pts[1]
        user_x_screen.normalize()
        
        #y direction of the user drawn line
        user_y_screen = mouse_v - mouse_v.dot(user_x_screen) * user_x_screen
        
        
        #map the screen x and y to world axes
        x_view_world = rv3d.view_rotation * Vector((1,0,0))
        y_view_world = rv3d.view_rotation * Vector((0,1,0))
        
        #the world vector of the line on the screen
        user_world_x = user_x_screen[0] * x_view_world + user_x_screen[1] * y_view_world
        user_world_x.normalize()
        
       
        
        mouse_world = mouse_v[0] * x_view_world + mouse_v[1] * y_view_world
        #mouse_world.normalize()
        
        
        
        #user_world_y = mouse_world - mouse_world.dot(user_world_x) * user_world_x
        user_world_y = user_y_screen[0] * x_view_world + user_y_screen[1] * y_view_world
        
        
        
        #orthographic view is enforced, so depth doesn't matter
        world_mid = view3d_utils.region_2d_to_location_3d(region, rv3d, mid_screen, Vector((0,0,0)))
        world_0 = view3d_utils.region_2d_to_location_3d(region, rv3d, self.screen_pts[0], Vector((0,0,0)))
        world_1 = view3d_utils.region_2d_to_location_3d(region, rv3d, self.screen_pts[1], Vector((0,0,0)))
        
        world_orthogonal_mouse = view3d_utils.region_2d_to_location_3d(region, rv3d, mid_screen + user_y_screen, Vector((0,0,0)))
        
        world_mouse_line = world_orthogonal_mouse - world_mid
        
        world_line = world_1 - world_0
        world_line.length
        
        return world_0, world_1, world_mouse_line
    
       
    def hover(self,context,x,y):
        '''
        hovering happens in mixed 3d and screen space.  It's a mess!
        '''
        
        self.mouse = (x,y)
        if len(self.screen_pts) == 0:
            return
        
        region = context.region
        rv3d = context.region_data
        self.mouse = Vector((x, y))
        coord = x, y

        world_loc = self.ray_cast_ob(context, x, y)

        if world_loc == None:
            self.over_object = False
        else:
            self.over_object = True
                
                    
        def dist(v):
            diff = v - Vector((x,y))
            return diff.length

        
        closest_2d_point = min(self.screen_pts, key = dist)
        screen_dist = dist(closest_2d_point)
        
        
        if screen_dist  < 20:
            self.hovered = ['POINT',self.screen_pts.index(closest_2d_point)]
            return
        
        else:
            self.hovered = [None, -1]
            return
        
        
    def calc_box(self):
        
        if len(self.screen_pts) != 2: 
            self.box_coords = []
            return None
        
        mouse = self.mouse
        mid_screen = .5 * (self.screen_pts[0] + self.screen_pts[1])
        mouse_v = mouse - mid_screen

        
        #x direction of the user drawn line
        user_x_screen = self.screen_pts[0] - self.screen_pts[1]
        user_x_screen.normalize()
        
        #y direction of the user drawn line
        user_y_screen = mouse_v - mouse_v.dot(user_x_screen) * user_x_screen
        
        p0= self.screen_pts[0]
        p1 = self.screen_pts[1]
        p2 = self.screen_pts[1] + user_y_screen
        p3 = self.screen_pts[0] + user_y_screen
        
        self.box_coords = [p0, p1, p2, p3]
        
        
           
    def draw(self,context):
        if len(self.screen_pts) == 0: return
        
        col = (self.point_color[0], self.point_color[1], self.point_color[2], 1)
        common_drawing.draw_points(context, self.screen_pts, col, self.point_size)
        
        if self.selected != -1:
            if self.selected == 0:
                col = (.2, .2, .8, 1)
            else:
                col = (self.active_color[0],self.active_color[1],self.active_color[2],1)
            common_drawing.draw_points(context,[self.screen_pts[self.selected]], col, self.point_size)
                
        if self.hovered[0] == 'POINT':
            if self.hovered[1] == 0:
                col = (.2, .2, .8, 1)
            else:
                col = (self.active_color[0],self.active_color[1],self.active_color[2],1)
                
            common_drawing.draw_points(context,[self.screen_pts[self.hovered[1]]], col, self.point_size, )
     
        if len(self.screen_pts) == 2:
            common_drawing.draw_polyline_from_points(context, self.screen_pts, (0,0,1,1), 4, "GL_LINE_STRIP")
        
        elif len(self.screen_pts) == 1:
            common_drawing.draw_polyline_from_points(context, [self.screen_pts[0], Vector(self.mouse)], (0,0,1,1), 4, "GL_LINE_STRIP")    

        if len(self.box_coords) == 4:
            common_drawing.draw_outline_or_region("GL_POLYGON", self.box_coords, (.1, .1, .7, .5))
   
   
class TextLineDrawer(object):
    '''
    a helper class for drawing 2D lines in the view and extracting 3D infomration from it
    '''
    def __init__(self,context,snap_type ='SCENE', snap_object = None, msg = '', f_id = 0):
        '''
        will create a new bezier object, with all auto
        handles. Links it to scene
        '''
        
        #text values
        self.message = msg
        self.text_dimensions = [1,1]
        self.text_size = 20
        self.dpi = 72
        
        self.text_angle = 0
        self.text_loc = Vector((0,0))
        
        self.screen_pts = []  #list of 2, 2D vectors
        
        self.snap_type = snap_type  #'SCENE' 'OBJECT'
        self.snap_ob = snap_object
        
        self.font_id = f_id
        
        self.selected = -1
        self.hovered = [None, -1]
        
        self.grab_undo_loc = None
        self.mouse = (None, None)
    
        self.point_size = 8
        self.point_color = (.9, .1, .1)
        self.active_color = (.8, .8, .2)
        
        live_draw = True
        self.projected_points = []
        self.grid_points = []
        
    def grab_initiate(self):
        if self.selected != -1:
            self.grab_undo_loc = self.screen_pts[self.selected]
            return True
        
        else:
            return False
    
    def grab_mouse_move(self,context,x,y):
        region = context.region
        rv3d = context.region_data
        coord = x, y
        self.screen_pts[self.selected] = Vector((x,y))
        
    def grab_cancel(self):
        old_co = self.grab_undo_loc
        self.screen_pts[self.selected] = old_co
        return
    
    def grab_confirm(self):
        self.grab_undo_loc = None
        return
               
    def click_add_point(self,context,x,y):
        '''
        x,y = event.mouse_region_x, event.mouse_region_y
        
        this will add a point into the bezier curve or
        close the curve into a cyclic curve
        '''
        region = context.region
        rv3d = context.region_data
        coord = x, y
        
        if len(self.screen_pts) >= 2:
            if self.hovered[0] == 'POINT':
                self.selected = self.hovered[1]
            
                return 'SELECT'
            else:
                return None
        
        else:
            self.screen_pts.append(Vector((x,y)))
            return 'ADD POINT'
        
    def click_delete_point(self, mode = 'mouse'):
        if mode == 'mouse':
            if not self.hovered[0] == 'POINT': return
            if self.started == False: return
            
            if len(self.b_pts) == 0:
                print('We have a big problem!?')
                return
            elif len(self.b_pts) == 1:
                print('removing the only point!')
                self.started = False
                
                self.b_pts.pop()  #len(self.b_pts) now = 0 and len(crv_data.splines[0].bezier_points) = 1
                
                
                bp = self.crv_data.splines[0].bezier_points[0]
                bp.co = Vector((0,0,0))
                bp.handle_left = Vector((1,0,0))
                bp.handle_right = Vector((-1,0,0))
                self.hovered = self.hovered = [None, -1]
                self.selected = -1
                return
            
            else:
                self.b_pts.pop(self.hovered[1])
                self.update_blender_curve_data()
                self.hovered = self.hovered = [None, -1]
                self.selected = -1
        
        else:
            if self.selected == -1: return
            if self.started == False: return
            
            if len(self.b_pts) == 0:
                print('We have a big problem!?')
                return
            
            elif len(self.b_pts) == 1:
                self.started = False
                
                self.b_pts.pop()  #len(self.b_pts) now = 0 and len(crv_data.splines[0].bezier_points) = 1
                
                
                bp = self.crv_data.splines[0].bezier_points[0]
                bp.co = Vector((0,0,0))
                bp.handle_left = Vector((1,0,0))
                bp.handle_right = Vector((-1,0,0))
                
                return
            
            else:
                self.b_pts.pop(self.selected)
                self.selected = -1
                self.update_blender_curve_data()
                          
    
    def calc_text_values(self):
        
        if len(self.screen_pts) == 0: return
        
        
        if len(self.screen_pts) == 1:
            mid = .5 * self.screen_pts[0] + .5 * self.mouse
            p1 = Vector(self.mouse)
            p0 = Vector(self.screen_pts[0])
            
        elif len(self.screen_pts) == 2:
            mid = .5 * self.screen_pts[0] + .5 * self.screen_pts[1]
            p1 = Vector(self.screen_pts[1])
            p0 =  Vector(self.screen_pts[0])
            
            
        pL = min((p0, p1), key = lambda x: x[0]) #find the left point
        pR = max((p0, p1), key = lambda x: x[0]) #find the right point
        
        R = pR - pL
        
        dy = pR[1] - pL[1]
        dx = pR[0] - pL[0]
        
        if abs(dx) < 5:
            self.text_angle = 0
            print('small absolute value')
            print(dx)
            print((pR, pL))
        else:
            self.text_angle = math.atan2(dy,dx)
            
        line_size = R.length
        
        blf.size(0, self.text_size, self.dpi)
        text_dim = blf.dimensions(0, self.message)
        
        if text_dim[0] < .00001:
            factor = 1
        else:
            factor = line_size/text_dim[0]
        
        #bracket the text size
        self.text_dimensions = text_dim
        self.text_size = min(150, math.floor(factor * self.text_size))
        self.text_size = max(20, self.text_size)
        self.text_loc = mid - R.length/2 * R.normalized()
        
        blf.size(0, 12, 72) #TODO read in settings!
        
    
    def ray_cast_pt(self,context, pt):
        region = context.region
        rv3d = context.region_data
        
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, pt)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, pt)
        ray_target = ray_origin + (view_vector * 1000)
        
        mx = self.snap_ob.matrix_world
        imx = mx.inverted()
        

        res, loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target - imx * ray_origin)
            
            
        return loc, no
    
    def ray_cast_pt3d(self,context, pt3d):
        region = context.region
        rv3d = context.region_data
        
        pt = view3d_utils.location_3d_to_region_2d(region, rv3d, pt3d, default=None)
        if pt == None:
            return Vector((0,0,0)), Vector((0,0,1))
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, pt)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, pt)
        ray_target = ray_origin + (view_vector * 1000)
        
        mx = self.snap_ob.matrix_world
        imx = mx.inverted()
        
 
        res, loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target - imx * ray_origin)
            
            
        return loc, no   
    def project_line(self, context, res = 10):
        
        self.projected_points = []
        if len(self.screen_pts) == 1:
            mid = .5 * self.screen_pts[0] + .5 * self.mouse
            p1 = Vector(self.mouse)
            p0 = Vector(self.screen_pts[0])
            
        elif len(self.screen_pts) == 2:
            mid = .5 * self.screen_pts[0] + .5 * self.screen_pts[1]
            p1 = Vector(self.screen_pts[1])
            p0 =  Vector(self.screen_pts[0])
            
        else:
            return []
        
            
        pL = min((p0, p1), key = lambda x: x[0]) #find the left point
        pR = max((p0, p1), key = lambda x: x[0]) #find the right point
        
        pairs = []
        R = pR - pL
        S = R.length
        
        R.normalize()
        delta = S/res
        
        for i in range(0, res):
            
            pt = pL + i * delta * R
            
            loc, no = self.ray_cast_pt(context, pt)
            
            if loc != None:
                pairs += [(loc, no)]
                self.projected_points += [self.snap_ob.matrix_world * loc]
        
        
        return pairs
        
        
    def bisect_grid(self, context, res = 5):
        '''
        will create a convex grid by bisecting
        and projecting from the view
        '''
        
        if len(self.screen_pts) != 2:
            return
        
        p1 = Vector(self.screen_pts[1])
        p0 =  Vector(self.screen_pts[0])
                 
        pL = min((p0, p1), key = lambda x: x[0]) #find the left point
        pR = max((p0, p1), key = lambda x: x[0]) #find the right point
        
        blf.size(0, self.text_size, self.dpi)
        text_size = blf.dimensions(0, self.message)
        Y = text_size[1]

        def bisect_vector_list(l):
            midpoints = []
            for i in range(0,len(l) - 1):
                midpoints.append((l[i] + l[i+1])/2)
            
            new_points = []    
            for i in range(len(midpoints)):
                new_points += [l[i] , midpoints[i]]
            new_points += [l[-1]]
                
            return new_points     

            
        bottom_row = [pL, pR]  
        middle_row = [pL + Y/2 * Vector((0,1)), pR + Y/2 * Vector((0,1))]
        top_row = [pL + Y * Vector((0,1)), pR + Y * Vector((0,1))]
        
        #TODO check for missed rays
        
        for i in range(0, res):
            bottom_row = bisect_vector_list(bottom_row)
            middle_row = bisect_vector_list(middle_row)
            top_row = bisect_vector_list(top_row)
            
            
        self.grid_points = bottom_row + middle_row + top_row  
        
    
    def sculpt_flatten_region(self, context):
        if len(self.projected_points) == 0:
            return
        
        mx = self.snap_ob.matrix_world
        imx = mx.inverted()
        
        bpy.ops.object.mode_set(mode = 'SCULPT')
        
        if not self.snap_ob.use_dynamic_topology_sculpting:
            bpy.ops.sculpt.dynamic_topology_toggle()
            
        scene = context.scene
        paint_settings = scene.tool_settings.unified_paint_settings
        paint_settings.use_locked_size = True
        paint_settings.unprojected_radius = 2
        brush = bpy.data.brushes['Fill/Deepen']
        scene.tool_settings.sculpt.brush = brush
        scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
        
        
        #if bversion() < '002.079.000':
            #scene.tool_settings.sculpt.constant_detail = 50
        #else:
        #enforce 2.79
        scene.tool_settings.sculpt.constant_detail_resolution = 2
        
        scene.tool_settings.sculpt.use_symmetry_x = False
        scene.tool_settings.sculpt.use_symmetry_y = False
        scene.tool_settings.sculpt.use_symmetry_z = False
        brush.strength = .8
        
        brush.use_frontface = True
        brush.stroke_method = 'DOTS'
        
        screen = bpy.context.window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for reg in area.regions:
                    if reg.type == 'WINDOW':
                        break
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        break    
                break
        
        override = bpy.context.copy()
        override['area'] = area
        override['region'] = reg
        override['space_data'] = space
        override['region_data'] = space.region_3d
        override['active_object'] = self.snap_ob
        override['object'] = self.snap_ob
        override['sculpt_object'] = self.snap_ob
        
        stroke = []
        i = 0
        for co in self.projected_points:
            #if i > 100: break
            i += 1
            mouse = view3d_utils.location_3d_to_region_2d(reg, space.region_3d, co)
            l_co = imx * co
            stroke = [{"name": "my_stroke",
                        "mouse" : (mouse[0], mouse[1]),
# [Blender 4.4] Warning: 'pen_flip' parameter removed from painting operators.

                        "is_start": True,
                        "location": (l_co[0], l_co[1], l_co[2]),
                        "pressure": 1,
                        "size" : 30,
                        "time": 1}]
                      
            bpy.ops.sculpt.brush_stroke(override, stroke=stroke, mode='NORMAL', ignore_background_click=False)
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
      
    def project_grid(self, context, res = 5, offset = .5):
        '''
        will create a convex grid by bisecting
        and projecting from the view
        '''
        
        if len(self.screen_pts) != 2:
            return
        
        p1 = Vector(self.screen_pts[1])
        p0 =  Vector(self.screen_pts[0])
                 
        pL = min((p0, p1), key = lambda x: x[0]) #find the left point
        pR = max((p0, p1), key = lambda x: x[0]) #find the right point
        
        blf.size(0, self.text_size, self.dpi)
        text_size = blf.dimensions(0, self.message)
    
        Y = text_size[1]
        Z = context.region_data.view_matrix.to_quaternion() * Vector((0,0,1))
        
        mx = self.snap_ob.matrix_world
        def bisect_vector_list(l):
            midpoints = []
            for i in range(0,len(l) - 1):
                midpoints.append((l[i] + l[i+1])/2)
            
            new_points = []    
            for i in range(len(midpoints)):
                new_points += [l[i] , midpoints[i]]
            new_points += [l[-1]]
                
            return new_points     
        
        def snap_pt_to_surface(context, pt):
            '''
            takes a 3d location and ray_casts back toward the view
            '''

            rv3d = context.region_data

            z = rv3d.view_matrix.to_quaternion() * Vector((0,0,1))
            mx = self.snap_ob.matrix_world
            imx = mx.inverted()
            mx_d = mx.to_3x3()
            imx_d = mx_d.inverted()
            mx_no = imx_d.transposed()
            imx_no = mx_d.transposed()
            
            
            res, loc, no, face_ind = self.snap_ob.find_nearest(imx * pt)

            return res, mx * loc, mx_no * no
        
        def convexify_list(L_cos, direction):
            print('convexify list')
            n = len(L_cos)
            new_list = L_cos.copy()
            
            for i in range(1, n-1):
                l0 = L_cos[i]
                l_m1 = L_cos[i-1]
                l_p1 = L_cos[i+1]
                mid = .5 * (l_m1 + l_p1)
                
                delta = mid - l0
                
                if delta.dot(direction) > 0:
                    new_list[i] = mid
        
            return new_list
        
        def bisect_and_project_list(L_cos, direction):
            
            midpoints = []
            #iterate through points
            for i in range(0,len(L_cos) - 1):
                #bisect each segment
                pt = (L_cos[i] + L_cos[i+1])/2
                #ray_cast or snap that segment to surface
                pt_snap, no = self.ray_cast_pt3d(context, pt)
            
                delta = mx * pt_snap - pt
                if delta.dot(direction) > 0: #test if it is below or above the line segment
                    print('New Point ABOVE neigbors')
                    pt = mx * pt_snap
                
                midpoints.append(pt)
            
            new_points = []    
            for i in range(len(midpoints)):
                new_points += [L_cos[i] , midpoints[i]]
            new_points += [L_cos[-1]]
             
            return new_points
               
            
        bottom_row = [pL,pR]  
        middle_row = [pL + Y/2 * Vector((0,1)), pR + Y/2 * Vector((0,1))]
        top_row = [pL + Y * Vector((0,1)), pR + Y * Vector((0,1))]
        
        #border = [mx * self.ray_cast_pt(context, pt)[0] for pt in border_verts]
        bottom_row = [mx * self.ray_cast_pt(context, pt)[0] for pt in bottom_row]
        middle_row = [mx * self.ray_cast_pt(context, pt)[0] for pt in middle_row]
        top_row = [mx * self.ray_cast_pt(context, pt)[0] for pt in top_row]
        
        for i in range(0, res):
            bottom_row = bisect_and_project_list(bottom_row, -Z)
            middle_row = bisect_and_project_list(middle_row, -Z)
            top_row = bisect_and_project_list(top_row, -Z)
            
            bottom_row = convexify_list(bottom_row, -Z)
            middle_row = convexify_list(middle_row, -Z)
            top_row = convexify_list(top_row, -Z)
            
        
        
        convex_verts = bottom_row + middle_row + top_row
        surface_verts = []
        for v in convex_verts:
            snap_pt, snap_no = self.ray_cast_pt3d(context, v)
            surface_verts += [mx * snap_pt - offset * -Z]
            
        self.projected_points = convex_verts + surface_verts# + border
        '''
        bme = bmesh.new()
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        for v in convex_verts + surface_verts: # + border:
            bme.verts.new(v)
            
        bmesh.ops.convex_hull(bme, input = bme.verts[:], use_existing_faces = False)
        
        text_base_me = bpy.data.meshes.new('Text Base')
        text_base_ob = bpy.data.objects.new('Text Base', text_base_me)
        context.scene.objects.link(text_base_ob)
        bme.to_mesh(text_base_me)
        text_base_me.update()
        '''
    def calc_matrix(self, context):
        region = context.region
        rv3d = context.region_data
        
        if len(self.screen_pts) == 1:
            mid = .5 * self.screen_pts[0] + .5 * self.mouse
            p1 = Vector(self.mouse)
            p0 = Vector(self.screen_pts[0])
            
        elif len(self.screen_pts) == 2:
            mid = .5 * self.screen_pts[0] + .5 * self.screen_pts[1]
            p1 = Vector(self.screen_pts[1])
            p0 =  Vector(self.screen_pts[0])
        else:
            return Matrix.Identity(4)    
            
        pL = min((p0, p1), key = lambda x: x[0]) #find the left point
        pR = max((p0, p1), key = lambda x: x[0]) #find the right point
        
        
        
        
        Z = rv3d.view_rotation * Vector((0,0,1))
        
        x_view_world = rv3d.view_rotation * Vector((1,0,0))
        y_view_world = rv3d.view_rotation * Vector((0,1,0))
        
        user_x = pR - pL
        user_x.normalize()
        
        #the world vector of the line on the screen
        user_world_x = user_x[0] * x_view_world + user_x[1] * y_view_world
        user_world_x = user_x[0] * x_view_world + user_x[1] * y_view_world
        
        
        X = user_world_x
        Y = Z.cross(X)
        
        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
        
        return R.to_4x4()
    
    def calc_matrix_projected(self, context):
        region = context.region
        rv3d = context.region_data
        
        if len(self.screen_pts) == 1:
            mid = .5 * self.screen_pts[0] + .5 * self.mouse
            p1 = Vector(self.mouse)
            p0 = Vector(self.screen_pts[0])
            
        elif len(self.screen_pts) == 2:
            mid = .5 * self.screen_pts[0] + .5 * self.screen_pts[1]
            p1 = Vector(self.screen_pts[1])
            p0 =  Vector(self.screen_pts[0])
        else:
            return Matrix.Identity(4)    
            
        pL = min((p0, p1), key = lambda x: x[0]) #find the left point
        pR = max((p0, p1), key = lambda x: x[0]) #find the right point
        
        pLproj, no = self.ray_cast_pt(context, pL)
        pRproj, no = self.ray_cast_pt(context, pR)
        
        
        Z = rv3d.view_rotation * Vector((0,0,1))
        X_proj = pRproj - pLproj
        X_proj.normalize()
        
        x_view_world = rv3d.view_rotation * Vector((1,0,0))
        y_view_world = rv3d.view_rotation * Vector((0,1,0))
        
        user_x = pR - pL
        user_x.normalize()
        
        #the world vector of the line on the screen
        user_world_x = user_x[0] * x_view_world + user_x[1] * y_view_world
        user_world_x.normalize()
        
        user_world_y = -1 *user_x[1] * x_view_world + user_x[0] * y_view_world
        user_world_y.normalize()
        
        X = X_proj
        Z = X.cross(user_world_y)
        Y = Z.cross(X)
        
        
        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
        
        return R.to_4x4()
        
    def hover(self,context,x,y):
        '''
        hovering happens in mixed 3d and screen space.  It's a mess!
        '''
        
        self.mouse = (x,y)
        if len(self.screen_pts) == 0:
            return
        
        region = context.region
        rv3d = context.region_data
        self.mouse = Vector((x, y))
        coord = x, y
        loc3d_reg2D = view3d_utils.location_3d_to_region_2d
        
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + (view_vector * 1000)
                  
        def dist(v):
            diff = v - Vector((x,y))
            return diff.length
        
        
        closest_2d_point = min(self.screen_pts, key = dist)
        screen_dist = dist(closest_2d_point)
        
        
        if screen_dist  < 20:
            self.hovered = ['POINT',self.screen_pts.index(closest_2d_point)]
            return
        
        else:
            self.hovered = [None, -1]
            return
        
        
        
    def draw(self,context, three_d = True):
        if len(self.screen_pts) == 0: return
        
        col = (self.point_color[0], self.point_color[1], self.point_color[2], 1)
        common_drawing.draw_points(context, self.screen_pts, col, self.point_size)
        if len(self.grid_points):
            common_drawing.draw_points(context, self.grid_points, (1,0,0,1), size = 4)
            
        if self.selected != -1:
            if self.selected == 0:
                col = (.2, .2, .8, 1)
            else:
                col = (self.active_color[0],self.active_color[1],self.active_color[2],1)
            common_drawing.draw_points(context,[self.screen_pts[self.selected]], col, self.point_size)
                
        if self.hovered[0] == 'POINT':
            if self.hovered[1] == 0:
                col = (.2, .2, .8, 1)
            else:
                col = (self.active_color[0],self.active_color[1],self.active_color[2],1)
                
            common_drawing.draw_points(context,[self.screen_pts[self.hovered[1]]], col, self.point_size, )
     
        if len(self.screen_pts) == 2:
            common_drawing.draw_polyline_from_points(context, self.screen_pts, (0,0,1,1), 4, "GL_LINE_STRIP")
        
        elif len(self.screen_pts) == 1:
            common_drawing.draw_polyline_from_points(context, [self.screen_pts[0], Vector(self.mouse)], (0,0,1,1), 4, "GL_LINE_STRIP")    
        
        
        if len(self.projected_points):
            common_drawing.draw_3d_points(context, self.projected_points, (1,0,0,1), size = 6)
            
        bgl.glColor4f(.2,.2,.2,1)
        blf.enable(self.font_id,blf.ROTATION)
        blf.rotation(self.font_id, self.text_angle)
        blf.position(self.font_id, self.text_loc[0], self.text_loc[1], 0)
        blf.size(self.font_id, self.text_size, 72)
        blf.draw(self.font_id, self.message)
        blf.disable(self.font_id, blf.ROTATION)
    
    
          