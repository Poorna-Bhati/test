'''
Created on Sep 9, 2019

@author: Patrick

https://blenderartists.org/t/efficient-copying-of-vertex-coords-to-and-from-numpy-arrays/661467/8
https://stackoverflow.com/questions/45604688/apply-function-on-each-row-row-wise-of-a-numpy-array
https://blog.michelanders.nl/2016/02/copying-vertices-to-numpy-arrays-in_4.html


'''

import random
import math
import time

import numpy as np

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import loops_tools
from mathutils import Vector, Color, Matrix
from mathutils.bvhtree import BVHTree

import tracking
from subtrees.bmesh_utils.bmesh_utilities_common import bmesh_join_list
from subtrees.geometry_utils.loops_tools import relax_loops_util
from subtrees.geometry_utils.bound_box_utils import get_bbox_center
from subtrees.addon_common.common.utils import get_settings
from subtrees.geometry_utils.transformations import random_axes_from_normal, r_matrix_from_principal_axes
from subtrees.metaballs.vdb_tools import remesh_bme


#ambi's examples from links above
def read_verts(self, mesh):
    mverts_co = np.zeros((len(mesh.vertices)*3), dtype=np.float)
    mesh.vertices.foreach_get("co", mverts_co)
    return np.reshape(mverts_co, (len(mesh.vertices), 3))      

def read_edges(self, mesh):
    fastedges = np.zeros((len(mesh.edges)*2), dtype=np.int) # [0.0, 0.0] * len(mesh.edges)
    mesh.edges.foreach_get("vertices", fastedges)
    return np.reshape(fastedges, (len(mesh.edges), 2))

def read_norms(self, mesh):
    mverts_no = np.zeros((len(mesh.vertices)*3), dtype=np.float)
    mesh.vertices.foreach_get("normal", mverts_no)
    return np.reshape(mverts_no, (len(mesh.vertices), 3))

