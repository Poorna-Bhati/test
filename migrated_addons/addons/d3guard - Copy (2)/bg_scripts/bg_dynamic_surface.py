import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
import time
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from articulator import load_driver_namespace, occlusal_surface_frame_change


#Passed Python data
#opposing_name
#jaw_type
#ops_string

#Linked Objects
#RCP, LCP
#GUIDE TABLE
#Articulator
#Opposing
#Dynamic Occlusal Surface
#append_from("Object", 'LCP')
#append_from("Object", 'RCP')
#append_from("Object", 'Incisal Guide Table')
#append_from("Object", 'Articulator')
#append_from("Object", opposing_name)
#append_from("Object", "Dynamic Occlusal Surface")
#append_from("Object", "Splint Shell")

#actually we don't need a frame change handler
#because we are stepping the animation
#manually with a for loop
#so we will use this as the frame change


for ob in bpy.data.objects:
    print(ob.name)
#remove the handler which is not needed
handlers = [hand.__name__ for hand in bpy.app.handlers.frame_change_pre]
if occlusal_surface_frame_change.__name__  in handlers:
    print('remove handler!')
    bpy.app.handlers.frame_change_pre.remove(occlusal_surface_frame_change)
        
plane = bpy.data.objects.get('Dynamic Occlusal Surface')
opp_jaw_model = bpy.data.objects.get(opposing_name)
print('got some models')
def occlusal_surface_frame_change_manual():
    
    mx_jaw = opp_jaw_model.matrix_world
    mx_pln = plane.matrix_world
    imx_j = mx_jaw.inverted()
    imx_p = mx_pln.inverted()
    
    if jaw_type == 'MAXILLA':
        Z = Vector((0,0,1))
    else:
        Z = Vector((0,0,-1))
    for v in plane.data.vertices:
        
        a = mx_pln * v.co
        b = mx_pln * (v.co + 10 * Z)
        
        hit = opp_jaw_model.ray_cast(imx_j * a, imx_j * b - imx_j * a)
        if hit[0]:
            #check again
            hit2 = opp_jaw_model.ray_cast(hit[1], imx_j * b - hit[1])
            
            if hit2[0]:
                v.co = imx_p * mx_jaw * hit2[1]
            else:
                v.co = imx_p * mx_jaw * hit[1]


bvh = BVHTree.FromObject(opp_jaw_model, bpy.context.scene)
def occlusal_surface_frame_change_bvh():
    
    mx_jaw = opp_jaw_model.matrix_world
    mx_pln = plane.matrix_world
    imx_j = mx_jaw.inverted()
    imx_p = mx_pln.inverted()
    
    #if jaw_type == 'MAXILLA':
    #    Z = Vector((0,0,1))
    #else:
    #    Z = Vector((0,0,-1))
    
    Z = Vector((0,0,1))  #the surface is flipped for max/mand so always ray casting in local positive Z of occlusal plane
    for v in plane.data.vertices:
        
        a = mx_pln * v.co
        b = mx_pln * (v.co + 10 * Z)
        
        hit = bvh.ray_cast(imx_j * a, imx_j * b - imx_j * a)
        if hit[0]:
            #check again
            hit2 = bvh.ray_cast(hit[0], imx_j * b - hit[0])
            
            if hit2[0]:
                v.co = imx_p * mx_jaw * hit2[0]
            else:
                v.co = imx_p * mx_jaw * hit[0]                
                
Shell = bpy.data.objects.get('Splint Shell')
Shell.data.update()
print('doing some stuff to the surface')
#truncate the occlusal surface to just what's beneath the shell
if Shell:    
    if len(Shell.modifiers):
        old_me = Shell.data
        new_me = Shell.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
        Shell.modifiers.clear()
        Shell.data = new_me
        bpy.data.meshes.remove(old_me)
        
    Shell.data.update()
    bpy.context.scene.update()
    
    bme = bmesh.new()
    bme.from_mesh(plane.data)
    bme.verts.ensure_lookup_table()
    
    #reset occusal plane if animate articulator has happened already
    if "AnimateArticulator" in ops_string:
        for v in bme.verts:
            v.co[2] = 0
        
    mx_p = plane.matrix_world
    imx_p = mx_p.inverted()
    
    mx_s = Shell.matrix_world
    imx_s = mx_s.inverted()
    
    keep_verts = set()
    if jaw_type == 'MAXILLA':
        Z = Vector((0,0,1))
    else:
        Z = Vector((0,0,-1))
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
    bme.to_mesh(plane.data)
    
print('starting the animation')


total_start = time.time()          
for n in range(0, bpy.context.scene.frame_end):
    #because of the circular reference of Lcondyle to Rcondyle
    #the scene frame must be set twice
    start = time.time()
    bpy.context.scene.frame_set(n)
    bpy.context.scene.frame_set(n)
    occlusal_surface_frame_change_bvh()
    finish = time.time()
    print('Frame rate: %f fps' % round(1/(finish-start)))
total_finish = time.time()
total_time = total_finish - total_start
print('Took %f seconds for whole animation' % (total_time))
print('average fps = %f' % round(bpy.context.scene.frame_end/total_time))


final_me = plane.to_mesh(bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
new_ob = bpy.data.objects.new('BG Dyn Plane', final_me)
data_blocks = [new_ob] 
    