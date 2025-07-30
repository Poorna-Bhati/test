'''
Created on Jun 3, 2020

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector

class D3DUAL_OT_paint_selected_shell(bpy.types.Operator):
    '''Use sculpt mask to mark parts of model'''
    bl_idname = "d3dual.enter_sculpt_paint_mask"
    bl_label = "Paint Model"
    bl_options = {'REGISTER','UNDO'}

    
    
    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.object.type != 'MESH':
            return False
        if 'Shell' not in context.object.name:
            return False
        
        return True
            
    def execute(self, context):
             
            
        bpy.ops.object.mode_set(mode = 'SCULPT')
        #if not model.use_dynamic_topology_sculpting:
        #    bpy.ops.sculpt.dynamic_topology_toggle()
        
        scene = context.scene
        paint_settings = scene.tool_settings.unified_paint_settings
        paint_settings.use_locked_size = True
        paint_settings.unprojected_radius = 2
        brush = bpy.data.brushes['Mask']
        brush.strength = 1
        brush.use_frontface = True
        brush.stroke_method = 'SPACE'
        scene.tool_settings.sculpt.brush = brush
        scene.tool_settings.sculpt.use_symmetry_x = False
        scene.tool_settings.sculpt.use_symmetry_y = False
        scene.tool_settings.sculpt.use_symmetry_z = False
        bpy.ops.brush.curve_preset(shape = 'MAX')
        
        return {'FINISHED'}
    
class D3DUAL_OT_mask_to_convex_hull_raw(bpy.types.Operator):
    '''Turn painted area into convex hull and merve with original mesh'''
    bl_idname = "d3dual.sculpt_mask_qhull_raw"
    bl_label = "Sculpt Mask to Convex Region"
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.object: return False
        c1 = context.object.type == 'MESH'
        c2 = context.mode == 'SCULPT'
        return c1 & c2
    
    def execute(self, context):
        
        start_ob = context.object
        
        bme = bmesh.new()
        bme.from_mesh(context.object.data)
        mask = bme.verts.layers.paint_mask.verify()
        bme.verts.ensure_lookup_table()
        convex = []
        for v in bme.verts:
            if v[mask] > 0.5:
                convex.append(v)

        out_geom = bmesh.ops.convex_hull(bme, input = convex, use_existing_faces = True)

        for v in convex:
            v[mask] = 0.0
            
        bme.to_mesh(start_ob.data)
        bme.free()
        start_ob.data.update()

        return {'FINISHED'}
    
    
class D3DUAL_OT_mask_to_flat_rim(bpy.types.Operator):
    '''Extrude painted area into a flat regio '''
    bl_idname = "d3dual.sculpt_mask_flat_pad"
    bl_label = "Sculpt Mask to Flat Plane"
    bl_options = {'REGISTER','UNDO'}

    height = bpy.props.FloatProperty(name = 'Height', default = 5.0, min = 1.0, max = 6.0)
    
    @classmethod
    def poll(cls, context):
        if not context.object: return False
        c1 = context.object.type == 'MESH'
        c2 = context.mode == 'SCULPT'
        return c1 & c2
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        start_ob = context.object
        
        bme = bmesh.new()
        bme.from_mesh(context.object.data)
        mask = bme.verts.layers.paint_mask.verify()
        bme.verts.ensure_lookup_table()
        painted = []
        for v in bme.verts:
            if v[mask] > 0.5:
                painted.append(v)

        #todo smooth the border, but maybe not?
        if 'MAND' in start_ob.name:
            
            v_base = max(painted, key = lambda x: x.co[2])
            up = 1
            plane_point = v_base.co
            
        else:
            v_base = min(painted, key = lambda x: x.co[2])
            up = -1
            plane_point = v_base.co
            
        faces = set()
        for v in painted:
            faces.update(v.link_faces)

        to_remove = []
        for f in faces:
            if not all([v in painted for v in f.verts]):
                to_remove.append(f)
        faces.difference_update(to_remove)
        
        new_geom = bmesh.ops.extrude_face_region(bme, geom = list(faces))  
        new_verts = [v for v in new_geom['geom'] if isinstance(v, bmesh.types.BMVert)]
        for v in new_verts:
            v.co[2] = plane_point[2] + up * self.height
            v[mask] = 0.0
                
        for v in painted :
            v[mask] = 0.0
            
        bme.to_mesh(start_ob.data)
        bme.free()
        start_ob.data.update()

        return {'FINISHED'}
    
def register():
    bpy.utils.register_class(D3DUAL_OT_paint_selected_shell)
    bpy.utils.register_class(D3DUAL_OT_mask_to_convex_hull_raw)
    bpy.utils.register_class(D3DUAL_OT_mask_to_flat_rim)
    
    
def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_paint_selected_shell)
    bpy.utils.unregister_class(D3DUAL_OT_mask_to_convex_hull_raw)
    bpy.utils.unregister_class(D3DUAL_OT_mask_to_flat_rim)
    

# ---- Perplexity API Suggested Migrations ----
height: bpy.props.FloatProperty(
    name="Height",
    default=5.0,
    min=1.0,
    max=6.0,
    options={'ANIMATABLE'}
)
