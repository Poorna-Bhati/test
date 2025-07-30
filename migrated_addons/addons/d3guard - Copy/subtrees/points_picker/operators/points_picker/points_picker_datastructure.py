# Copyright (C) 2018 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# System imports
# NONE!

# Blender imports
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
from bpy.types import Object
from mathutils import Vector, Matrix

# Module imports
# NONE!
from ...functions.common.transform import random_axes_from_normal, r_matrix_from_principal_axes

class D3Point(object):
    ''' Point object '''

    def __init__(self, location:Vector, surface_normal:Vector, view_direction:Vector, label:str="", source_object:Object=None):
        self.label = label
        self.location = location
        self.surface_normal = surface_normal
        self.view_direction = view_direction
        self.source_object = source_object

    def __str__(self):
        return "<D3Point (%0.4f, %0.4f, %0.4f)>" % (self.location.x, self.location.y, self.location.z)

    def __repr__(self):
        return self.__str__()
    
    
    def cache_to_empties(self):
        
        if self.label + "_empty" in bpy.data.objects:
            empty = bpy.data.objects.get(self.label + "_empty")
        else:
            empty = bpy.data.objects.new(self.label + "_empty", None)
            bpy.context.scene.objects.link(empty)
             
        if self.label + "view" in bpy.data.objects:
            view_dir = bpy.data.objects.get(self.label + "view")
        
        else:
            view_dir = bpy.data.objects.new(self.label + "view", None)
            bpy.context.scene.objects.link(view_dir)
        
        if self.source_object != None:
            empty.parent = self.source_object
            
        view_dir.parent = empty
        
        Tmx = Matrix.Translation(self.location)
        X, Y, Z = random_axes_from_normal(self.view_direction)
        Rmx = r_matrix_from_principal_axes(X, Y, Z).to_4x4()
        
        Xview, Yview, Zview = random_axes_from_normal(self.view_direction)
        Rview = r_matrix_from_principal_axes(Xview, Yview, Zview).to_4x4()
        
        empty.matrix_world = Tmx * Rmx
        view_dir.matrix_world = Tmx * Rview
        
        
        return empty, view_dir
    

        
        