'''
Created on Jan 31, 2020

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import numpy as np
import time

from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

from bpy.props import FloatProperty, BoolProperty, IntProperty, EnumProperty

from subtrees.metaballs.vdb_remesh import convert_vdb, read_bmesh
from subtrees.metaballs.vdb_tools import remesh_bme
from subtrees.bmesh_utils.bmesh_utilities_common import bmesh_join_list

import splint_cache

items  = [
    ("UNION", "Union", "Union of objects", "", 0),
    ("DIFFERENCE", "Cut", "Cut into another object", "", 1),
    ("INTERSECTION", "Intersection", "Intersection of objects", "", 2)]

class D3MODEL_OT_vdb_boolean(bpy.types.Operator):
    """Add or subtract with vdb"""
    bl_label = "Metball Boolean"
    bl_options = {'REGISTER', 'UNDO'}
    bl_idname = "d3model.vdb_boolean"
    bl_label = "VDB Boolean Operation"

    combineType = bpy.props.EnumProperty(name = "Type", default = "DIFFERENCE",
        items = items)

    res = bpy.props.FloatProperty(name = 'Voxel Size', default = .2, min = .05, max = 1)
    
    smooth_iters = bpy.props.IntProperty(name = "Smooth Iters", default = 0, min = 0, max = 20)
    
    iso = bpy.props.FloatProperty(name = 'Iso Value', default = 0.0, min = -.5, max = 1)
    adapt = bpy.props.FloatProperty(name = 'Iso Value', default = 0.0, min = 0.0, max = 2.0)
    @classmethod
    def poll(self, context):
        
        return len(context.selected_objects) > 1
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width = 200)
        
    def execute(self, context):
        
        start = time.time()
        
        ob0 = context.object
        ob1 = [ob for ob in context.selected_objects if ob != ob0][0]
        
        mx0 = ob0.matrix_world
        mx1 = ob1.matrix_world
        imx0 = mx0.inverted()
        
        bm0 = bmesh.new()
        bm0.from_mesh(ob0.data)
        bm1 = bmesh.new()
        bm1.from_mesh(ob1.data)
        bm1.transform(imx0 * mx1)
        
        voxel_size = self.res ##**TODO test more of this out.
        
        self.grid_voxelsize = voxel_size
        verts0, tris0, quads0 = read_bmesh(bm0)
        verts1, tris1, quads1 = read_bmesh(bm1)
        
        bm0.free()
        bm1.free()
        
        vdb0 = convert_vdb(verts0, tris0, quads0, voxel_size)
        vdb1 = convert_vdb(verts1, tris1, quads1, voxel_size)
        

        if self.combineType == 'DIFFERENCE':
            vdb0.difference(vdb1, False)
        elif self.combineType == 'UNION':
            vdb0.union(vdb1, False)
        elif self.combineType == 'INTERSECTION':
            vdb0.intersect(vdb1, False)
        
        
        for _ in range(self.smooth_iters):
            vdb0.gaussian(1.0, 4)  #filter sigma, filter_width
        
        isosurface = self.iso
        adaptivity = self.adapt
        isosurface *= vdb0.transform.voxelSize()[0]
        ve, tr, qu = vdb0.convertToPolygons(isosurface, (adaptivity/100.0)**2)

        bm = bmesh.new()
        for co in ve.tolist():
            bm.verts.new(co)

        bm.verts.ensure_lookup_table()    
        bm.faces.ensure_lookup_table()    

        for face_indices in tr.tolist() + qu.tolist():
            bm.faces.new(tuple(bm.verts[index] for index in reversed(face_indices)))

        bm.normal_update()
        
        
        bm.to_mesh(ob0.data)
        finish = time.time()
        print('Boolean operation in %f seconds' % (finish-start))
        return {'FINISHED'}
    
class D3DUAL_OT_vdb_min_join(bpy.types.Operator):
    """Use VDB to join the minimum thickness shell"""
    bl_idname = "d3splint.v_correct_minimum_thickness"
    bl_label = "Correct to Minimum Thickness Volume"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    resolution = FloatProperty(name = "Resolution", default = .25, min = .1, max = .4)
    
    target = bpy.props.EnumProperty(name = "Target", default = "MAX",
        items = [('MAX','MAX','MAX'),('MAND','MAND','MAND'),('BOTH','BOTH','BTOH')])
    @classmethod
    def poll(cls, context):
       
        return True
        
    def execute(self, context):
        
        #fit data from inputs to outputs with metaball
        #r_final = .901 * r_input - 0.0219
        
        #rinput = 1/.901 * (r_final + .0219)
        
        if self.target == 'MAX':
            models = [bpy.data.objects.get('Splint Shell_MAX')]
        elif self.target == 'MAND':
            models = [bpy.data.objects.get('Splint Shell_MAND')]
        else:
            models = [bpy.data.objects.get('Splint Shell_MAX'),bpy.data.objects.get('Splint Shell_MAND')]
            
            
        
        start = time.time()
        
        
        for Splint in models:
            
            mand_max = Splint.name.splint('_')[1]
            MinThick = bpy.data.objects.get('Minimum Thickness_{}'.format(mand_max))
        
            if not Splint:
                continue
            if not MinThick:
                continue
            
            bme = bmesh.new()
            bme_min = bmesh.new()  #TODO, cache this
            bme_min.from_mesh(MinThick.data)
            
            if len(Splint.modifiers):
                me = Splint.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
                Splint.modifiers.clear()
                old_me = Splint.data
                Splint.data = me
                bpy.data.meshes.remove(old_me)
                bme.from_mesh(me)
            else:
                bme.from_mesh(Splint.data)
                
                
            bme_joined = bmesh_join_list([bme_min, bme])
            bme_remesh = remesh_bme(bme_joined, 
                  isovalue = 0.0, 
                  adaptivity = 0.0, 
                  only_quads = False, 
                  voxel_size = self.resolution,
                  filter_iterations = 0,
                  filter_width = 4,
                  filter_sigma = 1.0,
                  grid = None,
                  write_method = 'FAST')
                    
            bme_remesh.to_mesh(Splint.data)
            bme.free()
            bme_joined.free()
            bme_remesh.free()
            bme_min.free()
            Splint.data.update()
            
            finish = time.time()
            print('Merged mininum thickness in %f seconds' % (finish-start))
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        splint.ops_string += 'Enforce Minimum Thickness {}:'.format(self.target) 
        return {'FINISHED'}
    
class D3DUAL_OT_vdb_rim_join(bpy.types.Operator):
    """Use VDB to join the rom to the shell"""
    bl_idname = "d3dual.v_join_rim"
    bl_label = "Join Rim to Shell V"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    res = FloatProperty(name = "Resolution", default = .3, min = .1, max = .4 )
    smooth_iters = IntProperty(name = 'Smooth Iterations', default = 2, min = 0, max = 10)
    
    target = bpy.props.EnumProperty(name = "Target", default = "MAX",
        items = [('MAX','MAX','MAX'),('MAND','MAND','MAND'),('BOTH','BOTH','BTOH')])
    
    @classmethod
    def poll(cls, context):
        
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width = 300)
    
    def execute(self, context):
        
        #fit data from inputs to outputs with metaball
        #r_final = .901 * r_input - 0.0219
        
        #rinput = 1/.901 * (r_final + .0219)
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        start = time.time()
        
        if self.target == 'MAX':
            models = [bpy.data.objects.get('Splint Shell_MAX')]
        elif self.target == 'MAND':
            models = [bpy.data.objects.get('Splint Shell_MAND')]
        else:
            models = [bpy.data.objects.get('Splint Shell_MAX'),bpy.data.objects.get('Splint Shell_MAND')]
        
        
        Rim = bpy.data.objects.get('Wax Rim')
        
        if None in models:
            return {'CANCELLED'}
        if not Rim:
            return {'CANCELLED'}
        
        for Splint in models:
            start = time.time()
            
            ob0 = Splint
            ob1 = Rim
            
            mx0 = ob0.matrix_world
            mx1 = ob1.matrix_world
            imx0 = mx0.inverted()
            
            
                
            bm0 = bmesh.new()
            if len(ob0.modifiers):
                bm0.from_object(ob0, context.scene, deform=True, render=False, cage=False, face_normals=True)
                ob0.modifiers.clear()
            else:
                bm0.from_mesh(ob0.data)
                
            bm1 = bmesh.new()
            bm1.from_mesh(ob1.data)
            bm1.transform(imx0 * mx1)
            
            voxel_size = self.res ##**TODO test more of this out.
            
            self.grid_voxelsize = voxel_size
    
            verts0, tris0, quads0 = read_bmesh(bm0)
            verts1, tris1, quads1 = read_bmesh(bm1)
            
            bm0.free()
            bm1.free()
            
            vdb0 = convert_vdb(verts0, tris0, quads0, voxel_size)
            vdb1 = convert_vdb(verts1, tris1, quads1, voxel_size)
            
            vdb0.union(vdb1, False)
            
            for _ in range(self.smooth_iters):
                vdb0.gaussian(1.0, 4)  #filter sigma, filter_width
            
            isosurface = 0.1
            adaptivity = 0.0
            isosurface *= vdb0.transform.voxelSize()[0]
            ve, tr, qu = vdb0.convertToPolygons(isosurface, (adaptivity/100.0)**2)
    
            bm = bmesh.new()
            for co in ve.tolist():
                bm.verts.new(co)
    
            bm.verts.ensure_lookup_table()    
            bm.faces.ensure_lookup_table()    
    
            for face_indices in tr.tolist() + qu.tolist():
                bm.faces.new(tuple(bm.verts[index] for index in reversed(face_indices)))
    
            bm.normal_update()
            
            
            bm.to_mesh(ob0.data)
            finish = time.time()
            ob0.hide = False
            
        Rim.hide = True
        print('Boolean join rim in %f seconds' % (finish-start))
        Splint.data.update()
        #splint.wax_rim_fuse = True
        splint.ops_string += 'JoinRim {}:'.format(self.target) 
        return {'FINISHED'}
    
class D3DUAL_OT_blockout_splint_shell(bpy.types.Operator):
    '''Blockout large undercuts in the splint'''
    bl_idname = "dual.metav_blockout_shell"
    bl_label = "Blockout Shell"
    bl_options = {'REGISTER','UNDO'}
    
    world = bpy.props.BoolProperty(default = True, name = "Use world coordinate for calculation...almost always should be true.")
    #smooth = bpy.props.BoolProperty(default = True, name = "Smooth the outline.  Slightly less acuurate in some situations but more accurate in others.  Default True for best results")
    resolution = bpy.props.FloatProperty(default = .3, min = 0.075, max = 1.0, description = 'Mesh resolution. Lower numbers are slower, bigger numbers less accurate')
    threshold = bpy.props.FloatProperty(default = .05, min = .001, max = .2, description = 'angle to blockout.  .09 is about 5 degrees, .17 is 10degrees.0001 no undercut allowed.')
    
    target = bpy.props.EnumProperty(name = "Target", default = "MAX",
        items = [('MAX','MAX','MAX'),('MAND','MAND','MAND'),('BOTH','BOTH','BTOH')])
    
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        return  True
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300) 
    
    def execute(self, context):
      
        start = time.time()
        if self.target == 'MAX':
            shells = [bpy.data.objects.get('Splint Shell_MAX')]
        if self.target == 'MAND':
            shells = [bpy.data.objects.get('Splint Shell_MAND')]
        if self.target == 'BOTH':

            shells = [bpy.data.objects.get('Splint Shell_MAX'), bpy.data.objects.get('Splint Shell_MAND')]
        
        
        for Shell in shells:
       
            if Shell == None:
                self.report({'WARNING'},'Need to have a splint shell created')
                continue
                
            if len(context.scene.odc_splints):
                n = context.scene.odc_splint_index
                splint = context.scene.odc_splints[n]
                splint.ops_string += "Blockout Large Undercuts:"
                
            if len(Shell.modifiers):
                old_data = Shell.data
                new_data = Shell.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
                
                for mod in Shell.modifiers:
                    Shell.modifiers.remove(mod)
                
                Shell.data = new_data
                bpy.data.meshes.remove(old_data)       
                print('Applied modifiers')
            
    
      
            bme = bmesh.new()
            bme.from_mesh(Shell.data)
            bme.verts.ensure_lookup_table()
            bme.edges.ensure_lookup_table()
            bme.faces.ensure_lookup_table()
            
            bme.normal_update()
            
            bvh = BVHTree.FromBMesh(bme)
            #keep track of the world matrix
            
            Z = Vector((0,0,1))  #the splint is more more less aligned with occlusal plane
            
            mx = Shell.matrix_world
            epsilon = .000009
    
            
    
        
            faces_undercut = [f for f in bme.faces if f.normal.dot(Z) < -self.threshold]
            faces_uppercut = [f for f in bme.faces if f.normal.dot(Z) > self.threshold]
            
            under_geom =  bmesh.ops.extrude_face_region(bme, geom = faces_undercut)
            upper_geom = bmesh.ops.extrude_face_region(bme, geom = faces_uppercut)
            
            vs = [ele for ele in under_geom['geom'] if isinstance(ele, bmesh.types.BMVert)]
            vs_up = [ele for ele in upper_geom['geom'] if isinstance(ele, bmesh.types.BMVert)]
            
            for v in vs:
                
                loc, no, ind, d = bvh.ray_cast(v.co - epsilon * Z, -Z)
                if not loc: continue
                else:
                    v.co = loc - .05 * Z
                    
            for v in vs_up:
                
                loc, no, ind, d = bvh.ray_cast(v.co + epsilon * Z, Z)
                if not loc: continue
                else:
                    v.co = loc + .05 * Z
               
               
            bme_r = remesh_bme(bme, 
                  isovalue = 0.15, 
                  adaptivity = 0.0, 
                  only_quads = False, 
                  voxel_size = self.resolution,
                  filter_iterations = 2,
                  filter_width = 4,
                  filter_sigma = 1.0,
                  grid = None,
                  write_method = 'FAST')
               
            bme_r.to_mesh(Shell.data)
                
            bme.free()
            bme_r.free()
            finish = time.time()
            print('Blocked out splint concavties in %f seconds' % (finish-start))
        if len(context.scene.odc_splints):
            n = context.scene.odc_splint_index
            splint = context.scene.odc_splints[n]
            splint.ops_string += "Blockout Large Undercuts {}:".format(self.target)
            
               
        return {'FINISHED'}    


class D3DUAL_OT_remesh_shell(bpy.types.Operator):
    '''Blockout large undercuts in the splint'''
    bl_idname = "d3dual.remesh_shell"
    bl_label = "Remesh Shell"
    bl_options = {'REGISTER','UNDO'}
    
   
    #smooth = bpy.props.BoolProperty(default = True, name = "Smooth the outline.  Slightly less acuurate in some situations but more accurate in others.  Default True for best results")
    resolution = bpy.props.FloatProperty(default = .25, min = 0.05, max = 1.0, description = 'Mesh resolution. Lower numbers are slower, bigger numbers less accurate')
    smmooth_iters = bpy.props.IntProperty(default = 0, min = 0, max = 10, description = 'Amount of smoothing')
    
    vol_correction = bpy.props.FloatProperty(default = .05, min = 0.00, max = .2, description = 'Inflate Mesh to compensate for volume loss when smoothing')
    
    
    
    target = bpy.props.EnumProperty(name = "Target", default = "MAX",
        items = [('MAX','MAX','MAX'),('MAND','MAND','MAND'),('BOTH','BOTH','BTOH')])
    
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        return  True
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    def execute(self, context):
      
        start = time.time()
        if self.target == 'MAX':
            shells = [bpy.data.objects.get('Splint Shell_MAX')]
        if self.target == 'MAND':
            shells = [bpy.data.objects.get('Splint Shell_MAND')]
        if self.target == 'BOTH':

            shells = [bpy.data.objects.get('Splint Shell_MAX'), bpy.data.objects.get('Splint Shell_MAND')]
        
        
        for Shell in shells:
       
            if Shell == None:
                self.report({'WARNING'},'Need to have a splint shell created')
                continue
                
            if len(context.scene.odc_splints):
                n = context.scene.odc_splint_index
                splint = context.scene.odc_splints[n]
                splint.ops_string += "Blockout Large Undercuts:"
                
            if len(Shell.modifiers):
                old_data = Shell.data
                new_data = Shell.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
                
                for mod in Shell.modifiers:
                    Shell.modifiers.remove(mod)
                
                Shell.data = new_data
                bpy.data.meshes.remove(old_data)       
                print('Applied modifiers')
            
    
      
            bme = bmesh.new()
            bme.from_mesh(Shell.data)
            bme.verts.ensure_lookup_table()
            bme.edges.ensure_lookup_table()
            bme.faces.ensure_lookup_table()
            
            bme.normal_update()
           
            for v in bme.verts:
                v.co += self.vol_correction * v.normal
               
            bme_r = remesh_bme(bme, 
                  isovalue = 0.0, 
                  adaptivity = 0.0, 
                  only_quads = False, 
                  voxel_size = self.resolution,
                  filter_iterations = self.smmooth_iters,
                  filter_width = 4,
                  filter_sigma = 1.0,
                  grid = None,
                  write_method = 'FAST')
               
            bme_r.to_mesh(Shell.data)
                
            bme.free()
            bme_r.free()
            finish = time.time()
            print('remeshed shell in %f seconds' % (finish-start))
        if len(context.scene.odc_splints):
            n = context.scene.odc_splint_index
            splint = context.scene.odc_splints[n]
            splint.ops_string += "Remesh Shell {}:".format(self.target)
            
               
        return {'FINISHED'} 
    
        
def register():
    bpy.utils.register_class(D3DUAL_OT_vdb_min_join)
    bpy.utils.register_class(D3MODEL_OT_vdb_boolean)
    bpy.utils.register_class(D3DUAL_OT_blockout_splint_shell)
    bpy.utils.register_class(D3DUAL_OT_vdb_rim_join)
    bpy.utils.register_class(D3DUAL_OT_remesh_shell)

    
    
def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_vdb_min_join)
    bpy.utils.unregister_class(D3MODEL_OT_vdb_boolean)
    bpy.utils.unregister_class(D3DUAL_OT_blockout_splint_shell)
    bpy.utils.unregister_class(D3DUAL_OT_vdb_rim_join)
    bpy.utils.unregister_class(D3DUAL_OT_remesh_shell)

# ---- Perplexity API Suggested Migrations ----
To migrate your Blender 2.79 property definitions to Blender 4.4, you must use **Python type annotations** (the colon syntax) and define properties inside a class derived from `bpy.types.PropertyGroup`. Properties are then registered as a pointer property on the target type (e.g., `Scene`, `Object`, etc.)[2].

Below is the corrected code block for Blender 4.4+:

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    combine_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('DIFFERENCE', "Difference", ""),
            # Add other enum items as needed
        ],
        default="DIFFERENCE"
    )
    res: bpy.props.FloatProperty(
        name='Voxel Size',
        default=0.2,
        min=0.05,
        max=1.0
    )
    smooth_iters: bpy.props.IntProperty(
        name="Smooth Iters",
        default=0,
        min=0,
        max=20
    )
    iso: bpy.props.FloatProperty(
        name='Iso Value',
        default=0.0,
        min=-0.5,
        max=1.0
    )
    adapt: bpy.props.FloatProperty(
        name='Adaptivity',
        default=0.0,
        min=0.0,
        max=2.0
    )
    target: bpy.props.EnumProperty(
        name="Target",
        items=[
            ('MAX', "Max", ""),
            # Add other enum items as needed
        ],
        default="MAX"
    )
    world: bpy.props.BoolProperty(
        default=True,
        name="Use world coordinate for calculation...almost always should be true."
    )
    # smooth: bpy.props.BoolProperty(
    #     default=True,
    #     name="Smooth the outline. Slightly less accurate in some situations but more accurate in others. Default True for best results"
    # )
    resolution: bpy.props.FloatProperty(
        default=0.3,
        min=0.075,
        max=1.0,
        description='Mesh resolution. Lower numbers are slower, bigger numbers less accurate'
    )

# Register the property group and add it to the Scene (or another type as needed)
def register():
    bpy.utils.register_class(MyProperties)
    bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyProperties)

def unregister():
    del bpy.types.Scene.my_props
    bpy.utils.unregister_class(MyProperties)
```

**Key changes:**
- Use **type annotations** (colon syntax) inside a `PropertyGroup` subclass[2].
- Define `items` for `EnumProperty` (required in 2.8+).
- Register the property group and add it to the desired Blender type (e.g., `Scene`)[2].
- Remove duplicate or conflicting property names.

This structure is compatible with Blender 4.4 and follows current API conventions.
In **Blender 4.4**, property definitions for custom classes (such as operators or PropertyGroups) must use the new type annotation syntax, and properties must be defined as class variables, not as assignments. The old assignment style (e.g., `threshold = bpy.props.FloatProperty(...)`) is deprecated and will raise errors.

Here is the corrected code block for Blender 4.4+:

```python
import bpy

class MyPropertyGroup(bpy.types.PropertyGroup):
    threshold: bpy.props.FloatProperty(
        default=0.05,
        min=0.001,
        max=0.2,
        description='angle to blockout.  .09 is about 5 degrees, .17 is 10degrees.0001 no undercut allowed.'
    )
    target: bpy.props.EnumProperty(
        name="Target",
        items=[
            ('MAX', "Max", ""),
            ('MIN', "Min", ""),
            # Add other items as needed
        ],
        default="MAX"
    )
    # smooth: bpy.props.BoolProperty(
    #     default=True,
    #     name="Smooth the outline.  Slightly less accurate in some situations but more accurate in others.  Default True for best results"
    # )
    resolution: bpy.props.FloatProperty(
        default=0.25,
        min=0.05,
        max=1.0,
        description='Mesh resolution. Lower numbers are slower, bigger numbers less accurate'
    )
    smmooth_iters: bpy.props.IntProperty(
        default=0,
        min=0,
        max=10,
        description='Amount of smoothing'
    )
    vol_correction: bpy.props.FloatProperty(
        default=0.05,
        min=0.00,
        max=0.2,
        description='Inflate Mesh to compensate for volume loss when smoothing'
    )
```

**Key changes:**
- Use **type annotations** (`name: bpy.props.PropertyType(...)`) instead of assignments.
- EnumProperty now requires an **items** argument (a list of tuples).
- All properties are defined as **class variables** inside a class derived from `bpy.types.PropertyGroup` (or `Operator`, etc.), not as module-level variables.

This syntax is required for Blender 2.80+ and is fully compatible with Blender 4.4.
