#    Addon info
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

#CITATIONS
#http://www.dentistrytoday.com/occlusion/1507--sp-720974386


bl_info = {
    'name': "D3T Dual Arch",
    'author': "Patrick R. Moore",
    'version': (0,0,6),
    'blender': (2, 7, 9),
    'api': "3c04373",
    'location': "3D View -> Tool Shelf",
    'description': "A training and educational Dental Design CAD Tool not intended for clinical use",
    'warning': "Not Intended for Clinical Use!",
    'wiki_url': "",
    'tracker_url': "",
    'category': '3D View'}


#we need to add the odc subdirectory to be searched for imports
#http://stackoverflow.com/questions/918154/relative-paths-in-python
import sys, os, platform, inspect, imp, time
sys.path.append(os.path.join(os.path.dirname(__file__)))
print(os.path.join(os.path.dirname(__file__)))


import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty
from bpy.app.handlers import persistent
#from . 

import odcutils
from articulator_drivers import load_driver_namespace
from .bg_test_ops import clear_dicts
from . import addon_updater_ops

from .attachments import enum_attachment_libraries, enum_attachment_objects

from .tooth_library import enum_tooth_libraries, enum_teeth_objects
#addon preferences
class D3SplintAddonPreferences(AddonPreferences):
    bl_idname = __name__

    addons = bpy.context.user_preferences.addons
    
    folderpath = os.path.dirname(os.path.abspath(__file__))
    cork_folder =os.path.join(folderpath,'cork\\')
    
    if platform.system() == "Windows":
        cork_exe =os.path.join(folderpath,'cork\\win\\wincork.exe')
        if not os.path.exists(cork_exe):
            cork_exe = ''
            print('Cork Unsupported')
    elif "Mac" in platform.system():
        cork_exe =os.path.join(folderpath,'cork\\mac\\cork')
        if not os.path.exists(cork_exe):
            cork_exe = ''
            print('Cork Unsupported')
    elif "Linux" in platform.system():
        cork_exe =os.path.join(folderpath,'cork\\linux\\cork.exe')
        if not os.path.exists(cork_exe):
            cork_exe = ''
            print('Cork Unsupported')
    else:
        cork_exe = ''
        print('Cork Unsupported')
    
    
    cork_lib = bpy.props.StringProperty(
        name="Cork Exe",
        default=cork_exe,
        #default = '',
        subtype='FILE_PATH')
    
    dev = bpy.props.BoolProperty(name="Development Mode",
                                 default=False)

    debug = IntProperty(
            name="Debug Level",
            default=1,
            min = 0,
            max = 4,
            )
    
    
    
    non_clinical_use = bpy.props.BoolProperty(default = False, name = 'Not For Clinical Use', description = 'By checking this box you certify that you are using this for non-clinical, training or educational purposes')
    #auto_use_background = bpy.props.BoolProperty(default = True, name = 'Auto Background', description = 'allow D3Splint to do some tasks automatically based on user preferences')
    
    
    #auto_optimize = bpy.props.BoolProperty(default = False, name = 'Auto Optimize Models', description = 'allow D3Splint to do some tasks automatically based on user preferences')
    auto_blockout = bpy.props.BoolProperty(default = False, name = 'Auto BLockout Large Concavities', description = 'Always automatically blockout concavities after rim fusion')
    auto_remesh_smooth = bpy.props.BoolProperty(default = False, name = 'Auto Remesh Smooth', description = 'Always automatically do remesh and smooth after rim fusion')
    
    #D3tool.online cloud support
    key_path = StringProperty(name = 'User Key File', subtype = 'FILE_PATH', default = '')
    key_string = StringProperty(name = 'User Key', subtype = 'PASSWORD',  default = '')
    
    
    ##########################################
    ###### WorkFlow Defaults      ############
    ##########################################
    
    #TODO DUAL
    default_jaw_type = bpy.props.EnumProperty(name = 'Jaw Type', 
                                              items = [('MAXILLA', 'MAXILLA', 'MAXILLA'),('MANDIBLE', 'MANDIBLE', 'MANDIBLE')],
                                              default = "MAXILLA",
                                              description = 'Appliance is on upper or lower jaw')
    
    
    
    #TODO DUAL
    default_workflow_type = bpy.props.EnumProperty(name = 'Workflow Type', 
                                              items = [('FREEFORM', 'Freeform', 'Exposes all D3Splint tools with no recommended sequence'),
                                                       ('SIMPLE_SHELL', 'Simple Shell', 'Basic anatomical offset shell, wear guard, thick retainer etc'),
                                                       ('DEPROGRAMMER', 'Anterior Deprogrammer', 'An antomic shell with anterior deprogrammer element'),
                                                       ('FLAT_PLANE', 'Flat Plane', 'A flat plane splint with even contact'),
                                                       ('MICHIGAN', 'Michigan Style', 'A flat posterior plane with anterior ramp/guidance'),
                                                       ('ANTERIOR_POSITIONER', 'Anterior Positioner', 'Farrar Style, anti-retrusion, pull forward'),
                                                       ('BITE_POSITIONER', 'Bite Positioner', 'A flat wafer, surgical occlusal stent or jaw positining jig')],
                                              default = "FLAT_PLANE",
                                              description = 'Use the simple workflow filter to expose recommende sequence')
    
    
    #Workflow Panel Drawing Toggles
    show_picking = bpy.props.BoolProperty(default = False, name = 'Show Picking')
    show_articulator = bpy.props.BoolProperty(default = False, name = 'Show Articulator')
    show_wax = bpy.props.BoolProperty(default = False, name = 'Show Wax')
    show_shape_refinement = bpy.props.BoolProperty(default = False, name = 'Show Shape Refinement')
    show_deprogrammer = bpy.props.BoolProperty(default = False, name = 'Show Deprogrammer')
    show_shell = bpy.props.BoolProperty(default = False, name = 'Show Shell')
    show_fit_and_retention = bpy.props.BoolProperty(default = False, name = 'Show Fit and Retention')
    show_occlusion = bpy.props.BoolProperty(default = False, name = 'Show Occlusion')
    show_finalize = bpy.props.BoolProperty(default = False, name = 'Show Finalize')
    show_outdated_tools = bpy.props.BoolProperty(default = False, name = 'Show Outdated')
    
    ##########################################
    ###### Colors and Drawing     ############
    ##########################################
    
    def_model_color = FloatVectorProperty(name="Model Color", description="Choose Model Color", min=0, max=1, default=(.477, .397,.256), subtype="COLOR")
    def_opposing_color = FloatVectorProperty(name="Opposing Color", description="Choose Model Color", min=0, max=1, default=(1, .83,.62), subtype="COLOR")
    def_splint_color = FloatVectorProperty(name="Splint Color", description="Choose Splint Color", min=0, max=1, default=(.59, .83,.75), subtype="COLOR")
    def_rim_color = FloatVectorProperty(name="Rim Color", description="Choose Rim Color", min=0, max=1, default=(.75, .75,.25), subtype="COLOR")
    
    point_size = IntProperty(
            name="Point SIze",
            description = "size of dots when drawing landmarks in scene",
            default=8,
            min = 3,
            max = 13,
            )
    
    def_point_color = FloatVectorProperty(name="Points Color", description="Color of reference points in interactive operators", min =0, max = 1, default=(.8, .1,.1), subtype="COLOR")
    active_point_color = FloatVectorProperty(name="Active Point Color", description="Color of the selected point in interactive operators", min =0, max = 1, default=(.8, .8,.2), subtype="COLOR")
    active_region_color = FloatVectorProperty(name="Active Region Color", description="A border of this color will be drawn when in interactive modes", min =0, max = 1, default=(.8, .2,.1), subtype="COLOR")
    
    undercut_color = FloatVectorProperty(name="Undercut Color", description="A border of this color will be drawn when in interactive modes", min =0, max = 1, default=(.75, .75,.75), subtype="COLOR")
    ##########################################
    ###### Operator Defaults      ############
    ##########################################
    
    ##### Deprogrammer #####
    def_guidance_angle = IntProperty(name = 'Guidance Angle', default = 15, min = -90, max = 90, description = 'Angle off of world Z')
    def_anterior_length = FloatProperty(name = 'Anterior Length', default = 5, description = 'Length of anterior ramp')
    def_posterior_length = FloatProperty(name ='Posterior Lenght', default = 10, description = 'Length of posterior ramp')
    def_posterior_width = FloatProperty(name = 'Posterior Width', default = 10, description = 'Posterior Width of ramp')
    def_anterior_width = FloatProperty(name = 'Anterior Width', default = 8, description = 'Anterior Width of ramp')
    def_thickness = FloatProperty(name = 'Ramp Thickness', default = 2.75, description = 'Thickness of ramp')
    def_support_height = FloatProperty(name = 'Support Height', default = 3, description = 'Height of support strut')
    def_support_width =  FloatProperty(name = 'Support Width', default = 6, description = 'Width of support strut')
    
    ##### Shell, Fit and Retention ####
    def_shell_thickness = FloatProperty(name = "Shell Thickness", default = 1.5, min = .8, max = 4)
    def_min_thickness = FloatProperty(name = 'Minimum Thickness', default = 1.25)
    def_passive_radius = FloatProperty(default = .12 , min = .01, max = .4, description = 'Thickness of Offset, larger numbers means less retention', name = 'Compensation Gap Thickness') 
    def_blockout_radius = FloatProperty(default = .05 , min = .01, max = .12, description = 'Allowable Undercut, larger numbers means more retention', name = 'Undercut Strength')
    def_drillcomp_value = FloatProperty(name = 'DrillComp Value', default = 0.75, min = .25, max = 1.5, description = 'Radius of smallest bur used in milling')
    def_use_drillcomp = BoolProperty(name = 'Default Use DrollComp', default = False)
    
    ##### Text Stencilling ##########
    #this value used to seed the modal operator
    d3_model_label = StringProperty(name = 'Text Label', default = 'Model Label')
    d3_model_label_depth = FloatProperty(name = 'Emboss Depth', min = .2, max = 4, default = .5)
    d3_model_label_stencil_font = StringProperty(name = 'Stencil Font', default = '', subtype = 'FILE_PATH')
    d3_model_block_label_font = StringProperty(name = 'Block Label Font', default = '', subtype = 'FILE_PATH') #TODO, include the font in the addon
    d3_model_block_label_size = FloatProperty(name = 'Block Label Size', min = 1.0, max = 5.0, default = 3.0)
    d3_model_block_label_depth = FloatProperty(name = 'Block Label Size', min = 0.25, max = 5.0, default = 1.0)
    d3_model_block_label_positive = BoolProperty(name = "Block Label Positive", default = True, description = "Positive or negative embossing of the label on block elements")
    
    
    ##### Hole Filler ##########
    #this value used to seed the modal operator
    d3_model_hole_fill_edge_length = FloatProperty(name = 'Hole Filler Edge Length', min = .1, max = 2.0, default = .25, description = 'Size of the edges hole filler uses to fill the hole.  Use larger values for larger holes.  .2 to .3 is typically good for tooth holes, .4 to .7 is good for bases and large areas')
    d3_model_max_hole_size = IntProperty(name = 'Auto Fill Hole Size', min = 3, max = 200, default = 20)
    d3_model_auto_fill_small = BoolProperty(name = 'Auto Fill Small Holes', default = False)
    
    
    ##### Elastic Button #####
    def_button_major = FloatProperty(name = 'Button Major', default = 8.5, description = 'Longest dimension of button hook')
    def_button_minor = FloatProperty(name ='Button Minor', default = 6.5, description = 'Smallest dimension of buton hook')
    def_button_thickness = FloatProperty(name ='Button Thickness', default = 1.5, description = 'Thickness of the button top')
    def_button_base_diameter  = FloatProperty(name = 'Base Diameter', default = 6.5, description = 'Width of base of button')
    def_button_stalk_height = FloatProperty(name = 'Stalk Height', default = 2.0, description = 'Button Stalk Height')
    def_button_stalk_diameter = FloatProperty(name = 'Stalk Diameter', default = 5.0, description = 'Diameter of Stalk')
    def_button_base_height = FloatProperty(name = 'Base Thickness', default = 2.0, description = 'Thickness of Base')
    def_button_constrain_length = FloatProperty(name = 'Constrain Length', default = 20.0, description = 'Default Distance between buttons')
    
    
    ######################
    #### ATTACHMENTS ####
    ######################
    
    folderpath = os.path.dirname(os.path.abspath(__file__))
    attach_folder =os.path.join(folderpath,'data_assets', 'attachments')
    
    
    if not os.path.exists(attach_folder):
        attach_folder = ''
            
            
            
    attachment_library_path = StringProperty(name = "Attachment Folder", default = attach_folder, subtype = 'FILE_PATH' )
    
    attachment_lib = bpy.props.EnumProperty(name = 'Attachment Library', 
                                              items = enum_attachment_libraries,
                                              description = 'Choose the Library You Would Like to Use')
    
    
    attachment_ob = bpy.props.EnumProperty(name = 'Attachment Object', 
                                              items = enum_attachment_objects,
                                              description = 'Choose the attachment object')
    
    ######################
    #### Tooth Lib ####
    ######################
    
    folderpath = os.path.dirname(os.path.abspath(__file__))
    tooth_folder =os.path.join(folderpath,'data_assets', 'tooth_libraries')
    
    
    if not os.path.exists(attach_folder):
        tooth_folder = ''
            
            
            
    tooth_library_path = StringProperty(name = "Tooth Lib Folder", default = tooth_folder, subtype = 'FILE_PATH' )
    
    tooth_lib = bpy.props.EnumProperty(name = 'Tooth Library', 
                                              items = enum_tooth_libraries,
                                              description = 'Choose the Library You Would Like to Use')
    
    
    tooth_lib_ob = bpy.props.EnumProperty(name = 'Tooth Object', 
                                              items = enum_teeth_objects,
                                              description = 'Choose the tooth object')
    
    
    ##########################################
    ###### Articulator Defaults   ############
    ##########################################
    
    
    def_intra_condyle_width = IntProperty(name = 'Intra-Condyle Width', default = 110, description = 'Width between condyles in mm')
    def_condyle_angle = IntProperty(name = 'Condyle Angle', default = 20, description = 'Condyle inclination in the sagital plane')
    def_bennet_angle = FloatProperty(name = 'Bennet Angle', default = 7.5, description = 'Bennet Angle: Condyle inclination in the axial plane')
    
    def_incisal_guidance = FloatProperty(default = 10, description = 'Incisal Guidance Angle', name = "Incisal Guidance")
    def_canine_guidance = FloatProperty(name = "Canine Guidance", default = 10, description = 'Canine Lateral Guidance Angle')
    def_guidance_delay_ant = FloatProperty(name = "Anterior Guidance Delay", default = .1, description = 'Anterior movement before guidance starts')
    def_guidance_delay_lat = FloatProperty(name = "Canine Guidance Delay", default = .1, description = 'Lateral movement before canine guidance starts')
    
    
    def_occlusal_plane_angle = FloatProperty(name = "Occlusal Plane Angle", default = 7.5, min = -5.0, max = 20, description = "Angle between occlusal plane and Frankfurt Horizontal Plane")
    
    def_balkwill_angle = FloatProperty(name = "Balkwill Angle", default = 20, description = "Psueduo-Balkwill Angle from condyles to upper incisors")
    def_arm_radius = FloatProperty(name = "Mand Arm Radius", default = 100, description = "Distance betweeen condyles and upper central incisor midpoint")

    def_condylar_resolution = IntProperty(name = "Condyle Resolution", default = 20, min = 5, max = 40, description = "Number of steps to interpolate each condylar position, higher = longer simulation times")
    def_range_of_motion = FloatProperty(name = "Condylar Range of Motion", default = 6, min = 3, max = 8, description = "Distance each condylar path is simulated")
    
    
    ##########################################
    ###### Alpha Experimental Properties ######
    ##########################################
    
    use_alpha_tools = bpy.props.BoolProperty(
        name = "Use Alpha Tools",
        description = "If enabled, display alpha experimental options",
        default = False,
        )
    
    use_poly_cut = bpy.props.BoolProperty(
        name = "Use Poly Cut",
        description = "If enabled, use the experimental poly knife to mark splint margin",
        default = False,
        )
    
    
    ##########################################
    ###### Updater Properties     ############
    ##########################################
    
    
    auto_check_update = bpy.props.BoolProperty(
        name = "Auto-check for Update",
        description = "If enabled, auto-check for updates using an interval",
        default = False,
        )
    updater_intrval_months = bpy.props.IntProperty(
        name='Months',
        description = "Number of months between checking for updates",
        default=0,
        min=0
        )
    updater_intrval_days = bpy.props.IntProperty(
        name='Days',
        description = "Number of days between checking for updates",
        default=7,
        min=0,
        )
    updater_intrval_hours = bpy.props.IntProperty(
        name='Hours',
        description = "Number of hours between checking for updates",
        default=0,
        min=0,
        max=23
        )
    updater_intrval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description = "Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59
        )

    show_occlusal_mod = bpy.props.BoolProperty(
        name = "Show Occlusal Mod",
        description = "Shows some beta Settings",
        default = False,
        )
    
    show_survey_functions = bpy.props.BoolProperty(
        name = "Show Survey Tools",
        description = "Shows Buttons for Survey Tools",
        default = False,
        )
    
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="D3Splint Preferences and Settings")
        #layout.prop(self, "mat_lib")
        
        
        if not self.non_clinical_use:
            
            row = layout.row()
            row.label('Please certify non-clinical use')
            row = layout.row()
            row.prop(self, "non_clinical_use")
            
            return
            
        row = layout.row()
        row.prop(self, "non_clinical_use")
        
        #row = layout.row()
        #row.prop(self, "auto_use_background") 
           
        row = layout.row()
        row.operator("opendental.d3t_critiacal_settings", text = 'Set Mandatory Settings')
        

        row = layout.row()
        row.prop(self, "attachment_library_path")
        ## Visualization 
        row = layout.row(align=True)
        row.label("Visualization Settings")

        row = layout.row(align=True)
        row.prop(self, "def_model_color")
        row.prop(self, "def_opposing_color")
        row.prop(self, "def_splint_color")
        row.prop(self, "def_rim_color")
        row = layout.row()
        row.prop(self, "point_size")
        row.prop(self, "def_point_color")
        row.prop(self, "active_point_color")
        row.prop(self, "active_region_color")
    
        row = layout.row()
        row.prop(self, "undercut_color")
        

        ## Operator Defaults
        #box = layout.box().column(align=False)
        row = layout.row()
        row.label(text="Operator Defaults")
        
        #REGISTERATION
        row = layout.row()
        row.label("Registration")
        
        row = layout.row(align=True)
        row.prop(self, "key_path")

        row = layout.row(align=True)
        row.prop(self, "key_string")
        
        ### AUTOMATION ####
        row = layout.row()
        row.label("Automation")
        row = layout.row()
        row.prop(self, "auto_blockout")
        row.prop(self, "auto_remesh_smooth")
        ##### Fit and Thickness ####
        row = layout.row()
        row.label('Thickness, Fit and Retention')
        row = layout.row()
        row.prop(self, "def_shell_thickness")
        row.prop(self, "def_passive_radius")
        row.prop(self, "def_blockout_radius")
    
        ##### Model Work ####
        row = layout.row()
        row.label('Model Work Settings')
        row = layout.row()
        row.prop(self, "d3_model_auto_fill_small")
        row.prop(self, "d3_model_max_hole_size")
        row.prop(self, "d3_model_hole_fill_edge_length")
        
        row = layout.row()
        row.label('Text and Labelling')
        
        row = layout.row()
        row.prop(self, "d3_model_label_stencil_font")
        row.prop(self, "d3_model_block_label_font")
        row.prop(self, "d3_model_block_label_size")
        row.prop(self, "d3_model_block_label_positive")
        row.prop(self, "d3_model_block_label_depth")
        
        #Elastic Button
        row = layout.row()
        row.label('Elastic Button Defaults')
        row = layout.row()
        
        row = layout.row()
        row.prop(self, "def_button_major") 
        row.prop(self, "def_button_minor")
        row.prop(self, "def_button_thickness")
        
        row = layout.row()
        row.prop(self, "def_button_stalk_height")
        row.prop(self, "def_button_stalk_diameter")
       
        row = layout.row()
        row.prop(self, "def_button_base_diameter")
        row.prop(self, "def_button_base_height")
        
        row = layout.row()
        row.prop(self, "def_button_constrain_length")
        
        
        
        ##### Deprogrammer #####
        row = layout.row()
        row.label('Deprogrammer Defaults')
        row = layout.row()
        
        row.prop(self, "def_guidance_angle") 
        row.prop(self, "def_anterior_length")
        row.prop(self, "def_posterior_length")
        
        row = layout.row()
        row.prop(self, "def_posterior_width")
        row.prop(self, "def_anterior_width")
        row.prop(self, "def_thickness")
        
        row = layout.row()
        row.prop(self, "def_support_height")
        row.prop(self, "def_support_width")
        
        
        ####  Articulator Values #####
        row = layout.row()
        row.label('Articulator and Mounting')
        
        row = layout.row()
        row.prop(self, "def_intra_condyle_width")
        row.prop(self, "def_condyle_angle")
        row.prop(self, "def_bennet_angle")
        
        row = layout.row()
        row.prop(self,"def_occlusal_plane_angle")
        row.prop(self,"def_balkwill_angle")
        row.prop(self,"def_arm_radius")

        row = layout.row()
        row.prop(self, "def_incisal_guidance")
        row.prop(self, "def_canine_guidance")
        row.prop(self, "def_guidance_delay_lat")
        row.prop(self, "def_guidance_delay_ant")
        
        row = layout.row()
        row.prop(self, "def_condylar_resolution")
        row.prop(self, "def_range_of_motion")
       

        #Experiental Settings
        #row = layout.row()
        #row.label('Alpha Features and Experiments')
        #row = layout.row()
        #row.label('Only use this if not in a time crunch or willing to crash Blender')
        
        #row = layout.row()
        #row.prop(self, "use_alpha_tools")
        
        #if self.use_alpha_tools:
        #    row = layout.row()
        #    row.prop(self, "use_poly_cut")
    
        addon_updater_ops.update_settings_ui(self, context)
        
