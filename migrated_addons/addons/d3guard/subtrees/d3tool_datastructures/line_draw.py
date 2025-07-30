'''
A couple of helper classes for curves
'''

import math

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bgl
import bmesh
import blf

from mathutils import Vector, Matrix
from bpy_extras import view3d_utils

from .. import common_drawing
from ...subtrees.addon_common.common.debug import simple_circle
                                                                 
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




    def project_points(self, context):
        '''
        -if depth is Surface, it will ray_cast the object and place it there
        -if depth is 'BOUNDS' it will place the matrix with translation at the
        midpoint of the user drawn line at the depth of the bbox center
        '''
        region = context.region
        rv3d = context.region_data
        
        if len(self.box_coords) < 2: return None
        
        
        
        coords_3d = []
        
        for pt in self.box_coords:
            view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, pt)
            ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, pt)
            ray_target = ray_origin + (view_vector * 1000)
        
            mx = self.snap_ob.matrix_world
            imx = mx.inverted()
        
        
            res, loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target - imx * ray_origin)
            if not res:
                coords_3d.append(None)
                   
            else:
                coords_3d.append(mx * loc)
               
       
        iters = 0 
        while None in coords_3d and iters < len(coords_3d):
            print(coords_3d)
            iters += 1
            for i,pt in enumerate(coords_3d):
                if pt == None:
                    np1 = int(math.fmod(i+1, len(coords_3d)))
                    nm1 = int(math.fmod(i-1, len(coords_3d)))
                    neighbor_ahead = coords_3d[np1]
                    neighbor_behind = coords_3d[nm1]
                    
                    if neighbor_ahead == None and neighbor_behind == None:
                        continue
                    
                    elif neighbor_ahead != None and neighbor_behind != None:
                        
                        print(neighbor_ahead)
                        print(neighbor_behind)
                        center = .5 * (neighbor_ahead + neighbor_behind)
                        v_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, self.box_coords[i], center)
                        coords_3d[i] = v_3d
                        
                    elif neighbor_ahead != None and neighbor_behind == None:
                        v_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, self.box_coords[i], neighbor_ahead)
                        coords_3d[i] = v_3d
                    else:
                        v_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, self.box_coords[i], neighbor_behind)
                        coords_3d[i] = v_3d
    
        return coords_3d
    
    def re_project_points(self, context, coords_3d, epsilon = .0001, max_depth = 100):
        '''
        will project the points again
        '''
        region = context.region
        rv3d = context.region_data
        
        
        new_coords_3d = []
        
        for i, pt in enumerate(coords_3d):
            
            pt2d = self.box_coords[i]
            view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, pt2d)
            ray_origin = pt + epsilon * view_vector
            ray_target = ray_origin + (view_vector * max_depth)
        
            mx = self.snap_ob.matrix_world
            imx = mx.inverted()
        
        
            res, loc, no, face_ind = self.snap_ob.ray_cast(imx * ray_origin, imx * ray_target - imx * ray_origin)
            if not res:
                new_coords_3d.append(None)
                   
            else:
                new_coords_3d.append(mx * loc)
               
       
        iters = 0 
        while None in new_coords_3d and iters < len(new_coords_3d):
            iters += 1
            for i,pt in enumerate(new_coords_3d):
                if pt == None:
                    np1 = int(math.fmod(i+1, len(new_coords_3d)))
                    nm1 = int(math.fmod(i-1, len(new_coords_3d)))
                    neighbor_ahead = new_coords_3d[np1]
                    neighbor_behind = new_coords_3d[nm1]
                    
                    if neighbor_ahead == None and neighbor_behind == None:
                        continue
                    
                    elif neighbor_ahead != None and neighbor_behind != None:
                        
                        print(neighbor_ahead)
                        print(neighbor_behind)
                        center = .5 * (neighbor_ahead + neighbor_behind)
                        v_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, self.box_coords[i], center)
                        new_coords_3d[i] = v_3d
                        
                    elif neighbor_ahead != None and neighbor_behind == None:
                        v_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, self.box_coords[i], neighbor_ahead)
                        new_coords_3d[i] = v_3d
                    else:
                        v_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, self.box_coords[i], neighbor_behind)
                        new_coords_3d[i] = v_3d
    
        return new_coords_3d
    
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
        
        
    
    def calc_circle(self):
        
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
        
        r_screen = (self.screen_pts[1] - self.screen_pts[0]).length/2
        self.box_coords = simple_circle(mid_screen[0], mid_screen[1], r_screen, 30)
        
           
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

        if len(self.box_coords) > 2:
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
    

          