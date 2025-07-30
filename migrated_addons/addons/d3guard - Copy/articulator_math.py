'''
Created on May 27, 2020

@author: Patrick


The dynamics of this articulator incoropate immediate side shift and progressive side shift

The working condyle is allowed to move laterally
https://www.researchgate.net/profile/Jung_Dug_Yang/publication/230633312/figure/fig6/AS:202797854269469@1425362184812/Movement-of-the-mandibular-condyle-A-Axial-view-of-the-mandibular-movement.png
 

'''
import time
import math

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

incisal_bvh = None

def intersect_x_axis_sphere(a,b,c,R):
    
    #equn of sphere
    #(X -a)� + (Y-b)� + (Z - C)� = R�
    #we are on X axis so y=0, z=0
    #(X -a)�  (-b)� + (-C)� = R�
    
    #X^2 - 2aX + b^2 + c^2 = r^2 
    #X^2 - 2aX  (a^2 + b^2 + c^2 - R^2) = 0
    #now convert to quatratic formunla
    
    A = 1
    B = -2 * a
    C = (a**2 + b**2 + c**2 - R**2)
    
    X0 = (-B + math.sqrt(B**2 - 4 * C))/2
    X1 = (-B - math.sqrt(B**2 - 4 * C))/2
    
    return (X0, X1)
    
def set_mandibular_bow_position(art_obj, right_lateral, left_lateral, hinge_opening):
    
    condyle_width = art_obj["intra_condyle_width"]
    bennet_angle = art_obj["bennet_angle"]
    condyle_angle = art_obj["condyle_angle"]
    condyle_track_length = art_obj["condyle_length"]
    immediate_side_shift = art_obj["immediate_side_shift"]
    side_shift_range = art_obj["side_shift_range"]
    
    
    #pin_offset = art_obj["pin_offset"]  #TODO Store This
    
    if 'Tracker Mesh' not in bpy.data.objects:
        me = bpy.data.meshes.new('Tracker Mesh')
        ob = bpy.data.objects.new('Tracker Mesh', me)
        bpy.context.scene.objects.link(ob)
        
    else:
        tracker = bpy.data.objects.get('Tracker Mesh')
        me = tracker.data 
    
    #mand_bow = [child for child in art_obj.children if 'Bottom Element' in art_obj.name][0]
    mand_bow = bpy.data.objects.get('Bottom Element')
    
    #incisal_table = [child for child in art_obj.children if 'Guide Table' in art_obj.name][0]
    incisal_table = bpy.data.objects.get('Guide Table')
    mx_table = incisal_table.matrix_world
    imx_table = mx_table.inverted()
    global incisal_bvh
    if not incisal_bvh:
        print('UPDATING THE BVH')
        bme = bmesh.new()
        bme.from_mesh(incisal_table.data)
        bvh = BVHTree.FromBMesh(bme)
        incisal_bvh = bvh
    
    T, rmx, rotation_center = calculate_matrix(left_lateral, right_lateral, hinge_opening,# + pin_offset, 
                                               condyle_width, condyle_angle, bennet_angle, 
                                               condyle_track_length, immediate_side_shift, side_shift_range)
    
    
    
    X_mand = rmx * Vector((1,0,0)) #Vector((rmx[0][0],rmx[1][0],rmx[2][0]))
    Z_mand = rmx * Vector((0,0,1)) # Vector((rmx[0][2],rmx[1][2],rmx[2][2])) #slice out the Z axis
    
    t_art = T.to_translation()
        
        
    mx_start = Matrix.Identity(4)   #placeholder for origin of mandibular bow 
    t0, r0, s0 = mx_start.decompose()
        
    # print('decomposed')
    #print(t0)
    #print(r0)
    #print(s0)
        
    dt = t0 + t_art - rotation_center
        
    #print(dt)
    tf = rotation_center + rmx * dt 
    #print("tf")
        
    T_total = Matrix.Translation(tf)
        
    mand_bow.matrix_world = T_total * rmx
    
    
    #calulate the guidance point
    t0_table = incisal_table.matrix_world.to_translation()
    dt_table = t0_table + t_art - rotation_center
    guidance_point = rotation_center + rmx * dt_table
    
    #Search for inersection in a 4 degree arc at .1 degree increments
    search_width = 6 * math.pi/180
    search_res = .1 * search_width
    
    #TODO binary search
    start = time.time()
    total_iters = 0
    theta_start = -search_width
    while search_res > .0005 * math.pi/180 and total_iters < 1000:
        
        for i in range(0, int(2 * search_width/search_res)):
            total_iters += 1
            theta = theta_start + i * search_res
            R0 = Matrix.Rotation(theta, 3, X_mand)
            R1 = Matrix.Rotation(theta + search_res, 3, X_mand)
        
            v0 = R0 * guidance_point
            v1 = R1 * guidance_point
            
            r = v1 - v0
            d = r.length
            r.normalize()
            
            #intersect the circle segment with the incisal table
            #res, loc, no, ind = incisal_table.ray_cast(imx_table * v0, r, d)
        
            loc, no, ind, d = incisal_bvh.ray_cast(imx_table * v0, r, d)
        
            if loc:
                theta_start = theta
                search_width = 2 * search_res
                search_res = .1 * search_width
                break
            
        if not loc:
            print('Could not find intersection')
            return T_total * rmx
    finish = time.time()
    #print('Ray cast binary search in %f seconds' % (finish-start))
    if loc:
        print('found it on the %i iteration' % total_iters)
            
    if not loc:
        #we went beyond the incisal table
        return T_total * rmx
    

    me.vertices.add(count = 1)
    me.vertices[-1].co = mx_table * loc
    
    d_theta = math.asin((mx_table * loc - v0).length/(2*guidance_point.length))
                        
    print('d_theta rotation %f' % d_theta)
    
    mx_guidance = Matrix.Rotation(theta + d_theta, 4, X_mand)

    return T_total * mx_guidance * rmx
    #mand_bow.matrix_world = T_total * mx_guidance * rmx

