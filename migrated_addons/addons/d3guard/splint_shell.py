import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix, Color, Quaternion, kdtree
from bpy.props import FloatProperty, BoolProperty, IntProperty, EnumProperty
from odcutils import get_settings
from subtrees.metaballs.vdb_tools import remesh_bme
import splint_cache

def old_method(context, shell_patch, radius, resolution):
    
    R_prime = 1/.901 * (radius + .0219)
    
    
    bme = bmesh.new()
    bme.from_object(shell_patch, context.scene)
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    
    meta_data = bpy.data.metaballs.new('Splint Shell')
    meta_obj = bpy.data.objects.new('Meta Splint Shell', meta_data)
    meta_data.resolution = resolution
    meta_data.render_resolution = resolution
    context.scene.objects.link(meta_obj)
    
    perimeter_edges = [ed for ed in bme.edges if len(ed.link_faces) == 1]
    perim_verts = set()
    for ed in perimeter_edges:
        perim_verts.update([ed.verts[0], ed.verts[1]])
        
    perim_verts = list(perim_verts)
    stroke = [v.co for v in perim_verts]
    print('there are %i non man verts' % len(stroke))                                          
    kd = kdtree.KDTree(len(stroke))
    for i in range(0, len(stroke)-1):
        kd.insert(stroke[i], i)
    kd.balance()
    perim_set = set(perim_verts)
    for v in bme.verts:
        if v in perim_set: 
            continue
        
        loc, ind, r = kd.find(v.co)
        
        if r and r < .8 * R_prime:
            
            mb = meta_data.elements.new(type = 'BALL')
            mb.co = v.co #+ #(R_prime - r) * v.normal
            mb.radius = .5 * r

        elif r and r < 0.2 * R_prime:
            continue
        else:
            mb = meta_data.elements.new(type = 'BALL')
            mb.radius = R_prime
            mb.co = v.co
        
    
    context.scene.update()
    
    me = meta_obj.to_mesh(context.scene, apply_modifiers = True, settings = 'PREVIEW')
    bme_meta = bmesh.new()
    bme_meta.from_mesh(me)
    
    bpy.data.meshes.remove(me) #get rid of that
    
        
    context.scene.objects.unlink(meta_obj)
    bpy.data.objects.remove(meta_obj)
    bpy.data.metaballs.remove(meta_data)    
        
    bme.free()

    return bme_meta

def new_method(context, shell_patch, radius):
    

    
    bme = bmesh.new()
    bme.from_object(shell_patch, context.scene)
    
    bme.verts.ensure_lookup_table()
    bme.edges.ensure_lookup_table()
    bme.faces.ensure_lookup_table()
    
    #normals are flipped because the shell patch normals point outward
    for f in bme.faces:
        f.normal_flip()
        
    for v in bme.verts:
        v.normal_update()
        
    old_verts = bme.verts[:]
    new_geom = bmesh.ops.extrude_face_region(bme, geom = bme.faces[:])  
    
    verts = [ele for ele in new_geom['geom'] if isinstance(ele, bmesh.types.BMVert)]
    
    for v in verts:
        v.co +=  .5 * radius * v.normal
        
    for v in old_verts:
        v.co +=  radius * v.normal
        
    bme_remesh = remesh_bme(bme, 
              isovalue = 0.0, 
              adaptivity = 0.0, 
              only_quads = False, 
              voxel_size = .25,
              filter_iterations = 1,
              filter_width = 2,
              filter_sigma = 1.0,
              grid = None,
              write_method = 'FAST')  
    
    bme.free() 
    return bme_remesh

    
