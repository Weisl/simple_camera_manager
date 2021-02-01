import math

import bgl
import blf
import bpy
import gpu
from bpy.props import IntProperty, FloatProperty
from gpu_extras.batch import batch_for_shader
from mathutils import Vector


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


class CAMERA_OT_dolly_zoom(bpy.types.Operator):
    """Modlar operator that keeps the object size in viewport when changing the focal lenght """
    bl_idname = "utilities.modal_camera_dolly_zoom"
    bl_label = "Dolly Zoom"
    bl_description = "Change focal lenght while keeping the target object at the same size in the camera view"
    bl_options = {'REGISTER', 'UNDO'}

    # Initial mouse position
    mouse_initial_x: IntProperty()

    # camera position. Only using Y Axis for now
    camera_location: FloatProperty()

    # FOV changes
    current_camera_fov: FloatProperty()
    initial_camera_fov: FloatProperty()

    # target object
    target_width: FloatProperty(default=4, name="Width")

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



        elif event.type == 'UP_ARROW':
            # Increase Mouse sensitivity

            scene.dolly_zoom_sensitivity *= 1.5

        elif event.type == 'DOWN_ARROW':
            # Decrease Mouse Sensitivity
            scene.dolly_zoom_sensitivity /= 1.5

        elif event.type == 'MOUSEMOVE':

            # calculate mouse movement and offset camera
            delta = self.mouse_initial_x - event.mouse_x

            # Camera offset in y axis
            # cameraObj.location.y = self.camera_location + delta * self.mouse_sensitivity

            # one blender unit in x-direction
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
            target_pos = self.target

            distance = distance_vec(cam_vector, target_pos)
            self.distance = distance
            print("distance = " + str(distance))

            # Dolly Zoom computation
            field_of_view = 2 * math.atan(self.target_width / distance)

            # Set camera field of view and
            camera.angle = field_of_view
            self.current_camera_fov = field_of_view
            self.camera_focal_length = camera.lens

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

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:

            self.report({'WARNING'}, "No scene camera assigned")
            return {'CANCELLED'}


classes = (
    CAMERA_OT_dolly_zoom,
)


def register():
    scene = bpy.types.Scene

    # properties stored in blender scene
    scene.dolly_zoom_sensitivity = FloatProperty(default=0.0008, name="Mouse Sensitivity")

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    scene = bpy.types.Scene
    del scene.dolly_zoom_sensitivity
