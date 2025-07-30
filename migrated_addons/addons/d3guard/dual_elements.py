'''
Created on Aug 15, 2017
@author: Patrick

This module contains functions that are used to mark and set
landmarks on the casts.  For example marking splint boundaries
midine etc.

#references for future development
https://blender.stackexchange.com/questions/73514/how-can-i-update-a-popup-while-shown
https://blender.stackexchange.com/questions/8717/property-update-function-for-properties-inside-a-collection/8769#8769
https://developer.blender.org/T39798
https://blenderartists.org/forum/showthread.php?396542-Display-properties-of-a-running-modal-operator-in-a-popup


'''
import os
import blf

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import odcutils
#from points_picker import PointPicker
from textbox import TextBox
from mathutils import Vector, Matrix, Color
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d
import math
from mesh_cut import flood_selection_faces, edge_loops_from_bmedges, flood_selection_faces_limit, space_evenly_on_path
from curve import CurveDataManager, PolyLineKnife
from common_utilities import bversion
import tracking
from odcutils import get_bbox_center, get_settings
from multiprocessing import get_start_method
from common_drawing import outline_region
from bmesh_fns import join_bmesh
from model_labels import split_solidify_remesh
from mathutils.bvhtree import BVHTree

def arch_crv_draw_callback(self, context):  
    self.crv.draw(context)
    self.help_box.draw()
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    outline_region(context.region,(r,g,b,1))    
    

def landmarks_draw_callback(self, context):  
    self.crv.draw(context)
    self.help_box.draw()
    prefs = get_settings()
    r,g,b = prefs.active_region_color
    outline_region(context.region,(r,g,b,1))    


def generate_bmesh_elastic_button(base_diameter = 4,
                                  base_height = 1.5,
                                  stalk_diameter = 2.5,
                                  stalk_height = 1.5,
                                  button_minor = 4,
                                  button_major = 5,
                                  button_height = 1.25,
                                  base_curvature_x = .3,
                                  base_curvature_y = .2,
                                  base_torque = 0):
    
    
        
    bme = bmesh.new()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    
    diameters = [base_diameter, stalk_diameter, button_minor]
    segments = [base_height, stalk_height, button_height]
    
    pairs = []
    pairs.append((.2 * base_diameter, 0))
    pairs.append((.9 * base_diameter, 0))
    
    pairs.append((base_diameter, 0))
    pairs.append((base_diameter, .25 * base_height))
    pairs.append((base_diameter, .75 * base_height))
    pairs.append((base_diameter, base_height))
    
    
    delta = stalk_diameter - base_diameter
    
    pairs.append((base_diameter + .25* delta, base_height))
    pairs.append((base_diameter + .75* delta, base_height))
    
    pairs.append((stalk_diameter, base_height))
    
    
    pairs.append((stalk_diameter, .25 * stalk_height + base_height))
    pairs.append((stalk_diameter, .75 * stalk_height + base_height))
    pairs.append((stalk_diameter, stalk_height + base_height))
    
    
    delta = button_minor - stalk_diameter
    pairs.append((stalk_diameter + .25 * delta, stalk_height + base_height))
    pairs.append((stalk_diameter + .75 * delta, stalk_height + base_height))
    
    
    pairs.append((button_minor, stalk_height + base_height + .25 * button_height))
    pairs.append((button_minor, stalk_height + base_height + .75 * button_height))
    pairs.append((button_minor, base_height + stalk_height + .9 * button_height))
    pairs.append((.7 * button_minor, base_height + stalk_height + button_height))
    pairs.append((.5 * button_minor, base_height + stalk_height + button_height))
    
    #initialize the base circle
    circle_data = bmesh.ops.create_circle(bme, cap_ends = True, segments = 64, diameter = .2 * base_diameter/2)
    bme.edges.ensure_lookup_table()
    new_eds = bme.edges[:]
    
    base_vs = bme.verts[:]
    button_vs = []
    tip_vs = []
    bottom_tip_vs = []
    
    for i, pair in enumerate(pairs):
        print(i, pair)
        r = pair[0]/2.0
        h = pair[1]
        
        if i == 0:
            continue
        
        gdict = bmesh.ops.extrude_edge_only(bme, edges = new_eds)  
        new_eds = [ed for ed in gdict['geom'] if isinstance(ed, bmesh.types.BMEdge)]
        vs = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)]
        for v in vs:
            v.co[2] = h
            
            R = Vector((v.co[0],v.co[1]))
            L = R.length
            s = r/L
        
            R_prime = s * R
        
            v.co[0], v.co[1] = R_prime[0], R_prime[1]
            
        
        if i < 8:
            base_vs += vs
            
        if i > (len(pairs) - 7):
            button_vs += vs
            
        if i > (len(pairs) -6) and i < (len(pairs) - 1):
            tip_vs += vs
        
        if i == (len(pairs) -6):
            bottom_tip_vs += vs
            
        bme.edges.ensure_lookup_table()
        bme.verts.ensure_lookup_table()
    
    
    rot_center = Vector((0,0, base_height))
    R = Matrix.Rotation(base_torque * math.pi/180, 4, Vector((1,0,0)))
    
    for v in base_vs:
        factor_y = abs(v.co[0])/(base_diameter/2.0)
        factor_x = abs(v.co[1])/(base_diameter/2.0)
        v.co[2] -= (factor_y ** 2) * base_curvature_y + (factor_x ** 2) * base_curvature_x
        
        v_trans = v.co - rot_center
        v_rot = R * v_trans
        v_final = v_rot + rot_center
        
        v.co = v_final
        
    for v in button_vs:
        if v.co[0] > 0.01:
            factor = v.co[0]/(button_minor/2.0)
            delta = (button_major - button_minor)/2
            
            v.co[0] += factor**2 * delta
    for v in tip_vs:
        if v.co[0] > 0.01:
            factor = v.co[0]/(button_major/2.0)
            v.co[2] -= factor**2 * .7
    
    for v in bottom_tip_vs:
        if v.co[0] > 0.01:
            factor = v.co[0]/(button_major/2.0)
            v.co[2] -= factor**2 * .3
                    
    
    for v in bme.verts:
        v.co += Vector((0,0,-base_height + 1))
                        
    bme.faces.ensure_lookup_table()
    bme.faces.new(vs)  #cap the last face
    
    bmesh.ops.recalc_face_normals(bme, faces = bme.faces[:])
    
    return bme


