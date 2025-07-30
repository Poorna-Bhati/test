import math

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Matrix, Vector, Color
import loops_tools
from mathutils.bvhtree import BVHTree


def bmesh_join_list(list_of_bmeshes, normal_update=False):
    """ takes as input a list of bm references and outputs a single merged bmesh 
    allows an additional 'normal_update=True' to force _normal_ calculations.
    """

    bm = bmesh.new()
    add_vert = bm.verts.new
    add_face = bm.faces.new
    add_edge = bm.edges.new

    for bm_to_add in list_of_bmeshes:
        offset = len(bm.verts)

        for v in bm_to_add.verts:
            add_vert(v.co)

        bm.verts.index_update()
        bm.verts.ensure_lookup_table()

        if bm_to_add.faces:
            for face in bm_to_add.faces:
                add_face(tuple(bm.verts[i.index+offset] for i in face.verts))
            bm.faces.index_update()

        if bm_to_add.edges:
            for edge in bm_to_add.edges:
                edge_seq = tuple(bm.verts[i.index+offset] for i in edge.verts)
                try:
                    add_edge(edge_seq)
                except ValueError:
                    # edge exists!
                    pass
            bm.edges.index_update()

    if normal_update:
        bm.normal_update()

    return bm


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
 
def bme_rip_vertex(bme, bmvert):
    
    fs = [f for f in bmvert.link_faces]
    
    for f in fs:
        vs = [v for v in f.verts]  #these come in order
        new_v = bme.verts.new(bmvert.co)
        
        #find the ripping vert
        ind = vs.index(bmvert)
        #replace it with the new vertex
        vs[ind] = new_v
        
        #create a new face
        new_f = bme.faces.new(vs)
        
    bmesh.ops.delete(bme, geom = [bmvert], context = 1)
    
    
def bme_linked_flat_faces(bme, start_face, angle, iter_max = 10000):
    '''
    args:
        bme - BMesh object
        start_face = BMFace
        angl - angle in degrees
    
    return:  list of BMFaces
    '''
    
    no = start_face.normal
    angl_rad = math.pi/180 * angle
    
    #intiiate the flat faces
    flat_faces = set([start_face])
    
    #how we detect flat neighbors
    def flat_neighbors(bmf):
        neighbors = set()
        for v in bmf.verts:
            neighbors.update([f for f in v.link_faces if f not in flat_faces and f != bmf])
            flat_neighbors = set([f for f in neighbors if f.normal.dot(no) > 0 and f.normal.angle(no) < angl_rad])
        return flat_neighbors
    
    
    new_faces = flat_neighbors(start_face)
    
    iters = 0
    while len(new_faces) and iters < iter_max:
        iters += 1
        flat_faces |= new_faces
        
        newer_faces = set()
        for f in new_faces:
            newer_faces |= flat_neighbors(f)
             
        new_faces = newer_faces
    
    return list(flat_faces)



def join_bmesh_map(source, target, src_trg_map = None, src_mx = None, trg_mx = None):
    '''
    
    '''
    
 
    L = len(target.verts)
    
    if not src_trg_map:
        src_trg_map = {-1:-1}
    l = len(src_trg_map)
    print('There are %i items in the vert map' % len(src_trg_map))
    if not src_mx:
        src_mx = Matrix.Identity(4)
    
    if not trg_mx:
        trg_mx = Matrix.Identity(4)
        i_trg_mx = Matrix.Identity(4)
    else:
        i_trg_mx = trg_mx.inverted()
        
        
    old_bmverts = [v for v in target.verts]  #this will store them in order
    new_bmverts = [] #these will be created in order
    
    source.verts.ensure_lookup_table()

    for v in source.verts:
        if v.index not in src_trg_map:
            new_ind = len(target.verts)
            new_bv = target.verts.new(i_trg_mx * src_mx * v.co)
            new_bmverts.append(new_bv)  #gross...append
            src_trg_map[v.index] = new_ind
            
        else:
            print('vert alread in the map %i' % v.index)
    
    lverts = old_bmverts + new_bmverts
    
    target.verts.index_update()
    target.verts.ensure_lookup_table()
    
    new_bmfaces = []
    for f in source.faces:
        v_inds = []
        for v in f.verts:
            new_ind = src_trg_map[v.index]
            v_inds.append(new_ind)
            
        if any([i > len(lverts)-1 for i in v_inds]):
            print('impending index error')
            print(len(lverts))
            print(v_inds)
            
        if target.faces.get(tuple(lverts[i] for i in v_inds)):
            print(v_inds)
            continue
        new_bmfaces += [target.faces.new(tuple(lverts[i] for i in v_inds))]
    
        target.faces.ensure_lookup_table()
    target.verts.ensure_lookup_table()

    new_L = len(target.verts)
    
    if src_trg_map:
        if new_L != L + len(source.verts) -l:
            print('seems some verts were left in that should not have been')
 
