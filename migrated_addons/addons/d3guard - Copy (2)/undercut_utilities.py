import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import loops_tools
from mathutils import Vector, Color, Matrix
from mathutils.bvhtree import BVHTree

import random
import math
from bmesh_fns import join_bmesh_map


def remove_undercuts(context, ob, view, world = True, smooth = True, res = .5, epsilon = .000001):
    '''
    args:
      ob - mesh object
      view - Mathutils Vector
      
    return:
       Bmesh with Undercuts Removed?
       
    best to make sure normals are consistent beforehand
    best for manifold meshes, however non-man works
    noisy meshes can be compensated for with island threhold
    '''
    
        
    
    me = ob.to_mesh(context.scene, True, 'RENDER')    
    bme = bmesh.new()
    bme.from_mesh(me)
    bme.normal_update()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    bvh = BVHTree.FromBMesh(bme)
    
    #keep track of the world matrix
    mx = ob.matrix_world
    
    if world:
        #meaning the vector is in world coords
        #we need to take it back into local
        i_mx = mx.inverted()
        view = i_mx.to_quaternion() * view
            
    face_directions = [[0]] * len(bme.faces)
    
    up_faces = set()
    overhang_faces = set()  #all faces pointing away from view
    
    #find the lowest part of the mesh to add a base plane to.
    lowest_vert = min(bme.verts[:], key = lambda x: x.co.dot(view))
    lowest_point = lowest_vert.co
    
    base_plane_center = lowest_point.dot(view) * view + .1 * view
    Z = view
    X = Vector((random.random(), random.random(), random.random()))
    X = X - X.dot(Z) * Z
    X.normalize()
    Y = Z.cross(X)
    
    #rotation matrix from principal axes
    R = Matrix.Identity(3)  #make the columns of matrix U, V, W
    R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
    R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
    R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
    R = R.to_4x4()
    T = Matrix.Translation(base_plane_center)
    
    grid_bme = bmesh.new()
    diag = Vector(ob.dimensions).length
    grid_cells = math.floor(diag/res)
    bmesh.ops.create_grid(grid_bme, x_segments = grid_cells, y_segments = grid_cells, size = diag/2, matrix = T*R)

    in_grid = set()
    out_grid = set()
    for v in grid_bme.verts:
        loc, no, face_ind, d = bvh.ray_cast(v.co, view)
        if loc:
            in_grid.add(v)
    
        else:
            out_grid.add(v)
    
    del_faces = set()
    #this will triangulate the diagonals
    for f in grid_bme.faces:
        if len(f.verts) != 4: continue
        out_verts = [v for v in f.verts if v in out_grid]
        #if len(out_verts) == 3:
            #grid_bme.faces.new(out_verts)
        if len(out_verts) == 4:
            del_faces.add(f)
    
    
    del_vs = [v for v in out_verts if all([f in del_faces for f in v.link_faces])]
    del_eds = [ed for ed in grid_bme.edges if all([f in del_faces for f in ed.link_faces])]
        
    for f in del_faces:
        grid_bme.faces.remove(f)
    for ed in del_eds:
        grid_bme.edges.remove(ed)
    for v in del_vs:
        grid_bme.verts.remove(v)    
              
    grid_bme.verts.ensure_lookup_table()
    grid_bme.edges.ensure_lookup_table()
    grid_bme.faces.ensure_lookup_table()
    
    for f in grid_bme.faces:
        f.normal_flip()
        
    gdict = bmesh.ops.extrude_face_region(grid_bme, geom = grid_bme.faces[:])
    move_vs = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)]
    for v in move_vs:
        v.co += -view
    
    base_me = bpy.data.meshes.new('Grid Base')
    base_ob = bpy.data.objects.new('Grid Base', base_me)
    context.scene.objects.link(base_ob)
    base_ob.matrix_world = ob.matrix_world
    grid_bme.to_mesh(base_me)
    grid_bme.free()
    
    
    #precalc all the face directions and store in dict
    for f in bme.faces:
        direction = f.normal.dot(view)
        
        if direction <= -epsilon:
            overhang_faces.add(f)
        else:
            up_faces.add(f)
            
        face_directions[f.index] = direction
    
    print('there are %i up_faces' % len(up_faces))
    print('there are %i down_faces' % len(overhang_faces))
    
    
    #for f in bme.faces:
    #    if f in overhangs:
    #        f.select_set(True)
    #    else:
    #        f.select_set(False)
            
    overhang_islands = [] #islands bigger than a certain threshold (by surface area?
    upfacing_islands = []
    def face_neighbors_up(bmface):
        neighbors = []
        for ed in bmface.edges:
            neighbors += [f for f in ed.link_faces if f != bmface and f in up_faces]
            
        return neighbors
    
    #remove small islands from up_faces and add to overhangs
    max_iters = len(up_faces)
    iters_0 = 0
    islands_removed = 0
    
    up_faces_copy = up_faces.copy()
    while len(up_faces_copy) and iters_0 < max_iters:
        iters_0 += 1
        max_iters_1 = len(up_faces)
        seed = up_faces_copy.pop()
        new_faces = set(face_neighbors_up(seed))
        up_faces_copy -= new_faces
        
        island = set([seed])
        island |= new_faces
        
        iters_1 = 0
        while iters_1 < max_iters_1 and new_faces:
            iters_1 += 1
            new_candidates = set()
            for f in new_faces:
                new_candidates.update(face_neighbors_up(f))
            
            new_faces = new_candidates - island
        
            if new_faces:
                island |= new_faces    
                up_faces_copy -= new_faces
        if len(island) < 75: #small patch surrounded by overhang, add to overhang area
            islands_removed += 1
            overhang_faces |= island
        else:
            upfacing_islands += [island]
            
    print('%i upfacing islands removed' % islands_removed)
    print('there are now %i down faces' % len(overhang_faces))
    
    def face_neighbors_down(bmface):
        neighbors = []
        for ed in bmface.edges:
            neighbors += [f for f in ed.link_faces if f != bmface and f in overhang_faces]
            
        return neighbors
    overhang_faces_copy = overhang_faces.copy()
    
    while len(overhang_faces_copy):
        seed = overhang_faces_copy.pop()
        new_faces = set(face_neighbors_down(seed))
        island = set([seed])
        island |= new_faces
        overhang_faces_copy -= new_faces
        iters = 0
        while iters < 100000 and new_faces:
            iters += 1
            new_candidates = set()
            for f in new_faces:
                new_candidates.update(face_neighbors_down(f))
            
            new_faces = new_candidates - island
        
            if new_faces:
                island |= new_faces    
                overhang_faces_copy -= new_faces
        if len(island) > 75: #TODO, calc overhang factor.  Surface area dotted with direction
            overhang_islands += [island]
    
    for f in bme.faces:
        f.select_set(False)   
    for ed in bme.edges:
        ed.select_set(False)
    for v in bme.verts:
        v.select_set(False)
            
    island_loops = []
    island_verts = []
    del_faces = set()
    for isl in overhang_islands:
        loop_eds = []
        loop_verts = []
        del_faces |= isl
        for f in isl:
            for ed in f.edges:
                if len(ed.link_faces) == 1:
                    loop_eds += [ed]
                    loop_verts += [ed.verts[0], ed.verts[1]]
                elif (ed.link_faces[0] in isl) and (ed.link_faces[1] not in isl):
                    loop_eds += [ed]
                    loop_verts += [ed.verts[0], ed.verts[1]]
                elif (ed.link_faces[1] in isl) and (ed.link_faces[0] not in isl):
                    loop_eds += [ed]
                    loop_verts += [ed.verts[0], ed.verts[1]]
                    
            #f.select_set(True) 
        island_verts += [list(set(loop_verts))]
        island_loops += [loop_eds]
    
    bme.faces.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    
    loop_edges = []
    for ed_loop in island_loops:
        loop_edges += ed_loop
        for ed in ed_loop:
            ed.select_set(True)
    
    loops_tools.relax_loops_util(bme, loop_edges, 5)
    
    for ed in bme.edges:
        ed.select_set(False)
        
    exclude_vs = set()
    for vs in island_verts:
        exclude_vs.update(vs)
    
    smooth_verts = []    
    for v in exclude_vs:
        smooth_verts += [ed.other_vert(v) for ed in v.link_edges if ed.other_vert(v) not in exclude_vs]
            
    ret = bmesh.ops.extrude_edge_only(bme, edges = loop_edges)
    
    
    new_fs = [ele for ele in ret['geom'] if isinstance(ele, bmesh.types.BMFace)]                
    new_vs = [ele for ele in ret['geom'] if isinstance(ele, bmesh.types.BMVert)]
    
    #TODO, ray cast down to base plane, yes
    for v in new_vs:
        
        delta = lowest_point - v.co
        v.co = v.co + delta.dot(view) * view
        #v.co -= 10*view
        #loc, no, face_ind, d = bvh.ray_cast(v.co - .01 * view, -view)
        #if loc:
        #    v.co = loc
        #else:
        #    #put the vert on the base plane
        #    delta = lowest_point - v.co
        #    v.co = v.co - delta.dot(view) * view
            
    for f in new_fs:
        f.select_set(True)
        
    bmesh.ops.delete(bme, geom = list(del_faces), context = 3)
    
    del_verts = []
    for v in bme.verts:
        if all([f in del_faces for f in v.link_faces]):
            del_verts += [v]        
    bmesh.ops.delete(bme, geom = del_verts, context = 1)
    
    
    del_edges = []
    for ed in bme.edges:
        if len(ed.link_faces) == 0:
            del_edges += [ed]
    print('deleting %i edges' % len(del_edges))
    bmesh.ops.delete(bme, geom = del_edges, context = 4) 
    bmesh.ops.recalc_face_normals(bme, faces = new_fs)
    
    bme.normal_update()
    
    new_me = bpy.data.meshes.new(ob.name + '_blockout')
    
    obj = bpy.data.objects.new(new_me.name, new_me)
    context.scene.objects.link(obj)
    
    obj.select = True
    context.scene.objects.active = obj
    
    
    
    bme.to_mesh(obj.data)
    # Get material
    mat = bpy.data.materials.get("Model Material")
    if mat is None:
        # create material
        print('creating model material')
        mat = bpy.data.materials.new(name="Model Material")
        #mat.diffuse_color = Color((0.8, .8, .8))
    
    # Assign it to object
    obj.data.materials.append(mat)
    print('Model material added')
    
    mat2 = bpy.data.materials.get("Undercut Material")
    if mat2 is None:
        # create material
        mat2 = bpy.data.materials.new(name="Undercut Material")
        mat2.diffuse_color = Color((0.8, .2, .2))
    

    obj.data.materials.append(mat2)
    mat_ind = obj.data.materials.find("Undercut Material")
    print('Undercut material is %i' % mat_ind)
    
    for f in new_faces:
        obj.data.polygons[f.index].material_index = mat_ind
            
    if world:
        obj.matrix_world = mx

    bme.free()
    del bvh
        
    return