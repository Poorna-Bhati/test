'''
Created on Jul 25, 2020

@author: Patrick
'''
import math
import numpy as np

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
from mathutils import Matrix, Vector

from common_utilities import showErrorMessage


class D3DUAL_OT_store_simulated_position(bpy.types.Operator):
    """Do something"""
    bl_idname = "d3dual.store_articulated_position"
    bl_label = "Store Simulated Position"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    name = bpy.props.StringProperty(name = 'Position Label', default = 'Stored Position')
    replace = bpy.props.BoolProperty(name = 'Replace', description = 'Overwrite if using the same name')
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n] #TODO better knowledge for multiple splints
            
        if not splint.landmarks_set:
            self.report({'ERROR'}, 'You must set landmarks to have saved mounting')
            return {'CANCELLED'}
        
        
        mandible = splint.get_mandible()
        maxilla = splint.get_maxilla()
        
        Mandible = bpy.data.objects.get(mandible)
        Maxilla = bpy.data.objects.get(maxilla)
        Bow = bpy.data.objects.get('Bottom Element')
        Articulator = bpy.data.objects.get('Articulator')
        
        if not Maxilla:
            self.report({'ERROR'},"It is not clear which model is the maxilla.  Have you set maxilla and mandibular models")
            return {'CANCELLED'}
        
        if not Mandible:
            self.report({'ERROR'},"It is not clear which model is the mandible.  Have you set model and set opposing?")
            return {'CANCELLED'}
        
        
        initial_orientation = bpy.data.objects.get('Mandibular Orientation')
        if initial_orientation == None:
            self.report({'ERROR'},"Initial position was not saved")
            return {'CANCELLED'}
        
        #marker = context.scene.timeline_markers.get(self.name)
        #markers_list = splint.stored_positions.split(",")
        #markers_list.pop()
        #print(markers_list)
        
        
        matrix_ob = bpy.data.objects.get(self.name)
        
        if not matrix_ob:
            matrix_ob = bpy.data.objects.new(self.name, None)
            context.scene.objects.link(matrix_ob)
            matrix_ob.parent = Articulator
        #if not marker:
        #    marker = context.scene.timeline_markers.new(self.name, context.scene.frame_current)
        #    markers_list.append(self.name)
        
        else:
            if not self.replace:
                showErrorMessage('Position with same name exists, rename or choose replace to overwrite')
                return {'CANCELLED'}
            
            #else:
                #replacing and existing marker
                #context.scene.timeline_markers.remove(marker)
                #marker = context.scene.timeline_markers.new(self.name, context.scene.frame_current)
        matrix_ob['stored_position'] = True  #give it an ID prop
        matrix_ob['frame'] = context.scene.frame_current
                
                
        mx_i = initial_orientation.matrix_world   
        mx_w = Mandible.matrix_world.copy()
        
        mx_bow_i = Matrix.Identity(4)
        mx_bow = Bow.matrix_world.copy()
        
        
        print(splint.stored_positions)
        splint.stored_positions += self.name + ','
        
        trans = mx_i.to_translation() - mx_w.to_translation()
        L = trans.length
        
        print('Total translation %f' % L)
        
        
        qi = mx_i.to_quaternion()
        qf = mx_w.to_quaternion()
        
        
        r_diff = qi.rotation_difference(qf)
        
        euler = r_diff.to_euler()
        
        hinge_opening = 180 * euler[1]/math.pi
        print('Rotation difference degrees')
        print(hinge_opening)
        
        
        
        v_incisal = bpy.data.objects.get('Incisal').matrix_world.to_translation()
        R_incisal = (v_incisal[0]**2 + v_incisal[2]**2)**.5
        opening = euler[1] * R_incisal
        
        print('Opening at incisal edges')
        print(opening)
        
        matrix_ob.matrix_world = mx_bow
        
        splint.ops_string += "Stored Position {} @ {:.2f}deg Hinge Rotation and {:.2f}mm Translation:".format(self.name,hinge_opening, L)
        
        
        return {'FINISHED'}
 

def get_items(self, context):
    
    stored_positions = [ob for ob in bpy.data.objects if ob.get('stored_position')]
    
    return [(ob.name, ob.name, ob.name) for ob in stored_positions]
    
    
class D3DUAL_OT_jump_to_stored_position(bpy.types.Operator):
    """Do something"""
    bl_idname = "d3dual.jump_to_stored_position"
    bl_label = "Show Simulated Position"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    position = bpy.props.EnumProperty(name = 'Position', items = get_items)
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_props_popup(self, event)
    
    def execute(self, context):
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n] #TODO better knowledge for multiple splints
    
        if not splint.landmarks_set:
            self.report({'ERROR'}, 'You must set landmarks to have saved mounting')
            return {'CANCELLED'}
        
        
        mandible = splint.get_mandible()
        maxilla = splint.get_maxilla()
        
        Mandible = bpy.data.objects.get(mandible)
        Maxilla = bpy.data.objects.get(maxilla)
        Bow = bpy.data.objects.get('Bottom Element')
        if not Maxilla:
            self.report({'ERROR'},"It is not clear which model is the mandible.  Have you set maxilla and mandibular models")
            return {'CANCELLED'}
        
        if not Mandible:
            self.report({'ERROR'},"It is not clear which model is the maxilla.  Have you set model and set opposing?")
            return {'CANCELLED'}
        if not Bow:
            self.report({'ERROR'},"Where is the articulato?  Stored positions are stored on the articulator")
            return {'CANCELLED'}
        
        initial_orientation = bpy.data.objects.get('Mandibular Orientation')
        if initial_orientation == None:
            self.report({'ERROR'},"Initial position was not saved!  We can't jump to other positions")
            return {'CANCELLED'}
        
        mx_i = initial_orientation.matrix_world  
        matrix_ob = bpy.data.objects.get(self.position)
        
        if not matrix_ob:
            showErrorMessage('This position has somehow become missing')
            #TODO remove it from splint.stored_positions list
            return {'CANCELLED'}
  
  
      
        mx_w_bow = matrix_ob.matrix_world
        
        context.scene.frame_set(0)
        Bow.matrix_world = mx_w_bow
        
        mx_w = Mandible.matrix_world
        
        trans = mx_i.to_translation() - mx_w.to_translation()
        L = trans.length
        
        print('Total translation %f' % L)
        
        qi = mx_i.to_quaternion()
        qf = mx_w.to_quaternion()
        
        r_diff = qi.rotation_difference(qf)
        
        euler = r_diff.to_euler()
        
        hinge_opening = 180 * euler[1]/math.pi
        print('Rotation difference degrees')
        print(hinge_opening)
        

        v_incisal = bpy.data.objects.get('Incisal').matrix_world.to_translation()
        R_incisal = (v_incisal[0]**2 + v_incisal[2]**2)**.5
        opening = euler[1] * R_incisal
        
        print('Opening at incisal edges')
        print(opening)
        
        #if matrix_ob.get('frame'):
        #    context.scene.frame_set(matrix_ob['frame'])
        #else:
        #    context.scene.frame_set(0)
            
        Mandible.matrix_world = mx_w
        return {'FINISHED'}
    
    
