'''
Created on Mar 9, 2019
@author: Patrick
patrick@d3tool.com
patrick.moore.bu@gmail.com
'''

import math


import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from bmesh_fns import new_bmesh_from_bmelements, bbox_center, bound_box_bmverts
from offset_utilities import create_dyntopo_meta_scaffold,\
    simple_metaball_offset


def mx_from_principal_axes(X,Y, Z):
    T = Matrix.Identity(3)  #make the columns of matrix U, V, W
    T[0][0], T[0][1], T[0][2]  = X[0] ,Y[0],  Z[0]
    T[1][0], T[1][1], T[1][2]  = X[1], Y[1],  Z[1]
    T[2][0] ,T[2][1], T[2][2]  = X[2], Y[2],  Z[2]
    
    return T

def diamond_circle_grid_element(width, diamond_width):
    
    bme = bmesh.new()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    bmesh.ops.create_grid(bme, x_segments = 3, y_segments = 3, size = width/4)
    
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    inds = [0,2,4,6,8]
    vs = [bme.verts[i] for i in inds]  #the 3 corners and the middle
    
    dw = min(.5 * diamond_width, .45 * width)
    
    geom =  bmesh.ops.bevel(bme, geom = vs, offset = dw, segments = 3, vertex_only = True)
    
    fs = geom['faces']
    bmesh.ops.delete(bme, geom = fs, context = 5)
    
    
    return bme


def diamond_grid_element(width, diamond_width):
    
    bme = bmesh.new()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    bmesh.ops.create_grid(bme, x_segments = 3, y_segments = 3, size = width/4)
    
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    inds = [0,2,4,6,8]
    vs = [bme.verts[i] for i in inds]  #the 3 corners and the middle
    
    dw = min(.5 * diamond_width, .45 * width)
    
    geom =  bmesh.ops.bevel(bme, geom = vs, offset = dw, segments = 1, vertex_only = True)
    
    fs = geom['faces']
    bmesh.ops.delete(bme, geom = fs, context = 5)
    
    
    return bme

def diamond_net_element(width):
    '''
    Dumb because a diamond net is just bmesh.ops.create_grid but
    casting it this way allows it to fit into the same modifier
    pipeline as the others
    '''
    
    bme = bmesh.new()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    bmesh.ops.create_grid(bme, x_segments = 2, y_segments = 2, size = width/2)
    
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    return bme

#https://rechneronline.de/pi/hexagon.php
def hexagon_grid_element(outer_diameter, inner_diameter):
    
    bme = bmesh.new()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    geo_outer = bmesh.ops.create_circle(bme, cap_ends = False, cap_tris = False, segments = 6, diameter = .5 * outer_diameter)
    geo_inner = bmesh.ops.create_circle(bme, cap_ends = False, cap_tris = False, segments = 6, diameter = .5 * inner_diameter)
    
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    for i in range(0, 6):
        
        ind0 = i
        ind1 = int(math.fmod(i + 1, 6))
        ind2 = 6 + int(math.fmod(i + 1, 6))
        ind3 = i + 6 # 6 - 1
        bme.faces.new((bme.verts[ind0], bme.verts[ind1], bme.verts[ind2], bme.verts[ind3]))
    
    return bme
 
 
def hexagon_net_element(diameter):
    
    bme = bmesh.new()
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    geo_outer = bmesh.ops.create_circle(bme, cap_ends = False, cap_tris = False, segments = 6, diameter = .5 * diameter)
    
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    
    return bme 
 
