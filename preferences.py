import bpy
import rna_keymap_ui

from . import addon_updater_ops
from .keymap import get_hotkey_entry_item


# addon Preferences
class CAM_MANAGER_OT_renaming_preferences(bpy.types.AddonPreferences):
    """Contains the blender addon preferences"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__  ### __package__ works on multifile and __name__ not

    # addon updater preferences

    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )
    updater_intrval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_intrval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31
    )
    updater_intrval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23
    )
    updater_intrval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59
    )

    def draw(self, context):
        ''' simple preference UI to define custom inputs and user preferences'''
        layout = self.layout

        # works best if a column, or even just self.layout
        mainrow = layout.row()

        box = layout.box()
        col = box.column()

        wm = context.window_manager
        kc = wm.keyconfigs.addon
        km = kc.keymaps['3D View']

        kmis = []
        # Operators
        kmis.append(get_hotkey_entry_item(km, 'cam_manager.cycle_cameras_next'))
        kmis.append(get_hotkey_entry_item(km, 'cam_manager.cycle_cameras_backward'))
        # Menus and Pies
        kmis.append(get_hotkey_entry_item(km, 'wm.call_panel', 'OBJECT_PT_camera_manager_popup'))
        kmis.append(get_hotkey_entry_item(km, 'wm.call_menu_pie', 'CAMERA_MT_pie_menu'))

        for kmi in kmis:
            if kmi:
                col.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)

            else:
                col.label(text="No hotkey entry found")
                col.operator("cam_manager.add_hotkey", text="Add hotkey entry", icon='ADD')

        # updater draw function
        # could also pass in col as third arg
        addon_updater_ops.update_settings_ui(self, context)


classes = (
    CAM_MANAGER_OT_renaming_preferences,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
