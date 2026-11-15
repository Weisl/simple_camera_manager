import bpy
from bpy.types import Menu, Panel

from .camera_presets import (
    BUILTIN_CAMERA_PRESETS,  # noqa: F401 - re-exported for tests/back-compat
    CAM_MANAGER_MT_camera_presets,
)


RESOLUTION_PRESET_ITEMS = [
    ('1080x1080', "Square (HD)  1080x1080", "1080x1080 (1:1)"),
    ('1280x720', "HD (720p)  1280x720", "1280x720 (16:9)"),
    ('1920x1080', "Full HD (1080p)  1920x1080", "1920x1080 (16:9)"),
    ('2560x1440', "QHD (1440p)  2560x1440", "2560x1440 (16:9)"),
    ('3840x2160', "4K UHD  3840x2160", "3840x2160 (16:9)"),
    ('7680x4320', "8K UHD  7680x4320", "7680x4320 (16:9)"),
    ('2560x1080', "Ultra-Wide HD  2560x1080", "2560x1080 (21:9)"),
    ('3440x1440', "Ultra-Wide QHD  3440x1440", "3440x1440 (21:9)"),
    ('5120x2160', "Ultra-Wide 4K  5120x2160", "5120x2160 (21:9)"),
    ('512x512', "Square  512x512", "512x512 (1:1)"),
    ('1024x1024', "Square  1024x1024", "1024x1024 (1:1)"),
    ('2048x2048', "Square  2048x2048", "2048x2048 (1:1)"),
    ('4096x4096', "Square  4096x4096", "4096x4096 (1:1)"),
    ('1080x1080_insta', "Instagram Square  1080x1080", "1080x1080 (1:1)"),
    ('1080x1350_insta', "Instagram Portrait  1080x1350", "1080x1350 (4:5)"),
    ('1080x608_insta', "Instagram Landscape  1080x608", "1080x608 (1.91:1)"),
    ('820x312_fb', "Facebook Cover  820x312", "820x312 (2.63:1)"),
    ('1280x720_yt', "YouTube Thumbnail  1280x720", "1280x720 (16:9)"),
    ('1500x500_tw', "Twitter Header  1500x500", "1500x500 (3:1)"),
    ('1584x396_linkedin', "LinkedIn Banner  1584x396", "1584x396 (4:1)"),
    ('720x480', "SD (Standard Definition)  720x480", "720x480 (4:3)"),
    ('2048x1080', "2K (DCI)  2048x1080", "2048x1080 (17:9)"),
    ('4096x2160', "4K DCI  4096x2160", "4096x2160 (17:9)"),
]

FOCAL_LENGTH_PRESET_ITEMS = [
    ('14', "Ultra Wide  14mm", "14mm — Ultra Wide"),
    ('18', "Wide  18mm", "18mm — Wide"),
    ('24', "Wide  24mm", "24mm — Wide"),
    ('28', "Wide  28mm", "28mm — Wide"),
    ('35', "Standard Wide  35mm", "35mm — Standard Wide"),
    ('40', "Standard Wide  40mm", "40mm — Standard Wide"),
    ('50', "Normal  50mm", "50mm — Normal"),
    ('85', "Portrait  85mm", "85mm — Portrait"),
    ('100', "Macro / Portrait  100mm", "100mm — Macro / Portrait"),
    ('105', "Portrait / Macro  105mm", "105mm — Portrait / Macro"),
    ('120', "Medium Telephoto  120mm", "120mm — Medium Telephoto"),
    ('135', "Short Telephoto  135mm", "135mm — Short Telephoto"),
    ('200', "Telephoto  200mm", "200mm — Telephoto"),
]


