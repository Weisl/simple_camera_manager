import math

import blf
from mathutils import Vector


def calculate_target_width(distance, fov):
    width = distance * math.tan(0.5 * fov)
    return width


def generate_target_location(camera, distance):
    # Create the transformation matrix to move 1 unit along x
    vec = Vector((0.0, 0.0, -distance))

    inv = camera.matrix_world.copy()
    inv.invert()
    vec_rot = vec @ inv

    target_location = camera.location.copy() + vec_rot

    return target_location


def set_cam_values(cam_dic, camera, distance):
    """Store current camera settings in a dictionary """
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
    target_location = generate_target_location(camera, distance)

    cam_dic['distance'] = distance
    cam_dic['target_location'] = target_location

    cam_dic['target_width'] = camera.data.dolly_zoom_target_scale

    return cam_dic


def distance_vec(point1: Vector, point2: Vector):
    """Calculates distance between two points."""
    return (point2 - point1).length


def draw_title_text(self, font_id, i, vertical_px_offset, left_margin, name, color):
    """Draw UI title text in the 3D Viewport """
    blf.size(font_id, 20)

    blf.color(font_id, color[0], color[1], color[2], color[3])
    blf.position(font_id, left_margin, i * vertical_px_offset, 0)
    blf.draw(font_id, name)


def draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, name, value, initial_value=None,
                       highlighting=False):
    """Draw UI operator parameters as text in the 3D Viewport """
    text = '{name:}:'.format(name=name)
    text2 = '{value:.2f}'.format(value=value)

    font_size = 20

    if bpy.app.version < (4, 00):
        # legacy support
        blf.size(font_id, 75, font_size)
    else:
        blf.size(font_id, font_size)

    # define color for input ignore
    if self.ignore_input:
        c1 = c2 = [0.5, 0.5, 0.5, 0.5]

    # define color for highlited value
    elif highlighting:
        c1 = c2 = [0.0, 1.0, 1.0, 1.0]

    # define default values
    else:
        c1 = [1.0, 1.0, 1.0, 1.0]
        c2 = [1.0, 1.0, 0.5, 1.0]

    blf.color(font_id, c1[0], c1[1], c1[2], c1[3])
    blf.position(font_id, left_margin, i * vertical_px_offset, 0)
    blf.draw(font_id, text)

    blf.color(font_id, c2[0], c2[1], c2[2], c2[3])
    blf.position(font_id, left_margin + 190, i * vertical_px_offset, 0)
    blf.draw(font_id, text2)

    # optional original value
    if initial_value:
        text3 = '{initial_value:.2f}'.format(initial_value=initial_value)
        blf.color(font_id, c1[0], c1[1], c1[2], c1[3])
        blf.position(font_id, left_margin + 350, i * vertical_px_offset, 0)
        blf.draw(font_id, text3)

    i += 1

    return i


def draw_callback_px(self, context):
    """Draw 3d viewport text for the dolly zoom modal operator"""
    scene = context.scene

    font_id = 0  # XXX, need to find out how best to get this.
    vertical_px_offset = 30
    left_margin = bpy.context.area.width / 2 - 200
    i = 1

    x = math.degrees(self.current_camera_fov)
    y = math.degrees(self.initial_cam_settings['camera_fov'])
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, 'FOV', x, initial_value=y)

    x = self.current_focal_length
    y = self.initial_cam_settings['camera_focal_length']
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, 'Focal Length', x, initial_value=y)

    x = self.camera.data.dolly_zoom_target_distance
    y = self.initial_cam_settings['distance']
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, 'Distance (D)', x, initial_value=y,
                           highlighting=self.set_distance)

    x = self.camera.data.dolly_zoom_target_scale
    y = self.initial_cam_settings['target_width']
    i = draw_vierport_text(self, font_id, i, vertical_px_offset, left_margin, 'Width (F)', x, initial_value=y,
                           highlighting=self.set_width)

    if self.ignore_input:
        color = (0.0, 1.0, 1.0, 1.0)
    else:
        color = (1.0, 1.0, 1.0, 1.0)

    draw_title_text(self, font_id, i, vertical_px_offset, left_margin, 'IGNORE INPUT (ALT)', color)


import bpy
import os


