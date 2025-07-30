'''
Created on Apr 24, 2020

@author: Patrick

#how far is joint from tragus.  10mm forward and 2mm down
#http://1.bp.blogspot.com/-bpmyYKVl2lw/Tpw2mF91jlI/AAAAAAAAAxw/xWc0aceNfuY/s1600/Anatomical_Landmarks_for_Needle_Entry_into_the_TMJ2-525x440.jpg

'''

import math
import random

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix, Color

# Addon imports

from common_utilities import get_settings


from subtrees.points_picker.operators.points_picker import VIEW3D_OT_points_picker
from subtrees.points_picker.subtrees.addon_common.common import ui



# https://github.com/CGCookie/retopoflow
def showErrorMessage(message:str, wrap:int=80):
    if not message or wrap == 0:
        return
    lines = message.splitlines()
    nlines = []
    for line in lines:
        spc = len(line) - len(line.lstrip())
        while len(line) > wrap:
            i = line.rfind(' ', 0, wrap)
            if i == -1:
                nlines += [line[:wrap]]
                line = line[wrap:]
            else:
                nlines += [line[:i]]
                line = line[i+1:]
            if line:
                line = ' '*spc + line
        nlines += [line]
    lines = nlines

    def draw(self,context):
        for line in lines:
            self.layout.label(text=line)

    bpy.context.window_manager.popup_menu(draw, title="Error Message", icon="ERROR")
    return

