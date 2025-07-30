'''
Created on Feb 5, 2019

@author: Patrick
'''
import math
import time

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix, Color
from mathutils.bvhtree import BVHTree
from bmesh_fns import flood_selection_faces

from common_utilities import get_settings
from segmentation.cookiecutter.cookiecutter import CookieCutter
from segmentation.common import ui
from segmentation.common.rays import get_view_ray_data, ray_cast
from tracking import trackUsage

def get_wax_material():
    mat = bpy.data.materials.get("Wax Material")
    if mat is None:
        # create material
        mat = bpy.data.materials.new(name="Wax Material")
        mat.diffuse_color = Color((.85, .4, .4))
        mat.use_transparency = True
        mat.transparency_method = 'Z_TRANSPARENCY'
        mat.alpha = .85

    return mat
    
    
class D3Splint_OT_cookie_embrasure_blocker(CookieCutter):
    
    """ Pick Insertion Axis """
    operator_id    = "d3splint.embrasures_and_tunnels"
    bl_idname      = "d3splint.embrasures_and_tunnels"
    bl_label       = "Blockout Embrasures and Tunnels"
    bl_description = "Use virtual wax to fill embrasures and tunels"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"

    default_keymap = {
        "cancel": {"ESC"},
    }

    @classmethod
    def can_start(cls, context):
        """ Start only splint started and model indicated"""

        
        return context.object != None and context.object.hide == False

    
    
    def get_bmesh_data(self):
        #get bmesh data to process
        bme = bmesh.new()
        bme.from_mesh(self.model.data)
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        
        return bme
    
    def get_create_meta_data(self):
        
        S = 1  #todo, advanced setting?
        mx = self.model.matrix_world
        L = Matrix.Translation(mx.to_translation())
        Smx = Matrix.Scale(1/S, 4)
        q = mx.to_quaternion()
        Rmx = q.to_matrix().to_4x4()
        
        if 'Diastema Blockou Meta' in bpy.data.objects:
            meta_obj = bpy.data.objects.get('Diastema Blockou Meta')
            meta_data = meta_obj.data
            meta_data.elements.clear()
            meta_data.resolution = self.final_meta_resolution
        else:
            meta_data = bpy.data.metaballs.new('Diastema Blockout Meta')
            meta_obj = bpy.data.objects.new('Diastema Mesh', meta_data)
            meta_data.resolution = self.final_meta_resolution
            meta_data.render_resolution = self.final_meta_resolution
            self.context.scene.objects.link(meta_obj)    
        
       
        meta_obj.hide = True
        meta_obj.matrix_world =  L * Rmx * Smx
        
        me = bpy.data.meshes.new('Embrasure Wax')
        wax_mesh = bpy.data.objects.new('Embrasure Wax', me) 
        wax_mesh.matrix_world =  L * Rmx * Smx
        self.context.scene.objects.link(wax_mesh)
        
        mat = get_wax_material()
        wax_mesh.data.materials.append(mat)
        wax_mesh.material_slots[0].material = mat
        meta_obj.data.materials.append(mat)
        return meta_obj, meta_data, wax_mesh
    
    def start(self):
        """ initialization function """
        bpy.ops.ed.undo_push()  # push current state to undo
        
        #TOOD the dictionary storage/organization
        #TODO presets
        self.max_gap = 2.0  ##min = .5, max = 5, description = 'Largest gap to close a diastema')
        self.wax_drop_size = 1.0   #, min = .25, max = 1.5, description = 'Size of wax droplets to use to blockout')
        self.max_tangential = 70  #max tangential surface angle to detect a collision
        self.final_meta_resolution = 0.4
        self.over_pack = 2
        self.cache_ray_data = {}
        self.wax_locaitons = []
        self.solver = 'BMESH'
        
        #collect contextual and model information
        self.context = bpy.context
        self.model = bpy.context.object
        self.bme = self.get_bmesh_data()
        self.bme.normal_update()
        self.meta_obj, self.meta_data, self.wax_mesh = self.get_create_meta_data()
        self.bvh = BVHTree.FromBMesh(self.bme)
    
        prefs = get_settings()
        r,g,b = prefs.undercut_color
        self.ucolor = Color((r,g,b))
    
        self.cache_self_raycast()
        self.find_intersection_cached()
        self.preview_wax2()
        
        #set view
        self.start_ui()
        
    def preview_merge(self):
        if 'Diastemas' not in self.model.modifiers:
            mod = self.model.modifiers.new('Diastemas', type = 'BOOLEAN')
            mod.operation = 'UNION'
            mod.solver = self.solver

        else:
            mod = self.model.modifiers.get('Diastemas')
            mod.solver = self.solver
        mod.object = self.wax_mesh    
        mod.show_viewport = True
        self.wax_mesh.hide = True
        self.context.scene.update()
        
        
        
    def unpreview_merge(self):
        if 'Diastemas' not in self.model.modifiers:
            return
        mod = self.model.modifiers.get('Diastemas')
        mod.show_viewport = False
        self.wax_mesh.hide = False
        
        
    def change_solver(self):
        if self.solver == 'CARVE':
            self.solver = 'BMESH'
        else:
            self.solver = 'CARVE'
            
        if 'Diastema' in self.model.modifiers:
            mod = self.model.modifiers.get('Diastemas')
            mod.solver = self.solver
            
            
    def end_commit(self):
        """ Commit changes to mesh! """
        
        
        if 'Diastemas' not in self.model.modifiers:
            mod = self.model.modifiers.new('Diastemas', type = 'BOOLEAN')
            mod.operation = 'UNION'
            mod.solver = self.solver
            mod.object = self.wax_mesh
            self.context.scene.update()
        else:
            mod = self.model.modifiers.get('Diastemas')
            mod.solver = self.solver
            if not mod.show_viewport:
                mod.show_viewport = True
                self.context.scene.update()
            
        self.wax_mesh.hide = True
        
        # settings for to_mesh
        apply_modifiers = True
        settings = 'PREVIEW'
        old_mesh = self.model.data
        new_mesh = self.model.to_mesh(self.context.scene, apply_modifiers, settings)
        new_mesh.calc_normals()
        # object will still have modifiers, remove them
        self.model.modifiers.clear()
        # assign the new mesh to obj.data 
        self.model.data = new_mesh
        # remove the old mesh from the .blend
        bpy.data.meshes.remove(old_mesh)
        
        self.context.scene.objects.unlink(self.meta_obj)
        bpy.data.metaballs.remove(self.meta_data)
        old_data = self.wax_mesh.data
        self.context.scene.objects.unlink(self.wax_mesh)
        bpy.data.meshes.remove(old_data)
        
        #trackUsage("D3Model:EmbrasuresTunnels",(str(self.wax_drop_size)[0:4],str(self.max_tangential), str(self.max_gap)))
        #bpy.ops.object.mode_set(mode = 'EDIT')
        #bpy.ops.mesh.select_all(action = 'SELECT')
        #bpy.ops.mesh.normals_make_consistent()
        #bpy.ops.object.mode_set(mode = 'OBJECT')
        
        return 'finish'

    def end_cancel(self):
        """ Cancel changes """
        bpy.ops.ed.undo()   # undo geometry hide, remove now objects

    def end(self):
        """ Restore everything, because we're done """
        #self.manipulator_restore()
        #self.header_text_restore()
        #self.cursor_modal_restore()

    def update(self):
        """ Check if we need to update any internal data structures """
        pass
    
    
    ##########################################
    ######## Nuts and Bolts   ###############        
    def detect_and_block(self):
        start = time.time()
        self.find_intersections_normal()
        
        finish = time.time()
        print('took %f seconds to find undercuts' % (finish-start))
        start = finish
        self.preview_wax()
        finish = time.time()
        print('took %f seconds to generate wax' % (finish-start))
    
    
    def confirm_merge(self):
        return
    
    def hide_wax(self):
        return
    
    def wax_opacity(self):
        return
    
     
        
    def start_ui(self):
        self.instructions = {
            "basic": "Adjust settings to allow the operator to look for tunnels and embrasures",
            "goal": "Wax will occlude tunnels and deep embrasures",
            "delete": "Right click on any wax blobs that are undesired",
            "merge": "Use the Preview Merge to ensure that the boolean union of the wax is successful.  If not successful, adjust wax droplet radius slightly, and retry",
            "commit": "When satisfactory blockout has been achieved, press the 'Commit' button"
        }
        
        #TOOLS Window
        win_tools = self.wm.create_window('Diastema/Tunnel Tools', {'pos':7, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})

        tools_container = win_tools.add(ui.UI_Container())
        tools_container.rounded_background = True
        
        actual_tools = tools_container.add(ui.UI_Frame('Wax Control', fontsize=14))
        #pview = actual_tools.add(ui.UI_Button('Preview Locations', self.find_intersection_cached, bgcolor = (.4, .4, .4, .9), margin = 3))
        #pview = actual_tools.add(ui.UI_Button('Preview Wax', self.preview_wax2, bgcolor = (.4, .8, .4, .9), margin = 3))
        pmerge= actual_tools.add(ui.UI_Button('Preview Merge', self.preview_merge, bgcolor = (.4, .4, .4, .9), margin = 3))
        cmerge= actual_tools.add(ui.UI_Button('Change Solver', self.confirm_merge, bgcolor = (.4, .4, .4, .9), margin = 3))
        
        
        #tweak_tools = tools_container.add(ui.UI_Frame('Tweak Direction', fontsize=14))
        #tweak_tools.add(ui.UI_Button('Tweak Anterior', self.tweak_anterior, margin = 3))
        #tweak_tools.add(ui.UI_Button('Tweak Posterior', self.tweak_posterior, margin = 3))
        #tweak_tools.add(ui.UI_Button('Tweak Right', self.tweak_right, margin = 3))
        #tweak_tools.add(ui.UI_Button('Tweak Left', self.tweak_left, margin = 3))
        
        tweak_tools = tools_container.add(ui.UI_Frame('Finish', fontsize=14))
        tweak_tools.add(ui.UI_Button('Commit', lambda:self.done(cancel=False), margin = 3))
        tweak_tools.add(ui.UI_Button('Cancel', lambda:self.done(cancel=True), margin = 3))
        
        
        
        #HELP AND OPTIOND WINDO
        info = self.wm.create_window('Diastema/Tunnel Help', {'pos':9, 'movable':True, 'bgcolor':(0.50, 0.50, 0.50, 0.90)})
        #info.add(ui.UI_Label('Instructions', fontsize=16, align=0, margin=4))
        collapse = info.add(ui.UI_Collapsible('Instructions          ',collapsed = False))
        self.inst_paragraphs = [collapse.add(ui.UI_Markdown('', min_size=(200,10))) for i in range(7)]
        
        self.inst_paragraphs[0].set_markdown(self.instructions['basic'])
        self.inst_paragraphs[1].set_markdown('Objective: ' + self.instructions['basic'])
        
        self.inst_paragraphs[2].set_markdown('- ' + self.instructions['goal'])
        self.inst_paragraphs[3].set_markdown('- ' + self.instructions['delete'])
        self.inst_paragraphs[4].set_markdown('- ' + self.instructions['merge'])
        self.inst_paragraphs[5].set_markdown('- ' + self.instructions['commit'])
        
        
        for i in self.inst_paragraphs: i.visible = True
        
        
        
        #######################################
        #####  Options Get/Set fns ############
        #######################################
        def wax_radius_getter():
            return self.wax_drop_size
            
        def wax_radius_setter(v):
            self.wax_drop_size = max(0.25, v)
            self.wax_drop_size = round(min(self.wax_drop_size, 5.0), 2)
            self.preview_wax2()
        
        def max_tangential_getter():
            return self.max_tangential

        def max_tangential_setter(v):
            self.max_tangential = max(50, v)
            self.max_tangential = int(min(self.max_tangential, 85))
            self.find_intersection_cached()
            self.preview_wax2()
            
            
        def meta_res_getter(): 
            return self.final_meta_resolution
            
        def meta_res_setter(v):
            by = max(0.25, v)
            by = min(by, 1.5)
            self.final_meta_resolution = round(by,2)
            self.meta_data.resolution = self.final_meta_resolution
            
            self.preview_wax2()
            
        def max_gap_getter(): 
            return self.max_gap
            
        def max_gap_setter(v):
            by = max(0.1, v)
            by = min(by, 5.0)
            self.max_gap = round(by,2)
            
            self.find_intersection_cached()
            self.preview_wax2()
            
            
        #self.ui_instructions = info.add(ui.UI_Markdown('test', min_size=(200,200)))
        options = info.add(ui.UI_Frame('Wax Settings', fontsize=14))
        
        drop_radius = options.add(ui.UI_Number("Droplet Radius", wax_radius_getter, wax_radius_setter, update_multiplier= .05))
        max_tangent = options.add(ui.UI_Number("Max Tangential", max_tangential_getter, max_tangential_setter, update_multiplier= .5))
        max_gap = options.add(ui.UI_Number("Maximum Gap", max_gap_getter, max_gap_setter, update_multiplier= .05))
        meta_res = options.add(ui.UI_Number("Wax Resolution", meta_res_getter, meta_res_setter, update_multiplier= .1))
        
        #drop_z = options.add(ui.UI_Number("Cube Z", blob_z_getter, blob_z_setter, update_multiplier= .05))
        #drop_y = options.add(ui.UI_Number("Cube Y", blob_y_getter, blob_y_setter, update_multiplier= .05))
        
        
        #options.add(ui.UI_Button('Top View', self.top_view, margin = 3))
        #options.add(ui.UI_Button('Right View', self.right_view, margin = 3))
        #options.add(ui.UI_Button('Left View', self.left_view, margin = 3))
        #options.add(ui.UI_Button('Front View', self.front_view, margin = 3))
        #options.add(ui.UI_Button('Insertion View', self.insert_view, margin = 3))
    
    
    
    
    def ray_cast_wax_mesh(self):
        mx = self.wax_mesh.matrix_world
        imx = mx.inverted()
        mouse = self.actions.mouse
        view_vector, ray_origin, ray_target = get_view_ray_data(self.context, mouse)
        loc, no, face_ind = ray_cast(self.wax_mesh, imx, ray_origin, ray_target, also_do_this = None)
        
        return loc, no, face_ind
        
        
    def cache_self_raycast(self):
        start = time.time()
        self.cache_ray_data = {}
        for v in self.bme.verts:
            ray_start = v.co + .0001 * v.normal
            
            loc, no, ind, d = self.bvh.ray_cast(ray_start, v.normal, 4.0)
            
            if loc:
                f = self.bme.faces[ind]
                self.cache_ray_data[v] = (v.co, loc, d, f.normal.dot(v.normal)**2 )
                
        finish = time.time()
        print('cached ray cast data in %f' % (finish-start))

    def find_intersection_cached(self):
        
        start = time.time()
        dot_max = abs(math.sin(self.max_tangential * math.pi/180))
        r_max = self.max_gap
        op = self.over_pack
        
        wax_locations = []
        for v, (loc0, loc1, d, dot) in self.cache_ray_data.items():
             
            if d < r_max and dot > dot_max:
                
                vec = loc1 - loc0
                steps = math.ceil(op * vec.length/self.wax_drop_size)
                vec.normalize()
                wax_locations += [loc0 + i * self.wax_drop_size/op * vec for i in range(0, steps+1)]

        self.wax_locations = wax_locations    
        
        finish = time.time()
        print('filtered cached ray data in %f' % (finish-start))
        
        
    def find_intersections_normal(self):
        self.ray_data = []
        undercut_vectors = []
        print('there are%i verts' % len(self.bme.verts))
        print(self.max_gap)
        for v in self.bme.verts:
            ray_start = v.co + .0001 * v.normal
            
            loc, no, ind, d = self.bvh.ray_cast(ray_start, v.normal, self.max_gap)
            
            if loc:
                f = self.bme.faces[ind]
                
                if f.normal.dot(v.normal)**2 > abs(math.sin(self.max_tangential * math.pi/180)):
                    
                    undercut_vectors += [(v.co, loc, d)]
                    
                    
                    
        self.ray_data = undercut_vectors
        
        print('Found %i undercut vectors' % len(undercut_vectors))
        
    def find_intersections_z(self):  
        Z = Vector((0,0,1))              
        self.ray_data = {}
        undercut_vectors = []
        for v in self.bme.verts:
            
            if v.normal.dot(Z) > 0:
                direction = Z
            else:
                direction = -Z
            ray_start = v.co + .0001 * v.normal
            
            loc, no, ind, d = self.bvh.ray_cast(ray_start, direction, self.max_gap)
            
            if loc:
                f = self.bme.faces[ind]
                
                if f.normal.dot(v.normal)**2 > self.max_tangential:
                    
                    undercut_vectors += [(v.co, loc, d)] 
                    
        self.ray_data = undercut_vectors
    
    
    def preview_wax(self):
        self.unpreview_merge()
        S= 1
        undercut_vectors = self.ray_data
        
        self.meta_data.elements.clear()
        op = float(self.over_pack) 
        for ele in undercut_vectors:
            
            mb = self.meta_data.elements.new(type = 'BALL')
            mb.co = S * ele[0]
            mb.radius = S * self.wax_drop_size
            
            mb = self.meta_data.elements.new(type = 'BALL')
            mb.co = S * ele[1]
            mb.radius = S * self.wax_drop_size
            
            vec = ele[1] - ele[0]
            steps = math.ceil(op * vec.length/self.wax_drop_size)
            vec.normalize() 
             
            for i in range(0,steps):
                mb = self.meta_data.elements.new(type = 'BALL')
                mb.co = S * (ele[0] + i * self.wax_drop_size/op * vec)
                mb.radius = S * self.wax_drop_size
        
        self.context.scene.update()
        me = self.meta_obj.to_mesh(self.context.scene, apply_modifiers = True, settings = 'PREVIEW')
        old_me  = self.wax_mesh.data
        self.wax_mesh.data = me
        bpy.data.meshes.remove(old_me)
        self.wax_mesh.data.update()
        
        
    def preview_wax2(self):
        self.unpreview_merge()
        self.meta_data.elements.clear()
        
        for loc in self.wax_locations:
            
            mb = self.meta_data.elements.new(type = 'BALL')
            mb.co = loc
            mb.radius = self.wax_drop_size
            
            
        self.context.scene.update()
        me = self.meta_obj.to_mesh(self.context.scene, apply_modifiers = True, settings = 'PREVIEW')
        old_me  = self.wax_mesh.data
        self.wax_mesh.data = me
        bpy.data.meshes.remove(old_me)
        self.wax_mesh.data.update() 
    
    
    def remove_wax_island(self, f_ind):
        
        #remove island at the wax_mesh level (alternatively we can remove it at the volumetric element level)
        
        bme = bmesh.new()
        bme.from_mesh(self.wax_mesh.data)
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        
        f = bme.faces[f_ind]
        
        island = flood_selection_faces(bme, set(), f, expansion_mode = 'VERTEX', max_iters = 1000)
        
        del_verts = set()
        for f in island:
            del_verts.update(f.verts[:])
            
        for f in island:
            bme.faces.remove(f)
        for v in del_verts:
            bme.verts.remove(v)
            
        bme.to_mesh(self.wax_mesh.data)
        self.wax_mesh.data.update()
        bme.free()
        
        
        
          
    @CookieCutter.FSM_State("main")
    def modal_main(self):
        #self.cursor_modal_set("CROSSHAIR")

        if self.actions.pressed("commit"):
            self.end_commit()
            return

        if self.actions.pressed("cancel"):
            self.done(cancel=True)
            return
        
        if self.actions.pressed('RIGHTMOUSE'):
            loc, no, ind = self.ray_cast_wax_mesh()
            if loc:
                self.remove_wax_island(ind)
            
        
        
def register():
    bpy.utils.register_class(D3Splint_OT_cookie_embrasure_blocker)
    
    #bpy.utils.register_class(D3SPLINT_OT_sculpt_model_undo)
    
def unregister():
    bpy.utils.unregister_class(D3Splint_OT_cookie_embrasure_blocker)

    #bpy.utils.unregister_class(D3SPLINT_OT_sculpt_model_undo)