RESOLUTION_PRESET_MAP = {
    '512x512': (512, 512),
    '1024x1024': (1024, 1024),
    '2048x2048': (2048, 2048),
    '4096x4096': (4096, 4096),
    '1080x1080': (1080, 1080),
    '1280x720': (1280, 720),
    '1920x1080': (1920, 1080),
    '2560x1440': (2560, 1440),
    '3840x2160': (3840, 2160),
    '7680x4320': (7680, 4320),
    '2560x1080': (2560, 1080),
    '3440x1440': (3440, 1440),
    '5120x2160': (5120, 2160),
    '1080x1080_insta': (1080, 1080),
    '1080x1350_insta': (1080, 1350),
    '1080x608_insta': (1080, 608),
    '820x312_fb': (820, 312),
    '1280x720_yt': (1280, 720),
    '1500x500_tw': (1500, 500),
    '1584x396_linkedin': (1584, 396),
    '720x480': (720, 480),
    '2048x1080': (2048, 1080),
    '4096x2160': (4096, 2160),
}


class CAM_MANAGER_OT_apply_resolution_preset(bpy.types.Operator):
    """Apply a common resolution preset to the active camera"""
    bl_idname = "cam_manager.apply_resolution_preset"
    bl_label = "Resolution Preset"
    bl_description = "Apply a common resolution preset to the camera and enable resolution overwrite"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(
        name="Preset",
        items=RESOLUTION_PRESET_ITEMS,
    )

    def execute(self, context):
        cam_obj = context.scene.camera
        if cam_obj is None:
            return {'CANCELLED'}
        cam = cam_obj.data
        w, h = RESOLUTION_PRESET_MAP[self.preset]
        cam.resolution = (w, h)
        cam.resolution_overwrite = True
        return {'FINISHED'}


class CAM_MANAGER_OT_apply_focal_length_preset(bpy.types.Operator):
    """Apply a common focal length preset to the active camera"""
    bl_idname = "cam_manager.apply_focal_length_preset"
    bl_label = "Focal Length Preset"
    bl_description = "Apply a common focal length preset to the camera"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(
        name="Preset",
        items=FOCAL_LENGTH_PRESET_ITEMS,
    )

    def execute(self, context):
        cam_obj = context.scene.camera
        if cam_obj is None:
            return {'CANCELLED'}
        cam_obj.data.lens = float(self.preset)
        return {'FINISHED'}


# spawn an edit mode selection pie (run while object is in edit mode to get a valid output)

def background_image_name(img, index):
    """Name of a camera background image's image or movie clip."""
    source = img.image if img.source == 'IMAGE' else img.clip
    return source.name if source else f"Background {index + 1}"


def draw_background_image_settings(context, layout, cam_obj):
    """Visibility, opacity, depth and framing of a camera's background images."""
    cam = cam_obj.data
    col = layout.column(align=True)
    if not cam_obj.visible_get():
        row = layout.row(align=True)
        row.label(text="Camera is hidden", icon='ERROR')
        op = row.operator("cam_manager.unhide_camera", text="Show", icon='HIDE_OFF')
        op.camera_name = cam_obj.name

    if len(cam.background_images) == 0:
        row = col.row(align=True)
        row.label(text="Camera has no Background Images", icon='INFO')
        return

    # Uses the first background image, so it's drawn once, not per image.
    op = layout.operator("cam_manager.camera_resolutio_from_image", icon='IMAGE_BACKGROUND')
    op.camera_name = cam.name

    for index, img in enumerate(cam.background_images):
        box = layout.box()
        col = box.column(align=True)
        col.prop(img, "show_background_image", text=background_image_name(img, index))
        sub = col.column(align=True)
        sub.active = img.show_background_image
        sub.prop(img, "alpha", slider=True)
        sub.row(align=True).prop(img, "display_depth", expand=True)
        sub.row(align=True).prop(img, "frame_method", expand=True)