class D3SPLINT_OT_create_splint_shell(bpy.types.Operator):
    """Create Offset Surface from mesh"""
    bl_idname = "d3splint.create_splint_shell"
    bl_label = "Create Splint Shell"
    bl_options = {'REGISTER', 'UNDO'}
    
    jaw_mode = EnumProperty(default = 'MAX', items = (('MAX','MAX','MAX'),('MAND','MAND','MAND')))
    
    radius = FloatProperty(default = 1.5, min = .6, max = 4, description = 'Thickness of splint', name = 'Thickness')
    new_method = BoolProperty(default = True, description = 'Use new method for offset')
    
    resolution = FloatProperty(default = .4, min = .1, max = 2.0, description = 'Small values result in more dense meshes and longer processing times, but may be needed for experimental workflows')
    finalize = BoolProperty(default = False, description = 'Will convert meta to mesh and remove meta object')
    
    @classmethod
    def poll(cls, context):
        if "Max Patch" in context.scene.objects or "Mand Patch" in context.scene.objects:
            return True
        else:
            return False
        
    def execute(self, context):
        
        #fit data from inputs to outputs with metaball
        #r_final = .901 * r_input - 0.0219
        
        #rinput = 1/.901 * (r_final + .0219)
        
        
        
        
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        
        if self.jaw_mode == 'MAX':
            shell_patch = bpy.data.objects.get('Max Patch')
        else:
        
            shell_patch = bpy.data.objects.get('Mand Patch')
        mx = shell_patch.matrix_world
        
        if self.new_method:
            bme_shell = new_method(context, shell_patch, self.radius)
        else:
            bme_shell = old_method(context, shell_patch, self.radius, self.resolution)
            
        
        mat = bpy.data.materials.get("Splint Material")
        if mat is None:
            # create material
            mat = bpy.data.materials.new(name="Splint Material")
            mat.diffuse_color = get_settings().def_splint_color
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            mat.alpha = .4
            
        if 'Splint Shell_' + self.jaw_mode not in bpy.data.objects:
            me = bpy.data.meshes.new('Splint Shell_' + self.jaw_mode)
            new_ob = bpy.data.objects.new('Splint Shell_' + self.jaw_mode, me)
            context.scene.objects.link(new_ob)
            new_ob.matrix_world = mx
            new_ob.data.materials.append(mat)
            
            cons = new_ob.constraints.new('COPY_TRANSFORMS')
            if self.jaw_mode == 'MAX':
                cons.target = bpy.data.objects.get(splint.max_model)
            else:
                cons.target = bpy.data.objects.get(splint.mand_model)
            
        else:
            new_ob = bpy.data.objects.get('Splint Shell_' + self.jaw_mode)
            
            
            
            to_remove = []
            for mod in new_ob.modifiers:
                if mod.name in {'Remove Teeth', 'Passive Fit'}:
                    to_remove += [mod]
                
            for mod in to_remove:
                new_ob.modifiers.remove(mod)
            
        
        bme_shell.to_mesh(new_ob.data)
        
        
        splint_cache.write_shell_cache(bme_shell)
        if 'shell_backup' in bpy.data.meshes:
            shell_back = bpy.data.meshes.get('shell backup')
        else:
            shell_back = bpy.data.meshes.new('shell backup')
            shell_back.use_fake_user = True
        bme_shell.to_mesh(shell_back)
        #bme_shell.free()  #dont free it because it's cached
        
        #tracking.trackUsage("D3Splint:OffsetShell",self.radius)   
        n = context.scene.odc_splint_index
        splint = context.scene.odc_splints[n]
        
        if self.jaw_mode == 'MAX':
            splint.max_shell_complete = True
            splint.max_shell = new_ob.name
            splint.max_shell_thickness = self.radius
        else:
            splint.mand_shell_complete = True
            splint.mand_shell = new_ob.name
            splint.mand_shell_thickness = self.radius
            
        splint.ops_string += self.jaw_mode + 'Splint Shell:'
        return {'FINISHED'}
    
    def invoke(self, context, event):
        settings = get_settings()
        self.radius = settings.def_shell_thickness
        return context.window_manager.invoke_props_dialog(self)
        #return context.window_manager.invoke_props_popup(self, event)
    
    def draw(self,context):
        
        layout = self.layout
        
        #row = layout.row()
        #row.label(text = "%i metaballs will be added" % self.n_verts)
        
        #if self.n_verts > 10000:
        #    row = layout.row()
        #    row.label(text = "WARNING, THIS SEEMS LIKE A LOT")
        #    row = layout.row()
        #    row.label(text = "Consider CANCEL/decimating more or possible long processing time")
        
        row = layout.row()
        row.prop(self, "radius")
        row = layout.row()
        row.prop(self, "new_method")
        
        #row = layout.row()
        #row.prop(self, "show_advanced")
        
        #if self.show_advanced:
        #    row = layout.row()
        #    row.prop(self, "resolution")
        
def register():
    bpy.utils.register_class(D3SPLINT_OT_create_splint_shell)
    
    
def unregister():
    bpy.utils.unregister_class(D3SPLINT_OT_create_splint_shell)