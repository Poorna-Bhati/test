'''
Created on Sep 5, 2017

@author: Patrick
'''
#common cache for bmesh and BVH
from mathutils import Vector

from subtrees.metaballs.vdb_remesh import read_bmesh, convert_vdb

mesh_cache = {}


def object_validation(ob):
    me = ob.data
    # get object data to act as a hash
    counts = (len(me.vertices), len(me.edges), len(me.polygons), len(ob.modifiers))
    bbox   = (tuple(min(v.co for v in me.vertices)), tuple(max(v.co for v in me.vertices)))
    vsum   = tuple(sum((v.co for v in me.vertices), Vector((0,0,0))))
    return (ob.name, counts, bbox, vsum)

def is_max_object_valid(ob):
    if 'max valid' not in mesh_cache: return False
    return mesh_cache['max valid'] == object_validation(ob)

def is_mand_object_valid(ob):
    if 'mand valid' not in mesh_cache: return False
    return mesh_cache['mand valid'] == object_validation(ob)


def write_max_mesh_cache(max_ob, max_bme, max_bvh):
    print('writing mesh cache')
    mesh_cache['max valid'] = object_validation(max_ob)
    mesh_cache['max bme'] = max_bme
    mesh_cache['max bvh'] = max_bvh
    
    
def write_mand_mesh_cache(mand_ob, mand_bme, mand_bvh):
    print('writing mesh cache')
    mesh_cache['mand valid'] = object_validation(mand_ob)
    mesh_cache['mand bme'] = mand_bme
    mesh_cache['mand bvh'] = mand_bvh
    
     
def write_shell_cache(bme_shell):
    if 'splint_shell' in mesh_cache and mesh_cache['splint_shell']:
        bme_old = mesh_cache['splint_shell']
        bme_old.free()
        del bme_old
    
    mesh_cache['splint_shell'] = bme_shell
     
def write_min_cache(bme_min):   
    if 'splint_shell' in mesh_cache and mesh_cache['splint_shell']:
        bme_old = mesh_cache['splint_shell']
        bme_old.free()
        del bme_old
    
    mesh_cache['min_shell'] = bme_min 

    if 'vdb_shell' in mesh_cache and mesh_cache['vdb_shell']:
        vdb_old = mesh_cache['vdb_shell']
        del vdb_old
       
    verts, tris, quads = read_bmesh(bme_min)
    vdb_min = convert_vdb(verts, tris, quads, .25)
    mesh_cache['vdb_min'] = vdb_min
    
            
def clear_mand_mesh_cache():
    if 'mand valid' in mesh_cache and mesh_cache['mand valid']:
        del mesh_cache['mand valid']
    if 'mand bme' in mesh_cache and mesh_cache['mand bme']:
        bme_old = mesh_cache['mand bme']
        bme_old.free()
        del mesh_cache['mand bme']
        
    if 'mand bvh' in mesh_cache and mesh_cache['mand bvh']:
        bvh_old = mesh_cache['mand bvh']
        del bvh_old
        
def clear_max_mesh_cache():
    print('clearing mesh cache')
    
    #mesh_cache['max valid'] = object_validation(max_ob)
    #mesh_cache['max bme'] = max_bme
    #mesh_cache['max bvh'] = max_bvh
    
    #mesh_cache['mand valid'] = object_validation(mand_ob)
    #mesh_cache['mand bme'] = mand_bme
    #mesh_cache['mand bvh'] = mand_bvh
    
    
    if 'max valid' in mesh_cache and mesh_cache['max valid']:
        del mesh_cache['max valid']
    
    
        
        
    if 'max bme' in mesh_cache and mesh_cache['max bme']:
        bme_old = mesh_cache['max bme']
        bme_old.free()
        del mesh_cache['max bme']

    
        
    
    if 'max bvh' in mesh_cache and mesh_cache['max bvh']:
        bvh_old = mesh_cache['max bvh']
        del bvh_old
    
    #TODO
        
    if 'vdb_shell' in mesh_cache and mesh_cache['vdb_shell']:
        vdb_old = mesh_cache['vdb_shell']
        del vdb_old
        
    if 'splint_shell' in mesh_cache and mesh_cache['splint_shell']:
        bme_old = mesh_cache['splint_shell']
        bme_old.free()
        del bme_old
        
    if 'vdb_min' in mesh_cache and mesh_cache['vdb_min']:
        vdb_old = mesh_cache['vdb_min']
        del vdb_old
        