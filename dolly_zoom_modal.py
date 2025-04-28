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


class CAM_MANAGER_OT_multi_camera_rendering(bpy.types.Operator):
    """Render all selected cameras"""
    bl_idname = "cam_manager.multi_camera_rendering"
    bl_label = "Render All Selected Cameras"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _cameras = []
    _current_index = 0
    _original_camera = None
    _rendering = False

    def render_complete_handler(self, scene, dummy):
        self._rendering = False
        print(f"Completed rendering camera: {self._cameras[self._current_index].name}")
        self._current_index += 1
        if self._current_index < len(self._cameras):
            self.start_next_render()
        else:
            self.cancel(bpy.context)

    def start_next_render(self):
        if self._current_index < len(self._cameras):
            camera = self._cameras[self._current_index]
            print(f"Rendering camera: {camera.name}")
            bpy.ops.cam_manager.change_scene_camera(camera_name=camera.name)
            self.register_handlers()

            # Use EXEC_DEFAULT to avoid opening the render window
            bpy.ops.render.render('EXEC_DEFAULT', write_still=True)
            self._rendering = True

    def register_handlers(self):
        if self.render_complete_handler not in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.append(self.render_complete_handler)

    def unregister_handlers(self):
        if self.render_complete_handler in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self.render_complete_handler)

    def modal(self, context, event):
        if event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if not self._rendering and self._current_index < len(self._cameras):
                self.start_next_render()

        return {'PASS_THROUGH'}

    def execute(self, context):
        scene = context.scene
        self._original_camera = scene.camera
        self._cameras = [obj for obj in bpy.data.objects if
                         obj.type == 'CAMERA' and getattr(obj.data, "render_selected", False)]

        if not self._cameras:
            self.report({'ERROR'}, "No cameras selected for rendering")
            return {'CANCELLED'}

        print(f"Cameras to render: {[cam.name for cam in self._cameras]}")

        self._current_index = 0
        self._rendering = False
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        # Open the render view
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    for space in area.spaces:
                        if space.type == 'IMAGE_EDITOR':
                            space.image = bpy.data.images.get("Render Result")
                            break
                    break

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        if self._original_camera:
            bpy.ops.cam_manager.change_scene_camera(camera_name=self._original_camera.name)
        self.unregister_handlers()
        self.report({'INFO'}, "Rendering completed or aborted")


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
