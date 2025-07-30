'''
Created on Sep 9, 2019

@author: Patrick
'''

import random
import math
import time

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import loops_tools
from mathutils import Vector, Color, Matrix
from mathutils.bvhtree import BVHTree

import tracking
from subtrees.bmesh_utils.bmesh_utilities_common import bmesh_join_list
from subtrees.geometry_utils.loops_tools import relax_loops_util
from subtrees.geometry_utils.bound_box_utils import get_bbox_center
from subtrees.addon_common.common.utils import get_settings
from subtrees.geometry_utils.transformations import random_axes_from_normal, r_matrix_from_principal_axes
from subtrees.metaballs.vdb_tools import remesh_bme

from refractory_numpy import remove_undercuts_fast

def remove_undercuts(context, ob, view, world = True, 
                     smooth = True,
                     offset = 0.00, use_offset = False,
                     undercut = 0.00, use_undercut = False,
                     res = .5, epsilon = .000001):
    '''
    args:
      ob - mesh object
      view - Mathutils Vector
      
    return:
       Bmesh with Undercuts Removed?
       
    best to make sure normals are consistent beforehand
    best for manifold meshes, however non-man works
    noisy meshes can be compensated for with island threhold
    '''
    
    interval = time.time()
    
    me = ob.to_mesh(context.scene, True, 'RENDER')    
    bme = bmesh.new()
    bme.from_mesh(me)
    bme.normal_update()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    
    if use_offset or use_undercut:
        bme_offset = bmesh.new()
        bme_offset.from_mesh(me)
        bme_offset.normal_update()
        bme_offset.verts.ensure_lookup_table()
        bme_offset.edges.ensure_lookup_table()
        bme_offset.faces.ensure_lookup_table()
    
    
    if use_offset:
        for v in bme_offset.verts:
            v.co += offset * v.normal
            
    if use_undercut:
        for v in bme.verts:
            if not use_offset:
                offset = 0.0
            v.co += (offset - undercut) * v.normal
    
    bvh = BVHTree.FromBMesh(bme)
    
    #keep track of the world matrix
    mx = ob.matrix_world
    
    if world:
        #meaning the vector is in world coords
        #we need to take it back into local
        i_mx = mx.inverted()
        view = i_mx.to_quaternion() * view
            
    up_faces = set()
    overhang_faces = set()  #all faces pointing away from view
    
    #find the lowest part of the mesh to add a base plane to.
    lowest_vert = min(bme.verts[:], key = lambda x: x.co.dot(view))
    lowest_point = lowest_vert.co
    
    #center point and flat
    box_center = get_bbox_center(ob, world = False)
    base_plane_center = box_center + (lowest_point - box_center).dot(view) * view + 1.1 * view
    X, Y, Z = random_axes_from_normal(view)
    print("Found the base plane in %f seconds" % (time.time() - interval))
    interval = time.time()
    
    R = r_matrix_from_principal_axes(X, Y, Z)
    R = R.to_4x4()    
    T = Matrix.Translation(base_plane_center)
    
    grid_bme = bmesh.new()
    diag = Vector(ob.dimensions).length
    grid_cells = math.floor(diag/res)
    bmesh.ops.create_grid(grid_bme, x_segments = grid_cells, y_segments = grid_cells, size = diag/2, matrix = T*R)

    in_grid = set()
    out_grid = set()
    for v in grid_bme.verts:
        loc, no, face_ind, d = bvh.ray_cast(v.co, view)
        if loc:
            in_grid.add(v)
    
        else:
            out_grid.add(v)
    
    del_faces = set()
    #this will triangulate the diagonals
    for f in grid_bme.faces:
        if len(f.verts) != 4: continue
        out_verts = [v for v in f.verts if v in out_grid]
        #if len(out_verts) == 3:
            #grid_bme.faces.new(out_verts)
        if len(out_verts) == 4:
            del_faces.add(f)
    
    
    del_vs = [v for v in out_verts if all([f in del_faces for f in v.link_faces])]
    del_eds = [ed for ed in grid_bme.edges if all([f in del_faces for f in ed.link_faces])]
        
    for f in del_faces:
        grid_bme.faces.remove(f)
    for ed in del_eds:
        grid_bme.edges.remove(ed)
    for v in del_vs:
        grid_bme.verts.remove(v)    
              
    grid_bme.verts.ensure_lookup_table()
    grid_bme.edges.ensure_lookup_table()
    grid_bme.faces.ensure_lookup_table()
    
    for f in grid_bme.faces:
        f.normal_flip()
        
    gdict = bmesh.ops.extrude_face_region(grid_bme, geom = grid_bme.faces[:])
    move_vs = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)]
    for v in move_vs:
        v.co += -view
    
    print("created the base grid in %f seconds" % (time.time() - interval))
    interval = time.time()
    
    #extend the base if needed, and record these before we do any other stuff
    non_man_eds = [ed for ed in bme.edges if len(ed.link_faces) == 1]
    if len(non_man_eds):
        gdict = bmesh.ops.extrude_edge_only(bme, edges = non_man_eds)
        bme.edges.ensure_lookup_table()
        new_edges = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMEdge)]
        new_verts = [ele for ele in gdict['geom'] if isinstance(ele, bmesh.types.BMVert)]
        for v in new_verts: 
            co_flat = v.co +  (base_plane_center - v.co).dot(view) * view    
            v.co = co_flat
        bme.verts.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        
    face_directions = [[0]] * len(bme.faces)
    #precalc all the face directions and store in dict
    for f in bme.faces:
        direction = f.normal.dot(view)
        
        if direction <= -epsilon:
            overhang_faces.add(f)
        else:
            up_faces.add(f)
            
        face_directions[f.index] = direction
    
    print('there are %i up_faces' % len(up_faces))
    print('there are %i down_faces' % len(overhang_faces))
    print("sorted the faces in %f seconds" % (time.time() - interval))
    interval = time.time()
    
    #for f in bme.faces:
    #    if f in overhangs:
    #        f.select_set(True)
    #    else:
    #        f.select_set(False)
            
    overhang_islands = [] #islands bigger than a certain threshold (by surface area?
    upfacing_islands = []
    def face_neighbors_up(bmface):
        neighbors = []
        for ed in bmface.edges:
            neighbors += [f for f in ed.link_faces if f != bmface and f in up_faces]
            
        return neighbors
    
    #remove small islands from up_faces and add to overhangs
    max_iters = len(up_faces)
    iters_0 = 0
    islands_removed = 0
    
    up_faces_copy = up_faces.copy()
    while len(up_faces_copy) and iters_0 < max_iters:
        iters_0 += 1
        max_iters_1 = len(up_faces)
        seed = up_faces_copy.pop()
        new_faces = set(face_neighbors_up(seed))
        up_faces_copy -= new_faces
        
        island = set([seed])
        island |= new_faces
        
        iters_1 = 0
        while iters_1 < max_iters_1 and new_faces:
            iters_1 += 1
            new_candidates = set()
            for f in new_faces:
                new_candidates.update(face_neighbors_up(f))
            
            new_faces = new_candidates - island
        
            if new_faces:
                island |= new_faces    
                up_faces_copy -= new_faces
        if len(island) < 75: #small patch surrounded by overhang, add to overhang area
            islands_removed += 1
            overhang_faces |= island
        else:
            upfacing_islands += [island]
            
    print('%i upfacing islands removed' % islands_removed)
    print('there are now %i down faces' % len(overhang_faces))
    
    
    def face_neighbors_down(bmface):
        neighbors = []
        for ed in bmface.edges:
            neighbors += [f for f in ed.link_faces if f != bmface and f in overhang_faces]
            
        return neighbors
    overhang_faces_copy = overhang_faces.copy()
    
    while len(overhang_faces_copy):
        seed = overhang_faces_copy.pop()
        new_faces = set(face_neighbors_down(seed))
        island = set([seed])
        island |= new_faces
        overhang_faces_copy -= new_faces
        iters = 0
        while iters < 100000 and new_faces:
            iters += 1
            new_candidates = set()
            for f in new_faces:
                new_candidates.update(face_neighbors_down(f))
            
            new_faces = new_candidates - island
        
            if new_faces:
                island |= new_faces    
                overhang_faces_copy -= new_faces
        if len(island) > 75: #TODO, calc overhang factor.  Surface area dotted with direction
            overhang_islands += [island]
    
    for f in bme.faces:
        f.select_set(False)   
    for ed in bme.edges:
        ed.select_set(False)
    for v in bme.verts:
        v.select_set(False)
    
    print("removed small overang islands in %f seconds" % (time.time() - interval))
    interval = time.time()   
    
         
    island_loops = []
    island_verts = []
    del_faces = set()
    for isl in overhang_islands:
        loop_eds = []
        loop_verts = []
        del_faces |= isl
        for f in isl:
            for ed in f.edges:
                if len(ed.link_faces) == 1:
                    loop_eds += [ed]
                    loop_verts += [ed.verts[0], ed.verts[1]]
                elif (ed.link_faces[0] in isl) and (ed.link_faces[1] not in isl):
                    loop_eds += [ed]
                    loop_verts += [ed.verts[0], ed.verts[1]]
                elif (ed.link_faces[1] in isl) and (ed.link_faces[0] not in isl):
                    loop_eds += [ed]
                    loop_verts += [ed.verts[0], ed.verts[1]]
                    
            #f.select_set(True) 
        island_verts += [list(set(loop_verts))]
        island_loops += [loop_eds]
    
    bme.faces.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    
    loop_edges = []
    for ed_loop in island_loops:
        loop_edges += ed_loop
        for ed in ed_loop:
            ed.select_set(True)
    
    relax_loops_util(bme, loop_edges, 5)
    
    print("found the boundaries of overhands, and smoothed them in %f seconds" % (time.time() - interval))
    interval = time.time() 
    
    for ed in bme.edges:
        ed.select_set(False)
        
    exclude_vs = set()
    for vs in island_verts:
        exclude_vs.update(vs)
    
    smooth_verts = []    
    for v in exclude_vs:
        smooth_verts += [ed.other_vert(v) for ed in v.link_edges if ed.other_vert(v) not in exclude_vs]
            
    ret = bmesh.ops.extrude_edge_only(bme, edges = loop_edges)
    
    
    new_fs = [ele for ele in ret['geom'] if isinstance(ele, bmesh.types.BMFace)]                
    new_vs = [ele for ele in ret['geom'] if isinstance(ele, bmesh.types.BMVert)]
    
    #TODO, ray cast down to base plane, yes
    for v in new_vs:
        
        delta = lowest_point - v.co
        v.co = v.co + delta.dot(view) * view
    
    
    
    print("extruded them downward in  %f seconds" % (time.time() - interval))
    interval = time.time()
    
    
    for f in new_fs:
        f.select_set(True)
        
    bmesh.ops.delete(bme, geom = list(del_faces), context = 3)
    
    del_verts = []
    for v in bme.verts:
        if all([f in del_faces for f in v.link_faces]):
            del_verts += [v]        
    bmesh.ops.delete(bme, geom = del_verts, context = 1)
    
    
    del_edges = []
    for ed in bme.edges:
        if len(ed.link_faces) == 0:
            del_edges += [ed]
    print('deleting %i edges' % len(del_edges))
    bmesh.ops.delete(bme, geom = del_edges, context = 4) 
    bmesh.ops.recalc_face_normals(bme, faces = new_fs)
    
    print("Deleted extraneous geometry in  %f seconds" % (time.time() - interval))
    interval = time.time()
    
    bme.normal_update()
    
    new_me = bpy.data.meshes.new(ob.name + '_blockout')
    
    obj = bpy.data.objects.new(new_me.name, new_me)
    context.scene.objects.link(obj)
    
    obj.select = True
    context.scene.objects.active = obj
  
    if use_offset or use_undercut:
        joined_bme = bmesh_join_list([grid_bme, bme, bme_offset])
        bme_offset.free()
    else:
        joined_bme = bmesh_join_list([grid_bme, bme])
    
    
    bme_remesh = remesh_bme(joined_bme, 
              isovalue = 0.0, 
              adaptivity = 0.0, 
              only_quads = False, 
              voxel_size = .2,
              filter_iterations = 0,
              filter_width = 4,
              filter_sigma = 1.0,
              grid = None,
              write_method = 'FAST')
    
        
    bme_remesh.to_mesh(obj.data)
            
    if world:
        obj.matrix_world = mx


    #test code
    #new_me = bpy.data.meshes.new(ob.name + '_grid')
    #new_obj = bpy.data.objects.new(new_me.name, new_me)
    #context.scene.objects.link(new_obj)
    #grid_bme.to_mesh(new_me)
    
    bme.free()
    grid_bme.free()
    joined_bme.free()
    bme_remesh.free()
    del bvh
        
    return obj


