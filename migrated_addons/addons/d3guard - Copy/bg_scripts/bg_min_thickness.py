import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils.kdtree import KDTree

#arguments from bg operator
#radius
#trimmed_model_name
#resolution

R_prime = 1/.901 * (radius + .0219)
        

#use blend file = False to conserve memory
#append_from("Object", trimmed_model_name)  #comment out if use_blend_file = True
ob = bpy.data.objects.get('Shell Patch')  #trimmed model name is in passed_data


bpy.ops.wm.memory_statistics()

bme = bmesh.new()
bme.from_object(ob, bpy.context.scene)
bme.verts.ensure_lookup_table()
bme.edges.ensure_lookup_table()
mx = ob.matrix_world

meta_data = bpy.data.metaballs.new('Minimum Thickness')
meta_obj = bpy.data.objects.new('Meta Minimum Shell', meta_data)
meta_data.resolution = resolution
meta_data.render_resolution = resolution
bpy.context.scene.objects.link(meta_obj)

perimeter_edges = [ed for ed in bme.edges if len(ed.link_faces) == 1]
perim_verts = set()
for ed in perimeter_edges:
    perim_verts.update([ed.verts[0], ed.verts[1]])
    
perim_verts = list(perim_verts)
stroke = [v.co for v in perim_verts]
#print('there are %i non man verts' % len(stroke))                                          
kd = KDTree(len(stroke))
for i in range(0, len(stroke)-1):
    kd.insert(stroke[i], i)
kd.balance()
perim_set = set(perim_verts)    
for v in bme.verts:
    if v in perim_set: 
        continue
    
    loc, ind, r = kd.find(v.co)
    
    if r and r < 0.2 * R_prime:
        continue
    
    elif r and r < .8 * R_prime:
        
        mb = meta_data.elements.new(type = 'BALL')
        mb.co = v.co #+ (R_prime - r) * v.normal
        mb.radius = .5 * r

    else:
        mb = meta_data.elements.new(type = 'BALL')
        mb.radius = R_prime
        mb.co = v.co
    
meta_obj.matrix_world = mx
bpy.context.scene.update()
me = meta_obj.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')

bpy.ops.wm.memory_statistics()
    
if 'Minimum Thickness' not in bpy.data.objects:
    new_ob = bpy.data.objects.new('Minimum Thickness', me)
    bpy.context.scene.objects.link(new_ob)
    new_ob.matrix_world = mx
    
    #cons = new_ob.constraints.new('COPY_TRANSFORMS')  #dp 
    #cons.target = bpy.data.objects.get(splint.model)
    #new_ob.data.materials.append(mat)
    
    mod = new_ob.modifiers.new('Smooth', type = 'SMOOTH')
    mod.iterations = 1
    mod.factor = .5
else:
    new_ob = bpy.data.objects.get('Minimum Thickness')
    new_ob.data = me
    #new_ob.data.materials.append(mat)
    
new_ob.show_transparent = True

    
bpy.context.scene.objects.unlink(meta_obj)
bpy.data.objects.remove(meta_obj)
bpy.data.metaballs.remove(meta_data)

bme.free() 

data_blocks = [new_ob]
