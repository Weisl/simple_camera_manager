import bpy

addon_keymaps = []


def remove_hotkey():
    ''' clears addon keymap hotkeys stored in addon_keymaps '''

    # only works for menues and pie menus
    for km, kmi in addon_keymaps:
        if hasattr(kmi.properties, 'name'):
            if kmi.properties.name in ['cam_manager.cycle_cameras_next', 'cam_manager.cycle_cameras_backward',
                                       'VIEW3D_PT_tools_type_suffix']:
                km.keymap_items.remove(kmi)

    addon_keymaps.clear()


def add_hotkey(context=None):
    '''Add default hotkey konfiguration'''
    if not context:
        context = bpy.context

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new("cam_manager.cycle_cameras_next", 'RIGHT_ARROW', 'PRESS', ctrl=True, shift=True)
        # kmi.properties.direction = 'FORWARD'
        kmi.active = True
        addon_keymaps.append((km, kmi))

        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new("cam_manager.cycle_cameras_backward", 'LEFT_ARROW', 'PRESS', ctrl=True, shift=True)
        kmi.active = True
        # kmi.properties.direction = 'BACKWARD'
        addon_keymaps.append((km, kmi))

        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(idname='wm.call_panel', type='C', value='PRESS', shift=True)
        kmi.properties.name = 'OBJECT_PT_camera_manager_popup'
        kmi.active = True
        # kmi.properties.direction = 'BACKWARD'
        addon_keymaps.append((km, kmi))

        km = kc.keymaps.new(name="3D View", space_type='VIEW_3D', region_type='WINDOW')
        kmi = km.keymap_items.new(idname='wm.call_menu_pie', type='C', value='PRESS', alt=True)
        kmi.properties.name = "CAMERA_pie_menu"
        kmi.active = True
        addon_keymaps.append((km, kmi))


def get_hotkey_entry_item(km, kmi_name, kmi_value=None):
    ''' returns hotkey of specific type, with specific properties.name (keymap is not a dict, so referencing by keys is not enough
    if there are multiple hotkeys!)'''
    # for menus and pie_menu
    if kmi_value:
        for i, km_item in enumerate(km.keymap_items):
            if km.keymap_items.keys()[i] == kmi_name:
                if km.keymap_items[i].properties.name == kmi_value:
                    return km_item

    # for operators
    else:
        if km.keymap_items.get(kmi_name):
            return km.keymap_items.get(kmi_name)

    return None


class CAM_MANAGER_OT_add_hotkey_renaming(bpy.types.Operator):
    ''' Add hotkey entry '''
    bl_idname = "cam_manager.add_hotkey"
    bl_label = "Addon Preferences Example"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        add_hotkey(context)
        return {'FINISHED'}


classes = (
    CAM_MANAGER_OT_add_hotkey_renaming,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    add_hotkey()


def unregister():
    from bpy.utils import unregister_class

    remove_hotkey()

    for cls in reversed(classes):
        unregister_class(cls)
