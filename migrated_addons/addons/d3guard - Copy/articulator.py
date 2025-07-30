'''
Created on Jul 5, 2017

@author: Patrick
'''
import math
from os.path import join, dirname, abspath, exists
import sys
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from bpy.props import FloatProperty, IntProperty, BoolProperty, EnumProperty

import tracking
import splint_cache
from common_utilities import get_settings

import articulator_math
from articulator_math import set_mandibular_bow_position

#from articulator_drivers import full_envelope_with_relax, three_way_envelope_l, three_way_envelope_r, saw_tooth, thirty_steps

def create_guide_table(incisal_guidance, canine_guidance, guidance_delay_ant, guidance_delay_lat): 
    
    ant_guidance = Vector((0, -math.cos(incisal_guidance*math.pi/180), -math.sin(incisal_guidance*math.pi/180)))  #LPS, -Y is forward
    rcan_guidance = Vector((-math.cos(canine_guidance*math.pi/180), 0,  -math.sin(canine_guidance*math.pi/180))) #-X is to the Right
    lcan_guidance = Vector((math.cos(canine_guidance*math.pi/180), 0, -math.sin(canine_guidance*math.pi/180)))   #+X is to the Left
    
    ant_guidance.normalize()
    rcan_guidance.normalize()
    lcan_guidance.normalize()
    
    
   
    bme = bmesh.new()
    v0 = Vector((.5 * guidance_delay_lat,0, 0))  #Left
    v1 = v0 + Vector((0, -guidance_delay_ant, 0))  #Forward by ant guideance delay
    v2 = v1 + 15 * ant_guidance  #Forward and down from three
    
    v3 = Vector((-.5 * guidance_delay_lat,0, 0)) #Right
    v4 = v3 + Vector((0, -guidance_delay_ant, 0)) #Forward by guidance delay
    v5 = v4 + 15 * ant_guidance  #Forward and down from there
    
    v6 = v0 + 15 * lcan_guidance
    v7 = v1 + 15 * lcan_guidance
    v8 = v2 + 15 * lcan_guidance
    
    v9 = v3 + 15 * rcan_guidance
    v10 = v4 + 15 * rcan_guidance
    v11 = v5 + 15 * rcan_guidance
    
    
    vecs = [v0,v1,v2,v3, v4,v5,v6,v7,v8,v9,v10,v11]
    
    vs = [bme.verts.new(v) for v in vecs]
    
    bme.faces.new((vs[0],vs[3],vs[4],vs[1]))
    bme.faces.new((vs[1], vs[4],vs[5],vs[2]))
    
    bme.faces.new((vs[3], vs[9],vs[10],vs[4]))
    bme.faces.new((vs[6], vs[0],vs[1],vs[7]))
    
    bme.faces.new((vs[4], vs[10],vs[11],vs[5]))
    bme.faces.new((vs[7], vs[1],vs[2],vs[8]))
    
    if 'Guide Table' in bpy.data.objects:
        guide_object = bpy.data.objects.get('Guide Table')
        guide_data = guide_object.data
        
    else:
        print('making new guide table')
        guide_data = bpy.data.meshes.new('Guide Table')
        guide_object = bpy.data.objects.new('Guide Table', guide_data)
        bpy.context.scene.objects.link(guide_object)
        #guide_object.parent = art_arm
        #guide_object.location = Vector((0, -99.9, -60))  #Updated to LPS
    
    bme.to_mesh(guide_data)
    
    print('UPDATING THE BVH ARTICULATOR.PY')
    bvh = BVHTree.FromBMesh(bme)
    articulator_math.incisal_bvh = bvh
    print(bvh)
    print(articulator_math.incisal_bvh)
    bme.free()
    guide_data.update()
    
    return guide_object

def adjust_bow_size(b_ele, condyle_width):
    
    
    if 'Left Bow' not in b_ele.vertex_groups: return
    if 'Right Bow' not in b_ele.vertex_groups: return
    if 'Left Condyle' not in b_ele.vertex_groups: return
    if 'Right Condyle' not in b_ele.vertex_groups: return
    
    
    vg0 = b_ele.vertex_groups.get('Left Bow')
    vg1 = b_ele.vertex_groups.get('Right Bow')
    vg2 = b_ele.vertex_groups.get('Left Condyle')
    vg3 = b_ele.vertex_groups.get('Right Condyle')
    
    
    vs0 = [v for v in b_ele.data.vertices if vg0.index in [ vg.group for vg in v.groups]]
    vs1 = [v for v in b_ele.data.vertices if vg1.index in [ vg.group for vg in v.groups]]
    vs2 = [v for v in b_ele.data.vertices if vg2.index in [ vg.group for vg in v.groups]]
    vs3 = [v for v in b_ele.data.vertices if vg3.index in [ vg.group for vg in v.groups]]

    #delta_right = Vector((0,-condyle_width/2, 0)) - vs3[0].co
    #delta_left = Vector((0, condyle_width/2, 0)) - vs2[0].co
    delta_right = Vector((-condyle_width/2, 0, 0)) - vs3[0].co
    delta_left = Vector((condyle_width/2, 0, 0)) - vs2[0].co
    
    print(delta_right)
    print(delta_left)
    
    for v in vs0 + vs2:
        v.co += delta_left
    for v in vs1 + vs3:
        v.co += delta_right
                
    return

def link_articulator_decoration(context):
    assets_path = join(dirname(abspath(__file__)), "data_assets")
    fullBlendPath = join(assets_path, 'articulator.blend')
    print(assets_path)
    print(fullBlendPath)
    
    ob_names = ['Top Element', 'L Condyle Path Block', 'L Condyle', 'R Condyle Path Block', 'R Condyle', 'Bottom Element']  
    
    for ob in ob_names:
        if ob not in context.scene.objects:
            obpath = fullBlendPath + '\\Object\\'
            filename = 'Top Element'
            bpy.ops.wm.append(filepath = fullBlendPath,
                      directory = obpath,
                      filename = ob)
    
    art_arm = bpy.data.objects.get('Articulator') 
    b_ele = bpy.data.objects.get('Bottom Element')
    t_ele = bpy.data.objects.get('Top Element')
    

    mx = b_ele.matrix_world
    b_ele.parent = art_arm
    b_ele.matrix_world = mx
    
    mx = t_ele.matrix_world
    t_ele.parent = art_arm
    t_ele.matrix_world = mx
    
    lcp = bpy.data.objects.get('LCP')
    rcp = bpy.data.objects.get('RCP')
    
    l_cond = bpy.data.objects.get('L Condyle')
    r_cond = bpy.data.objects.get('R Condyle')
    l_block = bpy.data.objects.get('L Condyle Path Block')
    r_block = bpy.data.objects.get('R Condyle Path Block')
    
    width = art_arm["intra_condyle_width"]
    bennet_angle = art_arm["bennet_angle"]
    condyle_angle = art_arm["condyle_angle"]
    
    
    adjust_bow_size(b_ele, width)
    
    #mx_t_l = Matrix.Translation(Vector((0, width/2, 0)))
    #mx_t_r = Matrix.Translation(Vector((0, -width/2, 0)))
    mx_t_l = Matrix.Translation(Vector((width/2, 0, 0)))
    mx_t_r = Matrix.Translation(Vector((-width/2, 0, 0)))
    
    
    theta_bennet = bennet_angle * math.pi/180
    theta_condyle = condyle_angle * math.pi/180
    
    mx_r_l = Matrix.Rotation(-theta_bennet, 4, Vector((0,0,1)))* Matrix.Rotation(theta_condyle, 4, Vector((1,0,0))) #Updated to LPS
    mx_r_r = Matrix.Rotation(theta_bennet, 4, Vector((0,0,1))) * Matrix.Rotation(theta_condyle, 4, Vector((1,0,0))) ##Updated to LPS
                             
    l_cond.parent = b_ele
    r_cond.parent = b_ele
    
    l_cond.matrix_world = mx_t_l
    r_cond.matrix_world = mx_t_r
    
    l_block.parent = art_arm
    r_block.parent = art_arm
    
    l_block.matrix_world = mx_t_l * mx_r_l
    r_block.matrix_world = mx_t_r * mx_r_r
    
    #cons = b_ele.constraints.new(type = 'CHILD_OF')
    #cons.target = art_arm
    #cons.subtarget = 'Mandibular Bow'
        
    #mx = art_arm.matrix_world * art_arm.pose.bones['Mandibular Bow'].matrix
    #cons.inverse_matrix = mx.inverted()
    
    
    #with bpy.data.libraries.load(fullBlendPath, False, False) as (data_from, data_to):
    #    ind = data_from.objects.index('Top Element')
    #    data_to.objects = [data_from.objects[ind]]
    
    #with bpy.data.libraries.load(fullBlendPath, False, False) as (data_from, data_to):
    #    ind = data_from.objects.index('Top Element')
    #    data_to.objects = [data_from.objects[ind]]
            
