from bpy.types import (
    GizmoGroup,
)

class CameraRotationWidgets(GizmoGroup):
    bl_idname = "OBJECT_GGT_rotate_camera"
    bl_label = "Object Camera Rotation Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.type == 'CAMERA')

    def setup(self, context):
        # Run an operator using the dial gizmo

        ob = context.object

        # Rotation Gizmo
        gz = self.gizmos.new("GIZMO_GT_dial_3d")

        # Gizmo types ttps://blender.stackexchange.com/questions/131685/gizmo-types-in-blender-2-8
        gz2 = self.gizmos.new("GIZMO_GT_dial_3d")

        props = gz.target_set_operator("transform.rotate")
        props.constraint_axis = False, False, True
        props.orient_type = 'LOCAL'
        props.release_confirm = True

        gz.matrix_basis = ob.matrix_world.normalized()
        gz.line_width = 3

        gz.color = 0.8, 0.8, 0.8
        gz.alpha = 0.5

        gz.color_highlight = 1.0, 1.0, 1.0
        gz.alpha_highlight = 1.0

        self.roll_gizmo = gz

    def refresh(self, context):
        ob = context.object
        gz = self.roll_gizmo
        gz.matrix_basis = ob.matrix_world.normalized()



class CameraFocusDistance(GizmoGroup):
    bl_idname = "OBJECT_GGT_focus_distance_camera"
    bl_label = "Camera Focus Distance Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.type == 'CAMERA')

    def setup(self, context):
        # Run an operator using the dial gizmo

        ob = context.object

        # Gizmo types ttps://blender.stackexchange.com/questions/131685/gizmo-types-in-blender-2-8
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")

        props = gz.target_set_prop("offset", ob.data, "lens")

        gz.matrix_basis = ob.matrix_world.normalized()
        gz.line_width = 3

        gz.color = 0.8, 0.8, 0.8
        gz.alpha = 0.5

        gz.color_highlight = 1.0, 1.0, 1.0
        gz.alpha_highlight = 1.0

        self.focal_lenght_gixmo = gz

    def refresh(self, context):
        ob = context.object
        gz = self.focal_lenght_gixmo
        gz.matrix_basis = ob.matrix_world.normalized()


classes = (
    CameraRotationWidgets,
    CameraFocusDistance,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

