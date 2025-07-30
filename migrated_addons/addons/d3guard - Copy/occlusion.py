'''
Created on Nov 22, 2016

@author: Patrick

#find all canvases
https://blender.stackexchange.com/questions/102471/trying-to-bake-all-dynamic-paint-image-sequences-with-python

https://blender.stackexchange.com/questions/99426/create-a-gradient-dependant-of-distance-to-an-object/99465#99465

'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
from vertex_color_utils import add_volcolor_material_to_obj


class OPENDENTAL_OT_check_clearance(bpy.types.Operator):
    '''
    select 2 objects, and adds a proximity modifier and
    vertex paint to demonstrate the clearance between them
    '''
    bl_idname = 'opendental.check_clearance'
    bl_label = "Check Clearance"
    bl_options = {'REGISTER','UNDO'}
    
    min_d = bpy.props.FloatProperty(name="Touching", description="", default=0, min=0, max=1, step=5, precision=2, options={'ANIMATABLE'})
    max_d = bpy.props.FloatProperty(name="Max D", description="", default=.5, min=.1, max=2, step=5, precision=2, options={'ANIMATABLE'})
    
    @classmethod
    def poll(cls, context):
        
        cond1 = context.object != None
        cond2 = len(context.selected_objects) == 2
        cond3 = all([ob.type == 'MESH' for ob in context.selected_objects])
        cond4 = context.mode == 'OBJECT'
        
        return cond1 & cond2 & cond3 & cond4
        
    def execute(self, context):
        
        ob0 = context.object
        ob1 = [ob for ob in context.selected_objects if ob != ob0][0]
        
        grp0 = "clearance " + ob1.name
        grp1 = "clearance " + ob0.name
        
        #check if group exists
        group0 = ob0.vertex_groups.get(grp0)
        group1 = ob1.vertex_groups.get(grp1)
        
        inds0 = [i for i in range(0, len(ob0.data.vertices))]
        inds1 = [i for i in range(0, len(ob1.data.vertices))]
                                  
        if not group0:
            group0 = ob0.vertex_groups.new(grp0)
            group0.add(inds0, 1, 'REPLACE')
        else:
            group0.add(inds0, 1, 'REPLACE')
            
        if not group1:
            group1 = ob1.vertex_groups.new(grp1)
            group1.add(inds1, 1, 'REPLACE')
        else:
            group1.add(inds1, 1, 'REPLACE')
        
        mod0 = ob0.modifiers.get('VertexWeightProximity')
        if not mod0:
            mod0 = ob0.modifiers.new(type ='VERTEX_WEIGHT_PROXIMITY', name = 'VertexWeightProximity')
        
        mod1 = ob1.modifiers.get('VertexWeightProximity')
        if not mod1:
            mod1 = ob1.modifiers.new(type = 'VERTEX_WEIGHT_PROXIMITY', name = 'VertexWeightProximity')
            
        mod0.vertex_group = group0.name
        mod0.min_dist = .3
        mod0.max_dist = 0
        mod0.proximity_mode = 'GEOMETRY'
        mod0.proximity_geometry = {'FACE'}
        mod1.vertex_group = group1.name
        mod1.min_dist = .3
        mod1.max_dist = 0
        mod1.proximity_mode = 'GEOMETRY'
        mod1.proximity_geometry = {'FACE'}
        #Do this last, it's the slow part
        mod0.target = ob1
        mod1.target = ob0
        
          
        return {'FINISHED'}



class D3SPLINT_OT_dynamic_paint_occlusion(bpy.types.Operator):
    '''
    Show occclusal marks on model using dynamic paint, may cause slower responsiveness
    '''
    bl_idname = 'd3splint.dynamic_paint_occlusion'
    bl_label = "Dynamic Occlusion"
    bl_options = {'REGISTER','UNDO'}
    
    min_d = bpy.props.FloatProperty(name="Occlusion Mark Distance", description="", default=0.2, min=0.001, max=1.0, step=5, precision=2, options={'ANIMATABLE'})
    
    
    @classmethod
    def poll(cls, context):
        
        cond1 = "Splint Shell" in bpy.data.objects
        
        return cond1
        
    def execute(self, context):
        
        #TODO, make this a normal check for the simple workflow step operator
        if not len(context.scene.odc_splints):
            self.report({'ERROR'},'You need to plan a splint')
            return {'CANCELLED'}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
           
        Shell = bpy.data.objects.get('Splint Shell')
        if Shell == None:
            self.report({'ERROR'},"Need a splint shell first")
            return {'CANCELLED'}
        
        opp = splint.opposing
        Opposing = bpy.data.objects.get(opp)
        if opp == None:
            self.report({'ERROR'},"Need to indicate opposing model")
            return {'CANCELLED'}  
        
        
        if len(Opposing.data.vertices) > 100000:
            if 'Decimate' not in Opposing.modifiers:
                L = len(Opposing.data.vertices)
                self.report({'WARNING'},"Recommend trimming or decimating the opposing model")
    
        for ob in bpy.data.objects:
            ob.select = False
        context.scene.objects.active = Shell
        Shell.hide = False
        Shell.select = True
        if 'Dynamic Paint' not in Shell.modifiers:
            bpy.ops.object.modifier_remove(modifier = 'Dynamic Paint')
            
        bpy.ops.object.modifier_add(type = 'DYNAMIC_PAINT')
        bpy.ops.dpaint.type_toggle(type ='CANVAS')
        
        for ob in bpy.data.objects:
            ob.select = False
        context.scene.objects.active = Opposing
        Opposing.hide = False
        Opposing.select = True
        Opposing.show_transparent = True                
        if 'Dynamic Paint'  in Opposing.modifiers:
            #mod = Opposing.modifiers.new('Dynamic Paint', type = 'DYNAMIC_PAINT')
            bpy.ops.object.modifier_remove(modifier = 'Dynamic Paint')
        bpy.ops.object.modifier_add(type = 'DYNAMIC_PAINT')        
        bpy.ops.dpaint.type_toggle(type ='BRUSH')
            
            
        mod = Opposing.modifiers.get('Dynamic Paint')
        mod.brush_settings.paint_source = 'VOLUME_DISTANCE'
        mod.brush_settings.paint_distance = self.min_d
        return {'FINISHED'}

class D3SPLINT_OT_stop_dynamic_paint_occlusion(bpy.types.Operator):
    '''
    Turn off live occlusion for faster performance
    '''
    bl_idname = 'd3splint.stop_dynamic_paint_occlusion'
    bl_label = "Dynamic Occlusion Stop"
    bl_options = {'REGISTER','UNDO'}
    
    @classmethod
    def poll(cls, context):
        
        cond1 = "Splint Shell" in bpy.data.objects
        
        return cond1
        
    def execute(self, context):
        
        #TODO, make this a normal check for the simple workflow step operator
        if not len(context.scene.odc_splints):
            self.report({'ERROR'},'You need to plan a splint')
            return {'CANCELLED'}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
           
        Shell = bpy.data.objects.get('Splint Shell')
        if Shell == None:
            self.report({'ERROR'},"Need a splint shell first")
            return {'CANCELLED'}
        
        opp = splint.opposing
        Opposing = bpy.data.objects.get(opp)
        if opp == None:
            self.report({'ERROR'},"Need to indicate opposing model")
            return {'CANCELLED'}  
        
        for ob in bpy.data.objects:
            ob.select = False
        context.scene.objects.active = Shell
        Shell.hide = False
        Shell.select = True
        if 'Dynamic Paint' not in Shell.modifiers:
            bpy.ops.object.modifier_remove(modifier = 'Dynamic Paint')
              
        for ob in bpy.data.objects:
            ob.select = False
        context.scene.objects.active = Opposing
        Opposing.hide = False
        Opposing.select = True
        Opposing.show_transparent = False                
        if 'Dynamic Paint'  in Opposing.modifiers:
            #mod = Opposing.modifiers.new('Dynamic Paint', type = 'DYNAMIC_PAINT')
            bpy.ops.object.modifier_remove(modifier = 'Dynamic Paint')
        
        return {'FINISHED'}




class D3SPLINT_OT_paint_all_movements(bpy.types.Operator):
    '''
    Show occclusal marks on model using dynamic paint, may cause slower responsiveness
    '''
    bl_idname = 'd3splint.bake_dynamic_paint'
    bl_label = "Paint Dynamic Occlusion"
    bl_options = {'REGISTER','UNDO'}
    
    min_d = bpy.props.FloatProperty(name="Occlusion Mark Distance", description="", default=0.2, min=0.001, max=1.0, step=5, precision=2, options={'ANIMATABLE'})
    
    
    @classmethod
    def poll(cls, context):
        
        cond1 = "Splint Shell" in bpy.data.objects
        
        return cond1
        
    def invoke(self, context, event):
        
        #TODO, make this a normal check for the simple workflow step operator
        if not len(context.scene.odc_splints):
            self.report({'ERROR'},'You need to plan a splint')
            return {'CANCELLED'}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
           
        Shell = bpy.data.objects.get('Splint Shell')
        if Shell == None:
            self.report({'ERROR'},"Need a splint shell first")
            return {'CANCELLED'}
        
        self.shell = Shell
        bpy.ops.d3splint.articulator_mode_set(mode  = '3WAY_ENVELOPE')
        bpy.ops.d3splint.dynamic_paint_occlusion()
        
        color, mat = add_volcolor_material_to_obj(Shell, "dp_paintmap")
        bpy.ops.screen.animation_play()
        wm = context.window_manager
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    
    def modal(self, context, event):
        

        if context.scene.frame_current == context.scene.frame_end - 1:
            bpy.ops.object.modifier_apply()
            #show textured solid
            bpy.ops.screen.animation_cancel()
            
            print('WE DID IT')
            mod = self.shell.modifiers.get('Dynamic Paint')
            bpy.ops.object.modifier_apply(modifier = 'Dynamic Paint')
            
            context.scene.frame_set(0)
            context.scene.frame_set(0)
            
            return {'FINISHED'}

        
        elif event.type in {'ESC'}:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            return {'CANCELLED'}

        #n = context.scene.frame_current + 1
        #context.scene.frame_set(n)
        
        return {'RUNNING_MODAL'}

   
def register():
    bpy.utils.register_class(OPENDENTAL_OT_check_clearance)
    bpy.utils.register_class(D3SPLINT_OT_dynamic_paint_occlusion)
    bpy.utils.register_class(D3SPLINT_OT_stop_dynamic_paint_occlusion)
    bpy.utils.register_class(D3SPLINT_OT_paint_all_movements)
    
def unregister():
    bpy.utils.unregister_class(OPENDENTAL_OT_check_clearance)
    bpy.utils.unregister_class(D3SPLINT_OT_dynamic_paint_occlusion)
    bpy.utils.unregister_class(D3SPLINT_OT_stop_dynamic_paint_occlusion)
    bpy.utils.unregister_class(D3SPLINT_OT_paint_all_movements)
    
if __name__ == "__main__":
    register()

# ---- Perplexity API Suggested Migrations ----
```python
min_d: bpy.props.FloatProperty(
    name="Touching",
    description="",
    default=0.0,
    min=0.0,
    max=1.0,
    step=5,
    precision=2,
    options={'ANIMATABLE'}
)
max_d: bpy.props.FloatProperty(
    name="Max D",
    description="",
    default=0.5,
    min=0.1,
    max=2.0,
    step=5,
    precision=2,
    options={'ANIMATABLE'}
)
min_d: bpy.props.FloatProperty(
    name="Occlusion Mark Distance",
    description="",
    default=0.2,
    min=0.001,
    max=1.0,
    step=5,
    precision=2,
    options={'ANIMATABLE'}
)
```

**Key changes for Blender 4.4:**
- Use **type annotations** (e.g., `min_d: bpy.props.FloatProperty(...)`) instead of assignment (`min_d = ...`) when defining properties in classes[4].
- Ensure all numeric literals use decimal points for clarity and compatibility.
- The `step`, `precision`, and `options` arguments remain valid in Blender 4.4[4].
- Remove duplicate property definitions with the same name in the same class.

If these are meant to be class properties (e.g., in a `PropertyGroup`), place them inside the class body using the annotation syntax as shown.