def full_envelope_math(articulator, anim_data, resolution):
    
    lx, ly, lz, rx, ry, rz, right_lat, left_lat = anim_data
    
    #print(resolution)
    
    #early = int(.5 * resolution)  #smaller steps in first 1/4 of range of motion
    
    #print(early)
    
    #n_points = 5*early + (resolution - early)
    n_points = resolution
    #print(n_points)
    
    for i in range(0, n_points):
        
        #if i < 5 * early:
        #    left_lateral = i/(5*early)
        #else:
        #    left_lateral = i/n_points
        
        left_lateral = math.pow((i/resolution), 3/2) # (i/resolution)  **2  
        for j in range(0, n_points):
            
            
            #if j < 5 * early:
            #    right_lateral = j/(5*early)
            #else:
            #    right_lateral = j/n_points
            
            #print(a, b)
            #left_lateral = a/resolution
            #right_lateral = b/resolution
            right_lateral = math.pow((j/resolution), 3/2)
            
            print(left_lateral, right_lateral)
            mx = set_mandibular_bow_position(articulator, right_lateral, left_lateral, 0)
    
            euler = mx.to_euler()
            loc = mx.to_translation()
            
            
            lx.append(loc[0])
            ly.append(loc[1])
            lz.append(loc[2])
            rx.append(euler[0])
            ry.append(euler[1])
            rz.append(euler[2])
            right_lat.append(right_lateral)
            left_lat.append(left_lateral)
            
def protrusive_math(articulator, anim_data, resolution):
    lx, ly, lz, rx, ry, rz, right_lat, left_lat = anim_data
    
    for i in range(0, resolution):    
        left_lateral = math.pow(i/resolution, 3/2)
        right_lateral = math.pow(i/resolution, 3/2)
        
        mx = set_mandibular_bow_position(articulator, right_lateral, left_lateral, 0)

        euler = mx.to_euler()
        loc = mx.to_translation()
        
        lx.append(loc[0])
        ly.append(loc[1])
        lz.append(loc[2])
        rx.append(euler[0])
        ry.append(euler[1])
        rz.append(euler[2])
        right_lat.append(right_lateral)
        left_lat.append(left_lateral)
            
def left_working_math(articulator, anim_data, resolution):
    lx, ly, lz, rx, ry, rz, right_lat, left_lat = anim_data
    
    for i in range(0, resolution):
        
        left_lateral = 0
        right_lateral = math.pow(i/resolution, 3/2)

        mx = set_mandibular_bow_position(articulator, right_lateral, left_lateral, 0)

        euler = mx.to_euler()
        loc = mx.to_translation()
        
        lx.append(loc[0])
        ly.append(loc[1])
        lz.append(loc[2])
        rx.append(euler[0])
        ry.append(euler[1])
        rz.append(euler[2])
        right_lat.append(right_lateral)
        left_lat.append(left_lateral)  
        
def right_working_math(articulator, anim_data, resolution):
    lx, ly, lz, rx, ry, rz, right_lat, left_lat = anim_data
    
    for i in range(0, resolution):
        
        left_lateral = math.pow(i/resolution, 2)
        right_lateral = 0

        mx = set_mandibular_bow_position(articulator, right_lateral, left_lateral, 0)

        euler = mx.to_euler()
        loc = mx.to_translation()
        
        lx.append(loc[0])
        ly.append(loc[1])
        lz.append(loc[2])
        rx.append(euler[0])
        ry.append(euler[1])
        rz.append(euler[2])
        right_lat.append(right_lateral)
        left_lat.append(left_lateral)   
               
def three_way_envelope_math(articulator, anim_data, resolution):
    lx, ly, lz, rx, ry, rz, right_lat, left_lat = anim_data
    
    for i in range(0, resolution):
        j = 0
        
        left_lateral = math.pow(i/resolution, 2)
        right_lateral = math.pow(j/resolution, 2)

        mx = set_mandibular_bow_position(articulator, right_lateral, left_lateral, 0)

        euler = mx.to_euler()
        loc = mx.to_translation()
        
        lx.append(loc[0])
        ly.append(loc[1])
        lz.append(loc[2])
        rx.append(euler[0])
        ry.append(euler[1])
        rz.append(euler[2])
        right_lat.append(right_lateral)
        left_lat.append(left_lateral)
            
    for j in range(0, resolution):
        i = 0
        
        left_lateral = math.pow(i/resolution, 2)
        right_lateral = math.pow(j/resolution, 2)

        mx = set_mandibular_bow_position(articulator, right_lateral, left_lateral, 0)

        euler = mx.to_euler()
        loc = mx.to_translation()
        
        lx.append(loc[0])
        ly.append(loc[1])
        lz.append(loc[2])
        rx.append(euler[0])
        ry.append(euler[1])
        rz.append(euler[2])
        right_lat.append(right_lateral)
        left_lat.append(left_lateral)
        
    for j in range(0, resolution):
        i = j
        
        left_lateral = math.pow(i/resolution, 2)
        right_lateral = math.pow(j/resolution, 2)

        mx = set_mandibular_bow_position(articulator, right_lateral, left_lateral, 0)

        euler = mx.to_euler()
        loc = mx.to_translation()
        
        lx.append(loc[0])
        ly.append(loc[1])
        lz.append(loc[2])
        rx.append(euler[0])
        ry.append(euler[1])
        rz.append(euler[2])
        right_lat.append(right_lateral)
        left_lat.append(left_lateral)
        