def join_bmesh(source, target, src_mx = None, trg_mx = None):

    src_trg_map = dict()
    L = len(target.verts)
    if not src_mx:
        src_mx = Matrix.Identity(4)
    
    if not trg_mx:
        trg_mx = Matrix.Identity(4)
        i_trg_mx = Matrix.Identity(4)
    else:
        i_trg_mx = trg_mx.inverted()
        
        
    new_bmverts = []
    source.verts.ensure_lookup_table()

    for v in source.verts:
        if v.index not in src_trg_map:
            new_ind = len(target.verts)
            new_bv = target.verts.new(i_trg_mx * src_mx * v.co)
            new_bmverts.append(new_bv)
            src_trg_map[v.index] = new_ind
    
    
    target.verts.index_update()
    target.verts.ensure_lookup_table()

    new_bmfaces = []
    for f in source.faces:
        v_inds = []
        for v in f.verts:
            new_ind = src_trg_map[v.index]
            v_inds.append(new_ind)
            
        new_bmfaces += [target.faces.new(tuple(target.verts[i] for i in v_inds))]
    
    target.faces.ensure_lookup_table()
    target.verts.ensure_lookup_table()
    target.verts.index_update()
    
   
    target.verts.index_update()        
    target.verts.ensure_lookup_table()
    target.faces.ensure_lookup_table()
    
    new_L = len(target.verts)
    

    if new_L != L + len(source.verts):
        print('seems some verts were left out')
            

def new_bmesh_from_bmelements(geom):
    
    out_bme = bmesh.new()
    out_bme.verts.ensure_lookup_table()
    out_bme.faces.ensure_lookup_table()
    
    faces = [ele for ele in geom if isinstance(ele, bmesh.types.BMFace)]
    verts = [ele for ele in geom if isinstance(ele, bmesh.types.BMVert)]
    
    vs = set(verts)
    for f in faces:
        vs.update(f.verts[:])
        
    src_trg_map = dict()
    new_bmverts = []
    for v in vs:
    
        new_ind = len(out_bme.verts)
        new_bv = out_bme.verts.new(v.co)
        new_bmverts.append(new_bv)
        src_trg_map[v.index] = new_ind
    
    out_bme.verts.ensure_lookup_table()
    out_bme.faces.ensure_lookup_table()
        
    new_bmfaces = []
    for f in faces:
        v_inds = []
        for v in f.verts:
            new_ind = src_trg_map[v.index]
            v_inds.append(new_ind)
            
        new_bmfaces += [out_bme.faces.new(tuple(out_bme.verts[i] for i in v_inds))]
        
    out_bme.faces.ensure_lookup_table()
    out_bme.verts.ensure_lookup_table()
    out_bme.verts.index_update()
    
   
    out_bme.verts.index_update()        
    out_bme.verts.ensure_lookup_table()
    out_bme.faces.ensure_lookup_table()
    
    return out_bme       
def join_objects(obs, name = ''):
    '''
    uses BMesh to join objects.  Advantage is that it is context
    agnostic, so no editmoe or bpy.ops has to be used.
    
    Args:
        obs - list of Blender objects
    
    Returns:
        new object with name specified.  Otherwise '_joined' will
        be added to the name of the first object in the list
    '''
    target_bme = bmesh.new()
    target_bme.verts.ensure_lookup_table()
    target_bme.faces.ensure_lookup_table()
    trg_mx = obs[0].matrix_world
    
    if name == '':
        name = obs[0].name + '_joined'
    
    for ob in obs:
        src_mx = ob.matrix_world

        if ob.data.is_editmode:
            src_bme = bmesh.from_editmesh(ob.data)
        else:
            src_bme = bmesh.new()
            if ob.type == 'MESH':
                if len(ob.modifiers):
                    src_bme.from_object(ob, bpy.context.scene)
                else:
                    src_bme.from_mesh(ob.data)
            else:
                me = ob.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
                src_bme.from_mesh(me)
                bpy.data.meshes.remove(me)
        join_bmesh(src_bme, target_bme, src_mx, trg_mx)

        src_bme.free()
    
    new_me = bpy.data.meshes.new(name)    
    new_ob = bpy.data.objects.new(name, new_me)
    new_ob.matrix_world = trg_mx
    target_bme.to_mesh(new_me)
    target_bme.free()
    return new_ob
    

def bound_box_bmverts(bmvs):
    bounds = []
    for i in range(0,3):
        components = [v.co[i] for v in bmvs]
        low = min(components)
        high = max(components)
        bounds.append((low,high))

    return bounds

def bbox_center(bounds):
    
    x = 0.5 * (bounds[0][0] + bounds[0][1])
    y = 0.5 * (bounds[1][0] + bounds[1][1])
    z = 0.5 * (bounds[2][0] + bounds[2][1])
    
    return Vector((x,y,z))