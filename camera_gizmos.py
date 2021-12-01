from bpy.types import (
    GizmoGroup,
    Gizmo
)
from .dolly_zoom_modal import calculate_target_width

import mathutils


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

class CameraFocusDistance(GizmoGroup):
    bl_idname = "OBJECT_GGT_focus_distance_camera"
    bl_label = "Camera Focus Distance Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SHOW_MODAL_ALL', 'DEPTH_3D'}

    cam = None

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.type == 'CAMERA')

    def setup(self, context):
        camera = context.object
        self.cam = camera

        gizmo = self.gizmos.new(MyCustomShapeWidget.bl_idname)
        # gizmo = self.gizmos.new("GIZMO_GT_arrow_3d")
        # gizmo = self.gizmos.new("GIZMO_GT_primitive_3d")
        # gizmo.use_draw_offset_scale = False

        gizmo.use_draw_scale = False
        gizmo.use_draw_offset_scale = False
        gizmo.use_draw_modal = True

        gizmo.color = (1.0, 1.0, 1.0)
        gizmo.color_highlight = (1.0, 1.0, 0.0)

        #Draw only when hovering
        # gizmo.use_draw_hover = True

        def get_dolly_zoom_target_distance():
            if self.cam:
                return self.cam.data.dolly_zoom_target_distance
            else:
                return (0.0,)

        def set_dolly_zoom_target_distance(value):
            if self.cam:
                print('ENTERED')
                self.cam.data.dolly_zoom_target_distance = value

        # gizmo.target_set_prop("offset", camera.data, "dolly_zoom_target_distance")
        gizmo.target_set_handler('offset', get=get_dolly_zoom_target_distance, set=set_dolly_zoom_target_distance)

        # Needed to keep the scale constant
        gizmo.scale_basis = 1.0

        gizmo.matrix_basis = camera.matrix_world.normalized()

        self.distance_gizmo = gizmo


    def refresh(self, context):
        camera = context.object

        self.cam = camera


        w_matrix = self.cam.matrix_world.copy()
        orig_loc, orig_rot, orig_scale = w_matrix.normalized().decompose()

        orig_loc_mat = mathutils.Matrix.Translation(orig_loc)
        orig_rot_mat = orig_rot.to_matrix().to_4x4()

        scale = calculate_target_width(self.cam.data.dolly_zoom_target_distance, self.cam.data.angle)

        scale_matrix_x2 = mathutils.Matrix.Scale(scale, 4, (1.0, 0.0, 0.0))
        scale_matrix_y2 = mathutils.Matrix.Scale(scale, 4, (0.0, 1.0, 0.0))
        scale_matrix_z2 = mathutils.Matrix.Scale(1, 4, (0.0, 0.0, 1.0))

        scale_mat = scale_matrix_x2 @ scale_matrix_y2 @ scale_matrix_z2

        # assemble the new matrix
        mat_out = orig_loc_mat @ orig_rot_mat @ scale_mat

        self.distance_gizmo.matrix_basis = mat_out


class MyCustomShapeWidget(Gizmo):
    bl_idname = "Custom_Dolly_Gizmo"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
        # {"id": "offset", "type": 'TUPLE', "array_length": 1},
    )
    #

    __slots__ = (
        "custom_shape",
        "init_mouse_x",
        "init_value",
    )

    def _update_offset_matrix(self):
        # offset behind the light
        print("VALUE" + str(self.target_get_value('offset')[0]))
        self.matrix_offset.col[3][2] = float(self.target_get_value('offset')[0]) * -1

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
        self.init_mouse_x = event.mouse_x
        self.init_value = self.target_get_value('offset')[0]
        return {'RUNNING_MODAL'}

    def exit(self, context, cancel):
        context.area.header_text_set(None)
        # if cancel:
            # self.target_set_value("offset", self.init_value)

    def modal(self, context, event, tweak):
        delta = (event.mouse_x - self.init_mouse_x) / 10.0
        if 'SNAP' in tweak:
            delta = round(delta)
        if 'PRECISE' in tweak:
            delta /= 10.0
        value = self.init_value + delta

        # Set value as a Tuple, it doesn't work otherwise
        self.target_set_value("offset", (value,))

        context.area.header_text_set("My Gizmo: %.4f" % value)
        return {'RUNNING_MODAL'}



classes = (
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

