'''
@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import math
import time

from mathutils import Vector, Matrix, Color, Quaternion, kdtree
from mathutils.geometry import intersect_point_line, intersect_line_plane
from mathutils.bvhtree import BVHTree


from bpy.props import FloatProperty, BoolProperty, IntProperty, EnumProperty

#from bmesh_fns import bmesh_loose_parts

#copy from bmesh_fns
def face_neighbors(bmface):
    neighbors = []
    for ed in bmface.edges:
        neighbors += [f for f in ed.link_faces if f != bmface]
        
    return neighbors

def face_neighbors_by_vert(bmface):
    neighbors = []
    for v in bmface.verts:
        neighbors += [f for f in v.link_faces if f != bmface]
    return neighbors    
def flood_selection_faces(bme, selected_faces, seed_face, expansion_mode = 'VERTEX', max_iters = 1000):
    '''
    bme - bmesh
    selected_faces - should create a closed face loop to contain "flooded" selection
    if an empty set, selection will grow to non manifold boundaries
    seed_face - a BMFace within/out selected_faces loop, or a LIST of faces
    expansion_mode = 'VERTEX' or 'EDGE' will epxand based on edge.link_faces or v.link_faces
    max_iters - maximum recursions to select_neightbors
    
    returns:
        -a set of BMFaces
    '''
    total_selection = set([f for f in selected_faces])
    levy = set([f for f in selected_faces])  #it's funny because it stops the flood :-)

    if expansion_mode == 'VERTEX':
        neighbor_fn = face_neighbors_by_vert
    else:
        neighbor_fn = face_neighbors
        
        
    if isinstance(seed_face, bmesh.types.BMFace):
        new_faces = set(neighbor_fn(seed_face)) - levy
        
    elif isinstance(seed_face, list):
        new_candidates = set()
        for f in seed_face:
            new_candidates.update(neighbor_fn(f))   
        new_faces = new_candidates - total_selection
        total_selection |= new_faces
    
    elif isinstance(seed_face, set):
        new_candidates = set()
        for f in seed_face:
            new_candidates.update(neighbor_fn(f))   
        new_faces = new_candidates - total_selection
        total_selection |= new_faces
            
    iters = 0
    while iters < max_iters and new_faces:
        iters += 1
        new_candidates = set()
        for f in new_faces:
            new_candidates.update(neighbor_fn(f))
            
        new_faces = new_candidates - total_selection
        
        if new_faces:
            total_selection |= new_faces    
    if iters == max_iters:
        print('max iterations reached')    
    return total_selection   
    
def bmesh_loose_parts(bme, selected_faces = None, max_iters = 100): 
    '''
    bme - BMesh
    selected_faces = list, set or None
    max_iters = maximum amount
    
    return - list of lists of BMFaces
    '''
    if selected_faces == None:
        total_faces = set(bme.faces[:])
    else:
        if isinstance(selected_faces, list):
            total_faces = set(selected_faces)
        elif isinstance(selected_faces, set):
            total_faces = selected_faces.copy()
            
        else:
            #raise exception
            return []
        
    islands = []
    iters = 0
    while len(total_faces) and iters < max_iters:
        iters += 1
        seed = total_faces.pop()
        island = flood_selection_faces(bme, {}, seed, max_iters = 10000)
        islands += [island]
        total_faces.difference_update(island)
    
    return islands

#copy from odcutils
# calculate a best-fit plane to the given vertices
#modified from looptoos script
def calculate_plane(locs, itermax = 500, debug = False):
    '''
    args: 
    vertex_locs - a list of type Vector
    return:
    normal of best fit plane
    '''
    if debug:
        start = time.time()
        n_verts = len(locs)
    
    # calculating the center of masss
    com = Vector()
    for loc in locs:
        com += loc
    com /= len(locs)
    x, y, z = com
    
    # creating the covariance matrix
    mat = Matrix(((0.0, 0.0, 0.0),
                  (0.0, 0.0, 0.0),
                  (0.0, 0.0, 0.0),
                   ))
    for loc in locs:
        mat[0][0] += (loc[0]-x)**2
        mat[1][0] += (loc[0]-x)*(loc[1]-y)
        mat[2][0] += (loc[0]-x)*(loc[2]-z)
        mat[0][1] += (loc[1]-y)*(loc[0]-x)
        mat[1][1] += (loc[1]-y)**2
        mat[2][1] += (loc[1]-y)*(loc[2]-z)
        mat[0][2] += (loc[2]-z)*(loc[0]-x)
        mat[1][2] += (loc[2]-z)*(loc[1]-y)
        mat[2][2] += (loc[2]-z)**2
    
    # calculating the normal to the plane
    normal = False
    try:
        mat.invert()
    except:
        if sum(mat[0]) == 0.0:
            normal = Vector((1.0, 0.0, 0.0))
        elif sum(mat[1]) == 0.0:
            normal = Vector((0.0, 1.0, 0.0))
        elif sum(mat[2]) == 0.0:
            normal = Vector((0.0, 0.0, 1.0))
    if not normal:
        # warning! this is different from .normalize()
        iters = 0
        vec = Vector((1.0, 1.0, 1.0))
        vec2 = (mat * vec)/(mat * vec).length
        while vec != vec2 and iters < itermax:
            iters+=1
            vec = vec2
            vec2 = mat * vec
            if vec2.length != 0:
                vec2 /= vec2.length
        if vec2.length == 0:
            vec2 = Vector((1.0, 1.0, 1.0))
        normal = vec2


    if debug:
        if iters == itermax:
            print("looks like we maxed out our iterations")
        print("found plane normal for %d verts in %f seconds" % (n_verts, time.time() - start))
    
    return normal  
   
class D3SPLINT_OT_refractory_model(bpy.types.Operator):
    '''Calculates selective blockout and a compensation gap, takes 35 to 55 seconds'''
    bl_idname = 'd3splint.refractory_model'
    bl_label = "Create Refractory Model"
    bl_options = {'REGISTER','UNDO'}
    
    
    b_radius = FloatProperty(default = .05 , min = .01, max = .12, description = 'Allowable Undercut, larger values results in more retention, more snap into place', name = 'Undercut')
    c_radius = FloatProperty(default = .12 , min = .05, max = .25, description = 'Compensation Gap, larger values results in less retention, less friction', name = 'Compensation Gap')
    d_radius = FloatProperty(default = 1.0, min = 0.5, max = 2.0, description = 'Drill compensation removes small concavities to account for the size of milling tools')
    resolution = FloatProperty(default = 1.5, description = 'Mesh resolution. 1.5 seems ok?')
    scale = FloatProperty(default = 10, description = 'Only chnage if willing to crash blender.  Small chnages can make drastic differences')
    
    max_blockout = FloatProperty(default = 10.0 , min = 2, max = 10.0, description = 'Limit the depth of blockout to save processing itme', name = 'Blockout Limit')
    override_large_angle = BoolProperty(name = 'Angle Override', default = False, description = 'Large deviations between insertion asxis and world Z')
    use_drillcomp = BoolProperty(name = 'Use Drill Compensation', default = False, description = 'Do additional calculation to overmill sharp internal angles')
    #use_drillcomp_Dev = BoolProperty(name = 'Use Drill Compensation Dev', default = False, description = 'Add an actual mesh sphere at surface')
    angle = FloatProperty(default = 0.0 , min = 0.0, max = 180.0, description = 'Angle between insertion axis and world Z', name = 'Insertion angle')
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        return  True

    
    def draw(self,context):
        
        layout = self.layout
    
        row = layout.row()
        row.prop(self, "b_radius")
        
        row = layout.row()
        row.prop(self, "c_radius")
        
        row = layout.row()
        row.prop(self, "max_blockout")
        
        row = layout.row()
        row.prop(self, "use_drillcomp")
        
        row = layout.row()
        row.prop(self, "d_radius")
        
        if self.angle > 25:
            row = layout.row()
            msg  = 'The angle between insertion axis and world z is: ' + str(self.angle)[0:3]
            row.label(msg)
            
            row = layout.row()
            row.label('You will need to confirm this by overriding')
            
            row = layout.row()
            row.label('Consider cancelling (right click) and inspecting your insertion axis')
            
            row = layout.row()
            row.prop(self, "override_large_angle")
            
    def invoke(self,context, evenet):
        #gather some information
        
        #determines 3D direction
        #Axis = bpy.data.objects.get('Insertion Axis')
        #if Axis == None:
        #    self.report({'ERROR'},'Need to set survey from view first, then adjust axis arrow')
        #    return {'CANCELLED'}
        
        #if len(context.scene.odc_splints) == 0:
        #    self.report({'ERROR'},'Need to plan a splint first')
        #    return {'CANCELLED'}
        #n = context.scene.odc_splint_index
        #splint = context.scene.odc_splints[n]
        
        #axis_z = Axis.matrix_world.to_quaternion() * Vector((0,0,1))
        
        #if splint.jaw_type == 'MAXILLA':
        #    Z = Vector((0,0,-1))
        #else:
        #    Z = Vector((0,0,1))
            
        #angle = axis_z.angle(Z)
        #angle_deg = 180/math.pi * angle
        
        #if angle_deg > 35:
        #    self.angle = angle_deg
            
        #settings = get_settings()
        #self.c_radius = settings.def_passive_radius
        #self.b_radius = settings.def_blockout_radius
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        global_total_start = time.time()
        #settings = get_settings()
        #dbg = settings.debug
        #n = context.scene.odc_splint_index
        #splint = context.scene.odc_splints[n]
        
        Model = context.object  #a dense triangle mesh
        
        #if Model == None:
        #    self.report({'ERROR'},'Need to set the model first')
        #    return {'CANCELLED'}
        
        #Axis = bpy.data.objects.get('Insertion Axis')
        #if Axis == None:
        #    self.report({'ERROR'},'Need to set survey from view first, then adjust axis arrow')
        #    return {'CANCELLED'}
        
        #if splint.jaw_type == 'MAXILLA':
        #    Z = Vector((0,0,-1))
        #else:
        #    Z = Vector((0,0,1))
            
        #axis_z = Axis.matrix_world.to_quaternion() * Vector((0,0,1))    
        #angle = axis_z.angle(Z)
        
        axis = Vector((0,0,1))
        
        #angle_deg = 180/math.pi * angle
        
        #if angle_deg > 35 and not self.override_large_angle:
        #    self.report({'ERROR'},'The insertion axis is very deviated from the world Z,\n confirm this is correct by using the override feature or \nsurvey the model from view again')
        #    return {'CANCELLED'}
            
            
        start = time.time()
        interval_start = start
        
        #I actually use 
        #Trim = bpy.data.objects.get('Trimmed_Model')
        #Perim = bpy.data.objects.get('Perim Model')

        #if not Trim:
        #    self.report({'ERROR'}, 'Must trim the upper model first')
        #    return {'CANCELLED'}
        #if not Perim:
        #    self.report({'ERROR'}, 'Must trim the upper model first')
        #    return {'CANCELLED'}
           
        
        model_mx = Model.matrix_world
        model_imx = model_mx.inverted()
         
        bme = bmesh.new()
        bme_pp = bmesh.new() #BME Pre Processing (by modifiers)
        
        bme.from_mesh(Model.data)
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        
        #Pre process an temp object with offset and smoothing
        me = bpy.data.meshes.new('Temp Offset')
        ob2 = bpy.data.objects.new('Temp Offset', me)
        context.scene.objects.link(ob2)
        bme.to_mesh(ob2.data)
        ob2.matrix_world = model_mx
        
        #pre-offset inard
        mod1 = ob2.modifiers.new('Displace', type = 'DISPLACE')
        mod1.mid_level = 1 - (.22 + self.b_radius)
        mod1.strength = -1
        
        #smooth
        mod2 = ob2.modifiers.new('Smooth', type = 'SMOOTH')
        mod2.iterations = 20
        
        #re-snap to surface with adjustment
        mod3 = ob2.modifiers.new('Shrinkwrap', type = 'SHRINKWRAP')
        mod3.target = Model
        mod3.offset = .22 + self.b_radius
        
        #smooth again
        mod4 = ob2.modifiers.new('Smooth', type = 'SMOOTH')
        mod4.iterations = 10
        
        #get a bmesh representation of the pre-processed verts
        bme_pp.from_object(ob2, context.scene)
        bme_pp.verts.ensure_lookup_table()
        bme_pp.edges.ensure_lookup_table()
        bme_pp.faces.ensure_lookup_table()
        
        print('Finished pre-processing in %f' % (time.time() - interval_start))
        interval_start = time.time()
        
               
        #local_axis_z = i_mx.to_quaternion() * axis
        #local_axis_z.normalize()
        
        #just use the local Z axis to find undercut faces
        local_axis_z = Vector((0,0,1))
        undercut_verts = set()
        for f in bme.faces:
            if f.normal.dot(local_axis_z) < -.01:
                undercut_verts.update([v for v in f.verts])
        
        perimeter_verts = set()
        perimeter_faces = set()
        for ed in bme.edges:
            if len(ed.link_faces) == 1:
                perimeter_verts.update([ed.verts[0], ed.verts[1]])
                for v in ed.verts:
                    perimeter_faces.update([f for f in v.link_faces])
        

        #often the verts at the perimeter get mislabeled.  We will handle them
        #for f in perimeter_faces:
        #    undercut_verts.difference_update([v for v in f.verts])
        
        fit_plane_co = Vector((0,0,0))
        for v in perimeter_verts:
            fit_plane_co += v.co
        fit_plane_co *= 1/len(perimeter_verts)
        fit_plane_no = calculate_plane([v.co for v in list(perimeter_verts)])
        
        if fit_plane_no.dot(local_axis_z) < 0:
            fit_plane_no *= -1
            
        
        base_plane_v = min(list(perimeter_verts), key = lambda x: (x.co - fit_plane_co).dot(fit_plane_no))
        base_plane_co = base_plane_v.co + .2 * fit_plane_no
        
        base_plane_center_max_height = fit_plane_co + (base_plane_v.co - fit_plane_co).dot(fit_plane_no) * fit_plane_no
        #Add the base plane to the scene with BBox larger than the model
        bbox = Model.bound_box[:]
        bbox_vs = [Vector(a) for a in bbox]
        
        v_max_x= max(bbox_vs, key = lambda x: x[0])
        v_min_x = min(bbox_vs, key = lambda x: x[0])
        v_max_y= max(bbox_vs, key = lambda x: x[1])
        v_min_y = min(bbox_vs, key = lambda x: x[1])
        
        diag_xy = (((v_max_x - v_min_x)[0])**2 + ((v_max_y - v_min_y)[1])**2)**.5
        
        T_cut = Matrix.Translation(base_plane_center_max_height)
        Z_cut = fit_plane_no
        X_cut = Vector((1,0,0)) - Vector((1,0,0)).dot(fit_plane_no) * fit_plane_no
        X_cut.normalize()
        Y_cut = Z_cut.cross(X_cut)
        
        R_cut = Matrix.Identity(3)
        R_cut[0][0], R_cut[0][1], R_cut[0][2]  = X_cut[0] ,Y_cut[0],  Z_cut[0]
        R_cut[1][0], R_cut[1][1], R_cut[1][2]  = X_cut[1], Y_cut[1],  Z_cut[1]
        R_cut[2][0] ,R_cut[2][1], R_cut[2][2]  = X_cut[2], Y_cut[2],  Z_cut[2]
        
        R_cut = R_cut.to_4x4()
        
        base_cut = bmesh.new()
        bmesh.ops.create_grid(base_cut, x_segments = 100, y_segments = 100, size = .5 * diag_xy, matrix = T_cut * R_cut)
        if 'Auto Base' not in bpy.data.objects:
            a_base_me = bpy.data.meshes.new('Auto Base')
            a_base = bpy.data.objects.new('Auto Base', a_base_me)
            a_base.matrix_world = model_mx
            base_cut.to_mesh(a_base_me)
            context.scene.objects.link(a_base)
        else:
            a_base = bpy.data.objects.get('Auto Base')
            base_cut.to_mesh(a_base.data)
            a_base.matrix_world = model_mx
        base_cut.free()
        
        print('Identified undercuts and best fit base in %f' % (time.time() - interval_start))
        interval_start = time.time()
        
        
        meta_data = bpy.data.metaballs.new('Blockout Meta')
        meta_obj = bpy.data.objects.new('Blockout Meta', meta_data)
        meta_data.resolution = self.resolution
        meta_data.render_resolution = self.resolution
        context.scene.objects.link(meta_obj)
        
        
        #No Longer Neded we pre-process the mesh
        #relax_loops_util(bme, [ed for ed in bme.edges if len(ed.link_faces) == 1], iterations = 10, influence = .5, override_selection = True, debug = True)
        #undisplaced_locs = dict()
        #pre_discplacement = self.radius + .17
        #for v in bme.verts:
        #    undisplaced_locs[v] = (v.co, v.normal)
        #    v.co -= pre_discplacement * v.normal
            
        #bme.normal_update()
        #mx_check = Trim.matrix_world
        #imx_check = mx_check.inverted()
        #bme_check = bmesh.new()
        #bme_check.from_mesh(Trim.data)
        #bme_check.verts.ensure_lookup_table()
        #bme_check.edges.ensure_lookup_table()
        #bme_check.faces.ensure_lookup_table()
        
        #a bvh is used to check the final surface
        bvh = BVHTree.FromBMesh(bme)
        
        #a KD tree of all particles is used to check that no spacing
        #is so large that there will be holes in the particle surface
        kd = kdtree.KDTree(len(bme.verts))
        for i in range(0, len(bme.verts)-1):
            kd.insert(bme.verts[i].co, i)        
        kd.balance()
        
        
        n_voids = 0 
        n_elements = 0

        milled_verts = set()
        cached_ray_results = {}
        unmilled_verts = set()
        drill_centers= []
        n_filter = 0
    
        #we are going to ignore the drill compensation for now!
        
        #if self.use_drillcomp:   
        #    for v in bme.verts:
        #        if v.index in milled_verts:
        #            n_filter += 1
        #            continue
        #        start_co = v.co - .0001 * v.normal
                
        #        drill_center = v.co - .88 *  (self.d_radius - .5 * self.c_radius) * v.normal
        #        r = -1 * v.normal
                
        #        loc, no, face_ind, d = bvh.ray_cast(start_co, r)
        #        cached_ray_results[v.index] = (loc, no, face_ind, d)
                
        #        if loc == None or (loc != None and d > 2 * self.d_radius):
        #            #no reasonable backside collisions, add a ball and continue   
        #            mb_d = meta_data.elements.new(type = 'BALL')
        #            mb_d.radius = self.scale * self.d_radius
        #            mb_d.co = self.scale * drill_center
                
                    #nearby_bvh = bvh.find_nearest_range(v.co - self.d_radius * v.normal, self.d_radius + .1 )
        #            nearby_kd = kd.find_range(drill_center, .7 * self.d_radius)
                
        #            for nearby_co, nearby_ind, nearby_d in nearby_kd:
        #                milled_verts.add(nearby_ind)
                    
                    #milled_verts.update([ele[1] for ele in nearby_kd])
        #            drill_centers += [drill_center]
                    
        #        else:
        #            unmilled_verts.add(v.index)
                    
                    
        #    print('filtered %i verts on first pass' % n_filter)
        
        #take a 2nd pass over the mesh, but ignore the already compensated for verts
        #corrected_verts = 0
        #kd_drill = kdtree.KDTree(len(drill_centers))
        #for i in range(0, len(drill_centers)-1):
        #    kd_drill.insert(drill_centers[i], i) 
        #kd_drill.balance()
        
        #n_filter = 0
        #for ind in unmilled_verts:
        
        #    v = bme.verts[ind]
        #    corrected_verts += 1
        #    start_co = v.co - .0001 * v.normal
            
        #    drill_center = v.co - .9 *  (self.d_radius - .5 * self.c_radius) * v.normal
            
        #    l_find, ind_find, d_find = kd_drill.find(drill_center)
        #    
        #    if d_find < .25 * self.d_radius: 
                
        #        n_filter += 1
        #        continue
            
        #    r = -1 * v.normal
            
            
            
        #    loc, no, face_ind, d = cached_ray_results[v.index]
            
        #    nearby_kd = kd.find_range(drill_center, self.d_radius)        
            
        #    other_side = [ele for ele in nearby_kd if bme.verts[ele[1]].normal.dot(-v.normal) > 0]
            
        #    if len(other_side):
            #    print('found nearby verts on other side of mesh')
        #        ele_max = max(other_side, key = lambda x: (x[0] - v.co).length)
        #        co_d = .5 * v.co + .5 * ele_max[0]
        #        mb_d = meta_data.elements.new(type = 'BALL')
        #        mb_d.radius = self.scale * self.d_radius
        #        mb_d.co = self.scale * co_d    
            
        
        #we use the vertex locations as locations of particles/metaballs
        for v in bme.verts:
                
            #VERY IMPORTANT!  GET THE PREPROCESSED COODINATE
            v_pre_p = bme_pp.verts[v.index]
            co = v_pre_p.co
            
            if not len(v.link_edges)>1: continue
            #This should guarantee good overlap of the disks, going past 1/2 way toward the furthest neighbor
            #by definition the neighbors disk has to go > 1/2 than it's furthest neighbor
            R = .8 * max([ed.calc_length() for ed in v_pre_p.link_edges])
        
            Z = v_pre_p.normal #get a smoothed normal, very important
            Z.normalize()
        
            size_x = self.scale * R
            size_y = self.scale * R
            
            #we pre-calculate a thickness for predictablility in generating the undercut blockout
            #and change the pre-offsetting (go see bme_pp)
            size_z = self.scale * .17   #.22 + self.radius - .05 - self.radius
        
            v_other = v.link_edges[0].other_vert(v)
            x_prime = v_other.co - v.co
            x_prime.normalize()
            Y = Z.cross(x_prime)
            X = Y.cross(Z)
    
            #rotation matrix from principal axes
            T = Matrix.Identity(3)  #make the columns of matrix U, V, W
            T[0][0], T[0][1], T[0][2]  = X[0] ,Y[0],  Z[0]
            T[1][0], T[1][1], T[1][2]  = X[1], Y[1],  Z[1]
            T[2][0] ,T[2][1], T[2][2]  = X[2], Y[2],  Z[2]

            Rotation_Matrix = T.to_4x4()
            quat = Rotation_Matrix.to_quaternion()
            
            base_plane_intersection = intersect_line_plane(co, co + 30 * local_axis_z, base_plane_co, fit_plane_no)
            
            height = (base_plane_intersection - co).length
            co_top = base_plane_intersection
        

            if v in perimeter_verts:
                N = min(math.ceil(height/.125), math.ceil(self.max_blockout/.125))  #limit the blockout depth
                if size_x < self.scale * .125 and size_y < self.scale * .125:
                        n_voids += 1
                for i in range(0,N):
                    n_elements += 1
                    
                    mb = meta_data.elements.new(type = 'ELLIPSOID')
                    mb.co = self.scale * (co - i * .125 * local_axis_z)  
                        
                    mb.size_x = max(size_x, self.scale*.125)
                    mb.size_y = max(size_y, self.scale*.125)
                    mb.size_z = size_z
                    mb.rotation = quat
                    
    
            if v in undercut_verts:
                N = min(math.ceil(height/.2), math.ceil(self.max_blockout/.2))  #limit the blockout depth
                for i in range(0,N):
                    
                    n_elements += 1
                    
                    mb = meta_data.elements.new(type = 'ELLIPSOID')
                    mb.co = self.scale * (co - i * .2 * local_axis_z)
                
                    mb.size_x = size_x
                    mb.size_y = size_y
                    mb.size_z = size_z
                    mb.rotation = quat
            
            
            if not (v in perimeter_verts or v in undercut_verts):
                
                n_elements += 2
                mb= meta_data.elements.new(type = 'ELLIPSOID')
                mb.co = self.scale * co 
            
                mb.size_x = size_x
                mb.size_y = size_y
                mb.size_z = self.scale * (.17 - .05)   #.17 - .02
                mb.rotation = quat
                
                #Add a flat base
                if self.angle < 25:
                    mb= meta_data.elements.new(type = 'BALL')
                    mb.co = self.scale * co_top
                    mb.radius = self.scale * .3
                 
        #Now do teh passive spacer part
        for v in bme.verts: 
            v.co -= .15 * v.normal
        
        #for v in bme2.verts:
        #    v.co -= .16 * v.normal
        
        bme.normal_update()
        #bme2.normal_update()
        
        
        for v in bme.verts[:]:# + bme2.verts[:]:
            if not len(v.link_edges): continue
            co = v.co
            R = .5 * max([ed.calc_length() for ed in v.link_edges])
            
            n_elements += 1
            Z = v.normal 
            Z.normalize()
            
            mb = meta_data.elements.new(type = 'ELLIPSOID')
            mb.co = self.scale * co
            mb.size_x = self.scale * R
            mb.size_y = self.scale * R
            mb.size_z = self.scale * (self.c_radius - .025 + .15)  #surface is pre negatively offset by .15
            
            v_other = v.link_edges[0].other_vert(v)
            x_prime = v_other.co - v.co
            x_prime.normalize()
            Y = Z.cross(x_prime)
            X = Y.cross(Z)
            
            #rotation matrix from principal axes
            T = Matrix.Identity(3)  #make the columns of matrix U, V, W
            T[0][0], T[0][1], T[0][2]  = X[0] ,Y[0],  Z[0]
            T[1][0], T[1][1], T[1][2]  = X[1], Y[1],  Z[1]
            T[2][0] ,T[2][1], T[2][2]  = X[2], Y[2],  Z[2]

            Rotation_Matrix = T.to_4x4()
                
            mb.rotation = Rotation_Matrix.to_quaternion()
            

        bme.free()
        bme_pp.free()
        
        print('%i voides were avoided by overthickening' % n_voids)
                       
        print('finished adding metaballs in %f' % (time.time() - interval_start))
        interval_start = time.time()
        print('added %i metaballs' % n_elements)
        R = model_mx.to_quaternion().to_matrix().to_4x4()
        L = Matrix.Translation(model_mx.to_translation())
        S = Matrix.Scale(.1, 4)  #we scale the metaball object up to compensate for the fact that the meta resolution is not in physical dimensions
           
        meta_obj.matrix_world =  L * R * S
        #meta_obj_d.matrix_world =  L * R * S
        
        print('transformed the meta ball object %f' % (time.time() - start))
        context.scene.update()
        total_meta_time = (time.time() - start)
        print('updated the scene %f' % total_meta_time )
        

        me = meta_obj.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        
        bme_final = bmesh.new()
        bme_final.from_mesh(me)

        bme_final.verts.ensure_lookup_table()
        bme_final.edges.ensure_lookup_table()
        bme_final.faces.ensure_lookup_table()
        
        #clean loose verts
        to_delete = []
        for v in bme_final.verts:
            if len(v.link_edges) < 2:
                to_delete.append(v)
                
        print('deleting %i loose verts' % len(to_delete))
        bmesh.ops.delete(bme_final, geom = to_delete, context = 1)  #TODO optimized with fast delete (bme.vets.remove(v))
        
        bme_final.verts.ensure_lookup_table()
        bme_final.edges.ensure_lookup_table()
        bme_final.faces.ensure_lookup_table()
        
        #delete edges without faces
        to_delete = []
        for ed in bme_final.edges:
            if len(ed.link_faces) == 0:
                for v in ed.verts:
                    if len(v.link_faces) == 0:
                        to_delete.append(v)

        to_delete = list(set(to_delete))
        bmesh.ops.delete(bme_final, geom = to_delete, context = 1) #TODO optimized with fast delete (bme.vets.remove(v))
        
                
        bme_final.verts.ensure_lookup_table()
        bme_final.edges.ensure_lookup_table()
        bme_final.faces.ensure_lookup_table()
        
        #we have done basic validity checks
        Lv = len(bme_final.verts)
        Lf = len(bme_final.faces)
        
        #by definition, the vert with a max coordinate in any reference
        #will be a vertex in the outer shell
        #we have also guaranteed that there are no crappy verts/edges which
        #might throw us off
        
        start = time.time()
        islands = bmesh_loose_parts(bme_final, selected_faces = None, max_iters = 5000)
        epsilon = .0001
        
        #do inner/outer ray casting to try and delete inner shell
        if len(islands) > 2:
            bvh = BVHTree.FromBMesh(bme_final)
            to_del = set()
            for isl in islands:
                if len(isl) < 100:
                    to_del.update(isl)
                    print('small island')
                #pick a location
                
                #offset epsilon in reverse  f.calc_center_bounds() - epsilon * f.normal
                #count the number of intersections...should be odd for interior
                n_faces = 0
                test_faces = []
                for f in isl:
                    test_faces += [f]
                    n_faces += 1
                    if n_faces >= 100: break
                
                free_faces = 0
                self_faces = 0
                other_faces = 0
                for f in test_faces:
                    v = f.calc_center_bounds() + epsilon * f.normal
                    loc, no, ind, d = bvh.ray_cast(v, f.normal)
                    if not loc:
                        free_faces += 1
                    else:
                        found = bme_final.faces[ind]
                        if found in isl:
                            self_faces += 1
                        else:
                            other_faces += 1
                
                if free_faces == 0:
                    to_del.update(isl)
                print('This island has %i free,  %i self, and %i other faces' % (free_faces, self_faces, other_faces))
                
        else:
            to_del = min(islands, key = len)
            
        del_vs = set()
        for f in to_del:
            del_vs.update([v for v in f.verts])  
        for v in del_vs:    
            bme_final.verts.remove(v)
                
        bme_final.to_mesh(me)
    
        if 'Refractory Model' in bpy.data.objects:
            new_ob = bpy.data.objects.get('Refractory Model')
            old_data = new_ob.data
            new_ob.data = me
            old_data.user_clear()
            bpy.data.meshes.remove(old_data)
        else:
            new_ob = bpy.data.objects.new('Refractory Model', me)
            context.scene.objects.link(new_ob)
        
        new_ob.matrix_world = L * R * S
        mat = bpy.data.materials.get("Refractory Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Refractory Material")
            mat.diffuse_color = Color((0.36, .8,.36))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        if len(new_ob.material_slots) == 0:
            new_ob.data.materials.append(mat)
        
        interval_start = time.time()
        if 'Smooth' not in new_ob.modifiers:
            mod = new_ob.modifiers.new('Smooth', type = 'SMOOTH')
            mod.factor = 1
            mod.iterations = 4
        
        else:
            mod = new_ob.modifiers.get('Smooth')
            
        context.scene.objects.active = new_ob
        new_ob.select = True
        bpy.ops.object.modifier_apply(modifier = 'Smooth')
        
        
        #apply the smoothing
        context.scene.objects.active = new_ob
        new_ob.select = True
        bpy.ops.object.modifier_apply(modifier = 'Smooth')
        
        
        
        print('Took %f seconds to smooth BMesh' % (time.time() - interval_start))
        interval_start = time.time()
        
                
        mx = new_ob.matrix_world
        imx = mx.inverted()
        bme = bmesh.new()
        bme.from_object(new_ob, context.scene)
        bme.verts.ensure_lookup_table()

        boundary_inds = set()
        #for ed in bme_check.edges:
        #    if len(ed.link_faces) == 1:
        #        for v in ed.verts:
        #            for f in v.link_faces:
        #                boundary_inds.add(f.index)
        
        #bme_check.free()

        print('Took %f seconds to initialize BMesh' % (time.time() - interval_start))
        interval_start = time.time()
            
        n_corrected = 0
        n_normal = 0
        n_loc = 0
        n_too_far = 0
        n_boundary = 0
        for v in bme.verts:
            #check the distance in trimmed model space
            co = model_imx * mx * v.co
            loc, no, ind, d = bvh.find_nearest(co)
            
            if not loc: continue
            
            if d < self.c_radius:  #compensation radius
                if ind in boundary_inds:
                    n_boundary += 1
                    continue
                n_corrected += 1
                R = co - loc
                
                R.normalize()
                    
                if R.dot(no) > 0:
                    delta = self.c_radius - d + .002
                    co += delta * R
                    n_loc += 1
                else:
                    co = loc + (self.c_radius + .002) * no
                    n_normal += 1
                    
                v.co = imx * model_mx * co
                v.select_set(True)
            
            elif d > self.c_radius and d < (self.c_radius + self.b_radius):
                if self.use_drillcomp:
                    continue
                co = loc + (self.c_radius + .0001) * no
                n_too_far += 1
                
            else:
                v.select_set(False)        
        print('corrected %i verts too close offset' % n_corrected)
        print('corrected %i verts using normal method' % n_normal)
        print('corrected %i verts using location method' % n_loc)
        print('corrected %i verts using too far away' % n_too_far)
        print('ignored %i verts clsoe to trim boundary' % n_boundary)
        

        #if 'Child Of' not in new_ob.constraints:
        #    Master = bpy.data.objects.get(splint.model)
        #    cons = new_ob.constraints.new('CHILD_OF')
        #    cons.target = Master
        #    cons.inverse_matrix = Master.matrix_world.inverted()
         
        context.scene.objects.unlink(meta_obj)
        bpy.data.objects.remove(meta_obj)
        bpy.data.metaballs.remove(meta_data)
        
        context.scene.objects.unlink(ob2)
        me = ob2.data
        bpy.data.objects.remove(ob2)
        bpy.data.meshes.remove(me)
        
        
        for ob in context.scene.objects:
            if "silhouette" in ob.name:
                ob.hide = False 
            else:
                ob.hide = True
        
        
        bme.to_mesh(new_ob.data)
        bme.free()
        
        global_total_finish = time.time() 
        
        
        print('TOTAL PROCESSING TIME %f' % (global_total_finish - global_total_start))  
        
        #Model.hide = False
        #new_ob.hide = False
        #splint.refractory_model = True
        #splint.passive_value = self.c_radius
        #splint.undercut_value = self.b_radius
        #splint.ops_string += 'Refractory Model:'
        #tracking.trackUsage("D3Splint:RemoveUndercuts", (str(self.b_radius)[0:4], str(self.b_radius)[0:4], str(total_meta_time)[0:4]), background = True)
        return {'FINISHED'}
     
def register():
    bpy.utils.register_class(D3SPLINT_OT_refractory_model)
    
    
def unregister():
    bpy.utils.unregister_class(D3SPLINT_OT_refractory_model)

    