class D3Splint_OT_general_preferences(Operator):
    """Change several critical settings for optimal D3Tool use"""
    bl_idname = "opendental.d3t_critiacal_settings"
    bl_label = "Set D3Tool Critical Blender Settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        user_preferences = context.user_preferences
        
        #needed to allow articulator drivers to work
        user_preferences.system.use_scripts_auto_execute = True
        
        
        user_preferences.filepaths.use_relative_paths = False
        
        #prevent accidental tweaking when blender responsiveness is slow
        #common problem once the scene gets complex with boolean modifiers
        user_preferences.inputs.tweak_threshold = 1000
        
        #make em stick
        bpy.ops.wm.save_userpref()
        
        return {'FINISHED'}
    
class D3Splint_OT_addon_prefs(Operator):
    """Display example preferences"""
    bl_idname = "opendental.odc_addon_pref"
    bl_label = "ODC Preferences Display"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        user_preferences = context.user_preferences
        addon_prefs = user_preferences.addons[__name__].preferences

        info = ("Path: %s, Number: %d, Boolean %r" %
                (addon_prefs.filepath, addon_prefs.number, addon_prefs.boolean))

        self.report({'INFO'}, info)
        print(info)

        return {'FINISHED'}

@persistent   
def load_post_method(dummy):
    print('loaded bridges')
    #make all the bridges reload their teeth.
    odcutils.scene_verification(bpy.context.scene, debug=True)
    
    print('loaded splints')
    for splint in bpy.context.scene.odc_splints:
        print(splint.ops_string)
        
    load_driver_namespace()
    clear_dicts()

