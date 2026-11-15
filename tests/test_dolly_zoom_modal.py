"""
Behaviour tests for the Dolly Zoom modal operator (dolly_zoom_modal.py).

A modal operator can't receive real mouse/key events in background mode, so
these call the operator's own modal() with simulated events on a real
camera, the way Blender would while it runs.

Run individually with::

    blender --background --factory-startup --python tests/test_dolly_zoom_modal.py
"""

import math
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_SOURCE = os.path.dirname(_ADDON_ROOT)
_ADDON_NAME = os.path.basename(_ADDON_ROOT)

if _ADDON_SOURCE not in sys.path:
    sys.path.insert(0, _ADDON_SOURCE)

import addon_utils  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

addon_utils.enable(_ADDON_NAME, default_set=True)

import simple_camera_manager as _addon  # noqa: E402

dolly = _addon.dolly_zoom_modal
_OP = dolly.CAM_MANAGER_OT_dolly_zoom


class _FakeOperator:
    """Carries the operator's real methods without needing Blender to
    instantiate the Operator (which only happens through bpy.ops)."""

    def __init__(self):
        self.reports = []

    def report(self, type, message):
        self.reports.append((type, message))


for _name in ('modal', '_init_state', '_set_mode', '_capture_reference', '_finish', '_redraw',
              '_update_width', '_dolly_to_angle', '_cycle_guide'):
    setattr(_FakeOperator, _name, _OP.__dict__[_name])


def _event(type, value='NOTHING', mouse_x=500, alt=False, shift=False, ctrl=False):
    return SimpleNamespace(type=type, value=value, mouse_x=mouse_x, mouse_y=300,
                           alt=alt, shift=shift, ctrl=ctrl)