class D3DUAL_OT_elastic_button(bpy.types.Operator):
    """Create an elastic button"""
    bl_idname = "d3splint.elastic_button"
    bl_label = "Elastic Button"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    base_diameter = bpy.props.FloatProperty(default =4, description = 'diameter of bonding pad')
    base_height = bpy.props.FloatProperty(default = 1.5, description = 'thickness of bonding pad')
    stalk_diameter = bpy.props.FloatProperty(default =2, description = 'diameter of stalk')
    stalk_height = bpy.props.FloatProperty(default =2, description = 'height of stalk')
    button_minor = bpy.props.FloatProperty(default =3, description = 'Diameter of button')
    button_major = bpy.props.FloatProperty(default =5, description = 'Diameter of button tip')
    button_height = bpy.props.FloatProperty(default =1.5, description = 'Thickness of button')
    base_curvature_y = bpy.props.FloatProperty(default =.2, description = 'Curvature of base y direction')
    base_curvature_x = bpy.props.FloatProperty(default =.2, description = 'Curvature of base x direction')                              
    base_torque = bpy.props.IntProperty(default =0, min = -45, max = 45, description = 'Torque of base')
    #mode =   bpy.props.EnumProperty(name = 'New or Modify', items = (('RIGHT', 'RIGHT','RIGHT'),('LEFT','LEFT','LEFT')), defualt = 'RIGHT')                            
    @classmethod
    def poll(cls, context):
        #if not context.object: return False
        #if 'Ramp' in context.object.name:
        #    return True
        
        return True
    def invoke(self, context, event):
        
        #ob_a = context.object
        #if ob_a == None:
        #    return context.window_manager.invoke_props_dialog(self)
        
        #if ob_a.get('slice_angle'):
        #    self.slice_angle = ob_a['slice_angle'] 
        #if ob_a.get('total_thickness'):
        #    self.total_thickness = ob_a['total_thickness']
        #if ob_a.get('anterior_h'):
        #    self.anterior_h = ob_a['anterior_h']
        #if ob_a.get('posterior_h'):
        #    self.posterior_h = ob_a['posterior_h']
        #if ob_a.get('anterior_length'):
        #    self.anterior_length = ob_a['anterior_length']
        #if ob_a.get('posterior_length'):
        #    self.posterior_length = ob_a['posterior_length']
        #if ob_a.get('bucco_lingual_width'):
        #    self.bucco_lingual_width = ob_a['bucco_lingual_width']
        #if ob_a.get('mandibular_advance'):   
        #    self.mandibular_advance = ob_a['mandibular_advance']
        #if ob_a.get('maxillary_advance'):
        #    self.maxillary_advance = ob_a['maxillary_advance']
        
        return context.window_manager.invoke_props_dialog(self)
        
    def execute(self, context):
        
        if "Button Mat" not in bpy.data.materials:
            a_mat = bpy.data.materials.new('Button Mat')
            a_mat.diffuse_color = Color((0,.8,.4))
            #mat.diffuse_intensity = 1
            #mat.emit = .8
        else:
            a_mat = bpy.data.materials.get('Button Mat')
          
        me = bpy.data.meshes.new("Elastic Button")
        ob = bpy.data.objects.new("Elastic Button", me)
        context.scene.objects.link(ob)
        
        ob.location = context.scene.cursor_location    
        me.materials.append(a_mat)
        #me_p.materials.append(p_mat)
        
        #p_group = ob_p.vertex_groups.new('Posterior Block')
        #a_group = ob_p.vertex_groups.new('Anterior Block')
        
        #mod_a = ob_p.modifiers.new('Posterior Mask', type = 'MASK')
        #mod_a.vertex_group = "Posterior Block"
        #mod_a.show_viewport = False
        
        #mod_p = ob_p.modifiers.new('Anterior Mask', type = 'MASK')
        #mod_p.vertex_group = "Anterior Block"
        #mod_p.show_viewport = False           
        
        bme_b = generate_bmesh_elastic_button(base_diameter = self.base_diameter,
                                              base_height = self.base_height,
                                              stalk_diameter = self.stalk_diameter,
                                              stalk_height = self.stalk_height,
                                              button_minor = self.button_minor,
                                              button_major = self.button_major,
                                              button_height = self.button_height,
                                              base_curvature_x = self.base_curvature_x,
                                              base_curvature_y = self.base_curvature_y,
                                              base_torque = self.base_torque)
        
                    
        #set ID props        
        ob['base_diameter'] =  self.base_diameter
        ob['base_heigt'] = self.base_height
        ob['stalk_diameter'] = self.stalk_diameter
        ob['stalk_height'] = self.stalk_height
        ob['button_major'] = self.button_major
        ob['button_minor'] = self.button_minor
        ob['button_height'] =  self.button_height
        ob['base_curvature_x'] = self.base_curvature_x
        ob['base_curvature_y'] = self.base_curvature_y
        ob['base_torque'] = self.base_torque
        
        mod = ob.modifiers.new('Subsurf', type = 'SUBSURF')
        mod.levels = 2
        
        bme_b.to_mesh(me)
        #update the mesh so it redraws
        me.update()

        bme_b.free()
        
        return {'FINISHED'}
    

