import math

import bgl
import blf
import bpy
import gpu

from bpy.props import IntProperty, FloatProperty
from bpy.types import (
    Gizmo,
    GizmoGroup,
)
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from bpy.props import (
    FloatVectorProperty,
)

def distance_vec(point1: Vector, point2: Vector):
    """Calculates distance between two points."""
    return (point2 - point1).length


def draw_callback_px(self, context):
    """Draw 3d viewport text for the dolly zoom modal operator"""
    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
    blf.position(font_id, 15, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "FOV" + str(math.degrees(self.current_camera_fov)))

    blf.position(font_id, 15, 60, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Focal Length" + str(self.camera_focal_length))

    blf.position(font_id, 15, 90, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "DISTANCE" + str(self.distance))

    scene = context.scene
    blf.position(font_id, 15, 120, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Mouse Sensitivity" + str(scene.dolly_zoom_sensitivity))

    # 50% alpha, 2 pixel width line
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(2)
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": self.mouse_path})
    shader.bind()
    shader.uniform_float("color", (0.0, 0.0, 0.0, 0.5))
    batch.draw(shader)

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)


class MyCameraWidgetGroup(GizmoGroup):
    bl_idname = "OBJECT_GGT_test_camera"
    bl_label = "Object Camera Test Widget"
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
        gz = self.gizmos.new("GIZMO_GT_dial_3d")
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


# Coordinates (each one is a triangle).
custom_shape_verts = (
    (3.0, 1.0, -1.0), (2.0, 2.0, -1.0), (3.0, 3.0, -1.0),
    (1.0, 3.0, 1.0), (3.0, 3.0, -1.0), (1.0, 3.0, -1.0),
    (3.0, 3.0, 1.0), (3.0, 1.0, -1.0), (3.0, 3.0, -1.0),
    (2.0, 0.0, 1.0), (3.0, 1.0, -1.0), (3.0, 1.0, 1.0),
    (2.0, 0.0, -1.0), (2.0, 2.0, 1.0), (2.0, 2.0, -1.0),
    (2.0, 2.0, -1.0), (0.0, 2.0, 1.0), (0.0, 2.0, -1.0),
    (1.0, 3.0, 1.0), (2.0, 2.0, 1.0), (3.0, 3.0, 1.0),
    (0.0, 2.0, -1.0), (1.0, 3.0, 1.0), (1.0, 3.0, -1.0),
    (2.0, 2.0, 1.0), (3.0, 1.0, 1.0), (3.0, 3.0, 1.0),
    (2.0, 2.0, -1.0), (1.0, 3.0, -1.0), (3.0, 3.0, -1.0),
    (-3.0, -1.0, -1.0), (-2.0, -2.0, -1.0), (-3.0, -3.0, -1.0),
    (-1.0, -3.0, 1.0), (-3.0, -3.0, -1.0), (-1.0, -3.0, -1.0),
    (-3.0, -3.0, 1.0), (-3.0, -1.0, -1.0), (-3.0, -3.0, -1.0),
    (-2.0, 0.0, 1.0), (-3.0, -1.0, -1.0), (-3.0, -1.0, 1.0),
    (-2.0, 0.0, -1.0), (-2.0, -2.0, 1.0), (-2.0, -2.0, -1.0),
    (-2.0, -2.0, -1.0), (0.0, -2.0, 1.0), (0.0, -2.0, -1.0),
    (-1.0, -3.0, 1.0), (-2.0, -2.0, 1.0), (-3.0, -3.0, 1.0),
    (0.0, -2.0, -1.0), (-1.0, -3.0, 1.0), (-1.0, -3.0, -1.0),
    (-2.0, -2.0, 1.0), (-3.0, -1.0, 1.0), (-3.0, -3.0, 1.0),
    (-2.0, -2.0, -1.0), (-1.0, -3.0, -1.0), (-3.0, -3.0, -1.0),
    (1.0, -1.0, 0.0), (-1.0, -1.0, 0.0), (0.0, 0.0, -5.0),
    (-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (0.0, 0.0, 5.0),
    (1.0, -1.0, 0.0), (1.0, 1.0, 0.0), (0.0, 0.0, 5.0),
    (1.0, 1.0, 0.0), (-1.0, 1.0, 0.0), (0.0, 0.0, 5.0),
    (-1.0, 1.0, 0.0), (-1.0, -1.0, 0.0), (0.0, 0.0, 5.0),
    (-1.0, -1.0, 0.0), (-1.0, 1.0, 0.0), (0.0, 0.0, -5.0),
    (-1.0, 1.0, 0.0), (1.0, 1.0, 0.0), (0.0, 0.0, -5.0),
    (1.0, 1.0, 0.0), (1.0, -1.0, 0.0), (0.0, 0.0, -5.0),
    (3.0, 1.0, -1.0), (2.0, 0.0, -1.0), (2.0, 2.0, -1.0),
    (1.0, 3.0, 1.0), (3.0, 3.0, 1.0), (3.0, 3.0, -1.0),
    (3.0, 3.0, 1.0), (3.0, 1.0, 1.0), (3.0, 1.0, -1.0),
    (2.0, 0.0, 1.0), (2.0, 0.0, -1.0), (3.0, 1.0, -1.0),
    (2.0, 0.0, -1.0), (2.0, 0.0, 1.0), (2.0, 2.0, 1.0),
    (2.0, 2.0, -1.0), (2.0, 2.0, 1.0), (0.0, 2.0, 1.0),
    (1.0, 3.0, 1.0), (0.0, 2.0, 1.0), (2.0, 2.0, 1.0),
    (0.0, 2.0, -1.0), (0.0, 2.0, 1.0), (1.0, 3.0, 1.0),
    (2.0, 2.0, 1.0), (2.0, 0.0, 1.0), (3.0, 1.0, 1.0),
    (2.0, 2.0, -1.0), (0.0, 2.0, -1.0), (1.0, 3.0, -1.0),
    (-3.0, -1.0, -1.0), (-2.0, 0.0, -1.0), (-2.0, -2.0, -1.0),
    (-1.0, -3.0, 1.0), (-3.0, -3.0, 1.0), (-3.0, -3.0, -1.0),
    (-3.0, -3.0, 1.0), (-3.0, -1.0, 1.0), (-3.0, -1.0, -1.0),
    (-2.0, 0.0, 1.0), (-2.0, 0.0, -1.0), (-3.0, -1.0, -1.0),
    (-2.0, 0.0, -1.0), (-2.0, 0.0, 1.0), (-2.0, -2.0, 1.0),
    (-2.0, -2.0, -1.0), (-2.0, -2.0, 1.0), (0.0, -2.0, 1.0),
    (-1.0, -3.0, 1.0), (0.0, -2.0, 1.0), (-2.0, -2.0, 1.0),
    (0.0, -2.0, -1.0), (0.0, -2.0, 1.0), (-1.0, -3.0, 1.0),
    (-2.0, -2.0, 1.0), (-2.0, 0.0, 1.0), (-3.0, -1.0, 1.0),
    (-2.0, -2.0, -1.0), (0.0, -2.0, -1.0), (-1.0, -3.0, -1.0),
)


class CAM_MANAGER_OT_dolly_zoom(Gizmo):
    """Modal operator that keeps the object size in viewport when changing the focal lenght """

    bl_idname = "cam_manager.modal_camera_dolly_zoom"
    # bl_label = "Dolly Zoom"
    # bl_description = "Change focal lenght while keeping the target object at the same size in the camera view"
    # bl_options = {'REGISTER', 'UNDO'}

    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
    )

    # advanced python magic from the blender python template
    __slots__ = (
        "custom_shape",
        "init_mouse_y",
        "init_value",
    )

    # Initial mouse position
    mouse_initial_x: IntProperty()

    # camera position. Only using Y Axis for now
    camera_location: FloatProperty()

    # FOV changes
    current_camera_fov: FloatProperty()
    initial_camera_fov: FloatProperty()

    # target object
    target_width: FloatProperty(default=4, name="Width")

    target_loc: FloatVectorProperty(
        size=3,
        default=(0, 0, 0),
    )

    def _update_offset_matrix(self):
        # offset behind the camera
        self.matrix_offset.col[3][2] = self.target_get_value("offset") / -10

    def draw(self, context):
        #draw updated gizmo
        self._update_offset_matrix()
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self._update_offset_matrix()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        # create custom shape
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('TRIS', custom_shape_verts)

    def exit(self, context, cancel):
        context.area.header_text_set(None)
        if cancel:
            self.target_set_value("offset", self.init_value)


    def modal(self, context, event):
        '''Calculate the FOV from the changed location to the target object '''

        camera = self.camera
        cameraObj = self.cameraObj

        scene = context.scene
        # cancel operator
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cameraObj.location.y = self.camera_location_initial
            return {'CANCELLED'}

        # apply operator
        elif event.type == 'LEFTMOUSE':
            return {'FINISHED'}

        if event.type == 'UP_ARROW':
            # Increase Mouse sensitivity
            scene.dolly_zoom_sensitivity_02 *= 2
        elif event.type == 'DOWN_ARROW':
            # Decrease Mouse Sensitivity
            scene.dolly_zoom_sensitivity_02 *= 0.5


        # default was 10
        delta = (event.mouse_y - self.init_mouse_y) / scene.dolly_zoom_sensitivity_02

        # if 'SNAP' in tweak:
        #     delta = round(delta)
        # if 'PRECISE' in tweak:
        #     # default was 10
        #     delta /= 0.01

        # one blender unit in z-direction
        vec = Vector((0.0, 0.0, delta * scene.dolly_zoom_sensitivity))

        # get world matrix and invert
        inv = cameraObj.matrix_world.copy()
        inv.invert()

        # vec aligned to local axis in Blender 2.8+
        vec_rot = vec @ inv

        cameraObj.location = cameraObj.location + vec_rot

        # get camera world position and target position
        cam_pos = self.cameraObj.matrix_world.to_translation()
        cam_vector = Vector(cam_pos)
        target_pos =

        distance = distance_vec(cam_vector, target_pos)
        self.distance = distance
        print("distance = " + str(distance))

        # Dolly Zoom computation
        field_of_view = 2 * math.atan(self.target_width / distance)

        # Set camera field of view and
        camera.angle = field_of_view
        self.current_camera_fov = field_of_view
        self.camera_focal_length = camera.lens

        value = self.init_value - delta
        self.target_set_value("offset", value)
        context.area.header_text_set("My Gizmo: %.4f Sensitivity: %.4f " % (value, scene.dolly_zoom_sensitivity_02))


        return {'RUNNING_MODAL'}



    def invoke(self, context, event):
        if context.scene.camera:
            camera = context.scene.camera

            self.cameraObj = camera
            self.camera = camera.data

            self.target = Vector((0.0, 0.0, 0.0))
            self.mouse_initial_x = event.mouse_x

            self.camera_location_initial = camera.location.y
            self.camera_location = camera.location.y

            # debug values
            self.current_camera_fov = camera.data.angle
            self.distance = 0

            # the arguments we pass the the callback
            args = (self, context)
            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

            self.init_mouse_y = event.mouse_y
            self.init_value = self.target_get_value("offset")

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:

            self.report({'WARNING'}, "No scene camera assigned")
            return {'CANCELLED'}




class CustomCamWidgetGroup(GizmoGroup):
    bl_idname = "OBJECT_GGT_CAMERA_test"
    bl_label = "Test CAMERA Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.type == 'CAMERA')

    # Helper functions
    @staticmethod
    def my_target_operator(context):
        wm = context.window_manager
        op = wm.operators[-1] if wm.operators else None
        if isinstance(op, CAM_MANAGER_OT_dolly_zoom):
            return op
        return None

    def setup(self, context):
        ob = context.object

        # Gizmo settings
        gz = self.gizmos.new(CAM_MANAGER_OT_dolly_zoom.bl_idname)
        gz.target_set_prop("offset", ob.data, "angle")

        # Color
        gz.color = 1.0, 0.5, 1.0
        gz.alpha = 0.5

        gz.color_highlight = 1.0, 1.0, 1.0
        gz.alpha_highlight = 0.5

        # units are large, so shrink to something more reasonable.
        gz.scale_basis = 0.1
        gz.use_draw_modal = True

        self.dolly_zoom_gizmo = gz

    def refresh(self, context):
        ob = context.object
        gz = self.dolly_zoom_gizmo
        gz.matrix_basis = ob.matrix_world.normalized()


classes = (
    CAM_MANAGER_OT_dolly_zoom,
    CustomCamWidgetGroup,
    MyCameraWidgetGroup
)


def register():
    scene = bpy.types.Scene

    # properties stored in blender scene
    scene.dolly_zoom_sensitivity = FloatProperty(default=0.0008,
                                                 description='Mouse sensitivity for controlling the dolly zoom',
                                                 name="Mouse Sensitivity")
    # properties stored in blender scene
    scene.dolly_zoom_sensitivity_02 = FloatProperty(default=0.1,
                                                    description='Mouse sensitivity for controlling the dolly zoom',
                                                    name="Mouse Sensitivity")
    # properties stored in blender scene
    scene.dolly_zoom_sensitivity_03 = FloatProperty(default=0.1,
                                                    description='Mouse sensitivity for controlling the dolly zoom',
                                                    name="Mouse Sensitivity")

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    scene = bpy.types.Scene
    del scene.dolly_zoom_sensitivity