#@persistent   
#def load_pre_method(dummy):
#    print('clearing the job director')
#    global director_running
#    if director_running:
#        bpy.ops.d3splint.stop_bg_job_director()
    #time.sleep(1.5)


@persistent    
def save_pre_method(dummy):
    odcutils.scene_verification(bpy.context.scene, debug=True)
    
    print('prepared splints for save')
    for splint in bpy.context.scene.odc_splints:
        splint.save_components_to_string()

@persistent
def pause_playback(scene):
    if scene.frame_current == scene.frame_end:
        bpy.ops.screen.animation_play()
        scene.frame_set(-1)
        scene.frame_set(0)
        
        print('REACHED THE END')

@persistent
def stop_playback(scene):
    if scene.frame_current == scene.frame_end:
        bpy.ops.screen.animation_cancel(restore_frame=False)
        scene.frame_set(scene.frame_current - 1) #prevent replaying
        print('REACHED THE END')

# or restore frames:
@persistent
def stop_playback_restore(scene):
    if scene.frame_current == scene.frame_end + 1:
        bpy.ops.screen.animation_cancel(restore_frame=True)
        print('REACHED THE END')
                               
def register():
    #bpy.utils.register_module(__name__)
    #import the relevant modules
    #from . 
    
    
    
    #register this module
    bpy.utils.register_class(D3SplintAddonPreferences)
    bpy.utils.register_class(D3Splint_OT_general_preferences)
    bpy.utils.register_class(D3Splint_OT_addon_prefs)
    
    
    addon_updater_ops.register(bl_info)
    
    #import validation
    #if not validation.check_userprefs_credits():
    #    import panel_register
    #    validation.register()
    #    panel_register.register()
    #    return
    
    # from update_authenticate import update
    # from update_authenticate import authenticate
    
    # authenticate.register()
    # update.register()
    
    # if not update.services_check_token():
    #     import panel_register
    #     #validation.register()
    #     panel_register.register()
    #     return
    
    # import tracking
    # tracking.register(bl_info)
    
    if not bpy.app.background:
        from segmentation.op_splint_margin import smargin
        from segmentation.op_live_bar import livebar
        from segmentation.mark_curves import livecurves
        from segmentation.wax_curve import wax_curve
        from segmentation.op_curve_network import livecurves as livecurves2
        smargin.register()
        livebar.register()
        livecurves.register()
        livecurves2.register()
        wax_curve.register()
    
    import d3dual_classes
    import d3dual_pick_models
    import d3dual_facial_landmarks
    import d3dual_pick_face_model
    import d3dual_wax_rim
    import d3dual_stored_positions
    
    import crown, margin, bridge, splint, implant, panel, help, flexible_tooth, bracket_placement, denture_base, occlusion, ortho, curve_partition, articulator # , odcmenus, bgl_utils
    import healing_abutment, model_work, import_export, splint_booleans, splint_face_bow
    import model_labels, splint_occlusal_surfaces, incremental_save, articulator_handlers, plane_cut, d3splint_view_presets
    import composite_buttons, vertical_base, insertion_axis, reports, min_thickness, remesh_utilities, blobs, diastemas, bg_test_ops, grids_scaffolds, offset_utilities
    import landmarks_p_picker
    import optimize_model
    import refractory_new
    import splint_shell
    import v_tools
    #import meta_modelling
    
    #Dual Arch Stuff
    import dual_margin
    import dual_elements, dual_visualization, button_placement, notch_cut, design_validation, reports
    import button_draw_handler
    import attachments
    import inter_occlusal_plane
    import convex_mask
    import tooth_library
    
    
    
    #from .subtrees.curve_cad.toolpath import OffsetCurve
    
    from .cut_mesh.op_hole_filler import hole_filler_modal
    #from .cut_mesh.op_splint_outline import splint_outline_modal
    
    #register them
    d3dual_classes.register()
    d3dual_pick_models.register()
    
    odcutils.register()
    curve_partition.register()
    splint.register()
    articulator.register()
    #help.register()
    #denture_base.register()
    occlusion.register()
    
    splint_booleans.register()
    model_work.register()
    import_export.register()
    splint_face_bow.register()
    blobs.register()
    #meta_modelling.register()
    diastemas.register()
    grids_scaffolds.register()
    offset_utilities.register()
    model_labels.register()
    plane_cut.register()
    hole_filler_modal.register()
    refractory_new.register()
    splint_shell.register()
    v_tools.register()
    dual_margin.register()
    button_draw_handler.register()
    attachments.register()
    tooth_library.register()
    inter_occlusal_plane.register()
    #validation.register()
    convex_mask.register()
    #bpy.utils.register_class(OffsetCurve)
    #splint_outline_modal.register()
    
    
    splint_occlusal_surfaces.register()
    incremental_save.register()
    insertion_axis.register()
    reports.register()
    bg_test_ops.register()
    articulator_handlers.register()
    d3splint_view_presets.register()
    composite_buttons.register()
    vertical_base.register()
    min_thickness.register()
    remesh_utilities.register()
    landmarks_p_picker.register()
    optimize_model.register()
    panel.register()
    
    
    #Dual Arch Stuff
    dual_elements.register()
    button_placement.register()
    dual_visualization.register()
    notch_cut.register()
    design_validation.register()
    d3dual_pick_face_model.register()
    d3dual_facial_landmarks.register()
    d3dual_wax_rim.register()
    d3dual_stored_positions.register()
    
    bpy.app.handlers.load_post.append(load_post_method)
    bpy.app.handlers.save_pre.append(save_pre_method)
    bpy.app.handlers.frame_change_pre.append(pause_playback)
    #bpy.app.handlers.load_pre.append(load_pre_method)
    
