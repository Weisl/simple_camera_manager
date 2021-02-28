import bpy
from bpy.types import Menu


# spawn an edit mode selection pie (run while object is in edit mode to get a valid output)


class CAM_MANAGER_MT_PIE_camera_settings(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Cam Manager Pie Menu"
    bl_idname = "CAMERA_MT_pie_menu"

    def draw(self, context):
        layout = self.layout

        view = bpy.context.space_data
        scene = context.scene
        r3d = view.region_3d

        pie = layout.menu_pie()
        # operator_enum will just spread all available options
        # for the type enum of the operator on the pie



        # West
        pie.operator("cam_manager.cycle_cameras_next", text="previous", icon='TRIA_LEFT')

        # East
        pie.operator("cam_manager.cycle_cameras_backward", text="next", icon='TRIA_RIGHT')

        # South
        pie.prop(view, "lock_camera")

        # 8 - TOP

        box = pie.split()

        b = box.box()
        column = b.column()
        self.draw_left_column(context, column)

        b = box.box()
        column = b.column()
        self.draw_center_column(context, column)

        b = box.box()
        column = b.column()
        self.draw_right_column(context, column)

        # 7 - TOP - LEFT
        pie.separator()

        # 9 - TOP - RIGHT
        pie.separator()

    def draw_left_column(self, context, col):
        col.scale_x = 2

        row = col.row()
        row.scale_y = 1.5

        obj = context.object
        row = col.row()
        row.prop(obj.data, "show_composition_thirds")
        row = col.row()
        row.prop(obj.data, "show_composition_center")
        row = col.row()
        row.prop(obj.data, "show_composition_center_diagonal")
        row = col.row()
        row.prop(obj.data, "show_composition_golden")
        row = col.row()
        row.prop(obj.data, "show_composition_golden_tria_a")
        row = col.row()
        row.prop(obj.data, "show_composition_golden_tria_b")
        row = col.row()
        row.prop(obj.data, "show_composition_harmony_tri_a")
        row = col.row()
        row.prop(obj.data, "show_composition_harmony_tri_b")

    def draw_center_column(self, context, col):
        col.scale_y = 1.5
        obj = context.object

        row = col.row(align=True)
        row.prop(obj.data, "lens")
        row = col.row(align=True)
        row.prop(obj.data, "clip_start")
        row = col.row(align=True)
        row.prop(obj.data, "clip_end")

    def draw_right_column(self, context, col):
        row = col.row()
        row.scale_y = 1.5

        cam = context.scene.camera.data

        col.use_property_decorate = False
        row = col.row(align=True)
        sub = row.row(align=True)
        sub.prop(cam, "show_passepartout", text="")
        sub = sub.row(align=True)
        sub.active = cam.show_passepartout
        sub.prop(cam, "passepartout_alpha", text="")
        row.prop_decorator(cam, "passepartout_alpha")


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
