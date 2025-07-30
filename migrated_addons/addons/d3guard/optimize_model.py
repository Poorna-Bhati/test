'''
Created on Jul 22, 2019

@author: Patrick
'''
import time
import math

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix, Color
from mathutils.geometry import intersect_line_plane
from mathutils.bvhtree import BVHTree

from odcutils import get_settings
from offset_utilities import dyntopo_remesh
from bmesh_fns import bmesh_loose_parts

def filter_model_by_shell():
    model = bpy.data.objects.get('optimized_model')
    shell = bpy.data.objects.get('Splint Shell')
    
    bme = bmesh.new()
    bme.from_mesh(model.data)
    
    bme_shell = bmesh.new()
    bme_shell.from_mesh(shell.data)
    
    bvh_shell = BVHTree.FromBMesh(bme_shell)
    
    delete = set()
    for v in bme.verts:
        loc, no, ind, d =  bvh_shell.find_nearest(v.co, 4.0)
        if not loc:
            delete.add(v)
            
            
    bmesh.ops.delete(bme, geom = list(delete), context = 1)
    
    bme.to_mesh(model.data)
    
    bme.free()


class D3SPLINT_OT_optimized_model(bpy.types.Operator):
    """Calculate optimized model"""
    bl_idname = "d3splint.optimized_model"
    bl_label = "Optimize Splint Model"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls,context):
        return True
    
    
    wax_droplet_size = bpy.props.FloatProperty(name = 'Volume Element Size', default =.7, min = .25, max = 2.0)
    pre_offset = bpy.props.FloatProperty(name = 'Pre Offset', default = .4, min = .001, max = .5)
    wax_resolution = bpy.props.FloatProperty(name = 'resolution', default = .3, min = .25, max = .6)
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        start = time.time()
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        axis = bpy.data.objects.get('Insertion Axis')
        if not axis:
            self.report('ERRROR', "need to set the insertion axis first")
            return {'CANCELLED'}
        
        model = bpy.data.objects.get(splint.model)
        
        simple_model = bpy.data.objects.get('Simple Model')
        
        if not simple_model:
            simple_start = time.time()
            simple_me = model.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
            simple_model = bpy.data.objects.new('Simple Model', simple_me)
            context.scene.objects.link(simple_model)
            dyntopo_remesh(simple_model, 2.5)
            
            #smooth a little to get rid of dyntopo criss crossed faces
            mod = simple_model.modifiers.new('Smooth', type = "SMOOTH")
            mod.factor = 1.0
            mod.iterations = 3
            
            context.scene.update()
            #apply the slight smooth, and then smooth a lot
            me = simple_model.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
            old_me = simple_model.data
            simple_model.data = me
            bpy.data.meshes.remove(old_me)
            mod.iterations = 30
            
            
            simple_model.lock_location = [True, True, True]
            simple_model.hide_select = True
            simple_model.hide = True
            simple_finish = time.time()
            
            simple_model.matrix_world = model.matrix_world
            #context.scene.objects.unlink(simple_model)
            #simple_model.use_fake_user = True  #prevent visibility in scene but prevent deleting
            
            print('Simplified model in %f seconds' % (simple_finish - simple_start))
            
        Z = Vector((0,0,1))
        view = axis.matrix_world.to_quaternion() * Z
        
        if splint.jaw_type == 'MAXILLA':
            up = Vector((0,0,-1))
        else: 
            up = Vector((0,0,1))
        ref_model = optimized_model(simple_model, view, splint.jaw_type, self.wax_droplet_size, self.pre_offset, self.wax_resolution)
        ref_model.matrix_world = model.matrix_world
        ref_model.show_transparent = True
        mat = bpy.data.materials.get("Optimized Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Optimized Material")
            mat.diffuse_color = Color((.9, .9, 1.0))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .2
        ref_model.data.materials.append(mat) 
        ref_model.hide_select = True
        ref_model.lock_location = [True, True, True]   
        finish = time.time()
        
        print('Optimized model in %f seconds' % (finish-start))
        return {'FINISHED'}
    
    
    
    