def unregister():
    #import the relevant modules
    from . import ( d3classes, odcutils, splint, 
                    panel, curve_partition, articulator, 
                    splint_landmark_fns, model_work,                    #                  tracking, 
                    splint_booleans, import_export,splint_face_bow,
                    meta_modelling, articulator_handlers, attachments)
    
    bpy.app.handlers.save_pre.remove(save_pre_method)
    bpy.app.handlers.load_post.remove(load_post_method)
    bpy.app.handlers.frame_change_pre.remove(pause_playback)
    
    #bpy.utils.unregister_module(__name__)
    bpy.utils.unregister_class(D3SplintAddonPreferences)
    bpy.utils.unregister_class(D3Splint_OT_addon_prefs)
    
    #unregister them
    d3classes.unregister()
    odcutils.unregister()

    splint.unregister()
    articulator.unregister()
    panel.unregister()
    curve_partition.unregister()
    splint_landmark_fns.unregister()
    splint_booleans.unregister()
    model_work.unregister()
    import_export.unregister()
    splint_face_bow.unregister()
    meta_modelling.unregister()
    articulator_handlers.unregister()
    attachments.unregister()
    tooth_library.unregister()
    #unregister this module
 
if __name__ == "__main__":
    register()

# ---- Perplexity API Suggested Migrations ----
To migrate your Blender 2.79 property definitions to Blender 4.4, you must use the new annotation syntax for properties inside classes, and register them as class attributes using type annotations. The direct assignment to bpy.props outside of classes is deprecated.