def make_grid_object(outer_diameter, inner_diameter, thickness, grid_repeats, method, add_bevel = True):
    
    
    assert method in {'DIAMOND', 'DIAMOND_CIRCLE', 'HEXAGON', 'HEXAGON_NET', "DIAMOND_NET"}
    if method == "DIAMOND":
        grid_fn = diamond_grid_element
    elif method == "DIAMOND_CIRCLE":
        grid_fn = diamond_circle_grid_element
    elif method == "HEXAGON":
        grid_fn = hexagon_grid_element
       
    elif method == "HEXAGON_NET":
        grid_fn = hexagon_net_element
    elif method == 'DIAMOND_NET':
        grid_fn = diamond_net_element
        
           
    if "NET" in method:
        bme_grid = grid_fn(outer_diameter)
    else:
        bme_grid = grid_fn(outer_diameter, inner_diameter)
    
    me = bpy.data.meshes.new('grid')
    ob = bpy.data.objects.new('Grid', me)
    bme_grid.to_mesh(me)
    
    bme_grid.free()
    
    
    if "HEXAGON" not in method:
        m1 = ob.modifiers.new('XArray', type = 'ARRAY')
        m1.count = grid_repeats
        m1.relative_offset_displace[0] = 1.0
        m1.relative_offset_displace[1] = 0.0
        m1.use_merge_vertices = True
        
        m2 = ob.modifiers.new('YArray', type = 'ARRAY')
        m2.count = grid_repeats
        m2.relative_offset_displace[0] = 0.0
        m2.relative_offset_displace[1] = 1.0
        m2.use_merge_vertices = True
    else:
        m1 = ob.modifiers.new('XArray', type = 'ARRAY')
        m1.count = grid_repeats
        m1.relative_offset_displace[0] = 1.0
        m1.relative_offset_displace[1] = 0.0
        m1.use_merge_vertices = True
        
        m2 = ob.modifiers.new('YArray', type = 'ARRAY')
        m2.count = 2
        m2.relative_offset_displace[0] = .5/float(grid_repeats)
        m2.relative_offset_displace[1] = .75
        m2.use_merge_vertices = True
        
        m3 = ob.modifiers.new('YArray2', type = 'ARRAY')
        m3.count = int(math.ceil(grid_repeats/2))
        m3.relative_offset_displace[0] = 0
        m3.relative_offset_displace[1] = 1 - 1/7  #first person to email me a proof of why this works I will mail you a $100 gift card.
        m3.use_merge_vertices = True
    
    
    if "NET" not in method:
        mthick = ob.modifiers.new('Solid', type = 'SOLIDIFY')
        mthick.thickness = thickness 
    
        if add_bevel:
            modb = ob.modifiers.new('bevel', type = "BEVEL")
            modb.segments = 2
        ob.data.update()
    
    

    return ob
    
    