class D3DUAL_OT_fuse_elastic_buttons(bpy.types.Operator):
    """Fuse elastic buttons to their snapped object"""
    bl_idname = "d3splint.elastic_button_fuse"
    bl_label = "Finalize Buttons/Hooks"
    bl_options = {'REGISTER', 'UNDO'}
    
    
                          
    @classmethod
    def poll(cls, context):
        #if not context.object: return False
        #if 'Ramp' in context.object.name:
        #    return True
        
        return True
        
    def execute(self, context):
        
        buttons = [ob for ob in bpy.data.objects if (('Elastic Button' in ob.name) or ('Elastic Hook' in ob.name))]
        
        for b in buttons:
            p = b.parent
            if not p: continue
            
            mod = p.modifiers.get(b.name)
            if mod == None:
                mod = p.modifiers.new(b.name, type = 'BOOLEAN')
                
            mod.operation = 'UNION'
            mod.object = b
            b.hide = True
            
        return {'FINISHED'}
    
    
class D3DUAL_OT_finalize_all_notches(bpy.types.Operator):
    """Fuse elastic buttons to their snapped object"""
    bl_idname = "d3splint.finalize_all_notches"
    bl_label = "Finalize Buttons/Hooks/Notches"
    bl_options = {'REGISTER', 'UNDO'}
    
    
                          
    @classmethod
    def poll(cls, context):
        #if not context.object: return False
        #if 'Ramp' in context.object.name:
        #    return True
        
        return True
        
    def execute(self, context):
        
        MaxShell = bpy.data.objects.get('Max Splint Shell')
        MandShell = bpy.data.objects.get('Mand Splint Shell')
        
        
        for ob in [MaxShell, MandShell]:
            if len(ob.modifiers) == 0: continue
            
            old_mesh = ob.data
            # settings for to_mesh
            apply_modifiers = True
            settings = 'PREVIEW'
            new_mesh = ob.to_mesh(context.scene, apply_modifiers, settings)

            # object will still have modifiers, remove them
            ob.modifiers.clear()
        
            # assign the new mesh to obj.data 
            ob.data = new_mesh
        
            # remove the old mesh from the .blend
            bpy.data.meshes.remove(old_mesh)
            
            
        
            
        return {'FINISHED'}
            