def draw_camera_settings(context, layout, cam_obj, use_subpanel=False, include_background_images=True):
    """Draw resolution, lens, clipping, focus, lighting, and background image settings for a camera.

    include_background_images=False leaves the background images out, for a
    caller that draws them in a section of its own (the camera popover)."""
    if cam_obj is None:
        return

    cam = cam_obj.data

    # Lens: the lens presets and every field they set (camera type, focal
    # length or ortho scale, sensor, resolution), so applying a preset never changes
    # anything that isn't shown right here.
    box = layout.box()
    box.label(text="Lens")
    row = box.row(align=True)
    row.menu("CAM_MANAGER_MT_camera_presets", text=CAM_MANAGER_MT_camera_presets.bl_label)
    row.operator("cam_manager.camera_preset_add", text="", icon='ADD')
    op = row.operator("cam_manager.camera_preset_add", text="", icon='REMOVE')
    op.remove_active = True

    box.prop(cam, "type", text="Type")

    col = box.column(align=True)
    if cam.type == 'ORTHO':
        col.prop(cam, "ortho_scale")
    else:
        row = col.row(align=True)
        row.prop(cam, "lens")
        row.operator_menu_enum("cam_manager.apply_focal_length_preset", "preset", text="", icon='DOWNARROW_HLT')
        col.prop(cam, 'angle')

    # Blender's own sensor-format presets, applied to the scene camera
    # (see CAM_MANAGER_MT_sensor_presets in camera_presets.py).
    col = box.column(align=True)
    row = col.row(align=True)
    row.menu("CAM_MANAGER_MT_sensor_presets", text="Sensor Format")
    row.prop(cam, "sensor_fit", text="")
    if cam.sensor_fit == 'AUTO':
        col.prop(cam, "sensor_width", text="Sensor Size")
    else:
        col.prop(cam, "sensor_width", text="Sensor Width")
        col.prop(cam, "sensor_height", text="Sensor Height")

    # Resolution (also set by the lens presets)
    row = box.row(align=True)
    col = box.column(align=True)
    row.prop(cam, "resolution_overwrite")

    row = col.row(align=True)
    row.enabled = cam.resolution_overwrite
    row.prop(cam, "resolution", text="Resolution")
    row.operator_menu_enum("cam_manager.apply_resolution_preset", "preset", text="", icon='DOWNARROW_HLT')

    col = layout.column(align=True)
    row = col.row(align=True)
    row.prop(cam, "clip_start")
    row = col.row(align=True)
    row.prop(cam, "clip_end")

    row = layout.row(align=True)
    row.prop(cam, "show_rotation_gizmo", text="Show Rotation Gizmo")

    def draw_focus_settings(layout):
        dof = cam.dof
        layout.label(text="Focus:")
        layout.prop(dof, 'use_dof')

        col = layout.column()
        col.prop(dof, "focus_object", text="Focus on Object")
        if dof.focus_object and dof.focus_object.type == 'ARMATURE':
            col.prop_search(dof, "focus_subtarget", dof.focus_object.data, "bones", text="Focus Bone")

        sub = col.row()
        sub.active = dof.focus_object is None
        sub.prop(dof, "focus_distance", text="Focus Distance")
        sub.operator(
            "ui.eyedropper_depth",
            icon='EYEDROPPER',
            text=""
        ).prop_data_path = "scene.camera.data.dof.focus_distance"

        col.prop(cam, "dolly_zoom_link_focus", text="Link to Dolly Zoom Target")
        row = col.row()
        row.scale_y = VIEWPORT_TOOL_SCALE_Y
        row.operator("cam_manager.modal_focus_distance", text="Focus Distance", icon='IMAGE_ZDEPTH')

        ob = context.object
        gizmo_cam = ob.data if (ob and ob.type == 'CAMERA') else cam
        col.prop(gizmo_cam, "show_dolly_gizmo", text="Show Gizmo")

    def draw_lighting_settings(layout):
        layout.label(text="Camera Lighting:")
        col = layout.column(align=False)
        row = col.row(align=True)
        row.prop(cam, 'exposure', text='Exposure')
        row = col.row(align=True)
        row.prop(cam, 'world', text='World')

    # Conditionally use subpanels or direct layout
    if use_subpanel:
        header, body = layout.panel(idname="FOCUS_PANEL", default_closed=True)
        header.label(text="Focus:")
        if body:
            draw_focus_settings(body)

        header, body = layout.panel(idname="LIGHT_PANEL", default_closed=True)
        header.label(text="Camera Lighting:")
        if body:
            draw_lighting_settings(body)

        if include_background_images:
            header, body = layout.panel(idname="BACKGROUND_IMG", default_closed=True)
            header.label(text="Background Image:")
            if body:
                body.label(text="Background Image:")
                draw_background_image_settings(context, body, cam_obj)
    else:
        draw_focus_settings(layout)
        draw_lighting_settings(layout)




