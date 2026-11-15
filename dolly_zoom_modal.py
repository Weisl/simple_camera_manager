import math

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector


def calculate_target_width(distance, fov):
    """Return the half-width of the camera frustum at the given distance for the given horizontal FOV."""
    width = distance * math.tan(0.5 * fov)
    return width


def generate_target_location(camera, distance):
    """Return the world-space position directly in front of the camera at the given distance."""
    vec = Vector((0.0, 0.0, -distance))

    inv = camera.matrix_world.copy()
    inv.invert()
    vec_rot = vec @ inv

    target_location = camera.location.copy() + vec_rot

    return target_location


# Running Dolly Zoom operators. While one runs, the gizmos don't push their
# own undo steps: the operator's single undo step covers the whole session.
_running = set()


def is_running():
    return bool(_running)


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
    cam_dic['camera_focal_length'] = camera.data.lens

    # Intitial Distance
    target_location = generate_target_location(camera, distance)

    cam_dic['distance'] = distance
    cam_dic['target_location'] = target_location

    cam_dic['target_width'] = camera.data.dolly_zoom_target_scale
    cam_dic['forward'] = (camera.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()

    return cam_dic


def distance_vec(point1: Vector, point2: Vector):
    """Calculates distance between two points."""
    return (point2 - point1).length


def frame_corners_at_distance(camera, scene, distance):
    """Return the world-space corners of the camera's render frame on the
    plane `distance` in front of the camera.

    Uses the camera's current lens, sensor fit, shift and the scene's render
    aspect, so it matches the frame drawn in camera view. The corners go
    around the frame (top right, bottom right, bottom left, top left)."""
    matrix = camera.matrix_world.normalized()
    corners = []
    for corner in camera.data.view_frame(scene=scene):
        if camera.data.type == 'ORTHO' or abs(corner.z) < 1e-9:
            local = Vector((corner.x, corner.y, -distance))
        else:
            local = corner * (distance / -corner.z)
        corners.append(matrix @ local)
    return corners


# ---------------------------------------------------------------------------
# Viewport overlay
#
# Same look as the modal operators of Simple Collider (its
# collider_shapes/add_bounding_primitive.py draw_viewport_overlay()), so the
# add-ons read as one family: a dark backdrop with a green top edge and thin
# frame, rows of "label  (key)  value", the active row highlighted in green,
# and every row greyed out while Alt is held or the view is being navigated.
# Simple Collider exposes these colors as preferences; here they are fixed to
# its defaults.
# ---------------------------------------------------------------------------

_PERSPECTIVE_ONLY = "Perspective only"
_ORTHO_MESSAGE = "Focal Length and Field of View need a perspective camera"

_COLOR_DEFAULT = (0.910, 0.914, 0.933, 1.0)
_COLOR_TITLE = (0.133, 0.773, 0.369, 1.0)
_COLOR_HIGHLIGHT = (0.133, 0.773, 0.369, 1.0)
_COLOR_MUTED = (0.604, 0.616, 0.651, 0.7)
_COLOR_BACKDROP = (0.141, 0.149, 0.176, 0.85)
_COLOR_FRAME = (0.204, 0.212, 0.243, 1.0)
_COLOR_ACCENT = (0.133, 0.773, 0.369, 1.0)
_FONT_SIZE_PREF = 36  # Simple Collider's default "Font Size" preference


def _font_size(context):
    # system.ui_scale follows the monitor DPI, view.ui_scale is the user's
    # Resolution Scale; Blender's own UI scales with both.
    return int(_FONT_SIZE_PREF * context.preferences.system.ui_scale
               * context.preferences.view.ui_scale / 3.6)


def _draw_rect(left, right, top, bottom, color):
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {"pos": ((left, bottom), (right, bottom), (left, top), (right, top))},
                             indices=((0, 1, 2), (2, 1, 3)))
    gpu.state.blend_set('ALPHA')
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.blend_set('NONE')


