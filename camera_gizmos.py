import math

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.types import (
    GizmoGroup,
    Gizmo
)
from bpy_extras.view3d_utils import location_3d_to_region_2d
from .dolly_zoom_modal import calculate_target_width

import mathutils


# ---------------------------------------------------------------------------
# Camera status indicator (locked / linked-to-view chips)
# ---------------------------------------------------------------------------

_draw_handler = None

_CHIP_BG_COLOR = (0.05, 0.05, 0.06, 0.75)
_CHIP_TEXT_COLOR = (0.95, 0.95, 0.95, 1.0)


def _get_camera_frame_rect(region, rv3d, scene, cam_ob):
    """Return (x, y, width, height) of the camera's render frame as actually drawn on screen,
    in region pixel space - accounts for the current view zoom/pan, not just a
    viewport-filling letterbox, so it matches Blender's own passepartout box even when
    navigating around within camera view."""
    corners_local = cam_ob.data.view_frame(scene=scene)
    mat = cam_ob.matrix_world
    coords_2d = []
    for corner in corners_local:
        co2d = location_3d_to_region_2d(region, rv3d, mat @ corner)
        if co2d is None:
            return None
        coords_2d.append(co2d)

    xs = [co.x for co in coords_2d]
    ys = [co.y for co in coords_2d]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return x0, y0, x1 - x0, y1 - y0


def _draw_rect(x0, y0, x1, y1, color):
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRI_FAN', {"pos": ((x0, y0), (x1, y0), (x1, y1), (x0, y1))})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_frame_border_outside(x0, y0, x1, y1, thickness, color):
    """Draw a solid coloured border hugging the outside edge of the given rect, so it never
    covers the rendered image inside the camera frame."""
    _draw_rect(x0 - thickness, y1, x1 + thickness, y1 + thickness, color)  # top
    _draw_rect(x0 - thickness, y0 - thickness, x1 + thickness, y0, color)  # bottom
    _draw_rect(x0 - thickness, y0 - thickness, x0, y1 + thickness, color)  # left
    _draw_rect(x1, y0 - thickness, x1 + thickness, y1 + thickness, color)  # right


def _draw_status_chip(x0, y0, label, accent_color, ui_scale):
    """Draw a small pill-shaped label with a coloured accent stripe, bottom-left corner at (x0, y0).
    Returns the (width, height) of the drawn chip, so callers can stack multiple chips."""
    font_id = 0
    text_size = round(12 * ui_scale)
    blf.size(font_id, text_size)
    text_w, text_h = blf.dimensions(font_id, label)

    stripe_w = round(3 * ui_scale)
    pad_x = round(9 * ui_scale)
    pad_y = round(6 * ui_scale)

    box_w = stripe_w + pad_x * 2 + text_w
    box_h = text_h + pad_y * 2

    _draw_rect(x0, y0, x0 + box_w, y0 + box_h, _CHIP_BG_COLOR)
    _draw_rect(x0, y0, x0 + stripe_w, y0 + box_h, accent_color)

    blf.color(font_id, *_CHIP_TEXT_COLOR)
    blf.position(font_id, x0 + stripe_w + pad_x, y0 + pad_y, 0)
    blf.draw(font_id, label)

    return box_w, box_h


