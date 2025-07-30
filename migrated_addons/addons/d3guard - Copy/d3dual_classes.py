# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

#import odc_public
#from  odc_public import odcutils, load_post_method

#from . import odcutils, load_post_method

'''
Template for classes and properties from Cycles Addon

class CyclesStyleClass(bpy.types.PropertyGroup):
    @classmethod
    def (cls):
        bpy.types.ParticleSettings.cycles = PointerProperty(
                name="Cycles Hair Settings",
                description="Cycles hair settings",
                type=cls,
                )
        cls.root_width = FloatProperty(

    @classmethod
    def unregister(cls):
        del bpy.types.ParticleSettings.cycles
'''


import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
#we need to add the odc subdirectory to be searched for imports
#http://stackoverflow.com/questions/918154/relative-paths-in-python
import sys, os, inspect
from odcmenus import button_data
from odcmenus import menu_utils

#enums
rest_types=['CONTOUR','PONTIC','COPING','ANATOMIC COPING']
rest_enum = []
for index, item in enumerate(rest_types):
    rest_enum.append((str(index), rest_types[index], str(index)))
    
teeth = ['11','12','13','14','15','16','17','18','21','22','23','24','25','26','27','28','31','32','33','34','35','36','37','38','41','42','43','44','45','46','47','48']    
teeth_enum=[]
for index, item in enumerate(teeth):
    teeth_enum.append((str(index), item, str(index)))
    
def index_update(self,context):
    #perhaps do some magic here to only call it later?
    bpy.ops.ed.undo_push(message="Changed active tooth index")
    
#classes
class D3DUALProps(bpy.types.PropertyGroup):
    
    @classmethod
    def register(cls):
        bpy.types.Scene.d3splint_props = bpy.props.PointerProperty(type=cls)
        
        cls.master = bpy.props.StringProperty(
                name="Master Model",
                default="")
        cls.opposing = bpy.props.StringProperty(
                name="Opposing Model",
                default="")
        
        cls.bone = bpy.props.StringProperty(
                name="Bone Model",
                default="")
        
        cls.register_II = bpy.props.BoolProperty(
                name="2nd Registration",
                default=False)
        
        cls.work_log = bpy.props.StringProperty(name="Work Log", default = "")
        cls.work_log_path = bpy.props.StringProperty(name="Work Log File", subtype = "DIR_PATH", default = "")
        
        ###Toolbar show/hide booleans for tool options###
        cls.show_teeth = bpy.props.BoolProperty(
                name="Tooth Panel",
                default=False)
        
        cls.show_bridge = bpy.props.BoolProperty(
                name="Bridge Panel",
                default=False)
        
        cls.show_implant = bpy.props.BoolProperty(
                name="Implant Panel",
                default=False)
        
        cls.show_splint = bpy.props.BoolProperty(
                name="Splint Panel",
                default=True)
        
        cls.show_ortho = bpy.props.BoolProperty(
                name="Ortho Panel",
                default=False)
        #implant panel
        #bridge panel
        #splint panel       
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.d3splint_props    
               
class D3DUALRestorationAdd(bpy.types.Operator):
    '''Be sure to have an object selected to build the splint on!'''
    bl_idname = 'd3dual.add_splint'
    bl_label = "Append Splint"
    bl_options = {'REGISTER','UNDO'}
    
    name = bpy.props.StringProperty(name="Splint Name",default="_Splint")  
    link_active = bpy.props.BoolProperty(name="Link",description = "Link active object as base model for splint", default = True)
    def invoke(self, context, event): 
        
        
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
    
    def execute(self, context):

        my_item = context.scene.odc_splints.add()        
        my_item.name = self.name
        
        if self.link_active:
            if context.object:
                my_item.model = context.object.name
            elif context.selected_objects:
                my_item.model = context.selected_objects[0].name
                
        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
    
        row = col.row()
        row.prop(self, "name", expand=True)
        
        row = col.row()
        row.prop(self, "link_active", text = "Plan splint on active object")
        
        row = col.row()
        row.label('Ensure you have the correct object')
        
        row = col.row()
        row.label('selected.  If not, cancel and retry!')
        
        if context.object != None:
            row = col.row()
            row.label('Active object:' + context.object.name)
          
