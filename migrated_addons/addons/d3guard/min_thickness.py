'''
Created on Dec 8, 2018

@author: Patrick
'''
import time

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import tracking

from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils import Vector, Matrix, Color, Quaternion

from subtrees.metaballs.vdb_tools import remesh_bme
from subtrees.bmesh_utils.bmesh_utilities_common import bmesh_join_list

import splint_cache
from bpy.props import FloatProperty, BoolProperty, IntProperty, EnumProperty

class D3SPLINT_OT_meta_splint_minimum_thickness(bpy.types.Operator):
    """Create Offset Surface from mesh"""
    bl_idname = "d3splint.splint_minimum_thickness"
    bl_label = "Minimum Thickness Model"
    bl_options = {'REGISTER', 'UNDO'}
    
    radius = FloatProperty(default = 1, min = .6, max = 4, description = 'Minimum thickness of splint', name = 'Thickness')
    resolution = FloatProperty(default = .75, description = '0.5 to 1.5 seems to be good')
    finalize = BoolProperty(default = False, description = 'Will convert meta to mesh and remove meta object')
    
    @classmethod
    def poll(cls, context):
        if "Shell Patch" in bpy.data.objects:
            return True
        else:
            return False
        
    def execute(self, context):
        
        #fit data from inputs to outputs with metaball
        #r_final = .901 * r_input - 0.0219
        
        #rinput = 1/.901 * (r_final + .0219)
        
        
        R_prime = 1/.901 * (self.radius + .0219)
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        splint.min_thick = True
        self.bme = bmesh.new()
        ob = bpy.data.objects.get('Shell Patch')
        self.bme.from_object(ob, context.scene)
        self.bme.verts.ensure_lookup_table()
        self.bme.edges.ensure_lookup_table()
        mx = ob.matrix_world
        
        meta_data = bpy.data.metaballs.new('Minimum Thickness')
        meta_obj = bpy.data.objects.new('Meta Minimum Shell', meta_data)
        meta_data.resolution = self.resolution
        meta_data.render_resolution = self.resolution
        context.scene.objects.link(meta_obj)
        
        perimeter_edges = [ed for ed in self.bme.edges if len(ed.link_faces) == 1]
        perim_verts = set()
        for ed in perimeter_edges:
            perim_verts.update([ed.verts[0], ed.verts[1]])
            
        perim_verts = list(perim_verts)
        stroke = [v.co for v in perim_verts]
        print('there are %i non man verts' % len(stroke))                                          
        kd = KDTree(len(stroke))
        for i in range(0, len(stroke)-1):
            kd.insert(stroke[i], i)
        kd.balance()
        perim_set = set(perim_verts)
        for v in self.bme.verts:
            if v in perim_set: 
                continue
            
            loc, ind, r = kd.find(v.co)
            
            if r and r < 0.2 * R_prime:
                continue
            
            elif r and r < .8 * R_prime:
                
                mb = meta_data.elements.new(type = 'BALL')
                mb.co = v.co #+ (R_prime - r) * v.normal
                mb.radius = .5 * r
                #mb = meta_data.elements.new(type = 'ELLIPSOID')
                #mb.size_z = .45 * r
                #mb.size_y = .45 * self.radius
                #mb.size_x = .45 * self.radius
                #mb.co = v.co
                
                #X = v.normal
                #Y = Vector((0,0,1)).cross(X)
                #Z = X.cross(Y)
                
                #rotation matrix from principal axes
                #T = Matrix.Identity(3)  #make the columns of matrix U, V, W
                #T[0][0], T[0][1], T[0][2]  = X[0] ,Y[0],  Z[0]
                #T[1][0], T[1][1], T[1][2]  = X[1], Y[1],  Z[1]
                #T[2][0] ,T[2][1], T[2][2]  = X[2], Y[2],  Z[2]
    
                #Rotation_Matrix = T.to_4x4()
    
                #mb.rotation = Rotation_Matrix.to_quaternion()
                
            
            else:
                mb = meta_data.elements.new(type = 'BALL')
                mb.radius = R_prime
                mb.co = v.co
            
        meta_obj.matrix_world = mx
        
        context.scene.update()
        me = meta_obj.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        
        mat = bpy.data.materials.get("Blockout Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Blockout Material")
            mat.diffuse_color = Color((0.8, .1, .1))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        if 'Minimum Thickness' not in bpy.data.objects:
            new_ob = bpy.data.objects.new('Minimum Thickness', me)
            context.scene.objects.link(new_ob)
            new_ob.matrix_world = mx
            
            cons = new_ob.constraints.new('COPY_TRANSFORMS')
            cons.target = bpy.data.objects.get(splint.model)
            
            
            
            new_ob.data.materials.append(mat)
            
            mod = new_ob.modifiers.new('Smooth', type = 'SMOOTH')
            mod.iterations = 1
            mod.factor = .5
        else:
            new_ob = bpy.data.objects.get('Minimum Thickness')
            new_ob.data = me
            new_ob.data.materials.append(mat)
            
        new_ob.show_transparent = True
        
        #cache this data into openVDB datastruture for fast union later
        bme = bmesh.new()
        bme.from_mesh(new_ob.data)
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        splint_cache.write_min_cache(bme)
        
        context.space_data.show_backface_culling = True
            
        context.scene.objects.unlink(meta_obj)
        bpy.data.objects.remove(meta_obj)
        bpy.data.metaballs.remove(meta_data)
        
        self.bme.free() 
        #tracking.trackUsage("D3Splint:MinimumThickness",self.radius)   
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        #splint.splint_shell = True
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    
    def draw(self,context):
        
        layout = self.layout
        
        #row = layout.row()
        #row.label(text = "%i metaballs will be added" % self.n_verts)
        
        #if self.n_verts > 10000:
        #    row = layout.row()
        #    row.label(text = "WARNING, THIS SEEMS LIKE A LOT")
        #    row = layout.row()
        #    row.label(text = "Consider CANCEL/decimating more or possible long processing time")
        
        row = layout.row()
        row.prop(self, "radius")
        
        
