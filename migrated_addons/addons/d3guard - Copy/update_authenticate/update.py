'''
Created on Mar 6, 2021
@author: Patrick
'''
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import os
from pathlib import Path
import tempfile
import time
import requests
import json
from threading import Thread
import tempfile
import shutil

import addon_utils

from common_utilities import get_settings


temp_dir = tempfile.gettempdir()
#dl_storage = os.path.join()

def get_addon_by_name(addon_name):
    addon = None
    
    for mod in addon_utils.modules():
        if mod.bl_info.get('name', None) == addon_name:
            return mod
    return addon


def threaded_download(signed_url, file_name, temp_path):
    def thread():
        data = requests.get(signed_url).content #text?
        with open(os.path.join(temp_path, file_name), 'wb') as f:
            f.write(data)
        return os.path.join(temp_path, file_name)
    my_thread = Thread(target=thread)
    my_thread.start()
    
    return my_thread
    

def download_nonthreaded(signed_url, file_name, temp_path):
    data = requests.get(signed_url).content
    with open(os.path.join(temp_path, file_name), 'wb') as f:
        f.write(data)
    return os.path.join(temp_path, file_name)
    
#I think this is right but I'm getting "jwt_auth_no_auth_header" response
def check_token(token):
    
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
    
   
def get_addon_local_version():   #TODO, better way to get this addon!!!
    
    print('Getting local adonn version')
    addon = get_addon_by_name("D3T Dual Arch")
    if addon == None:
        return 'v999.999.999'
    
    raw_version = addon.bl_info.get("version")
    
    str_version = 'v{}.{}.{}'.format(raw_version[0], raw_version[1],raw_version[2])
    
    return str_version
        
  
  
def force_get_signed_url(token):  
    API_ENDPOINT = "https://updates.d3tool.io/get_newer_version"
        
    #addon = get_addon_by_name("D3T Splint Module")
    #if addon == None:
    #    self.report({'ERROR'}, 'Could not find addon to update')
    #    return {'CANCELLED'}
    
    #raw_version = addon.bl_info.get("version")
    
    #str_version = 'v{}.{}.{}'.format(raw_version[0], raw_version[1],raw_version[2])
    
    #print(str_version)
    data = {}
    data['jwt_token'] = token
    data['product_name'] = "D3DualArch"
    data['current_version'] = 'v0.0.0'  #this forces a version

    payload = json.dumps(data)
    r = requests.post(url = API_ENDPOINT, data = payload) 

    auth_response = json.loads(r.text)

    code  = auth_response["code"]
    print(code)
    if code != 6:
        if code == 4:
            print("User does not own product")
            return None
    
    needed = auth_response["data"]["update_needed"]
    print('is an update needed?')
    print(needed)
    
    signed_url = auth_response["data"]["package_url"]
    
    return signed_url
        
        
    
