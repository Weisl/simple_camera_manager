bl_info = {
    "name": "Cam-Manager",
    "author": "Matthias Patscheider",
    "version": (1, 2, 0),
    "blender": (4, 0, 0),
    "location": "Shift + C > (Cam Overview Panel), Alt + C > (Cam Adjustment Panel), Properties Panel > Scene > Quick Overview ",
    "description": "Tools for managing multiple cameras",
    "doc_url": "https://weisl.github.io/Cam-Manager_Overview/",
    "tracker_url": "https://github.com/Weisl/Cam-Manager/issues",
    "category": "3D View",
}

# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(camera_controlls)
    importlib.reload(dolly_zoom_modal)
    importlib.reload(camera_gizmos)
    importlib.reload(keymap)
    importlib.reload(preferences)
    importlib.reload(ui)
    importlib.reload(addon_updater_ops)
    importlib.reload(pie_menu)

else:
    from . import camera_controlls
    from . import dolly_zoom_modal
    from . import camera_gizmos
    from . import ui
    from . import keymap
    from . import preferences
    from . import addon_updater_ops
    from . import pie_menu


import bpy

files = [
    camera_controlls,
    dolly_zoom_modal,
    ui,
    pie_menu,
    camera_gizmos,

    # keymap and preferences should be last
    keymap,
    preferences
]

# def update_show_gizmo(self, context):
#     scene = bpy.types.Scene
#     # Set Gizmo to be visibile during the modal operation. Dirty!
#     prefs = context.preferences.addons[__package__].preferences
#     prefs.show_dolly_gizmo = scene.toggle_dolly_gizmo
#

def register():
    # register variables saved in the blender scene
    # scene = bpy.types.Scene
    # scene.toggle_dolly_gizmo = bpy.props.BoolProperty(name='Dolly Zoom', description='Show the dolly gizmo', default=False, update=update_show_gizmo)


    # addon updater code and configurations
    # in case of broken version, try to register the updater first
    # so that users can revert back to a working version
    addon_updater_ops.register(bl_info)

    for file in files:
        file.register()


def unregister():
    # scene = bpy.types.Scene
    # del scene.show_dolly_gizmo

    for file in files.reverse():
        file.unregister()

    # addon updater unregister
    addon_updater_ops.unregister()
