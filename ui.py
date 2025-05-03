import os
import subprocess

import bpy

from .keymap import get_keymap_string
from .pie_menu import draw_camera_settings


def get_addon_name():
    """
    Returns the addon name as a string.
    """
    return "Simple Camera Manager"


def draw_simple_camera_manager_header(layout):
    row = layout.row(align=True)
    # Open documentation
    row.operator("wm.url_open", text="", icon="HELP").url = "https://weisl.github.io/camera_manager_Overview/"

    # Open Preferences
    addon_name = get_addon_name()
    op = row.operator("simple_camera.open_preferences", text="", icon='PREFERENCES')
    op.addon_name = addon_name
    op.prefs_tabs = 'GENERAL'

    # Open Export Popup
    op = row.operator("wm.call_panel", text="", icon="WINDOW")
    op.name = "OBJECT_PT_camera_manager_popup"

    # Display the combined label and keymap information
    row.label(text=f"Simple Camera Manager")


class CAMERA_OT_open_in_explorer(bpy.types.Operator):
    """Open render output directory in Explorer"""
    bl_idname = "cameras.open_in_explorer"
    bl_label = "Open Folder"
    bl_description = "Open the render output folder in explorer"


    def execute(self, context):
        filepath = os.path.dirname(os.path.abspath(context.scene.render.filepath))
        bpy.ops.file.external_operation(filepath=filepath, operation='FOLDER_OPEN')
        return {'FINISHED'}


def filter_list(self, context):
    """
    Filter cameras from all objects for the UI list and soft them
    :param self:
    :param context:
    :return: flt_flags is a bit-flag containing the filtering and flt
            flt_neworder defines the order of all cameras
    """
    helper_funcs = bpy.types.UI_UL_list

    # Default return values.
    flt_flags = []
    flt_neworder = []

    # Get all objects from scene.
    objects = context.scene.objects

    # Create bitmask for all objects
    flt_flags = [self.bitflag_filter_item] * len(objects)

    # Filter by object type.
    for idx, obj in enumerate(objects):
        if obj.type == "CAMERA":
            flt_flags[idx] |= self.CAMERA_FILTER
        else:
            flt_flags[idx] &= ~self.bitflag_filter_item

    flt_neworder = helper_funcs.sort_items_by_name(objects, "name")

    return flt_flags, flt_neworder


