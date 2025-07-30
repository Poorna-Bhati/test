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

# Blender imports
import bpy
bpy.utils.expose_bundled_modules()  # Blender 4.4 requirement
from bpy.types import AddonPreferences
from bpy.props import *

# updater import
from .. import addon_updater_ops


class WAXDROP_PT_preferences(AddonPreferences):
    bl_idname = __package__[:__package__.index(".lib")]

	# addon updater preferences
    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)
    updater_intrval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0, min=0)
    updater_intrval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7, min=0)
    updater_intrval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        min=0, max=23,
        default=0)
    updater_intrval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        min=0, max=59,
        default=0)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        # updater draw function
        addon_updater_ops.update_settings_ui(self,context)

# ---- Perplexity API Suggested Migrations ----
In Blender 4.4, the old style of defining properties directly with assignment (e.g., bpy.props.BoolProperty) at the module level is deprecated. Properties must now be defined as class annotations using Python's type hinting syntax within a bpy.types.PropertyGroup or similar class.

Here is the corrected code block for Blender 4.4:

```python
import bpy

class MyPropertyGroup(bpy.types.PropertyGroup):
    auto_check_update: bpy.props.BoolProperty()
    updater_intrval_months: bpy.props.IntProperty()
    updater_intrval_days: bpy.props.IntProperty()
    updater_intrval_hours: bpy.props.IntProperty()
    updater_intrval_minutes: bpy.props.IntProperty()
```

- Use **class annotations** (the colon syntax) instead of assignment.
- Place properties inside a subclass of **bpy.types.PropertyGroup** (or another appropriate Blender type).
- Register the class with `bpy.utils.register_class(MyPropertyGroup)` as needed in your add-on.

This approach is required for Blender 2.80+ and fully compatible with Blender 4.4[1][3][5].
