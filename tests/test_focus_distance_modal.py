"""
Behaviour tests for the Focus Distance modal operator (focus_distance_modal.py).

A modal operator can't receive real mouse/key events in background mode, so
these call the operator's own modal() with simulated events on a real
camera, the way Blender would while it runs.

Run individually with::

    blender --background --factory-startup --python tests/test_focus_distance_modal.py
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
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

addon_utils.enable(_ADDON_NAME, default_set=True)

import simple_camera_manager as _addon  # noqa: E402

focus = _addon.focus_distance_modal
dolly = _addon.dolly_zoom_modal
_OP = focus.CAM_MANAGER_OT_focus_distance


class _FakeOperator:
    """Carries the operator's real methods without needing Blender to
    instantiate the Operator (which only happens through bpy.ops)."""


for _name in ('modal', '_init_state', '_set_mode', '_capture_reference', '_finish', '_redraw',
              '_cycle_guide', '_focus_under_mouse', '_release_focus_object', '_restore'):
    setattr(_FakeOperator, _name, _OP.__dict__[_name])


def _event(type, value='NOTHING', mouse_x=500, alt=False, shift=False, ctrl=False):
    return SimpleNamespace(type=type, value=value, mouse_x=mouse_x, mouse_y=300,
                           mouse_region_x=200, mouse_region_y=150,
                           alt=alt, shift=shift, ctrl=ctrl)


class TestSharpRange(unittest.TestCase):
    """Depth of field limits, checked against the standard thin-lens formulas."""

    def test_known_values(self):
        # 50 mm at f/8 focused at 5 m with a 0.03 mm circle of confusion:
        # hyperfocal 10.467 m, sharp from 3.389 m to 9.527 m.
        near, far = focus.sharp_range(5.0, 50.0, 8.0, 0.03)
        self.assertAlmostEqual(near, 3.389, places=3)
        self.assertAlmostEqual(far, 9.527, places=3)

    def test_wider_aperture_gives_a_shallower_range(self):
        near_wide, far_wide = focus.sharp_range(5.0, 50.0, 1.8, 0.03)
        near, far = focus.sharp_range(5.0, 50.0, 8.0, 0.03)
        self.assertGreater(near_wide, near)
        self.assertLess(far_wide, far)
        self.assertLess(near_wide, 5.0)
        self.assertGreater(far_wide, 5.0)

    def test_far_limit_is_infinite_at_and_beyond_the_hyperfocal_distance(self):
        _near, far = focus.sharp_range(20.0, 50.0, 8.0, 0.03)
        self.assertEqual(far, math.inf)

    def test_scene_unit_scale(self):
        # One scene unit = 1 cm: 500 units is 5 m, the limits scale the same way.
        near, far = focus.sharp_range(500.0, 50.0, 8.0, 0.03, unit_scale=0.01)
        self.assertAlmostEqual(near, 338.9, places=1)
        self.assertAlmostEqual(far, 952.7, places=1)

    def test_circle_of_confusion_from_the_sensor_diagonal(self):
        cam = bpy.data.cameras.new('CocTestCam')
        self.addCleanup(bpy.data.cameras.remove, cam)
        scene = bpy.context.scene
        old = (scene.render.resolution_x, scene.render.resolution_y)
        self.addCleanup(lambda: setattr(scene.render, 'resolution_x', old[0]) or
                        setattr(scene.render, 'resolution_y', old[1]))
        scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
        cam.sensor_fit = 'HORIZONTAL'
        cam.sensor_width = 36.0
        expected = math.hypot(36.0, 36.0 * 1080 / 1920) / 1500
        self.assertAlmostEqual(focus.circle_of_confusion_mm(cam, scene), expected, places=6)


class TestFocusDistanceModal(unittest.TestCase):

    def setUp(self):
        self.camera_data = bpy.data.cameras.new('FocusTestCam')
        self.camera_obj = bpy.data.objects.new('FocusTestCam', self.camera_data)
        bpy.context.scene.collection.objects.link(self.camera_obj)
        # At y=-10 looking along +Y.
        self.camera_obj.location = (0.0, -10.0, 1.0)
        self.camera_obj.rotation_euler = (math.radians(90), 0.0, 0.0)
        dof = self.camera_data.dof
        dof.use_dof = False
        dof.focus_distance = 10.0
        dof.aperture_fstop = 2.8
        bpy.context.view_layer.update()

        focus._guide_settings.update(plane_display='PLANE', show_sharp_range=True)
        self.context = SimpleNamespace(area=mock.MagicMock(), screen=SimpleNamespace(areas=[]))
        self.op = _FakeOperator()
        self.op.report = mock.MagicMock()
        self.op._init_state(self.camera_obj, _event('NONE'))

    def tearDown(self):
        bpy.data.objects.remove(self.camera_obj, do_unlink=True)
        bpy.data.cameras.remove(self.camera_data)

    def _send(self, *args, **kwargs):
        return self.op.modal(self.context, _event(*args, **kwargs))

    # -- values ------------------------------------------------------------

    def test_starts_idle_and_turns_depth_of_field_on(self):
        self.assertIsNone(self.op.mode)
        self.assertTrue(self.camera_data.dof.use_dof)

    def test_mouse_move_without_key_changes_nothing_and_passes_through(self):
        self.assertEqual(self._send('MOUSEMOVE', mouse_x=800), {'PASS_THROUGH'})
        self.assertEqual(self.camera_data.dof.focus_distance, 10.0)
        self.assertAlmostEqual(self.camera_data.dof.aperture_fstop, 2.8, places=5)

    def test_d_drag_right_moves_focus_further_away(self):
        self._send('D', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=600)
        self.assertGreater(self.camera_data.dof.focus_distance, 10.0)
        self._send('MOUSEMOVE', mouse_x=400)
        self.assertLess(self.camera_data.dof.focus_distance, 10.0)
        self.assertAlmostEqual(self.camera_data.dof.aperture_fstop, 2.8, places=5)

    def test_shift_is_slower_than_normal(self):
        self._send('D', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=600)
        normal = self.camera_data.dof.focus_distance - 10.0
        self._send('LEFT_SHIFT', 'PRESS', mouse_x=600)
        before = self.camera_data.dof.focus_distance
        self._send('MOUSEMOVE', mouse_x=700, shift=True)
        self.assertLess(self.camera_data.dof.focus_distance - before, normal)

    def test_focus_distance_stays_positive(self):
        self._send('D', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=-100000)
        self.assertGreater(self.camera_data.dof.focus_distance, 0.0)

    def test_a_changes_the_f_stop_within_limits(self):
        self._send('A', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=600)
        self.assertGreater(self.camera_data.dof.aperture_fstop, 2.8)
        self._send('MOUSEMOVE', mouse_x=100000)
        self.assertEqual(self.camera_data.dof.aperture_fstop, focus._MAX_FSTOP)
        self._send('MOUSEMOVE', mouse_x=-100000)
        self.assertAlmostEqual(self.camera_data.dof.aperture_fstop, focus._MIN_FSTOP, places=5)
        self.assertEqual(self.camera_data.dof.focus_distance, 10.0)

    def test_same_key_again_turns_the_value_off(self):
        self._send('D', 'RELEASE')
        self._send('D', 'RELEASE')
        self.assertIsNone(self.op.mode)

    def test_d_clears_the_focus_object_and_escape_puts_it_back(self):
        target = bpy.data.objects.new('FocusTestTarget', None)
        bpy.context.scene.collection.objects.link(target)
        self.addCleanup(bpy.data.objects.remove, target, do_unlink=True)
        self.camera_data.dof.focus_object = target
        self.op._init_state(self.camera_obj, _event('NONE'))

        self._send('D', 'RELEASE')
        self.assertIsNone(self.camera_data.dof.focus_object)
        self._send('ESC', 'PRESS')
        self.assertEqual(self.camera_data.dof.focus_object, target)

    def test_escape_restores_everything(self):
        self._send('D', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=700)
        self._send('A', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=900)
        self.assertEqual(self._send('ESC', 'PRESS'), {'CANCELLED'})
        dof = self.camera_data.dof
        self.assertEqual(dof.focus_distance, 10.0)
        self.assertAlmostEqual(dof.aperture_fstop, 2.8, places=5)
        self.assertFalse(dof.use_dof)

    def test_click_and_enter_confirm_and_keep_the_values(self):
        self._send('D', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=700)
        changed = self.camera_data.dof.focus_distance
        self.assertEqual(self._send('LEFTMOUSE', 'PRESS'), {'FINISHED'})
        self.assertEqual(self.camera_data.dof.focus_distance, changed)
        self.assertTrue(self.camera_data.dof.use_dof)
        self.assertEqual(self._send('RET', 'PRESS'), {'FINISHED'})

    def test_navigation_passes_through_and_stops_the_active_value(self):
        self._send('D', 'RELEASE')
        self.assertEqual(self._send('MIDDLEMOUSE', 'PRESS'), {'PASS_THROUGH'})
        self.assertIsNone(self.op.mode)

    def test_alt_ignores_mouse_movement(self):
        self._send('D', 'RELEASE')
        self._send('MOUSEMOVE', mouse_x=900, alt=True)
        self.assertEqual(self.camera_data.dof.focus_distance, 10.0)

    def test_other_hotkeys_are_blocked(self):
        for key in ('G', 'S', 'X'):
            self.assertEqual(self._send(key, 'PRESS'), {'RUNNING_MODAL'})

    # -- focus on the surface under the mouse ------------------------------

    def _wall(self, y):
        """A large plane facing the camera at the given y."""
        mesh = bpy.data.meshes.new('FocusTestWall')
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=50.0)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=__import__('mathutils').Matrix.Rotation(math.radians(90), 3, 'X'))
        bm.to_mesh(mesh)
        bm.free()
        wall = bpy.data.objects.new('FocusTestWall', mesh)
        wall.location = (0.0, y, 0.0)
        bpy.context.scene.collection.objects.link(wall)
        bpy.context.view_layer.update()
        self.addCleanup(bpy.data.meshes.remove, mesh)
        self.addCleanup(bpy.data.objects.remove, wall, do_unlink=True)

    def _press_e(self, origin, direction):
        context = SimpleNamespace(
            area=mock.MagicMock(), screen=SimpleNamespace(areas=[]),
            region=object(), region_data=object(), scene=bpy.context.scene,
            evaluated_depsgraph_get=bpy.context.evaluated_depsgraph_get)
        with mock.patch.object(focus.view3d_utils, 'region_2d_to_origin_3d', return_value=Vector(origin)), \
                mock.patch.object(focus.view3d_utils, 'region_2d_to_vector_3d', return_value=Vector(direction)):
            return self.op.modal(context, _event('E', 'PRESS'))

    def test_e_focuses_on_the_surface_under_the_mouse(self):
        self._wall(y=4.0)
        # Viewed from somewhere else than the camera: the focus distance is
        # still measured from the camera, along its view axis.
        self._press_e((0.0, -20.0, 1.0), (0.0, 1.0, 0.0))
        self.assertAlmostEqual(self.camera_data.dof.focus_distance, 14.0, places=4)

    def test_e_with_nothing_under_the_mouse_changes_nothing(self):
        self._press_e((0.0, -20.0, 1.0), (0.0, 0.0, 1.0))
        self.assertEqual(self.camera_data.dof.focus_distance, 10.0)
        self.op.report.assert_called_once()

    def test_e_ignores_surfaces_behind_the_camera(self):
        self._wall(y=-15.0)
        self._press_e((0.0, -20.0, 1.0), (0.0, 1.0, 0.0))
        self.assertEqual(self.camera_data.dof.focus_distance, 10.0)

    # -- guides ------------------------------------------------------------

    def test_p_cycles_the_plane_display_and_r_toggles_the_sharp_range(self):
        self._send('P', 'RELEASE')
        self.assertEqual(self.op.plane_display, 'LINE')
        self._send('P', 'RELEASE')
        self.assertEqual(self.op.plane_display, 'OFF')
        self._send('P', 'RELEASE')
        self.assertEqual(self.op.plane_display, 'PLANE')
        self._send('R', 'RELEASE')
        self.assertFalse(self.op.show_sharp_range)

    def test_next_run_starts_with_the_last_guide_settings(self):
        self._send('P', 'RELEASE')
        self._send('R', 'RELEASE')
        op = _FakeOperator()
        op._init_state(self.camera_obj, _event('NONE'))
        self.assertEqual(op.plane_display, 'LINE')
        self.assertFalse(op.show_sharp_range)

    def _draw_guides(self):
        fake_bpy = SimpleNamespace(context=SimpleNamespace(
            scene=bpy.context.scene, region_data=mock.MagicMock(), region=mock.MagicMock()))
        self.op.as_pointer = lambda: 1
        with mock.patch.object(focus, 'bpy', fake_bpy), \
                mock.patch.object(focus, 'gpu'), \
                mock.patch.object(focus, '_draw_cut_line') as cut, \
                mock.patch.object(focus, '_draw_quad') as quads, \
                mock.patch.object(focus, '_draw_lines') as lines:
            focus.draw_callback_view(self.op, None)
        return cut, quads, lines

    def _distance(self, point):
        return focus.distance_along_view(self.camera_obj, point)

    def test_plane_is_drawn_at_the_focus_distance(self):
        cut, quads, _lines = self._draw_guides()
        cut.assert_called_once()
        corners, color = quads.call_args.args
        for corner in corners:
            self.assertAlmostEqual(self._distance(corner), 10.0, places=4)
        self.assertEqual(color, focus._COLOR_FOCUS_PLANE)

    def test_sharp_range_frames_are_drawn_at_the_near_and_far_limits(self):
        _cut, _quads, lines = self._draw_guides()
        points = lines.call_args.args[0]
        near, far = focus.camera_sharp_range(self.camera_obj, bpy.context.scene)
        distances = sorted({round(self._distance(p), 3) for p in points})
        self.assertEqual(distances, [round(near, 3), round(far, 3)])

    def test_guides_set_to_off_are_not_drawn(self):
        self._send('P', 'RELEASE')
        self._send('P', 'RELEASE')
        self._send('R', 'RELEASE')
        cut, quads, lines = self._draw_guides()
        cut.assert_not_called()
        quads.assert_not_called()
        lines.assert_not_called()

    def test_orthographic_camera_has_no_sharp_range(self):
        self.camera_data.type = 'ORTHO'
        _cut, _quads, lines = self._draw_guides()
        lines.assert_not_called()

    def test_guides_skip_drawing_after_operator_is_freed(self):
        def freed():
            raise ReferenceError
        self.op.as_pointer = freed
        with mock.patch.object(focus, '_draw_quad') as quads:
            focus.draw_callback_view(self.op, None)
        quads.assert_not_called()

    # -- overlay -----------------------------------------------------------

    def _draw_overlay_text(self):
        fake_bpy = SimpleNamespace(utils=bpy.utils, context=SimpleNamespace(
            scene=bpy.context.scene, area=SimpleNamespace(width=1200), preferences=bpy.context.preferences))
        self.op.as_pointer = lambda: 1
        # The rows are drawn by Dolly Zoom's shared _draw_row(), so its blf is the one to watch.
        with mock.patch.object(focus, 'bpy', fake_bpy), \
                mock.patch.object(focus, '_draw_rect'), \
                mock.patch.object(dolly, 'blf') as fake_blf:
            focus.draw_callback_px(self.op, None)
        return [c.args[1] for c in fake_blf.draw.call_args_list]

    def test_overlay_lists_keys_and_prompts_while_idle(self):
        texts = self._draw_overlay_text()
        for expected in ("Camera Focus", "Focus Distance", "(D)", "F-Stop", "(A)", "Focus on Surface", "(E)",
                         "Focus Plane", "(P)", "Sharp Range", "(R)", "PRESS D OR A TO ADJUST, E TO PICK"):
            self.assertIn(expected, texts)

    def test_overlay_shows_the_focus_object(self):
        target = bpy.data.objects.new('FocusTestTarget', None)
        bpy.context.scene.collection.objects.link(target)
        self.addCleanup(bpy.data.objects.remove, target, do_unlink=True)
        self.camera_data.dof.focus_object = target
        self.assertTrue(any(t.startswith("FocusTestTarget") for t in self._draw_overlay_text()))

    def test_overlay_skips_drawing_after_operator_is_freed(self):
        def freed():
            raise ReferenceError
        self.op.as_pointer = freed
        with mock.patch.object(dolly, 'blf') as fake_blf:
            focus.draw_callback_px(self.op, None)
        fake_blf.draw.assert_not_called()


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