def honeycomb_bme(bme, hole_radius, offset = .1, bvh = None, ):
    '''
    bme should be a scaffold with approximate vert spacing of 1/2 the
    desired cell major size and then a catmul clark subdivision
    
     Dissolving triangle fans into NGons creates
    cells with radius approximatly the vert spacing of the scaffold
    
    offset is a percentage of the cell size that the the cell will be extruded inward
    
    '''
    
    if bvh == None:
        bvh = BVHTree.FromBMesh(bme)
    
    dissolve_verts = [v for v in bme.verts if len(v.link_edges) > 5]
    
    iters = 0
    while len(dissolve_verts) and iters < 4:
        iters += 1
        bmesh.ops.dissolve_verts(bme, verts = dissolve_verts)
        bme.verts.ensure_lookup_table()
        dissolve_verts = [v for v in bme.verts if len(v.link_edges) > 5]
    
    dissolve_verts = [v for v in bme.verts if len(v.link_edges) > 4]     
    iters = 0
    while len(dissolve_verts) and iters < 4:
        iters += 1
        bmesh.ops.dissolve_verts(bme, verts = dissolve_verts)
        bme.verts.ensure_lookup_table()
        dissolve_verts = [v for v in bme.verts if len(v.link_edges) > 4]
        
    dissolve_verts = [v for v in bme.verts if len(v.link_edges) > 3]     
    iters = 0
    while len(dissolve_verts) and iters < 4:
        iters += 1
        bmesh.ops.dissolve_verts(bme, verts = dissolve_verts)
        bme.verts.ensure_lookup_table()
        dissolve_verts = [v for v in bme.verts if len(v.link_edges) > 3]
          
    dissolve_fs = [f for f in bme.faces if len(f.verts) <= 4]
    bmesh.ops.dissolve_faces(bme, faces = dissolve_fs)
    
    dissolve_vs =  [v for v in bme.verts if len(v.link_edges) == 2]
    bmesh.ops.dissolve_verts(bme, verts = dissolve_vs)
    
    
    
    perim_faces = set()
    for ed in bme.edges:
        if len(ed.link_faces) == 1:
            perim_faces.add(ed.link_faces[0])
            
    
    fs = [f for f in bme.faces if len(f.verts) > 4 and f not in perim_faces]
    geom = bmesh.ops.extrude_discrete_faces(bme, faces = fs)
    
    central_faces = set()
    bme_round_holes = bmesh.new()
    
    for f in geom['faces']:
        if len(f.verts) < 5: continue
        mid = f.calc_center_bounds()
        A = f.calc_area()
        R = math.sqrt(A/math.pi)  #approximate radius
        
        if R < .75 * hole_radius: continue
        
        s_factor = hole_radius/R
        s_factor = min(.8, s_factor)  #don't scale the holes bigger than their container
        s_factor = max(.1, s_factor)
        
        no = f.normal
        v_max = max(f.verts, key = lambda x: (x.co - mid).length)
        X = v_max.co - mid
        X.normalize()
        Y = no.cross(X)
        Rmx = mx_from_principal_axes(X, Y, no)
        Rmx = Rmx.to_4x4()
        snap = bvh.find_nearest(mid)
        T = Matrix.Translation(snap[0])
        
        bmesh.ops.create_circle(bme_round_holes, 
                                cap_ends = True, 
                                cap_tris = False,
                                segments = 6, 
                                diameter = s_factor * R, 
                                matrix = T*Rmx)
        
        
        for v in f.verts:
            #scale verts to make average hole size match the the desired hole size
            delta = v.co - mid
            v.co = mid + s_factor * delta
        
        central_faces.add(f)
    
    
    hole_bme  = new_bmesh_from_bmelements(central_faces)
    
    for f in central_faces:
        bme.faces.remove(f)
    

    return hole_bme, bme_round_holes
    
    
    
    
class D3MODEL_OT_create_grid(bpy.types.Operator):
    """Create 3D Grids and Pattersl"""
    bl_idname = "d3splint.create_3d_grid"
    bl_label = "3D Grid test"
    bl_options = {'REGISTER', 'UNDO'}
    
    method = bpy.props.EnumProperty(
        description="",
        items=(("DIAMOND", "DIAMOND", "DIAMOND"),
               ("DIAMOND_AND_CIRCLE","DIAMOND_AND_CIRCLE", "DIAMOND_AND_CIRCLE"),
               ("HEXAGON","HEXAGON","HEXAGON"),
               ("HEXAGON_NET","HEXAGON_NET","HEXAGON_NET"),
               ("DIAMOND_NET","DIAMOND_NET","DIAMOND_NET")),
        default="DIAMOND",
        )
    
    width = bpy.props.FloatProperty(name = 'element width', default = 4.0, min = .5, max = 10.0)
    hole_width = bpy.props.FloatProperty(name = 'hole width', default = 1.25, min = .25, max = 9.0)
    thickness = bpy.props.FloatProperty(name = 'thickness', default = 2.0, min = .25, max = 9.0)
    grid_repeats = bpy.props.IntProperty(name = 'repeats', default = 10, min = 2, max = 50)
    
    add_bevel = bpy.props.BoolProperty(name = 'add bevel', default = True)
    def execute(self, context):
        
        
        if self.method == "DIAMOND":
            grid_fn = diamond_grid_element
        elif self.method == "DIAMOND_AND_CIRCLE":
            grid_fn = diamond_circle_grid_element
        elif self.method == "HEXAGON":
            grid_fn = hexagon_grid_element
        
        elif self.method == "HEXAGON_NET":
            grid_fn = hexagon_net_element
        elif self.method == 'DIAMOND_NET':
            grid_fn = diamond_net_element
        
           
        if "NET" in self.method:
            bme_grid = grid_fn(self.width)
        else:
            bme_grid = grid_fn(self.width, self.hole_width)

        
        me = bpy.data.meshes.new('grid')
        ob = bpy.data.objects.new('Grid', me)
        bme_grid.to_mesh(me)
        
        bme_grid.free()
        
        context.scene.objects.link(ob)
        
        if self.method not in {"HEXAGON", "HEXAGON_NET"}:
            m1 = ob.modifiers.new('XArray', type = 'ARRAY')
            m1.count = self.grid_repeats
            m1.relative_offset_displace[0] = 1.0
            m1.relative_offset_displace[1] = 0.0
            m1.use_merge_vertices = True
            
            m2 = ob.modifiers.new('YArray', type = 'ARRAY')
            m2.count = self.grid_repeats
            m2.relative_offset_displace[0] = 0.0
            m2.relative_offset_displace[1] = 1.0
            m2.use_merge_vertices = True
        else: #HEXAGON OFFSETS
            m1 = ob.modifiers.new('XArray', type = 'ARRAY')
            m1.count = self.grid_repeats
            m1.relative_offset_displace[0] = 1.0
            m1.relative_offset_displace[1] = 0.0
            m1.use_merge_vertices = True
            
            m2 = ob.modifiers.new('YArray', type = 'ARRAY')
            m2.count = 2
            m2.relative_offset_displace[0] = .5/float(self.grid_repeats)
            m2.relative_offset_displace[1] = .75
            m2.use_merge_vertices = True
            
            m3 = ob.modifiers.new('YArray2', type = 'ARRAY')
            m3.count = int(math.ceil(self.grid_repeats/2))
            m3.relative_offset_displace[0] = 0
            m3.relative_offset_displace[1] = 1 - 1/7  #first person to email me a proof of why this works I will mail you a $100 gift card.
            m3.use_merge_vertices = True
        
        if "NET" not in self.method:
            mthick = ob.modifiers.new('Solid', type = 'SOLIDIFY')
            mthick.thickness = self.thickness 
            
            if self.add_bevel:
                modb = ob.modifiers.new('bevel', type = "BEVEL")
                modb.segments = 2
            ob.data.update()
        
        return {'FINISHED'}
     
 
