import time
import math

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
import odcutils
from bmesh_fns import bmesh_loose_parts

#arguments from bg operator
#radius
#resoultion

#objects needed from blender
#Trimmed Model
#append_from("Object", 'Trimmed_Model')  #only use if use_blend_file = False
ob = bpy.data.objects.get('Shell Patch')

#fit data from inputs to outputs with metaball
    #r_final = .901 * r_input - 0.0219
    #rinput = 1/.901 * (r_final + .0219)
        
        
R_prime = 1/.901 * (radius + .0219)

bme = bmesh.new()
bme.from_object(ob, bpy.context.scene)
bme.verts.ensure_lookup_table()
bme.edges.ensure_lookup_table()
mx = ob.matrix_world

meta_data = bpy.data.metaballs.new('Splint Shell')
meta_obj = bpy.data.objects.new('Meta Splint Shell', meta_data)
meta_data.resolution = resolution
meta_data.render_resolution = resolution
bpy.context.scene.objects.link(meta_obj)

perimeter_edges = [ed for ed in bme.edges if len(ed.link_faces) == 1]
perim_verts = set()
for ed in perimeter_edges:
    perim_verts.update([ed.verts[0], ed.verts[1]])
    
perim_verts = list(perim_verts)
stroke = [v.co for v in perim_verts]
print('there are %i non man verts' % len(stroke))                                          
kd = KDTree(len(stroke))
for i in range(0, len(stroke)-1):
    kd.insert(stroke[i], i)
kd.balance()
perim_set = set(perim_verts)
for v in bme.verts:
    if v in perim_set: 
        continue
    
    loc, ind, r = kd.find(v.co)
    
    if r and r < .8 * R_prime:
        
        mb = meta_data.elements.new(type = 'BALL')
        mb.co = v.co #+ #(R_prime - r) * v.normal
        mb.radius = .5 * r
        
    elif r and r < 0.2 * R_prime:
        continue
    else:
        mb = meta_data.elements.new(type = 'BALL')
        mb.radius = R_prime
        mb.co = v.co
    
meta_obj.matrix_world = mx

bpy.context.scene.update()
me = meta_obj.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')

bme.free()
new_ob = bpy.data.objects.new('Splint Shell', me)

#let's return a mesh to the other blender instance
data_blocks = [new_ob]