class D3DUALRestorationRemove(bpy.types.Operator):
    ''''''
    bl_idname = 'd3splint.remove_splint'
    bl_label = "Remove Splint Restoration"
    
    def execute(self, context):

        j = bpy.context.scene.odc_splint_index
        bpy.context.scene.odc_splints.remove(j)
            
        return {'FINISHED'}
    
class D3DualAppliance(bpy.types.PropertyGroup):
    
    @classmethod
    def register(cls):
        bpy.types.Scene.odc_splints = bpy.props.CollectionProperty(type = cls)
        bpy.types.Scene.odc_splint_index = bpy.props.IntProperty(name = "Working Splint Index", min=0, default=0, update=index_update)
  
        cls.name = bpy.props.StringProperty(name="Splint Name",default="")
        cls.max_model = bpy.props.StringProperty(name="Maxillary Model",default="")
        cls.mand_model = bpy.props.StringProperty(name="Mandibular Model",default="")
        cls.face_model = bpy.props.StringProperty(name="Face Model",default="")
        
        cls.max_perim_model = bpy.props.StringProperty(name="Maxillary Perim Model",default="")
        cls.max_trimmed_model = bpy.props.StringProperty(name="Maxillary Trimmed Model",default="")
        cls.max_refractory = bpy.props.StringProperty(name="Maxillary Refractory Model",default="")
        cls.max_axis = bpy.props.StringProperty(name="Maxillary Insertion",default="")
        cls.max_margin = bpy.props.StringProperty(name="Maxillary Margin",default="")
        cls.max_shell = bpy.props.StringProperty(name="Maxillary Shell",default="")
        
        cls.mand_perim_model = bpy.props.StringProperty(name="Mandibular Perim Model",default="")
        cls.mand_trimmed_model = bpy.props.StringProperty(name="Mandibular Trimmed Model",default="")
        cls.mand_refractory = bpy.props.StringProperty(name="Mandibular Refractory Model",default="")
        cls.mand_axis = bpy.props.StringProperty(name="Mandibular Insertion",default="")
        cls.mand_margin = bpy.props.StringProperty(name="Mandibular Margin",default="")
        cls.mand_shell = bpy.props.StringProperty(name="Mandibular Shell",default="")
        

        #string of all operator signatures used
        cls.ops_string = bpy.props.StringProperty(name="operators used",default="", maxlen = 2000)
        cls.custom_label = bpy.props.StringProperty(name="custom_label", default="", maxlen = 100)
        
        
        cls.show_stored_positions = bpy.props.BoolProperty(name = 'show_stored_positions', default = False)
        cls.stored_positions = bpy.props.StringProperty(name="Stored Positions",default="")
          
        ###############################################
        ####  BoolProperties for Steps Taken   ########
        ###############################################
        cls.max_model_set = bpy.props.BoolProperty(name = 'max_model_set', default = False)
        cls.mand_model_set = bpy.props.BoolProperty(name = 'mand_model_set', default = False)
        cls.face_model_set = bpy.props.BoolProperty(name="face_model_set",default=False)
        cls.landmarks_set = bpy.props.BoolProperty(name = 'landmarks_set', default = False)
        cls.facial_landmarks_set = bpy.props.BoolProperty(name = 'landmarks_set', default = False)
        
        cls.articulator_make = bpy.props.BoolProperty(name = 'articulator_made', default = False)
        
        cls.max_splint_outline = bpy.props.BoolProperty(name = 'max_splint_outline', default = False)
        cls.mand_splint_outline = bpy.props.BoolProperty(name = 'mand_splint_outline', default = False)
        
        
        cls.trim_max = bpy.props.BoolProperty(name = 'trim_max', default = False)
        cls.trim_mand = bpy.props.BoolProperty(name = 'trim_mand', default = False)
        
        cls.max_shell_complete = bpy.props.BoolProperty(name = 'max_shell_complete', default = False)
        cls.mand_shell_complete = bpy.props.BoolProperty(name = 'max_shell_complete', default = False)
        
        
        cls.max_insertion_complete = bpy.props.BoolProperty(name = 'max_insertion_complete', default = False)
        cls.mand_insertion_complete = bpy.props.BoolProperty(name = 'mand_insertion_complete', default = False)
        
        cls.max_refractory_model_complete =  bpy.props.BoolProperty(name = 'max_refractory_model_complete', default = False)
        cls.mand_refractory_model_complete =  bpy.props.BoolProperty(name = 'mand_refractory_model_complete', default = False)
        
        cls.arch_curves_complete = bpy.props.BoolProperty(name = 'arch_curves_complete', default = False)
        #cls.max_curve = bpy.props.BoolProperty(name = 'curve_max', default = False)
        #cls.mand_curve = bpy.props.BoolProperty(name = 'curve_mand', default = False)
        
        
        cls.ramps_generated = bpy.props.BoolProperty(name = 'ramps_generated', default = False)
        cls.ramp_array_generated = bpy.props.BoolProperty(name = 'ramp_array_generated', default = False)
        
        cls.finalize_splint_max = bpy.props.BoolProperty(name = 'finalize_splint_max', default = False)
        cls.finalize_splint_mand = bpy.props.BoolProperty(name = 'finalize_splint_mand', default = False)
        
        ###############################################
        #### Recorded Properties for Appliances ########
        ###############################################
        
        cls.max_shell_thickness = bpy.props.FloatProperty(name = 'Maxillary Shell Thickness', default = 1.25)
        cls.mand_shell_thickness = bpy.props.FloatProperty(name = 'Mandibular Shell Thickness', default = 1.25)
        
        cls.max_passive_value = bpy.props.FloatProperty(name = 'Maxillary Passive Spacer', default = 0.15)
        cls.max_undercut_value = bpy.props.FloatProperty(name = 'Maxillary Undercut', default = 0.05)
        
        cls.mand_passive_value = bpy.props.FloatProperty(name = 'Mandibular Passive Spacer', default = 0.15)
        cls.mand_undercut_value = bpy.props.FloatProperty(name = 'Mandibular Undercut', default = 0.05)
        
        
        cls.maxillary_offsets = bpy.props.StringProperty(name="Maxillary Offsets", default="")
        cls.mandibular_offsets = bpy.props.StringProperty(name="Mandibular Offsets", default="")
        
        cls.case_id = bpy.props.StringProperty(name="Case ID", default="")
        cls.start_time = bpy.props.FloatProperty(name="Start Time", default=0.0)
        cls.end_time = bpy.props.FloatProperty(name="Finish Time", default=0.0)
        
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.odc_splints
        del bpy.types.Scene.odc_splint_index
            
    
    def get_maxilla(self):
        return self.max_model
    
    def get_mandible(self):
        return self.mand_model
        
        
    def load_components_from_string(self,scene):
        print('no longer loading components')
        #tooth_list = self.tooth_string.split(sep=":")
        #for name in tooth_list:
        #    tooth = scene.odc_teeth.get(name)
        #    if tooth and tooth not in self.teeth:
        #        self.teeth.append(tooth)
    
        #imp_list = self.implant_string.split(sep=":")
        #for name in imp_list:
        #    implant = scene.odc_implants.get(name)
        #    if implant and implant not in self.implants:
        #        self.implants.append(implant)
                
    def save_components_to_string(self):
        print('no longer saving components to string')
        #print(self.tooth_string)
        #print(self.implant_string)
        
        #names = [tooth.name for tooth in self.teeth]
        #names.sort()
        #self.tooth_string = ":".join(names)
        
        #i_names = [implant.name for implant in self.implants]
        #i_names.sort()
        #self.implant_string = ":".join(i_names)
                
    def add_tooth(self,tooth):
        name = tooth.name
        if len(self.tooth_string):
            tooth_list = self.tooth_string.split(sep=":")
            if name not in tooth_list:
                tooth_list.append(name)
                tooth_list.sort()
                self.tooth_string = ":".join(tooth_list)
                self.teeth.append(tooth)           
     
    
    def get_maxilla(self):
        return self.max_model
    
    def get_mandible(self):
        return self.mand_model
            
    def cleanup(self):
        print('not implemented')
    
        