class D3DUAL_OT_generate_articulator(bpy.types.Operator):
    """Create Arcon Style semi adjustable articulator from parameters \n or modify the existing articulator
    """
    bl_idname = "d3dual.generate_articulator"
    bl_label = "Create Arcon Articulator"
    bl_options = {'REGISTER', 'UNDO'}
    
    intra_condyle_width = IntProperty(name = "Intra-Condyle Width", default = 110, description = 'Width between condyles in mm')
    condyle_length = FloatProperty(name = "Condyle Length", min = 2.5, max = 10.0, default = 8.0, description = 'Length of Condyle Track')
    
    condyle_angle = IntProperty(name = "Condyle Angle", default = 20, description = 'Condyle inclination in the sagital plane')
    bennet_angle = FloatProperty(name = "Bennet Angle", default = 7.5, description = 'Bennet Angle: Condyle inclination in the axial plane')
    
    side_shift = FloatProperty(name = "Side Shift", default = 0.0, min = 0.0, max = 4.0, description = 'Side Shift: Total magnitude of precurrent side shift')
    side_shift_range = FloatProperty(name = "Side Shift Range", 
                                     default = 1.0, min  = .05, max = 4.0, 
                                     description = 'Side Shift Range: Distnace the precurrent side shift takes place over')
    
    incisal_guidance = FloatProperty(name = "Incisal Guidance", default = 10, description = 'Incisal Guidance Angle')
    canine_guidance = FloatProperty(name = "Canine Guidance", default = 10, description = 'Canine Lateral Guidance Angle')
    guidance_delay_ant = FloatProperty(name = "Anterior Guidance Delay", default = .1, description = 'Anterior movement before guidance starts')
    guidance_delay_lat = FloatProperty(name = "Canine Guidance Delay", default = .1, description = 'Lateral movement before canine guidance starts')
    
    auto_mount = BoolProperty(default = True, description = 'Use if Upper and Lower casts are already in mounted position')
    
    resolution = IntProperty(name = 'Resolution', default = 30, min = 10, max = 50, description = 'Number of steps along each condyle to animate')
    factor = FloatProperty(name = 'Range of Motion', default = 6, min = 1, max = 8.0, description = 'Distance down condylaer inclines to use in motion')
    
    invoked = BoolProperty(default = False, description = 'Internal call to help determine if operator called by code or by user')
    
    @classmethod
    def poll(cls, context):
        
        return True
    
    def invoke(self, context, event):
        
        if 'Articulator' in bpy.data.objects:
            art_arm = bpy.data.objects.get('Articulator')
            
            if art_arm.get('bennet_angle'):
                self.bennet_angle  =  art_arm.get('bennet_angle')
            if art_arm.get('intra_condyle_width'):
                self.intra_condyle_width = art_arm['intra_condyle_width'] 
            if art_arm.get('condyle_length'):    
                self.condyle_length = art_arm["condyle_length"]
            if art_arm.get('incisal_guidance'):
                self.incisal_guidance = art_arm['incisal_guidance']   
            if art_arm.get('canine_guidance'):
                self.canine_guidance = art_arm['canine_guidance'] 
            if art_arm.get('condyle_angle'):
                self.condyle_angle = art_arm['condyle_angle']  
            if art_arm.get('guidance_delay_ant'):
                self.guidance_delay_ant = art_arm['guidance_delay_ant']
            if art_arm.get('guidance_delay_lat'):
                self.guidance_delay_lat = art_arm['guidance_delay_lat']
            if art_arm.get('immediate_side_shift'):
                self.side_shift = art_arm['immediate_side_shift']
            if art_arm.get('side_shift_range'):
                self.side_shift_range = art_arm['side_shift_range']
            
        else:
            settings = get_settings()
        
            self.intra_condyle_width = settings.def_intra_condyle_width
            self.condyle_length = settings.def_condyle_length
            self.condyle_angle = settings.def_condyle_angle
            self.bennet_angle = settings.def_bennet_angle
        
            self.incisal_guidance = settings.def_incisal_guidance 
            self.canine_guidance = settings.def_canine_guidance
            self.guidance_delay_ant = settings.def_guidance_delay_ant
            self.guidance_delay_lat = settings.def_guidance_delay_lat
        
        self.invoked = True
        return context.window_manager.invoke_props_dialog(self)
    
    
    def execute(self, context):
        
        tracking.trackUsage("D3Tool:GenArticulator",str((self.intra_condyle_width,
                                                         self.condyle_length,
                                                         self.bennet_angle,
                                                         self.canine_guidance,
                                                         self.incisal_guidance)))
        
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        context.scene.frame_start = 0
        #context.scene.frame_end = 3 * self.resolution
        context.scene.frame_set(0)
        
        
        #add 2 bezier paths named right and left condyle, move them to the condyle width
        if 'Articulator' in bpy.data.objects:
            #start fresh
            art_arm = bpy.data.objects.get('Articulator')
            n = context.scene.odc_splint_index
            splint = context.scene.odc_splints[n]
            opposing = splint.get_mandible()
            Model = bpy.data.objects.get(opposing)
            if Model:
                for cons in Model.constraints:
                    if cons.type == 'CHILD_OF' and cons.target == art_arm:
                        Model.constraints.remove(cons)
            
        else:
            art_arm = bpy.data.objects.new('Articulator', None)
            context.scene.objects.link(art_arm)

        guide_table = create_guide_table(self.incisal_guidance, self.canine_guidance, self.guidance_delay_ant, self.guidance_delay_lat)
        guide_table.parent = art_arm
        guide_table.matrix_world = Matrix.Translation(Vector((0, -99.9, -5))) #Updated to LPS
        
        bpy.ops.d3splint.enable_articulator_visualizations()
        
        #save settings to object
        art_arm['bennet_angle'] = self.bennet_angle
        art_arm['intra_condyle_width'] = self.intra_condyle_width
        art_arm['condyle_length'] = self.condyle_length
        art_arm['incisal_guidance'] = self.incisal_guidance 
        art_arm['canine_guidance'] =  self.canine_guidance
        art_arm['condyle_angle'] =  self.condyle_angle
        art_arm['guidance_delay_ant'] = self.guidance_delay_ant
        art_arm['guidance_delay_lat'] = self.guidance_delay_ant
        
        art_arm['immediate_side_shift'] = self.side_shift
        art_arm['side_shift_range'] = self.side_shift_range
        
        art_arm['pin_position'] = 0.0
        art_arm['condyle_r'] = 0.0
        art_arm['condyle_l'] = 0.0
        art_arm['art_mode'] = '3WAY_ENVELOPE'
        art_arm['resolution'] = self.resolution
        
        splint.ops_string += 'GenArticulator:'
        
        link_articulator_decoration(context)
        
        maxilla = splint.get_maxilla()
        Maxilla = bpy.data.objects.get(maxilla)
        if Maxilla:
            for ob in context.scene.objects:
                ob.select = False
            Maxilla.hide = False
            context.scene.objects.active = Maxilla
            Maxilla.select = True
        #bpy.ops.view3d.viewnumpad(type = 'RIGHT')
        
        
        if not self.auto_mount:
            return {'FINISHED'}
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        splint.ops_string += 'Generate Articulator:'
        mandible = splint.get_mandible()
        Mandible = bpy.data.objects.get(mandible)
        
        bottom_element = bpy.data.objects.get('Bottom Element')
        
        #https://blender.stackexchange.com/questions/19602/child-of-constraint-set-inverse-with-python
        if Mandible:
            Mandible.hide = False    
            cons = Mandible.constraints.new(type = 'CHILD_OF')
            cons.target = bottom_element
            #cons.subtarget = 'Mandibular Bow'
            mx = bottom_element.matrix_world
            cons.inverse_matrix = mx.inverted()
        
        
        
        #write the opposing jaw BVH to cache for fast ray_casting
        #OppModel = bpy.data.objects.get(splint.opposing)
        #if OppModel != None:
            #bme = bmesh.new()
            #bme.from_mesh(OppModel.data)    
            #bvh = BVHTree.FromBMesh(bme)
            #splint_cache.write_mesh_cache(OppModel, bme, bvh)
            
            #Model = bpy.data.objects.get(splint.model)
            
            #if fast_check_clearance(Model, OppModel, splint.minimum_thickness_value + .2, bvh_to = bvh, percentage = .5):
                #self.report({'INFO'}, 'Low clearance was detected in a quick check. Recommend using the check clearance tool!')
            #    showErrorMessage('Low clearance was detected in a quick check. Recommend using the check clearance tool!')
        
        bpy.ops.d3dual.generate_articulator_keyframes(mode = 'PROTRUSIVE')     
        if self.invoked:
            splint.articulator_made = True

            
        return {'FINISHED'}        


