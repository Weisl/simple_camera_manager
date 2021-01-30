bl_info = {
    "name": "Camera Manager",
    "author": "Matthias Patscheider",
    "version": (1, 0),
    "blender": (2, 91, 0),
    "location": "View3D > Object",
    "description": "A collection of some Utilities ",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
}

# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(camera_controlls)
    importlib.reload(keymap)
    importlib.reload(preferences)
    importlib.reload(ui)
    importlib.reload(addon_updater_ops)

else:
    from . import camera_controlls
    from . import ui
    from . import keymap
    from . import preferences
    from . import addon_updater_ops


def register():
    # addon updater code and configurations
    # in case of broken version, try to register the updater first
    # so that users can revert back to a working version
    addon_updater_ops.register(bl_info)

    # call the register functions from the other files
    camera_controlls.register()
    ui.register()
    keymap.register()
    preferences.register()


def unregister():
    # addon updater unregister
    addon_updater_ops.unregister()

    # call the unregister functions from the other files
    ui.unregister()
    camera_controlls.unregister()
    preferences.unregister()
    keymap.unregister()
