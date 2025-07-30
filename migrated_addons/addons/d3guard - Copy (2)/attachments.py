#python imports
from os.path import join, dirname, abspath, exists, isfile
from os import walk, listdir
from common_utilities import get_settings


#blender imports
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix

from common_utilities import  showErrorMessage
#https://devtalk.blender.org/t/can-bpy-props-be-used-for-dynamic-lists/10130/12
from subtrees.metaballs.vdb_remesh import convert_vdb, read_bmesh
from subtrees.bmesh_utils.bmesh_utilities_common import bmesh_join_list
from subtrees.geometry_utils.transformations import r_matrix_from_principal_axes
_enum_libraries = []
_enum_attachments = []

last_lib = None
cached_attachments = None


def enum_attachment_libraries(self, context):
    
    
    custom_assets_path = get_settings().attachment_library_path
    assets_path = join(dirname(abspath(__file__)), "data_assets","attachments")
    
    
    _enum_libraries.clear()
    blendfiles = [f for f in listdir(assets_path) if isfile(join(assets_path, f)) and  f.endswith('.blend')]

    custom_blend_files = []
    if custom_assets_path != '' and custom_assets_path != assets_path:
        custom_blend_files += [f for f in listdir(custom_assets_path) if isfile(join(custom_assets_path, f)) and  f.endswith('.blend')]
        
        
    for bf in blendfiles:
        _enum_libraries.append((join(assets_path, bf), bf,  ""))
   
    for bf in custom_blend_files:
        _enum_libraries.append((join(custom_assets_path, bf), bf,  ""))         
    return _enum_libraries


def enum_attachment_objects(self, context):
    """Populate Objects List from Parts Library.
    Creates list of objects that optionally have search string contained in them
    to populate variable pdt_lib_objects enumerator.
    Args:
        context: Blender bpy.context instance.
    Returns:
        list of Object Names.
    """

    prefs = get_settings()
    
    file_path = prefs.attachment_lib
    
    global cached_attachments
    
    #print(file_path)
    #print(isfile(file_path))
    
    if isfile(file_path) and file_path.endswith(".blend"):
        global last_lib
        if file_path == last_lib:  #don't re-load the file to read the obj names!
            #print('skipping update')
            #print(cached_attachments)
            return cached_attachments
        _enum_attachments.clear()    
        with bpy.data.libraries.load(str(file_path)) as (data_from, data_to):
            object_names = [obj for obj in data_from.objects if "_d3attach" in obj]
        for object_name in object_names:
            _enum_attachments.append((object_name, object_name.split("_")[0], ""))
            
        last_lib = file_path
        cached_attachments = _enum_attachments
    else:
        _enum_attachments.clear()
        _enum_attachments.append(("MISSING", "Library is Missing", ""))
        
    return _enum_attachments



#custom addon imports

def compnent_ob(ob):
    ob['d3d_a_type'] = 'component'
    ob['target'] = 'NONE'
    ob['csg_number'] = -1
    ob['csg_op'] = 'UNION'
    ob['visible'] = 'TRUE'

def container_ob(ob):
    
    ob['d3d_a_type'] = 'container'
    ob['target'] = 'NONE'
    
    ob['csg_number'] = -1
    ob['csg_op'] = 'NONE'
    
    ob['snap_target'] = 'NONE'
    ob['snap_source'] = 'NORMAL'
    
    ob['visible'] = 'TRUE'


def simple_attachment_ob(ob):
    
    ob['d3d_a_type'] = 'simple_attachment'
    ob['target'] = 'MAX'
    
    ob['csg_number'] = 0
    ob['csg_op'] = 'UNION'
    
    ob['snap_target'] = 'NONE'
    ob['snap_source'] = 'NORMAL'
    
    ob['visible'] = 'TRUE'
    
    
#structure for linking an attachment from library
def link_attachment_from_library(context):

    prefs = get_settings()
    file_path = prefs.attachment_lib
    attach_obj = prefs.attachment_ob

    if isfile(file_path) and file_path.endswith(".blend"):
        with bpy.data.libraries.load(str(file_path)) as (data_from, data_to):
            
            attachment_names = [obj for obj in data_from.objects if "_d3attach" in obj]
            if len(attachment_names) > 1:  #means a file with many simple attachemnts
                object_names = [obj for obj in attachment_names if attach_obj in obj] #filter out just the selected on
                print("simple attachment")
            else: #file with compelx attachment
                object_names = [obj for obj in data_from.objects if "_d3attach" in obj or "_d3comp" in obj]
                print('compplex attachment')
            
            print(object_names)
            data_to.objects = object_names
    
    for ob in data_to.objects:
        if ob.name not in context.scene.objects:
            context.scene.objects.link(ob)
            
            if not ob.get('visible'):
                if ob.hide:
                    ob['visible'] = 'FALSE'
                else:
                    ob['visible'] = 'TRUE'
                
    
    return data_to.objects   

