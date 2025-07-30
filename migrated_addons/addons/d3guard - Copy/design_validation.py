'''
Created on Jul 4, 2018 5:40AM (local time) 11:40 in Italian time

@author: Patrick Moore
Based off of some of the 3D printing toolbox (included addon)
and using some vertex color, matrerial properties for visualization
'''

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Color
from bpy.props import EnumProperty, FloatProperty, BoolProperty
import time
import tracking
from object_print3d_utils import mesh_helpers
from bpy_extras import view3d_utils
from mathutils.bvhtree import BVHTree

def setup_mat_and_vcolor(ob, layer_name):
    
    #Setup vertex color layer
    ########################################
    if layer_name not in ob.data.vertex_colors:
        vcol = ob.data.vertex_colors.new(name = layer_name)
    else:
        vcol = ob.data.vertex_colors.get(layer_name)
        
    #Make Material with same name
    #######################################
    if layer_name not in bpy.data.materials:
        mat = bpy.data.materials.new(layer_name)
        mat.use_shadeless = True
        mat.use_vertex_color_paint = True
    else:
        mat = bpy.data.materials.get(layer_name)
        mat.use_shadeless = True
        mat.use_vertex_color_paint = True
    if layer_name not in ob.data.materials:
        ob.data.materials.append(mat)
    
    ob.material_slots[0].material = mat
    
    return vcol, mat
    
def bmesh_check_thick_object(bm, thickness):
    '''
    -Expects a BMesh object, triangulated
    will TRIANGULATE your bmesh for you
    but will not push the bmesh back in to the mesh
    '''
    
    # map original faces to their index.
    face_index_map_org = {f: i for i, f in enumerate(bm.faces)}
    ret = bmesh.ops.triangulate(bm, faces=bm.faces)
    face_map = ret["face_map"]
    del ret
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    # old edge -> new mapping

    # Convert new/old map to index dict.

    # Create a BVHTree to accelerate ray_casting
    bvh = BVHTree.FromBMesh(bm)
    
    ray_cast = bvh.ray_cast

    EPS_BIAS = .01
    EPS_MIN_AREA = .5 ** 2 #TODO, this should be related to thickenss checking?

    faces_error_inds = set()
    bmfaces_error = set()

    bm_faces_new = bm.faces[:]
    i = len(bm_faces_new)
    print('Raycasting %i faces now' % i)
    for f in bm_faces_new:
        no = f.normal
        no_sta = no * EPS_BIAS
        no_end = no * thickness
        
        if f.calc_area() > EPS_MIN_AREA:
            #print("randomizing a large face")
            for p in mesh_helpers.bmesh_face_points_random(f, num_points=6):
                # Cast the ray backwards
                p_a = p - no_sta
                p_b = p - no_end
                p_dir = p_b - p_a
    
                co, no, index, d = ray_cast(p_a, -f.normal, thickness)
    
                if d != None and d < thickness - EPS_BIAS:
                    if d < 0.0:
                        print('Negative distance')
                    # Add the face we hit
                    bmfaces_error.add(f)
                    for f_iter in (f, bm_faces_new[index]):
                        # if the face wasn't triangulated, just use existing
                        f_org = face_map.get(f_iter, f_iter)
                        f_org_index = face_index_map_org[f_org]
                        faces_error_inds.add(f_org_index)
        else:
            # Cast the ray backwards
            p = f.calc_center_median()  #TODO test if calc_center_median is faster
            p_a = p - no_sta
            p_b = p - no_end
            p_dir = p_b - p_a

            co, no, index, d = ray_cast(p_a, -f.normal, thickness)

            if d != None and d < thickness:
                if d < 0.0:
                    print('Negative distance')
                # Add the face we hit
                bmfaces_error.add(f)
                for f_iter in (f, bm_faces_new[index]):
                    # if the face wasn't triangulated, just use existing
                    f_org = face_map.get(f_iter, f_iter)
                    f_org_index = face_index_map_org[f_org]
                    faces_error_inds.add(f_org_index)
    
    #do not free bmesh because using it again
    del bvh
    return faces_error_inds, bmfaces_error