# Blender's camera composition guides, in the order they appear in Blender's
# own Camera > Viewport Display panel.
COMPOSITION_GUIDES = (
    ("show_composition_thirds", "Thirds"),
    ("show_composition_center", "Center"),
    ("show_composition_center_diagonal", "Center Diagonal"),
    ("show_composition_golden", "Golden Ratio"),
    ("show_composition_golden_tria_a", "Golden Triangle A"),
    ("show_composition_golden_tria_b", "Golden Triangle B"),
    ("show_composition_harmony_tri_a", "Harmony Triangle A"),
    ("show_composition_harmony_tri_b", "Harmony Triangle B"),
)


def _view_3d(context):
    """The 3D Viewport space the UI is drawn in, or None outside one."""
    space = context.space_data
    return space if space is not None and space.type == 'VIEW_3D' else None


def _in_camera_view(view):
    return view is not None and view.region_3d is not None and view.region_3d.view_perspective == 'CAMERA'


def scene_cameras(context):
    """Cameras in the view layer, in the same (alphabetical) order the
    Previous/Next Camera operators cycle through."""
    vl_objects = context.view_layer.objects
    return sorted((ob for ob in context.scene.objects if ob.type == 'CAMERA' and ob.name in vl_objects),
                  key=lambda ob: ob.name.lower())


def draw_camera_lock_button(layout, cam_obj, text=""):
    """Toggle for locking the camera's transforms (location, rotation, scale)."""
    locked = bool(cam_obj.get('lock'))
    op = layout.operator("cam_manager.lock_unlock_camera", text=text,
                         icon='LOCKED' if locked else 'UNLOCKED', depress=locked)
    op.camera_name = cam_obj.name
    op.cam_lock = not locked


def draw_display_settings(context, layout, cam_obj):
    """Passepartout, name, safe areas and composition guides of a camera."""
    cam = cam_obj.data
    view = _view_3d(context)

    if view is not None and not view.overlay.show_overlays:
        row = layout.row(align=True)
        row.label(text="Overlays are off", icon='INFO')
        row.prop(view.overlay, "show_overlays", text="Show", icon='OVERLAY', toggle=True)

    row = layout.row(align=True)
    row.prop(cam, "show_passepartout", text="")
    sub = row.row(align=True)
    sub.active = cam.show_passepartout
    sub.prop(cam, "passepartout_alpha", text="Passepartout", slider=True)

    row = layout.row(align=True)
    row.prop(cam, "show_name", text="Name", toggle=True)
    row.prop(cam, "show_safe_areas", text="Safe Areas", toggle=True)
    sub = row.row(align=True)
    sub.active = cam.show_safe_areas
    sub.prop(cam, "show_safe_center", text="Center-Cut", toggle=True)

    if cam.show_safe_areas:
        safe_data = context.scene.safe_areas
        col = layout.column(align=True)
        col.prop(safe_data, "title", slider=True)
        col.prop(safe_data, "action", slider=True)
        if cam.show_safe_center:
            col.prop(safe_data, "title_center", slider=True)
            col.prop(safe_data, "action_center", slider=True)

    layout.label(text="Composition Guides")
    grid = layout.grid_flow(columns=2, even_columns=True, align=True)
    for prop, text in COMPOSITION_GUIDES:
        grid.prop(cam, prop, text=text, toggle=True)


