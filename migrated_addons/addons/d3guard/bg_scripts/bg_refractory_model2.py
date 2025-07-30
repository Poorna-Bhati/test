import time
import math

import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
import bmesh
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
import odcutils
from bmesh_fns import bmesh_loose_parts

#arguments from bg operator
#b_radius
#c_radius
#d_radius
#resoultion
#use_drillcomp
#max_blockout
#jaw_type
#model_name

#objects needed from blender
#Axis
#Model
#Trimmed Model
#Perim Model

#Axis = appendFrom("Objects", "Insertion Axis")
#Model = appendFrom("Objects", model_name)
#Trim = appendFrom("Objects", "Trimmed_Model")
#Perim = appendFrom("Objects", "Perim Model")

Model = bpy.data.objects.get(model_name)
mod = Model.modifiers.new('Remesh', type = 'REMESH')
    
me = Model.to_mesh(bpy.context.scene, apply_modifiers = True, )

new_ob = bpy.data.objects.new('Remeshed', me)

data_blocks = [new_ob]