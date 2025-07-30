import os, platform
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from bpy.types import Operator

from mesh_cut import flood_selection_faces, edge_loops_from_bmedges,\
    space_evenly_on_path, bound_box, contract_selection_faces, \
    face_neighbors_by_vert, flood_selection_faces_limit
    
import cork
from cork.cork_fns import cork_boolean
from cork.lib import get_cork_filepath, validate_executable
from cork.exceptions import *
import time
import tracking
from bpy.props import FloatProperty, BoolProperty, IntProperty, EnumProperty
import common_utilities
from common_utilities import get_settings
from bmesh_fns import bmesh_loose_parts

from subtrees.bmesh_utils.bmesh_utilities_common import bmesh_loose_parts, bmesh_join_list
from subtrees.metaballs.vdb_remesh import read_bmesh, convert_vdb

def prepare_bmesh_for_vdb(bme):
    ngons = [f for f in bme.faces if len(f.verts) > 4]
    if len(ngons):
        bmesh.ops.poke_faces(bme, faces = ngons)
        
    quads = [f for f in bme.faces if len(f.verts) == 4]
    if len(quads):
        bmesh.ops.triangulate(bme, faces = quads)



def vdb_from_bme(bme, voxel_size):
    
    ngons = [f for f in bme.faces if len(f.verts) > 4]
    if len(ngons):
        bmesh.ops.poke(bme, faces = ngons)
            
            
    quads = [f for f in bme.faces if len(f.verts) == 4]
    if len(quads):
        bmesh.ops.triangulate(bme, faces=quads)
    
    
    
    verts, tris, quads = read_bmesh(bme)
    vdb_ret = convert_vdb(verts, tris, quads, voxel_size)
    
    return vdb_ret



def boolean_final(context, Shell, Refractory, solver):
    if 'Final Splint' not in bpy.data.objects:
        me = Shell.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        ob = bpy.data.objects.new('Final Splint', me)
        context.scene.objects.link(ob)
        ob.matrix_world = Shell.matrix_world
    else:
        ob = bpy.data.objects.get('Final Splint')
        old_me = ob.data
        me = Shell.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        
        ob.data = me
        bpy.data.meshes.remove(old_me)
            
    #Final Spint needs only 1 boolean operation
    if 'Refractory Model' in ob.modifiers:
        mod = ob.modifiers.get('Refractory Model')
        
    else:
        mod = ob.modifiers.new('Refractory Model', type = 'BOOLEAN')
    mod.object = Refractory
    mod.operation = 'DIFFERENCE'
    mod.solver = solver
    
    for obj in context.scene.objects:
        obj.hide = True
        
    context.scene.objects.active = ob
    ob.select = True
    ob.hide = False
    ob.update_tag()
    context.scene.update()
    
    
def volume_final(context, Shell, Refractory):
    
    ob0 = Shell
    ob1 = Refractory
    
    if 'Final Splint' not in bpy.data.objects:
        me = bpy.data.meshes.new('Final Splint')
        ob = bpy.data.objects.new('Final Splint', me)
        context.scene.objects.link(ob)
        ob.matrix_world = Shell.matrix_world
    else:
        ob = bpy.data.objects.get('Final Splint')
        me = ob.data
        ob.modifiers.clear()
        
            
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
    
    voxel_size = 0.15 ##**TODO test more of this out.
    
    
    
    vdb0 = vdb_from_bme(bm0, voxel_size)
    vdb1 = vdb_from_bme(bm1, voxel_size)
    
    vdb0.difference(vdb1, False)
    
    #for _ in range(self.smooth_iters):
    #    vdb0.gaussian(1.0, 4)  #filter sigma, filter_width
    
    isosurface = 0.0
    adaptivity = 2.0
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
    
    
    bm.to_mesh(ob.data)
    
    if 'Splint Material' not in ob.data.materials:
        mat = bpy.data.materials.get('Splint Material')
        ob.data.materials.append(mat)
    
    for obj in context.scene.objects:
        obj.hide = True
        
    context.scene.objects.active = ob
    ob.select = True
    ob.hide = False
        
    bm.free()
    del vdb0
    del vdb1
    
    

