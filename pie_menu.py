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

        pie = layout.menu_pie()
        # operator_enum will just spread all available options
        # for the type enum of the operator on the pie

        obj = context.object

        # West
        pie.operator("cam_manager.cycle_cameras_next", text="previous", icon='TRIA_LEFT')
        # East
        pie.operator("cam_manager.cycle_cameras_backward", text="next", icon='TRIA_RIGHT')

        # South
        pie.prop(view, "lock_camera")

        # SouthWest
        if obj.type == 'CAMERA':
            if obj.get('lock'):
                op = pie.operator("cam_manager.lock_unlock_camera", icon='LOCKED', text='')
                op.camera_name = obj.name
                op.cam_lock = False
            else:
                op = pie.operator("cam_manager.lock_unlock_camera", icon='UNLOCKED', text='')
                op.camera_name = obj.name
                op.cam_lock = True

            # North
            row = pie.column()
            row.prop(obj.data, "lens")
            row.prop(obj.data, "clip_start")
            row.prop(obj.data, "clip_end")



            # NorthWest

            op = pie.operator("cam_manager.change_scene_camera", text='', icon='VIEW_CAMERA')
            op.camera_name = obj.name
            op.switch_to_cam = False

        # Northeast
        if obj.type == 'CAMERA':
            row = pie.column()
            row.prop(obj.data, "show_composition_thirds")
            row.prop(obj.data, "show_composition_center")
            row.prop(obj.data, "show_composition_center_diagonal")
            row.prop(obj.data, "show_composition_golden")
            row.prop(obj.data, "show_composition_golden_tria_a")
            row.prop(obj.data, "show_composition_golden_tria_b")
            row.prop(obj.data, "show_composition_harmony_tri_a")
            row.prop(obj.data, "show_composition_harmony_tri_b")

        if obj.type == 'CAMERA' and len(context.object.data.background_images) > 0:
            row = pie.column()
            row.prop(obj.data.background_images[0], "display_depth")
            row.prop(obj.data.background_images[0], "alpha")


        # SouthEast




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