def _draw_camera_status_overlay():
    """Draw small status chips in the bottom-left corner of the camera frame for locked or linked cameras."""
    context = bpy.context
    if not context or not context.scene:
        return

    rv3d = context.region_data
    if not rv3d or rv3d.view_perspective != 'CAMERA':
        return

    space = context.space_data
    if not space or space.type != 'VIEW_3D':
        return

    cam_ob = context.scene.camera
    if not cam_ob or cam_ob.type != 'CAMERA':
        return

    is_locked = bool(cam_ob.get('lock', False))
    is_linked = space.lock_camera

    if not is_locked and not is_linked:
        return

    try:
        prefs = context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        return

    entries = []
    if is_locked:
        entries.append(("Camera Locked", tuple(prefs.locked_camera_overlay_color)))
    if is_linked:
        entries.append(("Linked to View", tuple(prefs.linked_camera_overlay_color)))

    region = context.region
    frame_rect = _get_camera_frame_rect(region, rv3d, context.scene, cam_ob)
    if frame_rect is None:
        return
    x, y, fw, fh = frame_rect
    ui_scale = context.preferences.system.ui_scale
    margin = round(14 * ui_scale)
    gap = round(6 * ui_scale)

    gpu.state.blend_set('ALPHA')

    # Nested borders hugging the outside of the camera frame - one per active state, so
    # both remain distinguishable when a camera is both locked and view-linked, and
    # neither ever covers the rendered image inside the frame.
    border_thickness = max(2, round(3 * ui_scale))
    border_gap = round(2 * ui_scale)
    bx0, by0, bx1, by1 = x, y, x + fw, y + fh
    for i, (_label, accent_color) in enumerate(entries):
        outset = i * (border_thickness + border_gap)
        _draw_frame_border_outside(bx0 - outset, by0 - outset, bx1 + outset, by1 + outset,
                                    border_thickness, accent_color)

    cursor_y = y + margin
    for label, accent_color in entries:
        _, box_h = _draw_status_chip(x + margin, cursor_y, label, accent_color, ui_scale)
        cursor_y += box_h + gap

    gpu.state.blend_set('NONE')


# # Coordinates (each one is a line).
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


class MyCustomShapeWidget(Gizmo):
    """Custom gizmo widget that draws the dolly zoom target frame and handles drag interaction."""

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
            # verts (sequence of 2D or 3D coordinates.) – Coordinates.
            # display_name (Callable that takes a string and returns a string.) – Optional callback that takes the full path, returns the name to display.
            self.custom_shape = self.new_custom_shape('LINES', custom_shape_verts_02)


    def invoke(self, context, event):
        self.init_mouse_x = event.mouse_x
        self.init_value = self.target_get_value('offset')[0]
        return {'RUNNING_MODAL'}

    def exit(self, context, cancel):
        context.area.header_text_set(None)
        if cancel:
            self.target_set_value("offset", self.init_value)[0]

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


class CameraFocusDistance(GizmoGroup):
    """Gizmo group that displays the dolly zoom target distance frame in the 3D viewport."""

    bl_idname = "OBJECT_GGT_focus_distance_camera"
    bl_label = "Camera Focus Distance Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SHOW_MODAL_ALL', 'DEPTH_3D'}

    # DEPTH_3D allows for objects in the scene to overlap gizmos. It causes for gizmos not to work properly since Blender 3.1
    # bl_options = {'3D', 'PERSISTENT', 'SHOW_MODAL_ALL', 'DEPTH_3D'}

    cam = None

    @classmethod
    def poll(cls, context):
        ob = context.object
        if ob and ob.type == 'CAMERA':
            return ob.data.show_dolly_gizmo

    def setup(self, context):
        camera = context.object
        self.cam = camera

        gizmo = self.gizmos.new(MyCustomShapeWidget.bl_idname)
        # gizmo = self.gizmos.new("GIZMO_GT_arrow_3d")
        # gizmo = self.gizmos.new("GIZMO_GT_primitive_3d")
        # gizmo.use_draw_offset_scale = False

        gizmo.use_draw_scale = False
        gizmo.use_draw_offset_scale = True

        # Needed to work with modal operator
        gizmo.use_draw_modal = True

        gizmo.color = (1.0, 1.0, 1.0)
        gizmo.color_highlight = (1.0, 1.0, 0.0)

        # Draw only when hovering
        # gizmo.use_draw_hover = True

        def get_dolly_zoom_target_distance():
            if self.cam:
                return self.cam.data.dolly_zoom_target_distance
            else:
                return (0.0,)

        def set_dolly_zoom_target_distance(value):
            if self.cam:
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

        render = context.scene.render
        aspect = (render.resolution_x * render.pixel_aspect_x) / (render.resolution_y * render.pixel_aspect_y)

        scale_matrix_x2 = mathutils.Matrix.Scale(scale, 4, (1.0, 0.0, 0.0))
        scale_matrix_y2 = mathutils.Matrix.Scale(scale / aspect, 4, (0.0, 1.0, 0.0))
        scale_matrix_z2 = mathutils.Matrix.Scale(1, 4, (0.0, 0.0, 1.0))

        scale_mat = scale_matrix_x2 @ scale_matrix_y2 @ scale_matrix_z2

        # assemble the new matrix
        mat_out = orig_loc_mat @ orig_rot_mat @ scale_mat

        self.distance_gizmo.matrix_basis = mat_out