class D3SPLINT_OT_refractory_model_new(bpy.types.Operator):
    '''Calculates a blocked out and offset model'''
    bl_idname = 'd3splint.refractory_model_4'
    bl_label = "Refractory Model 4"
    bl_options = {'REGISTER','UNDO'}
    
    #world = bpy.props.BoolProperty(default = True, name = "Use world coordinate for calculation...almost always should be true.")
    #smooth = bpy.props.BoolProperty(default = True, name = "Smooth the outline.  Slightly less acuurate in some situations but more accurate in others.  Default True for best results")

    use_offset = bpy.props.BoolProperty(default = True, name = "Use Spacer", description = "Use offset spacer on the mesh")
    use_undercut = bpy.props.BoolProperty(default = True, name = "Allow Undercuts", description = "Allow undercuts up to a certain amount")
    #use_drillcomp = bpy.props.BoolProperty(default = False, name = "Use Drill Comp", description = "Use drilll compensation")
    
    offset_value = bpy.props.FloatProperty(default = 0.12, min = 0.01, max = 5.0, name = 'Offset')
    undercut_value = bpy.props.FloatProperty(default = 0.05, min = 0.01, max = 1.0, name = 'Undercut')
    
    
    method = bpy.props.EnumProperty(items = [('1','Standard','1'),('2','Fast (Beta)','2')])
      
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        C0 = context.space_data.type == 'VIEW_3D'
        return  C0

    def invoke(self, context, event):
        
        prefs = get_settings()
        self.offset_value = prefs.def_passive_radius
        self.undercut_value = prefs.def_blockout_radius
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        bpy.ops.ed.undo_push()
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        Model = bpy.data.objects.get(splint.model)
        if Model == None:
            self.report({'ERROR'},'Need to set the model first')
            return {'CANCELLED'}
        
        Axis = bpy.data.objects.get('Insertion Axis')
        if Axis == None:
            self.report({'ERROR'},'Need to set survey from view first, then adjust axis arrow')
            return {'CANCELLED'}
        
        
        ob = Model
        view = Axis.matrix_world.to_quaternion() * Vector((0,0,1))
        
        start = time.time()
        
        if self.method == '1':
            new_ob = remove_undercuts(context, ob, view, True, False,
                         offset = self.offset_value,
                         use_offset = self.use_offset,
                         undercut = self.undercut_value,
                         use_undercut = self.use_undercut)
            
        else:
            new_ob = remove_undercuts_fast(context, ob, view, True, False,
                         offset = self.offset_value,
                         use_offset = self.use_offset,
                         undercut = self.undercut_value,
                         use_undercut = self.use_undercut)
            
        
        finish = time.time()
        total_time = finish-start
        print('took %f seconds to block out mesh' % (finish-start))
        
        if 'Refractory Model' in bpy.data.objects:
            old_ob = bpy.data.objects.get('Refractory Model')
            old_data = old_ob.data
            context.scene.objects.unlink(old_ob)
            bpy.data.objects.remove(old_ob)
            bpy.data.meshes.remove(old_data)
        
        
        new_ob.name = 'Refractory Model'
        mat = bpy.data.materials.get("Refractory Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Refractory Material")
            mat.diffuse_color = Color((0.36, .8,.36))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        if len(new_ob.material_slots) == 0:
            new_ob.data.materials.append(mat)
        
        
        Model.hide = False
        new_ob.hide = False
        splint.refractory_model = True
        splint.refractory = new_ob.name
        splint.passive_value = self.offset_value
        splint.undercut_value = self.undercut_value
        splint.ops_string += 'Refractory Model:'
        #tracking.trackUsage("D3Splint:RemoveUndercuts3", (str(total_time)[0:4]), background = True)
        
        
        return {'FINISHED'}
    
   
   
