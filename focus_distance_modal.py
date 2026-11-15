"""Focus Distance modal operator.

Works like Dolly Zoom (dolly_zoom_modal.py) and Simple Collider's modal
tools: nothing changes until a value is activated with its key, dragging the
mouse then changes it. While it runs, the focus plane is drawn in the scene
with a cut line where it meets the surfaces that are in focus, plus dashed
frames at the near and far limits of the sharp range.

The drawing helpers and the overlay look are shared with Dolly Zoom.
"""
import math

import bpy
import gpu
from bpy_extras import view3d_utils
from mathutils import Vector

from .dolly_zoom_modal import (
    _COLOR_ACCENT,
    _COLOR_BACKDROP,
    _COLOR_FRAME,
    _NAVIGATION_EVENTS,
    _draw_cut_line,
    _draw_lines,
    _draw_quad,
    _draw_rect,
    _draw_row,
    _font_size,
    dashed_loop_segments,
    frame_corners_at_distance,
)

_MODE_KEYS = {'D': 'DISTANCE', 'A': 'FSTOP'}

# How the focus plane is shown, in the order P cycles through them.
_PLANE_DISPLAYS = ('PLANE', 'LINE', 'OFF')
_PLANE_DISPLAY_LABELS = {'PLANE': "Plane", 'LINE': "Cut Line", 'OFF': "Off"}

# The guide settings last chosen, so the next run starts with them (for the
# rest of the Blender session).
_guide_settings = {'plane_display': 'PLANE', 'show_sharp_range': True}

_COLOR_FOCUS_PLANE = (_COLOR_ACCENT[0], _COLOR_ACCENT[1], _COLOR_ACCENT[2], 0.12)
_COLOR_FOCUS_PLANE_ACTIVE = (_COLOR_ACCENT[0], _COLOR_ACCENT[1], _COLOR_ACCENT[2], 0.22)
_COLOR_SHARP_RANGE = (1.0, 1.0, 1.0, 0.6)
_SHARP_RANGE_LINE_WIDTH = 1.5

_MIN_DISTANCE = 0.001
_MIN_FSTOP = 0.1
_MAX_FSTOP = 128.0

# Circle of confusion for "acceptably sharp", as a fraction of the sensor
# diagonal. 1/1500 is the usual photography convention (0.029 mm on a full
# frame sensor); the sharp range is an estimate, not a render result.
_COC_FRACTION_OF_DIAGONAL = 1.0 / 1500.0

_HEADER_TEXT = ("Focus Distance: D Focus Distance, A F-Stop, E Focus on Surface under Mouse, "
                "P Focus Plane Display, R Sharp Range, Shift/Ctrl Slower/Faster, Alt Ignore Mouse, "
                "LMB/Enter Confirm, RMB/Esc Cancel")


def sharp_range(focus_distance, lens_mm, fstop, coc_mm, unit_scale=1.0):
    """Near and far limit of acceptable sharpness around `focus_distance`.

    Distances are in scene units, `unit_scale` is the length of one scene
    unit in meters (scene.unit_settings.scale_length). The far limit is
    math.inf at or beyond the hyperfocal distance."""
    to_scene = 1.0 / (1000.0 * unit_scale)  # millimeters to scene units
    f = lens_mm * to_scene
    c = coc_mm * to_scene
    s = focus_distance
    hyperfocal = f * f / (fstop * c) + f
    near = s * (hyperfocal - f) / (hyperfocal + s - 2 * f)
    far = math.inf if s >= hyperfocal else s * (hyperfocal - f) / (hyperfocal - s)
    return near, far


def circle_of_confusion_mm(cam, scene):
    """Acceptable circle of confusion for the camera's sensor, in millimeters."""
    render = scene.render
    aspect = (render.resolution_y * render.pixel_aspect_y) / max(render.resolution_x * render.pixel_aspect_x, 1e-9)
    if cam.sensor_fit == 'VERTICAL':
        height = cam.sensor_height
        width = height / max(aspect, 1e-9)
    elif cam.sensor_fit == 'HORIZONTAL' or aspect <= 1.0:
        width = cam.sensor_width
        height = width * aspect
    else:  # AUTO on a portrait frame: the sensor size applies to the long side
        height = cam.sensor_width
        width = height / aspect
    return math.hypot(width, height) * _COC_FRACTION_OF_DIAGONAL


def camera_sharp_range(camera, scene):
    """Sharp range of the camera at its current focus distance and f-stop,
    or None for an orthographic camera."""
    cam = camera.data
    if cam.type == 'ORTHO':
        return None
    return sharp_range(cam.dof.focus_distance, cam.lens, cam.dof.aperture_fstop,
                       circle_of_confusion_mm(cam, scene), scene.unit_settings.scale_length or 1.0)