class D3MODEL_OT_create_honeycomb(bpy.types.Operator):
    """Create Honeycomb on object surface"""
    bl_idname = "d3splint.object_honeycomb_surface"
    bl_label = "Honeycomb Object Suface"
    bl_options = {'REGISTER', 'UNDO'}
    

    hole_spacing = bpy.props.FloatProperty(name = 'element width', default = 4.0, min = 1.5, max = 8.0)
    hole_diameter  = bpy.props.FloatProperty(name = 'hole width', default = 1.0, min = .5, max = 3.0)
    thickness = bpy.props.FloatProperty(name = 'thickness', default = 2.0, min = .25, max = 9.0)
    
    snap = bpy.props.BoolProperty(name ='Snap to Source', default = True)
    snap_offset = bpy.props.FloatProperty(name = 'Snapp Offset', default = 0.0)
    
    def invoke(self, context, event):
        #return context.window_manager.invoke_props_popup(self, event)
        return context.window_manager.invoke_props_dialog(self)
    def execute(self, context):
        
        d_res = 1/self.hole_spacing
        hole_radius = min(.5 * self.hole_spacing, .5 * self.hole_diameter)
        extrude_scale = hole_radius/self.hole_spacing
                
        scaffold = create_dyntopo_meta_scaffold(context.object, d_res, return_type = 'OBJECT')
        mod = scaffold.modifiers.new('Catmul Clark', type = 'SUBSURF')
        
        mod2 = scaffold.modifiers.new('ShrinkWrap', type = 'SHRINKWRAP')
        mod2.target = context.object
        mod2.wrap_method = 'NEAREST_SURFACEPOINT'
        if abs(self.snap_offset) > .1:
            mod2.use_keep_above_surface = True
            mod2.offset = self.snap_offset
        
        me = scaffold.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        bme = bmesh.new()
        bme.from_mesh(me)
        
        hole_bme, round_bme = honeycomb_bme(bme, hole_radius, offset = extrude_scale)
        
        if 'Honeycomb' not in bpy.data.objects:
            me = bpy.data.meshes.new('Honeycomb')
            ob = bpy.data.objects.new('Honeycomb', me)
            bpy.context.scene.objects.link(ob)
            ob.show_wire = True
            ob.show_all_edges = True
            ob.matrix_world = context.object.matrix_world
        else:
            ob = bpy.data.objects.get('Honeycomb')
        bme.to_mesh(me)
        bme.free()
        
        if 'Honeycomb Holes' not in bpy.data.objects:
            me = bpy.data.meshes.new('Honeycomb Holes')
            ob = bpy.data.objects.new('Honeycomb  Holes', me)
            bpy.context.scene.objects.link(ob)
            ob.matrix_world = context.object.matrix_world
        else:
            ob = bpy.data.objects.get('Honeycomb Holes')
        round_bme.to_mesh(me)
        round_bme.free()
        
        #hole_bme.to_mesh(me)
        hole_bme.free()
        
        return {'FINISHED'}  


