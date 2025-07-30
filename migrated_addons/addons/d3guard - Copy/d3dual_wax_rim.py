'''
Created on Jun 10, 2020

@author: Patrick
'''
import math

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix, Quaternion

from common_utilities import get_settings
from common_utilities import space_evenly_on_path

from segmentation.common.maths import intersect_path_plane #TODO MOVE TO GEOMETRY UTILS
from mesh_cut import edge_loops_from_bmedges  #TODO update to new subtrees code


class D3SPLINT_OT_splint_add_rim(bpy.types.Operator):
    """Create Meta Wax Rim previously defined maxillary and mandibular curves"""
    bl_idname = "d3splint.splint_rim_from_dual_curves"
    bl_label = "Create Splint Rim "
    bl_options = {'REGISTER', 'UNDO'}
    
    
    meta_type = bpy.props.EnumProperty(name = 'Meta Type', items = [('CUBE','CUBE','CUBE'), ('ELLIPSOID', 'ELLIPSOID','ELLIPSOID')], default = 'CUBE', description = 'What shape gets extruded along the rim, ellipsoid will be a much rounder rim')
    
    width_offset = bpy.props.FloatProperty(name = 'Extra Wdith', default = 0.01, min = -3, max = 3, description = 'Can be used to add extra or remove extra Bucco/Lingnual width from the rim')
    
    thickness_offset = bpy.props.FloatProperty(name = 'Extra Thickness', default = 0.01, min = -3, max = 3, description = 'Will add extra (or reduce for negative values) thicknesss to the rim')
    anterior_projection = bpy.props.FloatProperty(name = 'Extra Anterior Width', default = 0.01, min = -2, max = 3, description = 'Will add more BuccoLingual width to the anterior rim/ramp')
    anterior_shift = bpy.props.FloatProperty(name = 'Anterior Shift', default = 0.0, min = -5.0, max = 50, description = 'Will Shift the anterior segment of the rim')
    
    flare = bpy.props.IntProperty(default = 0, min = -60, max = 60, description = 'Angle of anterior ramp from world, can be negative (maxillary prosthesis) or positive (mandibular), try -30')
    anterior_segment = bpy.props.FloatProperty(name = 'AP Spread', default = 0.3, min = .15, max = .85, description = 'Percentage of AP spread which is considered the anterior rim')
    ap_segment = bpy.props.EnumProperty(name = 'Rim Area', items = [('ANTERIOR_ONLY','Anterior Ramp','Only builds rim anterior to AP spread'),
                                                          ('POSTERIOR_ONLY', 'Posterior Pad','ONly builds rim posterior to AP spread'),
                                                          ('FULL_RIM', 'Full Rim', 'Buillds a posterior pad and anteiror ramp')], default = 'FULL_RIM')
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        if bpy.data.filepath == '':
            return False
        return True
    
    def execute(self, context):
        settings = get_settings()
        MaxCurve = bpy.data.objects.get('Occlusal Curve Max')
        if MaxCurve == None:
            self.report({'ERROR'}, "Need to mark maxillary buccal cusps")
            return {'CANCELLED'}
        
        MandCurve = bpy.data.objects.get('Occlusal Curve Mand')
        if MandCurve == None:
            self.report({'ERROR'}, "Need to mark mandibular lingual cusps")
            return {'CANCELLED'}
        
        #shell = bpy.data.objects.get('Splint Shell')
        #if not shell:
        #    self.report({'ERROR'}, "Need to calculate splint shell first")
        #    return {'CANCELLED'}
        
        splint = context.scene.odc_splints[0]
        
        
        #tracking.trackUsage("D3DUAL:MetaWaxRim",None)
        
        
        max_crv_data = MaxCurve.data
        mx_max = MaxCurve.matrix_world
        imx_max = mx_max.inverted()
        
        
        mand_crv_data = MandCurve.data
        mx_mand = MandCurve.matrix_world
        imx_mand = mx_mand.inverted()
        
        
        print('got curve object')
        
        meta_data = bpy.data.metaballs.new('Splint Wax Rim')
        meta_obj = bpy.data.objects.new('Meta Surface', meta_data)
        meta_data.resolution = .4
        meta_data.render_resolution = .4
        context.scene.objects.link(meta_obj)
        
        #get world path of the maxillary curve
        me_max = MaxCurve.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        bme_max = bmesh.new()
        bme_max.from_mesh(me_max)
        bme_max.verts.ensure_lookup_table()
        bme_max.edges.ensure_lookup_table()
        loops = edge_loops_from_bmedges(bme_max, [ed.index for ed in bme_max.edges])
        
        #only allow one maxillary loop
        if len(loops) > 1:
            return {'CANCELLED'}
        
        
        vs0 = [mx_max * bme_max.verts[i].co for i in loops[0]]
        vs_even_max, eds0 = space_evenly_on_path(vs0, [(0,1),(1,2)], 100)
        
        #get world path of the mandibular curve
        me_mand = MandCurve.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        bme_mand = bmesh.new()
        bme_mand.from_mesh(me_mand)
        bme_mand.verts.ensure_lookup_table()
        bme_mand.edges.ensure_lookup_table()
        loops = edge_loops_from_bmedges(bme_mand, [ed.index for ed in bme_mand.edges])
        
        if len(loops) == 1:
            #regular method
            
            vs0 = [mx_mand * bme_mand.verts[i].co for i in loops[0]]
            vs_even_mand, eds0 = space_evenly_on_path(vs0, [(0,1),(1,2)], 100)
        
        
            #check the curve direction.  Four our purposes, the curve should go from left to right
            #so that X points around the curve, Z points up, and Y points out (toward the cheek)
            #left in the world is positive Y direction.
            if vs_even_max[0][1] < vs_even_max[-1][1]:
                vs_even_max.reverse()
            
            #check for tip to tail
            if (vs_even_mand[0] - vs_even_max[0]).length > (vs_even_mand[0] - vs_even_max[-1]).length:
                print('reversing the mandibular curve')
                vs_even_mand.reverse()
            
            Z = Vector((0,0,1))
            
            
            max_x = min(vs_even_max, key = lambda x: x[1])  #most anteiror point is most negative Y value
            min_x = max(vs_even_max, key = lambda x: x[1])  #most posterior point is most positive Y value
            A_ap = max_x[1]
            P_ap = min_x[1]
            ap_spread = abs(max_x[0] - min_x[0])
            
        
            
            
            y_shift = 1
                
            for i in range(1,len(vs_even_max)-1):
                
                #use maxilary curve for estimattino
                
                v0_0 = vs_even_max[i]
                v0_p1 = vs_even_max[i+1]
                v0_m1 = vs_even_max[i-1]
    
                tan_vect = v0_p1 - v0_m1
                v0_mand = intersect_path_plane(vs_even_mand, v0_0, tan_vect)
                
                if not v0_mand: continue
                
                center = .5 * v0_0 + 0.5 * v0_mand
                
                size_z = max(1, abs(v0_0[2] - v0_mand[2] - 1))
                size_y = ((v0_0[0] - v0_mand[0])**2 + (v0_0[1] - v0_mand[1])**2)**.5
                size_y = max(3, size_y)
                
                X = v0_p1 - v0_m1
                X.normalize()
                
                Y = Z.cross(X)
                X_c = Y.cross(Z) #X corrected
                
                T = Matrix.Identity(3)
                T.col[0] = X_c
                T.col[1] = Y
                T.col[2] = Z
                quat = T.to_quaternion()
                
                if v0_0[1] < A_ap + self.anterior_segment * ap_spread:  #anterior points
                    if self.ap_segment == 'POSTERIOR_ONLY': continue
                    mb = meta_data.elements.new(type = self.meta_type)
                    mb.size_x = 1.5
                    Qrot = Quaternion(X_c, math.pi/180 * self.flare)
                    Zprime = Qrot * Z
                
                    Y_c = Zprime.cross(X_c)
                
                
                    T = Matrix.Identity(3)
                    T.col[0] = X_c
                    T.col[1] = Y_c
                    T.col[2] = Zprime
                    quat = T.to_quaternion()
                    
                    if v0_0[1] < A_ap + self.anterior_segment * ap_spread - .25 * self.anterior_segment * ap_spread:  #more than 25% more anterior and the AP cutoff
                        mb.size_y =  max(.5 * (size_y - 1.5 + self.width_offset) + self.anterior_projection, 1)
                        mb.size_z = max(.35 * size_z + .5 * self.thickness_offset, .75)
                        mb.co = center + (.5 * self.width_offset + self.anterior_projection + self.anterior_shift) * y_shift * Y_c
                        mb.rotation = quat
                    else:
                        #blend =  (v0_0[1] - (A_ap - self.anterior_segment * ap_spread))/(.25 * self.anterior_segment * ap_spread)
                        blend =  (v0_0[1] - (A_ap + self.anterior_segment * ap_spread))/(.25 * self.anterior_segment * ap_spread)
                        
                        mb.size_y =  max(.5 * (size_y - 1.5 + self.width_offset) + blend * self.anterior_projection, 1)
                        mb.size_z = max(.35 * size_z + .5 * self.thickness_offset, .75)
                        mb.co = center + (.5 * self.width_offset + blend * (self.anterior_projection + self.anterior_shift)) * y_shift * Y_c
                        mb.rotation = quat
                else:          
                    if self.ap_segment == 'ANTERIOR_ONLY': continue
                    mb = meta_data.elements.new(type = self.meta_type)
                    mb.size_x = 1.5
                    mb.size_y = max(.5 * (size_y - 1.5) + self.width_offset, 1)
                    mb.size_z = max(.35 * size_z + .5 * self.thickness_offset, .75)
                    mb.co = center
                    
                    mb.rotation = quat
                mb.stiffness = 2
            
        if len(loops) > 1:
            
            #segmental method
            
            paths = []
            for vloop in loops:
                vec_list = [mx_mand * bme_mand.verts[i].co for i in vloop]
                vs_even, eds = space_evenly_on_path(vec_list, [(0,1),(1,2)], 100)
                paths.append(vs_even)
        
        
            if len(paths) == 3:
                AP = min(paths, key = lambda x: sum([v[1] for v in x])/len(x))  #anterior path with most negative y coordinate (LPS coordinate system)
                
                paths.remove(AP)
                
            else:
                AP = []
            
            Z = Vector((0,0,1))
            y_shift = 1
            
            
            for vpath in paths:
                
                
                for i in range(1,len(vpath)-1):
                    v0_0 = vpath[i]
                    v0_p1 = vpath[i+1]
                    v0_m1 = vpath[i-1]
            
                    tan_vect = v0_p1 - v0_m1
                    v0_max = intersect_path_plane(vs_even_max, v0_0, tan_vect)
                    
                    if not v0_max: continue
                    
                    center = .5 * v0_0 + 0.5 * v0_max
                
                    size_z = max(1, abs(v0_0[2] - v0_max[2] - 1))
                    size_y = ((v0_0[0] - v0_max[0])**2 + (v0_0[1] - v0_max[1])**2)**.5
                    size_y = max(3, size_y)
                    
                    X = v0_p1 - v0_m1
                    X.normalize()
                    
                    Y = Z.cross(X)
                    X_c = Y.cross(Z) #X corrected
                    
                    T = Matrix.Identity(3)
                    T.col[0] = X_c
                    T.col[1] = Y
                    T.col[2] = Z
                    quat = T.to_quaternion()
                    
                    mb = meta_data.elements.new(type = self.meta_type)
                    mb.size_x = 1.5
                    mb.size_y = max(.5 * (size_y - 1.5) + self.width_offset, 1)
                    mb.size_z = max(.35 * size_z + .5 * self.thickness_offset, .75)
                    mb.co = center
                    
                    mb.rotation = quat
                    mb.stiffness = 2
             
            if len(AP) != 0:   
                for i in range(1,len(AP)-1):
                    v0_0 = AP[i]
                    v0_p1 = AP[i+1]
                    v0_m1 = AP[i-1]
            
                    tan_vect = v0_p1 - v0_m1
                    v0_max = intersect_path_plane(vs_even_max, v0_0, tan_vect)
                    
                    if not v0_max: continue
                    
                    center = .5 * v0_0 + 0.5 * v0_max
                
                    size_z = max(1, abs(v0_0[2] - v0_max[2] - 1))
                    size_y = ((v0_0[0] - v0_max[0])**2 + (v0_0[1] - v0_max[1])**2)**.5
                    size_y = max(3, size_y)
                    
                    X = v0_p1 - v0_m1
                    X.normalize()
                    
                    Y = Z.cross(X)
                    X_c = Y.cross(Z) #X corrected
                
                    Qrot = Quaternion(X_c, math.pi/180 * self.flare)
                    Zprime = Qrot * Z
                    Y_c = Zprime.cross(X_c)
                    
                    mb = meta_data.elements.new(type = self.meta_type)
                    mb.size_x = 1.5
                    mb.size_y =  max(.5 * (size_y - 1.5 + self.width_offset) + self.anterior_projection, 1)
                    mb.size_z = max(.35 * size_z + .5 * self.thickness_offset, .75)
                    mb.co = center + (.5 * self.width_offset + self.anterior_projection + self.anterior_shift) * y_shift * Y_c
                    mb.rotation = quat
                    mb.stiffness = 2   
                
                  
    
        context.scene.update()
        me = meta_obj.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        
        
        mat = bpy.data.materials.get("Rim Material")
        if mat is None:
        # create material
            mat = bpy.data.materials.new(name="Rim Material")
            mat.diffuse_color = get_settings().def_rim_color
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
        
        if 'Wax Rim' not in bpy.data.objects:
            new_ob = bpy.data.objects.new('Wax Rim', me)
            context.scene.objects.link(new_ob)
            new_ob.data.materials.append(mat)
            
        else:
            new_ob = bpy.data.objects.get('Wax Rim')
            new_ob.modifiers.clear()
            new_ob.data = me
            new_ob.hide = False
            if "Splint Material" not in new_ob.data.materials:
                new_ob.data.materials.append(mat)

        context.scene.objects.unlink(meta_obj)
        bpy.data.objects.remove(meta_obj)
        bpy.data.metaballs.remove(meta_data)
        
        bme_max.free()
        bme_mand.free()
        #todo remove/delete to_mesh mesh
  
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        splint.ops_string += 'MakeRim:'
        splint.wax_rim_calc = True
        return {'FINISHED'}

    
    def invoke(self, context, event):

        return context.window_manager.invoke_props_dialog(self)
    
    
    
