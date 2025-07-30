'''
Created on Oct 1, 2017

@author: Patrick
'''
import os
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import itertools
from mathutils import Matrix
from io_mesh_stl import stl_utils, blender_utils
from common_utilities import showErrorMessage


def write_some_data(context, filepath, use_some_setting):
    print("running write_some_data...")
    f = open(filepath, 'w', encoding='utf-8')
    f.write("Hello World %s" % use_some_setting)
    f.close()

    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator

from io_scene_obj import import_obj

from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper_factory,
        path_reference_mode,
        axis_conversion,
        )


IOOBJOrientationHelper = orientation_helper_factory("IOOBJOrientationHelper", axis_forward='-Z', axis_up='Y')
IOSTLOrientationHelper = orientation_helper_factory("IOSTLOrientationHelper", axis_forward='Y', axis_up='Z')

class D3DUALExportAppliance(Operator, ExportHelper, IOSTLOrientationHelper):
    """Use this to export your appliance"""
    bl_idname = "d3dual.export_appliance_stl"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Appliance STL"

    # ExportHelper mixin class uses this
    filename_ext = ".stl"

    filter_glob = StringProperty(
            default="*.stl",
            options={'HIDDEN'},
            maxlen=255,  # Max internal buffer length, longer would be clamped.
            )

    use_original_coords = BoolProperty(
            name="Original Coordiantes",
            description="Export object in the original reference frame of model import",
            default=True,
            )
    
    use_selection = BoolProperty(
            name="Selection Only",
            description="Export selected objects only",
            default=False,
            )
    global_scale = FloatProperty(
            name="Scale",
            min=0.01, max=1000.0,
            default=1.0,
            )

    use_scene_unit = BoolProperty(
            name="Scene Unit",
            description="Apply current scene's unit (as defined by unit scale) to exported data",
            default=False,
            )
    ascii = BoolProperty(
            name="Ascii",
            description="Save the file in ASCII file format",
            default=False,
            )
    use_mesh_modifiers = BoolProperty(
            name="Apply Modifiers",
            description="Apply the modifiers before saving",
            default=True,
            )
    batch_mode = EnumProperty(
            name="Batch Mode",
            items=(('OFF', "Off", "All data in one file"),
                   ('OBJECT', "Object", "Each object as a file")),
            default = 'OBJECT')
    
    def execute(self, context):
        keywords = self.as_keywords(ignore=("use_original_coords",
                                            "axis_forward",
                                            "axis_up",
                                            "use_selection",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            "use_scene_unit",
                                            "use_mesh_modifiers",
                                            "batch_mode"
                                            ))

        scene = context.scene
        
        ShellMax = bpy.data.objects.get('Final_Max')  #Check for CORK created Shell
        ShellMand = bpy.data.objects.get('Final_Mand')
        
        data_seq = []
        if ShellMax != None:
            data_seq.append(ShellMax)
        if ShellMand != None:
            data_seq.append(ShellMand)
        
        
        if len(data_seq) == 0:
            self.report('ERROR', 'There are no splint shells to export')
            return 'CANCELLED'
        
        
        splint = context.scene.odc_splints[0]
        
        if not splint.finalize_splint_max:
            self.report('WARNING', 'max shell has not been finalized')
            showErrorMessage( 'mand shell has not been finalized')
            
        if not splint.finalize_splint_mand:
            self.report('WARNING', 'mand shell has not been finalized')
            showErrorMessage( 'mand shell has not been finalized')
            
        
        Model = bpy.data.objects.get(splint.max_model)  
        children = [ob for ob in Model.children if ob.type == 'EMPTY' and 'orig_origin' in ob.name]
        if len(children) and self.use_original_coords:
            origin_empty = children[0]
            print(origin_empty)
            origin_mx = origin_empty.matrix_world
            i_origin_mx = origin_mx.inverted()
        else:
            print('NO MATRIX FOUND')
            i_origin_mx = Matrix.Identity(4)
        #i_origin_mx = Matrix.Identity(4)    
            

        # Take into account scene's unit scale, so that 1 inch in Blender gives 1 inch elsewhere! See T42000.
        global_scale = self.global_scale
        if scene.unit_settings.system != 'NONE' and self.use_scene_unit:
            global_scale *= scene.unit_settings.scale_length

        if self.use_original_coords:
            global_matrix = i_origin_mx
        else:
            global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4() * Matrix.Scale(global_scale, 4)

        if self.batch_mode == 'OFF':
            faces = itertools.chain.from_iterable(
                    blender_utils.faces_from_mesh(ob, global_matrix, self.use_mesh_modifiers)
                    for ob in data_seq)

            stl_utils.write_stl(faces=faces, **keywords)
        elif self.batch_mode == 'OBJECT':
            prefix = os.path.splitext(self.filepath)[0]
            keywords_temp = keywords.copy()
            for ob in data_seq:
                faces = blender_utils.faces_from_mesh(ob, global_matrix, self.use_mesh_modifiers)
                keywords_temp["filepath"] = prefix + bpy.path.clean_name(ob.name) + ".stl"
                stl_utils.write_stl(faces=faces, **keywords_temp)

        
        text_filepath = os.path.splitext(self.filepath)[0] + "_report.txt"
        reports = [txt for txt in bpy.data.texts if "Report" in txt.name]
        if len(reports):
            latest_report = max(reports, key = lambda x: x.name)
            txt_file = open(text_filepath, "w")
            txt_file.write(latest_report.as_string())
            txt_file.close()
        
        return {'FINISHED'}