def optimized_model(model, direction, jaw_type, offset, pre_offset, resolution):
    '''
    model - Blender Object
    direction - Vector, reresentig the insertion axis
    up - Vector, representing the upwward direction of the model.  positive Z for max, negative Z for mand
    '''
    mx = model.matrix_world 
    i_mx = mx.inverted()
    view = i_mx.to_quaternion() * direction
    
    start = time.time()
    
    
    #get bmesh of the raw data  
    bme = bmesh.new()
    bme.from_mesh(model.data)
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    bme.normal_update()
    
    #get bmesh of the modified data
    me = model.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
    bme_mod = bmesh.new()
    bme_mod.from_mesh(me)
    bme_mod.verts.ensure_lookup_table()
    bme_mod.edges.ensure_lookup_table()
    bme_mod.faces.ensure_lookup_table()
    bme_mod.normal_update()
    
    
    
    bvh = BVHTree.FromBMesh(bme)
    bvh_mod = BVHTree.FromBMesh(bme_mod)
    
    #find the lowest part of the mesh to add a base plane to.
    #lowest_vert = min(bme.verts[:], key = lambda x: x.co.dot(view))
    if jaw_type == 'MAXILLA':
        base_vert = max(bme.verts[:], key = lambda x: x.co[2])
        occlusal_dir = Vector((0,0,-1))  #vector pointing toward the occlusal plane
    else:
        base_vert = min(bme.verts[:], key = lambda x: x.co[2])
        occlusal_dir = Vector((0,0,1)) #vector pointing toward the occlusal plane
        
    base_pt = base_vert.co 
    
    #find the undercut verts
    undercut_verts = set()
    likely_tunnel_verts = set()
    
    for f in bme.faces:
        
        f_mod = bme_mod.faces[f.index]
        test = f_mod.normal.dot(direction)
        if test < -.001:
            undercut_verts.update([v for v in f.verts])
        if test < -.65:  #VERY UNDERCUT
            likely_tunnel_verts.update([v for v in f.verts])
    
        
    finish = time.time()
    print('found undercuts in %f seconds' % (finish-start))
    start = finish
    
    print('there are %i likely tunnel verts' % len(likely_tunnel_verts))
    #find the perimeter verts
    perimeter_verts = set()
    perimeter_faces = set()
    for ed in bme.edges:
        if len(ed.link_faces) == 1:
            perimeter_verts.update([ed.verts[0], ed.verts[1]])
            for v in ed.verts:
                perimeter_faces.update([f for f in v.link_faces])
    

    meta_data = bpy.data.metaballs.new('Optimized Meta')
    meta_obj = bpy.data.objects.new('Optimized Meta', meta_data)
    meta_data.resolution = resolution
    meta_data.render_resolution = resolution
    bpy.context.scene.objects.link(meta_obj)
    
    scale = 1
    max_blockout = 5
    n_elements = 0
    max_height =  math.ceil(max_blockout/(.25 * offset))
    
    for v in bme.verts:
            
        #extrude a chain of balls down 
        co = v.co  - pre_offset * v.normal
        base_height = (base_pt - v.co).dot(-occlusal_dir) #may need to use 1,-1 for max/mand
        
        
        if v in perimeter_verts:
            N = math.ceil(base_height/(.25 * offset))
            
            for i in range(0,N):
                n_elements += 1
                mb = meta_data.elements.new(type = 'BALL')
                mb.co = scale * (co - i * .25 * offset * occlusal_dir)
                mb.radius = offset
    
        if v in likely_tunnel_verts:
            
            #check for self intersection on the modified mesh
            v_mod = bme_mod.verts[v.index]
            loc, no, ind, d = bvh_mod.ray_cast(v_mod.co - .001 * view, -view)
            
            
            if not loc:
                mb= meta_data.elements.new(type = 'BALL')
                mb.co = scale * co
                mb.radius = offset
                continue
            
            pt = intersect_line_plane(v.co, v.co - 5 * view, base_pt, occlusal_dir)
            
            if not pt:
                N = math.ceil(5/(.25 * offset))
            else:
                v_length = (v.co - pt).length
                N = math.ceil(v_length/(.25*offset))
            #project to the base plane
            for i in range(0,N):
                
                n_elements += 1
                
                mb = meta_data.elements.new(type = 'BALL')
                mb.co = scale * (co - i * .25 * offset * view)
                mb.radius = offset
        
            n_elements += 1
            mb= meta_data.elements.new(type = 'BALL')
            mb.co = scale * (co - min(base_height, max_height) * occlusal_dir)
            mb.radius = offset
                 
        if not (v in perimeter_verts or v in likely_tunnel_verts):
            n_elements += 2
            mb= meta_data.elements.new(type = 'BALL')
            mb.co = scale * co 
            mb.radius = offset
            
            mb= meta_data.elements.new(type = 'BALL')
            mb.co = scale * (co - min(base_height, max_height) * occlusal_dir)
            mb.radius = offset
            
            
            
    
    bme.free()
    bme_mod.free()
       
    meta_obj.matrix_world =  model.matrix_world
    #meta_obj_d.matrix_world =  L * R * S
    
    finish = time.time()
    print('added %i metaballs in %f seconds' % (n_elements, finish-start))
    start = finish
    
    bpy.context.scene.update()
    me = meta_obj.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
    
    
    finish = time.time()
    print('converted to mesh %f seconds' % (finish-start))
    start = finish
    
    
    
    
    bme_final = bmesh.new()
    bme_final.from_mesh(me)
    bme_final.verts.ensure_lookup_table()
    bme_final.edges.ensure_lookup_table()
    bme_final.faces.ensure_lookup_table()
    
    bvh = BVHTree.FromBMesh(bme_final)
    
    
    islands = bmesh_loose_parts(bme_final, selected_faces = None, max_iters = 5000)
    epsilon = .0001
    
    if len(islands) >= 2:
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
            
    elif len(islands) == 1:
        to_del = []
        
    del_vs = set()
    for f in to_del:
        del_vs.update([v for v in f.verts])  
    for v in del_vs:    
        bme_final.verts.remove(v)
    
    
    bme_final.to_mesh(me)  #put the interior removed bmesh back in place
    
    if 'Optimized Model' in bpy.data.objects:
        new_ob = bpy.data.objects.get('Optimized Model')
        old_data = new_ob.data
        new_ob.data = me
        old_data.user_clear()
        bpy.data.meshes.remove(old_data)
    else:
        new_ob = bpy.data.objects.new('Optimized Model', me)
        bpy.context.scene.objects.link(new_ob)
    
    new_ob.matrix_world = model.matrix_world
    
    bpy.context.scene.objects.unlink(meta_obj)
    bpy.data.objects.remove(meta_obj)
    bpy.data.metaballs.remove(meta_data)

    return new_ob


