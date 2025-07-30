import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh

from mathutils import Vector, Color, Matrix
from mathutils.bvhtree import BVHTree

import random
import math
import time

from .geometry_utils import loops_tools



def silouette_brute_force(context, ob, view, world = True, smooth = True, apply = True, debug = False):
    '''
    args:
      ob - mesh object
      view - Mathutils Vector
      apply - apply all modifiers to the silhouette
      
    return:
       new mesh of type Mesh (not BMesh)
    '''
    if debug:
        start = time.time()
        
    #careful, this can get expensive with multires
    me = ob.to_mesh(context.scene, True, 'RENDER')    
    bme = bmesh.new()
    bme.from_mesh(me)
    bme.normal_update()
    
    #keep track of the world matrix
    mx = ob.matrix_world
    
    if world:
        #meaning the vector is in world coords
        #we need to take it back into local
        i_mx = mx.inverted()
        view = i_mx.to_quaternion() * view
    
    if debug:
        face_time = time.time()
        print("took %f to initialze the bmesh" % (face_time - start))
        
    face_directions = [[0]] * len(bme.faces)
    
    for f in bme.faces:
        if debug > 1:
            print(f.normal)
        
        face_directions[f.index] = f.normal.dot(view)
    
    
    if debug:
        edge_time = time.time()
        print("%f seconds to test the faces" % (edge_time - face_time))
        
        if debug > 2:
            print(face_directions)
            
    delete_edges = []
    keep_verts = set()
    
    for ed in bme.edges:
        if len(ed.link_faces) == 2:
            silhouette = face_directions[ed.link_faces[0].index] * face_directions[ed.link_faces[1].index]
            if silhouette < 0:
                keep_verts.add(ed.verts[0])
                keep_verts.add(ed.verts[1])
            else:
                delete_edges.append(ed)
    if debug > 1:
        print("%i edges to be delted" % len(delete_edges))
        print("%i verts to be deleted" % (len(bme.verts) - len(keep_verts)))
    if debug:
        delete_time = time.time()
        print("%f seconds to test the edges" % (delete_time - edge_time))
        
    delete_verts = set(bme.verts) - keep_verts
    delete_verts = list(delete_verts)
    
    
    #https://svn.blender.org/svnroot/bf-blender/trunk/blender/source/blender/bmesh/intern/bmesh_operator_api.h
    bmesh.ops.delete(bme, geom = bme.faces, context = 3)
    bmesh.ops.delete(bme, geom = delete_verts, context = 1)
    #bmesh.ops.delete(bme, geom = delete_edges, context = 2)  #presuming the delte enum is 0 = verts, 1 = edges, 2 = faces?  who knows.
    
    
    if ob.name + '_silhouette' in bpy.data.meshes:
        new_me = bpy.data.meshes.get(ob.name + '_silhouette')
        obj = bpy.data.objects.get(ob.name + '_silhouette')
        obj.hide = False
        bme.to_mesh(new_me)
        bme.free()
        new_me.update()
    else:    
        new_me = bpy.data.meshes.new(ob.name + '_silhouette')
    
        bme.to_mesh(new_me)
        bme.free()
        new_me.update()
        
        obj = bpy.data.objects.new(new_me.name, new_me)
        context.scene.objects.link(obj)
    
        obj.select = True
        context.scene.objects.active = obj
        obj.hide = False
        if world:
            obj.matrix_world = mx
        
        if smooth:
            mod = obj.modifiers.new('Smooth', 'SMOOTH')
            mod.iterations = 10
    
            mod2 = obj.modifiers.new('Wrap','SHRINKWRAP')
            mod2.target = ob
            mod2.use_keep_above_surface = True
            mod2.offset = .02
            
            bme = bmesh.new()
            bme.from_object(obj, context.scene)
            obj.modifiers.clear()
            
            bme.to_mesh(obj.data)
            obj.data.update()
            bme.free()
    if debug:
        print("finished in %f seconds" % (time.time() - start))
    
    return



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
    
    start = time.time()    
    
    me = ob.to_mesh(context.scene, True, 'RENDER')    
    bme = bmesh.new()
    bme.from_mesh(me)
    bme.normal_update()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    #keep track of the world matrix
    mx = ob.matrix_world
    if world:
        #meaning the vector is in world coords
        #we need to take it back into local
        i_mx = mx.inverted()
        view = i_mx.to_quaternion() * view
     
    #find the lowest part of the mesh to add a base plane to.
    lowest_vert = min(bme.verts[:], key = lambda x: x.co.dot(view))
    lowest_point = lowest_vert.co 
     
    #initialize some book keeping       
    face_directions = [[0]] * len(bme.faces)
    up_faces = set()
    overhang_faces = set()  #all faces pointing away from view
    
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
    print('analyzed faces in %f seconds' % (time.time() - start))
    
    start = time.time()
    
    hoc_edges = set()
    non_man_edges = set()
    for ed in bme.edges:
        if len(ed.link_faces) == 1:
            non_man_edges.add(ed)
            continue
        if ed.link_faces[0] in up_faces and ed.link_faces[1] in overhang_faces:
            hoc_edges.add(ed)
            continue
        
        if ed.link_faces[1] in up_faces and ed.link_faces[0] in overhang_faces:
            hoc_edges.add(ed)
            continue
            
    ret = bmesh.ops.extrude_edge_only(bme, edges = list(hoc_edges | non_man_edges))
    
    new_fs = [ele for ele in ret['geom'] if isinstance(ele, bmesh.types.BMFace)]                
    new_vs = [ele for ele in ret['geom'] if isinstance(ele, bmesh.types.BMVert)]
    
    #TODO, ray cast down to base plane, yes
    for v in new_vs:
        delta = lowest_point - v.co
        v.co = v.co + delta.dot(view) * view
       
    new_me = bpy.data.meshes.new(ob.name + '_blockout')
    obj = bpy.data.objects.new(new_me.name, new_me)
    bme.to_mesh(obj.data)
    bme.free()
    return obj