Below are the corrected code lines for Blender 4.4+:

```python
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty

class MyAddonProperties(bpy.types.PropertyGroup):
    cork_lib: StringProperty()
    dev: BoolProperty(name="Development Mode")
    non_clinical_use: BoolProperty(
        default=False,
        name='Not For Clinical Use',
        description='By checking this box you certify that you are using this for non-clinical, training or educational purposes'
    )
    # auto_use_background: BoolProperty(
    #     default=True,
    #     name='Auto Background',
    #     description='allow D3Splint to do some tasks automatically based on user preferences'
    # )
    # auto_optimize: BoolProperty(
    #     default=False,
    #     name='Auto Optimize Models',
    #     description='allow D3Splint to do some tasks automatically based on user preferences'
    # )
    auto_blockout: BoolProperty(
        default=False,
        name='Auto BLockout Large Concavities',
        description='Always automatically blockout concavities after rim fusion'
    )
    auto_remesh_smooth: BoolProperty(
        default=False,
        name='Auto Remesh Smooth',
        description='Always automatically do remesh and smooth after rim fusion'
    )
    default_jaw_type: EnumProperty(
        name='Jaw Type',
        # ... (add items and other parameters as needed)
    )
    default_workflow_type: EnumProperty(
        name='Workflow Type',
        # ... (add items and other parameters as needed)
    )
    show_picking: BoolProperty(
        default=False,
        name='Show Picking'
    )

# Register the property group and add it to a type, e.g., Scene
def register():
    bpy.utils.register_class(MyAddonProperties)
    bpy.types.Scene.my_addon = bpy.props.PointerProperty(type=MyAddonProperties)

def unregister():
    del bpy.types.Scene.my_addon
    bpy.utils.unregister_class(MyAddonProperties)
```