def get_applied_bme(context, ob):
    bm = bmesh.new()
    if len(ob.modifiers):
        bm.from_object(ob, context.scene, deform=True, render=False, cage=False, face_normals=True)
        ob.modifiers.clear()
    else:
        bm.from_mesh(ob.data)
        
    return bm
        
   
def volume_routine_volume(self, context, splint_shell, r_model, f_model):
    
    Shell = bpy.data.objects.get(splint_shell)
    Refractory = bpy.data.objects.get(r_model)
    
    if Shell == None:
        self.report({'ERROR'}, 'Need to calculate splint shell for this jaw first')
        return
    
    if Refractory == None:
        self.report({'ERROR'}, 'Need to make refractory model for this jaw first')    
        return 
    
    
    ob0 = Shell
    ob1 = Refractory
    
    mx_base = Shell.matrix_world
    imx_base = mx_base.inverted()
    
    mx1 = ob1.matrix_world
    
    bm0 = get_applied_bme(context, ob0)
    bm1 = get_applied_bme(context, ob1)

    #put everyone in bm0 coordinates
    bm1.transform(mx1 * imx_base)
    
    if f_model not in bpy.data.objects:
        me = bpy.data.meshes.new(f_model)
        ob = bpy.data.objects.new(f_model, me)
        context.scene.objects.link(ob)
        ob.matrix_world = mx_base
    else:
        ob = bpy.data.objects.get(f_model)
        me = ob.data
        ob.modifiers.clear()
        
    voxel_size = self.resolution ##**TODO test more of this out.

    vdb0 = vdb_from_bme(bm0, voxel_size)
    bm0.free() #free mem as we go
    vdb1 = vdb_from_bme(bm1, voxel_size)
    bm1.free()
    
    #execute VDB operations
    vdb0.difference(vdb1, False)
    del vdb1
    
    
    #for _ in range(self.smooth_iters):
    #    vdb0.gaussian(1.0, 4)  #filter sigma, filter_width
    
    isosurface = 0.0
    adaptivity = 2.0
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
    
    
    bm.to_mesh(ob.data)
    
    if 'Splint Material' not in ob.data.materials:
        mat = bpy.data.materials.get('Splint Material')
        ob.data.materials.append(mat)
    
    for obj in context.scene.objects:
        obj.hide = True
        
    context.scene.objects.active = ob
    ob.select = True
    ob.hide = False
    bm.free()

    
    
def volume_final_monoblock(context, Shell1, Shell2, Refractory1, Refractory2):
    
    ob0 = Shell1
    ob1 = Shell2
    ob2 = Refractory1
    ob3 = Refractory2
    
    mx_base = Shell1.matrix_world
    imx_base = mx_base.inverted()
    
    mx1 = ob1.matrix_world
    mx2 = ob2.matrix_world
    mx3 = ob3.matrix_world
    
    
    bm0 = get_applied_bme(context, ob0)
    bm1 = get_applied_bme(context, ob1)
    bm2 = get_applied_bme(context, ob2)
    bm3 = get_applied_bme(context, ob3)
    
    #put everyone in bm0 coordinates
    bm1.transform(mx1 * imx_base)
    bm2.transform(mx2 * imx_base)
    bm3.transform(mx3 * imx_base)
    
    
    if 'Final Mono Splint' not in bpy.data.objects:
        me = bpy.data.meshes.new('Final Mono Splint')
        ob = bpy.data.objects.new('Final Mono Splint', me)
        context.scene.objects.link(ob)
        ob.matrix_world = mx_base
    else:
        ob = bpy.data.objects.get('Final Mono Splint')
        me = ob.data
        ob.modifiers.clear()
        
   
    
    voxel_size = 0.15 ##**TODO test more of this out.
    
    
    
    vdb0 = vdb_from_bme(bm0, voxel_size)
    bm0.free() #free mem as we go
    vdb1 = vdb_from_bme(bm1, voxel_size)
    bm1.free()
    vdb2 = vdb_from_bme(bm2, voxel_size)
    bm2.free()
    vdb3 = vdb_from_bme(bm3, voxel_size)
    bm3.free()
    
    
    #execute VDB operations
    vdb0.union(vdb1, False)
    del vdb1
    vdb0.difference(vdb2, False)
    del vdb2
    vdb0.difference(vdb3, False)
    del vdb3
    
    #for _ in range(self.smooth_iters):
    #    vdb0.gaussian(1.0, 4)  #filter sigma, filter_width
    
    isosurface = 0.0
    adaptivity = 2.0
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
    
    
    bm.to_mesh(ob.data)
    
    if 'Splint Material' not in ob.data.materials:
        mat = bpy.data.materials.get('Splint Material')
        ob.data.materials.append(mat)
    
    for obj in context.scene.objects:
        obj.hide = True
        
    context.scene.objects.active = ob
    ob.select = True
    ob.hide = False
    bm.free()
    