def validate_complex_attachment(ob):
    #check for all the properties
    return True
    
def validate_simple_attachment(ob):
    #check all the properties
    return True
    
def validate_component(ob):
    #check all properties
    return True
    
    
def pretty_print_stack(csg_stack):
    print('WORKING ON IT')
    return


def csg_layer():
    layer = {}
    layer['UNION'] = []
    layer['DIFFERENCE'] = []
    
    return layer


def apply_stack(stack, target_ob, prefix = '', suffix = '', make_new = False, mode = 'BOOLEAN', voxel_size = .15):
    
    if target_ob == None: return
    
    target_ob.modifiers.clear()
    
    if prefix == '':
        prefix = target_ob.mame[0:3]
    
    
    if mode == 'VOLUME':
        bme_base = bmesh.new()
        bme_base.from_mesh(target_ob.data)
        bme_base.transform(target_ob.matrix_world) #all in world coordiantes
       
        ngons = [f for f in bme_base.faces if len(f.verts) > 4]
        if len(ngons):
            bmesh.ops.poke(bme_base, faces = ngons)
            
            
        quads = [f for f in bme_base.faces if len(f.verts) == 4]
        if len(quads):
            bmesh.ops.triangulate(bme_base, faces=quads)
        
        
        
        verts, tris, quads = read_bmesh(bme_base)
        vdb_base = convert_vdb(verts, tris, quads, voxel_size)
        
        vdbs = []
        

        
    for i in range(0, len(stack)):
        if i not in stack:
            print('nothing in   in this layer')
            continue
        layer =  stack[i]
        u_obs = layer['UNION']
        d_obs = layer['DIFFERENCE']
    
        print(layer['UNION'])
        print(layer['DIFFERENCE'])
    
        if len(u_obs):
            bme_u = bmesh.new()
            for ob in u_obs:
                ob.hide = True
                N = len(bme_u.verts)
                bme_u.from_object(ob, bpy.context.scene)
                for v in bme_u.verts[N:]:
                    v.co = ob.matrix_world * v.co
                
            
                bme_u.verts.ensure_lookup_table()
                bme_u.edges.ensure_lookup_table()
                bme_u.faces.ensure_lookup_table()
            
            if mode == 'BOOLEAN':
                me = bpy.data.meshes.new(prefix + '_union_' + str(i))
                ob  = bpy.data.objects.new(prefix +'_union_' + str(i), me)
                bpy.context.scene.objects.link(ob)
                ob.hide = True
            
                bme_u.to_mesh(me)
                bme_u.free()
            
                mod = target_ob.modifiers.new('Boolean', type = 'BOOLEAN')
                mod.operation = 'UNION'
                mod.object = ob
            else:
                
                #better success with poked ngons but cocave ngons my have problems
                ngons = [f for f in bme_u.faces if len(f.verts) > 4]
                if len(ngons):
                    bmesh.ops.poke(bme_u, faces = ngons)
            
                quads = [f for f in bme_u.faces if len(f.verts) == 4]
                if len(quads):
                    bmesh.ops.triangulate(bme_u, faces=quads)
        
                

                verts, tris, quads = read_bmesh(bme_u)
                vdb = convert_vdb(verts, tris, quads, voxel_size)
                vdbs.append((vdb, 'UNION'))
                
                #test_me = bpy.data.meshes.new('Test Me')
                #test_ob = bpy.data.objects.new('Test Ob', test_me)
                #bpy.context.scene.objects.link(test_ob)
                #bme_u.to_mesh(test_me)
                bme_u.free()
                
        
        

        if len(d_obs):
            bme_d = bmesh.new()
            for ob in d_obs:
                ob.hide = True
                N = len(bme_d.verts)
                
                if ob.type != 'MESH':
                    me = ob.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
                    me.transform(ob.matrix_world)
                    bme_d.from_mesh(me)
                    bpy.data.meshes.remove(me)
                    
                else:
                    bme_d.from_object(ob, bpy.context.scene)
                    for v in bme_d.verts[N:]:  #TODO, bme.transform(ob.matrix_world)
                        v.co = ob.matrix_world * v.co
            
                bme_d.verts.ensure_lookup_table()
                bme_d.edges.ensure_lookup_table()
                bme_d.faces.ensure_lookup_table()
                
                
            if mode == 'BOOLEAN':    
                me = bpy.data.meshes.new(prefix + '_diff_' + str(i))
                ob  = bpy.data.objects.new(prefix + '_diff_' + str(i), me)
                bpy.context.scene.objects.link(ob)
                ob.hide = True
            
                bme_d.to_mesh(me)
                bme_d.free()
        
                mod = target_ob.modifiers.new('Boolean', type = 'BOOLEAN')
                mod.operation = 'DIFFERENCE'
                mod.object = ob
            
            else:
                
                ngons = [f for f in bme_d.faces if len(f.verts) > 4]
                if len(ngons):
                    bmesh.ops.poke(bme_d, faces = ngons)
            
                quads = [f for f in bme_d.faces if len(f.verts) == 4]
                if len(quads):
                    bmesh.ops.triangulate(bme_d, faces=quads)
                verts, tris, quads = read_bmesh(bme_d)
                vdb = convert_vdb(verts, tris, quads, voxel_size)
                vdbs.append((vdb, 'DIFFERENCE'))
                
                #test_me = bpy.data.meshes.new('Test Me')
                #test_ob = bpy.data.objects.new('Test Ob', test_me)
                #bpy.context.scene.objects.link(test_ob)
                #bme_d.to_mesh(test_me)
                
                bme_d.free()
        
    if mode == 'VOLUME':
        for (vdb_op, op) in vdbs:
            if op == 'UNION':
                vdb_base.union(vdb_op, False)
                
            elif op == 'DIFFERENCE':
                vdb_base.difference(vdb_op, False)
                 
        
        isosurface = 0.25  #self.iso
        adaptivity = 0.0  #self.adapt
        isosurface *= vdb_base.transform.voxelSize()[0]
        ve, tr, qu = vdb_base.convertToPolygons(isosurface, (adaptivity/100.0)**2)
        

        bm = bmesh.new()
        for co in ve.tolist():
            bm.verts.new(co)

        bm.verts.ensure_lookup_table()    
        bm.faces.ensure_lookup_table()    

        for face_indices in tr.tolist() + qu.tolist():
            bm.faces.new(tuple(bm.verts[index] for index in reversed(face_indices)))

        bm.normal_update()
        bm.transform(target_ob.matrix_world.inverted())
        
        if make_new:
            me = bpy.data.meshes.new(target_ob.name + '_' + suffix)
            ob = bpy.data.objects.new(target_ob.name + '_' +  suffix, me)
            bpy.context.scene.objects.link(ob)
            ob.matrix_world = target_ob.matrix_world
            bm.to_mesh(me)
        else:
            bm.to_mesh(target_ob.data)
    
        bm.free()
                 