class D3DUAL_OT_refractory_model_max(bpy.types.Operator):
    '''Calculates a blocked out and offset model for maxilla'''
    bl_idname = 'd3dual.refractory_model_max'
    bl_label = "Refractory Model Max"
    bl_options = {'REGISTER','UNDO'}
    
    #world = bpy.props.BoolProperty(default = True, name = "Use world coordinate for calculation...almost always should be true.")
    #smooth = bpy.props.BoolProperty(default = True, name = "Smooth the outline.  Slightly less acuurate in some situations but more accurate in others.  Default True for best results")

    use_offset = bpy.props.BoolProperty(default = True, name = "Use Spacer", description = "Use offset spacer on the mesh")
    use_undercut = bpy.props.BoolProperty(default = True, name = "Allow Undercuts", description = "Allow undercuts up to a certain amount")
    #use_drillcomp = bpy.props.BoolProperty(default = False, name = "Use Drill Comp", description = "Use drilll compensation")
    
    offset_value = bpy.props.FloatProperty(default = 0.12, min = 0.01, max = 5.0, name = 'Offset')
    undercut_value = bpy.props.FloatProperty(default = 0.05, min = 0.01, max = 1.0, name = 'Undercut')
    
    
    method = bpy.props.EnumProperty(items = [('1','Standard','1'),('2','Fast','2')], default = '2')
    
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        C0 = context.space_data.type == 'VIEW_3D'
        return  C0 

    def draw(self, context):
        
        layout = self.layout
        if self.splint.max_refractory_model_complete and self.splint.finalize_splint_max:
            
            row = layout.row()
            row.label('WARNING: You have already finalized.')
            row = layout.row()
            row.label('this will change the fit if you re-export')
        
            
        row = layout.row()
        row.prop(self, "use_offset")
        row = layout.row()
        row.prop(self, "use_undercut")
        row = layout.row()
        row.prop(self, "offset_value")
        row = layout.row()
        row.prop(self, "undercut_value")
        row = layout.row()
        row.prop(self, "method")
        
        
    def invoke(self, context, event):
        
        prefs = get_settings()
        self.offset_value = prefs.def_passive_radius
        self.undercut_value = prefs.def_blockout_radius
        
        n = context.scene.odc_splint_index
        self.splint = context.scene.odc_splints[n]
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        bpy.ops.ed.undo_push()
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        Model = bpy.data.objects.get(splint.max_model)
        if Model == None:
            self.report({'ERROR'},'Need to set the max model first')
            return {'CANCELLED'}
        
        Axis = bpy.data.objects.get('Max Insertion Axis')
        if Axis == None:
            self.report({'ERROR'},'Need to survey from view first')
            return {'CANCELLED'}
        
        
        ob = Model
        view = Axis.matrix_world.to_quaternion() * Vector((0,0,1))
        
        start = time.time()
        
        if self.method == '1':
            new_ob = remove_undercuts(context, ob, view, True, False,
                         offset = self.offset_value,
                         use_offset = self.use_offset,
                         undercut = self.undercut_value,
                         use_undercut = self.use_undercut)
            
        else:
            new_ob = remove_undercuts_fast(context, ob, view, True, False,
                         offset = self.offset_value,
                         use_offset = self.use_offset,
                         undercut = self.undercut_value,
                         use_undercut = self.use_undercut)
        
        finish = time.time()
        total_time = finish-start
        print('took %f seconds to block out mesh' % (finish-start))
        
        if 'Max Refractory Model' in bpy.data.objects:
            old_ob = bpy.data.objects.get('Max Refractory Model')
            old_data = old_ob.data
            context.scene.objects.unlink(old_ob)
            bpy.data.objects.remove(old_ob)
            bpy.data.meshes.remove(old_data)
        
        
        new_ob.name = 'Max Refractory Model'
        cons = new_ob.constraints.new('COPY_TRANSFORMS')
        cons.target = bpy.data.objects.get(splint.max_model)
                
                
        mat = bpy.data.materials.get("Max Refractory Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Refractory Material")
            mat.diffuse_color = Color((0.36, .8,.36))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        if len(new_ob.material_slots) == 0:
            new_ob.data.materials.append(mat)
        
        
        Model.hide = False
        new_ob.hide = False
        
        for ob in bpy.data.objects:
            ob.select  = False
        context.scene.objects.active = None
        
        if self.splint.max_refractory_model_complete and self.splint.finalize_splint_max:
            if 'Final_Max' in bpy.data.objects:
                final = bpy.data.objects.get('Final_Max')
                if 'Refractory Model' in final.modifiers:
                    mod = final.modifiers.get('Refractory Model')
                    mod.object = new_ob
                    
        splint.max_refractory_model_complete = True
        splint.max_refractory = new_ob.name
        splint.max_passive_value = self.offset_value
        splint.max_undercut_value = self.undercut_value
        splint.ops_string += 'Max Refractory Model:'
        tracking.trackUsage("D3DUAL:MaxRefractoryModel", (str(total_time)[0:4], str(self.offset_value)[0:4], str(self.undercut_value)[0:4]), background = True)
        
        
        return {'FINISHED'}
    