def _draw_row(font_id, font_size, y, left, item, muted):
    if muted and item['type'] != 'title' or item.get('disabled'):
        label_color = _COLOR_MUTED
    elif item.get('highlight'):
        label_color = _COLOR_HIGHLIGHT
    elif item['type'] == 'title':
        label_color = _COLOR_TITLE
    else:
        label_color = _COLOR_DEFAULT

    blf.size(font_id, font_size)
    blf.color(font_id, *label_color)
    blf.position(font_id, left, y, 0)
    blf.draw(font_id, item['label'])

    if item.get('key'):
        # key hints are a secondary cue, dimmed so the label stays primary
        key_color = (*label_color[:3], label_color[3] * 0.5)
        blf.color(font_id, *key_color)
        blf.position(font_id, left + 220 / 20 * font_size, y, 0)
        blf.draw(font_id, item['key'])

    if item.get('value'):
        blf.color(font_id, *label_color)
        blf.position(font_id, left + 290 / 20 * font_size, y, 0)
        blf.draw(font_id, item['value'])


def draw_callback_px(self, _context):
    """Draw the dolly zoom overlay in the 3D Viewport."""
    context = bpy.context
    try:
        # The operator may have been freed without removing this handler
        # (e.g. the add-on was reloaded while the modal was running).
        self.as_pointer()
    except ReferenceError:
        return

    camera = self.camera
    cam = camera.data
    initial = self.initial_cam_settings

    # Rows are listed bottom to top.
    items = [
        {'label': "Target Gizmo", 'key': '(Drag)', 'type': 'default',
         'value': "Visible" if cam.show_dolly_gizmo else "Hidden"},
        {'label': "Target Plane", 'key': '(P)', 'type': 'default',
         'value': _TARGET_PLANE_DISPLAY_LABELS[self.target_plane_display]},
        {'label': "Start Framing", 'key': '(R)', 'type': 'default',
         'value': "On" if self.show_start_frame else "Off"},
    ]
    info_row_count = len(items)

    items += [
        {'label': "Target Width", 'key': '(W)', 'type': 'modal', 'highlight': self.mode == 'WIDTH',
         'value': "{:.3f}".format(cam.dolly_zoom_target_scale)},
        {'label': "Target Distance", 'key': '(D)', 'type': 'modal', 'highlight': self.mode == 'DISTANCE',
         'value': "{:.3f}".format(cam.dolly_zoom_target_distance)},
        {'label': "Field of View", 'key': '(V)', 'type': 'modal', 'highlight': self.mode == 'FOV',
         'value': "{:.1f}°  ({:.1f}°)".format(math.degrees(cam.angle), math.degrees(initial['camera_fov']))},
        {'label': "Focal Length", 'key': '(F)', 'type': 'modal', 'highlight': self.mode == 'FOCAL',
         'value': "{:.1f} mm  ({:.1f} mm)".format(cam.lens, initial['camera_focal_length'])},
    ]
    if cam.type == 'ORTHO':
        # F and V do nothing on an orthographic camera; say so instead of
        # leaving the keys looking broken.
        for item in items[-2:]:
            item.update(disabled=True, value=_PERSPECTIVE_ONLY)

    items.append({'label': "Dolly Zoom", 'type': 'title'})
    title_row = len(items)

    if self.navigation:
        items.append({'label': "VIEWPORT NAVIGATION", 'type': 'title', 'highlight': True})
    elif self.ignore_input:
        items.append({'label': "IGNORE INPUT (ALT)", 'type': 'title', 'highlight': True})
    elif self.mode is None:
        items.append({'label': "PRESS F, V, D OR W TO ADJUST", 'type': 'title'})

    font_id = 0
    font_size = _font_size(context)
    row_height = font_size * 1.5
    row_padding = font_size * 0.5
    center = context.area.width / 2
    text_left = center - 190 / 20 * font_size

    box_left = center - 240 / 20 * font_size
    box_right = center + 260 / 20 * font_size
    box_top = font_size * len(items) * 1.75 + row_padding * 2
    box_bottom = 10

    _draw_rect(box_left, box_right, box_top, box_bottom, _COLOR_BACKDROP)
    accent_px = 3
    _draw_rect(box_left, box_right, box_top, box_top - accent_px, _COLOR_ACCENT)
    _draw_rect(box_left, box_right, box_bottom + 1, box_bottom, _COLOR_FRAME)
    _draw_rect(box_left, box_left + 1, box_top - accent_px, box_bottom, _COLOR_FRAME)
    _draw_rect(box_right - 1, box_right, box_top - accent_px, box_bottom, _COLOR_FRAME)

    def draw_rule(row):
        y = row_padding + (row + 0.5) * row_height
        _draw_rect(box_left, box_right, y + 0.5, y - 0.5, _COLOR_FRAME)

    draw_rule(title_row - 1)
    draw_rule(info_row_count)

    muted = self.ignore_input or self.navigation
    for i, item in enumerate(items):
        _draw_row(font_id, font_size, row_padding + (i + 1) * row_height, text_left, item, muted)