def register():
    bpy.utils.register_class(D3SPLINT_OT_splint_add_rim)

    
    
    #bpy.utils.register_module(__name__)
    
def unregister():
    #bpy.utils.unregister_class(D3SPLINT_OT_splint_model)
    bpy.utils.unregister_class(D3SPLINT_OT_splint_add_rim)
    
    

# ---- Perplexity API Suggested Migrations ----
To migrate your property definitions from Blender 2.79 to Blender 4.4, update the deprecated `bpy.props.FloatProperty`, `IntProperty`, and `EnumProperty` usage as follows:

- In Blender 2.8+ (including 4.4), **all property definitions must be inside a class derived from `bpy.types.PropertyGroup` or similar, not as standalone variables**.
- The syntax for property definitions remains mostly the same, but you must define them as class attributes.

Here is the corrected code block for Blender 4.4:

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    meta_type: bpy.props.EnumProperty(
        name='Meta Type',
        items=[
            ('CUBE', 'CUBE', 'CUBE'),
            ('ELLIPSOID', 'ELLIPSOID', 'ELLIPSOID')
        ],
        default='CUBE',
        description='What shape gets extruded along the rim, ellipsoid will be a much rounder rim'
    )

    width_offset: bpy.props.FloatProperty(
        name='Extra Width',
        default=0.01,
        min=-3,
        max=3,
        description='Can be used to add extra or remove extra Bucco/Lingual width from the rim'
    )

    thickness_offset: bpy.props.FloatProperty(
        name='Extra Thickness',
        default=0.01,
        min=-3,
        max=3,
        description='Will add extra (or reduce for negative values) thickness to the rim'
    )

    anterior_projection: bpy.props.FloatProperty(
        name='Extra Anterior Width',
        default=0.01,
        min=-2,
        max=3,
        description='Will add more BuccoLingual width to the anterior rim/ramp'
    )

    anterior_shift: bpy.props.FloatProperty(
        name='Anterior Shift',
        default=0.0,
        min=-5.0,
        max=50,
        description='Will Shift the anterior segment of the rim'
    )

    flare: bpy.props.IntProperty(
        default=0,
        min=-60,
        max=60,
        description='Angle of anterior ramp from world, can be negative (maxillary prosthesis) or positive (mandibular), try -30'
    )

    anterior_segment: bpy.props.FloatProperty(
        name='AP Spread',
        default=0.3,
        min=0.15,
        max=0.85,
        description='Percentage of AP spread which is considered the anterior rim'
    )

    ap_segment: bpy.props.EnumProperty(
        name='Rim Area',
        items=[
            ('ANTERIOR_ONLY', 'Anterior Ramp', 'Only builds rim anterior to AP spread')
        ]
    )
```

**Key changes:**
- Properties are now defined as class attributes with a colon (`:`) and not as assignments (`=`) at the module level.
- The class must inherit from `bpy.types.PropertyGroup`.
- Register your property group and assign it to a data block (e.g., `bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyProperties)`).

This structure is required for Blender 2.8+ and is fully compatible with Blender 4.4[4].