def draw_render_settings(context, layout, cam_obj):
    """Render slot, render button and the cameras collection."""
    scene = context.scene
    cam = cam_obj.data

    row = layout.row(align=True)
    row.prop(cam, "slot")
    op = row.operator('cameras.custom_render', text='Render', icon='RENDER_STILL')
    op.camera_name = cam_obj.name

    layout.label(text="Cameras Collection")
    row = layout.row(align=True)
    # hide visibility settings for collection if it doesn't yet exist
    collection = scene.cam_collection.collection
    if collection:
        row.prop(collection, 'hide_viewport', text='')
        layer_collection = context.view_layer.layer_collection.children.get(collection.name)
        if layer_collection:
            row.prop(layer_collection, 'hide_viewport', text='')
    row.prop_search(scene.cam_collection, "collection", bpy.data, "collections", text='')
    op = row.operator("cameras.add_collection", icon='OUTLINER_COLLECTION', text='')
    op.object_name = cam_obj.name


class CAM_MANAGER_MT_scene_cameras(Menu):
    """Pick the scene camera. Goes through Set Active Camera so the camera's
    resolution, exposure, world and render slot are applied, like Previous/Next
    Camera do."""
    bl_label = "Scene Camera"
    bl_idname = "CAM_MANAGER_MT_scene_cameras"

    def draw(self, context):
        layout = self.layout
        cameras = scene_cameras(context)
        if not cameras:
            layout.label(text="No cameras in the scene", icon='INFO')
            return
        for cam_obj in cameras:
            icon = 'VIEW_CAMERA' if cam_obj == context.scene.camera else 'OUTLINER_OB_CAMERA'
            op = layout.operator("cam_manager.change_scene_camera", text=cam_obj.name, icon=icon)
            op.camera_name = cam_obj.name


# --- Visual language -------------------------------------------------------
# The pie, the camera popover and the sidebar draw the same kinds of controls
# the same way:
# - menus (pick from a list) show a dropdown arrow and, where they have one,
#   the current value. In a pie, plain menus get no arrow, so the pie opens
#   them as popovers (or enum menus), which do;
# - buttons that open a settings window end in "…" (Blender's convention);
# - actions are plain buttons, toggles light up while on;
# - the viewport tools (modal operators that take over the viewport until
#   you confirm) are always the pair Dolly Zoom + Focus Distance, in a taller
#   row of their own.

VIEWPORT_TOOL_SCALE_Y = 1.4


def draw_viewport_tools(layout, label=False):
    """Dolly Zoom and Focus Distance, drawn as the viewport tool pair: one
    below the other, in taller buttons."""
    col = layout.column(align=True)
    if label:
        col.label(text="Viewport Tools")
    col.scale_y = VIEWPORT_TOOL_SCALE_Y
    col.operator("cam_manager.modal_camera_dolly_zoom", text="Dolly Zoom", icon='CON_CAMERASOLVER')
    col.operator("cam_manager.modal_focus_distance", text="Focus Distance", icon='IMAGE_ZDEPTH')


def draw_camera_settings_button(layout, text="Camera Settings…"):
    """Opens the camera popover, which stays open while you edit."""
    op = layout.operator("wm.call_panel", text=text, icon='PREFERENCES')
    op.name = CAM_MANAGER_PT_camera_popover.bl_idname
    op.keep_open = True


class CAM_MANAGER_PT_lens_presets(Panel):
    """The lens preset menu as a popover, so it gets a dropdown arrow in the pie."""
    bl_idname = "CAM_MANAGER_PT_lens_presets"
    bl_label = "Lens Presets"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 12

    def draw(self, context):
        # The preset menu sets no bl_idname, so it is registered under its class name.
        self.layout.menu_contents(CAM_MANAGER_MT_camera_presets.__name__)


class CAM_MANAGER_PT_composition_guides(Panel):
    """Composition guides as a popover: it stays open, so several guides can
    be switched in one go."""
    bl_idname = "CAM_MANAGER_PT_composition_guides"
    bl_label = "Composition Guides"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 10

    @classmethod
    def poll(cls, context):
        return context.scene.camera is not None

    def draw(self, context):
        layout = self.layout
        cam = context.scene.camera.data
        col = layout.column(align=True)
        for prop, text in COMPOSITION_GUIDES:
            col.prop(cam, prop, text=text)
        layout.prop(cam, "show_safe_areas", text="Safe Areas")


