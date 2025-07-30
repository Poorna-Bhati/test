'''
Created on Mar 17, 2021

@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import requests
import json



#I think this is right but I'm getting "jwt_auth_no_auth_header" response
def check_d3tool_token(token):
    
    API_ENDPOINT = "https://d3tool.com//wp-json/jwt-auth/v1/token/validate"
    headers = {}
    
    headers["Authorization"] = "Bearer " + token
    
    r = requests.post(url = API_ENDPOINT, headers = headers) 
    auth_response = json.loads(r.text)
    
    print(auth_response)
    if auth_response["success"] == True:
        print('Validated the JRR Tolkien')
        return True
    else:
        print('YOU SHALL NOT PASS')
        return False
    
    
def get_json_cookie():
    
    #read in the saved stuff
    return None

def save_json_cookie():
    
    #read in the saved stuff
    return None

class D3TOOL_com_test_login(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "d3tool.com_test_login"
    bl_label = "D3tool dot com Login Opeartor"

    username = bpy.props.StringProperty(default = '')
    password = bpy.props.StringProperty(default = '', subtype = 'PASSWORD')


    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context,event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        
        API_ENDPOINT = "https://d3tool.com/wp-json/jwt-auth/v1/token"
        
        params = {}
        params['username'] = self.username
        params['password'] = self.password
    
        r = requests.post(url = API_ENDPOINT, data = params) 
        auth_response = json.loads(r.text)
        
        
        print(auth_response)
        if auth_response["success"] != True:
            
            self.report({'ERROR'}, "The credentials were incorrec")
            #get some other info from the auth response
            return {'CANCELLED'}
        
        
        token = auth_response["data"]["token"]  
        #TODO, save the token in a cookie or sumptin
        #Now lets validate the token  
        check_d3tool_token(token)
        
        
        #save the token
        
        #could be existing token or one we just requested
        
        
        
        #API_ENDPOINT = 'https://d3tool.online/api/user/auth_check'
        #headers = {}
        #headers['Auth-Token'] = auth_token
        
        #r = requests.post(url = API_ENDPOINT, headers = headers) 
        #username = r.text
        #print("The username of this token is %s" % username)
        
        #API_ENDPOINT = 'https://d3tool.online/api/user/has_active_subscription'

        #r = requests.post(url = API_ENDPOINT, headers = headers) 
        #active_sub = r.text
        #print("%s has an active sub:%s" % (username, active_sub))
       

        return {'FINISHED'}





def register():
    bpy.utils.register_class(D3TOOL_com_test_login)


def unregister():
    bpy.utils.unregister_class(D3TOOL_com_test_login)


if __name__ == "__main__":
    register()

    # test call
    #bpy.ops.object.simple_operator()

# ---- Perplexity API Suggested Migrations ----
The correct way to define properties in Blender 4.4+ is to use the annotation syntax with bpy.props. Here is the migrated code block:

```python
import bpy

class MyPropertyGroup(bpy.types.PropertyGroup):
    username: bpy.props.StringProperty(default='')
    password: bpy.props.StringProperty(default='', subtype='PASSWORD')
```

Replace your old property definitions with the above annotation-based syntax inside a class derived from bpy.types.PropertyGroup. This is required for Blender 2.80 and later, including 4.4[1].