def register():
    bpy.utils.register_class(D3SPLINT_OT_optimized_model)
    
     
def unregister():
    bpy.utils.unregister_class(D3SPLINT_OT_optimized_model)
    

# ---- Perplexity API Suggested Migrations ----
In Blender 4.4, the old bpy.props.FloatProperty assignment style is deprecated. Properties must be defined as class attributes within a class derived from bpy.types.PropertyGroup, bpy.types.Operator, or similar, and registered using type annotations. Here is the corrected code block for Blender 4.4+:

```python
import bpy
from bpy.props import FloatProperty

class MyProperties(bpy.types.PropertyGroup):
    wax_droplet_size: FloatProperty(
        name='Volume Element Size',
        default=0.7,
        min=0.25,
        max=2.0
    )
    pre_offset: FloatProperty(
        name='Pre Offset',
        default=0.4,
        min=0.001,
        max=0.5
    )
    wax_resolution: FloatProperty(
        name='resolution',
        default=0.3,
        min=0.25,
        max=0.6
    )
```

Key changes:
- Use type annotations (:) instead of assignment (=).
- Define properties inside a PropertyGroup or similar class, not at the module level.
- Register the PropertyGroup with bpy.utils.register_class and assign it to a context (e.g., bpy.types.Scene).

This is the Blender 4.4+ compatible way to define custom properties.