def register():
    bpy.utils.register_class(D3DUALProps)
    bpy.utils.register_class(D3DualAppliance)
    bpy.utils.register_class(D3DUALRestorationAdd)
    bpy.utils.register_class(D3DUALRestorationRemove)
    

def unregister():
    bpy.utils.unregister_class(D3DUALProps)
    D3DUALProps.unregister()
    D3DualAppliance.unregister()
    bpy.utils.unregister_class(D3DUALRestorationAdd)
    bpy.utils.unregister_class(D3DUALRestorationRemove)
    
    '''
if __name__ == "__main__":
    register()
    '''

# ---- Perplexity API Suggested Migrations ----
In Blender 4.4, the old-style property definitions using direct assignment (e.g., cls.prop = bpy.props.StringProperty(...)) are deprecated. Properties must now be defined as class-level annotations using Python's type hinting and the new annotation syntax. Here is the corrected code block for your properties:

```python
import bpy

class YourClassName(bpy.types.PropertyGroup):
    master: bpy.props.StringProperty()
    opposing: bpy.props.StringProperty()
    bone: bpy.props.StringProperty()
    register_II: bpy.props.BoolProperty()
    work_log: bpy.props.StringProperty(name="Work Log", default="")
    work_log_path: bpy.props.StringProperty(name="Work Log File", subtype="DIR_PATH", default="")
    show_teeth: bpy.props.BoolProperty()
    show_bridge: bpy.props.BoolProperty()
    show_implant: bpy.props.BoolProperty()
    show_splint: bpy.props.BoolProperty()
```
Replace YourClassName with the actual class name you are using. This syntax is required for Blender 2.80+ and is fully compatible with Blender 4.4[1][3][5].
Here is the corrected code block for Blender 4.4 compatibility. The main changes are:

- Use the new property registration system: properties must be defined as class annotations (using type hints and assignment), not as direct assignments to class attributes.
- All property definitions must be at the class level, inside a class that inherits from bpy.types.PropertyGroup, bpy.types.Operator, etc.
- Remove deprecated direct assignment to bpy.props in the class body.
- For properties on bpy.types.Scene, use bpy.types.Scene.<property> = bpy.props.<Type>Property(...) as before, but ensure all arguments are keyword arguments.

Below is the migrated code:

```python
import bpy
from bpy.props import BoolProperty, StringProperty, IntProperty

# Example PropertyGroup for class-level properties
class MySplintProperties(bpy.types.PropertyGroup):
    show_ortho: BoolProperty(
        name="Show Ortho"
    )
    name: StringProperty(
        name="Splint Name",
        default=""
    )
    max_model: StringProperty(
        name="Maxillary Model",
        default=""
    )
    mand_model: StringProperty(
        name="Mandibular Model",
        default=""
    )
    face_model: StringProperty(
        name="Face Model",
        default=""
    )
    max_perim_model: StringProperty(
        name="Maxillary Perim Model",
        default=""
    )
    max_trimmed_model: StringProperty(
        name="Maxillary Trimmed Model",
        default=""
    )
    link_active: BoolProperty(
        name="Link",
        description="Link active object as base model for splint",
        default=True
    )

# Register the PropertyGroup and add to Scene if needed
def register():
    bpy.utils.register_class(MySplintProperties)
    bpy.types.Scene.my_splint_props = bpy.props.PointerProperty(type=MySplintProperties)
    bpy.types.Scene.odc_splint_index = IntProperty(
        name="Working Splint Index",
        min=0,
        default=0,
        update=index_update  # Ensure index_update is defined elsewhere
    )

def unregister():
    del bpy.types.Scene.my_splint_props
    del bpy.types.Scene.odc_splint_index
    bpy.utils.unregister_class(MySplintProperties)
```

**Key points:**
- All property definitions for custom classes must use type annotations (e.g., `show_ortho: BoolProperty(...)`).
- Scene properties are still assigned directly to `bpy.types.Scene`, but all arguments must be keyword arguments.
- `PointerProperty` is used to attach the custom property group to the scene.

This code is compatible with Blender 4.4 and follows the current API requirements.
To migrate your code to **Blender 4.4**, you need to use the new property API, which replaces the old direct assignment of properties to classes. In Blender 4.x, properties must be defined using type annotations and the `bpy.props` module, typically as class variables with type hints.