class D3DUAL_OT_generate_articulator_keyframes(bpy.types.Operator):
    """Generate articulator keyframes"""
    bl_idname = "d3dual.generate_articulator_keyframes"
    bl_label = "Generate Articulator Keyframes"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    modes = ['PROTRUSIVE', 'RIGHT_EXCURSION', 'LEFT_EXCURSION', 'RELAX_RAMP', '3WAY_ENVELOPE','FULL_ENVELOPE']
    mode_items = []
    for m in modes:
        mode_items += [(m, m, m)]
        
    mode = EnumProperty(name = 'Articulator Mode', items = mode_items, default = 'PROTRUSIVE') 

    resolution = IntProperty(name = "Resolution", default = 40, description = 'Steps per condyle')
    
    #right_lateral = FloatProperty(name = "Right Lateral", default = 0.0, min = 0.0, max = 1.0, description = 'Percent down')
    #left_lateral = FloatProperty(name = "Left Lateral", default = 0.0, min = 0.0, max = 1.0, description = 'Percent down')
    #hinge_opening = FloatProperty(name = "Hinge Opening", default = 0.0, min = 0.0, max = 1.0, description = 'Percent opening')
    
    
    @classmethod
    def poll(cls, context):
        
        return 'Articulator' in bpy.data.objects
    
    def invoke(self, context, event):
        
        art_arm = bpy.data.objects.get('Articulator')
        if art_arm.get('art_mode'):
            self.mode = art_arm['art_mode']
    
        self.invoked = True
        return context.window_manager.invoke_props_dialog(self)
    
    
    def execute(self, context):
        
        if 'Tracker Mesh' not in bpy.data.objects:
            me = bpy.data.meshes.new('Tracker Mesh')
            ob = bpy.data.objects.new('Tracker Mesh', me)
            bpy.context.scene.objects.link(ob)
        
        else:
            tracker = bpy.data.objects.get('Tracker Mesh')
            me = tracker.data
            tracker.data = None
            
            new_me = bpy.data.meshes.new('Tracker Mesh')
            tracker.data = new_me
            
            bpy.data.meshes.remove(me)
            
    
            
        mand_bow = bpy.data.objects.get('Bottom Element')
        articulator = bpy.data.objects.get('Articulator')
        
        if mand_bow.animation_data != None:
            mand_bow.animation_data_clear()
        
        if articulator.animation_data != None:
            articulator.animation_data_clear()
            
            
        
        lx, ly, lz, rx, ry, rz, right_lat, left_lat = [], [], [], [], [], [], [], []
        anim_data = (lx, ly, lz, rx, ry, rz, right_lat, left_lat)
        
        if self.mode == 'FULL_ENVELOPE':
            articulator['art_mode'] = 'FULL_ENVELOPE'
            full_envelope_math(articulator, anim_data, min(self.resolution, 40))
        
        if self.mode == '3WAY_ENVELOPE':
            articulator['art_mode'] = '3WAY_ENVELOPE'
            three_way_envelope_math(articulator, anim_data, self.resolution)
            
        
        if self.mode == 'PROTRUSIVE':
            articulator['art_mode'] = 'PROTRUSIVE'
            protrusive_math(articulator, anim_data, self.resolution)
        
        
        if self.mode == 'RIGHT_EXCURSION':
            articulator['art_mode'] = 'RIGHT_EXCURSION'
            right_working_math(articulator, anim_data, self.resolution)
        
        
        if self.mode == 'LEFT_EXCURSION':
            articulator['art_mode'] = 'LEFT_EXCURSION'
            left_working_math(articulator, anim_data, self.resolution)
        
        
         
        n_frames = len(lx)   
        frames = [i for i in range(n_frames)]
        
        a_main = mand_bow.animation_data_create()
        action_main = bpy.data.actions.new("MainBodyAction")


        a_props = articulator.animation_data_create()
        action_props = bpy.data.actions.new('A Props')
        
        fc_lx = action_main.fcurves.new("location", 0, "LocX")
        fc_ly = action_main.fcurves.new("location", 1, "LocY")
        fc_lz = action_main.fcurves.new("location", 2, "LocZ")
        fc_rx = action_main.fcurves.new("rotation_euler", 0, "RotX")
        fc_ry = action_main.fcurves.new("rotation_euler", 1, "RotY")
        fc_rz = action_main.fcurves.new("rotation_euler", 2, "RotZ")
        
        
        
    
        #Main Body F-Curves
        fc_lx.keyframe_points.add(count=n_frames)
        fc_ly.keyframe_points.add(count=n_frames)
        fc_lz.keyframe_points.add(count=n_frames)
        fc_rx.keyframe_points.add(count=n_frames)
        fc_ry.keyframe_points.add(count=n_frames)
        fc_rz.keyframe_points.add(count=n_frames)
        
        #custom props f-cruves
        fc_rlat = action_props.fcurves.new('["condyle_r"]', 0)
        fc_llat = action_props.fcurves.new('["condyle_l"]', 0)
        
        
        
        
        #Set Main Body Fcurve Data
        fc_lx.keyframe_points.foreach_set("co", 
                                          [x for co in zip(frames, lx) for x in co])
        fc_ly.keyframe_points.foreach_set("co", 
                                          [x for co in zip(frames, ly) for x in co])
        fc_lz.keyframe_points.foreach_set("co", 
                                          [x for co in zip(frames, lz) for x in co])
        fc_rx.keyframe_points.foreach_set("co", 
                                          [x for co in zip(frames, rx) for x in co])
        fc_ry.keyframe_points.foreach_set("co", 
                                          [x for co in zip(frames, ry) for x in co])
        fc_rz.keyframe_points.foreach_set("co", 
                                          [x for co in zip(frames, rz) for x in co])
       
       
        #don't know how to use foreach_set for this
        for i, rc_val in enumerate(right_lat):
            #print((i, rc_val))
            fc_rlat.keyframe_points.insert(i, rc_val)
        
        for i, lc_val in enumerate(left_lat):
            #print((i, lc_val))
            fc_llat.keyframe_points.insert(i, lc_val)
            
            
        
        #fc_rlat.keyframe_points.foreach_set("real", 
        #                                    [x for co in zip(frames, right_lat) for x in co])
        #fc_llat.keyframe_points.foreach_set("real", 
        #                                    [x for co in zip(frames, left_lat) for x in co])
        
        
        
        #set the action to the animation data of each object
        a_main.action = action_main
        a_props.action = action_props
        
        
        context.scene.frame_start = 0
        context.scene.frame_end = n_frames
        context.scene.frame_set(0)
            
        return {'FINISHED'}
def update_articulator_params(self, context):
    if self.hold_update: return
    #remake the bow
    art_obj = bpy.data.objects.get('Articulator')
    l_cond = bpy.data.objects.get('L Condyle')
    r_cond = bpy.data.objects.get('R Condyle')
    l_block = bpy.data.objects.get('L Condyle Path Block')
    r_block = bpy.data.objects.get('R Condyle Path Block')
    
    
    art_obj["intra_condyle_width"] = self.intra_condyle_width
    
    
    b_ele = bpy.data.objects.get('Bottom Element')
    adjust_bow_size(b_ele, self.intra_condyle_width)
    
    
    art_obj['bennet_angle'] = self.bennet_angle
    art_obj['intra_condyle_width'] = self.intra_condyle_width
    art_obj['condyle_length'] = self.condyle_length
    art_obj['condyle_angle'] =  self.condyle_angle
    art_obj['immediate_side_shift'] = self.side_shift
    art_obj['side_shift_range'] = self.side_shift_range

    #mx_t_l = Matrix.Translation(Vector((0, width/2, 0)))
    #mx_t_r = Matrix.Translation(Vector((0, -width/2, 0)))
    mx_t_l = Matrix.Translation(Vector((self.intra_condyle_width/2, 0, 0)))
    mx_t_r = Matrix.Translation(Vector((-self.intra_condyle_width/2, 0, 0)))
    
    
    theta_bennet = self.bennet_angle * math.pi/180
    theta_condyle = self.condyle_angle * math.pi/180
    
    mx_r_l = Matrix.Rotation(-theta_bennet, 4, Vector((0,0,1)))* Matrix.Rotation(theta_condyle, 4, Vector((1,0,0))) #Updated to LPS
    mx_r_r = Matrix.Rotation(theta_bennet, 4, Vector((0,0,1))) * Matrix.Rotation(theta_condyle, 4, Vector((1,0,0))) ##Updated to LPS
                             
    
    l_cond.matrix_basis = mx_t_l
    r_cond.matrix_basis = mx_t_r
    
    l_block.matrix_world = mx_t_l * mx_r_l
    r_block.matrix_world = mx_t_r * mx_r_r
    
    #reconstruct the matrix and send it
    
    mx = set_mandibular_bow_position(art_obj, self.right_lateral, self.left_lateral, 0.0)
    b_ele.matrix_world = mx
    
def update_guidance_params(self, context):
    if self.hold_update: return
    art_obj = bpy.data.objects.get('Articulator')
    b_ele = bpy.data.objects.get('Bottom Element')
    
   
    art_obj['incisal_guidance'] = self.incisal_guidance 
    art_obj['canine_guidance'] =  self.canine_guidance
    art_obj['guidance_delay_ant'] = self.guidance_delay_ant
    art_obj['guidance_delay_lat'] = self.guidance_delay_ant
    art_obj['immediate_side_shift'] = self.side_shift
    art_obj['side_shift_range'] = self.side_shift_range

    
    #recalc the guide table
    guide = create_guide_table(self.incisal_guidance, self.canine_guidance, self.guidance_delay_ant, self.guidance_delay_lat)
    guide.update_tag()
    context.scene.update()
    
    #reconstruct the matrix
    mx = set_mandibular_bow_position(art_obj, self.right_lateral, self.left_lateral, 0.0)
    b_ele.matrix_world = mx
    
def update_condyle_drive_parameters(self, context):
    #reconstruct the matrix
    art_obj = bpy.data.objects.get('Articulator')
    b_ele = bpy.data.objects.get('Bottom Element')
    
    art_obj['condyle_r'] = self.right_lateral
    art_obj['condyle_l'] = self.left_lateral
    
    if self.hold_update: return
    
    mx = set_mandibular_bow_position(art_obj, self.right_lateral, self.left_lateral, 0.0)
    b_ele.matrix_world = mx
    
    hold = self.hold_update
    
    self.hold_update = True
    self.protrusion = min(self.right_lateral, self.left_lateral)
    self.hold_update = hold