def bmesh_check_thick_object_against(bm, thickness, bvh):
    '''
    -Expects a BMesh object, triangulated
    will TRIANGULATE your bmesh for you
    but will not push the bmesh back in to the mesh
    '''
    
    # map original faces to their index.
    face_index_map_org = {f: i for i, f in enumerate(bm.faces)}
    ret = bmesh.ops.triangulate(bm, faces=bm.faces)
    face_map = ret["face_map"]
    del ret
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    # old edge -> new mapping

    # Convert new/old map to index dict.

    # Create a BVHTree to accelerate ray_casting
    #bvh = BVHTree.FromBMesh(bm)
    
    ray_cast = bvh.ray_cast

    EPS_BIAS = .01
    EPS_MIN_AREA = .5 ** 2 #TODO, this should be related to thickenss checking?

    faces_error_inds = set()
    bmfaces_error = set()

    bm_faces_new = bm.faces[:]
    i = len(bm_faces_new)
    print('Raycasting %i faces now' % i)
    for f in bm_faces_new:
        no = f.normal
        no_sta = no * EPS_BIAS
        no_end = no * thickness
        
        if f.calc_area() > EPS_MIN_AREA:
            #print("randomizing a large face")
            for p in mesh_helpers.bmesh_face_points_random(f, num_points=6):
                # Cast the ray backwards
                p_a = p - no_sta
                p_b = p - no_end
                p_dir = p_b - p_a
    
                co, no, index, d = ray_cast(p_a, -f.normal, thickness)
    
                if d != None and d < thickness:
                    if d < 0.0:
                        print('Negative distance')
                    # Add the face we hit
                    bmfaces_error.add(f)
                    for f_iter in (f, bm_faces_new[index]):
                        # if the face wasn't triangulated, just use existing
                        f_org = face_map.get(f_iter, f_iter)
                        f_org_index = face_index_map_org[f_org]
                        faces_error_inds.add(f_org_index)
        else:
            # Cast the ray backwards
            p = f.calc_center_median()  #TODO test if calc_center_median is faster
            p_a = p - no_sta
            p_b = p - no_end
            p_dir = p_b - p_a

            co, no, index, d = ray_cast(p_a, -f.normal, thickness)

            if d != None and d < thickness-EPS_BIAS:
                if d < 0.0:
                    print('Negative distance')
                # Add the face we hit
                bmfaces_error.add(f)
                for f_iter in (f, bm_faces_new[index]):
                    # if the face wasn't triangulated, just use existing
                    f_org = face_map.get(f_iter, f_iter)
                    f_org_index = face_index_map_org[f_org]
                    faces_error_inds.add(f_org_index)
    
    return faces_error_inds, bmfaces_error

def bmesh_check_thick_object_verts(bm, thickness):
    '''
    -Expects a BMesh object, triangulated
    will TRIANGULATE your bmesh for you
    but will not push the bmesh back in to the mesh
    '''
    # Create a BVHTree to accelerate ray_casting
    bvh = BVHTree.FromBMesh(bm)
    
    ray_cast = bvh.ray_cast

    EPS_BIAS = .01
    EPS_MIN_AREA = .5 ** 2 #TODO, this should be related to thickenss checking?

    verts_error = set()

    for v in bm.verts:
        no = v.normal
        no_sta = no * EPS_BIAS
        no_end = no * thickness

        # Cast the ray backwards
        p = v.co  #TODO test if calc_center_median is faster
        p_a = p - no_sta
        p_b = p - no_end
        p_dir = p_b - p_a
        co, no, index, d = ray_cast(p_a, - v.normal, thickness)

        if d != None and d < thickness - EPS_BIAS:
            if d < 0.0:
                print('Negative distance')
            # Add the face we hit
            verts_error.add(v)
    
    #do not free bmesh because using it again
    del bvh
    return verts_error