class CAM_MANAGER_PT_camera_popover(Panel):
    """Settings of the scene camera. A popover stays open while you edit,
    unlike the pie menu, which closes after one click."""
    bl_idname = "CAM_MANAGER_PT_camera_popover"
    bl_label = "Scene Camera"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 15

    def draw(self, context):
        layout = self.layout
        view = _view_3d(context)
        in_camera_view = _in_camera_view(view)
        cam_obj = context.scene.camera

        # Camera row: cycle, pick, select, lock
        row = layout.row(align=True)
        row.operator("cam_manager.cycle_cameras_backward", text="", icon='TRIA_LEFT')
        row.menu(CAM_MANAGER_MT_scene_cameras.bl_idname,
                 text=cam_obj.name if cam_obj else "No Scene Camera", icon='OUTLINER_OB_CAMERA')
        row.operator("cam_manager.cycle_cameras_next", text="", icon='TRIA_RIGHT')
        if cam_obj:
            row.separator()
            row.operator('cameras.select_active_cam', text="", icon='RESTRICT_SELECT_OFF')
            draw_camera_lock_button(row, cam_obj)

        # Actions, then the view toggle
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("view3d.view_camera", text="Exit Camera View" if in_camera_view else "View Camera",
                     icon='VIEW_CAMERA')
        if in_camera_view:
            row.operator("camera.align_camera_to_view", text="Align to View", icon='CAMERA_DATA')
        else:
            row.operator("camera.create_camera_from_view", text="New from View", icon='OUTLINER_OB_CAMERA')
        if view is not None:
            col.prop(view, "lock_camera", text="Lock Camera to View", toggle=True,
                     icon='LOCKVIEW_ON' if view.lock_camera else 'LOCKVIEW_OFF')

        draw_viewport_tools(layout)

        if cam_obj is None:
            layout.label(text="Please specify a scene camera", icon='ERROR')
            return

        header, body = layout.panel("CAM_MANAGER_POPOVER_CAMERA", default_closed=False)
        header.label(text="Camera")
        if body:
            draw_camera_settings(context, body, cam_obj, use_subpanel=True, include_background_images=False)

        header, body = layout.panel("CAM_MANAGER_POPOVER_BACKGROUND", default_closed=False)
        header.prop(cam_obj.data, "show_background_images", text="")
        header.label(text="Background Image")
        if body:
            draw_background_image_settings(context, body, cam_obj)

        header, body = layout.panel("CAM_MANAGER_POPOVER_DISPLAY", default_closed=False)
        header.label(text="Viewport Display")
        if body:
            draw_display_settings(context, body, cam_obj)

        header, body = layout.panel("CAM_MANAGER_POPOVER_RENDER", default_closed=True)
        header.label(text="Render")
        if body:
            draw_render_settings(context, body, cam_obj)


def draw_view3d_header_button(self, context):
    """Camera button in the 3D Viewport header that opens the camera popover."""
    try:
        prefs = context.preferences.addons[__package__].preferences
        if not prefs.show_header_button:
            return
    except (KeyError, AttributeError):
        pass
    cam_obj = context.scene.camera
    self.layout.popover(CAM_MANAGER_PT_camera_popover.bl_idname,
                        text=cam_obj.name if cam_obj else "", icon='VIEW_CAMERA')


