'''
Created on Dec 15, 2018

@author: Patrick


http://mathworld.wolfram.com/TrianglePointPicking.html
http://mathworld.wolfram.com/DiskPointPicking.html
http://mathworld.wolfram.com/SimplexSimplexPicking.html
http://mathworld.wolfram.com/SpherePointPicking.html


'''
import time

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import tracking

from bpy.props import FloatProperty, IntProperty, BoolProperty, EnumProperty


#Modifier Remeshing

#Dyntopo Remseshing

#Particle Remeshing

def get_dyntopo_mask(context, ob):
    is_dynamic = ob.use_dynamic_topology_sculpting
    is_active = context.object == ob
    is_sculpt = ob.mode == 'SCULPT'
    
    
def long_edges(bme, min_len):
    return [ed for ed in bme.edges if ed.calc_length() > min_len]


#selective_remesh_long_edges
class D3MODEL_OT_remesh_coarse_areas(bpy.types.Operator):
    """Selectively add detail to low resolution areas"""
    bl_idname = "d3model.selective_remesh"
    bl_label = "Add Mesh Detail"
    bl_options = {'REGISTER', 'UNDO'}
    
    max_edge_length = FloatProperty(name = 'Max Edge Length', description = 'Edges longer than this will be re-meshed', default = 0.7, min = .1 , max = 1.5)
    target_edge_length = FloatProperty(name = 'Target Edge Length',description = 'Long edges will be remeshed to this, usually smaller than Max Edge Length', default = 0.4, min = .1 , max = 1.5)
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    
    def execute(self, context):
        
        
        #this is the final mode we will put back
        final_mode = context.mode
        
        #putting the object back into object mode, ensures the mask
        #layer data is up to date
        if final_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
        
        is_dyntopo = context.object.use_dynamic_topology_sculpting
            
        bme = bmesh.new()
        bme.from_mesh(context.object.data)
        
        bme.verts.ensure_lookup_table()
        mask = bme.verts.layers.paint_mask.verify()
    
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        
        long_vs = set()
        for ed in bme.edges:
            if ed.calc_length() > self.max_edge_length:
                long_vs.update([ed.verts[0], ed.verts[1]])
            
            
        for v in bme.verts:
            if v in long_vs:
                v[mask] = 0.0
            else:
                v[mask] = 1.0

        bme.to_mesh(context.object.data) #push the mask bak
        bme.free()
        context.object.data.update()
        
        bpy.ops.object.mode_set(mode = 'SCULPT')
    
        if not context.object.use_dynamic_topology_sculpting:
            bpy.ops.sculpt.dynamic_topology_toggle()
        context.scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
        context.scene.tool_settings.sculpt.constant_detail_resolution =  min(1/(1.5*self.target_edge_length), 6)
        bpy.ops.sculpt.detail_flood_fill()
         
        if final_mode != context.mode:
            bpy.ops.object.mode_set(mode = final_mode)
        
        return {'FINISHED'}

    
    def invoke(self, context, event):

        return context.window_manager.invoke_props_dialog(self)

class D3SPLINT_OT_remesh_smooth_inflate(bpy.types.Operator):
    """Remesh the model, smooth it, and volume correct"""
    bl_idname = "d3splint.remesh_smooth_inflate"
    bl_label = "Remesh Smooth and Inflate"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    orders =  [('REMESH_SMOOTH_INFLATE','Remesh Smooth Inflate', 'Better for surface preservation'),
               ('SMOOTH_REMESH_INFLATE','Remesh Smooth Inflate', 'Better for taking sharp features down')]
               #('REMESH_INFLATE_SMOOTH','Remesh Smooth Inflate', 'Perform operations in this order')]
               
    order_of_opertions = EnumProperty(name = 'Operation Order', items = orders, default = 'SMOOTH_REMESH_INFLATE')
    
    remesh_detail = FloatProperty(name = 'Remesh Detail', default = 1.5, min = 1, max = 3, description = 'Use small numbers to make big changes. Higher number is more detail')
    smooth_iterations = IntProperty(name = 'Smooth Iterations', default = 15, min = 1, max = 50)
    volume_correction = FloatProperty(name = 'Volume Correction', default = 0.05, min = .01 , max = .2)
    
    
    use_remesh = BoolProperty(name = 'Use Remesh', default = True, description = 'Good if booleans have failed')
    
    
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    
    def remesh(self, context, shell):
        
        bpy.ops.object.mode_set(mode = 'SCULPT')
        if not shell.use_dynamic_topology_sculpting:
            bpy.ops.sculpt.dynamic_topology_toggle()
        context.scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
        context.scene.tool_settings.sculpt.constant_detail_resolution = self.remesh_detail
        bpy.ops.sculpt.detail_flood_fill()
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
    
    def smooth(self, context, shell):
        mod = shell.modifiers.new('Smooth', type = 'SMOOTH')
        mod.iterations = self.smooth_iterations
        
        
    def inflate(self, context, shell):
        mod = shell.modifiers.new('Inflate', type = 'DISPLACE')
        mod.mid_level = 1 - self.volume_correction
    
    def apply(self, context, shell):
        failed_mods = []
        for mod in shell.modifiers:
            try:
                bpy.ops.object.modifier_apply(modifier = mod.name)
            except:
                failed_mods.append(mod)
        
        return failed_mods
    
    def execute(self, context):
        
        
        start = time.time()
        
        shell = bpy.data.objects.get('Splint Shell')
        if not shell:
            self.report({'ERROR'}, "Need to calculate splint shell first")
            return {'CANCELLED'}
        
        
        
        #it's on
        context.scene.objects.active = shell
        shell.select = True
        shell.hide = False
        
        old_mode = context.mode
        if old_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
        
        
        failed_mods = []
        
        for mod in shell.modifiers:
            try:
                bpy.ops.object.modifier_apply(mod = mod.name)
            except:
                failed_mods += [mod]
        
        
        if self.order_of_opertions == 'REMESH_SMOOTH_INFLATE':
            if self.use_remesh:
                self.remesh(context, shell)
            
            self.smooth(context, shell)
            self.inflate(context, shell)
            
        elif self.order_of_opertions == 'SMOOTH_REMESH_INFLATE':
            
            self.smooth(context, shell)
            
            self.apply(context, shell)
            
            self.remesh(context, shell)
            
            self.inflate(context, shell)
            
        self.apply(context, shell)
        
        
        if old_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = old_mode)
            
        finish = time.time()
        print('Took %f seconds to remesh/smooth/inflate' % (finish-start))
        tracking.trackUsage("D3Splint:RemeshSmoothInflate",None)
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        splint.ops_string += 'RemeshSmoothInflate:'
        return {'FINISHED'}

    
    def invoke(self, context, event):

        return context.window_manager.invoke_props_dialog(self)
    
    
def register():
    bpy.utils.register_class(D3SPLINT_OT_remesh_smooth_inflate)
    bpy.utils.register_class(D3MODEL_OT_remesh_coarse_areas)
    
def unregister():
    bpy.utils.unregister_class(D3SPLINT_OT_remesh_smooth_inflate)
    bpy.utils.unregister_class(D3MODEL_OT_remesh_coarse_areas)