# TODO(#67): first working pass on the camera roll gizmo - the ring interaction
# and visuals still need refinement (feel, sizing, discoverability) before this
# is considered done.

# Positioned exactly at the camera's own location, a roll ring would sit right
# at the eye point - invisible while looking through that same camera, since
# anything drawn at the viewpoint itself projects to zero size. Offset it
# forward (local -Z, the camera's view direction) by a fixed amount in the
# gizmo's own auto-scaled space so it stays visible both from outside the
# camera and from within its own view.
_ROLL_GIZMO_FORWARD_OFFSET = -1.2

_ROLL_RING_SEGMENTS = 48
_ROLL_RING_RADIUS = 1.0
_roll_ring_verts = tuple(
    (
        _ROLL_RING_RADIUS * math.cos(2 * math.pi * i / _ROLL_RING_SEGMENTS),
        _ROLL_RING_RADIUS * math.sin(2 * math.pi * i / _ROLL_RING_SEGMENTS),
        0.0,
    )
    for i in range(_ROLL_RING_SEGMENTS + 1)  # +1 to close the loop
)

_ROLL_SNAP_STEP = math.radians(5.0)


def _get_camera_roll(cam_ob):
    """Return the camera's current roll relative to level (world Z up), in radians.

    Raw rotation_euler.z is NOT this - for 'XYZ' Euler order it's the last-applied
    rotation, so once the camera has any pitch/yaw, changing it directly rotates
    around a fixed world axis rather than the camera's own current view axis
    (verified: forward direction visibly changes). This instead measures the angle
    between the camera's actual 'up' vector and a level reference, around its own
    forward axis, so it stays meaningful regardless of pitch/yaw.
    """
    mat = cam_ob.matrix_world.to_3x3().normalized()
    forward = mat @ mathutils.Vector((0, 0, -1))
    up = mat @ mathutils.Vector((0, 1, 0))

    # World Z can't serve as the level reference when looking straight up/down
    # (forward parallel to it - the projection collapses to zero, which used to
    # make this silently report 0.0 regardless of the camera's actual roll,
    # e.g. rotation_euler = (0, 0, 0.2°) points straight down world -Z, so the
    # roll was invisible to callers and re-emerged as a jump once you rolled
    # away from that orientation). World X is never parallel to world Z, so it
    # always works as a fallback reference for exactly that case.
    world_up = mathutils.Vector((0, 0, 1))
    reference_up = world_up - forward * world_up.dot(forward)
    if reference_up.length < 1e-4:
        world_x = mathutils.Vector((1, 0, 0))
        reference_up = world_x - forward * world_x.dot(forward)
    reference_up.normalize()

    cos_angle = max(-1.0, min(1.0, up.dot(reference_up)))
    angle = math.acos(cos_angle)
    if reference_up.cross(up).dot(forward) < 0:
        angle = -angle
    return angle


def _apply_camera_roll_delta(cam_ob, init_quat, delta):
    """Roll the camera by `delta` radians around its own current view axis, starting
    from the orientation captured in `init_quat` - post-multiplying a local -Z
    (forward-axis) delta is what keeps the forward direction fixed while only the
    roll changes; touching rotation_euler.z directly does not (see _get_camera_roll)."""
    roll_quat = mathutils.Quaternion((0, 0, -1), delta)
    new_quat = init_quat @ roll_quat
    cam_ob.rotation_euler = new_quat.to_euler(cam_ob.rotation_mode)


