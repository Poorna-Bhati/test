'''
Created on Aug 9, 2019

@author: Patrick


#citations
https://www.ommegaonline.org/article-details/The-Relationship-between-the-Lip-Length-and-Smile-Line-in-a-Malaysian-Population-A-Cross-Sectional-Study/1385

'''
import math
import random

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
from mathutils import Vector, Matrix

# Addon imports

from common_utilities import get_settings


from submodules.pts_picker.operators.points_picker import VIEW3D_OT_points_picker
from submodules.pts_picker.addon_common.common import ui
from submodules.pts_picker.functions.common import showErrorMessage


class D3SPLINT_OT_cookie_cutter_landmarks(VIEW3D_OT_points_picker):
    """ Click on the posterior contacts """
    bl_idname = "d3dual.mark_landmarks_cookie"
    bl_label = "Define Splint Landmarks"
    bl_description = "Indicate points to define the occlusal plane"

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
        
        max_model = self.splint.get_maxilla()
        mand_model = self.splint.get_mandible()
        
        #if self.splint.jaw_type == 'MANDIBLE' and max_model == '':
        #    Model = bpy.data.objects.get(mand_model)
            
        #else:
        Model = bpy.data.objects.get(max_model)
        Mand_Model = bpy.data.objects.get(mand_model)
             
        #make sure articulator is in the correct spot
        self.context.scene.frame_set(0)
        self.context.scene.frame_set(0)
        
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
        labels = ["Right Molar", "Left Molar", "Incisal Edge", "Midline"]
        
        if len(self.b_pts) > 4:
            self.b_pts = self.b_pts[0:4]
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

    def remove_point_post(self):
        labels = ["Right Molar", "Left Molar", "Incisal Edge", "Midline"]
        
        if len(self.b_pts) > 4:
            self.b_pts = self.b_pts[0:4]
            return

        for pt in self.b_pts:
            if pt.label in labels:
                labels.remove(pt.label)
        if len(labels) >= 1:
            self.win_obvious_instructions.visible = True
            self.win_obvious_instructions.hbf_title.set_label('Click ' + labels[0])  
        else:
            self.win_obvious_instructions.visible = False    
        
        
        
    def get_transform_data(self, mx, imx):
        '''
        mx and imx are the world matrix and it's inverse of the  model
        '''
        settings = get_settings()
        mx_data = {}
        
        bp_rm = [bpt for bpt in self.b_pts if bpt.label == 'Right Molar'][0]
        bp_lm = [bpt for bpt in self.b_pts if bpt.label == 'Left Molar'][0]
        bp_ie = [bpt for bpt in self.b_pts if bpt.label == 'Incisal Edge'][0]
        bp_ml = [bpt for bpt in self.b_pts if bpt.label == 'Midline'][0]
        
        v_R = imx * bp_rm.location #R molar
        v_L = imx * bp_lm.location #L molar 
        v_I = imx * bp_ie.location #Incisal Edge
        v_M = imx * bp_ml.location #midline
        
        #calculate the center (still in model local coordinates
        center = 1/3 * (v_R + v_L + v_I)
        mx_center = Matrix.Translation(center)
        imx_center = mx_center.inverted()
        
        ##Calculate the plane normal, and the rotation matrix that
        #orientes to that plane.
        vec_R =  v_R - v_L #vector pointing from left to right
        vec_R.normalize()
        
        vec_L = v_L - v_R #vector pointing from right to left
        vec_L.normalize()
        
        vec_I = v_I - v_R  #incisal edge frpm righ
        vec_I.normalize()
        
        vec_M = v_M -v_R   #midlind from right
        vec_M.normalize()
        
        Z = vec_I.cross(vec_L)  #The normal of the occlusal plane in Model LOCAL space
        Z.normalize()
                
        #X = v_M - center  #center point to midline  #OLD WAY
        #X = X - X.dot(Z) * Z #minus any component in occlusal plane normal direction 
        #X.normalize()
        
        Y = center - v_M   #center point to midline pointing posterior
        Y = Y - Y.dot(Z) * Z #minus any component in occlusal plane normal direction 
        Y.normalize()
        
        #Y = Z.cross(X)
        #Y.normalize()
        X = Y.cross(Z) #NEW/LPS
        X.normalize()
        
        #FORMER conventions was X-> Forward, Y-< Left, Z Up
        #NEW/Standard  LPS ->  X LEFT, Y posterior, Z up

        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2] 
        R = R.to_4x4()
        iR = R.inverted()
        ### NOW WE HAVE THE OCCLUSAL PLANE DESCRIBED
        
        mx_data['Occlusal Plane Matrix'] = R
        mx_data['Occlusal Plane iMatrix'] = iR
        
        #The Midine Poistion at the height of the incisal edge
        #Or the Incial Edge positiong projected onto the midline
        #v_M_corrected = v_I - (v_I - center).dot(Y) * Y
        v_M_corrected = v_I - (v_I - center).dot(X) * X 
        
        #Matrices assoicated with the oclusal plane cant
        #Lets Calculate the matrix transform for
        #the Fox plane cant from the user preferences
        X_w = Vector((1,0,0))
        Y_w = Vector((0,1,0))
        Z_w = Vector((0,0,1))
        
        op_angle = settings.def_occlusal_plane_angle
        #Fox_R = Matrix.Rotation(op_angle * math.pi /180, 3, 'Y')  #The Y axis represents a line drawn through the centers of condyles from right to left
        Fox_R = Matrix.Rotation(op_angle * math.pi /180, 3, 'X')  #The X axis represents a line drawn through the centers of condyles from right to left
        Z_fox = Fox_R * Z_w
        #X_fox = Fox_R * X_w
        Y_fox = Fox_R * Y_w
        
        R_fox = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R_fox[0][0], R_fox[0][1], R_fox[0][2]  = X_w[0] ,Y_fox[0],  Z_fox[0]
        R_fox[1][0], R_fox[1][1], R_fox[1][2]  = X_w[1], Y_fox[1],  Z_fox[1]
        R_fox[2][0] ,R_fox[2][1], R_fox[2][2]  = X_w[2], Y_fox[2],  Z_fox[2]
        R_fox = R_fox.to_4x4()
        
        mx_data['Fox Plane'] = R_fox
        
        #average distance from campers plane to occlusal
        #plane is 30 mm
        #file:///C:/Users/Patrick/Downloads/CGBCC4_2014_v6n6_483.pdf
        
        center = R_fox * iR * center
        v_ant = R_fox * iR * v_M_corrected
        
        if 'Articulator' not in bpy.data.objects:  #get defaults
            #x_radius = (settings.def_arm_radius **2 -  (.5 * settings.def_intra_condyle_width)**2)**.5
            y_radius = (settings.def_arm_radius **2 -  (.5 * settings.def_intra_condyle_width)**2)**.5
            
            balk_radians = settings.def_balkwill_angle * math.pi/180
            
        else:  #get settings from existing articulator
            art = bpy.data.objects.get('Articulator')
            #x_radius = (settings.def_arm_radius **2 -  (.5 * art.get('intra_condyle_width'))**2)**.5
            y_radius = (settings.def_arm_radius **2 -  (.5 * art.get('intra_condyle_width'))**2)**.5
            
            balk_radians = settings.def_balkwill_angle * math.pi/180
        
        if "Subnasion_empty" not in bpy.data.objects:
 
            balk_mx = Matrix.Rotation(balk_radians, 3, 'X')
            incisal_final = Vector((0,-y_radius, 0))
            incisal_final.rotate(balk_mx)    
            mx_data['incisal'] = incisal_final
        else:
            mx_incisal = bpy.data.objects.get('Subnasion_empty').matrix_world
            incisal_final = mx_incisal.to_translation() + Vector((0, 10, -20))
            mx_data['incisal'] = incisal_final
            
        
        
        T_incisal = Matrix.Translation(iR * v_M_corrected)
        T = Matrix.Translation(incisal_final-v_ant)
        mx_mount = T * R_fox
        
        mx_data['Mount'] = mx_mount
        
        return mx_data    
    
    def next(self):
        
        if len(self.b_pts) < 4:
            showErrorMessage("You have not marked all of the landmarks")
            return
        
        self.done()
               
        
    def getLabel(self, idx):
        return "P %(idx)s" % locals()

    def get_matrix_world_for_point(self, pt):
       
        if pt.label == "Replacement Point":
            #Z = pt.view_direction * Vector((0,0,1))  #TODO until pt.view_direction is not a quaternion
            Z = -pt.view_direction
        else:
            Z = pt.surface_normal
           
        x_rand = Vector((random.random(), random.random(), random.random()))
        x_rand.normalize()

        if abs(x_rand.dot(Z)) > .9:
            x_rand = Vector((random.random(), random.random(), random.random()))
            x_rand.normalize()
        X = x_rand - x_rand.dot(Z) * Z
        X.normalize()

        Y = Z.cross(X)

        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
        R = R.to_4x4()

        if pt.label == "Replacement Point":
            T = Matrix.Translation(pt.location + 2 * Z)
        else:
            T = Matrix.Translation(pt.location)

        return T * R
    #############################################

    def end_commit(self):
        settings = get_settings()
        
        #Spcial case, lower splint, no maxillary model.  Typically landmarks are always set on maxilla if maxillary model available
        #if self.splint.jaw_type == 'MANDIBLE' and self.splint.get_maxilla() == '':
        #    Model = bpy.data.objects[self.splint.get_mandible()]
        # 
        #else:
        Model =  bpy.data.objects[self.splint.get_maxilla()]
            
        mx = Model.matrix_world
        imx = mx.inverted()
        
        mx_data = self.get_transform_data(mx, imx)
        
        Mand_Model = bpy.data.objects.get(self.splint.get_mandible())
        if Mand_Model:
            mx_mand = Mand_Model.matrix_world
            imx_mand = mx_mand.inverted()
        
        #store child to parent oreintations before we mess with the parent matrix
        children = [ob for ob in Model.children]
        mx_children= {}
        for child in children:
            mx_children[child] = child.matrix_local.copy()
        
        #de-rotate the Model data so that it is aligned with occlusal plane
        #Plane normal defines Z axis
        #X axis is torward anterior
        #Y axis points from right o left (right hadn rule wit x and z)
        iR = mx_data['Occlusal Plane iMatrix']
        Model.data.transform(iR)
        
        #now to apply the equivlent rotation to children, since we did not
        #apply that rotation to the parent object, but rather to the parent data
        #Model_origin = mx.to_translation()
        #Model_rotation = mx.to_quaternion()
        
        #world_ir = iR.copy().to_3x3()
        #world_ir.rotate(Model_rotation)
        #ir4 = world_ir.to_4x4()
        
        for child in children:
            #get existing matrix
            mx_local = mx_children[child]
            child.matrix_world = mx * iR * mx_local
           

        
       
        m_children = [ob for ob in Mand_Model.children]
        mx_mchildren= {}
        for child in m_children:
            mx_mchildren[child] = child.matrix_local.copy()
    
    
        Mand_Model.data.transform(mx_mand)  #apply current transform
        Mand_Model.data.transform(imx) #make coordinate system the same as Model
        Mand_Model.data.transform(iR) #do the same de-rotation relative to the occlusal plane

        #apply the same transforms to the children
        for child in m_children:
            mx_local = mx_mchildren[child]
            #child.matrix_world = mx * iR * imx * mx_mand * mx_local
            child.matrix_local = iR * imx * mx_mand * mx_local

        #now put the Mand Model where it belongs...children follow
        Mand_Model.matrix_world = mx#set same world matrix as Model
                
                
        for ob in bpy.data.objects:
            ob.hide = False      
        
        incisal_final = mx_data['incisal']
        mx_mount = mx_data['Mount']
        Model.matrix_world =  mx_mount
        
        if 'Incisal' not in bpy.data.objects:
            empty = bpy.data.objects.new('Incisal', None)
            bpy.context.scene.objects.link(empty)
            #now it stays with Model forever
            empty.parent = Model
            empty.matrix_world = Matrix.Translation(incisal_final)
        else:
            empty = bpy.data.objects.get('Incisal')
            empty.matrix_world = Matrix.Translation(incisal_final)    
            
        
             
        if len(Mand_Model.constraints):
            for cons in Mand_Model.constraints:
                Mand_Model.constraints.remove(cons)

        Mand_Model.matrix_world = mx_mount
        Mand_Model.hide = False
            
        cons = Mand_Model.constraints.new('CHILD_OF')
        cons.target = Model
        cons.inverse_matrix = Model.matrix_world.inverted()
    
        if "Mandibular Orientation" in bpy.data.objects:
            Transform = bpy.data.objects.get('Mandibular Orientation')
        else:
            Transform = bpy.data.objects.new('Mandibular Orientation', None)
            Transform.parent = Model
            bpy.context.scene.objects.link(Transform)
            #Transform["stored_position"] = True  #store a custom property to tag this as a stored position
        Transform.matrix_world = mx_mount
                
        #TODO trim lines, silhoettes etc
        
        
        bpy.context.scene.cursor_location = Model.location
        bpy.ops.view3d.view_center_cursor()
        
        
        self.splint.landmarks_set = True
        
        if 'Articulator' not in bpy.context.scene.objects:#, 'DEPROGRAMMER'}:
            
            bpy.ops.d3dual.generate_articulator(
                intra_condyle_width = settings.def_intra_condyle_width,
                condyle_angle = settings.def_condyle_angle,
                bennet_angle = settings.def_bennet_angle,
                incisal_guidance = settings.def_incisal_guidance,
                canine_guidance = settings.def_canine_guidance,
                guidance_delay_ant = settings.def_guidance_delay_ant,
                guidance_delay_lat = settings.def_guidance_delay_lat)
            
            

        for ob in bpy.data.objects:
            ob.select = False
        
        bpy.context.space_data.show_manipulator = True
        bpy.context.space_data.transform_manipulators = {'TRANSLATE','ROTATE'}
        
        if self.splint.face_model:
            ob = bpy.data.objects.get(self.splint.face_model)
            ob.show_transparent = True
            ob.data.materials[0].alpha = .5
            
           
        bpy.context.scene.objects.active = Model               
        Model.select = True
        Model.hide = False
        bpy.ops.view3d.viewnumpad(type = 'FRONT')
        #tracking.trackUsage("D3Dual:SplintLandmarks",None)
        self.splint.ops_string += 'Set Landmarks:'
        
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
            "Requirements": "Click the Right Molar, Left Molar, Incisal Edge and then Midline"
        }
        
        for i,val in enumerate(['Add', 'Grab', 'Remove', "Requirements"]):
            self.inst_paragraphs[i].set_markdown(chr(65 + i) + ") " + self.new_instructions[val])

        
        
        self.win_obvious_instructions = self.wm.create_window('Click Right Molar', {'pos':8, "vertical":False, "padding":15, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.5), 'border_color':(0.50, 0.50, 0.50, 0.9), "border_width":4.0})
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
        


