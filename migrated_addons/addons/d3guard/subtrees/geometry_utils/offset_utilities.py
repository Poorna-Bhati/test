'''
Created on Mar 21, 2019

@author: Patrick

https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python

'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import random
import string
import math

from ...subtrees.bmesh_utils.bmesh_utilities_common import bmesh_loose_parts, new_bmesh_from_bmelements
from mathutils.bvhtree import BVHTree

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    '''
    because metaball objects will interact with others if the first part
    of the obejct name is the same, important to generate a non overlapping
    metabll obejct name
    '''
    return ''.join(random.choice(chars) for _ in range(size))

    
def find_inner_outer_shell(bme, bvh = None, delete_small = False, min_count = 100, test_size = 50, epsilon = .0001):
    '''
    for double shells, will return the faces of inner and outer
    shells.
    
    Ignores loose edges and verts
    
    if delete_small, will delete islands with less than min_count faces
    '''
    
    
    #first, determine how many loose parts there are
    islands = bmesh_loose_parts(bme, selected_faces = None, max_iters = 5000)
    if len(islands) == 0:
        return set(), set()
    if len(islands) == 1:
        return set(), islands[0]
    
    if len(islands) == 2:
        #assuming constant mesh density 
        inner = min(islands, key = len)
        outer = max(islands, key = len)
        return inner, outer
    
    inner_islands = set()
    outer_islands = set()
    to_del = set()
    if bvh == None:
        bvh = BVHTree.FromBMesh(bme)
            
    for isl in islands:
        if len(isl) < min_count:
            to_del.update(isl)
            print('small island')

        n_faces = 0
        test_faces = []
        for f in isl:
            test_faces += [f]
            n_faces += 1
            if n_faces >= test_size: break
        
        free_faces = 0
        self_faces = 0
        other_faces = 0
        for f in test_faces:
            v = f.calc_center_bounds() + epsilon * f.normal
            loc, no, ind, d = bvh.ray_cast(v, f.normal)
            if not loc:
                free_faces += 1
            else:
                found = bme.faces[ind]
                if found in isl:
                    self_faces += 1
                else:
                    other_faces += 1
        
        if free_faces == 0:
            inner_islands.update(isl)
        else:
            outer_islands.update(isl)
            
        print('This island has %i free,  %i self, and %i other faces' % (free_faces, self_faces, other_faces))
           
    return inner_islands, outer_islands




def find_inner_outer_wrt_other(bme, bvh, search_distance, border_angle_threshold =  45, epsilon = .0001):
    '''
    for a single shell that was created from a non closed surface scaffold
    ray casts thes source BVH to check if it finds a face normal pointed toward or away from it
    
    bme - the offset bmesh
    bvh - the 2d surface bvh
    search_distance - the max distance to search for a ray cast. Should be double the original offset
    
    border_threshold = angle in degrees beyond which is considered the border min 1, max 90
    
    '''
    
    
    #first, determine how many loose parts there are
    
    
    inner_faces = set()
    outer_faces = set()
    border_faces = set()
    
    #checks the parallness of the faces
    theta_threshold = math.cos(math.pi * border_angle_threshold / 180)
    
    for f in bme.faces:
        v = f.calc_center_bounds() - epsilon * f.normal  #move the point just inside of the existing mesh
        loc, no, ind, d = bvh.ray_cast(v, -1 * f.normal)
        if not loc:
            border_faces.add(f)
            continue
        
        #usually an oblique shot from the border
        if d > search_distance:
            border_faces.add(f)
            continue
        
        if no.dot(f.normal) > theta_threshold:
            outer_faces.add(f)
        
        elif no.dot(f.normal) < -theta_threshold:
            inner_faces.add(f)
            
        else:
            border_faces.add(f)
            
  
    return inner_faces, outer_faces, border_faces



def dyntopo_remesh(ob, dyntopo_resolution):
    #TODO, may try context override!
    '''
    uses dynamic topology detail flood fill
    to homogenize and triangulate a mesh object
    it is destructive
    '''
    c = bpy.context.copy()
    
    bpy.context.scene.objects.active = ob
    sel_state = ob.select
    
    ob.select = True
    
    bpy.ops.object.mode_set(mode = 'SCULPT')
    if not ob.use_dynamic_topology_sculpting:
        bpy.ops.sculpt.dynamic_topology_toggle()
    
    #save these settings to put them back as they were  
    detail_type = bpy.context.scene.tool_settings.sculpt.detail_type_method
    detail_res = bpy.context.scene.tool_settings.sculpt.constant_detail_resolution
    
    bpy.context.scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
    bpy.context.scene.tool_settings.sculpt.constant_detail_resolution = dyntopo_resolution
    bpy.ops.sculpt.detail_flood_fill()
    
    #put the settings back
    bpy.context.scene.tool_settings.sculpt.detail_type_method = detail_type
    bpy.context.scene.tool_settings.sculpt.constant_detail_resolution = detail_res
    
    #put the context back
    bpy.ops.object.mode_set(mode = c['mode'])
    bpy.context.scene.objects.active = c['object']
    ob.select = sel_state
    
def create_dyntopo_meta_scaffold(ob, dyntopo_resolution, return_type = 'OBJECT'):
    '''
    ob - Blender Object
    dynotopo_resolution - float 0.1 to 6.0  inverse of target edge lenght.  Higher Values = more dense mesh
    return_type = enum in 'OBJECT', - returns new object linked to scene
                          'MESH' - return Mesh data with no object linked to scene
                          'BMESH' - return bmesh with no temp object or mesh in D.objects or D.meshes
    '''
    context_copy = bpy.context.copy()
    
    #make a new copy
    me = ob.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
    tmp_ob = bpy.data.objects.new('mb_scaf' + ob.name[0:6], me)
    bpy.context.scene.objects.link(tmp_ob)
    tmp_ob.matrix_world = ob.matrix_world
    
    #remesh it using dynamic topology
    dyntopo_remesh(tmp_ob, dyntopo_resolution)
        
    #return the appropriate data type
    if return_type == 'OBJECT':
        return tmp_ob
    
    elif return_type == 'MESH':
        bpy.context.scene.objects.unlink(tmp_ob)
        bpy.data.objects.remove(tmp_ob)
        return tmp_ob.data
    
    else:
        bme = bmesh.new()
        me_data = tmp_ob.data
        bme.from_mesh(me_data)
        #hard delete
        bpy.context.scene.objects.unlink(tmp_ob)
        bpy.data.objects.remove(tmp_ob)
        bpy.data.meshes.remove(me_data)
        
        return bme
     
def simple_metaball_offset(scaffold, meta_radius, meta_resolution):
    '''
    scaffold - can be Mesh or BMEsh object
    simply adds a metaball at every vertex, converts to mesh, and returns
    the inner and outer representation
    
    return dict with keys
    geom{inner: bme_inner, outer:bme_outer}
    
    '''
    
    assert meta_radius > 0.1
    assert meta_resolution > 0.01
    
    #prepare a metaball object
    name = id_generator() + '_mb'
    mb_data = bpy.data.metaballs.new(name)
    mb_ob = bpy.data.objects.new(name, mb_data)
    mb_data.resolution = meta_resolution
    mb_data.render_resolution = meta_resolution
    bpy.context.scene.objects.link(mb_ob)
    
    if isinstance(scaffold, bpy.types.Mesh):
        vs = getattr(scaffold, 'vertices')
        
    elif isinstance(scaffold, bmesh.types.BMesh):
        vs = getattr(scaffold, 'verts')
         
    for v in vs:
        mb = mb_data.elements.new(type = 'BALL')
        mb.co = v.co
        mb.radius = meta_radius
        
    bpy.context.scene.update()  #calculates the metaball
    mb_me = mb_ob.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
    
    offset_bme = bmesh.new()
    offset_bme.from_mesh(mb_me)
    offset_bme.verts.ensure_lookup_table()
    offset_bme.edges.ensure_lookup_table()
    offset_bme.faces.ensure_lookup_table()
    
    print('There are %i verts in the bmesh' % len(offset_bme.verts))
          
    inner_fs, outer_fs = find_inner_outer_shell(offset_bme)
    
    if len(inner_fs):
        bme_inner = new_bmesh_from_bmelements(inner_fs)
    else:
        bme_inner = None
        
    if len(outer_fs):
        bme_outer = new_bmesh_from_bmelements(outer_fs)
    else:
        bme_outer = None

    #cleanup the various temp objects
    offset_bme.free()
    bpy.context.scene.objects.unlink(mb_ob)
    bpy.data.objects.remove(mb_ob)
    bpy.data.metaballs.remove(mb_data)
    
    
    gdict = {}
    gdict['inner'] = bme_inner
    gdict['outer'] = bme_outer
    return gdict
      
def metaball_pre_offset(scaffold, meta_radius, meta_resolution, pre_offset):
    '''
    allows thinner offsets with larger particles by offsetting
    the surface with a simple normal  offset
    '''
    
    
    assert meta_radius > 0.001
    assert meta_resolution > 0.01
    
    #prepare a metaball object
    name = id_generator() + '_mb'
    mb_data = bpy.data.metaballs.new(name)
    mb_ob = bpy.data.objects.new(name, mb_data)
    mb_data.resolution = meta_resolution
    mb_data.render_resolution = meta_resolution
    bpy.context.scene.objects.link(mb_ob)
    
    if isinstance(scaffold, bpy.types.Mesh):
        vs = getattr(scaffold, 'vertices')
        def get_normal(v):
            return v.normal
        
    elif isinstance(scaffold, bmesh.types.BMesh):
        vs = getattr(scaffold, 'verts')
        def get_normal(v):
            return v.normal
        
    for v in vs:
        mb = mb_data.elements.new(type = 'BALL')
        mb.co = v.co + pre_offset * get_normal(v)
        mb.radius = meta_radius
        
    bpy.context.scene.update()  #calculates the metaball
    mb_me = mb_ob.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
    
    offset_bme = bmesh.new()
    offset_bme.from_mesh(mb_me)
    offset_bme.verts.ensure_lookup_table()
    offset_bme.edges.ensure_lookup_table()
    offset_bme.faces.ensure_lookup_table()
    
    inner_fs, outer_fs = find_inner_outer_shell(offset_bme)
    
    #might be more efficient to keep one bmesh and delete
    #elements from it.
    if len(inner_fs):
        bme_inner = new_bmesh_from_bmelements(inner_fs)
    else:
        bme_inner = None
        
    if len(outer_fs):
        bme_outer = new_bmesh_from_bmelements(outer_fs)
    else:
        bme_outer = None
         
    #cleanup the various temp objects
    offset_bme.free()
    bpy.context.scene.objects.unlink(mb_ob)
    bpy.data.objects.remove(mb_ob)
    bpy.data.metaballs.remove(mb_data)
    bpy.data.meshes.remove(mb_me)
    
    gdict = {}
    gdict['inner'] = bme_inner
    gdict['outer'] = bme_outer
    return gdict

def create_offset_object(ob, radius, scaffold_density, meta_resolution, pre_offset = 0.0, shell = 'OUTER'):
    
    scaffold = create_dyntopo_meta_scaffold(ob, scaffold_density, return_type = 'BMESH')
    
    if abs(pre_offset) > 0.01:
        gdict = metaball_pre_offset(scaffold, radius, meta_resolution, pre_offset)
    else:
        gdict = simple_metaball_offset(scaffold, radius, meta_resolution)
        
    offset_me = bpy.data.meshes.new(ob.name + '_offset')
    offset_ob = bpy.data.objects.new(ob.name + '_offset', offset_me)
    
    bme_o = gdict['outer']
    bme_i = gdict['inner']
    
    if shell == 'OUTER' and bme_o:
        bme_o.to_mesh(offset_me)
    elif shell == 'INNER' and bme_i:
        bme_i.to_mesh(offset_me)
    
    if bme_o:   
        bme_o.free()
    if bme_i:
        bme_i.free
    
    return offset_ob



def create_offset_object_from_open_surface(ob, radius, scaffold_density, meta_resolution, pre_offset = 0.0):
    
    bme_check = bmesh.new()
    bme_check.from_mesh(ob.data)
    bme_check.verts.ensure_lookup_table()
    bme_check.faces.ensure_lookup_table()
    bme_check.edges.ensure_lookup_table()
    bvh_check = BVHTree.FromBMesh(bme_check)
    
    scaffold = create_dyntopo_meta_scaffold(ob, scaffold_density, return_type = 'BMESH')
    
    if abs(pre_offset) > 0.01:
        gdict = metaball_pre_offset(scaffold, radius, meta_resolution, pre_offset)
    else:
        gdict = simple_metaball_offset(scaffold, radius, meta_resolution)
        
    offset_me_i = bpy.data.meshes.new(ob.name + '_offset_inner')
    offset_ob_i = bpy.data.objects.new(ob.name + '_offset_inner', offset_me_i)
    
    
    offset_me_o = bpy.data.meshes.new(ob.name + '_offset_outer')
    offset_ob_o = bpy.data.objects.new(ob.name + '_offset_outer', offset_me_o)
    
    offset_me_b = bpy.data.meshes.new(ob.name + '_offset_border')
    offset_ob_b = bpy.data.objects.new(ob.name + '_offset_border', offset_me_b)
    
    
    #for 2d object there is only one!
    bme_o = gdict['outer']
    bme_i = gdict['inner']
    
    bme_o.normal_update()  #check if it's normals
    inner_fs, outer_fs, border_fs = find_inner_outer_wrt_other(bme_o, 
                                                               bvh_check, 
                                                               2 * radius, 
                                                               border_angle_threshold =  75, 
                                                               epsilon = .0001)
    
    

    
    bme_inner = new_bmesh_from_bmelements(inner_fs)
    bme_outer = new_bmesh_from_bmelements(outer_fs)
    bme_border = new_bmesh_from_bmelements(border_fs)
    
    
    bme_inner.to_mesh(offset_me_i)
    bme_outer.to_mesh(offset_me_o)
    bme_border.to_mesh(offset_me_b)
    
    bme_inner.free()
    bme_outer.free()
    bme_border.free()
    bme_o.free()
    if bme_i:
        bme_i.free()
    
    return offset_ob_i, offset_ob_o, offset_ob_b

class D3MODEL_OT_medium_metaball_offset(bpy.types.Operator):
    """Add uniform layer to mesh object"""
    bl_idname = "d3model.medium_offset"
    bl_label = "Metaball Offset 0.3 to 2.0mm"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    
    radius = bpy.props.FloatProperty(name = 'Offset', default = 0.5, description = 'Lateral offset from the  base', min = 0.3, max = 2.0)
    
    scaffold_density = bpy.props.FloatProperty(name = 'Scaffold Density', default = 3.0, description = 'density of metaball placement', min = 1.0, max = 7.0)
    meta_resolution = bpy.props.FloatProperty(name = 'Remesh Resolution', default = 0.5, description = 'Smaller is more detail and slower', min = 0.05, max = 1.0)
    pre_offset = bpy.props.FloatProperty(name = 'Pre Offset', default = 0.0, description = 'pre-offsetting the surface can allow for smaller offsets without using high resolution', min = -1.0, max = 1.0)
    
    
    @classmethod
    def poll(cls, context):
        if context.mode == "OBJECT" and context.object != None and context.object.type == 'MESH':
            return True
        else:
            return False
        
    def execute(self, context):
        
        ob = context.object
        ob_off = create_offset_object(ob, self.radius, self.scaffold_density, self.meta_resolution, pre_offset = self.pre_offset, shell = 'OUTER')
        
        context.scene.objects.link(ob_off)
        ob_off.matrix_world = ob.matrix_world
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_props_dialog(self)
    


class D3MODEL_OT_medium_metaball_offset_open(bpy.types.Operator):
    """Add uniform layer to open mesh object"""
    bl_idname = "d3model.open_medium_offset"
    bl_label = "Open Metaball Offset 0.3 to 2.0mm"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    
    radius = bpy.props.FloatProperty(name = 'Offset', default = 0.5, description = 'Lateral offset from the  base', min = 0.3, max = 2.0)
    
    scaffold_density = bpy.props.FloatProperty(name = 'Scaffold Density', default = 3.0, description = 'density of metaball placement', min = 1.0, max = 7.0)
    meta_resolution = bpy.props.FloatProperty(name = 'Remesh Resolution', default = 0.5, description = 'Smaller is more detail and slower', min = 0.05, max = 1.0)
    #pre_offset = bpy.props.FloatProperty(name = 'Pre Offset', default = 0.0, description = 'pre-offsetting the surface can allow for smaller offsets without using high resolution', min = -1.0, max = 1.0)
    
    
    @classmethod
    def poll(cls, context):
        if context.mode == "OBJECT" and context.object != None and context.object.type == 'MESH':
            return True
        else:
            return False
        
    def execute(self, context):
        
        ob = context.object
        ob_off1, ob_off2, ob_off3  = create_offset_object_from_open_surface(ob, self.radius, self.scaffold_density, self.meta_resolution, pre_offset = 0.0)
        context.scene.objects.link(ob_off1)
        context.scene.objects.link(ob_off2)
        context.scene.objects.link(ob_off3)
        ob_off1.matrix_world = ob.matrix_world
        ob_off2.matrix_world = ob.matrix_world
        ob_off3.matrix_world = ob.matrix_world
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_props_dialog(self)    
def register():
    bpy.utils.register_class(D3MODEL_OT_medium_metaball_offset)
    bpy.utils.register_class(D3MODEL_OT_medium_metaball_offset_open)
    
def unregister():
    bpy.utils.unregister_class(D3MODEL_OT_medium_metaball_offset)
    bpy.utils.unregister_class(D3MODEL_OT_medium_metaball_offset_open)

# ---- Perplexity API Suggested Migrations ----
In Blender 4.4, property definitions using bpy.props (such as FloatProperty) must be assigned as class attributes within a class derived from bpy.types.PropertyGroup, Operator, Panel, etc., not as standalone variables. Here is the corrected code block for Blender 4.4+:

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    radius: bpy.props.FloatProperty(
        name='Offset',
        default=0.5,
        description='Lateral offset from the base',
        min=0.3,
        max=2.0
    )
    scaffold_density: bpy.props.FloatProperty(
        name='Scaffold Density',
        default=3.0,
        description='density of metaball placement',
        min=1.0,
        max=7.0
    )
    meta_resolution: bpy.props.FloatProperty(
        name='Remesh Resolution',
        default=0.5,
        description='Smaller is more detail and slower',
        min=0.05,
        max=1.0
    )
    pre_offset: bpy.props.FloatProperty(
        name='Pre Offset',
        default=0.0,
        description='pre-offsetting the surface can allow for smaller offsets without using high resolution',
        min=-1.0,
        max=1.0
    )
```

To use these properties, register the PropertyGroup and assign it to a data block (e.g., Scene):

```python
def register():
    bpy.utils.register_class(MyProperties)
    bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyProperties)

def unregister():
    del bpy.types.Scene.my_props
    bpy.utils.unregister_class(MyProperties)
```

This approach is fully compatible with Blender 4.4 and avoids deprecated API usage[4].
