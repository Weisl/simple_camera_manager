import bgl
import blf
import bpy
import gpu
import math
import numpy

from bpy.props import IntProperty, FloatProperty

from gpu_extras.batch import batch_for_shader
from mathutils import Vector

def set_cam_values(cam_dic, camera, target_vector):
    # Initial Camera Position and Location Matrix
    cam_dic['cam_location'] = camera.location.copy()
    # get world matrix and invert
    inv = camera.matrix_world.copy()
    inv.invert()
    cam_dic['inverted_matrix'] = inv

    # Initial Camera Lens Settings
    cam_dic['camera_fov'] = camera.data.angle
    cam_dic['camera_focal_length'] = camera.data.angle

    # Intitial Distance
    cam_pos = camera.matrix_world.to_translation()
    cam_vector = Vector(cam_pos)
    distance = distance_vec(cam_vector, target_vector)
    cam_dic['distance'] = distance

    return cam_dic

def distance_vec(point1: Vector, point2: Vector):
    """Calculates distance between two points."""
    return (point2 - point1).length


def draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, name, value, initial_value = None):
    text = '{name:}:'.format(name=name)
    text2 = '{value:.2f}'.format(value=value)

    blf.size(font_id, 20, 72)

    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
    blf.position(font_id, left_margin, i * vertical_px_offset, 0)
    blf.draw(font_id, text)

    blf.color(font_id, 1.0, 1.0, 0.5, 1.0)

    if self.ignore_input:
        blf.color(font_id, 0.5, 0.5, 0.5, 1.0)

    blf.position(font_id, left_margin + 150, i * vertical_px_offset, 0)
    blf.draw(font_id, text2)

    #optional original value
    if initial_value:
        text3 = '{initial_value:.2f}'.format(initial_value=initial_value)
        blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
        blf.position(font_id, left_margin + 350, i * vertical_px_offset, 0)
        blf.draw(font_id, text3)

    i += 1

    return i

def draw_callback_px(self, context):
    """Draw 3d viewport text for the dolly zoom modal operator"""
    scene = context.scene

    font_id = 0  # XXX, need to find out how best to get this.
    vertical_px_offset = 30
    left_margin = bpy.context.area.width/2 - 200
    i = 1

    x = math.degrees(self.current_camera_fov)
    print(self.initial_cam_settings['camera_fov'])
    y = math.degrees(self.initial_cam_settings['camera_fov'])
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, 'FOV:', x, initial_value=y)


    x = self.current_focal_length
    y = self.initial_cam_settings['camera_focal_length']
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, 'Focal Length:', x, initial_value=y)


    x = self.distance
    y = self.initial_cam_settings['distance']
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, 'DISTANCE:', x, initial_value=y)



class CAM_MANAGER_OT_dolly_zoom(bpy.types.Operator):
    """Modlar operator that keeps the object size in viewport when changing the focal lenght """
    bl_idname = "cam_manager.modal_camera_dolly_zoom"
    bl_label = "Dolly Zoom"
    bl_description = "Change focal lenght while keeping the target object at the same size in the camera view"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.scene.camera:
            return True
        else:
            return False

    def invoke(self, context, event):
        if context.scene.camera:
            camera = context.scene.camera

            # Camera Object Settings
            self.camera = camera

            # Target
            self.target = Vector((0.0, 0.0, 0.0))
            self.target_width = 4

            cam_settings = {}
            cam_settings = set_cam_values(cam_settings, camera, self.target)

            # Camera Settings
            self.initial_cam_settings = cam_settings
            self.ref_cam_settings = cam_settings.copy()

            # Camera lens settings
            self.current_camera_fov = camera.data.angle
            self.current_focal_length = camera.data.lens

            # Mouse
            self.mouse_initial_x = event.mouse_x

            # Initial Mouse Position
            self.distance = 0

            # check if alt is pressed
            self.ignore_input = False

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


    def modal(self, context, event):
        '''Calculate the FOV from the changed location to the target object '''

        camera = self.camera
        scene = context.scene


        # Cancel Operator
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            #reset camera position and fov. resetting the fov will also reset the focal length
            self.camera.location = self.initial_cam_settings['cam_location']
            self.camera.data.angle = self.initial_cam_settings['camera_fov']

            # Remove Viewport Text
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass
            return {'CANCELLED'}


        # Apply operator
        elif event.type == 'LEFTMOUSE':
            # Remove Viewport Text
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass
            return {'FINISHED'}


        elif event.alt:
            print('ALT PRESSED')

            # update reference camera settings to current camera settings
            self.ignore_input = True
            return {'RUNNING_MODAL'}

        # Ignore Mouse Movement. The Operator will behave as starting it newly
        elif event.type == 'LEFT_ALT' and event.value == 'RELEASE':
            # update reference camera settings to current camera settings
            self.ref_cam_settings = set_cam_values(self.ref_cam_settings, camera, self.target)

            # update ref mouse position to current
            self.mouse_initial_x = event.mouse_x

            #Alt is not pressed anymore after release
            self.ignore_input = False

            return {'RUNNING_MODAL'}



        elif event.type == 'MOUSEMOVE':
            self.ignore_input = False

            # Ignore if Alt is pressed
            if event.alt:
                self.ignore_input = True
                return {'RUNNING_MODAL'}

            # Mouse Sensitivity and Sensitivity Modifiers (Shift, Ctrl)
            factor = 0.05
            if event.ctrl == True:
                factor = 0.15
            elif event.shift == True:
                factor = 0.01

            # calculate mouse movement and offset camera
            delta = int(self.mouse_initial_x - event.mouse_x)

            # cam_offset = round((delta * factor), 4)
            cam_offset = delta * factor

            # vec aligned to local axis in Blender 2.8+
            vec = Vector((0.0, 0.0, cam_offset))
            vec_rot = vec @ self.ref_cam_settings['inverted_matrix']
            camera.location = self.ref_cam_settings['cam_location'] + vec_rot

            # get camera world position and target position
            cam_pos = self.camera.matrix_world.to_translation()

            cam_vector = Vector(cam_pos)
            target_pos = self.target
            distance = distance_vec(cam_vector, target_pos)
            self.distance = distance

            # Dolly Zoom computation
            field_of_view = 2 * math.atan(self.target_width / distance)

            # Set camera field of view and
            camera.data.angle = field_of_view
            self.current_camera_fov = field_of_view
            self.current_focal_length = camera.data.lens
        return {'RUNNING_MODAL'}

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
