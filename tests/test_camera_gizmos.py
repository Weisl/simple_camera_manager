"""
Tests for the camera roll gizmo's placement (camera_gizmos.py).

Gizmos aren't drawn in background mode, so instead of rendering, these
project the roll ring into the camera's own view and check that it is
visible there: inside the camera frame, in front of clip_start and
behind clip_end. The ring used to be auto-scaled by view distance, which
collapses it to nothing when viewing through the camera.

Run individually with::

    blender --background --factory-startup --python tests/test_camera_gizmos.py
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
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402

addon_utils.enable(_ADDON_NAME, default_set=True)

import simple_camera_manager as _addon  # noqa: E402

gizmos = _addon.camera_gizmos


class TestRollRingVisibleInCameraView(unittest.TestCase):

    def setUp(self):
        self.scene = bpy.context.scene
        self._orig_res = (self.scene.render.resolution_x, self.scene.render.resolution_y)
        self.camera_data = bpy.data.cameras.new('RollGizmoTestCam')
        self.camera_obj = bpy.data.objects.new('RollGizmoTestCam', self.camera_data)
        self.scene.collection.objects.link(self.camera_obj)
        self.camera_obj.location = (3.0, -4.0, 2.0)
        self.camera_obj.rotation_euler = (math.radians(70), 0.0, math.radians(35))
        bpy.context.view_layer.update()

    def tearDown(self):
        self.scene.render.resolution_x, self.scene.render.resolution_y = self._orig_res
        bpy.data.objects.remove(self.camera_obj, do_unlink=True)
        bpy.data.cameras.remove(self.camera_data)

    def _ring_in_camera_view(self):
        """Ring points as (x, y, depth): x/y are 0..1 across the camera frame."""
        offset = gizmos._roll_ring_offset_matrix(self.camera_obj, self.scene)
        world = self.camera_obj.matrix_world.normalized() @ offset
        return [world_to_camera_view(self.scene, self.camera_obj, world @ mathutils_vec(v))
                for v in gizmos._roll_ring_verts]

    def _assert_visible(self, label):
        cam = self.camera_data
        points = self._ring_in_camera_view()
        for p in points:
            self.assertTrue(0.0 < p.x < 1.0 and 0.0 < p.y < 1.0,
                            f"{label}: ring point {tuple(p)} is outside the camera frame")
            self.assertGreater(p.z, cam.clip_start, f"{label}: ring is in front of clip_start")
            self.assertLess(p.z, cam.clip_end, f"{label}: ring is behind clip_end")
        span = max(max(p.x for p in points) - min(p.x for p in points),
                   max(p.y for p in points) - min(p.y for p in points))
        self.assertGreater(span, 0.4, f"{label}: ring is too small to see or grab ({span:.3f})")

    def test_default_perspective_camera(self):
        self._assert_visible("default")

    def test_long_and_short_lenses(self):
        for lens in (9.0, 24.0, 135.0, 400.0):
            self.camera_data.lens = lens
            self._assert_visible(f"{lens}mm")

    def test_large_clip_start(self):
        self.camera_data.clip_start = 5.0
        self.camera_data.clip_end = 500.0
        self._assert_visible("clip_start 5")

    def test_portrait_resolution_and_lens_shift(self):
        self.scene.render.resolution_x, self.scene.render.resolution_y = 1080, 1920
        self.camera_data.shift_x = 0.2
        self.camera_data.shift_y = -0.1
        self._assert_visible("portrait + shift")

    def test_orthographic_camera(self):
        self.camera_data.type = 'ORTHO'
        for scale in (0.5, 5.0, 50.0):
            self.camera_data.ortho_scale = scale
            self._assert_visible(f"ortho {scale}")


def mathutils_vec(v):
    import mathutils
    return mathutils.Vector(v)


class TestGizmoDragsAreUndoable(unittest.TestCase):
    """Blender only adds undo steps for gizmos that run an operator. These
    gizmos write to the camera directly, so a confirmed drag must push its
    own undo step, except while Dolly Zoom runs (one step for the session)."""

    def setUp(self):
        self.camera_data = bpy.data.cameras.new('UndoGizmoTestCam')
        self.camera_obj = bpy.data.objects.new('UndoGizmoTestCam', self.camera_data)
        bpy.context.scene.collection.objects.link(self.camera_obj)
        self.camera_obj.rotation_euler = (math.radians(80), 0.0, math.radians(20))
        self.context = SimpleNamespace(area=mock.MagicMock())
        self.undo_push = mock.MagicMock()
        fake_bpy = SimpleNamespace(ops=SimpleNamespace(ed=SimpleNamespace(undo_push=self.undo_push)))
        patcher = mock.patch.object(gizmos, 'bpy', fake_bpy)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        bpy.data.objects.remove(self.camera_obj, do_unlink=True)
        bpy.data.cameras.remove(self.camera_data)

    def _roll_drag(self, cancel, roll=math.radians(15)):
        init_quat = self.camera_obj.rotation_euler.to_quaternion()
        gizmo = SimpleNamespace(group=SimpleNamespace(cam=self.camera_obj), init_quat=init_quat)
        gizmos._apply_camera_roll_delta(self.camera_obj, init_quat, roll)
        gizmos.CameraRollWidget.exit(gizmo, self.context, cancel)
        return init_quat

    def test_confirmed_roll_pushes_undo_step(self):
        self._roll_drag(cancel=False)
        self.undo_push.assert_called_once_with(message="Camera Roll")

    def test_cancelled_roll_restores_without_undo_step(self):
        init_quat = self._roll_drag(cancel=True)
        self.undo_push.assert_not_called()
        self.assertAlmostEqual(
            self.camera_obj.rotation_euler.to_quaternion().rotation_difference(init_quat).angle, 0.0, places=5)

    def test_click_without_roll_pushes_no_undo_step(self):
        self._roll_drag(cancel=False, roll=0.0)
        self.undo_push.assert_not_called()

    def test_no_undo_step_while_dolly_zoom_runs(self):
        dolly = _addon.dolly_zoom_modal
        dolly._running.add('test')
        try:
            self._roll_drag(cancel=False)
        finally:
            dolly._running.discard('test')
        self.undo_push.assert_not_called()

    def _distance_drag(self, cancel, new_value):
        values = {'offset': 10.0}
        gizmo = SimpleNamespace(
            init_value=10.0,
            target_get_value=lambda name: (values[name],),
            target_set_value=lambda name, value: values.__setitem__(name, value[0]),
        )
        values['offset'] = new_value
        gizmos.MyCustomShapeWidget.exit(gizmo, self.context, cancel)
        return values['offset']

    def test_confirmed_target_distance_drag_pushes_undo_step(self):
        self._distance_drag(cancel=False, new_value=12.0)
        self.undo_push.assert_called_once_with(message="Dolly Zoom Target Distance")

    def test_cancelled_target_distance_drag_restores_value(self):
        self.assertEqual(self._distance_drag(cancel=True, new_value=12.0), 10.0)
        self.undo_push.assert_not_called()


class TestRollSnapping(unittest.TestCase):
    """Ctrl snaps the roll to 5° steps, matching the "Snap: Ctrl" hint
    Blender shows in the status bar while dragging a gizmo."""

    def setUp(self):
        self.camera_data = bpy.data.cameras.new('RollSnapTestCam')
        self.camera_obj = bpy.data.objects.new('RollSnapTestCam', self.camera_data)
        bpy.context.scene.collection.objects.link(self.camera_obj)
        self.camera_obj.rotation_euler = (math.radians(90), 0.0, 0.0)
        bpy.context.view_layer.update()

    def tearDown(self):
        bpy.data.objects.remove(self.camera_obj, do_unlink=True)
        bpy.data.cameras.remove(self.camera_data)

    def _drag_to_degrees(self, degrees, ctrl=False, shift=False):
        """Drag the mouse around the ring's center from 0° to `degrees`."""
        gizmo = SimpleNamespace(
            group=SimpleNamespace(cam=self.camera_obj),
            init_quat=self.camera_obj.rotation_euler.to_quaternion(),
            init_value=gizmos._get_camera_roll(self.camera_obj),
            pivot_2d=(0.0, 0.0), init_angle=0.0, sign=1.0,
        )
        angle = math.radians(degrees)
        event = SimpleNamespace(mouse_region_x=100 * math.cos(angle), mouse_region_y=100 * math.sin(angle),
                                ctrl=ctrl, shift=shift)
        gizmos.CameraRollWidget.modal(gizmo, SimpleNamespace(area=mock.MagicMock()), event, set())
        bpy.context.view_layer.update()
        return math.degrees(gizmos._get_camera_roll(self.camera_obj) - gizmo.init_value)

    def test_ctrl_snaps_to_5_degrees(self):
        self.assertAlmostEqual(abs(self._drag_to_degrees(12.0, ctrl=True)), 10.0, places=3)

    def test_shift_does_not_snap(self):
        self.assertAlmostEqual(abs(self._drag_to_degrees(12.0, shift=True)), 12.0, places=3)

    def test_no_modifier_follows_the_mouse(self):
        self.assertAlmostEqual(abs(self._drag_to_degrees(12.0)), 12.0, places=3)


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