Key changes:
- Use **type annotations** (e.g., `cork_lib: StringProperty()`) inside a subclass of `bpy.types.PropertyGroup`.
- Register the property group and attach it to a Blender data type (e.g., `Scene`) using a `PointerProperty`.
- Do not assign properties directly to `bpy.props` or Blender types outside of a class definition[4].

This is the Blender 4.4+ standard for custom properties.
To migrate your Blender 2.79 property definitions to Blender 4.4, you must use the new property function syntax and assign properties as class annotations (not as direct class attributes). The old bpy.props.*Property assignment is deprecated. Here is the corrected code block for Blender 4.4:

```python
import bpy
from bpy.props import BoolProperty, EnumProperty

class MyProperties(bpy.types.PropertyGroup):
    show_articulator: BoolProperty(default=False, name='Show Articulator')
    show_wax: BoolProperty(default=False, name='Show Wax')
    show_shape_refinement: BoolProperty(default=False, name='Show Shape Refinement')
    show_deprogrammer: BoolProperty(default=False, name='Show Deprogrammer')
    show_shell: BoolProperty(default=False, name='Show Shell')
    show_fit_and_retention: BoolProperty(default=False, name='Show Fit and Retention')
    show_occlusion: BoolProperty(default=False, name='Show Occlusion')
    show_finalize: BoolProperty(default=False, name='Show Finalize')
    show_outdated_tools: BoolProperty(default=False, name='Show Outdated')
    attachment_lib: EnumProperty(name='Attachment Library', items=[('A', 'A', ''), ('B', 'B', '')])
```

