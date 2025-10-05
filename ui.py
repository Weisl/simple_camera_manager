import os

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
        col.menu("OBJECT_MT_camera_list_dropdown_menu", icon='DOWNARROW_HLT', text="")

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


class OBJECT_PT_camera_manager_popup(bpy.types.Panel):
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
        row.operator('cameras.open_in_explorer', text='Open Render Folder', icon='FILE_FOLDER')
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
    bl_label = "Camera Operators"
    bl_idname = "OBJECT_MT_camera_dropdown_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("camera.create_collection", text='Camera Collection', icon='COLLECTION_NEW')
        layout.operator("cameras.all_to_collection", text='Move to Camera Collection', icon='OUTLINER_COLLECTION')
        layout.operator("camera.create_camera_from_view", text='Create Camera from View', icon='VIEW_CAMERA')
        layout.operator("view3d.view_camera", text="Toggle Camera View", icon='VIEW_CAMERA')
        layout.operator("cameras.open_in_explorer", text='Open Render Folder', icon='FILE_FOLDER')


classes = (
    CameraCollectionProperty,
    CAMERA_OT_open_in_explorer,
    CAMERA_OT_SelectAllCameras,
    CAM_MANAGER_PT_scene_properties,
    OBJECT_PT_camera_manager_popup,
    CAM_MANAGER_PT_camera_properties,
    VIEW3D_PT_SimpleCameraManager,
    CameraOperatorDropdownMenu,
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