class D3SPLINT_OT_project_minimum_thickness(bpy.types.Operator):
    """Create Offset Surface from mesh"""
    bl_idname = "d3splint.splint_correct_minimum_thickness"
    bl_label = "Correct to Minimum Thickness"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        if "Splint Shell" not in bpy.data.objects:
            return False
        
        if 'Minimum Thickness' not in bpy.data.objects:
            return False
        return True
        
    def execute(self, context):
        
        #fit data from inputs to outputs with metaball
        #r_final = .901 * r_input - 0.0219
        
        #rinput = 1/.901 * (r_final + .0219)
        
        
        Splint = bpy.data.objects.get('Splint Shell')
        MinThick = bpy.data.objects.get('Minimum Thickness')
        
        if not Splint:
            return {'CANCELLED'}
        if not MinThick:
            return {'CANCELLED'}
        
        
        bvh = BVHTree.FromObject(MinThick, context.scene)
        
        bme = bmesh.new()
        
        if len(Splint.modifiers):
            me = Splint.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
            Splint.modifiers.clear()
            old_me = Splint.data
            Splint.data = me
            bpy.data.meshes.remove(old_me)
            bme.from_mesh(me)
        else:
            bme.from_mesh(Splint.data)
            
            
        for v in bme.verts:
            loc, no, ind, d = bvh.ray_cast(v.co - .0001 * v.normal, v.normal)
            if loc and d < 1.0:
                v.co = loc + .0001 * v.normal
                
        bme.to_mesh(Splint.data)
        bme.free()
        Splint.data.update()
        return {'FINISHED'}
    
    


def register():
    bpy.utils.register_class(D3SPLINT_OT_meta_splint_minimum_thickness)
    bpy.utils.register_class(D3SPLINT_OT_project_minimum_thickness)

    
    
def unregister():
    bpy.utils.unregister_class(D3SPLINT_OT_meta_splint_minimum_thickness)
    bpy.utils.unregister_class(D3SPLINT_OT_project_minimum_thickness)