class TestDollyZoomModal(unittest.TestCase):

    def setUp(self):
        self.camera_data = bpy.data.cameras.new('DollyTestCam')
        self.camera_obj = bpy.data.objects.new('DollyTestCam', self.camera_data)
        bpy.context.scene.collection.objects.link(self.camera_obj)
        self.camera_obj.location = (0.0, -10.0, 1.0)
        self.camera_obj.rotation_euler = (math.radians(90), 0.0, 0.0)
        self.camera_data.lens = 50.0
        self.camera_data.dolly_zoom_target_distance = 10.0
        self.camera_data.dolly_zoom_target_scale = 1.23
        self.camera_data.show_dolly_gizmo = False
        bpy.context.view_layer.update()

        dolly._guide_settings.update(target_plane_display='PLANE', show_start_frame=True)
        self.context = SimpleNamespace(
            area=mock.MagicMock(),
            screen=SimpleNamespace(areas=[]),
        )
        self.op = _FakeOperator()
        self.op._init_state(self.camera_obj, _event('NONE'))

        self.start_location = self.camera_obj.location.copy()

    def tearDown(self):
        dolly._running.discard(id(self.op))
        bpy.data.objects.remove(self.camera_obj, do_unlink=True)
        bpy.data.cameras.remove(self.camera_data)

    def _send(self, *args, **kwargs):
        return self.op.modal(self.context, _event(*args, **kwargs))

    def _frame_width_at_target(self):
        cam = self.camera_data
        return dolly.calculate_target_width(cam.dolly_zoom_target_distance, cam.angle)

    def test_starts_idle_and_shows_gizmo(self):
        self.assertIsNone(self.op.mode)
        self.assertTrue(self.camera_data.show_dolly_gizmo)

    def test_mouse_move_without_key_changes_nothing_and_passes_through(self):
        result = self._send('MOUSEMOVE', mouse_x=300)
        self.assertEqual(result, {'PASS_THROUGH'})
        self.assertEqual(self.camera_data.lens, 50.0)
        self.assertEqual(self.camera_obj.location, self.start_location)

    def _distance_to_start_target(self):
        target = self.op.initial_cam_settings['target_location']
        return (self.camera_obj.location - target).length

    def test_f_increases_focal_length_and_dollies_back(self):
        width_before = self._frame_width_at_target()
        self._send('F', 'RELEASE')
        self.assertEqual(self.op.mode, 'FOCAL')

        result = self._send('MOUSEMOVE', mouse_x=600)  # 100 px right
        self.assertEqual(result, {'RUNNING_MODAL'})
        self.assertAlmostEqual(self.camera_data.lens, 60.0, places=3)
        # longer lens -> camera moves away from the target, which keeps its size
        self.assertGreater(self._distance_to_start_target(), 10.0 + 1e-3)
        self.assertAlmostEqual(self._distance_to_start_target(),
                               self.camera_data.dolly_zoom_target_distance, places=4)
        self.assertAlmostEqual(self._frame_width_at_target(), width_before, places=4)

    def test_v_increases_field_of_view_and_dollies_in(self):
        width_before = self._frame_width_at_target()
        fov_before = self.camera_data.angle
        self._send('V', 'RELEASE')
        self.assertEqual(self.op.mode, 'FOV')

        self._send('MOUSEMOVE', mouse_x=600)  # 100 px right = +10 degrees
        self.assertAlmostEqual(self.camera_data.angle, fov_before + math.radians(10.0), places=4)
        self.assertLess(self.camera_data.lens, 50.0)
        self.assertLess(self._distance_to_start_target(), 10.0 - 1e-3)
        self.assertAlmostEqual(self._frame_width_at_target(), width_before, places=4)

    def test_focal_length_and_fov_are_clamped(self):
        self._send('F', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=-100000)
        self.assertGreaterEqual(self.camera_data.lens, 1.0)
        self._send('V', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=100000)
        self.assertLessEqual(math.degrees(self.camera_data.angle), 170.0 + 1e-3)

    def test_orthographic_camera_ignores_f_and_v_and_says_why(self):
        self.camera_data.type = 'ORTHO'
        self._send('F', 'RELEASE')
        self._send('V', 'RELEASE')
        self.assertIsNone(self.op.mode)
        self.assertEqual(self.op.reports, [({'WARNING'}, dolly._ORTHO_MESSAGE)] * 2)

    def test_overlay_marks_f_and_v_as_perspective_only_on_ortho_camera(self):
        self.assertNotIn(dolly._PERSPECTIVE_ONLY, self._draw_overlay_text())
        self.camera_data.type = 'ORTHO'
        self.assertEqual(self._draw_overlay_text().count(dolly._PERSPECTIVE_ONLY), 2)

    def test_w_changes_target_width_without_moving_camera(self):
        self._send('W', 'RELEASE')
        self.assertEqual(self.op.mode, 'WIDTH')
        width_before = self.camera_data.dolly_zoom_target_scale
        self._send('MOUSEMOVE', mouse_x=600)
        self.assertGreater(self.camera_data.dolly_zoom_target_scale, width_before)
        self.assertEqual(self.camera_obj.location, self.start_location)
        self.assertAlmostEqual(self._frame_width_at_target(), self.camera_data.dolly_zoom_target_scale, places=4)

    def test_same_key_again_turns_the_value_off(self):
        self._send('F', 'RELEASE')
        self._send('F', 'RELEASE')
        self.assertIsNone(self.op.mode)
        self.assertEqual(self._send('MOUSEMOVE', mouse_x=300), {'PASS_THROUGH'})

    def test_only_one_value_active_at_a_time(self):
        self._send('F', 'RELEASE')
        self._send('D', 'RELEASE')
        self.assertEqual(self.op.mode, 'DISTANCE')
        self._send('W', 'RELEASE')
        self.assertEqual(self.op.mode, 'WIDTH')
        self._send('V', 'RELEASE')
        self.assertEqual(self.op.mode, 'FOV')

    def test_z_does_nothing(self):
        self._send('Z', 'RELEASE')
        self.assertIsNone(self.op.mode)

    def test_d_changes_only_the_target_distance(self):
        self._send('D', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=560)
        self.assertGreater(self.camera_data.dolly_zoom_target_distance, 10.0)
        self.assertEqual(self.camera_data.lens, 50.0)
        self.assertEqual(self.camera_obj.location, self.start_location)

    def test_click_on_highlighted_gizmo_passes_through_while_idle(self):
        with mock.patch.object(_addon.camera_gizmos, 'any_interactive_gizmo_highlighted', return_value=True):
            self.assertEqual(self._send('LEFTMOUSE', 'PRESS'), {'PASS_THROUGH'})

    def test_click_elsewhere_confirms_and_restores_gizmo_visibility(self):
        with mock.patch.object(_addon.camera_gizmos, 'any_interactive_gizmo_highlighted', return_value=False):
            self.assertEqual(self._send('LEFTMOUSE', 'PRESS'), {'FINISHED'})
        self.assertFalse(self.camera_data.show_dolly_gizmo)

    def test_click_confirms_while_a_value_is_active_even_over_a_gizmo(self):
        self._send('F', 'RELEASE')
        with mock.patch.object(_addon.camera_gizmos, 'any_interactive_gizmo_highlighted', return_value=True):
            self.assertEqual(self._send('LEFTMOUSE', 'PRESS'), {'FINISHED'})

    def test_enter_confirms(self):
        self.assertEqual(self._send('RET', 'PRESS'), {'FINISHED'})

    def test_escape_restores_everything(self):
        self._send('F', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=400)
        self._send('D', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=600)

        self.assertEqual(self._send('ESC', 'PRESS'), {'CANCELLED'})
        self.assertEqual(self.camera_obj.location, self.start_location)
        self.assertAlmostEqual(self.camera_data.lens, 50.0, places=4)
        self.assertAlmostEqual(self.camera_data.dolly_zoom_target_distance, 10.0, places=4)
        self.assertAlmostEqual(self.camera_data.dolly_zoom_target_scale, 1.23, places=4)
        self.assertFalse(self.camera_data.show_dolly_gizmo)

    def test_escape_restores_roll_made_with_the_gizmo(self):
        start_rotation = self.camera_obj.rotation_euler.copy()
        self.camera_obj.rotation_euler.y += math.radians(20)  # as the roll gizmo would
        self._send('ESC', 'PRESS')
        for got, expected in zip(self.camera_obj.rotation_euler, start_rotation):
            self.assertAlmostEqual(got, expected, places=5)

    def test_is_running_while_active_only(self):
        self.assertTrue(dolly.is_running())
        self._send('RET', 'PRESS')
        self.assertFalse(dolly.is_running())

    def test_navigation_passes_through_and_stops_the_active_value(self):
        self._send('F', 'RELEASE')
        self.assertEqual(self._send('MIDDLEMOUSE', 'PRESS'), {'PASS_THROUGH'})
        self.assertIsNone(self.op.mode)

    def test_alt_ignores_mouse_movement(self):
        self._send('F', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=300, alt=True)
        self.assertEqual(self.camera_obj.location, self.start_location)

    def test_other_hotkeys_are_blocked(self):
        self.assertEqual(self._send('G', 'PRESS'), {'RUNNING_MODAL'})

    def _draw_overlay_text(self):
        fake_bpy = SimpleNamespace(context=SimpleNamespace(
            area=SimpleNamespace(width=1200), preferences=bpy.context.preferences))
        self.op.as_pointer = lambda: 1
        with mock.patch.object(dolly, 'bpy', fake_bpy), \
                mock.patch.object(dolly, '_draw_rect'), \
                mock.patch.object(dolly, 'blf') as fake_blf:
            dolly.draw_callback_px(self.op, None)
        return [c.args[1] for c in fake_blf.draw.call_args_list]

    def test_overlay_lists_keys_and_prompts_while_idle(self):
        texts = self._draw_overlay_text()
        for expected in ("Dolly Zoom", "Focal Length", "(F)", "Field of View", "(V)",
                         "Target Distance", "(D)", "Target Width", "(W)", "PRESS F, V, D OR W TO ADJUST"):
            self.assertIn(expected, texts)
        self.assertNotIn("(Z)", texts)

    def test_overlay_shows_ignore_input_while_alt_is_held(self):
        self._send('F', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=300, alt=True)
        self.assertIn("IGNORE INPUT (ALT)", self._draw_overlay_text())

    def test_overlay_lists_guide_toggles(self):
        texts = self._draw_overlay_text()
        for expected in ("Target Plane", "(P)", "Start Framing", "(R)"):
            self.assertIn(expected, texts)

    # -- 3D guides ---------------------------------------------------------

    def _frame_center_and_width(self, corners):
        center = sum(corners, Vector()) / 4
        width = (corners[0] - corners[3]).length  # top right to top left
        return center, width

    def test_frame_corners_lie_on_the_target_plane_and_match_the_target_width(self):
        corners = dolly.frame_corners_at_distance(self.camera_obj, bpy.context.scene, 10.0)
        self.assertEqual(len(corners), 4)
        forward = self.camera_obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
        for corner in corners:
            depth = (corner - self.camera_obj.location).dot(forward.normalized())
            self.assertAlmostEqual(depth, 10.0, places=4)
        center, width = self._frame_center_and_width(corners)
        expected_center = dolly.generate_target_location(self.camera_obj, 10.0)
        self.assertAlmostEqual((center - expected_center).length, 0.0, places=4)
        self.assertAlmostEqual(width, 2 * self._frame_width_at_target(), places=4)

    def test_frame_corners_ignore_camera_object_scale(self):
        expected = dolly.frame_corners_at_distance(self.camera_obj, bpy.context.scene, 10.0)
        self.camera_obj.scale = (3.0, 3.0, 3.0)
        bpy.context.view_layer.update()
        got = dolly.frame_corners_at_distance(self.camera_obj, bpy.context.scene, 10.0)
        for a, b in zip(got, expected):
            self.assertAlmostEqual((a - b).length, 0.0, places=4)

    def test_start_frame_stays_put_while_the_lens_changes(self):
        start = [c.copy() for c in self.op.start_frame_corners]
        self._send('W', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=700)
        self._send('F', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=900)
        for a, b in zip(self.op.start_frame_corners, start):
            self.assertEqual(a, b)
        # ...while the current frame on the start plane did change
        now = dolly.frame_corners_at_distance(self.camera_obj, bpy.context.scene, 10.0)
        self.assertNotAlmostEqual(self._frame_center_and_width(now)[1],
                                  self._frame_center_and_width(start)[1], places=3)

    def test_p_cycles_the_plane_display_and_r_toggles_the_start_frame(self):
        self._send('F', 'RELEASE')
        self.assertEqual(self.op.target_plane_display, 'PLANE')
        self.assertTrue(self.op.show_start_frame)
        seen = []
        for _ in range(3):
            self._send('P', 'RELEASE')
            seen.append(self.op.target_plane_display)
        self.assertEqual(seen, ['LINE', 'OFF', 'PLANE'])
        self._send('R', 'RELEASE')
        self.assertFalse(self.op.show_start_frame)
        self.assertEqual(self.op.mode, 'FOCAL')

    def test_overlay_shows_the_plane_display(self):
        self._send('P', 'RELEASE')
        self.assertIn("Cut Line", self._draw_overlay_text())

    def test_next_run_starts_with_the_last_guide_settings(self):
        self._send('P', 'RELEASE')
        self._send('R', 'RELEASE')
        self._send('RET', 'PRESS')
        op = _FakeOperator()
        op._init_state(self.camera_obj, _event('NONE'))
        try:
            self.assertEqual(op.target_plane_display, 'LINE')
            self.assertFalse(op.show_start_frame)
        finally:
            dolly._running.discard(id(op))

    def test_dashed_loop_is_dashed_and_stays_on_the_edges(self):
        corners = [Vector((1, 1, 0)), Vector((1, -1, 0)), Vector((-1, -1, 0)), Vector((-1, 1, 0))]
        points = dolly.dashed_loop_segments(corners, dashes_on_longest_edge=4)
        self.assertEqual(len(points) % 2, 0)
        self.assertEqual(len(points) // 2, 16)  # 4 dashes on each of the 4 equal edges
        for p in points:
            self.assertAlmostEqual(max(abs(p.x), abs(p.y)), 1.0, places=6)
        self.assertEqual(dolly.dashed_loop_segments([Vector()] * 4), [])

    def _draw_guides(self):
        rv3d = SimpleNamespace(view_matrix=self.camera_obj.matrix_world.inverted(), is_perspective=True)
        fake_bpy = SimpleNamespace(context=SimpleNamespace(
            scene=bpy.context.scene, region=SimpleNamespace(width=1200, height=800), region_data=rv3d))
        self.op.as_pointer = lambda: 1
        with mock.patch.object(dolly, 'bpy', fake_bpy), \
                mock.patch.object(dolly, 'gpu') as fake_gpu, \
                mock.patch.object(dolly, '_draw_quad') as quads, \
                mock.patch.object(dolly, '_draw_lines') as lines:
            fake_gpu.state.depth_mask_get.return_value = True
            dolly.draw_callback_view(self.op, None)
        return quads, lines, fake_gpu

    def _quad_distances(self, quads):
        """Depth in front of the camera of each quad drawn, with its color."""
        forward = (self.camera_obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
        return [(round((c.args[0][0] - self.camera_obj.location).dot(forward), 4), tuple(c.args[1]))
                for c in quads.call_args_list]

    def test_plane_display_draws_cut_line_then_plane_depth_tested(self):
        quads, lines, fake_gpu = self._draw_guides()
        drawn = self._quad_distances(quads)
        band = 10.0 * dolly._CUT_LINE_BAND
        # cut line: two inverting quads just before and just past the target
        (near, _), (far, _) = drawn[:2]
        self.assertAlmostEqual(10.0 - near, far - 10.0, places=3)
        self.assertTrue(0.5 * band < far - 10.0 <= band)
        fake_gpu.state.blend_set.assert_any_call('INVERT')
        # then the translucent plane on the target
        self.assertEqual(drawn[2], (10.0, dolly._COLOR_TARGET_PLANE))
        self.assertEqual(len(drawn), 3)
        fake_gpu.state.depth_test_set.assert_any_call('LESS_EQUAL')
        self.assertEqual(fake_gpu.state.depth_mask_set.call_args_list[-1].args, (True,))
        lines.assert_called_once()

    def test_cut_line_quads_cover_the_same_pixels(self):
        corners = dolly.frame_corners_at_distance(self.camera_obj, bpy.context.scene, 10.0)
        eye = Vector((7.0, -3.0, 6.0))  # some other perspective view
        near, far = dolly.cut_line_quads(corners, 0.05, eye=eye)
        for a, b, c in zip(near, far, corners):
            self.assertAlmostEqual((a - eye).normalized().dot((b - eye).normalized()), 1.0, places=6)
            self.assertAlmostEqual((b - a).length, 0.1, places=6)
            self.assertLess((a - eye).length, (c - eye).length)
        direction = Vector((0.0, 1.0, 0.0))  # orthographic view
        near, far = dolly.cut_line_quads(corners, 0.05, view_direction=direction)
        for a, b in zip(near, far):
            self.assertAlmostEqual(((b - a) - direction * 0.1).length, 0.0, places=6)

    def test_cut_line_display_draws_no_plane(self):
        self._send('P', 'RELEASE')
        quads, _, fake_gpu = self._draw_guides()
        self.assertEqual(len(quads.call_args_list), 2)
        fake_gpu.state.blend_set.assert_any_call('INVERT')

    def test_plane_is_stronger_while_distance_or_width_is_active(self):
        idle_color = self._quad_distances(self._draw_guides()[0])[-1][1]
        self._send('D', 'RELEASE')
        active_color = self._quad_distances(self._draw_guides()[0])[-1][1]
        self.assertGreater(active_color[3], idle_color[3])

    def test_guides_set_to_off_are_not_drawn(self):
        self._send('P', 'RELEASE')
        self._send('P', 'RELEASE')
        self._send('R', 'RELEASE')
        quads, lines, _ = self._draw_guides()
        quads.assert_not_called()
        lines.assert_not_called()

    def test_guides_skip_drawing_after_operator_is_freed(self):
        def freed():
            raise ReferenceError
        self.op.as_pointer = freed
        with mock.patch.object(dolly, '_draw_quad') as quads:
            dolly.draw_callback_view(self.op, None)
        quads.assert_not_called()

    def test_overlay_skips_drawing_after_operator_is_freed(self):
        def freed():
            raise ReferenceError
        self.op.as_pointer = freed
        with mock.patch.object(dolly, 'blf') as fake_blf:
            dolly.draw_callback_px(self.op, None)
        fake_blf.draw.assert_not_called()


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
