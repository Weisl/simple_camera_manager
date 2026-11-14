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


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
