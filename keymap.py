import bpy

keymaps_items_dict = {
    "Simple Camera Manager": {"name": 'cam_menu', "idname": 'wm.call_panel', "operator":
        'OBJECT_PT_camera_manager_popup', "type": 'C', "value": 'PRESS',
                              "ctrl": False, "shift": True, "alt": True, "active": True},
    "Active Camera Pie": {"name": 'cam_pie', "idname": 'wm.call_menu_pie',
                          "operator": 'CAMERA_MT_pie_menu',
                          "type": 'C', "value": 'PRESS', "ctrl": False, "shift": False, "alt": True, "active": True},
    "Next Camera": {"name": 'next_cam', "idname": 'cam_manager.cycle_cameras_next',
                    "operator": '', "type": 'RIGHT_ARROW',
                    "value": 'PRESS', "ctrl": True, "shift": True, "alt": False, "active": True},
    "Previous Camera": {"name": 'prev_cam', "idname": 'cam_manager.cycle_cameras_backward',
                        "operator": '', "type": 'LEFT_ARROW', "value": 'PRESS', "ctrl": True, "shift": True,
                        "alt": False, "active": True}}


def get_panel_keymap_string(panel_id):
    # Get all keymaps
    keymaps = bpy.context.window_manager.keyconfigs.user.keymaps

    # Find the keymap item for the given panel
    keymap_item = None
    for km in keymaps:
        for kmi in km.keymap_items:
            if kmi.idname == "wm.call_panel" and kmi.properties.name == panel_id:
                keymap_item = kmi
                break
        if keymap_item:
            break

    if not keymap_item:
        return

    # Extract the key information
    modifiers = []
    if keymap_item.ctrl:
        modifiers.append("Ctrl")
    if keymap_item.alt:
        modifiers.append("Alt")
    if keymap_item.shift:
        modifiers.append("Shift")
    if keymap_item.oskey:
        modifiers.append("Cmd" if bpy.app.build_platform == 'Darwin' else "Win")

    key = keymap_item.type

    # Print the keymap in the desired format
    keymap_str = " + ".join(modifiers + [key])
    return keymap_str


def add_key(context, idname, type, ctrl, shift, alt, operator, active):
    km = context.window_manager.keyconfigs.addon.keymaps.new(name="Window")

    kmi = km.keymap_items.new(idname=idname, type=type, value='PRESS',
                              ctrl=ctrl, shift=shift,
                              alt=alt)

    if operator != '':
        add_key_to_keymap(operator, kmi, active=active)


def remove_key(context, idname, properties_name):
    """Removes addon hotkeys from the keymap"""
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps['Window']

    for kmi in km.keymap_items:
        if properties_name:
            if kmi.idname == idname and kmi.properties.name == properties_name:
                km.keymap_items.remove(kmi)
        else:
            if kmi.idname == idname:
                km.keymap_items.remove(kmi)


def add_keymap():
    context = bpy.context
    prefs = context.preferences.addons[__package__].preferences

    for key, valueDic in keymaps_items_dict.items():
        idname = valueDic["idname"]
        type = getattr(prefs, f'{valueDic["name"]}_type')
        ctrl = getattr(prefs, f'{valueDic["name"]}_ctrl')
        shift = getattr(prefs, f'{valueDic["name"]}_shift')
        alt = getattr(prefs, f'{valueDic["name"]}_alt')
        operator = valueDic["operator"]
        active = valueDic["active"]
        add_key(context, idname, type, ctrl, shift, alt, operator, active)


def add_key_to_keymap(idname, kmi, active=True):
    """ Add ta key to the appropriate keymap """
    kmi.properties.name = idname
    kmi.active = active


def remove_keymap():
    wm = bpy.context.window_manager
    addon_keymaps = wm.keyconfigs.addon.keymaps.get('Window')

    if not addon_keymaps:
        return

    # Collect items to remove first
    items_to_remove = []
    for kmi in addon_keymaps.keymap_items:
        for key, valueDic in keymaps_items_dict.items():
            idname = valueDic["idname"]
            operator = valueDic["operator"]
            if kmi.idname == idname and (not operator or getattr(kmi.properties, 'name', '') == operator):
                items_to_remove.append(kmi)

    # Remove items
    for kmi in items_to_remove:
        addon_keymaps.keymap_items.remove(kmi)


class REMOVE_OT_hotkey(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "cam.remove_hotkey"
    bl_label = "Remove hotkey"
    bl_description = "Remove hotkey"
    bl_options = {'REGISTER', 'INTERNAL'}

    idname: bpy.props.StringProperty()
    properties_name: bpy.props.StringProperty()
    property_prefix: bpy.props.StringProperty()

    def execute(self, context):
        remove_key(context, self.idname, self.properties_name)

        prefs = bpy.context.preferences.addons[__package__].preferences
        setattr(prefs, f'{self.property_prefix}_type', "NONE")
        setattr(prefs, f'{self.property_prefix}_ctrl', False)
        setattr(prefs, f'{self.property_prefix}_shift', False)
        setattr(prefs, f'{self.property_prefix}_alt', False)

        return {'FINISHED'}


class BUTTON_OT_change_key(bpy.types.Operator):
    """UI button to assign a new key to an addon hotkey"""
    bl_idname = "cam.key_selection_button"
    bl_label = "Press the button you want to assign to this operation."
    bl_options = {'REGISTER', 'INTERNAL'}

    property_prefix: bpy.props.StringProperty()

    def __init__(self):
        self.my_event = ''

    def invoke(self, context, event):
        prefs = bpy.context.preferences.addons[__package__].preferences
        self.prefs = prefs
        setattr(prefs, f'{self.property_prefix}_type', "NONE")

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.my_event = 'NONE'

        if event.type and event.value == 'RELEASE':  # Apply
            self.my_event = event.type

            setattr(self.prefs, f'{self.property_prefix}_type', self.my_event)
            self.execute(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.report({'INFO'},
                    "Key change: " + bpy.types.Event.bl_rna.properties['type'].enum_items[self.my_event].name)
        return {'FINISHED'}


classes = (
    BUTTON_OT_change_key,
    REMOVE_OT_hotkey,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    remove_keymap()

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
