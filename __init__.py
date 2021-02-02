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
    importlib.reload(dolly_zoom)
    importlib.reload(keymap)
    importlib.reload(preferences)
    importlib.reload(ui)
    importlib.reload(addon_updater_ops)
    importlib.reload(pie_menu)

else:
    from . import camera_controlls
    from . import dolly_zoom
    from . import ui
    from . import keymap
    from . import preferences
    from . import addon_updater_ops
    from . import pie_menu


def register():
    # addon updater code and configurations
    # in case of broken version, try to register the updater first
    # so that users can revert back to a working version
    addon_updater_ops.register(bl_info)

    # call the register functions from the other files
    camera_controlls.register()
    dolly_zoom.register()
    ui.register()
    pie_menu.register()

    #keymap and preferences should be last
    keymap.register()
    preferences.register()


def unregister():
    # addon updater unregister
    addon_updater_ops.unregister()

    # call the unregister functions from the other files
    ui.unregister()
    camera_controlls.unregister()
    preferences.unregister()
    dolly_zoom.unregister()
    pie_menu.unregister()
    keymap.unregister()

