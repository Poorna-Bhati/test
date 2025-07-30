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


class POINTSPICKER_PT_preferences(AddonPreferences):
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
To migrate your property definitions from Blender 2.79 to Blender 4.4, replace the deprecated direct assignment of properties with the recommended use of type annotations inside a class derived from bpy.types.PropertyGroup. Register the class and use bpy.props in the annotation, not as a direct assignment.

**Blender 4.4 compatible code:**

```python
import bpy

class MyAddonProperties(bpy.types.PropertyGroup):
    auto_check_update: bpy.props.BoolProperty(
        name="Auto Check Update",
        description="Automatically check for updates",
        default=False
    )
    updater_interval_months: bpy.props.IntProperty(
        name="Updater Interval Months",
        description="Months between update checks",
        default=0
    )
    updater_interval_days: bpy.props.IntProperty(
        name="Updater Interval Days",
        description="Days between update checks",
        default=0
    )
    updater_interval_hours: bpy.props.IntProperty(
        name="Updater Interval Hours",
        description="Hours between update checks",
        default=0
    )
    updater_interval_minutes: bpy.props.IntProperty(
        name="Updater Interval Minutes",
        description="Minutes between update checks",
        default=0
    )

# Register the property group (required)
bpy.utils.register_class(MyAddonProperties)

# Assign to a context, e.g., scene
bpy.types.Scene.my_addon = bpy.props.PointerProperty(type=MyAddonProperties)
```

**Key changes:**
- Use type annotations (`:`) instead of direct assignment (`=`).
- Define properties inside a `PropertyGroup` subclass.
- Register the class and assign it as a `PointerProperty` to a Blender data block (e.g., `Scene`).

This approach is required for Blender 2.80+ and fully compatible with Blender 4.4[2][3].
