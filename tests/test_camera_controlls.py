"""
Unit tests for camera_controlls.py's view-snapping operators (issue: "camera
from view throws an error when in camera view").

Runs the real operators against a real headless Blender, because the bug
only reproduces through bpy.ops's actual poll/execute dispatch - a mocked
context can't reproduce a poll() failure raised by Blender's own C code.

Run individually with::

    blender --background --factory-startup --python tests/test_camera_controlls.py
"""

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

addon_utils.enable(_ADDON_NAME, default_set=True)


def _find_view3d_area(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            return area
    return None


class TestCameraToViewFromCameraView(unittest.TestCase):
    """camera.create_camera_from_view / camera.align_camera_to_view must
    work while the viewport is already looking through a camera.

    Both operators used to call bpy.ops.view3d.camera_to_view() directly,
    whose poll() rejects the call whenever region_3d.view_perspective is
    already 'CAMERA' ("context is incorrect") - so entering camera view and
    then trying to snap/create a camera from that same view always failed.
    """

    def setUp(self):
        self.area = _find_view3d_area(bpy.context)
        self.assertIsNotNone(self.area, "no VIEW_3D area in the test .blend's default screen")
        self.region = next(r for r in self.area.regions if r.type == 'WINDOW')
        self.space = self.area.spaces.active

        self._orig_perspective = self.space.region_3d.view_perspective
        self._orig_scene_camera = bpy.context.scene.camera
        self._orig_objects = set(bpy.data.objects.keys())

        self.space.region_3d.view_perspective = 'CAMERA'

    def tearDown(self):
        for obj in list(bpy.data.objects):
            if obj.name not in self._orig_objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        self.space.region_3d.view_perspective = self._orig_perspective
        bpy.context.scene.camera = self._orig_scene_camera

    def _override(self):
        return bpy.context.temp_override(area=self.area, region=self.region, scene=bpy.context.scene)

    def test_create_camera_from_view_while_in_camera_view(self):
        with self._override():
            result = bpy.ops.camera.create_camera_from_view()
        self.assertEqual(result, {'FINISHED'})
        self.assertEqual(self.space.region_3d.view_perspective, 'CAMERA')

    def test_align_camera_to_view_while_in_camera_view(self):
        camera_data = bpy.data.cameras.new('TestCam')
        camera_obj = bpy.data.objects.new('TestCam', camera_data)
        bpy.context.scene.collection.objects.link(camera_obj)
        bpy.context.scene.camera = camera_obj

        with self._override():
            result = bpy.ops.camera.align_camera_to_view()
        self.assertEqual(result, {'FINISHED'})
        self.assertEqual(self.space.region_3d.view_perspective, 'CAMERA')

    def test_create_camera_from_view_still_works_outside_camera_view(self):
        self.space.region_3d.view_perspective = 'PERSP'
        with self._override():
            result = bpy.ops.camera.create_camera_from_view()
        self.assertEqual(result, {'FINISHED'})
        # view3d.camera_to_view() itself switches the viewport into camera
        # view as a side effect (true both before and after this fix) -
        # this case only guards that the fix's PERSP/CAMERA toggle didn't
        # break the normal, already-working call path.
        self.assertEqual(self.space.region_3d.view_perspective, 'CAMERA')


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