def update_protrusion_value(self, context):
    
    art_obj = bpy.data.objects.get('Articulator')
    if self.hold_update: return
        
    self.hold_update = True
    
    self.right_lateral = self.protrusion
    self.left_lateral = self.protrusion
    art_obj['condyle_r'] = self.right_lateral
    art_obj['condyle_l'] = self.left_lateral
        
    b_ele = bpy.data.objects.get('Bottom Element')
    mx = set_mandibular_bow_position(art_obj, self.right_lateral, self.left_lateral, 0.0)
    b_ele.matrix_world = mx
    
    self.hold_update = False


class D3DUAL_OT_live_articulator_parameters(bpy.types.Operator):
    """Change the Parameters of the Articulator"""
    bl_idname = "d3dual.live_articulator_parameters"
    bl_label = "Live Articulator Parameters"
    bl_options = {'REGISTER', 'UNDO'}
    

    intra_condyle_width = IntProperty(name = "Condyle Width", default = 110, 
                                      min = 60, max = 200,
                                      description = 'Width between condyles in mm',
                                      update = update_articulator_params)
    
    condyle_length = FloatProperty(name = "Condyle Length", default = 8.0,
                                   min = 2.5, max = 10.0,
                                   description = 'Length of Condyle Track',
                                   update = update_articulator_params)
    
    condyle_angle = IntProperty(name = "Condyle Angle", default = 20, step = 1,
                                min = 0, max = 65,
                                update = update_articulator_params,
                                description = 'Condyle inclination in the sagital plane')
    
    bennet_angle = FloatProperty(name = "Bennet Angle", default = 7.5, step = 10,
                                 min = 0.0, max = 15.0,
                                 update = update_articulator_params,
                                 description = 'Bennet Angle: Condyle inclination in the axial plane')
    
    side_shift = FloatProperty(name = "Side Shift", default = 0.0, min = 0.0, max = 4.0, step = 1,
                               update = update_articulator_params,
                               description = 'Side Shift: Total magnitude of precurrent side shift')
    
    side_shift_range = FloatProperty(name = "Side Shift Range", 
                                     default = 1.0, min  = .05, max = 4.0, step = 1,
                                     update = update_articulator_params,  
                                     description = 'Side Shift Range: Distance the precurrent side shift takes place over')
    
    
    incisal_guidance = FloatProperty(name = "Incisal Guidance", min = 0.0, max = 75.0, default = 10.0, step = 25,
                                     update = update_guidance_params,
                                     description = 'Incisal Guidance Angle')
    canine_guidance = FloatProperty(name = "Canine Guidance", min = 0.0, max = 75.0, default = 10.0, step = 25, 
                                    update = update_guidance_params,
                                    description = 'Canine Lateral Guidance Angle')
    guidance_delay_ant = FloatProperty(name = "Anterior Guidance Delay", default = .1, step = 1, 
                                       update = update_guidance_params,
                                       description = 'Anterior movement before guidance starts')
    
    guidance_delay_lat = FloatProperty(name = "Canine Guidance Delay", default = .1, step = 1, 
                                       min = .00001, max = 1.0,
                                       update = update_guidance_params,
                                       description = 'Lateral movement before canine guidance starts')
    
    protrusion =  FloatProperty(name = "Protrusion", default = 0.0, min = 0.0, max = 1.0, step = .1, 
                                update = update_protrusion_value,
                                description = 'Protrusion down the Condyles')
    
    right_lateral = FloatProperty(name = "Right Condyle Position", default = 0.0,  min = 0.0, max = 1.0,  step = .1, 
                                  update = update_condyle_drive_parameters,
                                  description = 'Right Condyle displacement')
    left_lateral = FloatProperty(name = "Left  Condyle Position", default = 0.0,  min = 0.0, max = 1.0, step = .1, 
                                 update = update_condyle_drive_parameters,
                                 description = 'Left Condyle Displacement')
    pin_position = FloatProperty(name = "Pin Position", default = 0.0,  min = -6.0, max = 6.0, step = .1,
                                 update = update_condyle_drive_parameters,
                                 description = 'Pin Adjustment')
    
    hold_update = BoolProperty(name = "Hold Update", default = False)
    detail1 = BoolProperty(name = "Details 1", default = False)
    detail2 = BoolProperty(name = "Details 2", default = False)
    @classmethod
    def poll(cls, context):
        if 'Articulator' not in bpy.data.objects:
            return False
        
        return True
    
    
    def check(self, context):
        return True
    def draw(self, context):   
        
        layout = self.layout
        
        row = layout.row()
        row.label('Drive Properties')
        
        row = layout.row()
        row.prop(self, "protrusion", slider = True)
        
        row = layout.row()
        row.prop(self, "left_lateral", slider = True)
        row.prop(self, "right_lateral", slider = True)
        
        
        row = layout.row()
        row.label('Condyle Properties')
        
        row = layout.row()
        row.prop(self, "intra_condyle_width", slider = True)
        
        row = layout.row()
        row.prop(self, "condyle_angle", slider = True)
        row.prop(self, "bennet_angle", slider = True)
        
        row = layout.row()
        row.prop(self, "condyle_length", slider = True)
        
        
        row = layout.row()
        row.prop(self, "detail1")
        if self.detail1:
            row = layout.row()
            row.prop(self, "side_shift", slider = True)
            row.prop(self, "side_shift_range", slider = True)
        
        row = layout.row()
        row.label('Guidance Properties')
        
        row = layout.row()
        row.prop(self, "canine_guidance", slider = True)
        
        row = layout.row()
        row.prop(self, "incisal_guidance", slider = True)
        
        
        
        
    def invoke(self, context, event):
        bpy.ops.ed.undo_push()
        self.start_frame = context.scene.frame_current  #maybe put it back when done?
        #ONLY ALLOW THIS STUFF IN 0 POSITION for now
        art_arm = bpy.data.objects.get('Articulator')

        #if keyframe data give warning
        
        do_hold = self.hold_update
        
        self.hold_update = True  #don't unnecessarily update these things while loading them!
        self.bennet_angle  =  art_arm.get('bennet_angle')   
        self.intra_condyle_width = art_arm['intra_condyle_width']        
        self.condyle_length = art_arm["condyle_length"]
        self.incisal_guidance = art_arm['incisal_guidance']   
        self.canine_guidance = art_arm['canine_guidance']    
        self.condyle_angle = art_arm['condyle_angle']  
        self.guidance_delay_ant = art_arm['guidance_delay_ant']
        self.guidance_delay_lat = art_arm['guidance_delay_lat']
        self.side_shift = art_arm['immediate_side_shift']
        self.side_shift_range = art_arm['side_shift_range']
        
        print('\n\n EXISTING PARAMETERS \n\n')
        print(art_arm['condyle_r'], art_arm['condyle_l'])
        self.hold_update = False  #update to the positions asked for
        
        if "A Props" in bpy.data.actions:
            a_actions = bpy.data.actions["A Props"]
            fcr = a_actions.fcurves[0]
            fcl = a_actions.fcurves[1]
            
            self.right_lateral = fcr.evaluate(self.start_frame)
            self.left_lateral = fcl.evaluate(self.start_frame)
            
            art_arm['condyle_r']
            art_arm['condyle_l']
        self.pin_position = art_arm["pin_position"]
        
        context.scene.frame_set(0)
        update_condyle_drive_parameters(self, context)
        self.hold_update = do_hold
        
        self.old_selection = [ob for ob in bpy.data.objects if ob.select]
        for ob in bpy.data.objects:
            ob.select = False
        
        return context.window_manager.invoke_props_dialog(self)
      
    def execute(self, context):
        
        
        art_obj = bpy.data.objects.get('Articulator')

        art_obj['condyle_r'] = self.right_lateral
        art_obj['condyle_l'] = self.left_lateral
        
        art_obj["intra_condyle_width"] = self.intra_condyle_width
        art_obj['incisal_guidance'] = self.incisal_guidance 
        art_obj['canine_guidance'] =  self.canine_guidance
        art_obj['guidance_delay_ant'] = self.guidance_delay_ant
        art_obj['guidance_delay_lat'] = self.guidance_delay_ant
        art_obj['immediate_side_shift'] = self.side_shift
        art_obj['side_shift_range'] = self.side_shift_range
        art_obj['bennet_angle'] = self.bennet_angle
        art_obj['intra_condyle_width'] = self.intra_condyle_width
        art_obj['condyle_length'] = self.condyle_length
        art_obj['condyle_angle'] =  self.condyle_angle
    
        
        bpy.ops.d3dual.generate_articulator_keyframes(mode = art_obj['art_mode'])
        bpy.ops.ed.undo_push()
        
        for ob in self.old_selection:
            ob.select = True
        
        return {'FINISHED'}
    
    def cancel(self, context):
        art_obj = bpy.data.objects.get('Articulator')
        art_obj['condyle_r'] = self.right_lateral
        art_obj['condyle_l'] = self.left_lateral
        art_obj["intra_condyle_width"] = self.intra_condyle_width
        art_obj['incisal_guidance'] = self.incisal_guidance 
        art_obj['canine_guidance'] =  self.canine_guidance
        art_obj['guidance_delay_ant'] = self.guidance_delay_ant
        art_obj['guidance_delay_lat'] = self.guidance_delay_ant
        art_obj['immediate_side_shift'] = self.side_shift
        art_obj['side_shift_range'] = self.side_shift_range
        art_obj['bennet_angle'] = self.bennet_angle
        art_obj['intra_condyle_width'] = self.intra_condyle_width
        art_obj['condyle_length'] = self.condyle_length
        art_obj['condyle_angle'] =  self.condyle_angle
        
        context.scene.frame_set(context.scene.frame_current)
        bpy.ops.ed.undo_push()
        bpy.ops.ed.undo_push()  #do a double push becuase after cancel...the operator does an undo on it's own
   