def build_csg_stack():            
    #dictionary for upper and lower stacks
    csg_stack = {}
    
    #create the maxillary and mandibular stacks
    max_stack = {}
    mand_stack= {}
    
    #assigng them
    csg_stack['MAX'] = max_stack
    csg_stack['MAND'] = mand_stack
    
    #create the first layer
    max_stack[0] = csg_layer()
    mand_stack[0] = csg_layer()
    
    #all simple attachments go into layer 0
    simple_attachments = [ob for ob in bpy.data.objects if ob.get('d3d_a_type') != None and ob.get('d3d_a_type') == 'simple_attachment']
    
    #complex attachments build 
    complex_attachments = [ob for ob in bpy.data.objects if ob.get('d3d_a_type') != None and ob.get('d3d_a_type') == 'container']
    
    for A in complex_attachments:
        
        eles = []
        children = [ob for ob in A.children]
        
        iters = 0
        while len(children) and iters < 5:  #safety can't go deeper than 5 layers
            iters += 1
            eles += [ob for ob in children if ob.get('d3d_a_type') and ob.get('d3d_a_type') == 'component']
            
            new_children = []
            for ele in children:
                new_children.extend([ob for ob in ele.children])
                
            children = new_children   
                
        eles.sort(key = lambda x: x.get('csg_number'))
        for ob in eles:   
            if ob.get('target') not in {'MAX','MAND'}:continue
            n = ob.get('csg_number')
            if n == -1: continue
        
            stack = csg_stack[ob.get('target')] #get the upper or lower stack
        
            if n not in stack:
                stack[n] = csg_layer()  #add a new layerg
            
            layer = stack[n]
            layer[ob.get('csg_op')] += [ob]
    
    
    for ob in simple_attachments:
        if ob.get('target') not in {'MAX','MAND'}:continue
        n = ob.get('csg_number')
        if n == -1: continue
    
        stack = csg_stack[ob.get('target')] #get the upper or lower stack
    
        if n not in stack:
            stack[n] = csg_layer()  #add a new layer
        
        layer = stack[n]
        layer[ob.get('csg_op')] += [ob]
            
            
    print(len(csg_stack['MAX']))
    print(len(csg_stack['MAND']))
    
    print(csg_stack['MAND'])
    return csg_stack