class D3DUAL_OT_refractory_model_mand(bpy.types.Operator):
    '''Calculates a blocked out and offset model for mandible'''
    bl_idname = 'd3dual.refractory_model_mand'
    bl_label = "Refractory Model Mand"
    bl_options = {'REGISTER','UNDO'}
    
    #world = bpy.props.BoolProperty(default = True, name = "Use world coordinate for calculation...almost always should be true.")
    #smooth = bpy.props.BoolProperty(default = True, name = "Smooth the outline.  Slightly less acuurate in some situations but more accurate in others.  Default True for best results")

    use_offset = bpy.props.BoolProperty(default = True, name = "Use Spacer", description = "Use offset spacer on the mesh")
    use_undercut = bpy.props.BoolProperty(default = True, name = "Allow Undercuts", description = "Allow undercuts up to a certain amount")
    #use_drillcomp = bpy.props.BoolProperty(default = False, name = "Use Drill Comp", description = "Use drilll compensation")
    
    offset_value = bpy.props.FloatProperty(default = 0.12, min = 0.01, max = 5.0, name = 'Offset')
    undercut_value = bpy.props.FloatProperty(default = 0.05, min = 0.01, max = 1.0, name = 'Undercut')
    
    
    method = bpy.props.EnumProperty(items = [('1','Standard','1'),('2','Fast (Beta)','2')], default = '2')
    
    @classmethod
    def poll(cls, context):
        #restoration exists and is in scene
        C0 = context.space_data.type == 'VIEW_3D'
        return  C0

    
    def draw(self, context):
        
        layout = self.layout
        if self.splint.mand_refractory_model_complete and self.splint.finalize_splint_mand:
            
            row = layout.row()
            row.label('WARNING: You have already finalized.')
            row = layout.row()
            row.label('this will change the fit if you re-export')
            
        row = layout.row()
        row.prop(self, "use_offset")
        row = layout.row()
        row.prop(self, "use_undercut")
        row = layout.row()
        row.prop(self, "offset_value")
        row = layout.row()
        row.prop(self, "undercut_value")
        row = layout.row()
        row.prop(self, "method")
    
        
        
    def invoke(self, context, event):
        
        prefs = get_settings()
        self.offset_value = prefs.def_passive_radius
        self.undercut_value = prefs.def_blockout_radius
        
        n = context.scene.odc_splint_index
        self.splint = context.scene.odc_splints[n]
        
        
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        
        bpy.ops.ed.undo_push()
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        Model = bpy.data.objects.get(splint.mand_model)
        if Model == None:
            self.report({'ERROR'},'Need to set the max model first')
            return {'CANCELLED'}
        
        Axis = bpy.data.objects.get('Mand Insertion Axis')
        if Axis == None:
            self.report({'ERROR'},'Need to survey from view first')
            return {'CANCELLED'}
        
        
        ob = Model
        view = Axis.matrix_world.to_quaternion() * Vector((0,0,1))
        
        start = time.time()
        
        if self.method == '1':
            new_ob = remove_undercuts(context, ob, view, True, False,
                         offset = self.offset_value,
                         use_offset = self.use_offset,
                         undercut = self.undercut_value,
                         use_undercut = self.use_undercut)
            
        else:
            new_ob = remove_undercuts_fast(context, ob, view, True, False,
                         offset = self.offset_value,
                         use_offset = self.use_offset,
                         undercut = self.undercut_value,
                         use_undercut = self.use_undercut)
        
        finish = time.time()
        total_time = finish-start
        print('took %f seconds to block out mesh' % (finish-start))
        
        if 'Mand Refractory Model' in bpy.data.objects:
            old_ob = bpy.data.objects.get('Mand Refractory Model')
            old_data = old_ob.data
            context.scene.objects.unlink(old_ob)
            bpy.data.objects.remove(old_ob)
            bpy.data.meshes.remove(old_data)
        
        
        new_ob.name = 'Mand Refractory Model'
        cons = new_ob.constraints.new('COPY_TRANSFORMS')
        cons.target = bpy.data.objects.get(splint.mand_model)
        
        mat = bpy.data.materials.get("Refractory Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Refractory Material")
            mat.diffuse_color = Color((0.36, .8,.36))
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        if len(new_ob.material_slots) == 0:
            new_ob.data.materials.append(mat)
        
        
        Model.hide = False
        new_ob.hide = False
        for ob in bpy.data.objects:
            ob.select  = False
        context.scene.objects.active = None
        
        
        if self.splint.mand_refractory_model_complete and self.splint.finalize_splint_mand:
            if 'Final_Mand' in bpy.data.objects:
                final = bpy.data.objects.get('Final_Mand')
                if 'Refractory Model' in final.modifiers:
                    mod = final.modifiers.get('Refractory Model')
                    mod.object = new_ob
            
        print('Setting mand ref model complete')
        splint.mand_refractory_model_complete = True
        print(splint.mand_refractory_model_complete)
        splint.mand_refractory = new_ob.name
        splint.mand_passive_value = self.offset_value
        splint.mand_undercut_value = self.undercut_value
        splint.ops_string += 'Mand Refractory Model:'
        tracking.trackUsage("D3DUAL:MandRefractoryModel", (str(total_time)[0:4], str(self.offset_value)[0:4], str(self.undercut_value)[0:4]), background = True)
        
        
        return {'FINISHED'}
    
    
