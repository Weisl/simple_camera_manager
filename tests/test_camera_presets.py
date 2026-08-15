"""
Integration tests for camera_presets.py's save/apply round trip (issue #161:
"Camera presets / saved setups").

AddPresetBase writes real .py files under the user's actual Blender config
directory (bpy.utils.user_resource('SCRIPTS', ...)), not a sandboxed temp
dir, so every test here must remove what it creates.

Run individually with::

    blender --background --factory-startup --python tests/test_camera_presets.py
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

import simple_camera_manager as _addon  # noqa: E402

_PRESET_NAME = "Simple Camera Manager Test Preset"
_PRESET_SUBDIR = "simple_camera_manager/camera"


class TestCameraPresetRoundTrip(unittest.TestCase):
    def setUp(self):
        self.camera_data = bpy.data.cameras.new('PresetTestCam')
        self.camera_obj = bpy.data.objects.new('PresetTestCam', self.camera_data)
        bpy.context.scene.collection.objects.link(self.camera_obj)
        self._orig_scene_camera = bpy.context.scene.camera
        bpy.context.scene.camera = self.camera_obj

        self.world_a = bpy.data.worlds.new('PresetTestWorldA')
        self.world_b = bpy.data.worlds.new('PresetTestWorldB')

        cam = self.camera_data
        cam.type = 'PERSP'
        cam.lens = 85.0
        cam.clip_start = 0.5
        cam.clip_end = 500.0
        cam.exposure = 1.5
        cam.dof.use_dof = True
        cam.dof.focus_distance = 3.0
        cam.show_rotation_gizmo = True
        cam.world = self.world_a

        self._preset_filepath = None

    def tearDown(self):
        if self._preset_filepath and os.path.exists(self._preset_filepath):
            os.remove(self._preset_filepath)
            # execfile()-ing the preset leaves a compiled __pycache__ entry
            # next to it in the same real config directory - remove that too
            # so the test suite leaves no trace there.
            preset_dir = os.path.dirname(self._preset_filepath)
            pycache_dir = os.path.join(preset_dir, "__pycache__")
            if os.path.isdir(pycache_dir):
                stem = os.path.splitext(os.path.basename(self._preset_filepath))[0]
                for fn in os.listdir(pycache_dir):
                    if fn.startswith(stem + "."):
                        os.remove(os.path.join(pycache_dir, fn))
                if not os.listdir(pycache_dir):
                    os.rmdir(pycache_dir)

        bpy.context.scene.camera = self._orig_scene_camera
        bpy.data.objects.remove(self.camera_obj, do_unlink=True)
        bpy.data.cameras.remove(self.camera_data)
        for world in (self.world_a, self.world_b):
            try:
                if world.users == 0:
                    bpy.data.worlds.remove(world)
            except ReferenceError:
                pass  # already removed by the test itself

    def _save_preset(self):
        result = bpy.ops.cam_manager.camera_preset_add(name=_PRESET_NAME)
        self.assertEqual(result, {'FINISHED'})

        filename = _addon.camera_presets.CAM_MANAGER_OT_camera_preset_add.as_filename(_PRESET_NAME)
        self._preset_filepath = bpy.utils.preset_find(filename, _PRESET_SUBDIR, ext=".py")
        self.assertIsNotNone(self._preset_filepath, "preset file was not written to disk")

    def test_save_then_apply_restores_values(self):
        self._save_preset()

        cam = self.camera_data
        cam.lens = 24.0
        cam.clip_start = 0.01
        cam.clip_end = 10.0
        cam.exposure = 0.0
        cam.dof.use_dof = False
        cam.dof.focus_distance = 1.0
        cam.show_rotation_gizmo = False
        cam.world = self.world_b

        result = bpy.ops.script.execute_preset(
            filepath=self._preset_filepath, menu_idname="CAM_MANAGER_MT_camera_presets")
        self.assertEqual(result, {'FINISHED'})

        self.assertEqual(cam.lens, 85.0)
        self.assertEqual(cam.clip_start, 0.5)
        self.assertEqual(cam.clip_end, 500.0)
        self.assertEqual(cam.exposure, 1.5)
        self.assertTrue(cam.dof.use_dof)
        self.assertEqual(cam.dof.focus_distance, 3.0)
        self.assertTrue(cam.show_rotation_gizmo)
        self.assertEqual(cam.world, self.world_a)

    def test_apply_still_applies_earlier_fields_when_world_is_missing(self):
        self._save_preset()

        # Simulate applying this preset in a file that never had this World -
        # cam.world is captured by name and re-resolved via bpy.data.worlds[...]
        # on apply, so removing it here reproduces that case.
        bpy.data.worlds.remove(self.world_a)

        cam = self.camera_data
        cam.lens = 24.0
        cam.exposure = 0.0

        # ExecutePreset.execute() itself completes and reports an ERROR
        # rather than returning CANCELLED - but calling it via bpy.ops still
        # raises RuntimeError to the caller once any ERROR-level report was
        # made, *after* execute() (and every field before "cam.world" in
        # preset_values) has already run.
        with self.assertRaises(RuntimeError):
            bpy.ops.script.execute_preset(
                filepath=self._preset_filepath, menu_idname="CAM_MANAGER_MT_camera_presets")

        self.assertEqual(cam.lens, 85.0)
        self.assertEqual(cam.exposure, 1.5)


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