def apply_csg_stack_to_shells(csg_stack, mode = 'BOOLEAN', jaw_mode = 'BOTH', suffix = '', make_new = False):
    
    
    if jaw_mode in {'BOTH', 'MAX'}:
        max_shell = bpy.data.objects.get('Splint Shell_MAX')
        if max_shell:
            apply_stack(csg_stack['MAX'], max_shell, mode = mode, prefix = 'MAX', suffix = suffix, make_new = make_new) 
    
    
    if jaw_mode in {'BOTH', 'MAND'}:
        mand_shell = bpy.data.objects.get('Splint Shell_MAND')        
        if mand_shell:
            apply_stack(csg_stack['MAND'], mand_shell, mode = mode, prefix = 'MAND', suffix = suffix, make_new = make_new)


class D3Dual_OT_hide_all_attachments(bpy.types.Operator):
    """Hide ALl attachments"""
    bl_idname = "d3dual.hide_all_attachments"
    bl_label = "Hide All Attachment"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        
        return True
   
    def execute(self, context):
        
        for ob in bpy.data.objects:
            print(ob.name)
            print(ob.get('d3d_a_type'))
            if ob.get('d3d_a_type') not in {'attachment', 'container', "component"}: continue
            ob.hide = True
            #else                                
        return {'FINISHED'} 
    
class D3Dual_OT_show_all_attachments(bpy.types.Operator):
    """Show all attachments"""
    bl_idname = "d3dual.show_all_attachments"
    bl_label = "Show Attachments"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return True
   
    def execute(self, context):
        for ob in bpy.data.objects:
            if ob.get('d3d_a_type') not in {'simple_attachment','attachment', 'container', "component"}: continue
                
            if ob.get('visible') == 'TRUE':
                ob.hide = False
            #else                
                        
        return {'FINISHED'} 
    
            
class D3Dual_OT_remove_attachment_element(bpy.types.Operator):
    """Remove selected attachment"""
    bl_idname = "d3dual.remove_attachment"
    bl_label = "Remove Attachment"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        
        if  not context.object: return False
        if context.object.get('d3d_a_type') not in {'attachment', 'container'}: return False
        
        return True
   
    def execute(self, context):
        
        A = context.object  #attachmen
        
        eles = []
        
        children = [ob for ob in A.children]
        
        iters = 0
        while len(children) and iters < 5:  #safety can't go deeper than 5 layers
            iters += 1
            eles += [ob for ob in children if ob.get('d3d_a_type') and ob.get('d3d_a_type') == 'component']
            
            new_children = []
            for ele in children:
                new_children.extend([ob for ob in ele.children])
                
            children = new_children  
        
        
        print(eles)
        for ob in eles + [A]:
            
            context.scene.objects.unlink(ob)
            data = ob.data
            bpy.data.objects.remove(ob)
            
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)
            elif isinstance(data, bpy.types.MetaBall):
                bpy.data.metaballs.remove(data)
                
                        
        return {'FINISHED'} 


