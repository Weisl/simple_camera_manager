bl_info = {
    "name": "simple_camera_manager",
    "author": "Matthias Patscheider",
    "version": (1, 2, 0),
    "blender": (4, 2, 0),
    "location": "Shift + C > (Cam Overview Panel), Alt + C > (Cam Adjustment Panel), Properties Panel > Scene > Quick Overview ",
    "description": "Tools for managing multiple cameras",
    "doc_url": "https://weisl.github.io/cam_Overview/",
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
    importlib.reload(pie_menu)

else:
    from . import camera_controlls
    from . import dolly_zoom_modal
    from . import camera_gizmos
    from . import ui
    from . import keymap
    from . import preferences
    from . import pie_menu



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


def register():

    for file in files:
        file.register()


def unregister():

    for file in files.reverse():
        file.unregister()