def update_elastic_button(self, context):
    if self.hold_update:
        return
    
    ob = context.object
    me = ob.data
    
    bme_b = generate_bmesh_elastic_button(base_diameter = self.base_diameter,
                                              base_height = self.base_height,
                                              stalk_diameter = self.stalk_diameter,
                                              stalk_height = self.stalk_height,
                                              button_minor = self.button_minor,
                                              button_major = self.button_major,
                                              button_height = self.button_height,
                                              base_curvature_x = self.base_curvature_x,
                                              base_curvature_y = self.base_curvature_y,
                                              base_torque= self.base_torque)
            
                       
                
    #set ID props        
    ob['base_diameter'] =  self.base_diameter
    ob['base_heigt'] = self.base_height
    ob['stalk_diameter'] = self.stalk_diameter
    ob['stalk_height'] = self.stalk_height
    ob['button_major'] = self.button_major
    ob['button_minor'] = self.button_minor
    ob['button_height'] =  self.button_height
    ob['base_curvature_x'] = self.base_curvature_x
    ob['base_curvature_y'] = self.base_curvature_y
    ob['base_torque'] = self.base_torque
    
    
    bme_b.to_mesh(me)
    #update the mesh so it redraws
    me.update()

    bme_b.free()
    
    return
    
class D3DUAL_OT_update_elastic_button(bpy.types.Operator):
    """Edit an elastic button"""
    bl_idname = "d3splint.elastic_button_edit"
    bl_label = "Edit Elastic Button"
    bl_options = {'REGISTER', 'UNDO'}
    
    hold_update =  bpy.props.BoolProperty(default = True, description = 'Pause auto update')
    base_diameter = bpy.props.FloatProperty(default =4, description = 'diameter of bonding pad', update = update_elastic_button)
    base_height = bpy.props.FloatProperty(default = 1.5, description = 'thickness of bonding pad', update = update_elastic_button)
    base_curvature_y = bpy.props.FloatProperty(default =.2, description = 'Curvature of base y direction', update = update_elastic_button)
    base_curvature_x = bpy.props.FloatProperty(default =.2, description = 'Curvature of base x direction', update = update_elastic_button)      
    stalk_diameter = bpy.props.FloatProperty(default =2, description = 'diameter of stalk', update = update_elastic_button)
    stalk_height = bpy.props.FloatProperty(default =2, description = 'height of stalk', update = update_elastic_button)
    button_minor = bpy.props.FloatProperty(default =3, description = 'Diameter of button', update = update_elastic_button)
    button_major = bpy.props.FloatProperty(default =5, description = 'Diameter of button tip', update = update_elastic_button)
    button_height = bpy.props.FloatProperty(default =1.5, description = 'Thickness of button', update = update_elastic_button)                      
    base_torque = bpy.props.IntProperty(default =0, min = -45, max = 45, description = 'Torque of base', update = update_elastic_button)                              

    #mode =   bpy.props.EnumProperty(name = 'New or Modify', items = (('RIGHT', 'RIGHT','RIGHT'),('LEFT','LEFT','LEFT')), defualt = 'RIGHT')                            
    @classmethod
    def poll(cls, context):
        if not context.object: return False
        if 'Button' in context.object.name:
            return True
        
        return False
    
    def invoke(self, context, event):
        
        ob = context.object
        
        self.base_diameter = ob['base_diameter']
        self.base_height = ob['base_heigt']
        self.stalk_diameter = ob['stalk_diameter']
        self.stalk_height = ob['stalk_height']
        self.button_major = ob['button_major']
        self.button_minor = ob['button_minor']
        self.button_height = ob['button_height']
        
        self.base_curvature_x = ob['base_curvature_x']
        self.base_curvature_y = ob['base_curvature_y']
        self.base_torque = ob['base_torque']
        
        self.hold_update = False
        
        return context.window_manager.invoke_props_dialog(self)
        
    def execute(self, context):
        
        update_elastic_button(self, context)
        
        self.hold_update = True
        
        return {'FINISHED'}    
        