class D3TOOL_services_update_addon(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "d3tool.service_update_addon"
    bl_label = "D3tool Service Update Addon"

    username = bpy.props.StringProperty(default = '')
    password = bpy.props.StringProperty(default = '', subtype = 'PASSWORD')

    #package_filename = bpy.props.StringProperty(default='')
    #package_download_dir = bpy.props.StringProperty(default='')


    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context,event):
        settings = get_settings() ## TODO:  Patrick implement the get_settings() we are using in d3denture?
        self.username = settings.d3_user_email
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        self.package_filename = "code_package.zip"
        self.package_download_dir = tempfile.mkdtemp()  ## shutil.rmtree(package_download_dir)

        API_ENDPOINT = "https://updates.d3tool.io/authenticate"
        
        data = {}
        data['username'] = self.username
        data['password'] = self.password
    
        payload = json.dumps(data)
        
        headers = {}
    
        
        r = requests.post(url = API_ENDPOINT, headers = headers, data = payload) 
        
        print(r)
        auth_response = json.loads(r.text)
        print(auth_response)
        if auth_response["success"] != True:
            
            self.report({'ERROR'}, "The credentials were incorrec")
            #get some other info from the auth response
            return {'CANCELLED'}
        
        token = auth_response["data"]["token"]  
        #TODO, save the token in a cookie or sumptin
        #Now lets validate the token  
        API_ENDPOINT = "https://updates.d3tool.io/get_newer_version"
        
        addon = get_addon_by_name("D3T Dual Arch")
        if addon == None:
            self.report({'ERROR'}, 'Could not find addon to update')
            return {'CANCELLED'}
        
        raw_version = addon.bl_info.get("version")
        
        str_version = 'v{}.{}.{}'.format(raw_version[0], raw_version[1],raw_version[2])
        
        print(str_version)
        data = {}
        
        data['jwt_token'] = token
        data['product_name'] = "D3DualArch"
        data['current_version'] = str_version  #TODO get_version()
    
        payload = json.dumps(data)
        
        r = requests.post(url = API_ENDPOINT, data = payload) 

        
        print(r)
        auth_response = json.loads(r.text)
        print(auth_response)
        
        code  = auth_response["code"]
        print(code)
        if code != 6:
            if code == 4:
                self.report({'ERROR'}, "User does not own product")
                return {'CANCELLED'}
        
        needed = auth_response["data"]["update_needed"]
        print('is an update needed?')
        print(needed)
        
        signed_url = auth_response["data"]["package_url"]

        #context.package_filename = self.package_filename
        #context.package_download_dir = self.package_download_dir

        self.download_thread = threaded_download(signed_url,
                                                self.package_filename,
                                                self.package_download_dir)
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window)
        wm.modal_handler_add(self)
        
        self.timeout = 100
        self.start_time = time.time()
        
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            shutil.rmtree(self.package_download_dir)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            print('DOWNLOADING')
            if time.time() - self.start_time > self.timeout:
                print('Error, timed out, buy faster internet')
                return {'FINISHED'}
            
            if not self.download_thread.is_alive():
                print('FINISHED DOWNLOADING')
                self.download_thread.join()
                #self.uninstall_current_addon(context)
                #package_path = os.path.join(self.package_download_dir, self.package_filename)
                #self.install_updated_addon(context, package_path=package_path)
                # shutil.rmtree(self.package_download_dir)
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def uninstall_current_addon(self, context):
        bpy.ops.wm.addon_disable(module='d3guard')
        print("ADDON DISABLED!")
        #bpy.ops.wm.addon_remove(module='d3guard')
        #print("ADDON UNINSTALLED!")

    def install_updated_addon(self, context, package_path):
        bpy.ops.wm.addon_install(filepath=package_path, overwrite=True)
        print("NEW ADDON INSTALLED!")
        bpy.ops.wm.addon_enable(module='d3guard')
        print("NEW ADDON ENABLED!")


def uninstall_current_addon():
    print("DISABLING...")
    time.sleep(5.0)
    #bpy.ops.wm.addon_disable(module='d3guard')
    addon_utils.disable("d3guard")
    bpy.ops.wm.addon_refresh()

    print("ADDON DISABLED!")
    time.sleep(5.0)
    #bpy.ops.wm.addon_remove(module='d3guard')
    #bpy.ops.wm.addon_refresh()
    # print("ADDON UNINSTALLED!")

def install_updated_addon(package_path):
    print("INSTALLING...")
    time.sleep(5.0)
    package_path = "C:\\Users\\test\AppData\\Local\\Temp\\tmppvsetdxh\\code_package.zip"
    bpy.ops.wm.addon_install(filepath=package_path, overwrite=True)
    bpy.ops.wm.addon_refresh()
    print("INSTALLED...")
    time.sleep(5.0)
    print("NEW ADDON INSTALLED!")
    #bpy.ops.wm.addon_enable(module='d3guard')
    addon_utils.enable("d3guard")
    bpy.ops.wm.addon_refresh()
    print("NEW ADDON ENABLED!")

