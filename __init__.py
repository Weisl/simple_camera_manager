# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(camera_controlls)
    importlib.reload(ui_helpers)
    importlib.reload(dolly_zoom_modal)
    importlib.reload(camera_gizmos)
    importlib.reload(batch_render)
    importlib.reload(keymap)
    importlib.reload(preferences)
    importlib.reload(ui)
    importlib.reload(uilist)
    importlib.reload(pie_menu)


else:
    from . import camera_controlls
    from . import ui_helpers
    from . import dolly_zoom_modal
    from . import batch_render
    from . import camera_gizmos
    from . import ui
    from . import uilist
    from . import keymap
    from . import preferences
    from . import pie_menu


files = [
    camera_controlls,
    ui_helpers,
    dolly_zoom_modal,
    batch_render,
    ui,
    uilist,
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
    for file in reversed(files):
        file.unregister()