# ---------------------------------------------------------------------------
# 3D guides
#
# Drawn in the scene (POST_VIEW), so they line up in camera view and in any
# other 3D view:
# - the framing the camera had when the operator started, as a dashed frame,
#   so changing the width or field of view can be compared against it;
# - the target plane at the target distance, depth tested against the
#   scene, so where it cuts through objects shows where the target is. P
#   cycles how it is shown: a translucent plane with the cut line, only the
#   cut line, or nothing.
# ---------------------------------------------------------------------------

# How the target plane is shown, in the order P cycles through them.
_TARGET_PLANE_DISPLAYS = ('PLANE', 'LINE', 'OFF')
_TARGET_PLANE_DISPLAY_LABELS = {'PLANE': "Plane", 'LINE': "Cut Line", 'OFF': "Off"}

# The guide settings last chosen, so the next run starts with them (for the
# rest of the Blender session).
_guide_settings = {'target_plane_display': 'PLANE', 'show_start_frame': True}

# Half the depth range, as a fraction of the target distance, counted as "on
# the plane" when drawing the cut line.
_CUT_LINE_BAND = 0.004

_COLOR_START_FRAME = (1.0, 1.0, 1.0, 0.75)
_COLOR_TARGET_PLANE = (_COLOR_ACCENT[0], _COLOR_ACCENT[1], _COLOR_ACCENT[2], 0.12)
# Stronger while the plane itself is being moved or resized.
_COLOR_TARGET_PLANE_ACTIVE = (_COLOR_ACCENT[0], _COLOR_ACCENT[1], _COLOR_ACCENT[2], 0.22)
_START_FRAME_DASHES = 32  # dashes along the longer side of the frame
_START_FRAME_LINE_WIDTH = 1.5


def dashed_loop_segments(corners, dashes_on_longest_edge=_START_FRAME_DASHES):
    """Return line segment end points for a dashed closed loop through `corners`.

    The dash length is the same on every edge, taken from the longest one."""
    edges = [(corners[i], corners[(i + 1) % len(corners)]) for i in range(len(corners))]
    longest = max((b - a).length for a, b in edges)
    if longest <= 0.0:
        return []
    dash = longest / (2 * dashes_on_longest_edge)
    points = []
    for a, b in edges:
        length = (b - a).length
        if length <= 0.0:
            continue
        direction = (b - a) / length
        start = 0.0
        while start < length:
            end = min(start + dash, length)
            points.append(a + direction * start)
            points.append(a + direction * end)
            start += 2 * dash
    return points


def _draw_quad(corners, color):
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {"pos": corners}, indices=((0, 1, 2), (0, 2, 3)))
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_lines(points, color, width, region):
    shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": points})
    shader.bind()
    shader.uniform_float("viewportSize", (region.width, region.height))
    shader.uniform_float("lineWidth", width)
    shader.uniform_float("color", color)
    batch.draw(shader)


def cut_line_quads(corners, band, eye=None, view_direction=None):
    """Return the two quads _draw_cut_line() draws: `corners` moved `band`
    toward and away from the viewer.

    Both must cover exactly the same pixels, or the rim where only one of
    them is drawn shows up as a line too, so each corner moves along its own
    view ray: from `eye` in a perspective view, along `view_direction` in an
    orthographic one."""
    rays = [(c - eye).normalized() if eye is not None else view_direction for c in corners]
    return ([c - r * band for c, r in zip(corners, rays)],
            [c + r * band for c, r in zip(corners, rays)])