class CameraRollWidget(Gizmo):
    """Custom gizmo that draws a ring for rolling the camera around its own view axis.

    Dragging tracks the mouse angle around the ring's on-screen center, so
    turning the ring visually matches the drag - holding Shift snaps the
    result to 5-degree increments and the current roll is shown in the
    viewport header while dragging.

    Reads/writes the camera directly via self.group.cam rather than through
    Blender's generic target_get_value/target_set_handler property system -
    that system polls the getter at times outside our control (redraws, hover
    state, etc.), and a getter with the side effect of snapshotting "where the
    drag started" breaks the moment it's called more than once per drag.
    """

    bl_idname = "Custom_Camera_Roll_Gizmo"

    __slots__ = (
        "custom_shape",
        "pivot_2d",
        "init_angle",
        "init_quat",
        "init_value",
        "sign",
    )

    def _apply_forward_offset(self):
        self.matrix_offset.col[3][2] = _ROLL_GIZMO_FORWARD_OFFSET

    def draw(self, context):
        self._apply_forward_offset()
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self._apply_forward_offset()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('LINE_STRIP', _roll_ring_verts)

    def invoke(self, context, event):
        cam = self.group.cam
        self.init_quat = cam.rotation_euler.to_quaternion() if cam else mathutils.Quaternion()
        self.init_value = _get_camera_roll(cam) if cam else 0.0

        region = context.region
        rv3d = context.region_data
        origin_2d = location_3d_to_region_2d(region, rv3d, self.matrix_world.translation)
        self.pivot_2d = origin_2d if origin_2d else (event.mouse_region_x, event.mouse_region_y)

        self.init_angle = math.atan2(
            event.mouse_region_y - self.pivot_2d[1],
            event.mouse_region_x - self.pivot_2d[0],
        )

        # A screen-space CCW drag only matches a CCW roll around the view axis
        # when you're looking at the ring's "front" face. From the other side
        # (e.g. orbited around to view the camera from in front of the lens,
        # since the ring sits forward of it) the same drag reads backwards
        # unless this is flipped.
        gaze = rv3d.view_rotation @ mathutils.Vector((0.0, 0.0, -1.0))
        axis = self.init_quat @ mathutils.Vector((0.0, 0.0, -1.0))
        self.sign = -1.0 if gaze.dot(axis) > 0 else 1.0

        return {'RUNNING_MODAL'}

    def exit(self, context, cancel):
        context.area.header_text_set(None)
        cam = self.group.cam
        if cancel and cam:
            cam.rotation_euler = self.init_quat.to_euler(cam.rotation_mode)

    def modal(self, context, event, tweak):
        cam = self.group.cam
        if not cam:
            return {'RUNNING_MODAL'}

        current_angle = math.atan2(
            event.mouse_region_y - self.pivot_2d[1],
            event.mouse_region_x - self.pivot_2d[0],
        )
        delta = self.sign * (current_angle - self.init_angle)
        value = self.init_value + delta

        # Read the live modifier state directly rather than the gizmo tweak
        # system's 'PRECISE' flag - that only fires on a Shift press *during*
        # the active drag, so Shift held before the click never registers.
        if event.shift:
            value = round(value / _ROLL_SNAP_STEP) * _ROLL_SNAP_STEP

        _apply_camera_roll_delta(cam, self.init_quat, value - self.init_value)
        context.area.header_text_set("Camera Roll: %.1f°" % math.degrees(value))
        return {'RUNNING_MODAL'}


class CameraRotationGizmo(GizmoGroup):
    """Gizmo group that shows a ring for rolling the camera around its own view axis."""

    bl_idname = "OBJECT_GGT_camera_rotation"
    bl_label = "Camera Rotation Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    cam = None

    @classmethod
    def poll(cls, context):
        ob = context.object
        if ob and ob.type == 'CAMERA':
            return ob.data.show_rotation_gizmo

    def setup(self, context):
        camera = context.object
        self.cam = camera

        gizmo = self.gizmos.new(CameraRollWidget.bl_idname)
        gizmo.use_draw_modal = True

        gizmo.color = 0.8, 0.8, 0.8
        gizmo.alpha = 0.5

        gizmo.color_highlight = 1.0, 1.0, 1.0
        gizmo.alpha_highlight = 1.0

        gizmo.line_width = 3
        gizmo.scale_basis = 1.0

        gizmo.matrix_basis = camera.matrix_world.normalized()

        self.roll_gizmo = gizmo

    def refresh(self, context):
        camera = context.object
        self.cam = camera
        self.roll_gizmo.matrix_basis = camera.matrix_world.normalized()


classes = (
    CameraFocusDistance,
    MyCustomShapeWidget,
    CameraRollWidget,
    CameraRotationGizmo,
)


def register():
    global _draw_handler
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
        _draw_camera_status_overlay, (), 'WINDOW', 'POST_PIXEL'
    )


def unregister():
    global _draw_handler
    from bpy.utils import unregister_class

    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None

    for cls in reversed(classes):
        if hasattr(cls, 'bl_rna'):
            unregister_class(cls)