class CAM_MANAGER_OT_multi_camera_rendering(bpy.types.Operator):
    """Render all selected cameras"""
    bl_idname = "cam_manager.multi_camera_rendering"
    bl_label = "Render All Selected Cameras"
    bl_options = {'REGISTER', 'UNDO'}

    _cameras = []
    _original_camera = None
    _original_output_path = None
    _current_frame = 1

    def frame_change_pre_handler(self, scene, depsgraph):
        print(f"frame_change_pre_handler called for frame: {scene.frame_current}")
        if self._current_frame <= len(self._cameras):
            camera = self._cameras[self._current_frame - 1]
            print(f"Setting camera: {camera.name}")
            self.report({'INFO'}, f"Setting camera: {camera.name}")
            self.set_camera_settings(camera)

    def render_complete_handler(self, scene, depsgraph):
        print(f"render_complete_handler called for frame: {scene.frame_current}")
        self._current_frame += 1
        if self._current_frame <= len(self._cameras):
            # Trigger the next frame change
            print(f"Setting frame to: {self._current_frame}")
            scene.frame_set(self._current_frame)
            # Start the next render
            print(f"Starting render for frame: {self._current_frame}")
            bpy.ops.render.render('EXEC_DEFAULT', write_still=True, use_viewport=False)
        else:
            self.cleanup(bpy.context)

    def execute(self, context):
        scene = context.scene
        self._original_camera = scene.camera
        self._original_output_path = scene.render.filepath
        self._cameras = [obj for obj in bpy.data.objects if
                         obj.type == 'CAMERA' and getattr(obj.data, "render_selected", False)]

        if not self._cameras:
            self.report({'ERROR'}, "No cameras selected for rendering")
            return {'CANCELLED'}

        print(f"Cameras to render: {[cam.name for cam in self._cameras]}")
        self.report({'INFO'}, f"Cameras to render: {[cam.name for cam in self._cameras]}")

        # Set up the frame range to match the number of cameras
        scene.frame_start = 1
        scene.frame_end = len(self._cameras)
        scene.frame_current = 1

        # Register the frame change and render complete handlers
        bpy.app.handlers.frame_change_pre.append(self.frame_change_pre_handler)
        bpy.app.handlers.render_complete.append(self.render_complete_handler)

        try:
            # Start the first render
            print(f"Starting first render for frame: {self._current_frame}")
            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True, use_viewport=False)
        except Exception as e:
            self.report({'ERROR'}, f"Rendering failed: {e}")
            self.cleanup(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def cleanup(self, context):
        scene = context.scene
        print("Cleanup called")
        # Restore the original camera and output path
        if self._original_camera:
            scene.camera = self._original_camera
        if self._original_output_path:
            scene.render.filepath = self._original_output_path

        # Remove the handlers
        if self.frame_change_pre_handler in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.remove(self.frame_change_pre_handler)
        if self.render_complete_handler in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self.render_complete_handler)

        self.report({'INFO'}, "Rendering completed or aborted")

    def set_camera_settings(self, camera):
        scene = bpy.context.scene
        print(f"Setting camera settings for: {camera.name}")

        # Set the active camera
        scene.camera = camera

        # Update resolution
        if hasattr(camera.data, 'resolution') and camera.data.resolution:
            scene.render.resolution_x = camera.data.resolution[0]
            scene.render.resolution_y = camera.data.resolution[1]
            print(f"Resolution set to: {camera.data.resolution}")

        # Update exposure
        scene.view_settings.exposure = getattr(camera.data, 'exposure', 0)
        print(f"Exposure set to: {scene.view_settings.exposure}")

        # Update world settings
        if hasattr(camera.data, 'world') and camera.data.world:
            try:
                scene.world = camera.data.world
                print(f"World set to: {camera.data.world.name}")
            except KeyError:
                self.report({'WARNING'}, 'World material could not be found')

        # Update render slot
        if hasattr(camera.data, 'slot') and camera.data.slot <= len(bpy.data.images['Render Result'].render_slots):
            bpy.data.images['Render Result'].render_slots.active_index = camera.data.slot - 1
            print(f"Render slot set to: {camera.data.slot}")

        # Update output path
        if scene.output_use_cam_name:
            old_path = bpy.context.scene.render.filepath
            path, basename = os.path.split(old_path)
            new_path = os.path.join(path, camera.name)
            bpy.context.scene.render.filepath = new_path
            print(f"Output path set to: {new_path}")

        # Ensure the render settings are updated
        bpy.context.view_layer.update()