def finalize_routine(self, context, splint_shell, r_model, f_model):
         
    Shell = bpy.data.objects.get(splint_shell)
    Refractory = bpy.data.objects.get(r_model)
    
    if Shell == None:
        self.report({'ERROR'}, 'Need to calculate splint shell first')
        return
    
    if Refractory == None:
        self.report({'ERROR'}, 'Need to make refractory model first')    
        return 
    #don't add multiple boolean modifiers
    shell_data = Shell.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
    
    for obj in context.scene.objects:
        obj.hide = True
        
    ob = bpy.data.objects.new(f_model, shell_data)  
    context.scene.objects.link(ob)
    ob.matrix_world = Shell.matrix_world  
    mod = ob.modifiers.new('Refractory Model', type = 'BOOLEAN')
    mod.object = Refractory
    mod.operation = 'DIFFERENCE'
    mod.solver = self.solver
    
    ob.update_tag()
    ob.select = True

    context.scene.update()
    old_data = ob.data
    shell_data = ob.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
    ob.modifiers.clear()
    ob.data = shell_data
    bpy.data.meshes.remove(old_data)

def finalize_routine_stored(self, context, splint_shell, r_model, f_model):
         
    Shell = bpy.data.objects.get(splint_shell)
    Refractory = bpy.data.objects.get(r_model)
    
    if Shell == None:
        self.report({'ERROR'}, 'Need to calculate splint shell first')
        return
    
    if Refractory == None:
        self.report({'ERROR'}, 'Need to make refractory model first')    
        return 
    
    
    for obj in context.scene.objects:
        obj.hide = True
        
    Shell.hide = False
    
    mod = Shell.modifiers.new('Refractory Model', type = 'BOOLEAN')
    mod.object = Refractory
    mod.operation = 'DIFFERENCE'
    mod.solver = self.solver
    
    Shell.update_tag()
    Shell.select = True
    context.scene.update()
    
    #don't add multiple boolean modifiers
    shell_data = Shell.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
    Shell.modifiers.clear()
    old_data = Shell.data

    Shell.modifiers.clear()
    Shell.data = shell_data
    bpy.data.meshes.remove(old_data)
    Shell.name = f_model
    