class DialogOperator(bpy.types.Operator):
    bl_idname = "object.dialog_operator"
    bl_label = "Simple Dialog Operator"

    my_float = bpy.props.FloatProperty(name="Some Floating Point")
    my_bool = bpy.props.BoolProperty(name="Toggle Option")
    my_string = bpy.props.StringProperty(name="String Value")

    def execute(self, context):
        message = "Popup Values: %f, %d, '%s'" % \
            (self.my_float, self.my_bool, self.my_string)
        self.report({'INFO'}, message)
        return {'FINISHED'}

    def check(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "my_bool")
        if self.my_bool:
            layout.label("It's TRUE")
            layout.prop(self, "my_string")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    
    
        
def register():
    bpy.utils.register_class(D3DUAL_OT_elastic_button)
    bpy.utils.register_class(D3DUAL_OT_update_elastic_button)
    bpy.utils.register_class(D3DUAL_OT_fuse_elastic_buttons)
    bpy.utils.register_class(D3DUAL_OT_finalize_all_notches)
     
def unregister():

    bpy.utils.unregister_class(D3DUAL_OT_elastic_button)
    bpy.utils.unregister_class(D3DUAL_OT_update_elastic_button)
    bpy.utils.unregister_class(D3DUAL_OT_fuse_elastic_buttons)
    bpy.utils.unregister_class(D3DUAL_OT_finalize_all_notches)
    
if __name__ == "__main__":
    register()

# ---- Perplexity API Suggested Migrations ----
In **Blender 4.4**, property definitions must be placed inside a class derived from `bpy.types.PropertyGroup` (or similar), and you must use type annotations rather than direct assignment. The old style of assigning properties directly to variables at the module level is deprecated.

Here is the **corrected code block** for Blender 4.4+:

```python
import bpy
from bpy.props import FloatProperty, IntProperty
from bpy.types import PropertyGroup

class MyProperties(PropertyGroup):
    base_diameter: FloatProperty(default=4, description='diameter of bonding pad')
    base_height: FloatProperty(default=1.5, description='thickness of bonding pad')
    stalk_diameter: FloatProperty(default=2, description='diameter of stalk')
    stalk_height: FloatProperty(default=2, description='height of stalk')
    button_minor: FloatProperty(default=3, description='Diameter of button')
    button_major: FloatProperty(default=5, description='Diameter of button tip')
    button_height: FloatProperty(default=1.5, description='Thickness of button')
    base_curvature_y: FloatProperty(default=0.2, description='Curvature of base y direction')
    base_curvature_x: FloatProperty(default=0.2, description='Curvature of base x direction')
    base_torque: IntProperty(default=0, min=-45, max=45, description='Torque of base')
```

**Key changes:**
- Properties are now defined as class attributes with type annotations (`:`), not as assignments (`=`) at the module level.
- All property definitions must be inside a class derived from `PropertyGroup`.
- Register the property group and assign it to a context (e.g., `bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyProperties)`) as needed in your registration code[3].

