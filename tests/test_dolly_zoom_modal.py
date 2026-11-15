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

addon_utils.enable(_ADDON_NAME, default_set=True)

import simple_camera_manager as _addon  # noqa: E402

dolly = _addon.dolly_zoom_modal
_OP = dolly.CAM_MANAGER_OT_dolly_zoom


class _FakeOperator:
    """Carries the operator's real methods without needing Blender to
    instantiate the Operator (which only happens through bpy.ops)."""


for _name in ('modal', '_init_state', '_set_mode', '_capture_reference', '_finish', '_redraw',
              '_update_width', '_dolly_to_angle'):
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

    def test_orthographic_camera_ignores_f_and_v(self):
        self.camera_data.type = 'ORTHO'
        self._send('F', 'RELEASE')
        self._send('V', 'RELEASE')
        self.assertIsNone(self.op.mode)

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