#how to dot a single vector to evey element of v
def remove_undercuts_fast(context, ob, view, world = True, 
                     smooth = True,
                     offset = 0.00, use_offset = False,
                     undercut = 0.00, use_undercut = False,
                     res = .25, epsilon = .000001):
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
    
    interval = time.time()
    
    me_offset = ob.to_mesh(context.scene, True, 'RENDER')
    me_offset.calc_normals()
    me_undercut = me_offset.copy()
    
    #keep track of the world matrix
    mx = ob.matrix_world
    if world:
        #meaning the vector is in world coords#we need to take it back into local
        i_mx = mx.inverted()
        view = i_mx.to_quaternion() * view
    
    
    
    np_view = np.array(view)
    
    #get the vertex locations
    vlen = len(me_offset.vertices)
    flen = len(me_offset.polygons)
    
    vco = np.empty(vlen * 3, 'f')
    me_offset.vertices.foreach_get('co', vco)
    vco_vec = np.reshape(vco, (vlen, 3))
    
    #get the vertex normals
    vno = np.empty(vlen * 3, 'f')
    me_offset.vertices.foreach_get('normal', vno)
    vno_vec = np.reshape(vno, (vlen, 3))
    
    
    print([v.normal for v in me_offset.vertices[0:4]])
    print(vno_vec[0:4])
    
    #get the face normals
    f_nors = np.empty(flen * 3, 'f')
    me_offset.polygons.foreach_get("normal", f_nors)
    f_nors_vec = np.reshape(f_nors, (flen, 3))
    
    print('derived numpy datastructures in %f seconds' % (time.time() - interval))
    interval = time.time()

    #calculate the numpy bounding box
    minx, miny, minz = np.min(vco_vec, axis = 0)
    maxx, maxy, maxz = np.max(vco_vec, axis = 0)
    
    numpy_bbox_center = .5 * Vector((minx + maxx, miny +  maxy, minz + maxz))
    print('numpy bbox center')
    print(numpy_bbox_center)
    
    #calculate the new positions
    offset_co = np.add(vco_vec, vno_vec * offset)
    undercut_co = np.add(vco_vec,  vno_vec *  (offset - undercut))
    
    #push the offsets back into the mesh
    me_offset.vertices.foreach_set("co", offset_co.flatten())
    me_undercut.vertices.foreach_set("co", undercut_co.flatten())
    
    print('did numpy offsets in %f seconds' % (time.time() - interval))
    interval = time.time()
    
        
    co_dots = np.dot(vco_vec, np_view)
    result = np.where(co_dots == np.amin(co_dots))
    lowest_point = vco_vec[result[0]]
    print(lowest_point)
    print('found lowest point in %f seconds' % (time.time() - interval))
    interval = time.time()
    
    bme = bmesh.new()
    bme.from_mesh(me_undercut)
    bme.normal_update()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
        
    bme_offset = bmesh.new()
    bme_offset.from_mesh(me_offset)
    bme_offset.normal_update()
    bme_offset.verts.ensure_lookup_table()
    bme_offset.edges.ensure_lookup_table()
    bme_offset.faces.ensure_lookup_table()
    
    
    print('created bmesh in %f sconds' % (time.time() - interval))
    interval = time.time()
    bvh = BVHTree.FromBMesh(bme)
    
    print("Create the BVH in %f seconds" % (time.time() - interval))
    interval = time.time()
    
    #find the lowest part of the mesh to add a base plane to.
    lowest_vert = min(bme.verts[:], key = lambda x: x.co.dot(view))
    lowest_point = lowest_vert.co
    print(lowest_point)
    print("Found the lowest point python in %f seconds" % (time.time() - interval))
    interval = time.time()
    
    #center point and flat    
    box_center = get_bbox_center(ob, world = False)
    base_plane_center = box_center + (lowest_point - box_center).dot(view) * view + 1.1 * view
    X, Y, Z = random_axes_from_normal(view)
    print("Found the bbox and base plane in %f seconds" % (time.time() - interval))
    print(box_center)
    interval = time.time()
    
    R = r_matrix_from_principal_axes(X, Y, Z)
    R = R.to_4x4()    
    T = Matrix.Translation(base_plane_center)
    
    grid_me = bpy.data.meshes.new('base_grid')
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
    
    for f in grid_bme.faces:  #must be faster way to do this
        f.normal_flip()
        
    gdict = bmesh.ops.extrude_face_region(grid_bme, geom = grid_bme.faces[:])
    move_vs = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)]
    for v in move_vs:
        v.co += -view
    
    grid_bme.to_mesh(grid_me)
    grid_me.update()
    
    
    print("created the base grid in %f seconds" % (time.time() - interval))
    interval = time.time()
    
    #extend the base if needed, and record these before we do any other stuff
    non_man_eds = [ed for ed in bme.edges if len(ed.link_faces) == 1]
    if len(non_man_eds):
        gdict = bmesh.ops.extrude_edge_only(bme, edges = non_man_eds)
        bme.edges.ensure_lookup_table()
        new_edges = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMEdge)]
        new_verts = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)]
        for v in new_verts: 
            co_flat = v.co +  (base_plane_center - v.co).dot(view) * view    
            v.co = co_flat
        bme.verts.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
     
     
    print("handled nonmanifold open edge in %f seconds" % (time.time() - interval))
    interval = time.time()
       
    #face_directions = [[0]] * len(bme.faces)
    #precalc all the face directions and store in dict
    #for f in bme.faces:
    #    direction = f.normal.dot(view)
        
    #    if direction <= -epsilon:
    #        overhang_faces.add(f)
    #    else:
    #        up_faces.add(f)
    #        
    #    face_directions[f.index] = direction
    
    #print("sorted undercut faces %f seconds" % (time.time() - interval))
    #interval = time.time()
    #gdict = bmesh.ops.extrude_face_region(bme, geom = list(overhang_faces))
    
    view_dots = np.dot(f_nors_vec, np_view)
    undercut_inds = np.where(view_dots <= -epsilon )[0]
    undercut_faces = [bme.faces[i] for i in undercut_inds]
    
    print('found undercuts and sliced in %f seconds' % (time.time() - interval))
    interval = time.time()
    
    gdict = bmesh.ops.extrude_face_region(bme, geom = undercut_faces)
    
    print("extruded with bmesh ops in  %f seconds" % (time.time() - interval))
    interval = time.time()
    
    
    new_vs = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)]
    new_fs =  [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMFace)]
    #TODO, ray cast down to base plane, yes
    for v in new_vs:
        delta = lowest_point - v.co
        v.co = v.co + delta.dot(view) * view
    
    print("moved them downward with for loop in %f seconds" % (time.time() - interval))
    interval = time.time()
    
    
    for f in new_fs:
        f.select_set(True)
    
    bme.normal_update()
    
    new_me = bpy.data.meshes.new(ob.name + '_blockout')
    
    obj = bpy.data.objects.new(new_me.name, new_me)
    context.scene.objects.link(obj)
    
    obj.select = True
    context.scene.objects.active = obj
  
    if use_offset or use_undercut:
        #joined_bme = bmesh_join_list([grid_bme, bme, bme_offset])
        bme.from_mesh(me_offset)
        bme.from_mesh(grid_me)
        #bme_offset.free()
        
        
    else:
        #joined_bme = bmesh_join_list([grid_bme, bme])
        bme.from_mesh(grid_me)
    
    bme.normal_update()
        
    #bme.to_mesh(obj.data)
    print('joined in %f seconds' % (time.time() - interval))
    interval = time.time()
    
    bme_remesh = remesh_bme(bme, 
              isovalue = 0.0, 
              adaptivity = 0.0, 
              only_quads = False, 
              voxel_size = .2,
              filter_iterations = 0,
              filter_width = 4,
              filter_sigma = 1.0,
              grid = None,
              write_method = 'FAST')
    
    
    print('remesh in %f seconds' % (time.time() - interval))
    interval = time.time()
    
    bme_remesh.to_mesh(obj.data)
            
    if world:
        obj.matrix_world = mx

    
    #test code
    #new_me = bpy.data.meshes.new(ob.name + '_grid')
    #new_obj = bpy.data.objects.new(new_me.name, new_me)
    #context.scene.objects.link(new_obj)
    #grid_bme.to_mesh(new_me)
    
    bme.free()
    grid_bme.free()
    #joined_bme.free()
    bme_remesh.free()
    del bvh
        
    return obj