This code is compatible with Blender 4.4 and follows current API conventions.
To migrate your Blender 2.79 property definitions to Blender 4.4, you must use the new annotation-based syntax for property declarations inside classes. The old assignment style (e.g., myprop = bpy.props.BoolProperty(...)) is deprecated and will not work in Blender 2.80+.

Below is the corrected code block for Blender 4.4+ (including 4.0, 4.1, 4.2, 4.3, and 4.4):

```python
import bpy

class MyPropertyGroup(bpy.types.PropertyGroup):
    hold_update: bpy.props.BoolProperty(
        default=True,
        description='Pause auto update'
    )
    base_diameter: bpy.props.FloatProperty(
        default=4,
        description='diameter of bonding pad',
        update=update_elastic_button
    )
    base_height: bpy.props.FloatProperty(
        default=1.5,
        description='thickness of bonding pad',
        update=update_elastic_button
    )
    base_curvature_y: bpy.props.FloatProperty(
        default=0.2,
        description='Curvature of base y direction',
        update=update_elastic_button
    )
    base_curvature_x: bpy.props.FloatProperty(
        default=0.2,
        description='Curvature of base x direction',
        update=update_elastic_button
    )
    stalk_diameter: bpy.props.FloatProperty(
        default=2,
        description='diameter of stalk',
        update=update_elastic_button
    )
    stalk_height: bpy.props.FloatProperty(
        default=2,
        description='height of stalk',
        update=update_elastic_button
    )
    button_minor: bpy.props.FloatProperty(
        default=3,
        description='Diameter of button',
        update=update_elastic_button
    )
    button_major: bpy.props.FloatProperty(
        default=5,
        description='Diameter of button tip',
        update=update_elastic_button
    )
```

**Key changes:**
- Use the annotation syntax (`propname: bpy.props.PropertyType(...)`) inside a class derived from `bpy.types.PropertyGroup`.
- Register your property group and assign it to a data block (e.g., `bpy.types.Scene.my_props: PointerProperty(type=MyPropertyGroup)`).
- The `update` callback signature remains the same: it must accept `(self, context)`.

**Note:** If you need the EnumProperty, use the same annotation style:

```python
mode: bpy.props.EnumProperty(
    name='New or Modify',
    items=[('RIGHT', 'RIGHT', 'RIGHT'), ('LEFT', 'LEFT', 'LEFT')],
    default='RIGHT'
)
```

This code is fully compatible with Blender 4.4 and follows current API conventions[4].
In **Blender 4.4**, property definitions must be declared as class attributes inside a class derived from `PropertyGroup`, `Operator`, or `Panel`, not as standalone assignments. The old usage like `button_height = bpy.props.FloatProperty(...)` is deprecated. Instead, use type annotations and assign the property to a class attribute within a class, then register the class and (for custom properties) assign a `PointerProperty` to the relevant data block (e.g., `Scene`, `Object`).

Here is the **corrected code block** for Blender 4.4:

```python
import bpy

def update_elastic_button(self, context):
    # Your update logic here
    pass

class MyProperties(bpy.types.PropertyGroup):
    button_height: bpy.props.FloatProperty(
        default=1.5,
        description='Thickness of button',
        update=update_elastic_button
    )
    base_torque: bpy.props.IntProperty(
        default=0,
        min=-45,
        max=45,
        description='Torque of base',
        update=update_elastic_button
    )
    # mode: bpy.props.EnumProperty(
    #     name='New or Modify',
    #     items=[('RIGHT', 'RIGHT', 'RIGHT'), ('LEFT', 'LEFT', 'LEFT')],
    #     default='RIGHT'
    # )
    my_float: bpy.props.FloatProperty(name="Some Floating Point")
    my_bool: bpy.props.BoolProperty(name="Toggle Option")
    my_string: bpy.props.StringProperty(name="String Value")

# Register the PropertyGroup
bpy.utils.register_class(MyProperties)

# Attach to Scene (or Object, etc.)
bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyProperties)
```

**Key changes:**
- Properties are now defined as class attributes with type annotations inside a `PropertyGroup` subclass.
- Register the class with `bpy.utils.register_class`.
- Attach the property group to a data block (e.g., `Scene`) using `PointerProperty`.

This is the Blender 4.4-compliant way to define and use custom properties[3].
