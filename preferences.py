import bpy

from .keymap import remove_key
from .keymap import keymaps_items_dict
from .keymap import add_keymap, add_key



def update_key(self, context, idname, operator_name, property_prefix):
    # This functions gets called when the hotkey assignment is updated in the preferences
    wm = context.window_manager
    km = wm.keyconfigs.addon.keymaps["Window"]

    prefs = context.preferences.addons[__package__.split('.')[0]].preferences

    # Remove previous key assignment
    remove_key(context, idname, operator_name)
    add_key(context, idname, getattr(prefs, f'{property_prefix}_type'),
            getattr(prefs, f'{property_prefix}_ctrl'), getattr(prefs, f'{property_prefix}_shift'),
            getattr(prefs, f'{property_prefix}_alt'), operator_name, getattr(prefs, f'{property_prefix}_active'))


def update_next_cam_key(self, context):
    key_entry = keymaps_items_dict["Next Camera"]
    idname = key_entry["idname"]
    name = key_entry["name"]
    operator_name = key_entry["operator"]
    update_key(self, context, idname, operator_name, name)


def update_prev_cam_key(self, context):
    key_entry = keymaps_items_dict["Previous Camera"]
    idname = key_entry["idname"]
    name = key_entry["name"]
    operator_name = key_entry["operator"]
    update_key(self, context, idname, operator_name, name)


def update_cam_pie_key(self, context):
    key_entry = keymaps_items_dict["Active Camera Pie"]
    idname = key_entry["idname"]
    name = key_entry["name"]
    operator_name = key_entry["operator"]
    update_key(self, context, idname, operator_name, name)


def update_cam_menu_key(self, context):
    key_entry = keymaps_items_dict["Simple Camera Manager"]
    idname = key_entry["idname"]
    name = key_entry["name"]
    operator_name = key_entry["operator"]
    update_key(self, context, idname, operator_name, name)