class D3DUAL_OT_splint_open_pin_on_articulator(bpy.types.Operator):
    """Open Pin on Articulator.  Pin increments are assumed 1mm at 85mm from condyles"""
    bl_idname = "d3dual.open_pin_on_articulator"
    bl_label = "Change Articulator Pin"
    bl_options = {'REGISTER', 'UNDO'}
    
    amount = FloatProperty(name = 'Pin Setting', default = 0.5, step = 10, min = -3.0, max = 6.0)
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def invoke(self,context,event):
        #tracking.trackUsage("D3DUAL:ChangePinSetting",None)
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        if context.scene.frame_current != 0:
            self.report({'WARNING'}, "The articulator is not at the 0 position, resetting it to 0 before changing pin")
            context.scene.frame_current = 0
            context.scene.frame_set(0)
            context.scene.frame_set(0)
            
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n] #TODO better knowledge for multiple splints
        if not splint.landmarks_set:
            self.report({'ERROR'}, 'You must set landmarks to get an approximate mounting')
            return {'CANCELLED'}
        
        mandible = splint.get_mandible()
        maxilla = splint.get_maxilla()
        
        Model = bpy.data.objects.get(mandible)
        Master = bpy.data.objects.get(maxilla)
        if not Model:
            self.report({'ERROR'},"Please set opposing model")
            return {'CANCELLED'}
        
        Articulator = bpy.data.objects.get('Articulator')
        if Articulator == None:
            self.report({'ERROR'},"Please use Add Arcon Articulator function")
            return {'CANCELLED'}
        
        if context.scene.frame_current != 0:
            context.scene.frame_set(0)
        
        re_mount = False
        
        constraints = []
        if len(Model.constraints):
            re_mount = True
            for cons in Model.constraints:
                cdata = {}
                cdata['name'] = cons.name
                cdata['type'] = cons.type
                cdata['target'] = cons.target
                cdata['subtarget'] = cons.subtarget
                cdata['inverse_matrix'] = cons.inverse_matrix
                constraints += [cdata]
                Model.constraints.remove(cons)
            
            
        
        radians = self.amount/75
        
        R = Matrix.Rotation(radians, 4, 'X')
        Model.matrix_world = R * Model.matrix_world
        
        if re_mount:
            
            for cdata in constraints:
                
                cons = Model.constraints.new(type = cdata['type'])
                cons.target = cdata['target']
                cons.subtarget = cdata['subtarget']
                cons.inverse_matrix = cdata['target'].matrix_world.inverted()
            
            
            #BottomElement = bpy.data.objects.get('Bottom Element')
            #cons = Model.constraints.new(type = 'CHILD_OF')
            #cons.target = Master
            #cons.inverse_matrix = Master.matrix_world.inverted()
             
            #cons = Model.constraints.new(type = 'CHILD_OF')
            #cons.target = BottomElement
            #cons.subtarget = 'Mandibular Bow'
        
            #mx = Articulator.matrix_world * Articulator.pose.bones['Mandibular Bow'].matrix
            #cons.inverse_matrix = mx.inverted()
    
        context.space_data.show_manipulator = True
        
        if self.amount > 0:
            sign = '+'
        else:
            sign = '-'
        splint.ops_string += "Change Pin {}{}:".format(sign, str(self.amount)[0:4])
        
        return {'FINISHED'}

class D3DUAL_OT_recover_mandible_mounting(bpy.types.Operator):
    """Recover original bite/mount relationship when models were first imported"""
    bl_idname = "d3dual.recover_mounting_relationship"
    bl_label = "Recover Mandibular Mounting"
    bl_options = {'REGISTER', 'UNDO'}
    
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
        
        if context.scene.frame_current != 0:
            self.report({'WARNING'}, "The articulator is not at the 0 position, resetting it to 0 before recovering moutn")
            context.scene.frame_current = 0
            context.scene.frame_set(0)
            context.scene.frame_set(0)
            
        if not splint.landmarks_set:
            self.report({'ERROR'}, 'You must set landmarks to have saved mounting')
            return {'CANCELLED'}
        
        
        if "Mandibular Orientation" not in bpy.data.objects:
            self.report({'ERROR'}, 'Unfortunately, the mounting backup is not present.  Did you delete it?')
            return {'CANCELLED'}
        
        mandible = splint.get_mandible()
        maxilla = splint.get_maxilla()
        
        Model = bpy.data.objects.get(mandible)
        Master = bpy.data.objects.get(maxilla)
        
        if not Model:
            self.report({'ERROR'},"It is not clear which model is the mandible.  Have you set model and set opposing?")
            return {'CANCELLED'}
        
        if not Master:
            self.report({'ERROR'},"It is not clear which model is the maxilla.  Have you set model and set opposing?")
            return {'CANCELLED'}
        
        
        Orientation = bpy.data.objects.get('Mandibular Orientation')
        mx_recover = Orientation.matrix_world
        
        if context.scene.frame_current != 0:
            context.scene.frame_current = -1
            context.scene.frame_current = 0
            context.scene.frame_set(0)
        
        re_mount = False
        
        constraints = []
        if len(Model.constraints):
            re_mount = True
            for cons in Model.constraints:
                cdata = {}
                cdata['type'] = cons.type
                cdata['target'] = cons.target
                cdata['subtarget'] = cons.subtarget
                constraints += [cdata]
                Model.constraints.remove(cons) 
    
        Model.matrix_world = mx_recover
        
        Articulator = bpy.data.objects.get('Articulator')
        Bow = bpy.data.objects.get('Bottom Element')
        if re_mount:
            
            cons = Model.constraints.new(type = 'CHILD_OF')
            cons.target = Master
            cons.inverse_matrix = Master.matrix_world.inverted()
             
            if Articulator:
                cons = Model.constraints.new(type = 'CHILD_OF')
                cons.target = Bow
                #cons.subtarget = 'Mandibular Bow'
        
                mx = Bow.matrix_world # * Articulator.pose.bones['Mandibular Bow'].matrix
                cons.inverse_matrix = mx.inverted()
    
        splint.ops_string += "Reset Pin:"
        return {'FINISHED'}

class D3SPLINT_OT_articulator_view(bpy.types.Operator):
    """View the scene in a way that makes sense for assessing articulation"""
    bl_idname = "d3splint.articulator_view"
    bl_label = "Articulator VIew"
    bl_options = {'REGISTER', 'UNDO'}
    
    

    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def execute(self, context):
        
        if not len(context.scene.odc_splints):
            return {'CANCELLED'}
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        Articulator = bpy.data.objects.get('Articulator')
        
        Max = bpy.data.objects.get(splint.get_maxilla())
        Mand = bpy.data.objects.get(splint.get_mandible())
        
        for ob in bpy.data.objects:
            ob.hide = True
        if Articulator:
            Articulator.hide = False
        if Max:
            Max.hide = False
        if Mand:
            Mand.hide = False
            
        return {'FINISHED'}
               