class D3Dual_OT_snap_element_to_surface(bpy.types.Operator):
    """snap align the selected element to the mesh surface"""
    bl_idname = "d3dual.snap_attachment_to_surface"
    bl_label = "Snap Attachment to Surface"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    axis = bpy.props.EnumProperty(name = 'Axis', items = [('X','X','X'),('Y','Y','Y'),('Z','Z','Z'),('-X','-X','-X'),('-Y','-Y','-Y'),('-Z','-Z','-Z')], default = 'Z')
    @classmethod
    def poll(cls, context):
        
        if  not context.object: return False
        if context.object.get('d3d_a_type') not in {'simple_attachment', 'container'}: return False
        
        return True
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        ob = context.object  #attachmen
        loc = ob.matrix_world.to_translation()
        
        if ob.get('snap_target') == 'MAX':
            Shell = bpy.data.objects.get("Splint Shell_MAX")
        else:
            Shell = bpy.data.objects.get("Splint Shell_MAND") 
            
        mx = Shell.matrix_world
        imx = mx.inverted()
        mx_norm = imx.transposed().to_3x3() #local directions to global
        imx_norm = imx.to_3x3()
        
        _, snap_loc, no, ind = Shell.closest_point_on_mesh(imx * loc)
        no_world = mx_norm * no
        no_world.normalize()
        
        if self.axis == 'X':
            X = no_world  #establish that the X axis aligns with the surface
            world_Y = Vector((0,1,0))
            #pick any direction (in this case world Y) and remove any parallel component
            #to the surface normal
            Y = world_Y - world_Y.dot(X) *X
            Y.normalize()
        
            Z = X.cross(Y)
            Z.normalize()

        if self.axis == 'Y':
            Y = no_world  #establish that the X axis aligns with the surface
            world_X = Vector((1,0,0))
            #pick any direction (in this case world Y) and remove any parallel component
            #to the surface normal
            X = world_X - world_X.dot(Y) *Y
            Y.normalize()
        
            Z = X.cross(Y)
            Z.normalize()

        if self.axis == 'Z':
            Z = no_world  #establish that the X axis aligns with the surface
            world_X = Vector((1,0,0))
            #pick any direction (in this case world Y) and remove any parallel component
            #to the surface normal
            X = world_X - world_X.dot(Z) *Z
            X.normalize()
        
            Y = X.cross(Z)
            Y.normalize()
        
        if self.axis == '-X':
            X = -no_world  #establish that the X axis aligns with the surface
            world_Y = Vector((0,1,0))
            #pick any direction (in this case world Y) and remove any parallel component
            #to the surface normal
            Y = world_Y - world_Y.dot(X) *X
            Y.normalize()
        
            Z = X.cross(Y)
            Z.normalize()

        if self.axis == '-Y':
            Y = -no_world  #establish that the X axis aligns with the surface
            world_X = Vector((1,0,0))
            #pick any direction (in this case world Y) and remove any parallel component
            #to the surface normal
            X = world_X - world_X.dot(Y) *Y
            Y.normalize()
        
            Z = X.cross(Y)
            Z.normalize()

        if self.axis == '-Z':
            Z = -no_world  #establish that the X axis aligns with the surface
            world_X = Vector((1,0,0))
            #pick any direction (in this case world Y) and remove any parallel component
            #to the surface normal
            X = world_X - world_X.dot(Z) *Z
            X.normalize()
        
            Y = X.cross(Z)
            Y.normalize()
            
            
                
        rmx = r_matrix_from_principal_axes(X,Y,Z)
        rmx = rmx.to_4x4()
        
        tmx = Matrix.Translation(mx * snap_loc)
        ob.matrix_world = tmx * rmx
        
        
                           
        return {'FINISHED'} 

class D3Dual_OT_place_attachment_element(bpy.types.Operator):
    """Place an attachment located at the 3D cursor"""
    bl_idname = "d3dual.place_attachment"
    bl_label = "Place Attachment"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        
        return True
   
    def execute(self, context):
        
        obs = link_attachment_from_library(context)   
        
        for ob in bpy.data.objects:
            ob.select = False
            
        for ob in obs:
            if "d3attach" in ob.name:
                ob.location = context.scene.cursor_location
                context.scene.objects.active = ob
                ob.select = True
        
        context.space_data.show_manipulator = True
        context.space_data.transform_manipulators = {'TRANSLATE', 'ROTATE'}
        context.space_data.transform_orientation = 'LOCAL'
                    
        return {'FINISHED'}    