def register():
    bpy.utils.register_class(D3DUAL_OT_refractory_model_max)
    bpy.utils.register_class(D3DUAL_OT_refractory_model_mand)
    
    
def unregister():
    bpy.utils.unregister_class(D3DUAL_OT_refractory_model_max)
    bpy.utils.register_class(D3DUAL_OT_refractory_model_mand)
    

# ---- Perplexity API Suggested Migrations ----
To migrate your property definitions from Blender 2.79 to Blender 4.4, you must use the new annotation syntax for properties inside classes (using `:` and not assignment), and ensure you define them within a class derived from `bpy.types.PropertyGroup`, `Operator`, or `Panel` as appropriate. The old assignment style is deprecated and will not work in Blender 2.8+ and especially not in 4.x.

Here is the corrected code block for Blender 4.4+:

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    use_offset: bpy.props.BoolProperty(
        default=True,
        name="Use Spacer",
        description="Use offset spacer on the mesh"
    )
    use_undercut: bpy.props.BoolProperty(
        default=True,
        name="Allow Undercuts",
        description="Allow undercuts up to a certain amount"
    )
    offset_value: bpy.props.FloatProperty(
        default=0.12,
        min=0.01,
        max=5.0,
        name='Offset'
    )
    undercut_value: bpy.props.FloatProperty(
        default=0.05,
        min=0.01,
        max=1.0,
        name='Undercut'
    )
    method: bpy.props.EnumProperty(
        items=[
            ('1', 'Standard', '1'),
            ('2', 'Fast (Beta)', '2')
        ]
    )
