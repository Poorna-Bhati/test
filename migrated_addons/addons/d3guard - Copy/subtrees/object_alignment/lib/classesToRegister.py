# Copyright (C) 2019 Christopher Gearhart
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

from .reportError import *
from .preferences import *
from ..ui import *
from ..operators import *

classes = [
    ObjectAlignmentPreferences,
    OBJECT_OT_icp_align,
    OBJECT_OT_icp_align_feedback,
    OBJECT_OT_align_add_include,
    OBJECT_OT_align_add_exclude,
    OBJECT_OT_align_include_clear,
    OBJECT_OT_align_exclude_clear,
    OBJECT_OT_align_pick_points,
    VIEW3D_PT_object_alignment,
]