class CAMERA_MT_pie_menu(Menu):
    """Quick camera actions. Every item does one thing: a pie menu closes after
    any click, so settings that you change several at a time live in the
    camera popover (Camera Settings…) instead."""
    # label is displayed at the center of the pie menu.
    bl_label = "Active Camera Pie"
    bl_idname = "CAMERA_MT_pie_menu"

    def draw(self, context):
        view = _view_3d(context)
        in_camera_view = _in_camera_view(view)
        cam_obj = context.scene.camera

        pie = self.layout.menu_pie()

        # West / East
        pie.operator("cam_manager.cycle_cameras_backward", text="Previous Camera", icon='TRIA_LEFT')
        pie.operator("cam_manager.cycle_cameras_next", text="Next Camera", icon='TRIA_RIGHT')

        # South
        pie.operator("view3d.view_camera", text="Exit Camera View" if in_camera_view else "View Camera",
                     icon='VIEW_CAMERA')

        # North
        self.draw_quick_settings(context, pie.box(), cam_obj, view)

        # North West / North East stay empty: the mouse passes through their
        # sectors on the way to the North box, and an item there would take
        # the click meant for the box.
        pie.separator()
        pie.separator()

        # South West
        if in_camera_view:
            pie.operator("camera.align_camera_to_view", text="Align Camera to View", icon='CAMERA_DATA')
        else:
            pie.operator("camera.create_camera_from_view", text="New Camera from View", icon='OUTLINER_OB_CAMERA')

        # South East
        draw_camera_settings_button(pie)

    @staticmethod
    def draw_quick_settings(context, box, cam_obj, view):
        """One-click settings; each closes the pie. Top to bottom: menus,
        background images, toggles, and the viewport tools nearest the pie's
        centre."""
        box.ui_units_x = 13
        if cam_obj is None:
            box.label(text="Please specify a scene camera", icon='ERROR')
            return
        cam = cam_obj.data

        col = box.column(align=True)
        col.popover(CAM_MANAGER_PT_lens_presets.bl_idname, text="Lens Preset", icon='PRESET')
        if cam.type != 'ORTHO':
            col.operator_menu_enum("cam_manager.apply_focal_length_preset", "preset",
                                   text=f"Focal Length  {cam.lens:g} mm", icon='DRIVER_DISTANCE')
        resolution = (f"Resolution  {cam.resolution[0]} × {cam.resolution[1]}" if cam.resolution_overwrite
                      else "Resolution  (scene)")
        col.operator_menu_enum("cam_manager.apply_resolution_preset", "preset", text=resolution, icon='IMAGE_DATA')
        col.popover(CAM_MANAGER_PT_composition_guides.bl_idname, text="Composition Guides", icon='GRID')

        if len(cam.background_images) > 0:
            col = box.column(align=True)
            col.prop(cam, "show_background_images", text="Background Images", toggle=True, icon='IMAGE_REFERENCE')
            for index, img in enumerate(cam.background_images):
                row = col.row(align=True)
                row.active = cam.show_background_images and img.show_background_image
                row.prop(img, "alpha", text=background_image_name(img, index), slider=True)
                row = col.row(align=True)
                row.active = cam.show_background_images and img.show_background_image
                row.prop(img, "display_depth", expand=True)

        grid = box.grid_flow(columns=2, even_columns=True, align=True)
        # Guides and passepartout only show while overlays are on.
        if view is not None:
            grid.prop(view.overlay, "show_overlays", text="Overlays", toggle=True, icon='OVERLAY')
        grid.prop(cam, "show_passepartout", text="Passepartout", toggle=True)
        if view is not None:
            grid.prop(view, "lock_camera", text="Lock to View", toggle=True,
                      icon='LOCKVIEW_ON' if view.lock_camera else 'LOCKVIEW_OFF')
        draw_camera_lock_button(grid, cam_obj, text="Lock Camera")
        grid.operator('cameras.select_active_cam', text="Select", icon='RESTRICT_SELECT_OFF')

        draw_viewport_tools(box)


classes = (
    CAM_MANAGER_OT_apply_resolution_preset,
    CAM_MANAGER_OT_apply_focal_length_preset,
    CAM_MANAGER_MT_scene_cameras,
    CAM_MANAGER_PT_lens_presets,
    CAM_MANAGER_PT_composition_guides,
    CAM_MANAGER_PT_camera_popover,
    CAMERA_MT_pie_menu,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    bpy.types.VIEW3D_HT_header.append(draw_view3d_header_button)


def unregister():
    from bpy.utils import unregister_class

    bpy.types.VIEW3D_HT_header.remove(draw_view3d_header_button)

    for cls in reversed(classes):
        if hasattr(cls, 'bl_rna'):
            unregister_class(cls)