class D3DUAL_OT_import_face_obj(Operator, ImportHelper, IOOBJOrientationHelper):
    
    """Load a Wavefront OBJ File"""
    bl_idname = "d3dual.import_face_obj"
    bl_label = "Import Face OBJ"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".obj"
    filter_glob = StringProperty(
            default="*.obj;*.mtl",
            options={'HIDDEN'},
            )

    use_edges = BoolProperty(
            name="Lines",
            description="Import lines and faces with 2 verts as edge",
            default=True,
            )
    use_smooth_groups = BoolProperty(
            name="Smooth Groups",
            description="Surround smooth groups by sharp edges",
            default=True,
            )

    use_split_objects = BoolProperty(
            name="Object",
            description="Import OBJ Objects into Blender Objects",
            default=True,
            )
    use_split_groups = BoolProperty(
            name="Group",
            description="Import OBJ Groups into Blender Objects",
            default=True,
            )

    use_groups_as_vgroups = BoolProperty(
            name="Poly Groups",
            description="Import OBJ groups as vertex groups",
            default=False,
            )

    use_image_search = BoolProperty(
            name="Image Search",
            description="Search subdirs for any associated images "
                        "(Warning, may be slow)",
            default=True,
            )

    split_mode = EnumProperty(
            name="Split",
            items=(('ON', "Split", "Split geometry, omits unused verts"),
                   ('OFF', "Keep Vert Order", "Keep vertex order from file"),
                   ),
            )

    global_clamp_size = FloatProperty(
            name="Clamp Size",
            description="Clamp bounds under this value (zero to disable)",
            min=0.0, max=1000.0,
            soft_min=0.0, soft_max=1000.0,
            default=0.0,
            )

    def execute(self, context):
        # print("Selected: " + context.active_object.name)
        

        if self.split_mode == 'OFF':
            self.use_split_objects = False
            self.use_split_groups = False
        else:
            self.use_groups_as_vgroups = False

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "split_mode",
                                            ))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix
        keywords["use_cycles"] = (context.scene.render.engine == 'CYCLES')

        if bpy.data.is_saved and context.user_preferences.filepaths.use_relative_paths:
            
            keywords["relpath"] = os.path.dirname(bpy.data.filepath)

        return import_obj.load(context, **keywords)

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "use_smooth_groups")
        row.prop(self, "use_edges")

        box = layout.box()
        row = box.row()
        row.prop(self, "split_mode", expand=True)

        row = box.row()
        if self.split_mode == 'ON':
            row.label(text="Split by:")
            row.prop(self, "use_split_objects")
            row.prop(self, "use_split_groups")
        else:
            row.prop(self, "use_groups_as_vgroups")

        row = layout.split(percentage=0.67)
        row.prop(self, "global_clamp_size")
        layout.prop(self, "axis_forward")
        layout.prop(self, "axis_up")

        layout.prop(self, "use_image_search")
    

def register():
    print('\n\n\nREGIESTER IO\n\n\n ')
    bpy.utils.register_class(D3DUALExportAppliance)
    bpy.utils.register_class(D3DUAL_OT_import_face_obj)
    

def unregister():
    bpy.utils.unregister_class(D3DUALExportAppliance)
    bpy.utils.unregister_class(D3DUAL_OT_import_face_obj)
    


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_test.some_data('INVOKE_DEFAULT')