class D3DUAL_OT_next_position(bpy.types.Operator):
    """Do something"""
    bl_idname = "d3dual.next_stored_position"
    bl_label = "Next Simulated Position"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    previous = bpy.props.BoolProperty(default = False)
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def execute(self, context):
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n] #TODO better knowledge for multiple splints
        
        models = [ob.name for ob in bpy.data.objects if ob.get('stored_position')]
        
        models = splint.stored_positions.split(',')
        models.pop()
        print('STORED POSITIONS JUMP JUMP')
        print(models)
        
        #models = [ob.name for ob in bpy.data.objects if ob.get('stored_position')]
        if len(models) == 0:
            self.report({'ERROR'}, 'No Stored Positions to Jump To')
            return {'CANCELLED'}
        

        Mandible = bpy.data.objects.get(splint.get_mandible())
        Bow = bpy.data.objects.get('Bottom Element')
        if not Mandible:
            self.report({'ERROR'},"It is not clear which model is the maxilla.  Have you set model and set opposing?")
            return {'CANCELLED'}
        if not Bow:
            self.report({'ERROR'},"It is not clear which model is the maxilla.  Have you set model and set opposing?")
            return {'CANCELLED'}
        
        
        initial_orientation = bpy.data.objects.get('Mandibular Orientation')
        if initial_orientation == None:
            self.report({'ERROR'},"Initial position was not saved!  We can't jump to other positions")
            return {'CANCELLED'}
        
        active = None
        active_pos = None
        for i, m_name in enumerate(models):
            obj = bpy.data.objects.get(m_name)
            if not obj: continue
            
            print(m_name)
            print(Bow.matrix_world)
            print(obj.matrix_world)
            
            if np.allclose(obj.matrix_world, Bow.matrix_world, atol = .00001):
                active_ind = i
                active_pos = m_name
                print('found the active position!')
                print(i)
                print(m_name)
                break
        
        if active_pos == None:
            print('did not find the active positino')
            next_ind = 0
            prev_ind = 0
        else:
            print('did  find the active position')
            next_ind = int(math.fmod(active_ind + 1, len(models)))
            prev_ind = int(math.fmod(active_ind - 1, len(models)))
        
        #print(active_ind, next_ind, prev_ind)
        mx_i = initial_orientation.matrix_world  
        
        if self.previous:
            matrix_ob = bpy.data.objects.get(models[prev_ind])

        else:
            matrix_ob = bpy.data.objects.get(models[next_ind])
        
        print(matrix_ob)
        if not matrix_ob:
            showErrorMessage('This position has somehow become missing')
            #TODO remove it from splint.stored_positions list
            return {'CANCELLED'}
        
        #if matrix_ob.get('frame'):
        #    context.scene.frame_set(matrix_ob['frame'])
        #else:
        
        context.scene.frame_set(0)
        mx_w = matrix_ob.matrix_world
        Bow.matrix_world = mx_w
        return {'FINISHED'}
    
     
def register():
    bpy.utils.register_class(D3DUAL_OT_store_simulated_position)
    bpy.utils.register_class(D3DUAL_OT_jump_to_stored_position)
    bpy.utils.register_class(D3DUAL_OT_next_position)
    
def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_store_simulated_position)
    bpy.utils.unregister_class(D3DUAL_OT_jump_to_stored_position)
    bpy.utils.unregister_class(D3DUAL_OT_next_position)
    

# ---- Perplexity API Suggested Migrations ----
In Blender 4.4, operator and property definitions must use type annotations rather than direct assignment. The old style:

```python
name = bpy.props.StringProperty(name = 'Position Label', default = 'Stored Position')
replace = bpy.props.BoolProperty(name = 'Replace', description = 'Overwrite if using the same name')
position = bpy.props.EnumProperty(name = 'Position', items = get_items)
previous = bpy.props.BoolProperty(default = False)
```

should be updated to:

```python
name: bpy.props.StringProperty(name='Position Label', default='Stored Position')
replace: bpy.props.BoolProperty(name='Replace', description='Overwrite if using the same name')
position: bpy.props.EnumProperty(name='Position', items=get_items)
previous: bpy.props.BoolProperty(default=False)
```

This change is required for all property definitions in Blender 2.80 and later, including 4.4[1].
