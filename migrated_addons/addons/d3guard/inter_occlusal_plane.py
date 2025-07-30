'''
Created on Mar 4, 2020

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh

from mathutils import Vector, Matrix, Color
from mathutils.bvhtree import BVHTree


class D3DUAL_OT_blended_interarch_plane(bpy.types.Operator):
    """Create blended functional surface"""
    bl_idname = "d3dual.blended_functional_surface"
    bl_label = "Blended Functional Surface"
    bl_options = {'REGISTER', 'UNDO'}
                              
    @classmethod
    def poll(cls, context):
        #if not context.object: return False
        #if 'Ramp' in context.object.name:
        #    return True
        
        return True
        
    def execute(self, context):
        
        main()
        return {'FINISHED'}
  
  
  

def get_plane_object():
    if 'Inter Arch Surface' not in bpy.data.objects:
        me = bpy.data.meshes.new('Inter Arch Surface')
        new_ob = bpy.data.objects.new('Inter Arch Surface', me)
        bpy.context.scene.objects.link(new_ob)
        new_ob.show_transparent = True
        me.show_double_sided = True
        
        mat = bpy.data.materials.get("Plane Material")
        if mat is None:
        # create material
            mat = bpy.data.materials.new(name="Plane Material")
            mat.diffuse_color = Color((1, .5, .5))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
    
        new_ob.data.materials.append(mat)
        
        mod = new_ob.modifiers.new('Solidify', type = 'SOLIDIFY')
        mod.thickness = .2

    else:
        new_ob = bpy.data.objects.get('Inter Arch Surface')
        new_ob.hide = False
        new_ob.show_transparent = True
        
            
    
    return new_ob


    
def main():  

    ob0 = bpy.data.objects.get('Max Occlusal Surface')
    ob1 = bpy.data.objects.get('Mand Occlusal Surface')
    ob2 = get_plane_object()
    
    #both have same Z axis alignment so no big deal
    mx0= ob0.matrix_world
    imx0 = mx0.inverted()
    
    mx1 = ob1.matrix_world
    imx1 = mx1.inverted()
    
    
    bme0 = bmesh.new()
    bme0.from_mesh(ob0.data)
    bme0.verts.ensure_lookup_table()
    bme0.edges.ensure_lookup_table()
    bme0.faces.ensure_lookup_table()
    
    
    bme1 = bmesh.new()
    bme1.from_mesh(ob1.data)
    bme1.verts.ensure_lookup_table()
    bme1.edges.ensure_lookup_table()
    bme1.faces.ensure_lookup_table()
    
    
    
    def del_flat(bme):
        to_del = []
        for v in bme.verts:
            if abs(v.co[2]) < .001:
                to_del.append(v)
     
                
        bmesh.ops.delete(bme, geom = to_del, context = 0)       
    
    
    def del_loose(bme):
        to_del = []
        
        for v in bme.verts:
            if len(v.link_faces) == 0:
                to_del.append(v)
                
        bmesh.ops.delete(bme, geom = to_del, context = 0)     
    
    del_flat(bme0)
    del_flat(bme1)
    del_loose(bme0)
    del_loose(bme1)
    
    bme0.transform(mx0)
    bme1.transform(mx1)
         
    iters = 5
    seen = set()
    for i in range(0, iters):
        
        bvh0 = BVHTree.FromBMesh(bme0)
        bvh1 = BVHTree.FromBMesh(bme1)
        
        for v in bme0.verts:
            loc, no, ind, d= bvh1.ray_cast(v.co, Vector((0,0,1)))
            if loc:
                if v not in seen:
                    seen.add(v)
                v.co = .5*v.co + .5 *loc
            
            
            else:
                loc, no, ind, d= bvh1.ray_cast(v.co, Vector((0,0,-1)))
                if loc:
                    if v not in seen:
                        seen.add(v)
                        v.co = .5*v.co + .5 *loc
            
            
                    
        for v in bme1.verts:
            loc, no, ind, d = bvh0.ray_cast(v.co, Vector((0,0,-1)))
            if loc:
                v.co = .5*v.co + .5 *loc
    
            else:
                loc, no, ind, d= bvh0.ray_cast(v.co, Vector((0,0,1)))
                if loc:
                    if v not in seen:
                        seen.add(v)
                        v.co = .5*v.co + .5 *loc
                        
    to_del = set(bme0.verts[:])
    to_del.difference_update(seen)
    bmesh.ops.delete(bme0, geom = list(to_del), context = 1)   
    
    for i in range(20):
        bmesh.ops.smooth_vert(bme0, verts = bme0.verts[:], factor = .75, use_axis_x = False, use_axis_y = False, use_axis_z = True)
             
    #update the obect data   
    bme0.to_mesh(ob2.data)
    ob0.data.update()
        
    #bme1.to_mesh(ob1.data)
    #ob1.data.update()
        
    bme0.free()
    bme1.free()
    
    
def register():
    bpy.utils.register_class(D3DUAL_OT_blended_interarch_plane)
    
    
def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_blended_interarch_plane) 
    