class CAM_MANAGER_OT_dolly_zoom(bpy.types.Operator):
    """Modlar operator that keeps the object size in viewport when changing the focal lenght """

    bl_idname = "cam_manager.modal_camera_dolly_zoom"
    bl_label = "Dolly Zoom"
    bl_description = "Change focal lenght while keeping the target object at the same size in the camera view"
    bl_options = {'REGISTER', 'UNDO'}

    def force_redraw(self):
        bpy.context.object.data.show_limits = not self.show_limits
        bpy.context.object.data.show_limits = self.show_limits

    def update_camera(self, cam_offset=0, use_cam_offset=False):

        camera = self.camera

        if use_cam_offset:
            if cam_offset > -self.ref_cam_settings['distance']:
                cam_move = cam_offset
                distance = cam_move + self.ref_cam_settings['distance']

            else:  # Camera goes past the target
                cam_move = abs(cam_offset) - self.ref_cam_settings['distance'] - self.ref_cam_settings['distance']
                distance = cam_move + self.ref_cam_settings['distance']

            # move camera
            # vec aligned to local axis in Blender 2.8+
            vec = Vector((0.0, 0.0, cam_move))
            vec_rot = vec @ self.ref_cam_settings['inverted_matrix']
            camera.location = self.ref_cam_settings['cam_location'] + vec_rot

        else:
            # Calculate Distance from camera to target
            cam_vector = Vector(self.camera.matrix_world.to_translation())
            target_pos = Vector(self.ref_cam_settings['target_location'])
            distance = distance_vec(cam_vector, target_pos)

        camera.data.dolly_zoom_target_distance = distance

        # Dolly Zoom computation
        if distance != 0:
            field_of_view = 2 * math.atan(self.camera.data.dolly_zoom_target_scale / distance)
        else:
            field_of_view = 2 * math.atan(self.camera.data.dolly_zoom_target_scale / 0.01)

        # Set camera field of view and
        camera.data.angle = field_of_view
        self.current_camera_fov = field_of_view
        self.current_focal_length = camera.data.lens

    @classmethod
    def poll(cls, context):
        if context.scene.camera:
            return True
        else:
            return False

    def invoke(self, context, event):
        bpy.ops.object.select_all(action='DESELECT')

        if context.scene.camera:
            camera = context.scene.camera
            camera.select_set(True)
            context.view_layer.objects.active = camera

            # initial state Gizmo
            prefs = context.preferences.addons[__package__].preferences
            self.initial_gizmo_state = prefs.show_dolly_gizmo

            # Camera Object Settings
            self.camera = camera
            self.show_limits = bpy.context.object.data.show_limits

            # setting used when changing the distance with the modal operator
            self.tmp_distance = False

            # Camera lens settings
            self.current_camera_fov = camera.data.angle
            self.current_focal_length = camera.data.lens

            #####  UI  #######
            # Mouse
            self.mouse_initial_x = event.mouse_x

            # check if alt is pressed
            self.ignore_input = False

            # Operator modes
            self.set_width = False
            self.set_distance = False

            # Target
            width = calculate_target_width(camera.data.dolly_zoom_target_distance, camera.data.angle)
            camera.data.dolly_zoom_target_scale = width

            # Camera Reference Values
            cam_settings = {}
            cam_settings = set_cam_values(cam_settings, camera, self.camera.data.dolly_zoom_target_distance)

            # Camera Settings
            self.initial_cam_settings = cam_settings
            self.ref_cam_settings = cam_settings.copy()

            # update camera
            self.update_camera()

            # the arguments we pass to the callback

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
        """Calculate the FOV from the changed location to the target object """

        camera = self.camera
        scene = context.scene

        # Set Gizmo to be visibile during the modal operation. Dirty!
        prefs = context.preferences.addons[__package__].preferences
        prefs.show_dolly_gizmo = True

        # Cancel Operator
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            # reset camera position and fov. resetting the fov will also reset the focal length
            self.camera.location = self.initial_cam_settings['cam_location']
            self.camera.data.angle = self.initial_cam_settings['camera_fov']
            self.camera.data.dolly_zoom_target_distance = self.initial_cam_settings['distance']
            prefs.show_dolly_gizmo = self.initial_gizmo_state

            # Remove Viewport Text
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass
            return {'CANCELLED'}


        # Apply operator
        elif event.type == 'LEFTMOUSE':
            # Remove Viewport Text
            prefs.show_dolly_gizmo = self.initial_gizmo_state
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass
            return {'FINISHED'}


        elif event.alt:
            # update reference camera settings to current camera settings
            self.ignore_input = True
            self.force_redraw()

            return {'RUNNING_MODAL'}

        elif event.type == 'F' and event.value == 'RELEASE':
            self.set_width = not self.set_width
            self.set_distance = False

            self.ref_cam_settings = set_cam_values(self.ref_cam_settings, camera,
                                                   self.camera.data.dolly_zoom_target_distance)

        elif event.type == 'D' and event.value == 'RELEASE':
            self.set_distance = not self.set_distance
            self.set_width = False

            if self.set_distance:
                self.tmp_distance = self.ref_cam_settings['distance']
            else:
                self.tmp_distance = False

            self.ref_cam_settings = set_cam_values(self.ref_cam_settings, camera,
                                                   self.camera.data.dolly_zoom_target_distance)

        # Set ref values when switching mode to avoid jumping of field of view.
        elif event.type in ['LEFT_SHIFT', 'LEFT_CTRL'] and event.value in ['PRESS', 'RELEASE']:
            # update reference camera settings to current camera settings
            self.ref_cam_settings = set_cam_values(self.ref_cam_settings, camera,
                                                   self.camera.data.dolly_zoom_target_distance)
            self.tmp_distance = self.ref_cam_settings['distance']

            # update ref mouse position to current
            self.mouse_initial_x = event.mouse_x

            # Alt is not pressed anymore after release
            self.ignore_input = False

            return {'RUNNING_MODAL'}

        # Ignore Mouse Movement. The Operator will behave as starting it newly
        elif event.type == 'LEFT_ALT' and event.value == 'RELEASE':
            # update reference camera settings to current camera settings
            self.ref_cam_settings = set_cam_values(self.ref_cam_settings, camera,
                                                   self.camera.data.dolly_zoom_target_distance)
            self.tmp_distance = self.ref_cam_settings['distance']

            # update ref mouse position to current
            self.mouse_initial_x = event.mouse_x

            # Alt is not pressed anymore after release
            self.ignore_input = False
            return {'RUNNING_MODAL'}

        elif event.type == 'MOUSEMOVE':
            self.ignore_input = False

            # calculate mouse movement and offset camera
            delta = int(self.mouse_initial_x - event.mouse_x)

            # Ignore if Alt is pressed
            if event.alt:
                self.ignore_input = True
                return {'RUNNING_MODAL'}

            elif self.set_width:
                # Mouse Sensitivity and Sensitivity Modifiers (Shift, Ctrl)

                factor = 0.005
                if event.ctrl:
                    factor = 0.015
                elif event.shift:
                    factor = 0.001

                # calculate width offset
                offset = delta * factor
                width = abs(self.ref_cam_settings['target_width'] + offset)

                # set operator variables and camera property
                self.camera.data.dolly_zoom_target_scale = width

                # update camera
                self.update_camera()

            elif self.set_distance:

                factor = 0.05
                if event.ctrl:
                    factor = 0.15
                elif event.shift:
                    factor = 0.005

                # calculate width offset
                offset = delta * factor
                distance = abs(self.tmp_distance + offset)

                self.camera.data.dolly_zoom_target_distance = distance
                self.ref_cam_settings['distance'] = distance

                # Target
                width = calculate_target_width(camera.data.dolly_zoom_target_distance, camera.data.angle)
                camera.data.dolly_zoom_target_scale = width

                # update camera
                # self.update_camera()

            else:
                # Mouse Sensitivity and Sensitivity Modifiers (Shift, Ctrl)
                factor = 0.05
                if event.ctrl:
                    factor = 0.15
                elif event.shift:
                    factor = 0.005

                cam_offset = delta * factor

                self.update_camera(cam_offset=cam_offset, use_cam_offset=True)

        return {'RUNNING_MODAL'}


classes = (
    CAM_MANAGER_OT_dolly_zoom,
    CAM_MANAGER_OT_multi_camera_rendering,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