class D3MODEL_OT_create_metaball_honeycomb(bpy.types.Operator):
    """Create Bmesh Honeycomb"""
    bl_idname = "d3splint.object_honeycomb_surface"
    bl_label = "Honeycomb Object Suface"
    bl_options = {'REGISTER', 'UNDO'}
    

    hole_spacing = bpy.props.FloatProperty(name = 'element width', default = 4.0, min = 1.5, max = 8.0)
    hole_diameter  = bpy.props.FloatProperty(name = 'hole width', default = 1.0, min = .5, max = 3.0)
    thickness = bpy.props.FloatProperty(name = 'thickness', default = 2.0, min = .25, max = 9.0)
    
    snap = bpy.props.BoolProperty(name ='Snap to Source', default = True)
    snap_offset = bpy.props.FloatProperty(name = 'Snapp Offset', default = 0.0)
    
    def invoke(self, context, event):
        #return context.window_manager.invoke_props_popup(self, event)
        return context.window_manager.invoke_props_dialog(self)
    def execute(self, context):
        
        d_res = 1/self.hole_spacing
        hole_radius = min(.5 * self.hole_spacing, .5 * self.hole_diameter)
        extrude_scale = hole_radius/self.hole_spacing
                
        scaffold = create_dyntopo_meta_scaffold(context.object, d_res, return_type = 'OBJECT')
        mod = scaffold.modifiers.new('Catmul Clark', type = 'SUBSURF')
        
        mod2 = scaffold.modifiers.new('ShrinkWrap', type = 'SHRINKWRAP')
        mod2.target = context.object
        mod2.wrap_method = 'NEAREST_SURFACEPOINT'
        if abs(self.snap_offset) > .1:
            mod2.use_keep_above_surface = True
            mod2.offset = self.snap_offset
        
        me = scaffold.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        bme = bmesh.new()
        bme.from_mesh(me)
        
        hole_bme, round_bme = honeycomb_bme(bme, hole_radius, offset = extrude_scale)
        
        if 'Honeycomb' not in bpy.data.objects:
            me = bpy.data.meshes.new('Honeycomb')
            ob = bpy.data.objects.new('Honeycomb', me)
            bpy.context.scene.objects.link(ob)
            ob.show_wire = True
            ob.show_all_edges = True
            ob.matrix_world = context.object.matrix_world
        else:
            ob = bpy.data.objects.get('Honeycomb')
        bme.to_mesh(me)
        bme.free()
        
        if 'Honeycomb Holes' not in bpy.data.objects:
            me = bpy.data.meshes.new('Honeycomb Holes')
            ob = bpy.data.objects.new('Honeycomb  Holes', me)
            bpy.context.scene.objects.link(ob)
            ob.matrix_world = context.object.matrix_world
        else:
            ob = bpy.data.objects.get('Honeycomb Holes')
        round_bme.to_mesh(me)
        round_bme.free()
        
        #hole_bme.to_mesh(me)
        hole_bme.free()
        
        return {'FINISHED'}  
 
 