class D3DUAL_OT_splint_create_functional_surface(bpy.types.Operator):
    """Create functional surface using envelope of motion on articulator"""
    bl_idname = "d3dual.splint_animate_articulator"
    bl_label = "Animate on Articulator"
    bl_options = {'REGISTER', 'UNDO'}
    
    modes = ['PROTRUSIVE', 'RIGHT_EXCURSION', 'LEFT_EXCURSION', 'RELAX_RAMP', '3WAY_ENVELOPE','FULL_ENVELOPE']
    mode_items = []
    for m in modes:
        mode_items += [(m, m, m)]
        
    mode = EnumProperty(name = 'Articulator Mode', items = mode_items, default = 'FULL_ENVELOPE')
    resolution = IntProperty(name = 'Resolution', description = "Number of steps along the condyle to create surface.  10-40 is reasonable.  Larger = Slower", default = 20)
    range_of_motion = FloatProperty(name = 'Range of Motion', min = 2, max = 8, description = 'Distance to allow translation down condyles', default = 0.8)
    use_relax = BoolProperty(name = 'Use Relax Ramp', default = False)
    relax_ramp_length = FloatProperty(name = 'Relax Ramp Length', min = 0.1, max = 2.0, description = 'Length of condylar path to animate, typically .2 to 1.0', default = 0.8)
    
    
    projection_modes = ['SHELL_SHELL', 'TEETH_TEETH', 'TEETH_SHELL', 'SHELL_TEETH']
    p_mode_items = []
    for m in projection_modes:
        p_mode_items += [(m, m, m)]
        
    projection_mode = EnumProperty(name = 'Projection Mode', items = p_mode_items, default = 'SHELL_SHELL')
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def invoke(self, context, event):
        
        settings = get_settings()
        
        self.resolution = settings.def_condylar_resolution
        self.range_of_motion = settings.def_range_of_motion
        
        return context.window_manager.invoke_props_dialog(self)
        
    def execute(self, context):
        splint = context.scene.odc_splints[0]
        
        
        
        Art = bpy.data.objects.get('Articulator')
        
        
        pmode = self.projection_mode
        
        top_mode = pmode.split('_')[0]
        bottom_mode = pmode.split('_')[1]
        
        
        if top_mode == 'TEETH':
            MaxModel = bpy.data.objects.get(splint.get_maxilla())
        else:
            MaxModel = bpy.data.objects.get(splint.max_shell)
        
        if bottom_mode == 'TEETH':
            MandModel = bpy.data.objects.get(splint.get_mandible())
        else:
            MandModel = bpy.data.objects.get(splint.mand_shell)
        
        
        if MaxModel == None or MandModel == None:
            self.report({'ERROR'}, 'Models not set correctly')
            return {'CANCELLED'}
        
        if Art == None:
            self.report({'ERROR'}, 'You need to Generate Articulator or set initial articulator values first')
            return {'CANCELLED'}
        
        splint.dynamic_surface = True
        if not splint_cache.is_max_object_valid(MaxModel):
            splint_cache.clear_max_mesh_cache()
            bme = bmesh.new()
            bme.from_mesh(MaxModel.data)    
            bme.faces.ensure_lookup_table()
            bme.verts.ensure_lookup_table()
            bvh = BVHTree.FromBMesh(bme)
            splint_cache.write_max_mesh_cache(MaxModel, bme, bvh)
        
        if not splint_cache.is_mand_object_valid(MandModel):
            splint_cache.clear_mand_mesh_cache()
            bme = bmesh.new()
            bme.from_mesh(MandModel.data)    
            bme.faces.ensure_lookup_table()
            bme.verts.ensure_lookup_table()
            
            bvh = BVHTree.FromBMesh(bme)
            splint_cache.write_mand_mesh_cache(MandModel, bme, bvh)
            
             
        bpy.ops.d3dual.articulator_mode_set(mode = self.mode, 
                                              resolution = self.resolution, 
                                              range_of_motion = self.range_of_motion, 
                                              use_relax = self.use_relax,
                                              relax_ramp_length = self.relax_ramp_length)
        
        #filter the occlusal surface verts
        MaxPlane = bpy.data.objects.get('Max Occlusal Surface')
        MandPlane = bpy.data.objects.get('Mand Occlusal Surface')
        
        
        MandShell = bpy.data.objects.get('Splint Shell_MAND')
        MaxShell = bpy.data.objects.get('Splint Shell_MAX')
        
        
        def cull_plane_by_shell(Plane, Shell, Z):   
        
            
            if len(Shell.modifiers):
                Shell.select = True
                Shell.hide = False
                context.scene.objects.active = Shell
                
                for mod in Shell.modifiers:
                    bpy.ops.object.modifier_apply(modifier = mod.name)
            
            bme = bmesh.new()
            bme.from_mesh(Plane.data)
            bme.verts.ensure_lookup_table()
            
            #reset occusal plane if animate articulator has happened already
            if "AnimateArticulator" in splint.ops_string:
                for v in bme.verts:
                    v.co[2] = 0
                
            mx_p = Plane.matrix_world
            imx_p = mx_p.inverted()
            
            mx_s = Shell.matrix_world
            imx_s = mx_s.inverted()
            
            keep_verts = set()

            for v in bme.verts:
                ray_orig = mx_p * v.co
                ray_target = mx_p * v.co + 5 * Z
                ok, loc, no, face_ind = Shell.ray_cast(imx_s * ray_orig, imx_s * ray_target - imx_s*ray_orig)
            
                if ok:
                    keep_verts.add(v)
        
            print('there are %i keep verts' % len(keep_verts))
            front = set()
            for v in keep_verts:
        
                immediate_neighbors = [ed.other_vert(v) for ed in v.link_edges if ed.other_vert(v) not in keep_verts]
            
                front.update(immediate_neighbors)
                front.difference_update(keep_verts)
            
            keep_verts.update(front)
        
            for i in range(0,10):
                new_neighbors = set()
                for v in front:
                    immediate_neighbors = [ed.other_vert(v) for ed in v.link_edges if ed.other_vert(v) not in front]
                    new_neighbors.update(immediate_neighbors)
                    
                keep_verts.update(front)
                front = new_neighbors
                
            delete_verts = [v for v in bme.verts if v not in keep_verts]
            bmesh.ops.delete(bme, geom = delete_verts, context = 1)
            bme.to_mesh(Plane.data)
        
        
        if MaxShell:
            print('Culling Max Plane')
            cull_plane_by_shell(MaxPlane, MandShell, Vector((0,0,1)))
            
        if MandShell:
            print('Culling Mand Plane')
            cull_plane_by_shell(MandPlane, MaxShell, Vector((0,0,-1)))
            
        for ob in bpy.data.objects:
            if ob.type == 'MESH':
                ob.hide = True
            elif ob.type == 'CURVE':
                ob.hide = True
                
        
        MaxPlane.hide = False
        MaxModel.hide = False
        MandModel.hide = False
        MandPlane.hide = False

        #tracking.trackUsage("D3DUAL:CreateSurface",None)
        context.scene.frame_current = -1
        context.scene.frame_current = 0
        splint.ops_string += 'AnimateArticulator:'
        print('adding the handler!')
        
        handlers = [hand.__name__ for hand in bpy.app.handlers.frame_change_pre]
        
        if occlusal_surface_frame_change.__name__ not in handlers:
            bpy.app.handlers.frame_change_pre.append(occlusal_surface_frame_change)
        
        else:
            print('handler already in there')
        
        context.space_data.show_backface_culling = False    
        bpy.ops.screen.animation_play()
        
        return {'FINISHED'}
    
class D3SPLINT_OT_splint_reset_functional_surface(bpy.types.Operator):
    """Flatten the Functional Surface and Re-Set it"""
    bl_idname = "d3splint.reset_functional_surface"
    bl_label = "Reset Functional Surface"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def execute(self, context):
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        #filter the occlusal surface verts
        Plane = bpy.data.objects.get('Dynamic Occlusal Surface')
        if Plane == None:
            self.report({'ERROR'}, 'Need to mark occlusal curve on opposing object to get reference plane')
            return {'CANCELLED'}
        
        bme_shell = bmesh.new()
        
        bme = bmesh.new()
        bme.from_mesh(Plane.data)
        bme.verts.ensure_lookup_table()
        
        #reset occusal plane if animate articulator has happened already
        
        for v in bme.verts:
            v.co[2] = 0
        
            
            
        bme.to_mesh(Plane.data)
        Plane.data.update()
        return {'FINISHED'}
    