# addon Preferences
class CAM_MANAGER_OT_renaming_preferences(bpy.types.AddonPreferences):
    """Contains the blender addon preferences"""
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__  ### __package__ works on multifile and __name__ not

    # addon updater preferences

    prefs_tabs: bpy.props.EnumProperty(items=(('GENERAL', "General", "General Settings"),
                                              ('KEYMAPS', "Keymaps", "Keymaps")),
                                       default='GENERAL')

    next_cam_type: bpy.props.StringProperty(
        name="Renaming Popup",
        default=keymaps_items_dict["Next Camera"]['type'],
        update=update_next_cam_key
    )

    next_cam_ctrl: bpy.props.BoolProperty(
        name="Ctrl",
        default=keymaps_items_dict["Next Camera"]['ctrl'],
        update=update_next_cam_key
    )

    next_cam_shift: bpy.props.BoolProperty(
        name="Shift",
        default=keymaps_items_dict["Next Camera"]['shift'],
        update=update_next_cam_key
    )
    next_cam_alt: bpy.props.BoolProperty(
        name="Alt",
        default=keymaps_items_dict["Next Camera"]['alt'],
        update=update_next_cam_key
    )

    next_cam_active: bpy.props.BoolProperty(
        name="Active",
        default=keymaps_items_dict["Next Camera"]['active'],
        update=update_next_cam_key
    )

    prev_cam_type: bpy.props.StringProperty(
        name="Renaming Popup",
        default=keymaps_items_dict["Previous Camera"]["type"],
        update=update_prev_cam_key
    )

    prev_cam_ctrl: bpy.props.BoolProperty(
        name="Ctrl",
        default=keymaps_items_dict["Previous Camera"]["ctrl"],
        update=update_prev_cam_key
    )

    prev_cam_shift: bpy.props.BoolProperty(
        name="Shift",
        default=keymaps_items_dict["Previous Camera"]["shift"],
        update=update_prev_cam_key
    )
    prev_cam_alt: bpy.props.BoolProperty(
        name="Alt",
        default=keymaps_items_dict["Previous Camera"]["alt"],
        update=update_prev_cam_key
    )

    prev_cam_active: bpy.props.BoolProperty(
        name="Active",
        default=keymaps_items_dict["Previous Camera"]["active"],
        update=update_prev_cam_key
    )

    cam_pie_type: bpy.props.StringProperty(
        name="Renaming Popup",
        default=keymaps_items_dict["Active Camera Pie"]["type"],
        update=update_cam_pie_key
    )

    cam_pie_ctrl: bpy.props.BoolProperty(
        name="Ctrl",
        default=keymaps_items_dict["Active Camera Pie"]["ctrl"],
        update=update_cam_pie_key
    )

    cam_pie_shift: bpy.props.BoolProperty(
        name="Shift",
        default=keymaps_items_dict["Active Camera Pie"]["shift"],
        update=update_cam_pie_key
    )
    cam_pie_alt: bpy.props.BoolProperty(
        name="Alt",
        default=keymaps_items_dict["Active Camera Pie"]["alt"],
        update=update_cam_pie_key
    )

    cam_pie_active: bpy.props.BoolProperty(
        name="Active",
        default=keymaps_items_dict["Active Camera Pie"]["active"],
        update=update_cam_pie_key
    )

    cam_menu_type: bpy.props.StringProperty(
        name="Renaming Popup",
        default=keymaps_items_dict["Simple Camera Manager"]["type"],
        update=update_cam_menu_key
    )

    cam_menu_ctrl: bpy.props.BoolProperty(
        name="Ctrl",
        default=keymaps_items_dict["Simple Camera Manager"]["ctrl"],
        update=update_cam_menu_key
    )

    cam_menu_shift: bpy.props.BoolProperty(
        name="Shift",
        default=keymaps_items_dict["Simple Camera Manager"]["shift"],
        update=update_cam_menu_key
    )
    cam_menu_alt: bpy.props.BoolProperty(
        name="Alt",
        default=keymaps_items_dict["Simple Camera Manager"]["alt"],
        update=update_cam_menu_key
    )

    cam_menu_active: bpy.props.BoolProperty(
        name="Active",
        default=keymaps_items_dict["Simple Camera Manager"]["active"],
        update=update_cam_menu_key
    )

    def keymap_ui(self, layout, title, property_prefix, id_name, properties_name):
        box = layout.box()
        split = box.split(align=True, factor=0.5)
        col = split.column()

        # Is hotkey active checkbox
        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_active', text="")
        row.label(text=title)

        # Button to assign the key assignments
        col = split.column()
        row = col.row(align=True)
        key_type = getattr(self, f'{property_prefix}_type')
        text = (
            bpy.types.Event.bl_rna.properties['type'].enum_items[key_type].name
            if key_type != 'NONE'
            else 'Press a key'
        )

        op = row.operator("cam.key_selection_button", text=text)
        op.property_prefix = property_prefix
        # row.prop(self, f'{property_prefix}_type', text="")
        op = row.operator("cam.remove_hotkey", text="", icon="X")
        op.idname = id_name
        op.properties_name = properties_name
        op.property_prefix = property_prefix

        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_ctrl')
        row.prop(self, f'{property_prefix}_shift')
        row.prop(self, f'{property_prefix}_alt')

    # Gizmos
    show_dolly_gizmo: bpy.props.BoolProperty(name='Dolly Zoom', description='Show the dolly gizmo', default=False)

    
    def draw(self, context):
        """ simple preference UI to define custom inputs and user preferences"""
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "prefs_tabs", expand=True)

        # Settings regarding the keymap
        if self.prefs_tabs == 'KEYMAPS':
            box = layout.box()

            for title, value in keymaps_items_dict.items():
                self.keymap_ui(box, title, value['name'], value["idname"], value["operator"])


        else:
            box = layout.box()
            row = box.row()
            row.label(text='Always show Gizmo')

            row = box.row()
            row.prop(self, "show_dolly_gizmo", expand=True)

            # updater draw function
            # could also pass in col as third arg


classes = (
    CAM_MANAGER_OT_renaming_preferences,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    add_keymap()


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