def calculate_matrix(left_lateral, right_lateral, hinge_opening,
                     condyle_width, condyle_angle, bennet_angle, condyle_track_length,
                     immediate_side_shift = 1.5,
                     side_shift_range = 2.0
                     ):
    
    '''
    right_lateral and left lateral are a percentage of the track range 0 to 1
    hinge_opening in radians
    condyle_width in mm
    condyle_angle in radians
    bennet_angle in radians
    condyle track length in MM
    immediate_side_shift in mm
    side_shift_range in mm
    '''
    
    print(immediate_side_shift)
    print(side_shift_range)
    
    #print('Calculating matrix')
    orig_LC = Vector((condyle_width/2, 0, 0)) #40))
    orig_RC = Vector((-condyle_width/2, 0, 0))
    
    #print(orig_LC)
    mx_condyle_angle = Matrix.Rotation(math.pi * condyle_angle/180, 4, 'X')
    #print(mx_condyle_angle)
    mx_bennet_angleR = Matrix.Rotation(bennet_angle * math.pi/180, 4, mx_condyle_angle * Vector((0,0,1)))
    #print(mx_bennet_angleR)
    mx_bennet_angleL = Matrix.Rotation(bennet_angle * math.pi/180, 4, mx_condyle_angle * Vector((0,0,-1)))
    #print(mx_bennet_angleL)
    
    track_directionL = mx_bennet_angleL * mx_condyle_angle * Vector((0,-1, 0))  #the overall track direction which is a composite of ISS + PSS
    track_directionR = mx_bennet_angleR * mx_condyle_angle * Vector((0,-1, 0))
    
    L = Vector((1,0,0))
    R = Vector((-1,0,0))
    
    #deal with side shift
    iss_range = side_shift_range/condyle_track_length  #normalize to a percentage
    pss_range = (condyle_track_length - side_shift_range)/condyle_track_length #normalized to percentage   
    
    #Total side shift at end of the track is just the X component of the total track
    t_ss_left = track_directionL.dot(R) * condyle_track_length
    t_ss_right = track_directionR.dot(L) * condyle_track_length   
    
    immediate_side_shift = min(t_ss_left, immediate_side_shift)  #Make sure ISS isn't greater than TotalSideShift
    immediate_side_shift = max(immediate_side_shift, iss_range * t_ss_left)   #make sure ISS isn't less than PSS in the iss_range
    
    
    #print('immediate side shift')
    #print(immediate_side_shift)
    
    progressive_l = t_ss_left - immediate_side_shift  #scalar amount of progressive  side shift, the remaining side shift
    progressive_r = t_ss_right - immediate_side_shift 
    
    #print('Progressive L R')
    #print(progressive_l)
    #print(progressive_r)
    
    #print('ISS Range, PSS Range ')
    #print(iss_range)
    #print(pss_range)
    
    #Viss_l = normal track displacement + immediate_side_shift amount 

    Viss_l = iss_range * condyle_track_length * (track_directionL - track_directionL.dot(R) * R)  + immediate_side_shift * R
    Viss_r = iss_range * condyle_track_length * (track_directionR - track_directionR.dot(L) * L)  + immediate_side_shift * L
    
    Vpss_l = condyle_track_length * track_directionL - Viss_l
    Vpss_r = condyle_track_length * track_directionR - Viss_r
    
    
    #now we make the piecewise vectors representing the two condylar paths
    def left_condyle_vec(left_lateral):
        
        return min(left_lateral/iss_range, 1) * Viss_l + max(0, (left_lateral - iss_range)/pss_range) * Vpss_l
        
    def right_condyle_vec(right_lateral):
        
        return min(right_lateral/iss_range, 1) * Viss_r + max(0, (right_lateral - iss_range)/pss_range) * Vpss_r    
    
    
    if 'Tracker Mesh' not in bpy.data.objects:
        me = bpy.data.meshes.new('Tracker Mesh')
        ob = bpy.data.objects.new('Tracker Mesh', me)
        bpy.context.scene.objects.link(ob)
        
    else:
        tracker = bpy.data.objects.get('Tracker Mesh')
        me = tracker.data 
        
    
    #calculate the early side shift
    if left_lateral < .001:
        #shift = (self.left_lateral - self.right_lateral) *ector((1,0,0))
        
        rc = orig_RC + right_condyle_vec(right_lateral)
        
        a, b, c = rc[0], rc[1], rc[2]
        A = 1
        B = -2 * a
        C = (a**2 + b**2 + c**2 - condyle_width**2)
    
        lx = (-B + math.sqrt(B**2 - 4 * C))/2  #intersect sphere with x axis to find left condyle
        
        lc = Vector((lx, 0, 0))
        
        me.vertices.add(count = 1) 
        me.vertices[-1].co = rc

        me.vertices.add(count = 1) 
        me.vertices[-1].co = lc
    
    
    
    elif right_lateral < .001:
        
        lc = orig_LC + left_condyle_vec(left_lateral)

        a, b, c = lc[0], lc[1], lc[2]
        A = 1
        B = -2 * a
        C = (a**2 + b**2 + c**2 - condyle_width**2)
    
        rx = (-B - math.sqrt(B**2 - 4 * C))/2  #intersect sphere with x axis to find left condyle
        
        rc = Vector((rx, 0, 0))
        
        me.vertices.add(count = 1) 
        me.vertices[-1].co = rc

        me.vertices.add(count = 1) 
        me.vertices[-1].co = lc
        
        
    else:
        
       
        #calculate the protruded position first
        pro = min(left_lateral, right_lateral)
        lvc_i = left_condyle_vec(pro)
        rvc_i = right_condyle_vec(pro)
        
        vec_pro = .5*(lvc_i + rvc_i)  #this should cancel out side shifts and get just the anterior and inferior movement
        
        print('Vec Protrusion')
        print(vec_pro)
        
        if right_lateral < left_lateral:
            
            lc_vec = left_condyle_vec(left_lateral)
            lc_eff = orig_LC + lc_vec - lvc_i #.dot(R)*R  #remove the side shift from first part cancelled by other side
            
            lc = vec_pro + lc_eff
            
            a, b, c = lc_eff[0], lc_eff[1], lc_eff[2]
            A = 1
            B = -2 * a
            C = (a**2 + b**2 + c**2 - condyle_width**2)
    
            rx = (-B - math.sqrt(B**2 - 4 * C))/2  #intersect sphere with x axis to find left condyle
            rc = Vector((rx, 0, 0)) + vec_pro
        
        
        
            
        else: #left_lateral <= right_lateral
            
            rc_vec = right_condyle_vec(right_lateral)
            rc_eff = orig_RC + rc_vec - rvc_i #.dot(L)*L  #remove the side shift from first part cancelled by other side
            
            rc = vec_pro + rc_eff
            
            a, b, c = rc_eff[0], rc_eff[1], rc_eff[2]
            A = 1
            B = -2 * a
            C = (a**2 + b**2 + c**2 - condyle_width**2)
    
            lx = (-B + math.sqrt(B**2 - 4 * C))/2  #intersect sphere with x axis to find left condyle
            lc = Vector((lx, 0, 0)) + vec_pro
            
            
        
    
    #condyle_position = condyle_original_positino + percentage_tanslation * condyle length * direction_vector
    #in our world, the condyles are fixed length apart so we will have to make corrections to shit
    #pos_LC = orig_LC + left_lateral * condyle_track_length * track_directionL + v_shift
    #pos_RC = orig_RC + right_lateral * condyle_track_length * track_directionR + v_shift
    
    pos_LC = lc
    pos_RC = rc
    
    #me.vertices.add(count = 1) 
    #me.vertices[-1].co = pos_RC

    #me.vertices.add(count = 1) 
    #me.vertices[-1].co = pos_LC

    #calculate progressive shift
    #Straight PROTRUSION
    if abs(left_lateral - right_lateral) < .001:
        rotation_origin = .5 * (pos_LC + pos_RC)
        d_condyle = rotation_origin - .5 * (orig_LC + orig_RC)
    #Left Working    
    elif left_lateral < right_lateral:  #there is more movement in the right condyle than the left
        rotation_origin = pos_LC
        d_condyle = pos_LC - orig_LC 
        #d_bennet_l = (pos_RC - orig_RC).dot(Vector((1,0,0)))
        #d_bennet_r = (pos_LC - orig_LC).dot(Vector((1,0,0)))
        
        #d_bennet = d_bennet_l + d_bennet_r
        #if d_bennet > immediate_side_shift:
        #    pos_LC = orig_LC + d_bennet * Vector((1, 0, 0))   
        
    #Right Working    
    else:  #there is more movement in left condyle, so right working
        rotation_origin = pos_RC
        d_condyle = pos_RC - orig_RC  #how much the non-working side has moved
        #d_bennet_r = (pos_LC - orig_LC).dot(Vector((-1,0,0)))  #how much the non-working side has moved
        #d_bennet_l = (pos_RC - orig_RC).dot(Vector((-1,0,0)))
        
        #d_bennet = d_bennet_l + d_bennet_r 
        #if d_bennet > immediate_side_shift:
        #    pos_RC = orig_RC + d_bennet * Vector((-1, 0, 0))
        
        
    X = pos_LC - pos_RC
    print(X.length)
    X.normalize()
    mx_hinge = Matrix.Rotation(hinge_opening * math.pi/180, 4, X)
    
      
    condyle_width = (pos_RC - pos_LC).length
    print(condyle_width)     
    
    T = Matrix.Translation(d_condyle)  #the amount the condyle has moved, the jaw must move that amount too
    
    #print(T)
    Z = Vector((0,0,1))
    #hinge_mx = Matrix.Rotation(12 * math.pi/180, 3, X)
    Z = mx_hinge * Z
    Y = Z.cross(X)
    Y.normalize()
    Z = X.cross(Y)
    
    rmx_total = Matrix.Identity(4)
    rmx_total[0][0], rmx_total[0][1], rmx_total[0][2]  = X[0] ,Y[0],  Z[0]
    rmx_total[1][0], rmx_total[1][1], rmx_total[1][2]  = X[1], Y[1],  Z[1]
    rmx_total[2][0] ,rmx_total[2][1], rmx_total[2][2]  = X[2], Y[2],  Z[2]
    
    
    #print(T, rmx_total)
    #print('We made it to the end')
    return (T, rmx_total, rotation_origin)

    
#def update_mand_bow_mx():
        
        #print('changing active object matrix')
#        obj = bpy.context.active_object
        
        #print(obj.name)
        
#        T, rmx, rotation_center = calculate_matrix()
        
        #rotation_ob = bpy.data.objects.get('Rotation Origin')
        #if rotation_ob:
        #    print('Setting rotation obj matrix')
        #    rotation_ob.location = rotation_center
        
        #side_shift_indicator = bpy.data.objects.get('Side Shift')
        #if side_shift_indicator:
        #    print('Setting side shiff obj matrix')
        #    side_shift_indicator.matrix_world = T
            
            
#        t_art = T.to_translation()
        
        
        
#        t0, r0, s0 = self.mx_start.decompose()
        
#        print('decomposed')
        #print(t0)
        #print(r0)
        #print(s0)
        
#        dt = t0 + t_art - rotation_center
        
        #print(dt)
#        tf = rotation_center + rmx * dt 
        #print("tf")
        
#        T_total = Matrix.Translation(tf)
        
#        obj.matrix_world = T_total * rmx
        
#        print('This is the matrix')
#        print(T_total * rmx)