class D3SPLINT_OT_splint_restart_functional_surface(bpy.types.Operator):
    """Turn the functional surface calculation on"""
    bl_idname = "d3splint.start_surface_calculation"
    bl_label = "Start Surface Calculation"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def execute(self, context):
        #tracking.trackUsage("D3DUAL:RestartFunctionalSurface",None)
        print('removing the handler')
        
        
        handlers = [hand.__name__ for hand in bpy.app.handlers.frame_change_pre]
        
        if occlusal_surface_frame_change.__name__ not in handlers:
        
            bpy.app.handlers.frame_change_pre.append(occlusal_surface_frame_change)
        
        else:
            print('alrady added')
            
        return {'FINISHED'}
    
class D3SPLINT_OT_splint_stop_functional_surface(bpy.types.Operator):
    """Stop functional surface calculation to improve responsiveness"""
    bl_idname = "d3splint.stop_surface_calculation"
    bl_label = "Stop Surface Calculation"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    @classmethod
    def poll(cls, context):
        #if context.mode == "OBJECT" and context.object != None and context.object.type == 'CURVE':
        #    return True
        #else:
        #    return False
        return True
    
    def execute(self, context):
        #tracking.trackUsage("D3DUAL:StopFunctionalSurface",None)
        print('removing the handler')
        
        
        handlers = [hand.__name__ for hand in bpy.app.handlers.frame_change_pre]
        
        if occlusal_surface_frame_change.__name__ in handlers:
        
            bpy.app.handlers.frame_change_pre.remove(occlusal_surface_frame_change)
        
        else:
            print('alrady removed')
            
        return {'FINISHED'}

class D3DUAL_OT_capture_articulated_position(bpy.types.Operator):
    """Set the current postion as the new starting position"""
    bl_idname = "d3dual.capture_articulated_position"
    bl_label = "Capture Articulated Position"
    bl_options = {'REGISTER', 'UNDO'}
    
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
        
        
            
        if not splint.landmarks_set:
            self.report({'ERROR'}, 'You must set landmarks to have saved mounting')
            return {'CANCELLED'}
        
        
        mandible = splint.get_mandible()
        maxilla = splint.get_maxilla()
        
        Model = bpy.data.objects.get(mandible)
        Master = bpy.data.objects.get(maxilla)
        
        if not Model:
            self.report({'ERROR'},"It is not clear which model is the mandible.  Have you set maxilla and mandibular models")
            return {'CANCELLED'}
        
        if not Master:
            self.report({'ERROR'},"It is not clear which model is the maxilla.  Have you set model and set opposing?")
            return {'CANCELLED'}
        
        
        initial_orientation = bpy.data.objects.get('Mandibular Orientation')
        if initial_orientation == None:
            self.report({'ERROR'},"Initial position was not saved")
            return {'CANCELLED'}
        
        
        saved_orientation = bpy.data.objects.get('Articulated Position')
        if not saved_orientation:
            saved_orientation = bpy.data.objects.new('Articulated Position', None)
            context.scene.objects.link(saved_orientation)
            saved_orientation.parent = Master
        
        mx_i = initial_orientation.matrix_world   
        mx_w = Model.matrix_world.copy()
        
        
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
        
        saved_orientation.matrix_world = mx_w
        
        
        
        if context.scene.frame_current != 0:
            context.scene.frame_current = 0
            context.scene.frame_set(0)
            context.scene.frame_set(0)
            
        re_mount = True
        
        constraints = []
        if len(Model.constraints):
            re_mount = True
            for cons in Model.constraints:
                cdata = {}
                cdata['type'] = cons.type
                cdata['target'] = cons.target
                cdata['subtarget'] = cons.subtarget
                constraints += [cdata]
                Model.constraints.remove(cons) 
            
            
        Model.matrix_world = mx_w
        
        Articulator = bpy.data.objects.get('Articulator')
        Bow = bpy.data.objects.get('Bottom Element')
        if re_mount:
            
            cons = Model.constraints.new(type = 'CHILD_OF')
            cons.target = Master
            cons.inverse_matrix = Master.matrix_world.inverted()
             
            if Articulator:
                cons = Model.constraints.new(type = 'CHILD_OF')
                cons.target = Bow
                #cons.subtarget = 'Mandibular Bow'
        
                mx = Bow.matrix_world #Articulator.matrix_world * Articulator.pose.bones['Mandibular Bow'].matrix
                cons.inverse_matrix = mx.inverted()
    
        splint.ops_string += "Simulated Position {:.2f}deg Hinge Rotation and {:.2f}mm Translation:".format(hinge_opening, L)
        
        return {'FINISHED'}

class D3DUAL_OT_show_hide_articulator(bpy.types.Operator):
    """Show/Hide the articulator"""
    bl_idname = "d3dual.show_hide_articulator"
    bl_label = "Hide All Attachment"
    bl_options = {'REGISTER', 'UNDO'}
    
    hide = bpy.props.BoolProperty(default = False)
    @classmethod
    def poll(cls, context):
        
        return True
   
    def execute(self, context):
        
        Art = bpy.data.objects.get('Articulator')
        if Art:
            Art.hide = self.hide                           
        return {'FINISHED'} 
    
              
def register():
    bpy.utils.register_class(D3DUAL_OT_generate_articulator)
    bpy.utils.register_class(D3DUAL_OT_generate_articulator_keyframes)
    bpy.utils.register_class(D3DUAL_OT_capture_articulated_position)
    bpy.utils.register_class(D3DUAL_OT_live_articulator_parameters)
    bpy.utils.register_class(D3DUAL_OT_show_hide_articulator)
    bpy.utils.register_class(D3DUAL_OT_splint_open_pin_on_articulator)
    bpy.utils.register_class(D3DUAL_OT_recover_mandible_mounting)
    
    bpy.utils.register_class(D3SPLINT_OT_articulator_view)
    bpy.utils.register_class(D3DUAL_OT_splint_create_functional_surface)
    bpy.utils.register_class(D3SPLINT_OT_splint_stop_functional_surface)
    bpy.utils.register_class(D3SPLINT_OT_splint_restart_functional_surface)
    bpy.utils.register_class(D3SPLINT_OT_splint_reset_functional_surface)
    
    
def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_generate_articulator)
    bpy.utils.unregister_class(D3DUAL_OT_generate_articulator_keyframes)
    bpy.utils.unregister_class(D3DUAL_OT_capture_articulated_position)
    bpy.utils.unregister_class(D3DUAL_OT_live_articulator_parameters)
    bpy.utils.unregister_class(D3DUAL_OT_show_hide_articulator)

    bpy.utils.unregister_class(D3SPLINT_OT_articulator_view)
    bpy.utils.unregister_class(D3DUAL_OT_splint_open_pin_on_articulator)
    bpy.utils.unregister_class(D3DUAL_OT_recover_mandible_mounting)
    bpy.utils.unregister_class(D3DUAL_OT_splint_create_functional_surface)
    bpy.utils.unregister_class(D3SPLINT_OT_splint_stop_functional_surface)
    bpy.utils.unregister_class(D3SPLINT_OT_splint_restart_functional_surface)
    bpy.utils.unregister_class(D3SPLINT_OT_splint_reset_functional_surface)
    
    
if __name__ == "__main__":
    register()

# ---- Perplexity API Suggested Migrations ----
In Blender 4.4, property definitions like BoolProperty must be assigned as class attributes within a PropertyGroup or similar, not as standalone variables. The direct assignment you provided is deprecated.

**Replace:**
```python
hide = bpy.props.BoolProperty(default = False)
```

**With:**
```python
import bpy
from bpy.props import BoolProperty

class MyProperties(bpy.types.PropertyGroup):
    hide: BoolProperty(default=False)
```

You must then register this PropertyGroup and assign it to a data block (e.g., scene, object) as needed. The key change is using the colon (:) for type annotations and defining the property inside a class derived from PropertyGroup.
