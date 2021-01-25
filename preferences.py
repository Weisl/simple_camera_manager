import bpy
import rna_keymap_ui

from .keymap import get_hotkey_entry_item


# addon Preferences
class VIEW3D_OT_renaming_preferences(bpy.types.AddonPreferences):
    """Contains the blender addon preferences"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__  ### __package__ works on multifile and __name__ not

    def draw(self, context):
        ''' simple preference UI to define custom inputs and user preferences'''
        layout = self.layout

        box = layout.box()
        split = box.split()
        col = box.column()

        wm = context.window_manager
        kc = wm.keyconfigs.addon
        km = kc.keymaps['3D View']

        kmis = []
        kmis.append(get_hotkey_entry_item(km, 'utilities.cycle_cameras_next'))
        kmis.append(get_hotkey_entry_item(km, 'utilities.cycle_cameras_backward'))
        kmis.append(get_hotkey_entry_item(km, 'VIEW3D_PT_tools_type_suffix'))


        for kmi in kmis:
            if kmi:
                col.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
            else:
                col.label(text="No hotkey entry found")
                col.operator("utilities.add_hotkey", text="Add hotkey entry", icon='ADD')

classes = (
    VIEW3D_OT_renaming_preferences,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
