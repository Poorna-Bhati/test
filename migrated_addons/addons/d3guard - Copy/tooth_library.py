#python imports
from os.path import join, dirname, abspath, exists, isfile
from os import walk, listdir
from common_utilities import get_settings


#blender imports
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix

#https://devtalk.blender.org/t/can-bpy-props-be-used-for-dynamic-lists/10130/12
from subtrees.metaballs.vdb_remesh import convert_vdb, read_bmesh
from subtrees.bmesh_utils.bmesh_utilities_common import bmesh_join_list
from subtrees.geometry_utils.transformations import r_matrix_from_principal_axes
_enum_libraries = []
_enum_teeth = []

last_lib = None
cached_teeth = None


def enum_tooth_libraries(self, context):
    
    assets_path = join(dirname(abspath(__file__)), "data_assets","tooth_libraries")
    _enum_libraries.clear()
    blendfiles = [f for f in listdir(assets_path) if isfile(join(assets_path, f)) and  f.endswith('.blend')]
    
    for bf in blendfiles:
        _enum_libraries.append((join(assets_path, bf), bf,  ""))
            
    return _enum_libraries


def enum_teeth_objects(self, context):
    """Populate Objects List from Parts Library.
    Creates list of objects that optionally have search string contained in them
    to populate variable pdt_lib_objects enumerator.
    Args:
        context: Blender bpy.context instance.
    Returns:
        list of Object Names.
    """

    prefs = get_settings()
    
    file_path = prefs.tooth_lib
    
    global cached_teeth
    
    if isfile(file_path) and file_path.endswith(".blend"):
        global last_lib
        if file_path == last_lib:  #don't re-load the file to read the obj names!
            #print('skipping update')
            #print(cached_attachments)
            return cached_teeth
        _enum_teeth.clear()    
        with bpy.data.libraries.load(str(file_path)) as (data_from, data_to):
            object_names = [obj for obj in data_from.objects if "_d3attach" in obj]
        for object_name in object_names:
            _enum_teeth.append((object_name, object_name.split("_")[0], ""))
            
        last_lib = file_path
        cached_teeth = _enum_teeth
    else:
        _enum_teeth.clear()
        _enum_teeth.append(("MISSING", "Library is Missing", ""))
        
    return _enum_teeth


  
    
#structure for linking an attachment from library
def link_tooth_from_library(context):

    prefs = get_settings()
    file_path = prefs.tooth_lib
    attach_obj = prefs.tooth_lib_ob

    if isfile(file_path) and file_path.endswith(".blend"):
        with bpy.data.libraries.load(str(file_path)) as (data_from, data_to):
            
            attachment_names = [obj for obj in data_from.objects]
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


    
class D3Dual_OT_place_lib_tooth(bpy.types.Operator):
    """Place a tooth located at the 3D cursor"""
    bl_idname = "d3dual.place_lib_tooth"
    bl_label = "Place tooth"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        
        return True
   
    def execute(self, context):
        
        obs = link_tooth_from_library(context)
        
        for ob in bpy.data.objects:
            ob.select = False
        
        obs[0].select = True
        context.scene.objects.active = obs[0]
        obs[0].location = context.scene.cursor_location
        
        context.space_data.show_manipulator = True
        context.space_data.transform_manipulators = {'TRANSLATE', 'ROTATE'}
        context.space_data.transform_orientation = 'LOCAL'
                    
        return {'FINISHED'}    



def fast_join(ob_base, ob_list):
    
    ob_mx = ob_base.matrix_world
    ob_imx = ob_mx.inverted()
    
    bme = bmesh.new()
    bme.from_mesh(ob_base.data)
    
    
    for ob in ob_list:
        mx = ob.matrix_world
        imx = mx.inverted()
        
        me = ob.data
        me.transform(ob_imx * mx)
        bme.from_mesh(me)
        me.transform(imx * ob_mx)
        
        
    bme.to_mesh(ob_base.data)
    
    bme.free()
    
    
class D3Dual_OT_join_teeth_to_models(bpy.types.Operator):
    """Place an attachment located at the 3D cursor"""
    bl_idname = "d3dual.simple_join_teeth_to_models"
    bl_label = "Join Teeth to Models"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        
        return True
   
    def execute(self, context):

        teeth = [ob for ob in bpy.data.objects if ob.get('d3d_a_type') == 'tooth']
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        max_teeth = [ob for ob in teeth if ob.get('target') == 'MAX']
        mand_teeth = [ob for ob in teeth if ob.get('target') == 'MAND']
        
        print(teeth)
        print(max_teeth)
        print(mand_teeth)
        if len(max_teeth):
            max_ob = bpy.data.objects.get(splint.get_maxilla())
            fast_join(max_ob, max_teeth)
        
        if len(mand_teeth):
            mand_ob = bpy.data.objects.get(splint.get_mandible())
            fast_join(mand_ob, mand_teeth)
            
                    
        return {'FINISHED'}
    
    
class D3Dual_OT_boolean_teeth_to_models(bpy.types.Operator):
    """Place an attachment located at the 3D cursor"""
    bl_idname = "d3dual.boolean_join_teeth_to_models"
    bl_label = "Boolean Join Teeth to Models"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        
        return True
   
    def execute(self, context):
        
        teeth = [ob for ob in bpy.data.objects if ob.get('d3d_a_type') == 'tooth']
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        max_teeth = [ob for ob in teeth if ob.get('target') == 'MAX']
        mand_teeth = [ob for ob in teeth if ob.get('target') == 'MAND']
        
        
        if len(max_teeth):
            max_ob = bpy.data.objects.get(splint.get_maxilla())
            
            rem_mods = [mod for mod in max_ob.modifiers if 'tooth' in mod.name]
            for mod in rem_mods:
                max_ob.modifiers.remove(mod)
                
            for ob in max_teeth:
                mod = max_ob.modifiers.new("JOIN tooth", type = 'BOOLEAN')
                mod.operation = 'UNION'
                mod.object = ob
                
        
        if len(mand_teeth):
            mand_ob = bpy.data.objects.get(splint.get_mandible())
            

            rem_mods = [mod for mod in mand_ob.modifiers if 'tooth' in mod.name]
            for mod in rem_mods:
                mand_ob.modifiers.remove(mod)
                
            for ob in mand_teeth:
                mod = mand_ob.modifiers.new("JOIN tooth", type = 'BOOLEAN')
                mod.operation = 'UNION'
                mod.object = ob
                
                
                    
        return {'FINISHED'}  
    
def register():
    bpy.utils.register_class(D3Dual_OT_place_lib_tooth)
    bpy.utils.register_class(D3Dual_OT_join_teeth_to_models)
    bpy.utils.register_class(D3Dual_OT_boolean_teeth_to_models)

def unregister():
    bpy.utils.unregister_class(D3Dual_OT_place_lib_tooth)
    bpy.utils.unregister_class(D3Dual_OT_join_teeth_to_models)
    bpy.utils.unregister_class(D3Dual_OT_boolean_teeth_to_models)