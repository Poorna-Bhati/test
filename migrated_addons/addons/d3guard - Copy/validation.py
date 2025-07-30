'''
Created on Mar 7, 2020

@author: Patrick
'''
import requests
import json
import os

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement

from odcutils import get_settings

from subtrees.addon_common.common.blender import show_blender_popup
def check_credits(key):
    #submit user key to the credit check link
    
    
    server = 'http://104.196.199.206'
    
    url = 'http://104.196.199.206/get_dual_arch?key={}'.format(key)
    

    
    raw_response = requests.get(url).text
    if raw_response:
        jdict = json.loads(raw_response)
        credit_balance = float(jdict['credits'])
        
    else:
        credit_balance = -1
    
    return credit_balance


def check_userprefs_credits():
    prefs = get_settings() 
    key_path = prefs.key_path
    if key_path != '' and os.path.exists(key_path):
        key_file = open(prefs.key_path)
        key_val = key_file.read()
        
    else:
        key_val = prefs.key_string
        
    cred = check_credits(key_val)
    
    if cred != -1:
        return True
    else:
        return False

    
    
    
def get_cloud_key():
    prefs = get_settings()    
    key_path = prefs.key_path
    if key_path != '' and os.path.exists(key_path):
        key_file = open(prefs.key_path)
        key_val = key_file.read()
        
    else:
        key_val = prefs.key_string
        
    return key_val


class D3DUAL_OT_check_and_save_user_key(bpy.types.Operator):
    """Submit file to get convex teeth"""
    bl_idname = "d3dual.check_and_save_user_key"
    bl_label = "Check and Save User Key"

    
    key = bpy.props.StringProperty(name = 'User Key', subtype = 'PASSWORD',  default = '')
    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        #validate scene
        #if not valid, warn users -> cancel
        #check credits
        #show popup with credit amount, ask user if they are sure
        
        prefs = get_settings()
        
        key_path = prefs.key_path
        if key_path != '' and os.path.exists(key_path):
            key_file = open(prefs.key_path)
            key_val = key_file.read()
        
        else:
            key_val = prefs.key_string
        
        self.key = key_val
          
        if key_val == '':
            self.credits_avail = -1.0
        else:  
            self.credits_avail = check_credits(key_val)
        
        
        return context.window_manager.invoke_props_dialog(self, width = 300)
    
    def draw(self, context):
        
        layout = self.layout
        
        row = layout.row()
        row.prop(self, "key")
        
    def execute(self,context):
        
        prefs = get_settings()
        if check_credits(self.key) != -1: 
            prefs.key_string = self.key
            bpy.ops.wm.save_userpref()
            self.key = ''  #don't save password!
            show_blender_popup("The key was successfully registered and saved. Restart Blender to begin", title="Key Success!", icon="FILE_TICK", wrap=80)
            
        else:
            show_blender_popup("The key was could not be validated", title="Key Failure!", icon="CANCEL", wrap=80)
            self.report({'ERROR'}, 'The key you entered is invalid!  Please try again')  
            return {'CANCELLED'}  
        return {'FINISHED'}
    
     
    
def register():
    bpy.utils.register_class(D3DUAL_OT_check_and_save_user_key)
    
def unregister():
    bpy.utils.register_class(D3DUAL_OT_check_and_save_user_key)
    

# ---- Perplexity API Suggested Migrations ----
The correct Blender 4.4+ code for defining a password-style string property is:

```python
key: bpy.props.StringProperty(
    name="User Key",
    subtype='PASSWORD',
    default=""
)
```

Key changes:
- Use the **annotation syntax** (key: ...) instead of assignment (key = ...).
- All arguments remain the same, as subtype='PASSWORD' is still valid in Blender 4.4+.

This syntax is required for all property definitions in Blender 2.8 and later.