class D3DUAL_OT_finish_booleans(bpy.types.Operator):
    """Finish the Booleans, this will take a while!"""
    bl_idname = "d3dual.finish_booleans"
    bl_label = "Finalize all Appliances"
    bl_options = {'REGISTER', 'UNDO'}
    
    solver = EnumProperty(
        description="Boolean Method",
        items=(("BMESH", "Bmesh", "Faster/More Errors"),
               ("CARVE", "Carve", "Slower/Less Errors"),
               ("VOLUME", "Volume", "No Errors, medium speed")),
        default = "VOLUME")
  
    resolution = bpy.props.FloatProperty(default = .175, min = .1, max = .5)
    
    jaw_mode = bpy.props.EnumProperty(default = 'MAX', items = (('MAX','MAX','MAX'),('MAND','MAND','MAND')))
    
    all_positions = bpy.props.BoolProperty(name = 'All Positions', default = False, description = 'Create a unique shell for all stored positions')
    
    
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    

    def invoke(self,context,event):
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        prefs = get_settings()
        #if not prefs.non_clinical_use:
        #    self.report({'ERROR'}, 'You must certify non-clinical use in your addon preferences or in the panel')
        #    return {'CANCELLED'}
        start = time.time()
        
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
        
        if self.all_positions:
            stored_positions = [ob.name for ob in bpy.data.objects if ob.get('stored_position')]
            for pos in stored_positions:    
                shells = [ob.name for ob in bpy.data.objects if self.jaw_mode in ob.name and pos in ob.name.split('_')]
                if len(shells) != 1: continue
                splint_shell = shells[0]
                
                print(shells[0])
                if self.jaw_mode == 'MAX': 
                    r_model = 'Max Refractory Model'
                    f_model = 'Final_Max' + '_' + pos
                else:
                    r_model = 'Mand Refractory Model'
                    f_model = 'Final_Mand'+ '_' + pos
                    
                bpy.ops.d3dual.jump_to_stored_position(position = pos)
                if self.solver != 'VOLUME':
                    finalize_routine_stored(self, context, splint_shell, r_model, f_model)
                else:
                    volume_routine_volume(self, context, splint_shell, r_model, f_model)
        else:        
            if self.jaw_mode == 'MAX':
                splint_shell = 'Splint Shell_MAX'
                r_model = 'Max Refractory Model'
                f_model = 'Final_Max'
    
                
            else:
                splint_shell = 'Splint Shell_MAND'
                r_model = 'Mand Refractory Model'
                f_model = 'Final_Mand'
           
        
            if self.solver != 'VOLUME':
                finalize_routine(self, context, splint_shell, r_model, f_model)
            else:
                volume_routine_volume(self, context, splint_shell, r_model, f_model)
        
        #tracking.trackUsage("D3DUAL:Finalize {}".format(self.jaw_mode),(self.solver, str(completion_time)[0:4]))
        
        #tmodel = bpy.data.objects.get(t_mo)
        #make sure user can verify no intersections
        #if tmodel:
        #    tmodel.hide = False
        context.space_data.show_textured_solid = False
        completion_time = time.time() - start
        print('competed all %s boolean operations in %f seconds' % (self.jaw_mode, completion_time))  
        if self.jaw_mode == 'MAX':
            splint.finalize_splint_max = True
        else:
            splint.finalize_splint_mand = True
            
        splint.end_time = time.time()
        return {'FINISHED'}
    
class D3DUAL_OT_finish_as_monoblock(bpy.types.Operator):
    """Finish the Booleans, this will take a while!"""
    bl_idname = "d3dual.finish_booleans_monoblock"
    bl_label = "Finish as Monoblock Appliance"
    bl_options = {'REGISTER', 'UNDO'}
    


    resolution = bpy.props.FloatProperty(name = 'Detail Level', min = .1, max = .5, default = .175, description  = 'Smaller numbers = higher precision and slower calc time')
    all_positions = bpy.props.BoolProperty(name = 'All Positions', default = False, description = 'Create a unique shell for all stored positions')
    
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    
    def invoke(self,context,event):
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        prefs = get_settings()
        #if not prefs.non_clinical_use:
        #    self.report({'ERROR'}, 'You must certify non-clinical use in your addon preferences or in the panel')
        #    return {'CANCELLED'}
        start = time.time()
        
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
        
        if self.all_positions:
            self.report({'ERROR'}, "Multi positions not supported in moboblock yet")
            return {'CANCELLED'}
            stored_positions = [ob.name for ob in bpy.data.objects if ob.get('stored_position')]
            for pos in stored_positions:    
                shells = [ob.name for ob in bpy.data.objects if self.jaw_mode in ob.name and pos in ob.name.split('_')]
                if len(shells) != 1: continue
                splint_shell = shells[0]
                
                print(shells[0])
                if self.jaw_mode == 'MAX': 
                    r_model = 'Max Refractory Model'
                    f_model = 'Final_Max' + '_' + pos
                else:
                    r_model = 'Mand Refractory Model'
                    f_model = 'Final_Mand'+ '_' + pos
                    
                bpy.ops.d3dual.jump_to_stored_position(position = pos)
                finalize_routine_stored(self, context, splint_shell, r_model, f_model)
                
        else:        
        
            splint_shell1 = 'Splint Shell_MAX'
            r_model1 = 'Max Refractory Model'
        
            splint_shell2 = 'Splint Shell_MAND'
            r_model2 = 'Mand Refractory Model'
            
            Shell1 = bpy.data.objects.get(splint_shell1)
            Shell2 = bpy.data.objects.get(splint_shell2)
            Refractory1 = bpy.data.objects.get(r_model1)
            Refractory2 = bpy.data.objects.get(r_model2)
            
            volume_final_monoblock(context, Shell1, Shell2, Refractory1, Refractory2)
            

        context.space_data.show_textured_solid = False
        completion_time = time.time() - start
        print('competed all boolean operations in %f seconds' % completion_time) 
        splint.finalize_splint_max = True
        splint.finalize_splint_mand = True    
        splint.end_time = time.time()
        return {'FINISHED'}
    
    