**Key changes:**
- Use **type annotations** (the colon syntax) instead of direct assignment.
- Define properties inside a class derived from `bpy.types.PropertyGroup`.
- Register this class and assign it to a data block (e.g., `bpy.types.Scene.my_props = PointerProperty(type=MyProperties)`).

This syntax is required for Blender 2.80+ and is fully compatible with Blender 4.4[2][5].
To migrate your Blender 2.79 property definitions to Blender 4.4, you must now define properties as class attributes within a bpy.types.PropertyGroup or similar class, and register them using type annotations. The direct assignment to bpy.props at the module level is deprecated.

Here is the corrected code block for Blender 4.4:

```python
import bpy
from bpy.props import (
    EnumProperty,
    BoolProperty,
    IntProperty,
)

class MyProperties(bpy.types.PropertyGroup):
    attachment_ob: EnumProperty(name='Attachment Object')
    tooth_lib: EnumProperty(name='Tooth Library')
    tooth_lib_ob: EnumProperty(name='Tooth Object')
    use_alpha_tools: BoolProperty(name='Use Alpha Tools')
    use_poly_cut: BoolProperty(name='Use Poly Cut')
    auto_check_update: BoolProperty(name='Auto Check Update')
    updater_intrval_months: IntProperty(name='Updater Interval Months')
    updater_intrval_days: IntProperty(name='Updater Interval Days')
    updater_intrval_hours: IntProperty(name='Updater Interval Hours')
    updater_intrval_minutes: IntProperty(name='Updater Interval Minutes')
```

**Key changes:**
- Properties are now defined as class attributes with type annotations inside a PropertyGroup subclass.
- Use the colon (:) syntax, not equals (=), for property definitions.
- Register your PropertyGroup and assign it to a context (e.g., bpy.types.Scene) as needed.

This approach is required for Blender 2.8+ and fully compatible with Blender 4.4[3].
In **Blender 4.4**, the use of `bpy.props.BoolProperty` for class-level property definitions is deprecated. You should now use Python's type annotations with `bpy.props` as the value. Here is how to migrate your code:

```python
import bpy

class MyPropertyGroup(bpy.types.PropertyGroup):
    show_occlusal_mod: bpy.props.BoolProperty(
        name="Show Occlusal Mod",
        description="Show the occlusal modification",
        default=False
    )
    show_survey_functions: bpy.props.BoolProperty(
        name="Show Survey Functions",
        description="Show the survey functions",
        default=False
    )
```

**Key changes:**
- Use type annotations (`:`) instead of assignment (`=`) for property definitions at the class level.
- The rest of the property definition (name, description, default) remains the same.

This is the Blender 4.4 compatible way to define properties in a `PropertyGroup` or similar class.