class D3MODEL_OT_create_metaball_grid(bpy.types.Operator):
    """Create Bmesh Honeycomb"""
    bl_idname = "d3model.object_volumetric_grid"
    bl_label = "Volumetric Grid Object"
    bl_options = {'REGISTER', 'UNDO'}
    

    hole_diameter  = bpy.props.FloatProperty(name = 'Hole Diameter', default = 6.0, min = .5, max = 10.0)
    wall_thickness = bpy.props.FloatProperty(name = 'Wall Thicknes', default = 2.0, min = .25, max = 9.0)
    
    method = bpy.props.EnumProperty(
        description="",
        items=(("HEXAGON_NET","HEXAGON_NET","HEXAGON_NET"),
               ("DIAMOND_NET","DIAMOND_NET","DIAMOND_NET")),
        default="HEXAGON_NET",
        )
    
    grid_repeats = bpy.props.IntProperty(name = 'Repeats', default = 10, min = 2, max = 50)
    resolution = bpy.props.FloatProperty(name = 'Mesh Resolution', default = .3, min = .2, max = 3.0)
    
    
    def invoke(self, context, event):
        #return context.window_manager.invoke_props_popup(self, event)
        return context.window_manager.invoke_props_dialog(self)
    
    
    def execute(self, context):
        
        
        outer_diameter = self.hole_diameter + self.wall_thickness
        ob = make_grid_object(outer_diameter, 1.0, 1.0, self.grid_repeats, self.method, False)
        
        context.scene.objects.link(ob)
        context.scene.update()
        
        
        
        me = ob.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
        
        
        bme = bmesh.new()
        bme.from_mesh(me)
        bme.verts.ensure_lookup_table()
        bme.edges.ensure_lookup_table()
        bme.faces.ensure_lookup_table()
        
        bounds = bound_box_bmverts(bme.verts[:])
        center = bbox_center(bounds)
        print('TRANSFORMING THE GRID')
        print(center)
        T = Matrix.Translation(center)
        imx = T.inverted()
        bme.transform(imx)
        
        edge_shrink = .2
        
        metadata = bpy.data.metaballs.new('Meta Grid')
        metadata.resolution = self.resolution
        meta_obj = bpy.data.objects.new('Meta Grid', metadata)
        
        for ed in bme.edges:
            X = ed.verts[1].co - ed.verts[0].co
            r = (ed.verts[1].co - ed.verts[0].co).length
            X.normalize()
            Z = Vector((0,0,1))
            Y = Z.cross(X)
            R = Matrix.Identity(3)  #make the columns of matrix U, V, W
            R[0][0], R[0][1], R[0][2]  = X[0] ,Y[0],  Z[0]
            R[1][0], R[1][1], R[1][2]  = X[1], Y[1],  Z[1]
            R[2][0] ,R[2][1], R[2][2]  = X[2], Y[2],  Z[2]
            quat = R.to_4x4().to_quaternion()
            center = .5 * (ed.verts[0].co + ed.verts[1].co)

            
            cube = metadata.elements.new(type = 'CUBE')
            cube.co = center + 5.0 * Z
        
            cube.size_x = .5 * r
            cube.size_y = .5 * (self.wall_thickness - .2)
            cube.size_z = 5.0
            cube.radius = 0.2
            cube.stiffness = 1.0
            cube.rotation = quat
        
        context.scene.objects.link(meta_obj)
        return {'FINISHED'}  
     
def register():
    bpy.utils.register_class(D3MODEL_OT_create_grid)
    bpy.utils.register_class(D3MODEL_OT_create_honeycomb)
    bpy.utils.register_class(D3MODEL_OT_create_metaball_grid)
    
     
def unregister():
    bpy.utils.unregister_class(D3MODEL_OT_create_grid)
    bpy.utils.unregister_class(D3MODEL_OT_create_honeycomb)
    bpy.utils.unregister_class(D3MODEL_OT_create_metaball_grid)
    

