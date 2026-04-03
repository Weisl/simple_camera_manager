import bpy
from bpy.types import Menu


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

def draw_camera_settings(context, layout, cam_obj, use_subpanel=False):
    if cam_obj is None:
        return

    cam = cam_obj.data

    # Resolution
    row = layout.row(align=True)
    col = layout.column(align=True)
    row.prop(cam, "resolution_overwrite")

    row = col.row(align=True)
    row.enabled = cam.resolution_overwrite
    row.prop(cam, "resolution", text="Resolution")
    row.operator_menu_enum("cam_manager.apply_resolution_preset", "preset", text="", icon='DOWNARROW_HLT')

    # Lens
    col = layout.column(align=True)
    row = col.row(align=True)
    row.prop(cam, "lens")
    row.operator_menu_enum("cam_manager.apply_focal_length_preset", "preset", text="", icon='DOWNARROW_HLT')
    row = col.row(align=True)
    row.prop(cam, 'angle')

    col = layout.column(align=True)
    row = col.row(align=True)
    row.prop(cam, "clip_start")
    row = col.row(align=True)
    row.prop(cam, "clip_end")

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

    def draw_background_image_settings(layout):
        layout.label(text="Background Image:")
        col = layout.column(align=True)
        if not cam_obj.visible_get():
            row = layout.row(align=True)
            row.label(text="Camera is hidden", icon='ERROR')

        if len(cam.background_images) > 0:
            for img in cam.background_images:
                row = col.row(align=True)
                row.prop(img, "show_background_image")
                row = col.row(align=True)
                op = row.operator("cam_manager.camera_resolutio_from_image", icon='IMAGE_BACKGROUND')
                op.camera_name = cam.name
                row = col.row(align=True)
                row.prop(img, "alpha")
                row = col.row(align=True)
                row.prop(img, "display_depth")
        else:
            row = col.row(align=True)
            row.label(text="Camera has no Background Images", icon='INFO')

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

        header, body = layout.panel(idname="BACKGROUND_IMG", default_closed=True)
        header.label(text="Background Image:")
        if body:
            draw_background_image_settings(body)
    else:
        draw_focus_settings(layout)
        draw_lighting_settings(layout)


class CAMERA_MT_pie_menu(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Active Camera Pie "
    bl_idname = "CAMERA_MT_pie_menu"

    def draw(self, context):
        layout = self.layout

        view = bpy.context.space_data
        scene = context.scene
        r3d = view.region_3d

        pie = layout.menu_pie()
        # operator_enum will just spread all available options
        # for the type enum of the operator on the pie

        cam_obj = scene.camera

        # West
        pie.operator("cam_manager.cycle_cameras_next", text="previous", icon='TRIA_LEFT')

        # East
        pie.operator("cam_manager.cycle_cameras_backward", text="next", icon='TRIA_RIGHT')

        # South lock camrea to view
        pie.prop(view, "lock_camera")

        # North
        box = pie.split()

        if cam_obj:
            b = box.box()
            column = b.column()
            self.draw_left_column(context, column, cam_obj)

            b = box.box()
            column = b.column()
            self.draw_center_column(context, column, cam_obj)

            b = box.box()
            column = b.column()
            self.draw_right_column(context, column, cam_obj)
        else:
            b = box.box()
            column = b.column()
            column.label(text="Please specify a scene camera", icon='ERROR')

        # North West
        pie.separator()

        # North East
        pie.separator()

        # South West
        if cam_obj:
            if cam_obj.get('lock'):
                op = pie.operator("cam_manager.lock_unlock_camera", icon='UNLOCKED', text='')
                op.camera_name = cam_obj.name
                op.cam_lock = False
            else:
                op = pie.operator("cam_manager.lock_unlock_camera", icon='LOCKED', text='')
                op.camera_name = cam_obj.name
                op.cam_lock = True
        else:
            pie.separator()

        # South East
        pie.operator('cameras.select_active_cam')

        # pie.operator("view3d.view_camera", text="Toggle Camera View", icon='VIEW_CAMERA')

    def draw_left_column(self, context, col, cam_obj):
        row = col.row()
        row.scale_y = 1.5

        cam = cam_obj.data
        scene = context.scene

        row = col.row(align=True)
        row.label(text='Render settings')
        row = col.row(align=True)
        row.prop(cam, "slot")
        op = row.operator('cameras.custom_render', text='Render', icon='RENDER_STILL')
        op.camera_name = cam_obj.name

        row = col.row(align=True)
        row.label(text='Cameras Collection')
        row = col.row(align=True)

        # hide visibility settings for collection if it doesn't yet exist
        if scene.cam_collection.collection:
            row.prop(scene.cam_collection.collection, 'hide_viewport', text='')
            row.prop(context.view_layer.layer_collection.children[scene.cam_collection.collection.name],
                     'hide_viewport', text='')

        row.prop_search(scene.cam_collection, "collection", bpy.data, "collections", text='')
        op = row.operator("cameras.add_collection", icon='OUTLINER_COLLECTION', text='')
        op.object_name = cam_obj.name

        row = col.row(align=True)
        row.label(text='Background Images')

        if not cam_obj.visible_get():
            row = col.row(align=True)
            row.label(text="Camera is hidden", icon='ERROR')

        if len(cam.background_images) > 0:
            for img in cam.background_images:
                row = col.row(align=True)
                row.prop(img, "show_background_image")
                row = col.row(align=True)
                op = row.operator("cam_manager.camera_resolutio_from_image", icon='IMAGE_BACKGROUND')
                op.camera_name = cam.name
                row = col.row(align=True)
                row.prop(img, "alpha")
                row = col.row(align=True)
                row.prop(img, "display_depth")
        else:
            row = col.row(align=True)
            row.label(text="Camera has no Backround Images", icon='INFO')

    def draw_center_column(self, context, layout, cam_obj):
        row = layout.row(align=True)
        row.label(text='Camera Settings')

        draw_camera_settings(context, layout, cam_obj, use_subpanel=False)

    def draw_right_column(self, context, col, cam_obj):
        # col.scale_x = 2

        row = col.row()
        # row.scale_y = 1.5

        cam = cam_obj.data

        view = context.space_data
        overlay = view.overlay
        shading = view.shading

        col.use_property_decorate = False
        row = col.row(align=True)
        row.prop(overlay, "show_overlays", icon='OVERLAY', text="")
        row.label(text='Viewport Display')
        row = col.row(align=True)

        row.separator()

        row = col.row(align=True)
        row.label(text='Passepartout')
        row = col.row(align=True)
        row.prop(cam, "show_passepartout", text="")
        row.active = cam.show_passepartout
        row.prop(cam, "passepartout_alpha", text="")
        row.prop_decorator(cam, "passepartout_alpha")

        row = col.row(align=True)
        row.prop(cam, 'show_name')

        row = col.row()
        row.prop(cam, "show_composition_thirds")
        row = col.row()
        row.prop(cam, "show_composition_center")
        row = col.row()
        row.prop(cam, "show_composition_center_diagonal")
        row = col.row()
        row.prop(cam, "show_composition_golden")


classes = (
    CAM_MANAGER_OT_apply_resolution_preset,
    CAM_MANAGER_OT_apply_focal_length_preset,
    CAMERA_MT_pie_menu,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