class D3Dual_OT_csg_attachment_elements(bpy.types.Operator):
    """Perform all CSG Operations"""
    bl_idname = "d3dual.csg_attachment_elements"
    bl_label = "Merge/Subtract Attachments"
    bl_options = {'REGISTER', 'UNDO'}
    
    mode = bpy.props.EnumProperty(name = 'Merge Mode', items = [('BOOLEAN', 'BOOLEAN', 'BOOLEAN'), ('VOLUME', 'VOLUME', 'VOLUME')], default = 'VOLUME')
    v_res = bpy.props.FloatProperty(name = 'Voxel Size', min = .1, max = .3, default = .15)
    optimize = bpy.props.BoolProperty(name = 'Decimate', default = True)
    jaw_mode = bpy.props.EnumProperty(name = 'Merge Mode', items = [('MAX', 'MAX', 'MAX'), ('MAND', 'MAND', 'MAND'), ('BOTH','BOTH','BOTH')], default = 'BOTH')
    
    all_positions = bpy.props.BoolProperty(name = 'All Positions', default = True, description = 'Create a unique shell for all stored positions')
    
    @classmethod
    def poll(cls, context):
        
        return True
   
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300) 
    
    def execute(self, context):
        
        csg_stack = build_csg_stack()
        
        stored_positions = [ob.name for ob in bpy.data.objects if ob.get('stored_position')]
        
        if self.all_positions and len(stored_positions):
            if self.jaw_mode == 'BOTH':
                showErrorMessage('Cannot do both shells in all positions at once!')
                return {'CANCELLED'}
            #todo, create a class method for this!
            
            for pos in stored_positions:
                #set position
                
                bpy.ops.d3dual.jump_to_stored_position(position = pos)
                
                apply_csg_stack_to_shells(csg_stack, 
                                          mode = self.mode, 
                                          jaw_mode = self.jaw_mode, 
                                          suffix = pos, 
                                          make_new = True)
                
        else:
            apply_csg_stack_to_shells(csg_stack, mode = self.mode, jaw_mode = self.jaw_mode)
                    
        return {'FINISHED'} 
    
def register():
    bpy.utils.register_class(D3Dual_OT_place_attachment_element)
    bpy.utils.register_class(D3Dual_OT_csg_attachment_elements)
    bpy.utils.register_class(D3Dual_OT_remove_attachment_element)
    bpy.utils.register_class(D3Dual_OT_snap_element_to_surface)
    bpy.utils.register_class(D3Dual_OT_show_all_attachments)
    bpy.utils.register_class(D3Dual_OT_hide_all_attachments)
    
def unregister():
    bpy.utils.unregister_class(D3Dual_OT_place_attachment_element)
    bpy.utils.unregister_class(D3Dual_OT_csg_attachment_elements)
    bpy.utils.unregister_class(D3Dual_OT_remove_attachment_element)
    bpy.utils.unregister_class(D3Dual_OT_snap_element_to_surface)
    bpy.utils.unregister_class(D3Dual_OT_show_all_attachments)
    bpy.utils.unregister_class(D3Dual_OT_hide_all_attachments)
        

# ---- Perplexity API Suggested Migrations ----
Replace the deprecated property definitions with the new-style type annotations and assignment, as required in Blender 2.80+ and still current in Blender 4.4. The properties should be defined as class attributes using type hints, not as direct assignments in the class body. Here is the corrected code block:

```python
import bpy

class MyPropertyGroup(bpy.types.PropertyGroup):
    axis: bpy.props.EnumProperty(
        name='Axis',
        items=[
            ('X', 'X', 'X'),
            ('Y', 'Y', 'Y'),
            ('Z', 'Z', 'Z'),
            ('-X', '-X', '-X'),
            ('-Y', '-Y', '-Y'),
            ('-Z', '-Z', '-Z')
        ],
        default='Z'
    )
    mode: bpy.props.EnumProperty(
        name='Merge Mode',
        items=[
            ('BOOLEAN', 'BOOLEAN', 'BOOLEAN'),
            ('VOLUME', 'VOLUME', 'VOLUME')
        ],
        default='VOLUME'
    )
    v_res: bpy.props.FloatProperty(
        name='Voxel Size',
        min=0.1,
        max=0.3,
        default=0.15
    )
    optimize: bpy.props.BoolProperty(
        name='Decimate',
        default=True
    )
    jaw_mode: bpy.props.EnumProperty(
        name='Merge Mode',
        items=[
            ('MAX', 'MAX', 'MAX'),
            ('MAND', 'MAND', 'MAND'),
            ('BOTH', 'BOTH', 'BOTH')
        ],
        default='BOTH'
    )
    all_positions: bpy.props.BoolProperty(
        name='All Positions',
        default=True,
        description='Create a unique shell for all stored positions'
    )
```

**Key changes:**
- Use `axis: bpy.props.EnumProperty(...)` instead of `axis = bpy.props.EnumProperty(...)`.
- All property definitions must be class attributes with type annotations, not simple assignments[1][3][5].
- This format is required for Blender 2.80 and newer, including 4.4.
