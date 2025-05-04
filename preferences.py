import bpy
import textwrap

from .keymap import add_keymap, add_key
from .keymap import keymaps_items_dict
from .keymap import remove_key
from .ui import VIEW3D_PT_SimpleCameraManager


def label_multiline(context, text, parent):
    """
    Draw a label with multiline text in the layout.

    Args:
        context (Context): The current context.
        text (str): The text to display.
        parent (UILayout): The parent layout to add the label to.
    """
    chars = int(context.region.width / 7)  # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)


def update_panel_category(self, context):
    """Update panel tab for simple export"""
    panels = [
        VIEW3D_PT_SimpleCameraManager,
    ]

    for panel in panels:
        try:
            bpy.utils.unregister_class(panel)
        except:
            pass

        prefs = context.preferences.addons[__package__].preferences
        panel.bl_category = prefs.panel_category

        if prefs.enable_n_panel:
            try:
                bpy.utils.register_class(panel)
            except ValueError:
                pass  # Avoid duplicate registrations
    return


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
                                              ('KEYMAPS', "Keymaps", "Keymap Settings"),
                                              ('SUPPORT', "Support", "Support me")),
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

    panel_category: bpy.props.StringProperty(name="Category Tab",
                                             description="The category name used to organize the addon in the properties panel for all the addons",
                                             default='Simple Camera Manager',
                                             update=update_panel_category)  # update = update_panel_position,

    enable_n_panel: bpy.props.BoolProperty(
        name="Enable Simple Camera Manager N-Panel",
        description="Toggle the N-Panel on and off.",
        default=True,
        update=update_panel_category)

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

        if self.prefs_tabs == 'GENERAL':
            box = layout.box()
            box.label(text="UI")
            box.prop(self, 'enable_n_panel')
            box.prop(self, 'panel_category')
            # updater draw function
            # could also pass in col as third arg


            box = layout.box()
            box.label(text="Gizmos")
            row = box.row()
            row.label(text='Always show Gizmo')
            row = box.row()
            row.prop(self, "show_dolly_gizmo", expand=True)





        # Settings regarding the keymap
        elif self.prefs_tabs == 'KEYMAPS':
            box = layout.box()

            for title, value in keymaps_items_dict.items():
                self.keymap_ui(box, title, value['name'], value["idname"], value["operator"])


        elif self.prefs_tabs == 'SUPPORT':
            # Cross Promotion

            text = "Explore my other Blender Addons designed for more efficient game asset workflows!"
            label_multiline(
                context=context,
                text=text,
                parent=layout
            )

            layout.label(text="♥♥♥ Leave a Review or Rating! ♥♥♥")
            col = layout.column(align=True)

            row = col.row(align=True)
            row.label(text="Simple Camera Manager")
            row.operator("wm.url_open", text="Superhive",
                         icon="URL").url = "https://superhivemarket.com/products/simple-camera-manager"
            row.operator("wm.url_open", text="Gumroad",
                         icon="URL").url = "https://weisl.gumroad.com/l/simple_camera_manager"


            layout.label(text="Other Simple Tools ($)")

            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Simple Collider")
            row.operator("wm.url_open", text="Superhive",
                         icon="URL").url = "https://superhivemarket.com/products/simple-collider"
            row.operator("wm.url_open", text="Gumroad",
                         icon="URL").url = "https://weisl.gumroad.com/l/simple_collider"

            # row = col.row(align=True)
            # row.label(text="Simple Export")
            # row.operator("wm.url_open", text="Superhive",
            #              icon="URL").url = "https://superhivemarket.com/products/simple-export"
            # row.operator("wm.url_open", text="Gumroad",
            #              icon="URL").url = "https://weisl.gumroad.com/l/simple_export"

            layout.label(text="Free Simple Tools")
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Simple Renaming")
            row.operator("wm.url_open", text="Blender Extensions",
                         icon="URL").url = "https://extensions.blender.org/add-ons/simple-renaming-panel/"
            row.operator("wm.url_open", text="Gumroad",
                         icon="URL").url = "https://weisl.gumroad.com/l/simple_renaming"

            col = layout.column(align=True)
            row = col.row()
            row.label(text='Support & Feedback')
            row = col.row()
            row.label(text='Support is primarily provided through the store pages for Superhive and Gumroad.')
            row.label(text='Questions or Feedback?')
            row = col.row()
            row.operator("wm.url_open", text="Join Discord", icon="URL").url = "https://discord.gg/kSWeQpfD"


classes = (
    CAM_MANAGER_OT_renaming_preferences,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    add_keymap()

    # Initialize correct property panel for the Simple Export Panel
    update_panel_category(None, bpy.context)

def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
