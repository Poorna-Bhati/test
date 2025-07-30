'''
Created on Apr 27, 2018

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement

class D3SPLINT_OT_sleep_view_presets(bpy.types.Operator):
    """Create a ramp pair"""
    bl_idname = "d3splint.sleep_ramp_view_presets"
    bl_label = "Ramps View Presets"
    bl_options = {'REGISTER', 'UNDO'}
    
    #Caps mean Shell, lowercase means Model
    #First letter is shell visibility, second letter is ramp visibility
    
    #T/T = Top Shell/Top Ramps
    #t/T = top model/Top Ramps
    mode = bpy.props.EnumProperty(name = "mode", items = (("T/T","T/T","T/T"),
                                                          ("B/B","B/B","B/B"),
                                                          ("T/B", "T/B","T/B"),
                                                          ("B/T", "B/T","B/T"),
                                                          ("A/A", "A/A","A/A"),
                                                          ("t/T","t/T","t/T"),
                                                          ("b/B","b/B","b/B"),
                                                          ("t/B", "t/B","t/B"),
                                                          ("b/T", "b/T","b/T"),
                                                          ("a/T", "a/T","a/T"),
                                                          ("a/B", "a/B","a/B"),
                                                          ))                    
    @classmethod
    def poll(cls, context):

        return True

        
    def execute(self, context):
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]    
        
        max_model = splint.get_maxilla()
        mand_model = splint.get_mandible()
        
        if max_model in bpy.data.objects:
            top_model = bpy.data.objects.get(max_model)
        else:
            self.report({'ERROR'}, "You need to mark the Maxillary Model First")
            return {'CANCELLED'}
        
        if mand_model in bpy.data.objects:
            bottom_model = bpy.data.objects.get(mand_model)
        else:
            self.report({'ERROR'}, "You need to mark the Mandibular Model First")
            return {'CANCELLED'}
        
        if splint.max_shell in bpy.data.objects:
            top_shell = bpy.data.objects.get(splint.max_shell)
        else:
            self.report({'ERROR'}, "You need to make the Maxillary Shell First")
            return {'CANCELLED'}
         
        if splint.mand_shell in bpy.data.objects:
            bottom_shell = bpy.data.objects.get(splint.mand_shell)
        else:
            self.report({'ERROR'}, "You need to make the Madnibular Shell First")
            return {'CANCELLED'}
        
        if "Right Ramp Pair" in bpy.data.objects:
            ob_p_right = bpy.data.objects.get("Right Ramp Pair")
            mod_p_right = ob_p_right.modifiers.get("Posterior Mask")
            mod_a_right = ob_p_right.modifiers.get("Anterior Mask")
        else:
            self.report({'ERROR'}, "Missing ramp element, please do ramp landmarks")
            return {'CANCELLED'}
          
        
        if "Left Ramp Pair" in bpy.data.objects:
            ob_p_left = bpy.data.objects.get("Left Ramp Pair")
            mod_p_left = ob_p_left.modifiers.get("Posterior Mask")
            mod_a_left = ob_p_left.modifiers.get("Anterior Mask")
        else:
            self.report({'ERROR'}, "Missing ramp element, please do ramp landmarks")
            return {'CANCELLED'}    
          
        
        for ob in bpy.data.objects:
            ob.hide = True
        
        ob_p_left.hide = False
        ob_p_right.hide = False
                        
        if self.mode == "T/T":
            top_shell.hide = False
            #bottom_shell.hide = True
            
            mod_p_left.show_viewport = True  
            mod_p_right.show_viewport = True
            mod_a_left.show_viewport = False
            mod_a_right.show_viewport = False
            
        elif self.mode == "T/B":
            top_shell.hide = False
            mod_p_left.show_viewport = False  
            mod_p_right.show_viewport = False
            mod_a_left.show_viewport = True
            mod_a_right.show_viewport = True
            
        elif self.mode == "B/B":
            top_shell.hide = True
            bottom_shell.hide = False
            mod_p_left.show_viewport = False  
            mod_p_right.show_viewport = False
            mod_a_left.show_viewport = True
            mod_a_right.show_viewport = True
            
        elif self.mode == "B/T":
            bottom_shell.hide = False
            mod_p_left.show_viewport = True  
            mod_p_right.show_viewport = True
            mod_a_left.show_viewport = False
            mod_a_right.show_viewport = False
            
        elif self.mode == "A/A":
            top_shell.hide = False
            ob_p_left.hide = False
            ob_p_right.hide = False
            bottom_shell.hide = False
            mod_p_left.show_viewport = False  
            mod_p_right.show_viewport = False
            mod_a_left.show_viewport = False
            mod_a_right.show_viewport = False
        
        
        
        if self.mode == "t/T":
            top_model.hide = False
            #bottom_shell.hide = True
            
            mod_p_left.show_viewport = True  
            mod_p_right.show_viewport = True
            mod_a_left.show_viewport = False
            mod_a_right.show_viewport = False
            
        elif self.mode == "t/B":
            top_model.hide = False
            mod_p_left.show_viewport = False  
            mod_p_right.show_viewport = False
            mod_a_left.show_viewport = True
            mod_a_right.show_viewport = True
            
        elif self.mode == "b/B":
            top_model.hide = True
            bottom_model.hide = False
            mod_p_left.show_viewport = False  
            mod_p_right.show_viewport = False
            mod_a_left.show_viewport = True
            mod_a_right.show_viewport = True
            
        elif self.mode == "b/T":
            bottom_model.hide = False
            mod_p_left.show_viewport = True  
            mod_p_right.show_viewport = True
            mod_a_left.show_viewport = False
            mod_a_right.show_viewport = False
            
        elif self.mode == "a/T":
            bottom_model.hide = False
            top_model.hide = False
            mod_p_left.show_viewport = True  
            mod_p_right.show_viewport = True
            mod_a_left.show_viewport = False
            mod_a_right.show_viewport = False 
            
        elif self.mode == "a/B":
            top_model.hide = False
            bottom_model.hide = False
            mod_p_left.show_viewport = False  
            mod_p_right.show_viewport = False
            mod_a_left.show_viewport = True
            mod_a_right.show_viewport = True    
                     
        return {'FINISHED'}
    


class D3DUAL_attachment_view_presets(bpy.types.Operator):
    """Show Hide Models Shells and Attachments"""
    bl_idname = "d3dual.attach_view_presets"
    bl_label = "Ramps View Presets"
    bl_options = {'REGISTER', 'UNDO'}
    
    #Caps mean Shell, lowercase means Model
    #First letter is shell visibility, second letter is ramp visibility
    
    #T/T = Top Shell/Top Ramps
    #t/T = top model/Top Ramps
    mode = bpy.props.EnumProperty(name = "mode", items = (("T/T","T/T","T/T"),
                                                          ("B/B","B/B","B/B"),
                                                          ("T/B", "T/B","T/B"),
                                                          ("B/T", "B/T","B/T"),
                                                          ("A/A", "A/A","A/A"),
                                                          ("t/T","t/T","t/T"),
                                                          ("b/B","b/B","b/B"),
                                                          ("t/B", "t/B","t/B"),
                                                          ("b/T", "b/T","b/T"),
                                                          ("a/T", "a/T","a/T"),
                                                          ("a/B", "a/B","a/B"),
                                                          ))                    
    @classmethod
    def poll(cls, context):

        return True

        
    def execute(self, context):
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]    
        
        max_model = splint.get_maxilla()
        mand_model = splint.get_mandible()
        
        if max_model in bpy.data.objects:
            top_model = bpy.data.objects.get(max_model)
        else:
            self.report({'ERROR'}, "You need to mark the Maxillary Model First")
            return {'CANCELLED'}
        
        if mand_model in bpy.data.objects:
            bottom_model = bpy.data.objects.get(mand_model)
        else:
            self.report({'ERROR'}, "You need to mark the Mandibular Model First")
            return {'CANCELLED'}
        
        if splint.max_shell in bpy.data.objects:
            top_shell = bpy.data.objects.get(splint.max_shell)
        else:
            self.report({'ERROR'}, "You need to make the Maxillary Shell First")
            return {'CANCELLED'}
         
        if splint.mand_shell in bpy.data.objects:
            bottom_shell = bpy.data.objects.get(splint.mand_shell)
        else:
            self.report({'ERROR'}, "You need to make the Madnibular Shell First")
            return {'CANCELLED'}
        
        
        attachments = []
        hide_dict = {}
        for ob in bpy.data.objects:
            if "d3attach" in ob.name or "d3comp" in ob.name:
                attachments.append(ob)
                hide_dict[ob] = ob.hide
                

        for ob in bpy.data.objects:
            ob.hide = True
        
        for ob in attachments:
            ob.hide = hide_dict[ob]
                        
        if self.mode == "T/T":
            top_shell.hide = False
            #bottom_shell.hide = True
            
            
            
        elif self.mode == "T/B":
            top_shell.hide = False

            
        elif self.mode == "B/B":
            top_shell.hide = True
            bottom_shell.hide = False

            
        elif self.mode == "B/T":
            bottom_shell.hide = False

            
        elif self.mode == "A/A":
            top_shell.hide = False
            bottom_shell.hide = False

        
        if self.mode == "t/T":
            top_model.hide = False
            #bottom_shell.hide = True
            
            
        elif self.mode == "t/B":
            top_model.hide = False

            
        elif self.mode == "b/B":
            top_model.hide = True
            bottom_model.hide = False

            
        elif self.mode == "b/T":
            bottom_model.hide = False

            
        elif self.mode == "a/T":
            bottom_model.hide = False
            top_model.hide = False

            
        elif self.mode == "a/B":
            top_model.hide = False
            bottom_model.hide = False
  
                     
        return {'FINISHED'}
    
        
def register():
    bpy.utils.register_class(D3DUAL_attachment_view_presets)
    
     
def unregister():
    bpy.utils.unregister_class(D3DUAL_attachment_view_presets)
    

# ---- Perplexity API Suggested Migrations ----
Replace your deprecated Blender 2.79 EnumProperty line with the following Blender 4.4 compatible code:

```python
mode: bpy.props.EnumProperty(
    name="mode",
    items=[
        ("T/T", "T/T", "T/T")
    ]
)
```

Key changes:
- Use **type annotations** (the colon syntax) instead of assignment for class properties[4].
- Use a **list** for the `items` argument (tuples are still accepted, but lists are now preferred for clarity and future compatibility)[4].
- The rest of the tuple structure for each item remains the same: `(identifier, name, description)`.

If this property is inside a class (e.g., an Operator or PropertyGroup), ensure it is defined as a class variable, not inside `__init__` or as an instance variable.