class D3SPLINT_OT_cookie_cutter_mand_landmarks(VIEW3D_OT_points_picker):
    """ Click on the posterior contacts """
    bl_idname = "d3dual.mark_mand_landmarks"
    bl_label = "Define Mandibular Landmarks"
    bl_description = "Indicate points to define the occlusal plane"

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
        
        mand_model = self.splint.get_mandible()
        
        Model = bpy.data.objects.get(mand_model)
             
        #make sure articulator is in the correct spot
        self.context.scene.frame_set(0)
        self.context.scene.frame_set(0)
        
        for ob in bpy.data.objects:
            ob.select = False
            ob.hide = True
        Model.select = True
        Model.hide = False
        bpy.context.scene.objects.active = Model
        
        
        bpy.ops.view3d.viewnumpad(type = 'TOP')
        bpy.ops.view3d.view_selected()

        bpy.context.space_data.show_manipulator = False
        bpy.context.space_data.transform_manipulators = {'TRANSLATE','ROTATE'}
        v3d = bpy.context.space_data
        v3d.pivot_point = 'MEDIAN_POINT'
   
    def resetLabels(self):  #must override this becuase we have pre-defineid label names
        return          
    def add_point_post(self, pt_added):
        labels = ["Right Molar", "Left Molar", "Incisal Edge", "Midline"]
        
        if len(self.b_pts) > 4:
            self.b_pts = self.b_pts[0:4]
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

    def remove_point_post(self):
        labels = ["Right Molar", "Left Molar", "Incisal Edge", "Midline"]
        
        if len(self.b_pts) > 4:
            self.b_pts = self.b_pts[0:4]
            return

        for pt in self.b_pts:
            if pt.label in labels:
                labels.remove(pt.label)
        if len(labels) >= 1:
            self.win_obvious_instructions.visible = True
            self.win_obvious_instructions.hbf_title.set_label('Click ' + labels[0])  
        else:
            self.win_obvious_instructions.visible = False    
        
        
        
    def get_transform_data(self, mx, imx):
        '''
        mx and imx are the world matrix and it's inverse of the  model
        '''
        settings = get_settings()
        mx_data = {}
        
        bp_rm = [bpt for bpt in self.b_pts if bpt.label == 'Right Molar'][0]
        bp_lm = [bpt for bpt in self.b_pts if bpt.label == 'Left Molar'][0]
        bp_ie = [bpt for bpt in self.b_pts if bpt.label == 'Incisal Edge'][0]
        bp_ml = [bpt for bpt in self.b_pts if bpt.label == 'Midline'][0]
        
        v_R = imx * bp_rm.location #R molar
        v_L = imx * bp_lm.location #L molar 
        v_I = imx * bp_ie.location #Incisal Edge
        v_M = imx * bp_ml.location #midline
        
        #calculate the center (still in model local coordinates
        center = 1/3 * (v_R + v_L + v_I)
        mx_center = Matrix.Translation(center)
        imx_center = mx_center.inverted()
        
        ##Calculate the plane normal, and the rotation matrix that
        #orientes to that plane.
        vec_R =  v_R - v_L #vector pointing from left to right
        vec_R.normalize()
        
        vec_L = v_L - v_R #vector pointing from right to left
        vec_L.normalize()
        
        vec_I = v_I - v_R  #incisal edge frpm righ
        vec_I.normalize()
        
        vec_M = v_M -v_R   #midlind from right
        vec_M.normalize()
        
        Z = vec_I.cross(vec_L)  #The normal of the occlusal plane in Model LOCAL space
        Z.normalize()
                
        X = v_M - center  #center point to midline
        X = X - X.dot(Z) * Z #minus any component in occlusal plane normal direction 
        X.normalize()
        
        Y = Z.cross(X)
        Y.normalize()

        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2] 
        R = R.to_4x4()
        iR = R.inverted()
        ### NOW WE HAVE THE OCCLUSAL PLANE DESCRIBED
        
        mx_data['Occlusal Plane Matrix'] = R
        mx_data['Occlusal Plane iMatrix'] = iR
        
        #The Midine Poistion at the height of the incisal edge
        #Or the Incial Edge positiong projected onto the midline
        v_M_corrected = v_I - (v_I - center).dot(Y) * Y 
        
        #Matrices assoicated with the oclusal plane cant
        #Lets Calculate the matrix transform for
        #the Fox plane cant from the user preferences
        Z_w = Vector((0,0,1))
        X_w = Vector((1,0,0))
        Y_w = Vector((0,1,0))
        
        op_angle = settings.def_occlusal_plane_angle
        Fox_R = Matrix.Rotation(op_angle * math.pi /180, 3, 'Y')  #The Y axis represents a line drawn through the centers of condyles from right to left
        Z_fox = Fox_R * Z_w
        X_fox = Fox_R * X_w
        
        R_fox = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R_fox[0][0], R_fox[0][1], R_fox[0][2]  = X_fox[0] ,Y_w[0],  Z_fox[0]
        R_fox[1][0], R_fox[1][1], R_fox[1][2]  = X_fox[1], Y_w[1],  Z_fox[1]
        R_fox[2][0] ,R_fox[2][1], R_fox[2][2]  = X_fox[2], Y_w[2],  Z_fox[2]
        R_fox = R_fox.to_4x4()
        
        mx_data['Fox Plane'] = R_fox
        
        #average distance from campers plane to occlusal
        #plane is 30 mm
        #file:///C:/Users/Patrick/Downloads/CGBCC4_2014_v6n6_483.pdf
        
        center = R_fox * iR * center
        v_ant = R_fox * iR * v_M_corrected
        
        if 'Articulator' not in bpy.data.objects:  #get defaults
            x_radius = (settings.def_arm_radius **2 -  (.5 * settings.def_intra_condyle_width)**2)**.5
            balk_radians = settings.def_balkwill_angle * math.pi/180
            
        else:  #get settings from existing articulator
            art = bpy.data.objects.get('Articulator')
            x_radius = (settings.def_arm_radius **2 -  (.5 * art.get('intra_condyle_width'))**2)**.5
            balk_radians = settings.def_balkwill_angle * math.pi/180
        
        if "Subnasion_empty" not in bpy.data.objects:
            print( 'NO SUBNASINO BITCHES') 
            balk_mx = Matrix.Rotation(balk_radians, 3, 'Y')
            incisal_final = Vector((x_radius, 0, 0))
            incisal_final.rotate(balk_mx)    
            mx_data['incisal'] = incisal_final
        else:
            print('SUBNASION BITCESH')
            mx_incisal = bpy.data.objects.get('Subnasion_empty').matrix_world
            incisal_final = mx_incisal.to_translation() + Vector((0, 5, -15))
            mx_data['incisal'] = incisal_final
            
            
        T_incisal = Matrix.Translation(iR * v_M_corrected)
        T = Matrix.Translation(incisal_final-v_ant)
        mx_mount = T * R_fox
        
        mx_data['Mount'] = mx_mount
        
        return mx_data    
    
    def next(self):
        
        if len(self.b_pts) < 4:
            showErrorMessage("You have not marked all of the landmarks")
            return
        
        self.done()
               
        
    def getLabel(self, idx):
        return "P %(idx)s" % locals()

    def get_matrix_world_for_point(self, pt):
       
        if pt.label == "Replacement Point":
            #Z = pt.view_direction * Vector((0,0,1))  #TODO until pt.view_direction is not a quaternion
            Z = -pt.view_direction
        else:
            Z = pt.surface_normal
           
        x_rand = Vector((random.random(), random.random(), random.random()))
        x_rand.normalize()

        if abs(x_rand.dot(Z)) > .9:
            x_rand = Vector((random.random(), random.random(), random.random()))
            x_rand.normalize()
        X = x_rand - x_rand.dot(Z) * Z
        X.normalize()

        Y = Z.cross(X)

        R = Matrix.Identity(3)  #make the columns of matrix U, V, W
        R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
        R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
        R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
        R = R.to_4x4()

        if pt.label == "Replacement Point":
            T = Matrix.Translation(pt.location + 2 * Z)
        else:
            T = Matrix.Translation(pt.location)

        return T * R
    #############################################

    def end_commit(self):
        settings = get_settings()
        
        #Spcial case, lower splint, no maxillary model.  Typically landmarks are always set on maxilla if maxillary model available
        #if self.splint.jaw_type == 'MANDIBLE' and self.splint.get_maxilla() == '':
        #    Model = bpy.data.objects[self.splint.get_mandible()]
        # 
        #else:
        Model =  bpy.data.objects[self.splint.get_mandible()]
            
        mx = Model.matrix_world
        imx = mx.inverted()
        
        mx_data = self.get_transform_data(mx, imx)
        
        
        bpy.context.scene.objects.active = Model               
        Model.select = True
        Model.hide = False
        #tracking.trackUsage("D3Dual:SplintLandmarks",None)
        self.splint.ops_string += 'Set Mand Landmarks:'
        
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
            "Requirements": "Click the Right Molar, Left Molar, Incisal Edge and then Midline"
        }
        
        for i,val in enumerate(['Add', 'Grab', 'Remove', "Requirements"]):
            self.inst_paragraphs[i].set_markdown(chr(65 + i) + ") " + self.new_instructions[val])

        
        
        self.win_obvious_instructions = self.wm.create_window('Click Right Molar', {'pos':8, "vertical":False, "padding":15, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.5), 'border_color':(0.50, 0.50, 0.50, 0.9), "border_width":4.0})
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
    bpy.utils.register_class(D3SPLINT_OT_cookie_cutter_landmarks)
    
     
def unregister():
    bpy.utils.unregister_class(D3SPLINT_OT_cookie_cutter_landmarks)
    