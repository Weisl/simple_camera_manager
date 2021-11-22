from bpy.types import (
    GizmoGroup,
    Gizmo
)

# Coordinates (each one is a line).
custom_shape_verts_02 = (
    (0.2, -1.0, 0.0), (1.0, -1.0, 0.0),
    (1.0, -1.0, 0.0), (1.0, -0.2, 0.0),
    (-1.0, -0.2, 0.0), (-1.0, -1.0, 0.0),
    (-1.0, -1.0, 0.0), (-0.2, -1.0, 0.0),
    (-1.0, 1.0, 0.0), (-1.0, 0.2, 0.0),
    (-0.2, 1.0, 0.0), (-1.0, 1.0, 0.0),
    (1.0, 0.2, 0.0), (1.0, 1.0, 0.0),
    (1.0, 1.0, 0.0), (0.2, 1.0, 0.0)
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
        # gz2 = self.gizmos.new("GIZMO_GT_dial_3d")

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
        ob = context.object

        arrow = self.gizmos.new(MyCustomShapeWidget.bl_idname)
        # arrow.use_draw_offset_scale = False

        arrow.use_draw_scale = False
        arrow.use_draw_offset_scale = False

        # Needed to keep the scale constant
        arrow.scale_basis = 1.0

        def move_get_x():
            return -ob.data.dof.focus_distance

        def move_set_x(value):
            ob.data.dof.focus_distance = -value

        # arrow.target_set_handler("offset", get=move_get_x, set=move_set_x)
        arrow.target_set_prop("offset", ob.data.dof, "focus_distance")

        arrow.matrix_basis = context.object.matrix_world.normalized()

        self.x_gizmo = arrow

    def refresh(self, context):
        self.x_gizmo.matrix_basis = context.object.matrix_world.normalized()


class MyCustomShapeWidget(Gizmo):
    bl_idname = "VIEW3D_GT_auto_facemap"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
    )

    __slots__ = (
        "custom_shape",
        "init_mouse_y",
        "init_value",
    )

    def _update_offset_matrix(self):
        # offset behind the light
        self.matrix_offset.col[3][2] = self.target_get_value("offset") * -1

    def draw(self, context):
        self._update_offset_matrix()
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self._update_offset_matrix()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        if not hasattr(self, "custom_shape"):
            # type (string) – The type of shape to create in (POINTS, LINES, TRIS, LINE_STRIP).
            # verts (sequence of of 2D or 3D coordinates.) – Coordinates.
            # display_name (Callable that takes a string and returns a string.) – Optional callback that takes the full path, returns the name to display.
            self.custom_shape = self.new_custom_shape('LINES', custom_shape_verts_02)

    def invoke(self, context, event):
        self.init_mouse_y = event.mouse_y
        self.init_value = self.target_get_value("offset")
        return {'RUNNING_MODAL'}

    def exit(self, context, cancel):
        context.area.header_text_set(None)
        if cancel:
            self.target_set_value("offset", self.init_value)

    def modal(self, context, event, tweak):
        delta = (event.mouse_y - self.init_mouse_y) / 10.0
        if 'SNAP' in tweak:
            delta = round(delta)
        if 'PRECISE' in tweak:
            delta /= 10.0
        value = self.init_value - delta
        self.target_set_value("offset", value)
        context.area.header_text_set("My Gizmo: %.4f" % value)
        return {'RUNNING_MODAL'}







classes = (
    # CameraRotationWidgets,
    CameraFocusDistance,
    MyCustomShapeWidget,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