```

**Key changes:**
- Use the `:` annotation syntax, not `=`.
- Place properties inside a class derived from `bpy.types.PropertyGroup`.
- Register the property group and assign it to a data block (e.g., `Scene`, `Object`) as needed in your `register()` function.

**Example registration:**
```python
def register():
    bpy.utils.register_class(MyProperties)
    bpy.types.Scene.my_tool = bpy.props.PointerProperty(type=MyProperties)

def unregister():
    del bpy.types.Scene.my_tool
    bpy.utils.unregister_class(MyProperties)
```

This is the Blender 4.4+ compatible way to define and register custom properties[3].
To migrate your property definitions from Blender 2.79 to **Blender 4.4**, you must use the new `bpy.props` API style, which requires properties to be defined as class attributes within a `PropertyGroup` or directly in an `Operator`/`Panel` class. The old style of assigning properties directly to classes at the module level is deprecated.

Below is the **Blender 4.4 compatible code block** for your properties, assuming you are defining them in a `PropertyGroup` (the recommended modern approach):

```python
import bpy

class MyAddonProperties(bpy.types.PropertyGroup):
    use_offset: bpy.props.BoolProperty(
        default=True,
        name="Use Spacer",
        description="Use offset spacer on the mesh"
    )
    use_undercut: bpy.props.BoolProperty(
        default=True,
        name="Allow Undercuts",
        description="Allow undercuts up to a certain amount"
    )
    offset_value: bpy.props.FloatProperty(
        default=0.12,
        min=0.01,
        max=5.0,
        name='Offset'
    )
    undercut_value: bpy.props.FloatProperty(
        default=0.05,
        min=0.01,
        max=1.0,
        name='Undercut'
    )
    method: bpy.props.EnumProperty(
        items=[
            ('1', 'Standard', '1'),
            ('2', 'Fast', '2')
        ],
        default='2'
    )