def distance_along_view(camera, point):
    """Distance of `point` in front of the camera, measured along its view axis
    (the distance Blender's focus distance uses)."""
    matrix = camera.matrix_world.normalized()
    forward = (matrix.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
    return (point - matrix.translation).dot(forward)


def format_length(scene, value):
    if value == math.inf:
        return "∞"
    units = scene.unit_settings
    try:
        return bpy.utils.units.to_string(units.system, 'LENGTH', value * (units.scale_length or 1.0), precision=3)
    except (ValueError, TypeError):
        return f"{value:.3f}"


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw_callback_view(self, _context):
    """Draw the focus plane and the sharp range in the 3D Viewport."""
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

    depth_mask = gpu.state.depth_mask_get()
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_mask_set(False)

    distance = camera.data.dof.focus_distance
    if self.plane_display != 'OFF':
        corners = frame_corners_at_distance(camera, context.scene, distance)
        gpu.state.depth_test_set('LESS_EQUAL')
        _draw_cut_line(corners, distance, context.region_data)
        if self.plane_display == 'PLANE':
            _draw_quad(corners, _COLOR_FOCUS_PLANE_ACTIVE if self.mode == 'DISTANCE' else _COLOR_FOCUS_PLANE)
        gpu.state.depth_test_set('NONE')

    if self.show_sharp_range:
        limits = camera_sharp_range(camera, context.scene)
        if limits is not None:
            points = []
            for limit in limits:
                if 0.0 < limit < math.inf:
                    points += dashed_loop_segments(frame_corners_at_distance(camera, context.scene, limit))
            if points:
                _draw_lines(points, _COLOR_SHARP_RANGE, _SHARP_RANGE_LINE_WIDTH, context.region)

    gpu.state.depth_mask_set(depth_mask)
    gpu.state.blend_set('NONE')


def draw_callback_px(self, _context):
    """Draw the Focus Distance overlay, in the same style as Dolly Zoom's."""
    context = bpy.context
    try:
        self.as_pointer()
    except ReferenceError:
        return

    camera = self.camera
    cam = camera.data
    scene = context.scene
    initial = self.initial

    limits = camera_sharp_range(camera, scene)
    if limits is None:
        range_value = "Orthographic"
    elif self.show_sharp_range:
        range_value = f"{format_length(scene, limits[0])} – {format_length(scene, limits[1])}"
    else:
        range_value = "Off"

    # Rows are listed bottom to top.
    items = [
        {'label': "Focus on Surface", 'key': '(E)', 'type': 'default', 'value': "under the mouse"},
        {'label': "Focus Plane", 'key': '(P)', 'type': 'default',
         'value': _PLANE_DISPLAY_LABELS[self.plane_display]},
        {'label': "Sharp Range", 'key': '(R)', 'type': 'default', 'value': range_value},
    ]
    if cam.dof.focus_object is not None:
        items.append({'label': "Focus Object", 'type': 'default',
                      'value': f"{cam.dof.focus_object.name}  (D or E clears it)"})
    info_row_count = len(items)

    items += [
        {'label': "F-Stop", 'key': '(A)', 'type': 'modal', 'highlight': self.mode == 'FSTOP',
         'value': "f/{:.1f}  (f/{:.1f})".format(cam.dof.aperture_fstop, initial['fstop'])},
        {'label': "Focus Distance", 'key': '(D)', 'type': 'modal', 'highlight': self.mode == 'DISTANCE',
         'value': "{}  ({})".format(format_length(scene, cam.dof.focus_distance),
                                    format_length(scene, initial['distance']))},
    ]

    items.append({'label': "Camera Focus", 'type': 'title'})
    title_row = len(items)

    if self.navigation:
        items.append({'label': "VIEWPORT NAVIGATION", 'type': 'title', 'highlight': True})
    elif self.ignore_input:
        items.append({'label': "IGNORE INPUT (ALT)", 'type': 'title', 'highlight': True})
    elif self.mode is None:
        items.append({'label': "PRESS D OR A TO ADJUST, E TO PICK", 'type': 'title'})

    font_id = 0
    font_size = _font_size(context)
    row_height = font_size * 1.5
    row_padding = font_size * 0.5
    center = context.area.width / 2
    text_left = center - 190 / 20 * font_size

    box_left = center - 240 / 20 * font_size
    box_right = center + 300 / 20 * font_size
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
# Operator
# ---------------------------------------------------------------------------

class CAM_MANAGER_OT_focus_distance(bpy.types.Operator):
    """Set the scene camera's focus distance and f-stop in the viewport.

    Nothing changes until a value is activated with its key: D focus
    distance, A f-stop. E focuses on the surface under the mouse. The focus
    plane is drawn in the scene with a cut line where it meets the surfaces
    in focus (P cycles Plane, Cut Line and Off), and dashed frames mark the
    near and far limits of the sharp range (R toggles them)."""

    bl_idname = "cam_manager.modal_focus_distance"
    bl_label = "Focus Distance"
    bl_description = "Set the focus distance and f-stop in the viewport, with a preview of the focus plane"
    bl_options = {'REGISTER', 'UNDO'}

    @staticmethod
    def _redraw(context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    def _capture_reference(self, event):
        """Start the next drag from the current values and mouse position."""
        dof = self.camera.data.dof
        self.ref = {'distance': dof.focus_distance, 'fstop': dof.aperture_fstop}
        self.mouse_initial_x = event.mouse_x

    def _release_focus_object(self):
        """A focus object overrides the focus distance, so setting the
        distance clears it (Esc puts it back)."""
        self.camera.data.dof.focus_object = None

    def _set_mode(self, mode, event, context):
        self.mode = None if self.mode == mode else mode
        if self.mode == 'DISTANCE':
            self._release_focus_object()
        self._capture_reference(event)
        self._redraw(context)

    def _cycle_guide(self, key, context):
        """P cycles the focus plane display, R shows or hides the sharp range."""
        if key == 'P':
            index = _PLANE_DISPLAYS.index(self.plane_display)
            self.plane_display = _PLANE_DISPLAYS[(index + 1) % len(_PLANE_DISPLAYS)]
        elif key == 'R':
            self.show_sharp_range = not self.show_sharp_range
        _guide_settings['plane_display'] = self.plane_display
        _guide_settings['show_sharp_range'] = self.show_sharp_range
        self._redraw(context)

    def _focus_under_mouse(self, context, event):
        """Set the focus distance to the surface under the mouse. Returns
        False when nothing in front of the camera is under the mouse."""
        region = context.region
        rv3d = context.region_data
        if region is None or rv3d is None:
            return False
        coord = (event.mouse_region_x, event.mouse_region_y)
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        hit, location, *_ = context.scene.ray_cast(context.evaluated_depsgraph_get(), origin, direction)
        if not hit:
            return False
        distance = distance_along_view(self.camera, location)
        if distance <= 0.0:
            return False
        self._release_focus_object()
        self.camera.data.dof.focus_distance = distance
        self._capture_reference(event)
        return True

    def _restore(self):
        dof = self.camera.data.dof
        init = self.initial
        dof.use_dof = init['use_dof']
        dof.focus_object = init['focus_object']
        dof.focus_distance = init['distance']
        dof.aperture_fstop = init['fstop']

    def _finish(self, context):
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
        """Record the starting values and turn depth of field on, so the
        viewport can show the blur while you adjust it."""
        self.camera = camera
        dof = camera.data.dof
        self.initial = {
            'use_dof': dof.use_dof,
            'focus_object': dof.focus_object,
            'distance': dof.focus_distance,
            'fstop': dof.aperture_fstop,
        }
        dof.use_dof = True

        self.mode = None
        self.ignore_input = False
        self.navigation = False
        self.plane_display = _guide_settings['plane_display']
        self.show_sharp_range = _guide_settings['show_sharp_range']
        self._capture_reference(event)

    @classmethod
    def poll(cls, context):
        return context.scene.camera is not None

    def invoke(self, context, event):
        camera = context.scene.camera
        if camera is None:
            self.report({'WARNING'}, "No scene camera assigned")
            return {'CANCELLED'}
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Focus Distance needs to be started from a 3D Viewport")
            return {'CANCELLED'}

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
        dof = self.camera.data.dof

        if event.type in _NAVIGATION_EVENTS:
            self.mode = None
            self.navigation = True
            self._redraw(context)
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE' and self.navigation:
            self.navigation = False
            self._redraw(context)

        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._restore()
            self._finish(context)
            return {'CANCELLED'}

        if event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            self._finish(context)
            return {'FINISHED'}

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

        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT', 'LEFT_CTRL', 'RIGHT_CTRL'} \
                and event.value in {'PRESS', 'RELEASE'}:
            self._capture_reference(event)
            return {'RUNNING_MODAL'}

        if event.type in _MODE_KEYS and event.value == 'RELEASE':
            self._set_mode(_MODE_KEYS[event.type], event, context)
            return {'RUNNING_MODAL'}

        if event.type in {'P', 'R'} and event.value == 'RELEASE':
            self._cycle_guide(event.type, context)
            return {'RUNNING_MODAL'}

        if event.type == 'E' and event.value == 'PRESS':
            if not self._focus_under_mouse(context, event):
                self.report({'INFO'}, "Nothing under the mouse to focus on")
            self._redraw(context)
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            self.ignore_input = False
            if self.mode is None:
                return {'PASS_THROUGH'}

            # Dragging to the right increases the active value.
            drag = event.mouse_x - self.mouse_initial_x

            def step(normal, fine, coarse):
                return coarse if event.ctrl else fine if event.shift else normal

            if self.mode == 'DISTANCE':
                # Proportional to the distance, so near and far focus feel the same.
                factor = math.exp(drag * step(0.004, 0.0005, 0.012))
                dof.focus_distance = max(self.ref['distance'] * factor, _MIN_DISTANCE)
            elif self.mode == 'FSTOP':
                # Full stops are powers of sqrt(2), so the f-stop changes geometrically too.
                factor = math.exp(drag * step(0.005, 0.0008, 0.015))
                dof.aperture_fstop = min(max(self.ref['fstop'] * factor, _MIN_FSTOP), _MAX_FSTOP)

            self._redraw(context)
            return {'RUNNING_MODAL'}

        # Block other hotkeys (G, R, S, ...) while the operator runs.
        return {'RUNNING_MODAL'}


classes = (
    CAM_MANAGER_OT_focus_distance,
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