def _draw_cut_line(corners, distance, rv3d):
    """Mark the surfaces that lie on the target plane given by `corners`.

    Inverts the colors behind a copy of the plane just in front of it, then
    inverts them back behind a copy just past it. Both inversions cancel
    everywhere except on surfaces between the two copies, which leaves a line
    where the target plane cuts through the scene, without reading or writing
    the depth buffer. Expects the depth test to be on."""
    view = rv3d.view_matrix.inverted()
    if rv3d.is_perspective:
        quads = cut_line_quads(corners, distance * _CUT_LINE_BAND, eye=view.translation)
    else:
        direction = (view.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
        quads = cut_line_quads(corners, distance * _CUT_LINE_BAND, view_direction=direction)
    gpu.state.blend_set('INVERT')
    for quad in quads:
        _draw_quad(quad, (1.0, 1.0, 1.0, 1.0))
    gpu.state.blend_set('ALPHA')


def draw_callback_view(self, _context):
    """Draw the start framing and the target plane in the 3D Viewport."""
    context = bpy.context
    try:
        self.as_pointer()
    except ReferenceError:
        return

    camera = self.camera
    try:
        camera.name
    except ReferenceError:
        return

    # The plane is see-through: it must not hide what is drawn after it
    # (e.g. the target gizmo, which sits on the same plane).
    depth_mask = gpu.state.depth_mask_get()
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_mask_set(False)

    if self.target_plane_display != 'OFF':
        distance = camera.data.dolly_zoom_target_distance
        corners = frame_corners_at_distance(camera, context.scene, distance)
        gpu.state.depth_test_set('LESS_EQUAL')
        _draw_cut_line(corners, distance, context.region_data)
        if self.target_plane_display == 'PLANE':
            color = _COLOR_TARGET_PLANE_ACTIVE if self.mode in {'DISTANCE', 'WIDTH'} else _COLOR_TARGET_PLANE
            _draw_quad(corners, color)
        gpu.state.depth_test_set('NONE')

    if self.show_start_frame and self.start_frame_corners:
        points = dashed_loop_segments(self.start_frame_corners)
        if points:
            _draw_lines(points, _COLOR_START_FRAME, _START_FRAME_LINE_WIDTH, context.region)

    gpu.state.depth_mask_set(depth_mask)
    gpu.state.blend_set('NONE')


_NAVIGATION_EVENTS = {
    'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADPAN', 'TRACKPADZOOM',
    'NDOF_MOTION', 'NDOF_BUTTON_FIT',
}

_MODE_KEYS = {'F': 'FOCAL', 'V': 'FOV', 'D': 'DISTANCE', 'W': 'WIDTH'}

# Keys that change how the 3D guides are shown.
_GUIDE_KEYS = {'P', 'R'}

# Modes that change the lens and move the camera to keep the target's size.
_DOLLY_MODES = {'FOCAL', 'FOV'}

_MIN_FOV = math.radians(1.0)
_MAX_FOV = math.radians(170.0)
_MIN_LENS = 1.0

_HEADER_TEXT = ("Dolly Zoom: F Focal Length, V Field of View, D Target Distance, W Target Width, "
                "drag the gizmo to move the target, P Target Plane Display, R Start Framing, "
                "Shift/Ctrl Slower/Faster, Alt Ignore Mouse, "
                "LMB/Enter Confirm, RMB/Esc Cancel")


class CAM_MANAGER_OT_dolly_zoom(bpy.types.Operator):
    """Modal operator that keeps the subject size constant in the frame while changing focal length.

    Nothing changes until a value is activated with its key (F, V, D or W),
    the same way Simple Collider's modal operators work. Changing the focal
    length (F) or field of view (V) moves the camera along its view axis so
    the target keeps its size in the frame. While no value is
    active, mouse movement passes through to the viewport, so the dolly zoom
    target gizmo can be hovered and dragged.

    Two guides are drawn in the scene while it runs: the starting framing as
    a dashed frame (R toggles it) and a see-through plane at the target
    distance that shows where the target cuts through objects (P cycles
    Plane, Cut Line and Off)."""

    bl_idname = "cam_manager.modal_camera_dolly_zoom"
    bl_label = "Dolly Zoom"
    bl_description = "Change focal length while keeping the target at the same size in the camera view"
    bl_options = {'REGISTER', 'UNDO'}

    @staticmethod
    def _redraw(context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    def _update_width(self):
        """Target width changed: keep the camera where it is and set the
        field of view so the target frame fills the same part of the view."""
        cam = self.camera.data
        distance = max(cam.dolly_zoom_target_distance, 0.01)
        cam.angle = min(max(2 * math.atan(cam.dolly_zoom_target_scale / distance), _MIN_FOV), _MAX_FOV)

    def _dolly_to_angle(self, angle):
        """Set the field of view and move the camera along its view axis so
        the target keeps its size in the frame (the dolly zoom effect)."""
        ref = self.ref_cam_settings
        cam = self.camera.data
        angle = min(max(angle, _MIN_FOV), _MAX_FOV)
        distance = ref['target_width'] / math.tan(angle / 2)
        self.camera.location = ref['cam_location'] - ref['forward'] * (distance - ref['distance'])
        cam.angle = angle
        cam.dolly_zoom_target_distance = distance

    def _capture_reference(self, event):
        """Start the next drag from the camera's current state and the current mouse position.

        Called whenever the active value, a modifier key or Alt changes, and
        so also picks up any change made by dragging the gizmo in between."""
        cam = self.camera.data
        if self.mode in _DOLLY_MODES:
            # The dolly keeps the frame at the target distance constant, so
            # take its width from the current lens (the gizmo may have moved
            # the target since the last time).
            cam.dolly_zoom_target_scale = calculate_target_width(cam.dolly_zoom_target_distance, cam.angle)
        self.ref_cam_settings = set_cam_values(self.ref_cam_settings, self.camera, cam.dolly_zoom_target_distance)
        self.mouse_initial_x = event.mouse_x

    def _set_mode(self, mode, event, context):
        if mode in _DOLLY_MODES and self.camera.data.type == 'ORTHO':
            # An orthographic camera has no focal length or field of view.
            self.report({'WARNING'}, _ORTHO_MESSAGE)
            return
        self.mode = None if self.mode == mode else mode
        self._capture_reference(event)
        # A key press alone doesn't repaint the viewport, so the highlight
        # wouldn't update until the next mouse move without this.
        self._redraw(context)

    def _cycle_guide(self, key, context):
        """P cycles the target plane display, R shows or hides the start framing."""
        if key == 'P':
            index = _TARGET_PLANE_DISPLAYS.index(self.target_plane_display)
            self.target_plane_display = _TARGET_PLANE_DISPLAYS[(index + 1) % len(_TARGET_PLANE_DISPLAYS)]
        elif key == 'R':
            self.show_start_frame = not self.show_start_frame
        _guide_settings['target_plane_display'] = self.target_plane_display
        _guide_settings['show_start_frame'] = self.show_start_frame
        self._redraw(context)

    def _finish(self, context):
        _running.discard(id(self))
        self.camera.data.show_dolly_gizmo = self.initial_gizmo_state
        context.area.header_text_set(None)
        for attr in ('_handle', '_handle_view'):
            handle = getattr(self, attr, None)
            if handle is not None:
                try:
                    bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
                except ValueError:
                    pass
                setattr(self, attr, None)
        self._redraw(context)

    def _init_state(self, camera, event):
        """Record the starting camera state. Nothing is changed until a value
        is activated with F, V, D or W."""
        self.camera = camera
        cam = camera.data

        self.initial_gizmo_state = cam.show_dolly_gizmo
        self.initial_target_scale = cam.dolly_zoom_target_scale
        self.initial_lens = cam.lens
        # The roll gizmo can be used while the operator runs.
        self.initial_rotation = camera.rotation_euler.copy()
        cam.show_dolly_gizmo = True
        _running.add(id(self))

        self.mode = None
        self.ignore_input = False
        self.navigation = False
        self.mouse_initial_x = event.mouse_x

        self.target_plane_display = _guide_settings['target_plane_display']
        self.show_start_frame = _guide_settings['show_start_frame']
        # Fixed in the world: the frame the camera saw when the operator
        # started, on the target plane of that moment.
        self.start_frame_corners = frame_corners_at_distance(camera, bpy.context.scene,
                                                             cam.dolly_zoom_target_distance)

        cam.dolly_zoom_target_scale = calculate_target_width(cam.dolly_zoom_target_distance, cam.angle)

        self.initial_cam_settings = set_cam_values({}, camera, cam.dolly_zoom_target_distance)
        self.ref_cam_settings = self.initial_cam_settings.copy()

    @classmethod
    def poll(cls, context):
        return context.scene.camera is not None

    def invoke(self, context, event):
        camera = context.scene.camera
        if camera is None:
            self.report({'WARNING'}, "No scene camera assigned")
            return {'CANCELLED'}
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Dolly Zoom needs to be started from a 3D Viewport")
            return {'CANCELLED'}

        # The gizmos only show for the active camera object.
        bpy.ops.object.select_all(action='DESELECT')
        camera.select_set(True)
        context.view_layer.objects.active = camera

        self._init_state(camera, event)

        self._handle_view = bpy.types.SpaceView3D.draw_handler_add(draw_callback_view, (self, context), 'WINDOW',
                                                                   'POST_VIEW')
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (self, context), 'WINDOW',
                                                              'POST_PIXEL')
        context.area.header_text_set(_HEADER_TEXT)
        context.window_manager.modal_handler_add(self)
        self._redraw(context)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """Calculate the FOV from the changed location to the target object """
        from .camera_gizmos import any_interactive_gizmo_highlighted

        camera = self.camera

        # Dragging a gizmo clears the header text when it ends.
        context.area.header_text_set(_HEADER_TEXT)

        # Viewport navigation: let it through and stop the active value, like
        # Simple Collider, so navigating doesn't fight with an active drag.
        if event.type in _NAVIGATION_EVENTS:
            self.mode = None
            self.navigation = True
            self._redraw(context)
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE' and self.navigation:
            self.navigation = False
            self._redraw(context)

        # Cancel
        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            init = self.initial_cam_settings
            camera.location = init['cam_location']
            camera.rotation_euler = self.initial_rotation
            camera.data.lens = self.initial_lens
            camera.data.dolly_zoom_target_distance = init['distance']
            camera.data.dolly_zoom_target_scale = self.initial_target_scale
            self._finish(context)
            return {'CANCELLED'}

        # Confirm, unless the click is meant for a gizmo under the mouse.
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self.mode is None and any_interactive_gizmo_highlighted():
                return {'PASS_THROUGH'}
            self._finish(context)
            return {'FINISHED'}

        if event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            self._finish(context)
            return {'FINISHED'}

        # Hold Alt to move the mouse without changing anything.
        if event.alt:
            if not self.ignore_input:
                self.ignore_input = True
                self._redraw(context)
            return {'RUNNING_MODAL'}

        if event.type == 'LEFT_ALT' and event.value == 'RELEASE':
            self.ignore_input = False
            self._capture_reference(event)
            self._redraw(context)
            return {'RUNNING_MODAL'}

        # Changing the sensitivity restarts the drag from here to avoid a jump.
        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT', 'LEFT_CTRL', 'RIGHT_CTRL'} \
                and event.value in {'PRESS', 'RELEASE'}:
            self._capture_reference(event)
            return {'RUNNING_MODAL'}

        if event.type in _MODE_KEYS and event.value == 'RELEASE':
            self._set_mode(_MODE_KEYS[event.type], event, context)
            return {'RUNNING_MODAL'}

        if event.type in _GUIDE_KEYS and event.value == 'RELEASE':
            self._cycle_guide(event.type, context)
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            self.ignore_input = False
            if self.mode is None:
                # Let the viewport see the mouse so gizmos highlight on hover.
                return {'PASS_THROUGH'}

            # Dragging to the right increases the active value.
            drag = event.mouse_x - self.mouse_initial_x
            ref = self.ref_cam_settings

            def step(normal, fine, coarse):
                return coarse if event.ctrl else fine if event.shift else normal

            if self.mode == 'FOCAL':
                camera.data.lens = max(ref['camera_focal_length'] + drag * step(0.1, 0.01, 0.5), _MIN_LENS)
                self._dolly_to_angle(camera.data.angle)

            elif self.mode == 'FOV':
                self._dolly_to_angle(ref['camera_fov'] + math.radians(drag * step(0.1, 0.01, 0.5)))

            elif self.mode == 'WIDTH':
                camera.data.dolly_zoom_target_scale = abs(ref['target_width'] + drag * step(0.005, 0.001, 0.015))
                self._update_width()

            elif self.mode == 'DISTANCE':
                distance = abs(ref['distance'] + drag * step(0.05, 0.005, 0.15))
                camera.data.dolly_zoom_target_distance = distance
                camera.data.dolly_zoom_target_scale = calculate_target_width(distance, camera.data.angle)

            self._redraw(context)
            return {'RUNNING_MODAL'}

        # Block other hotkeys (G, R, S, ...) while the operator runs.
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
        if hasattr(cls, 'bl_rna'):
            unregister_class(cls)