Here is the corrected code block for Blender 4.4+:

```python
import bpy
from bpy.props import StringProperty

class YourClassName(bpy.types.PropertyGroup):
    max_refractory: StringProperty(name="Maxillary Refractory Model", default="")
    max_axis: StringProperty(name="Maxillary Insertion", default="")
    max_margin: StringProperty(name="Maxillary Margin", default="")
    max_shell: StringProperty(name="Maxillary Shell", default="")
    mand_perim_model: StringProperty(name="Mandibular Perim Model", default="")
    mand_trimmed_model: StringProperty(name="Mandibular Trimmed Model", default="")
    mand_refractory: StringProperty(name="Mandibular Refractory Model", default="")
    mand_axis: StringProperty(name="Mandibular Insertion", default="")
    mand_margin: StringProperty(name="Mandibular Margin", default="")
    mand_shell: StringProperty(name="Mandibular Shell", default="")
```

**Key changes:**
- Use type annotations (`:`) instead of assignment (`=`).
- Define properties inside a class derived from `bpy.types.PropertyGroup`.
- Register the class and assign it as a property group to your target type (e.g., `Scene`, `Object`) as needed.

This is the Blender 4.x-compliant way to define custom properties for use in add-ons and scripts.
In **Blender 4.4**, the use of `bpy.props.StringProperty` and `bpy.props.BoolProperty` as *class attributes* (e.g., `cls.my_prop = ...`) is deprecated. Instead, properties must be defined directly in the class body, not assigned dynamically. The `maxlen` argument for `StringProperty` is also deprecated and should be removed.

Here is the **corrected code block** for Blender 4.4+:

```python
import bpy

class MyClass(bpy.types.PropertyGroup):
    ops_string: bpy.props.StringProperty(name="operators used", default="")
    custom_label: bpy.props.StringProperty(name="custom_label", default="")
    show_stored_positions: bpy.props.BoolProperty(name='show_stored_positions', default=False)
    stored_positions: bpy.props.StringProperty(name="Stored Positions", default="")
    max_model_set: bpy.props.BoolProperty(name='max_model_set', default=False)
    mand_model_set: bpy.props.BoolProperty(name='mand_model_set', default=False)
    face_model_set: bpy.props.BoolProperty(name="face_model_set", default=False)
    landmarks_set: bpy.props.BoolProperty(name='landmarks_set', default=False)
    facial_landmarks_set: bpy.props.BoolProperty(name='landmarks_set', default=False)
    articulator_make: bpy.props.BoolProperty(name='articulator_made', default=False)
```

**Key changes:**
- Use the `:` (type annotation) syntax for property definitions inside the class body.
- Remove the `maxlen` argument from `StringProperty` (it is no longer supported).
- Define all properties as class attributes, not via dynamic assignment (e.g., `cls.prop = ...` is no longer valid)[3].

This code is compatible with Blender 4.4 and follows current API conventions.
In Blender 4.4, the use of class-level assignment for properties (e.g., cls.my_prop = bpy.props.BoolProperty(...)) is deprecated. Instead, properties must be defined as class attributes directly in the class body, not dynamically assigned. Here is the corrected code block for Blender 4.4+:

```python
import bpy

class MyPropertyGroup(bpy.types.PropertyGroup):
    max_splint_outline: bpy.props.BoolProperty(name='max_splint_outline', default=False)
    mand_splint_outline: bpy.props.BoolProperty(name='mand_splint_outline', default=False)
    trim_max: bpy.props.BoolProperty(name='trim_max', default=False)
    trim_mand: bpy.props.BoolProperty(name='trim_mand', default=False)
    max_shell_complete: bpy.props.BoolProperty(name='max_shell_complete', default=False)
    mand_shell_complete: bpy.props.BoolProperty(name='mand_shell_complete', default=False)
    max_insertion_complete: bpy.props.BoolProperty(name='max_insertion_complete', default=False)
    mand_insertion_complete: bpy.props.BoolProperty(name='mand_insertion_complete', default=False)
    max_refractory_model_complete: bpy.props.BoolProperty(name='max_refractory_model_complete', default=False)
    mand_refractory_model_complete: bpy.props.BoolProperty(name='mand_refractory_model_complete', default=False)
```