class CAMERA_UL_cameras_popup(bpy.types.UIList):
    """UI list showing all cameras with associated resolution. The resolution can be changed directly from this list"""
    # The draw_item function is called for each item of the collection that is visible in the list.
    #   data is the RNA object containing the collection,
    #   item is the current drawn item of the collection,
    #   icon is the "computed" icon for the item (as an integer, because some objects like materials or textures
    #   have custom icons ID, which are not available as enum items).
    #   active_data is the RNA object containing the active property for the collection (i.e. integer pointing to the
    #   active item of the collection).
    #   active_propname is the name of the active property (use 'getattr(active_data, active_propname)').
    #   index is index of the current item in the collection.
    #   flt_flag is the result of the filtering process for this item.
    #   Note: as index and flt_flag are optional arguments, you do not have to use/declare them here if you don't
    #         need them.

    # Constants (flags)
    # Be careful not to shadow FILTER_ITEM!
    CAMERA_FILTER = 1 << 0

    def filter_items(self, context, data, propname):
        # This function gets the collection property (as the usual tuple (data, propname)), and must return two lists:
        # * The first one is for filtering, it must contain 32bit integers were self.bitflag_filter_item marks the
        #   matching item as filtered (i.e. to be shown), and 31 other bits are free for custom needs. Here we use the
        #   first one to mark CAMERA_FILTER.
        # * The second one is for reordering, it must return a list containing the new indices of the items (which
        #   gives us a mapping org_idx -> new_idx).
        # Please note that the default UI_UL_list defines helper functions for common tasks (see its doc for more info).
        # If you do not make filtering and/or ordering, return empty list(s) (this will be more efficient than
        # returning full lists doing nothing!).
        flt_flags, flt_neworder = filter_list(self, context)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        obj = item
        cam = item.data

        # draw_item must handle the three layout types. Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The latter also enables ctrl-click rename.
            # We use icon_value of label, as our given icon is an integer value, not an enum ID.
            # Note "data" names should never be translated!
            if obj.type == 'CAMERA':

                split = layout.split(factor=0.6)
                split_left = split.column().split(factor=0.45)
                # Camera name
                col_01 = split_left.column()
                col_02 = split_left.column()
                split_right = split.column().split(factor=0.5)
                col_03 = split_right.column()
                split_right_02 = split_right.split(factor=0.5)
                col_04 = split_right_02.column()
                col_05 = split_right_02.column()

                ###### Col01 #####
                # Camera name and visibility

                row = col_01.row(align=True)
                icon = 'VIEW_CAMERA' if obj == bpy.context.scene.camera else 'FORWARD'
                op = row.operator("cam_manager.change_scene_camera", text='', icon=icon)
                op.camera_name = obj.name
                op.switch_to_cam = False
                row.prop(obj, 'name', text='')

                icon = 'HIDE_OFF' if obj.visible_get() else 'HIDE_ON'
                op = row.operator("camera.hide_unhide", icon=icon, text='')
                op.camera_name = obj.name
                op.cam_hide = obj.visible_get()
                row.prop(obj, "hide_viewport", text='')
                row.prop(obj, "hide_select", text='')

                if obj.get('lock'):
                    op = row.operator("cam_manager.lock_unlock_camera", icon='LOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = False
                else:
                    op = row.operator("cam_manager.lock_unlock_camera", icon='UNLOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = True

                ###### Col02 #####
                row = col_02.row()
                c = row.column(align=True)
                c.prop(cam, 'lens', text='')
                c.prop(cam, 'angle', text='')
                c = row.column(align=True)
                c.prop(cam, "resolution", text="")
                op = row.operator("cam_manager.camera_resolutio_from_image", text="", icon='IMAGE_BACKGROUND')
                op.camera_name = cam.name
                c = row.column(align=True)
                c.prop(cam, "clip_start", text="")
                c.prop(cam, "clip_end", text="")

                ###### Col03 #####
                row = col_03.row(align=True)
                row.prop_search(cam, "world", bpy.data, "worlds", text='')
                row.prop(cam, 'exposure', text='EXP')

                ###### Col04 #####
                row = col_04.row(align=True)
                op = row.operator("cameras.add_collection", icon='OUTLINER_COLLECTION')
                op.object_name = obj.name

                ###### Col05 #####
                row = col_05.row(align=True)
                row.prop(cam, "slot")
                op = row.operator('cameras.custom_render', text='', icon='RENDER_STILL')
                op.camera_name = obj.name


            else:
                layout.label(text=obj.name)

        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=obj.name)


class CAMERA_UL_cameras_scene(bpy.types.UIList):
    """UI list showing all cameras with associated resolution. The resolution can be changed directly from this list"""
    CAMERA_FILTER = 1 << 0

    def filter_items(self, context, data, propname):
        flt_flags, flt_neworder = filter_list(self, context)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        obj = item
        cam = item.data

        # draw_item must handle the three layout types. Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The latter also enables ctrl-click rename.
            # We use icon_value of label, as our given icon is an integer value, not an enum ID.
            # Note "data" names should never be translated!
            if obj.type == 'CAMERA':
                c = layout.column()
                row = c.row()

                split = row.split(factor=0.6)
                col_01 = split.column()
                col_02 = split.column()

                # COLUMN 01
                row = col_01.row(align=True)

                # Checkbox for selecting the collection for export
                row.prop(cam, "render_selected", text="")

                # Change icon for already active cam
                icon = 'VIEW_CAMERA' if obj == bpy.context.scene.camera else 'FORWARD'
                op = row.operator("cam_manager.change_scene_camera", text='', icon=icon)
                op.camera_name = obj.name
                op.switch_to_cam = False
                row.prop(obj, 'name', text='')

                # COLUMN 02
                row = col_02.row(align=True)

                if obj.get('lock'):
                    op = row.operator("cam_manager.lock_unlock_camera", icon='LOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = False
                else:
                    op = row.operator("cam_manager.lock_unlock_camera", icon='UNLOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = True

                row = row.row(align=True)

                row.prop(cam, 'slot', text='')
                op = row.operator('cameras.custom_render', text='', icon='RENDER_STILL')
                op.camera_name = obj.name


            else:
                layout.label(text=obj.name)

        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=obj.name)


class VIEW3D_PT_SimpleCameraManager(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Camera Manager"
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        draw_simple_camera_manager_header(layout)

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        row = layout.row()
        cam = scene.camera

        if cam:
            row.label(text=f"Active Camera: {cam.name}", icon='VIEW_CAMERA')

        # template_list now takes two new args.
        # The first one is the identifier of the registered UIList to use (if you want only the default list,
        # with no custom draw code, use "UI_UL_list").

        row = layout.row()
        row.template_list("CAMERA_UL_cameras_scene", "", scene, "objects", scene, "camera_list_index")
        col = row.column(align=True)
        col.operator("cam_manager.cycle_cameras_backward", text="", icon='TRIA_UP')
        col.operator("cam_manager.cycle_cameras_next", text="", icon='TRIA_DOWN')
        col.menu(UIListDropdownMenu.bl_idname, icon='DOWNARROW_HLT', text="")

        row = layout.row()
        row.operator("cam_manager.multi_camera_rendering_handlers", text="Batch Render ", icon="RENDER_ANIMATION")
        row = layout.row()
        row.prop(context.scene.render, 'filepath', text='Folder')
        # col.operator("cam_manager.multi_camera_rendering_modal", text="Batch Render (Background)", icon="FILE_SCRIPT")

        # Get the keymap for the panel
        panel_keymap = get_keymap_string("OBJECT_PT_camera_manager_popup", "PANEL")
        menu_keymap = get_keymap_string("CAMERA_MT_pie_menu", "MENU")
        operator1_keymap = get_keymap_string("cam_manager.cycle_cameras_backward", "OPERATOR")
        operator2_keymap = get_keymap_string("cam_manager.cycle_cameras_next", "OPERATOR")

        # Draw the panel header
        header, body = layout.panel(idname="ACTIVE_COL_PANEL", default_closed=False)
        header.label(text=f"Active Camera", icon='OUTLINER_COLLECTION')

        if body:
            cam_obj = context.scene.camera
            draw_camera_settings(context, body, cam_obj, use_subpanel=True)

        layout.label(text='Dolly Zoom', icon='VIEW_CAMERA')
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("cam_manager.modal_camera_dolly_zoom", text="Dolly Zoom", icon='CON_CAMERASOLVER')

        row = col.row(align=True)
        prefs = context.preferences.addons[__package__].preferences
        row.prop(prefs, "show_dolly_gizmo", text="Gizmo")

        layout.separator()
        layout.label(text='Collection Operators')
        layout.menu(CameraOperatorDropdownMenu.bl_idname, icon='OUTLINER_COLLECTION')

        layout.separator()
        layout.label(text='Keymap')
        # Display the combined label and keymap information
        layout.label(text=f"Camera Manager ({panel_keymap})")
        layout.label(text=f"Camera Pie ({menu_keymap})")
        layout.label(text=f"Previous Cam ({operator1_keymap})")
        layout.label(text=f"Next Cam ({operator2_keymap})")


class CAM_MANAGER_PT_scene_panel:
    """Properties Panel in the scene tab"""
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"


class CAM_MANAGER_PT_scene_properties(CAM_MANAGER_PT_scene_panel, bpy.types.Panel):
    bl_idname = "OBJECT_PT_camera_manager"
    bl_label = ""
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        draw_simple_camera_manager_header(layout)

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        row = layout.row()
        row.prop(scene, "camera")

        row = layout.row()
        # template_list now takes two new args.
        # The first one is the identifier of the registered UIList to use (if you want only the default list,
        # with no custom draw code, use "UI_UL_list").

        row = layout.row()
        row.template_list("CAMERA_UL_cameras_scene", "", scene, "objects", scene, "camera_list_index")
        col = row.column(align=True)
        col.operator("cam_manager.cycle_cameras_backward", text="", icon='TRIA_UP')
        col.operator("cam_manager.cycle_cameras_next", text="", icon='TRIA_DOWN')

        layout.separator()
        layout.label(text='All Cameras')

        row = layout.row(align=True)
        row.prop_search(scene.cam_collection, "collection", bpy.data, "collections", text='Camera Collection')
        row.operator("camera.create_collection", text='New Collection', icon='COLLECTION_NEW')

        row = layout.row()
        row.operator('cameras.all_to_collection')


class CAM_MANAGER_PT_popup(bpy.types.Panel):
    bl_idname = "OBJECT_PT_camera_manager_popup"
    bl_label = "Simple Camera Manager Popup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = "empty"
    bl_ui_units_x = 45

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Simple Camera Manager")

        scene = context.scene
        split = layout.split(factor=0.333)
        col_01 = split.column()
        split = split.split(factor=0.5)
        col_02 = split.column()
        col_03 = split.column()

        # Collections
        row = col_01.row(align=True)
        row.prop_search(scene.cam_collection, "collection", bpy.data, "collections", text='')
        row.operator("camera.create_collection", text='', icon='COLLECTION_NEW')
        col_01.operator('cameras.all_to_collection')

        # Camera Settings
        col_03.operator("view3d.view_camera", text="Toggle Camera View", icon='VIEW_CAMERA')

        layout.separator()
        # template_list now takes two new args.
        # The first one is the identifier of the registered UIList to use (if you want only the default list,
        # with no custom draw code, use "UI_UL_list").

        layout.separator()

        split = layout.split(factor=0.6)
        split_left = split.column().split(factor=0.45)

        # Camera name
        col_01 = split_left.column()
        col_02 = split_left.column()
        split_right = split.column().split(factor=0.5)
        col_03 = split_right.column()
        split_right_02 = split_right.split(factor=0.5)
        col_04 = split_right_02.column()
        col_05 = split_right_02.column()

        row = col_01.row(align=True)
        row.label(text="Camera")
        row.label(text="Visibility")
        # col_02.label(text="Focal Length, Resolution, Clipping")
        row = col_02.row(align=True)
        row.label(text="Focal Length")
        row.label(text="Resolution")
        row.label(text="Clipping")
        # col_03.label(text="World & Exposure")
        row = col_03.row(align=True)
        row.label(text="World")
        row.label(text="Exposure")
        row = col_04.row(align=True)
        row.label(text="Collection")
        row = col_05.row(align=True)
        row.label(text="Render Slot")

        row = layout.row()
        row.template_list("CAMERA_UL_cameras_popup", "", scene, "objects", scene, "camera_list_index")
        col = row.column(align=True)
        col.operator("cam_manager.cycle_cameras_backward", text="", icon='TRIA_UP')
        col.operator("cam_manager.cycle_cameras_next", text="", icon='TRIA_DOWN')

        row = layout.row()
        row.prop(scene, 'output_render')
        row = layout.row()
        row.prop(scene, 'output_use_cam_name')
        row = layout.row()
        row.prop(context.scene.render, 'filepath')
        row.operator('cameras.open_in_explorer', text='Open Render Folder', Icon='FILE_FOLDER')
        row = layout.row()  # layout.label(text="Output path" + os.path.abspath(context.scene.render.filepath))


class CAM_MANAGER_PT_camera_properties(bpy.types.Panel):
    bl_idname = "CAMERA_PT_manager_menu"
    bl_label = "Simple Camera Manager Menu"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_options = {'HIDE_HEADER'}
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'}

    @classmethod
    def poll(cls, context):
        engine = context.engine
        # Check if the properties data panel is for the camera or not
        return context.camera and (engine in cls.COMPAT_ENGINES)

    def draw(self, context):
        layout = self.layout

        cam = context.camera

        row = layout.row(align=True)
        row.prop(cam, "resolution", text="")
        op = row.operator("cam_manager.camera_resolutio_from_image", text="",
                          icon='IMAGE_BACKGROUND').camera_name = cam.name


class CameraCollectionProperty(bpy.types.PropertyGroup):
    collection: bpy.props.PointerProperty(name="Collection", type=bpy.types.Collection, )


class CAMERA_OT_SelectAllCameras(bpy.types.Operator):
    bl_idname = "cam_manager.select_all_cameras"
    bl_label = "Select All Collections"
    bl_options = {'REGISTER', 'UNDO'}

    invert: bpy.props.BoolProperty()

    def execute(self, context):
        for cam in bpy.data.cameras:
            cam.render_selected = not self.invert
        return {'FINISHED'}


# Define the custom menu
class CameraOperatorDropdownMenu(bpy.types.Menu):
    bl_label = "Camera Collection Operator"
    bl_idname = "OBJECT_MT_camera_dropdown_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("camera.create_collection", text='Camera Collection', icon='COLLECTION_NEW')
        layout.operator("cameras.all_to_collection", text='Move to Camera Collection', icon='OUTLINER_COLLECTION')
        layout.operator("camera.create_camera_from_view", text='Create Camera from View', icon='VIEW_CAMERA')
        layout.operator("view3d.view_camera", text="Toggle Camera View", icon='VIEW_CAMERA')
        layout.operator("cameras.open_in_explorer", text='Open Render Folder', icon='FILE_FOLDER')

class UIListDropdownMenu(bpy.types.Menu):
    bl_label = "Camera List Operators"
    bl_idname = "OBJECT_MT_camera_list_dropdown_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("cam_manager.select_all_cameras", text='Select All', icon='CHECKBOX_HLT').invert = False
        layout.operator("cam_manager.select_all_cameras", text='Select None', icon='CHECKBOX_DEHLT').invert = True


classes = (
    CameraCollectionProperty,
    CAMERA_OT_open_in_explorer,
    CAMERA_UL_cameras_popup,
    CAMERA_UL_cameras_scene,
    CAMERA_OT_SelectAllCameras,
    CAM_MANAGER_PT_scene_properties,
    CAM_MANAGER_PT_popup,
    CAM_MANAGER_PT_camera_properties,
    VIEW3D_PT_SimpleCameraManager,
    CameraOperatorDropdownMenu,
    UIListDropdownMenu,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    scene = bpy.types.Scene

    # The PointerProperty has to be after registering the classes to know about the custom property type
    scene.cam_collection = bpy.props.PointerProperty(name="Camera Collection",
                                                     description='User collection dedicated for the cameras',
                                                     type=CameraCollectionProperty)

    scene.output_render = bpy.props.BoolProperty(name="Save Render to Disk", description="Save renders to disk",
                                                 default=True)

    scene.output_use_cam_name = bpy.props.BoolProperty(name="Use Camera Name as File Name",
                                                       description="Use camera name as file name", default=True)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    scene = bpy.types.Scene

    del scene.my_operator
    del scene.output_use_cam_name
    del scene.output_render
    del scene.cam_collection