class D3DUAL_OT_re_finalize_selected(bpy.types.Operator):
    """Re-Finalize a selected final shell """
    bl_idname = "d3dual.re_finalize_selected_shell"
    bl_label = "Re-Finalize Selected Shell"
    bl_options = {'REGISTER', 'UNDO'}
    
    solver = EnumProperty(
        description="Boolean Method",
        items=(("BMESH", "Bmesh", "Faster/More Errors"),
               ("CARVE", "Carve", "Slower/Less Errors")),
        default = "BMESH")
  
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    

    def invoke(self,context,event):
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        prefs = get_settings()
        #if not prefs.non_clinical_use:
        #    self.report({'ERROR'}, 'You must certify non-clinical use in your addon preferences or in the panel')
        #    return {'CANCELLED'}
        start = time.time()
        
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
        
        
        stored_positions = [ob.name for ob in bpy.data.objects if ob.get('stored_position')]
        shell = context.object
        
        
        shell_name_info = shell.name.split('_')
        if 'MAX' in shell_name_info:
            r_model = 'Max Refractory Model'
        else:
            r_model = 'Mand Refractory Model'
            
            
        for pos in stored_positions: 
            
            if pos in shell.name.split('_'):  
                bpy.ops.d3dual.jump_to_stored_position(position = pos)
                    
                break
            
                
        #get the original shell data
        #send it back in
        #remesh it
        #re-boolean it
        
        
        return {'FINISHED'}
 
# ############################################################
# Registration
# ############################################################

def register():
    bpy.utils.register_class(D3DUAL_OT_finish_booleans)
    bpy.utils.register_class(D3DUAL_OT_finish_as_monoblock)


def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_finish_booleans)
    bpy.utils.unregister_class(D3DUAL_OT_finish_as_monoblock)

# ---- Perplexity API Suggested Migrations ----
In **Blender 4.4**, property definitions must use the new-style annotation syntax with type hints and assignment to class attributes, not direct assignment to variables. The old `bpy.props.*Property` assignment outside of a class is deprecated. Here is the corrected code block for defining these properties in a Blender 4.4-compatible way, assuming they are part of a class (e.g., a PropertyGroup or Operator):

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    resolution: bpy.props.FloatProperty(
        name="Detail Level",
        min=0.1,
        max=0.5,
        default=0.175,
        description="Smaller numbers = higher precision and slower calc time"
    )
    jaw_mode: bpy.props.EnumProperty(
        name="Jaw Mode",
        default='MAX',
        items=[
            ('MAX', 'MAX', 'MAX'),
            ('MAND', 'MAND', 'MAND')
        ]
    )
    all_positions: bpy.props.BoolProperty(
        name="All Positions",
        default=False,
        description="Create a unique shell for all stored positions"
    )
```

**Key changes:**
- Use **type annotations** (`:`) and assign to class attributes inside a class derived from `bpy.types.PropertyGroup` or similar.
- Do not assign properties to variables at the module level.
- Use only one definition per property name within the class.

This is the required approach for Blender 2.80+ and is fully compatible with Blender 4.4[2][4].