class D3TOOL_services_reinstall_addon(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "d3tool.service_reinstall_addon"
    bl_label = "D3tool Service Reinstall Addon"

    # package_filename = bpy.props.StringProperty(default='')
    # package_download_dir = bpy.props.StringProperty(default='')

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        self.package_filename = "code_package.zip"
        self.package_download_dir = tempfile.mkdtemp()  ## shutil.rmtree(package_download_dir)

        uninstall_current_addon()
        package_path = os.path.join(self.package_download_dir, self.package_filename)
        install_updated_addon(package_path=package_path)
        #shutil.rmtree(self.package_download_dir)
        return {'FINISHED'}



class D3TOOL_services_get_token(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "d3tool.services_get_token"
    bl_label = "D3tool Service Get Token"

    username = bpy.props.StringProperty(default='')
    password = bpy.props.StringProperty(default='', subtype='PASSWORD')

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        settings = get_settings()  ## TODO:  Patrick implement the get_settings() we are using in d3denture?
        
        if hasattr(settings, "d3_user_email"):
            self.username = settings.d3_user_email
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        API_ENDPOINT = "https://updates.d3tool.io/authenticate"

        data = {}
        data['username'] = self.username
        data['password'] = self.password

        payload = json.dumps(data)

        headers = {}

        r = requests.post(url=API_ENDPOINT, headers=headers, data=payload)
        auth_response = json.loads(r.text)
        if auth_response["success"] != True:
            self.report({'ERROR'}, "The credentials were incorrect")
            # get some other info from the auth response
            return {'CANCELLED'}

        self.report({'INFO'}, "Credentials Validated!")
        token = auth_response["data"]["token"]

        update_authenticate_dir = os.path.dirname(__file__)
        addon_dir = os.path.dirname(update_authenticate_dir)
        optimize_json_path = os.path.join(addon_dir, "_optimize.json")

        ##  Read/Write _optimize.json file to add token
        if not os.path.exists(optimize_json_path):
            #create a new blank dictionary with optimize info
            jdata = {}
            jdata["jrr"] = token
            f = open(optimize_json_path, "x")
            json.dump(jdata, f)
            f.close()
            
            return {'FINISHED'}
        
        #add the token into the existing file
        else:
        
            #read existing data
            with open(optimize_json_path, 'r') as f:
                jdata = json.load(f)
                jdata['jrr'] = token

            #os.remove(optimize_json_path)
            #add the new data into it
            with open(optimize_json_path, 'w') as f:
                json.dump(jdata, f, indent=4)
                print('dumping data')

        return {'FINISHED'}
def services_check_token():
    #settings = context.user_preferences.addons["d3guard"].preferences  ## TODO:  Patrick implement the get_settings() we are using in d3denture?

    API_ENDPOINT = "https://d3tool.com/wp-json/jwt-auth/v1/token/validate"

    update_authenticate_dir = os.path.dirname(__file__)
    addon_dir = os.path.dirname(update_authenticate_dir)
    optimize_json_path = os.path.join(addon_dir, "_optimize.json")
    token = ""
    
    if not os.path.exists(optimize_json_path):
        print("ERROR: no token saved, please log in!")
        return False
    
    
    ##  Read/Write _optimize.json file to add token
    with open(optimize_json_path, 'r') as f:
        data = json.load(f)

    if 'jrr' in data.keys():
        token = data['jrr']
        
    else:
        print("ERROR: no token saved, please log in!")
        return False


    if token == "":
        print("ERROR:  Blank token.  Error with getting .json data")
        return False
    headers = {
        'Authorization': 'Bearer ' + token
    }

    r = requests.post(API_ENDPOINT, headers=headers)
    if 200 <= r.status_code < 300:
        auth_response = r.json()
        the_data = auth_response['data']
        return True
    else:
        return False

def services_get_saved_token():
    
    update_authenticate_dir = os.path.dirname(__file__)
    addon_dir = os.path.dirname(update_authenticate_dir)
    optimize_json_path = os.path.join(addon_dir, "_optimize.json")
    token = ""
    
    if not os.path.exists(optimize_json_path):
        print("ERROR: no token saved, please log in!")
        return ""
    
    
    ##  Read/Write _optimize.json file to add token
    with open(optimize_json_path, 'r') as f:
        data = json.load(f)

    if 'jrr' in data.keys():
        token = data['jrr']

    if token == "":
        print("ERROR:  Blank token.  Error with getting .json data")
        return ""
    return token

def services_get_newest_ver():
    API_ENDPOINT = "https://updates.d3tool.io/get_newest_version"
    newest_ver = None
    data = {}
    data['product_name'] = "D3DualArch"

    payload = json.dumps(data)

    headers = {}

    r = requests.post(url=API_ENDPOINT, headers=headers, data=payload)
    auth_response = json.loads(r.text)
    if auth_response["success"] != True:
        print("Error:  The credentials were incorrect")
        # get some other info from the auth response
        return None

    newest_ver = auth_response["data"]["version"]
    #print("newest_ver: " + newest_ver)
    if newest_ver != None:
        return newest_ver
    return None

class D3TOOL_services_check_token(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "d3tool.services_check_token"
    bl_label = "D3tool Service Checks if Token is Valid"

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        token_valid = services_check_token(context)
        print("token_valid: " + str(token_valid))
        return {"FINISHED"}

class D3TOOL_services_get_update_ver(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "d3tool.services_get_update_ver"
    bl_label = "D3tool Service Get Version of Update"


    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        settings = get_settings()  ## TODO:  Patrick implement the get_settings() we are using in d3denture?
        newest_ver = services_get_newest_ver()
        print("newest_ver: " + newest_ver)
        print("settings" + str(settings))
        print("settings.d3_available_version: " + str(settings.d3_available_version))
        settings.d3_available_version = newest_ver
        settings.d3_available_version_checked = True
        print("settings.d3_available_version: " + str(settings.d3_available_version))
        return {"FINISHED"}

def register():
    bpy.utils.register_class(D3TOOL_services_update_addon)
    bpy.utils.register_class(D3TOOL_services_get_token)
    bpy.utils.register_class(D3TOOL_services_check_token)
    bpy.utils.register_class(D3TOOL_services_get_update_ver)
    bpy.utils.register_class(D3TOOL_services_reinstall_addon)



def unregister():
    bpy.utils.unregister_class(D3TOOL_services_reinstall_addon)
    bpy.utils.unregister_class(D3TOOL_services_get_update_ver)
    bpy.utils.unregister_class(D3TOOL_services_check_token)
    bpy.utils.unregister_class(D3TOOL_services_get_token)
    bpy.utils.unregister_class(D3TOOL_services_update_addon)



if __name__ == "__main__":
    register()

    # test call
    #bpy.ops.object.simple_operator()

# ---- Perplexity API Suggested Migrations ----
In Blender 4.4, properties like StringProperty must be defined as class attributes inside a class derived from bpy.types.PropertyGroup, Operator, or Panel, and not as standalone variables. The correct migration is:

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    username: bpy.props.StringProperty(default='')
    password: bpy.props.StringProperty(default='', subtype='PASSWORD')
    # package_filename: bpy.props.StringProperty(default='')
    # package_download_dir: bpy.props.StringProperty(default='')
```

Key changes:
- Properties are now defined as class attributes with a colon (:) and not assigned directly.
- Properties must be inside a class derived from bpy.types.PropertyGroup (or similar).
- Register the PropertyGroup and assign it to a data path (e.g., bpy.types.Scene).

Example registration (not required if you only want the property definitions):

```python
bpy.utils.register_class(MyProperties)
bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyProperties)
```

This is the Blender 4.4 compatible way to define and use custom properties[2].