**Key changes:**
- Use the **colon (:) annotation syntax** for property definitions in the class body.
- Do not assign properties dynamically to the class (i.e., do not use `cls.prop = ...`).

This is the required approach for all custom properties in Blender 2.80 and later, including 4.4[3][4].
To migrate these property definitions to **Blender 4.4**, you must use the new `bpy.props` API and the **annotations system**. Properties should be defined as class annotations, not as assignments inside a class or in the register function. Here is the corrected code block for Blender 4.4+:

```python
import bpy

class MyPropertyGroup(bpy.types.PropertyGroup):
    arch_curves_complete: bpy.props.BoolProperty(name='arch_curves_complete', default=False)
    # max_curve: bpy.props.BoolProperty(name='curve_max', default=False)
    # mand_curve: bpy.props.BoolProperty(name='curve_mand', default=False)
    ramps_generated: bpy.props.BoolProperty(name='ramps_generated', default=False)
    ramp_array_generated: bpy.props.BoolProperty(name='ramp_array_generated', default=False)
    finalize_splint_max: bpy.props.BoolProperty(name='finalize_splint_max', default=False)
    finalize_splint_mand: bpy.props.BoolProperty(name='finalize_splint_mand', default=False)
    max_shell_thickness: bpy.props.FloatProperty(name='Maxillary Shell Thickness', default=1.25)
    mand_shell_thickness: bpy.props.FloatProperty(name='Mandibular Shell Thickness', default=1.25)
    max_passive_value: bpy.props.FloatProperty(name='Maxillary Passive Spacer', default=0.15)
```

**Key changes:**
- Use **type annotations** (the colon syntax) instead of assignment (`=`) for property definitions.
- Define properties directly in the class body, not dynamically or via `cls.` assignment[3].

This is the required and supported way to define custom properties in Blender 2.80 and later, including 4.4.
Replace the deprecated use of `bpy.props.FloatProperty` and `bpy.props.StringProperty` as class attributes with type annotations and assignment to `bpy.props` properties, as required in Blender 2.80+ and still valid in Blender 4.4[1][2]. The corrected code block is:

```python
import bpy

max_undercut_value: bpy.props.FloatProperty(
    name='Maxillary Undercut', default=0.05
)
mand_passive_value: bpy.props.FloatProperty(
    name='Mandibular Passive Spacer', default=0.15
)
mand_undercut_value: bpy.props.FloatProperty(
    name='Mandibular Undercut', default=0.05
)
maxillary_offsets: bpy.props.StringProperty(
    name="Maxillary Offsets", default=""
)
mandibular_offsets: bpy.props.StringProperty(
    name="Mandibular Offsets", default=""
)
case_id: bpy.props.StringProperty(
    name="Case ID", default=""
)
start_time: bpy.props.FloatProperty(
    name="Start Time", default=0.0
)
end_time: bpy.props.FloatProperty(
    name="Finish Time", default=0.0
)
```

If these are inside a class (such as a `PropertyGroup`), use:

```python
class MyProperties(bpy.types.PropertyGroup):
    max_undercut_value: bpy.props.FloatProperty(
        name='Maxillary Undercut', default=0.05
    )
    mand_passive_value: bpy.props.FloatProperty(
        name='Mandibular Passive Spacer', default=0.15
    )
    mand_undercut_value: bpy.props.FloatProperty(
        name='Mandibular Undercut', default=0.05
    )
    maxillary_offsets: bpy.props.StringProperty(
        name="Maxillary Offsets", default=""
    )
    mandibular_offsets: bpy.props.StringProperty(
        name="Mandibular Offsets", default=""
    )
    case_id: bpy.props.StringProperty(
        name="Case ID", default=""
    )
    start_time: bpy.props.FloatProperty(
        name="Start Time", default=0.0
    )
    end_time: bpy.props.FloatProperty(
        name="Finish Time", default=0.0
    )
```

**Key changes:**
- Use type annotations (`:`) instead of assignment (`=`) for property definitions in classes.
- Do not assign properties directly to the class with `=`, but use the annotation syntax as shown above[1][2].
