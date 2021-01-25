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

else:
    from . import camera_controlls
    from . import ui
    from . import keymap
    from . import preferences


def register():
    # call the register functions from the other files
    camera_controlls.register()
    ui.register()
    keymap.register()
    preferences.register()


def unregister():
    # call the unregister functions from the other files
    ui.unregister()
    camera_controlls.unregister()
    preferences.unregister()
    keymap.unregister()
