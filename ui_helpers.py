import bpy

class CAM_MANAGER_OT_open_preferences(bpy.types.Operator):
    """Open the addon preferences and navigate to a specific tab."""
    bl_idname = "cam_manager.open_preferences"
    bl_label = "Open Addon preferences"
    bl_description = "Open the Simple Camera Manager addon preferences"

    addon_name: bpy.props.StringProperty()
    prefs_tabs: bpy.props.StringProperty()

    def execute(self, context):

        bpy.ops.screen.userpref_show()

        bpy.context.preferences.active_section = 'ADDONS'
        bpy.data.window_managers["WinMan"].addon_search = self.addon_name

        prefs = context.preferences.addons[__package__].preferences
        prefs.prefs_tabs = self.prefs_tabs

        import addon_utils
        # Ensure `addons_fake_modules` is populated before reading from it
        # (mirrors Blender's own PREFERENCES_OT_addon_expand implementation).
        # Keyed by the addon's actual runtime module name (e.g.
        # "bl_ext.<repo>.simple_camera_manager" for an installed extension),
        # same as the preferences lookup above — not the bare package id,
        # which never matches once installed through the Extensions platform.
        addon_utils.modules(refresh=False)
        mod = addon_utils.addons_fake_modules.get(__package__)

        if mod:
            mod.bl_info['show_expanded'] = True

            # Find User Preferences area and redraw it
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'USER_PREFERENCES':
                        area.tag_redraw()

        return {'FINISHED'}

classes = (
    CAM_MANAGER_OT_open_preferences,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if hasattr(cls, 'bl_rna'):
            unregister_class(cls)
