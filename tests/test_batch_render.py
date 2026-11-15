"""
Tests for Batch Render (issue #159): render every camera marked for
rendering in turn, and stop the whole batch when a render is cancelled.

Background mode doesn't run timers or render jobs, so the render start
and the timer are replaced: renders are recorded instead of started, and
deferred work runs immediately. The render handlers are then called the
way Blender calls them when a render ends.

Run individually with::

    blender --background --factory-startup --python tests/test_batch_render.py
"""

import os
import sys
import unittest
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

batch = _addon.batch_render

_OUTPUT_PATH = "//renders/"


def _make_camera(name, render_selected=True):
    cam_data = bpy.data.cameras.new(name)
    cam_data.render_selected = render_selected
    obj = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _batch_handlers_installed():
    return (batch._on_render_complete in bpy.app.handlers.render_complete
            or batch._on_render_cancel in bpy.app.handlers.render_cancel)


class TestBatchRender(unittest.TestCase):

    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj)
        scene = bpy.context.scene
        scene.render.filepath = _OUTPUT_PATH
        scene.output_use_cam_name = False

        self.original = _make_camera("Original", render_selected=False)
        scene.camera = self.original
        self.cam_a = _make_camera("Cam_A")
        self.cam_b = _make_camera("Cam_B")
        self.cam_c = _make_camera("Cam_C")

        self.rendered = []
        patches = [
            mock.patch.object(batch, "_start_render",
                              side_effect=lambda: self.rendered.append(bpy.context.scene.camera.name)),
            mock.patch.object(batch, "_defer", side_effect=lambda func, delay=0: func()),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(batch._forget_batch_on_load)

    def _complete_render(self):
        """What Blender does when a render job finishes."""
        for func in list(bpy.app.handlers.render_complete):
            func(bpy.context.scene, None)

    def _cancel_render(self):
        """What Blender does when you press Esc during a render."""
        for func in list(bpy.app.handlers.render_cancel):
            func(bpy.context.scene, None)

    def _start_batch(self):
        return bpy.ops.cam_manager.multi_camera_rendering_handlers()

    def test_renders_every_selected_camera_then_restores(self):
        self.assertEqual(self._start_batch(), {'FINISHED'})
        self.assertTrue(batch.is_batch_rendering())
        self._complete_render()
        self._complete_render()
        self._complete_render()

        self.assertEqual(self.rendered, ["Cam_A", "Cam_B", "Cam_C"])
        self.assertFalse(batch.is_batch_rendering())
        self.assertFalse(_batch_handlers_installed())
        self.assertEqual(bpy.context.scene.camera, self.original)
        self.assertEqual(bpy.context.scene.render.filepath, _OUTPUT_PATH)

    def test_cancel_stops_the_batch_and_restores(self):
        self._start_batch()
        self._complete_render()  # Cam_A done, Cam_B starts
        self._cancel_render()    # Esc during Cam_B

        self.assertEqual(self.rendered, ["Cam_A", "Cam_B"])
        self.assertFalse(batch.is_batch_rendering())
        self.assertFalse(_batch_handlers_installed())
        self.assertEqual(bpy.context.scene.camera, self.original)
        self.assertEqual(bpy.context.scene.render.filepath, _OUTPUT_PATH)

    def test_normal_render_after_cancel_does_not_resume_the_batch(self):
        """Before #159, the batch kept listening after Esc, so the next F12
        render continued it with the next camera."""
        self._start_batch()
        self._cancel_render()
        self._complete_render()  # an ordinary F12 render later on

        self.assertEqual(self.rendered, ["Cam_A"])
        self.assertEqual(bpy.context.scene.camera, self.original)

    def test_only_one_batch_at_a_time(self):
        self._start_batch()
        self.assertEqual(self._start_batch(), {'CANCELLED'})
        self.assertEqual(self.rendered, ["Cam_A"])

    def test_no_selected_cameras(self):
        for cam in (self.cam_a, self.cam_b, self.cam_c):
            cam.data.render_selected = False
        with self.assertRaisesRegex(RuntimeError, "No cameras selected"):
            self._start_batch()
        self.assertEqual(self.rendered, [])
        self.assertFalse(_batch_handlers_installed())

    def test_camera_deleted_during_batch_is_skipped(self):
        self._start_batch()
        bpy.data.objects.remove(self.cam_b)
        self._complete_render()
        self._complete_render()

        self.assertEqual(self.rendered, ["Cam_A", "Cam_C"])
        self.assertFalse(batch.is_batch_rendering())

    def test_use_camera_name_output_path_restored(self):
        bpy.context.scene.output_use_cam_name = True
        self._start_batch()
        self._complete_render()
        self._complete_render()
        self._complete_render()
        self.assertEqual(bpy.context.scene.render.filepath, _OUTPUT_PATH)

    def test_failed_render_start_ends_the_batch(self):
        batch._start_render.side_effect = RuntimeError("no render engine")
        self._start_batch()
        self.assertFalse(batch.is_batch_rendering())
        self.assertFalse(_batch_handlers_installed())
        self.assertEqual(bpy.context.scene.camera, self.original)

    def test_disabling_the_addon_removes_the_handlers(self):
        self._start_batch()
        batch.unregister()
        try:
            self.assertFalse(_batch_handlers_installed())
            self.assertNotIn(batch._forget_batch_on_load, bpy.app.handlers.load_post)
        finally:
            batch.register()


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
