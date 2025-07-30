'''
Created on Apr 27, 2018

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement

class D3SPLINT_OT_view_presets(bpy.types.Operator):
    """Create a ramp pair"""
    bl_idname = "d3splint.view_presets"
    bl_label = "Ramps View Presets"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    mode = bpy.props.EnumProperty(name = "mode", items = (("U/O","U/O","U/O"),
                                                          ("L/O","L/O","L/O"),
                                                          ("Q", "Q","Q")))
                                                          #("B/T", "B/T","B/T"),
                                                          #("A/A", "A/A","A/A"),
                                                          #  ))                    
    @classmethod
    def poll(cls, context):

        return True

        
    def execute(self, context):
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]    
        
        max_model = splint.get_maxilla()
        mand_model = splint.get_mandible()
    
        
                        
        if self.mode == "U/O":
            MaxModel = bpy.data.objects.get(max_model)
            if not MaxModel:
                return {'CANCELLED'}
            
            for ob in bpy.data.objects:
                ob.hide = True
            
            MaxModel.hide = False
            bpy.ops.view3d.viewnumpad(type = 'BOTTOM')  
        elif self.mode == "L/O":
            ManModel = bpy.data.objects.get(mand_model)
            if not ManModel:
                return {'CANCELLED'}
            
            for ob in bpy.data.objects:
                ob.hide = True  
            ManModel.hide = False
            bpy.ops.view3d.viewnumpad(type = 'TOP')    
        elif self.mode == "Q":
            bpy.ops.screen.region_quadview()
        return {'FINISHED'}
    


 
def register():
    bpy.utils.register_class(D3SPLINT_OT_view_presets)
    
     
def unregister():
    bpy.utils.unregister_class(D3SPLINT_OT_view_presets)
    

# ---- Perplexity API Suggested Migrations ----
The correct way to define an EnumProperty in Blender 4.4+ is to use the annotation syntax and assign the property to a class variable, not a module-level variable. Here is the migrated code block:

```python
import bpy

class MyPropertyGroup(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="mode",
        items=[
            ("U/O", "U/O", "U/O"),
        ]
    )
```

Key changes:
- Use the annotation syntax (mode: ...).
- Define the property inside a class derived from bpy.types.PropertyGroup or bpy.types.Operator, not at the module level.
- Use a list for items, not a tuple (both are accepted, but list is more common in recent Blender versions)[3].
