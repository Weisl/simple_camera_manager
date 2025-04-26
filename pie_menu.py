import bpy
from bpy.types import Menu


# spawn an edit mode selection pie (run while object is in edit mode to get a valid output)

def draw_camera_settings(context, layout, cam_obj , use_subpanel=False):
    if cam_obj is None:
        return

    # col.scale_y = 1
    cam = cam_obj.data

    row = layout.row(align=True)
    row.prop(cam, "resolution", text="Resolution")

    # Lens
    col = layout.column(align=True)
    row = col.row(align=True)
    row.prop(cam, "lens")
    row = col.row(align=True)
    row.prop(cam, 'angle')

    col = layout.column(align=True)
    row = col.row(align=True)
    row.prop(cam, "clip_start")
    row = col.row(align=True)
    row.prop(cam, "clip_end")

    # Draw the panel header
    header, body = layout.panel(idname="FOCUS_PANEL", default_closed=True)

    # header
    dof = cam.dof
    header.label(text=f"Focus:")
    header.prop(dof, 'use_dof')

    if body:
        split = body.split()

        col = split.column()
        col.prop(dof, "focus_object", text="Focus on Object")
        if dof.focus_object and dof.focus_object.type == 'ARMATURE':
            col.prop_search(dof, "focus_subtarget", dof.focus_object.data, "bones", text="Focus Bone")

        sub = col.row()
        sub.active = dof.focus_object is None
        sub.prop(dof, "focus_distance", text="Focus Distance")
        sub.operator(
            "ui.eyedropper_depth",
            icon='EYEDROPPER',
            text="").prop_data_path = "scene.camera.data.dof.focus_distance"

    # Draw the panel header
    header, body = layout.panel(idname="LIGHT_PANEL", default_closed=True)
    header.label(text=f"Camera Lighting:")
    if body:
        col = body.column(align=False)

        row = col.row(align=True)
        row.prop(cam, 'exposure', text='Exposure')
        row = col.row(align=True)
        row.prop(cam, 'world', text='World')

    header, body = layout.panel(idname="BACKGROUND_IMG", default_closed=True)
    header.label(text=f"Background Image:")

    if body:
        col = body.column(align=True)
        if not cam_obj.visible_get():
            row = body.row(align=True)
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
    col = layout.column(align=True)


class CAM_MANAGER_MT_PIE_camera_settings(Menu):
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

        draw_camera_settings(context, layout, cam_obj)


    
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
    CAM_MANAGER_MT_PIE_camera_settings,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