# Register the PropertyGroup and add it to a context, e.g., Scene
def register():
    bpy.utils.register_class(MyAddonProperties)
    bpy.types.Scene.my_addon_props = bpy.props.PointerProperty(type=MyAddonProperties)

def unregister():
    del bpy.types.Scene.my_addon_props
    bpy.utils.unregister_class(MyAddonProperties)
```

**Key changes:**
- Properties are now defined as class attributes with a colon (`:`) and type annotation.
- Properties must be inside a `PropertyGroup` (or directly in an Operator/Panel class).
- Use `PointerProperty` to attach your `PropertyGroup` to `Scene`, `Object`, etc.

This is the modern, Blender 4.4-compliant way to define and register custom properties.
```python
import bpy
from bpy.props import FloatProperty, EnumProperty

offset_value: FloatProperty(
    name="Offset",
    default=0.12,
    min=0.01,
    max=5.0,
    description="Offset"
)

undercut_value: FloatProperty(
    name="Undercut",
    default=0.05,
    min=0.01,
    max=1.0,
    description="Undercut"
)

method: EnumProperty(
    name="Method",
    items=[
        ('1', 'Standard', '1'),
        ('2', 'Fast (Beta)', '2')
    ],
    default='2'
)
```

**Key changes:**
- Use type annotations (`offset_value: FloatProperty(...)`) instead of assignment (`offset_value = bpy.props.FloatProperty(...)`).
- Import property types directly from `bpy.props`.
- Provide `name` and `description` as keyword arguments, not positional.
- This syntax is required for Blender 2.80+ and fully compatible with Blender 4.4[1].