# ---- Perplexity API Suggested Migrations ----
In Blender 4.4, the old property registration functions like `bpy.props.FloatProperty`, `IntProperty`, `BoolProperty`, and `EnumProperty` are still used, but the syntax for declaring them has changed. Properties must now be defined as class annotations using type hints, not as direct assignments. Here is the corrected code block for Blender 4.4+:

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    method: bpy.props.EnumProperty(
        name="Method",
        items=[
            ('OPTION1', "Option 1", ""),
            ('OPTION2', "Option 2", ""),
        ],
        default='OPTION1'
    )
    width: bpy.props.FloatProperty(name='element width', default=4.0, min=0.5, max=10.0)
    hole_width: bpy.props.FloatProperty(name='hole width', default=1.25, min=0.25, max=9.0)
    thickness: bpy.props.FloatProperty(name='thickness', default=2.0, min=0.25, max=9.0)
    grid_repeats: bpy.props.IntProperty(name='repeats', default=10, min=2, max=50)
    add_bevel: bpy.props.BoolProperty(name='add bevel', default=True)
    hole_spacing: bpy.props.FloatProperty(name='element width', default=4.0, min=1.5, max=8.0)
    hole_diameter: bpy.props.FloatProperty(name='hole width', default=1.0, min=0.5, max=3.0)
    snap: bpy.props.BoolProperty(name='Snap to Source', default=True)
```

**Key changes:**
- Use **type annotations** (the colon `:` syntax) instead of assignment (`=`) for property definitions in classes derived from `bpy.types.PropertyGroup`[3][4].
- Define all properties inside a class, not at the module level.
- EnumProperty now requires an `items` argument.

This is the Blender 4.4+ compatible way to declare custom properties for use in panels, operators, etc.
In **Blender 4.4**, the old style of defining properties directly as class variables using `bpy.props` is deprecated. Instead, you should use type annotations and assign the property to the class attribute, typically within a class derived from `bpy.types.PropertyGroup`, `bpy.types.Operator`, or `bpy.types.Panel`. Here is the **corrected code block** for Blender 4.4+:

```python
import bpy

class MyProperties(bpy.types.PropertyGroup):
    snap_offset: bpy.props.FloatProperty(
        name='Snapp Offset',
        default=0.0
    )
    hole_spacing: bpy.props.FloatProperty(
        name='element width',
        default=4.0,
        min=1.5,
        max=8.0
    )
    hole_diameter: bpy.props.FloatProperty(
        name='Hole Diameter',
        default=6.0,
        min=0.5,
        max=10.0
    )
    thickness: bpy.props.FloatProperty(
        name='thickness',
        default=2.0,
        min=0.25,
        max=9.0
    )
    snap: bpy.props.BoolProperty(
        name='Snap to Source',
        default=True
    )
    wall_thickness: bpy.props.FloatProperty(
        name='Wall Thicknes',
        default=2.0,
        min=0.25,
        max=9.0
    )
    method: bpy.props.EnumProperty(
        name='Method',
        items=[
            ('OPTION1', 'Option 1', ''),
            ('OPTION2', 'Option 2', ''),
        ]
    )
    grid_repeats: bpy.props.IntProperty(
        name='Repeats',
        default=10,
        min=2,
        max=50
    )
```

**Key changes:**
- Use **type annotations** (the colon `:`) instead of assignment (`=`) for property definitions.
- Define properties inside a class derived from `bpy.types.PropertyGroup` (or another appropriate Blender type).
- Register the property group and assign it to a context (e.g., `bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyProperties)`), if needed for use.

This is the Blender 4.4+ compatible way to define custom properties[2].
In **Blender 4.4**, property definitions must be declared as class attributes within a subclass of a Blender type (such as bpy.types.PropertyGroup, bpy.types.Operator, etc.), not as standalone assignments. The use of bpy.props.FloatProperty directly in a variable assignment is deprecated.

**Migrate your code as follows:**

```python
import bpy
from bpy.props import FloatProperty

class MyProperties(bpy.types.PropertyGroup):
    resolution: FloatProperty(
        name='Mesh Resolution',
        default=0.3,
        min=0.2,
        max=3.0
    )
```

**Key changes:**
- Define the property as a class attribute with a colon (:) and not as a direct assignment.
- Place the property inside a subclass of a Blender type (e.g., PropertyGroup, Operator, Panel, etc.).
- Register the PropertyGroup and assign it to a context (e.g., bpy.types.Scene) as needed.

This is the Blender 4.4 compatible way to define custom properties[2].