class D3DUAL_OT_cookie_cutter_landmarks(VIEW3D_OT_points_picker):
    """ Click on the posterior contacts """
    bl_idname = "d3dual.mark_facial_landmarks"
    bl_label = "Identify Face Landmarks"
    bl_description = "Indicate points on the face"

    #############################################
    # overwriting functions from wax drop

    @classmethod
    def can_start(cls, context):
        """ Start only if editing a mesh """
        if not hasattr(context.scene, "odc_splints"): return False
        if len(context.scene.odc_splints) < 1: return False
        return True

    
    def start_pre(self):
        n = self.context.scene.odc_splint_index
        self.splint = self.context.scene.odc_splints[n]    
        

        Model = bpy.data.objects.get(self.splint.face_model)
        self.model = Model
        self.obs_unhide = []
        
        for ob in bpy.data.objects:
            ob.select = False
            ob.hide = True
        Model.select = True
        Model.hide = False
        bpy.context.scene.objects.active = Model
        
        
        bpy.ops.view3d.viewnumpad(type = 'FRONT')
        bpy.ops.view3d.view_selected()

        bpy.context.space_data.show_manipulator = False
        bpy.context.space_data.transform_manipulators = {'TRANSLATE','ROTATE'}
        v3d = bpy.context.space_data
        v3d.pivot_point = 'MEDIAN_POINT'
   
    def resetLabels(self):  #must override this becuase we have pre-defineid label names
        return          
    def add_point_post(self, pt_added):
        labels = ["Right TMJ", "Right Infraorbital", "Left TMJ", "Left Infraorbital", "Subnasion"]
        
        if len(self.b_pts) > 5:
            self.b_pts = self.b_pts[0:5]
            return
        
        used_labels = []
        unlabeled_points = []
        for pt in self.b_pts:
            if pt.label in labels:
                used_labels += [pt.label]
            else:
                unlabeled_points += [pt]
                
        print(used_labels)
        for label in used_labels:
            labels.remove(label)
                
        for i, pt in enumerate(unlabeled_points):
            pt.label = labels[i]
        
        if len(labels) > 1:
            self.win_obvious_instructions.visible = True
            self.win_obvious_instructions.hbf_title.set_label('Click ' + labels[1])  
        else:
            self.win_obvious_instructions.visible = False      

    def move_point_post(self, hovered):
        print('move point post')
        if len(self.b_pts) < 4: return
        self.update_plane_vis()
        
    def remove_point_post(self):
        labels = labels = ["Right TMJ", "Right Infraorbital", "Left TMJ", "Left Infraorbital", "Subnasion"]
        
        if len(self.b_pts) > 5:
            self.b_pts = self.b_pts[0:5]
            return

        for pt in self.b_pts:
            if pt.label in labels:
                labels.remove(pt.label)
        if len(labels) >= 1:
            self.win_obvious_instructions.visible = True
            self.win_obvious_instructions.hbf_title.set_label('Click ' + labels[0])  
        else:
            self.win_obvious_instructions.visible = False    
        
        
    
    def get_create_plane_vis(self):
        name = "FPV_" + self.model.name
        PlaneOb = bpy.data.objects.get(name)
        if PlaneOb == None:
            bme = bmesh.new()
            bmesh.ops.create_grid(bme, x_segments = 2, y_segments = 2, size = 200)
            
            mx0 = Matrix.Rotation(math.pi/2, 4, 'X')
            bmesh.ops.create_grid(bme, x_segments = 2, y_segments = 2, size = 200, matrix = mx0)
            
            mx1 = Matrix.Rotation(math.pi/2, 4, 'Y')
            bmesh.ops.create_grid(bme, x_segments = 2, y_segments = 2, size = 200, matrix = mx1)
            
            me = bpy.data.meshes.new(name)
            PlaneOb = bpy.data.objects.new(name, me)
            bpy.context.scene.objects.link(PlaneOb)
            
            #mx_s = Matrix.Identity(4)
            #mx_s[0][0], mx_s[1][1], mx_s[2][2] = 50,50,50
        
        
            bme.to_mesh(me)
            bme.free()
            PlaneOb.show_transparent = True
            
            mat = bpy.data.materials.get("Occ Pln Material")
            if mat is None:
                # create material
                mat = bpy.data.materials.new(name="Occ Pln Material")
                mat.diffuse_color = Color((0.1, .4, .8))
                mat.use_transparency = True
                mat.transparency_method = 'Z_TRANSPARENCY'
                mat.alpha = .4
            
            me.materials.append(mat)    
        return PlaneOb
    
    def update_plane_vis(self):
        print('UPDATE PLANE')
        if len(self.b_pts) < 4: return
        
        Model = self.model    
        mx = Model.matrix_world
        imx = mx.inverted()
        
        mx_data = self.get_transform_data()
    
    
        Plane = self.get_create_plane_vis()
        
        #if Plane.parent == None:
        #    Plane.parent = Model
        
        mx_rot = mx_data['Facial Plane Matrix'].to_4x4()
        #mx_t = Matrix.Translation(mx * mx_data['Rotation Center'].to_translation())
        mx_t = mx_data['Rotation Center']
        
        Plane.matrix_world = mx_t * mx_rot
        Plane.hide = False
            
    def get_transform_data(self):
        '''
        mx and imx are the world matrix and it's inverse of the  model
        '''
        settings = get_settings()
        mx_data = {}
        
        #["Right TMJ", "Right Ala", "Left TMJ", "Left Ala", "Subnasion"]
        
        bp_rt = [bpt for bpt in self.b_pts if bpt.label == 'Right TMJ'][0]
        bp_lt = [bpt for bpt in self.b_pts if bpt.label == 'Left TMJ'][0]
        bp_ria = [bpt for bpt in self.b_pts if bpt.label == 'Right Infraorbital'][0]
        bp_lia = [bpt for bpt in self.b_pts if bpt.label == "Left Infraorbital"][0]
        bp_sn = [bpt for bpt in self.b_pts if bpt.label == 'Subnasion'][0]
        
        v_RTMJ =  bp_rt.location 
        v_LTMJ = bp_lt.location 
        v_RIA =  bp_ria.location 
        v_LIA =  bp_lia.location 
        v_SN =  bp_sn.location #midline
        
        #calculate the center (still in model local coordinates
        center = 1/2 * (v_RTMJ + v_LTMJ)
        
        
        #
        infra_oribital_mid = 1/2 * (v_LIA + v_RIA)
        v2 = v_RTMJ - infra_oribital_mid
        v1 = v_LTMJ - infra_oribital_mid
        v1.normalize()
        v2.normalize()
        
        print(v1, v2)
        
        Z = v1.cross(v2)
        X = v_LTMJ - v_RTMJ
        X.normalize()
        Y = Z.cross(X)
        
        print(X, Y, Z)
    
        R = Matrix.Identity(3)  #make the columns of matrix U, V, W for an LPS coordinate system
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2] 
        
        R = R.to_4x4()
        iR = R.inverted()
        ### NOW WE HAVE THE OCCLUSAL PLANE DESCRIBED
        
        #we put the condyles on the articulator, but allow the face to be shifted if needed?
        center_shift = (v_SN - center).dot(X) * X
        mx_center = Matrix.Translation(center + center_shift)
        
        mx_data['Facial Plane Matrix'] = R
        mx_data['Facial Plane iMatrix'] = iR
        mx_data['Rotation Center'] = mx_center
        
        return mx_data    
    
    def next(self):
        
        if len(self.b_pts) < 4:
            showErrorMessage("You have not marked all of the landmarks")
            return
        
        self.done()
               
        
    def getLabel(self, idx):
        return "P %(idx)s" % locals()


    def end_commit(self):
        settings = get_settings()
        
        #Spcial case, lower splint, no maxillary model.  Typically landmarks are always set on maxilla if maxillary model available
        #if self.splint.jaw_type == 'MANDIBLE' and self.splint.get_maxilla() == '':
        #    Model = bpy.data.objects[self.splint.get_mandible()]
        # 
        #else:
        Model =  bpy.data.objects[self.splint.face_model]
            
        mx = Model.matrix_world
        imx = mx.inverted()
        
        mx_data = self.get_transform_data()
        
        #de-rotate the Model data so that it is aligned with occlusal plane
        #Plane normal defines Z axis
        #X axis is torward anterior
        #Y axis points from right o left (right hadn rule wit x and z)
        
        
        mx_t = mx_data["Rotation Center"]
        mx_r = mx_data["Facial Plane Matrix"]
        
        
        for pt in self.b_pts:
            print('caching')
            pt.cache_to_empties()
            
            
        if 'Facial Matrix Empty' in bpy.data.objects:
            empty = bpy.data.objects.get('Facial Plane Empty')
        else:
            empty = bpy.data.objects.new('Faical Plane Empty', None)
        empty.matrix_world = mx_t * mx_r
        bpy.context.scene.objects.link(empty)
        empty.parent = Model
        
        
        name = "MX_Orig_" + Model.name
        if name in bpy.data.objects:
            empty1 = bpy.data.objects.get(name)
        else:
            empty1 = bpy.data.objects.new(name, None)
        
        #prevent accidental selection
        empty1.hide_select = True
        self.context.scene.objects.link(empty1)
        
        empty1.parent = Model
        empty1.matrix_world = Model.matrix_world   #put this one at the object orign
             
        #iR = mx_data['Facial Plane iMatrix']
        PlaneOb = self.get_create_plane_vis()
        Model.matrix_world = PlaneOb.matrix_world.inverted() * Model.matrix_world  #apply to existing?
        PlaneOb.matrix_world = Matrix.Identity(4)
        PlaneOb.show_wire = True
        
        self.splint.facial_landmarks_set = True
        bpy.context.scene.objects.active = Model               
        Model.select = True
        Model.hide = False
        #tracking.trackUsage("D3Dual:SplintLandmarks",None)
        self.splint.ops_string += 'Set Facial Landmarks:'
        
    ####  Enhancing UI ############
    
    def ui_setup_post(self):
        #####  Hide Existing UI Elements  ###
        self.info_panel.visible = False
        self.tools_panel.visible = False
        
        
        self.info_panel = self.wm.create_window('Landmarks Help',
                                                {'pos':9,
                                                 'movable':True,
                                                 'bgcolor':(0.50, 0.50, 0.50, 0.90)})

        collapse_container = self.info_panel.add(ui.UI_Collapsible('Instructions     ', collapsed=False))
        self.inst_paragraphs = [collapse_container.add(ui.UI_Markdown('', min_size=(100,10), max_size=(250, 50))) for i in range(6)]
        
        self.new_instructions = {
            
            "Add": "Left click to place a point",
            "Grab": "Hold left-click on a point and drag to move it along the surface of the mesh",
            "Remove": "Right Click to remove a point",
            "Requirements": "Click the Right Pupil, Left Pupil, Left Commisure then Right Commisure"
        }
        
        for i,val in enumerate(['Add', 'Grab', 'Remove', "Requirements"]):
            self.inst_paragraphs[i].set_markdown(chr(65 + i) + ") " + self.new_instructions[val])

        
        
        self.win_obvious_instructions = self.wm.create_window('Click Right TMJ', {'pos':8, "vertical":False, "padding":15, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.5), 'border_color':(0.50, 0.50, 0.50, 0.9), "border_width":4.0})
        self.win_obvious_instructions.hbf_title.fontsize = 20
        
        win_next_back = self.wm.create_window(None, {'pos':2, "vertical":False, "padding":15, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.0), 'border_color':(0.50, 0.50, 0.50, 0.9), "border_width":4.0})
        next_back_container = win_next_back.add(ui.UI_Container(vertical = False, background = (0.50, 0.50, 0.50, 0.90)))
        #next_back_frame = next_back_container.add(ui.UI_Frame('', vertical = False, equal = True, separation = 4))#, background = (0.50, 0.50, 0.50, 0.90)))
            
        #back_button = next_back_container.add(ui.UI_Button('Back', mode_backer, margin = 10))
        #back_button.label.fontsize = 20
            
        #cancel_button = next_back_frame.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=0))
        cancel_button = next_back_container.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin=10))
        cancel_button.label.fontsize = 20
        calc_plane_button = next_back_container.add(ui.UI_Button('Finish', self.next, margin = 10))
        calc_plane_button.label.fontsize = 20
        
        #next_button = next_back_frame.add(ui.UI_Button('Next', mode_stepper, margin = 0))
        
        
        self.set_ui_text()
        



      
def register():
    bpy.utils.register_class(D3DUAL_OT_cookie_cutter_landmarks)
    
     
def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_cookie_cutter_landmarks)
