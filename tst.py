import bpy
from bpy.types import (
    GizmoGroup,
)


class OtherWidget(GizmoGroup):
    bl_idname = "OBJECT_GGT_othjer_camera"
    bl_label = "Object Camera Test Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.type == 'CAMERA')

    def setup(self, context):
        arrow = self.gizmos.new("GIZMO_GT_arrow_3d")

        def move_get_x():
            return -context.object.data.dof.focus_distance

        def move_set_x(value):
            context.object.data.dof.focus_distance = -value

        arrow.target_set_handler("offset", get=move_get_x, set=move_set_x)

        arrow.matrix_basis = context.object.matrix_world.normalized()

        self.x_gizmo = arrow

    def refresh(self, context):
        self.x_gizmo.matrix_basis = context.object.matrix_world.normalized()


bpy.utils.register_class(OtherWidget)