def bmesh_check_thick_object_verts_against(bm, thickness, bvh):
    '''
    -Expects a BMesh object, triangulated
    will TRIANGULATE your bmesh for you
    but will not push the bmesh back in to the mesh
    
    -takes a BVH in the same coordinate system a bm
    
    
    '''    
    ray_cast = bvh.ray_cast

    EPS_BIAS = .01
    EPS_MIN_AREA = .5 ** 2 #TODO, this should be related to thickenss checking?

    verts_error = set()

    for v in bm.verts:
        no = v.normal
        no_sta = no * EPS_BIAS
        no_end = no * thickness

        # Cast the ray backwards
        p = v.co  #TODO test if calc_center_median is faster
        p_a = p - no_sta
        p_b = p - no_end
        p_dir = p_b - p_a
        co, no, index, d = ray_cast(p_a, - v.normal, thickness)

        if d != None and d < thickness-EPS_BIAS:
            
            r = thickness - d
            if d < 0.0:
                print('Negative distance')
                
            # Add the face we hit
            verts_error.add(v)
    
    #do not free bmesh because using it again
    return verts_error


class D3SPLINT_OT_splint_finish_check_thickness(bpy.types.Operator):
    """Check for thin parts"""
    bl_idname = "d3splint.splint_check_thickness"
    bl_label = "Check Appliance Thickness"
    bl_options = {'REGISTER', 'UNDO'}
    
    jaw_mode = EnumProperty(default = 'MAX', items = (('MAX','MAX','MAX'),('MAND','MAND','MAND')))
    check_mode = EnumProperty(default = 'VERTS', items = (('FACES','FACES','FACES'),('VERTS','VERTS','VERTS')))
    thickness_min = FloatProperty(default = 0.5, min = .01, max = 3.0)
    
    check_against = EnumProperty(default = 'REFRACTORY', items = (('SELF','SELF','SELF'),('REFRACTORY','REFRACTORY','REFRACTORY')))
    #correct = BoolProperty(default = False, name = "Correct Verts")
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def invoke(self,context,event):
        
        return context.window_manager.invoke_props_dialog(self)
    
    
    def sculpt_fix_thin(self, context, Shell, verts):
        
        mx = Shell.matrix_world
        imx = mx.inverted()
        world_sculpt_verts = [mx * v.co for v in verts]
        context.scene.objects.active = Shell
        Shell.select = True
        Shell.hide = False
        bpy.ops.object.mode_set(mode = 'SCULPT')
        bpy.ops.view3d.view_selected()
            
        if not Shell.use_dynamic_topology_sculpting:
            bpy.ops.sculpt.dynamic_topology_toggle()
        
        scene = context.scene
        paint_settings = scene.tool_settings.unified_paint_settings
        paint_settings.use_locked_size = True
        paint_settings.unprojected_radius = self.thickness_min
        brush = bpy.data.brushes['Inflate/Deflate']
        scene.tool_settings.sculpt.brush = brush
        scene.tool_settings.sculpt.detail_type_method = 'CONSTANT'
        
        
        #if bversion() < '002.079.000':
            #scene.tool_settings.sculpt.constant_detail = 50
        #else:
        #enforce 2.79
        scene.tool_settings.sculpt.constant_detail_resolution = 3.5
        
        scene.tool_settings.sculpt.use_symmetry_x = False
        scene.tool_settings.sculpt.use_symmetry_y = False
        scene.tool_settings.sculpt.use_symmetry_z = False
        brush.strength = .5
        
        brush.use_frontface = False
        brush.stroke_method = 'DOTS'
        
        screen = bpy.context.window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for reg in area.regions:
                    if reg.type == 'WINDOW':
                        break
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        break    
                break
        
        override = bpy.context.copy()
        override['area'] = area
        override['region'] = reg
        override['space_data'] = space
        override['region_data'] = space.region_3d
        override['active_object'] = Shell
        override['object'] = Shell
        override['sculpt_object'] = Shell
        
        
        stroke = []
        i = 0
        for co in world_sculpt_verts:
            #if i > 100: break
            i += 1
            mouse = view3d_utils.location_3d_to_region_2d(reg, space.region_3d, co)
            l_co = imx * co
            stroke = [{"name": "my_stroke",
                        "mouse" : (mouse[0], mouse[1]),
# [Blender 4.4] Warning: 'pen_flip' parameter removed from painting operators.

                        "is_start": True,
                        "location": (l_co[0], l_co[1], l_co[2]),
                        "pressure": 1,
                        "size" : 30,
                        "time": 1}]
                      
            bpy.ops.sculpt.brush_stroke(override, stroke=stroke, mode='NORMAL', ignore_background_click=False)
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
    
    
    def execute(self, context):
        start_time = time.time()
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        
        #prefs = get_settings()
        #if not prefs.non_clinical_use:
        #    self.report({'ERROR'}, 'You must certify non-clinical use in your addon preferences or in the panel')
        #    return {'CANCELLED'}
        
        
        #TODO repeat for every model?...seems DUMB
        #
        if self.jaw_mode == 'MAX':
            splint_shell ='Splint Shell_MAX'
            r_model = 'Max Refractory Model'
            
            
        else:
            splint_shell ='Splint Shell_MAND'
            r_model = 'Mand Refractory Model'
            
         
        Shell = bpy.data.objects.get(splint_shell)
        Shell.hide = False
        #TODO make this represent the sleep appliances
        if Shell == None:
            self.report({'ERROR'}, 'Need to calculate splint shell for this arch first')
            return {'CANCELLED'}
        
        if len(Shell.modifiers):
            self.report({'ERROR'}, 'Need to finalize labels and/or notches first')
            return {'CANCELLED'}
        
            
        if self.check_against == 'REFRACTORY':
            Refractory = bpy.data.objects.get(r_model)
            if Refractory == None:
                self.report({'ERROR'}, 'You must calculate refactory model for this arch first')
                return {'CANCELLED'}
            Refractory.hide = False
            
        setup_mat_and_vcolor(Shell, "Design Verification")
        
        
        signature = "Validate " + splint_shell + " vs " + self.check_against + " >= " + str(self.thickness_min)[0:4] + "mm:"
        splint.ops_string += signature
        
        
        # Triangulate
        bm = bmesh.new()
        bm.from_mesh(Shell.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
    
        #get the vertex color layer
        vcol_layer = bm.loops.layers.color["Design Verification"]
            
            
        #########################################
        #for now, use the existing 3d print tools
        #TODO rewrite with accelerated BVH strcuture to avoid temporary object!
        #TODO only randomly triangulate faces with area > (.3 x .3)
        
        white = Color((1.0,1.0,1.0))
        red = Color((1.0, .2, .2))
        
        if self.check_mode == 'VERTS':
        
            if self.check_against == 'SELF':
                verts_error = bmesh_check_thick_object_verts(bm, self.thickness_min)
                
            elif self.check_against == 'REFRACTORY':
                rbm = bmesh.new()
                rbm.from_mesh(Refractory.data)
                rbm.verts.ensure_lookup_table()
                rbm.edges.ensure_lookup_table()
                rbm.faces.ensure_lookup_table()
    
                mx = Refractory.matrix_world
                imx_shell = Shell.matrix_world.inverted()
                
                rbm.transform(imx_shell * mx)
                bvh = BVHTree.FromBMesh(rbm)
                
                verts_error = bmesh_check_thick_object_verts_against(bm, self.thickness_min, bvh)
                
            for v in bm.verts:
                for f in v.link_faces:
                    for loop in f.loops:
                        if loop.vert in verts_error:
                            loop[vcol_layer] = red
                        else:
                            loop[vcol_layer] = white
        
        else:
            if self.check_against == 'SElF':
                faces_error_inds, bmfaces_error = bmesh_check_thick_object(bm, self.thickness_min)
                
            else:
                rbm = bmesh.new()
                rbm.from_mesh(Refractory.data)
                rbm.verts.ensure_lookup_table()
                rbm.edges.ensure_lookup_table()
                rbm.faces.ensure_lookup_table()
    
                mx = Refractory.matrix_world
                imx_shell = Shell.matrix_world.inverted()
                
                rbm.transform(imx_shell * mx)
                bvh = BVHTree.FromBMesh(rbm)
                
                faces_error_inds, bmfaces_error = bmesh_check_thick_object_against(bm, self.thickness_min, bvh)
                
            for f in bm.faces:
                if f in bmfaces_error:
                    for loop in f.loops:
                        loop[vcol_layer] = red
                else:
                    for loop in f.loops:
                        loop[vcol_layer] = white
                
        bm.to_mesh(Shell.data)
        
        #if self.correct and self.check_mode == 'VERTS':
        #    self.sculpt_fix_thin(context, Shell, list(verts_error))
        bm.free()               
        #########################################
        context.space_data.show_textured_solid = True
        #tracking.trackUsage("D3DUAL:ValidateThickness" + self.jaw_mode,(str(self.thickness_min), str(completion_time)[0:4]))
        
        #splint.ops_string += "ValidateThickness" + self.jaw_mode + ":"
        
        
            
        return {'FINISHED'}

class D3SPLINT_OT_splint_check_selected_thickness(bpy.types.Operator):
    """Check for thin parts"""
    bl_idname = "d3splint.splint_check_thickness_selected"
    bl_label = "Check Splint Thickness"
    bl_options = {'REGISTER', 'UNDO'}
    
    #jaw_mode = EnumProperty(default = 'MAX', items = (('MAX','MAX','MAX'),('MAND','MAND','MAND')))
    check_mode = EnumProperty(default = 'FACES', items = (('FACES','FACES','FACES'),('VERTS','VERTS','VERTS')))
    thickness_min = FloatProperty(default = 0.5, min = .01, max = 3.0)
        
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def invoke(self,context,event):
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        start_time = time.time()
        #n = context.scene.odc_splint_index
        #splint = context.scene.odc_splints[n]
        #prefs = get_settings()
        #if not prefs.non_clinical_use:
        #    self.report({'ERROR'}, 'You must certify non-clinical use in your addon preferences or in the panel')
        #    return {'CANCELLED'}
        
        
        #TODO repeat for every model?...seems DUMB
        #if self.jaw_mode == 'MAX':
        #    splint_shell = 'Max Splint Shell'
        #    r_model = 'Max Refractory Model'
        #    f_model = 'Max Final Splint'
            
        #else:
        #    splint_shell = 'Mand Splint Shell'
        #    r_model = 'Mand Refractory Model'
        #    f_model = 'Mand Final Splint'
         
        #Shell = bpy.data.objects.get(splint_shell)
        ob = context.object
        
        #TODO make this represent the sleep appliances
        if ob == None:
            self.report({'ERROR'}, 'Need to select and object')
            return {'CANCELLED'}
            
        setup_mat_and_vcolor(ob, "Design Verification")
        
        # Triangulate
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
    
        #get the vertex color layer
        vcol_layer = bm.loops.layers.color["Design Verification"]
            
            
        #########################################
        #for now, use the existing 3d print tools
        #TODO rewrite with accelerated BVH strcuture to avoid temporary object!
        #TODO only randomly triangulate faces with area > (.3 x .3)
        
        white = Color((1.0,1.0,1.0))
        red = Color((1.0, .2, .2))
        
        if self.check_mode == 'VERTS':
        
            verts_error = bmesh_check_thick_object_verts(bm, self.thickness_min)
      
            for v in bm.verts:
                for f in v.link_faces:
                    for loop in f.loops:
                        if loop.vert in verts_error:
                            loop[vcol_layer] = red
                        else:
                            loop[vcol_layer] = white
        
        else:
            faces_error_inds, bmfaces_error = bmesh_check_thick_object(bm, self.thickness_min)
            for f in bm.faces:
                if f in bmfaces_error:
                    for loop in f.loops:
                        loop[vcol_layer] = red
                else:
                    for loop in f.loops:
                        loop[vcol_layer] = white
                
        bm.to_mesh(ob.data) 
        bm.free()               
        #########################################
        completion_time = time.time() - start_time
        context.space_data.show_textured_solid = True
        #tracking.trackUsage("D3DUAL:ValidateThickness",(str(self.thickness_min), str(completion_time)[0:4]))
        
        #tmodel = bpy.data.objects.get(t_mo)
        #make sure user can verify no intersections
        #if tmodel:
        #    tmodel.hide = False
    
        
        return {'FINISHED'}
        
def register():
    # the order here determines the UI order
    bpy.utils.register_class(D3SPLINT_OT_splint_finish_check_thickness)
def unregister():
    # the order here determines the UI order
    bpy.utils.register_class(D3SPLINT_OT_splint_finish_check_thickness)