import bgl
import blf
import bpy
import gpu
import math
import numpy

from bpy.props import IntProperty, FloatProperty

from gpu_extras.batch import batch_for_shader
from mathutils import Vector


def distance_vec(point1: Vector, point2: Vector):
    """Calculates distance between two points."""
    return (point2 - point1).length


def draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, text):
    blf.color(font_id,1.0,1.0,1.0,1.0)
    blf.position(font_id, left_margin, i * vertical_px_offset, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, text)
    i += 1
    return i

def draw_callback_px(self, context):
    """Draw 3d viewport text for the dolly zoom modal operator"""
    scene = context.scene

    font_id = 0  # XXX, need to find out how best to get this.
    vertical_px_offset = 30
    left_margin = 50
    i = 1

    x = str(math.degrees(self.current_camera_fov))
    text = 'FOV: {}'.format(x)
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, text)

    x = str(self.camera_focal_length)
    text = 'Focal Length: {}'.format(x)
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, text)

    x = str(self.distance)
    text = 'DISTANCE: {}'.format(x)
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, text)

    x = str(self.delta)
    text = 'DELTA: {}'.format(x)
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, text)


class CAM_MANAGER_OT_dolly_zoom(bpy.types.Operator):
    """Modlar operator that keeps the object size in viewport when changing the focal lenght """
    bl_idname = "cam_manager.modal_camera_dolly_zoom"
    bl_label = "Dolly Zoom"
    bl_description = "Change focal lenght while keeping the target object at the same size in the camera view"
    bl_options = {'REGISTER', 'UNDO'}

    # # Initial mouse position
    mouse_initial_x: IntProperty()
    # # camera position. Only using Y Axis for now
    # camera_location: FloatProperty()
    # # FOV changes
    # current_camera_fov: FloatProperty()
    # initial_camera_fov: FloatProperty()
    # # target object
    # target_width: FloatProperty(default=4, name="Width")


    def modal(self, context, event):
        '''Calculate the FOV from the changed location to the target object '''

        camera = self.camera
        cameraObj = self.cameraObj

        scene = context.scene
        # cancel operator
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cameraObj.location = self.camera_location_initial
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass
            return {'CANCELLED'}

        # apply operator
        elif event.type == 'LEFTMOUSE':
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass
            return {'FINISHED'}

        elif event.type == 'MOUSEMOVE':
            factor = 0.015
            if event.ctrl == True:
                factor = 0.15
            elif event.shift == True:
                factor = 0.001

            # calculate mouse movement and offset camera
            delta = int(self.mouse_initial_x - event.mouse_x)

            cam_offset = round((delta * factor), 4)

            # if self.cam_offset != cam_offset:
            #     self.cam_offset = cam_offset

            # one blender unit in z-direction
            vec = Vector((0.0, 0.0, cam_offset))

            # vec aligned to local axis in Blender 2.8+
            vec_rot = vec @ self.cam_inverted_matrix

            cameraObj.location = self.camera_location_initial + vec_rot

            # get camera world position and target position
            cam_pos = self.cameraObj.matrix_world.to_translation()

            cam_vector = Vector(cam_pos)
            target_pos = self.target
            distance = distance_vec(cam_vector, target_pos)
            self.distance = distance

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

            # Camera Object Settings
            self.cameraObj = camera
            self.camera = camera.data
            self.camera_location_initial = camera.location.copy()
            # get world matrix and invert
            inv = camera.matrix_world.copy()
            inv.invert()
            self.cam_inverted_matrix = inv

            # Camera lens settings
            self.current_camera_fov = camera.data.angle
            self.camera_focal_length = camera.data.lens

            # Target
            self.target = Vector((0.0, 0.0, 0.0))
            self.target_width = 4

            # Mouse
            self.mouse_initial_x = event.mouse_x

            # debug values
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
    CAM_MANAGER_OT_dolly_zoom,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    scene = bpy.types.Scene
    del scene.dolly_zoom_sensitivity
