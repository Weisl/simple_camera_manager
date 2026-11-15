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
    """A saved lens preset restores camera type, focal length / ortho scale,
    sensor and resolution, and leaves every other camera setting alone."""

    def setUp(self):
        self.camera_data = bpy.data.cameras.new('PresetTestCam')
        self.camera_obj = bpy.data.objects.new('PresetTestCam', self.camera_data)
        bpy.context.scene.collection.objects.link(self.camera_obj)
        self._orig_scene_camera = bpy.context.scene.camera
        bpy.context.scene.camera = self.camera_obj

        cam = self.camera_data
        cam.type = 'PERSP'
        cam.lens = 85.0
        cam.ortho_scale = 7.0
        cam.sensor_fit = 'VERTICAL'
        cam.sensor_width = 44.0
        cam.sensor_height = 33.0
        cam.resolution_overwrite = True
        cam.resolution = (1600, 1200)

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

    def _save_preset(self):
        result = bpy.ops.cam_manager.camera_preset_add(name=_PRESET_NAME)
        self.assertEqual(result, {'FINISHED'})

        filename = _addon.camera_presets.CAM_MANAGER_OT_camera_preset_add.as_filename(_PRESET_NAME)
        self._preset_filepath = bpy.utils.preset_find(filename, _PRESET_SUBDIR, ext=".py")
        self.assertIsNotNone(self._preset_filepath, "preset file was not written to disk")

    def _apply_preset(self):
        result = bpy.ops.script.execute_preset(
            filepath=self._preset_filepath, menu_idname="CAM_MANAGER_MT_camera_presets")
        self.assertEqual(result, {'FINISHED'})

    def test_saves_exactly_the_lens_fields(self):
        self.assertEqual(
            _addon.camera_presets.CAM_MANAGER_OT_camera_preset_add.preset_values,
            [f"cam.{f}" for f in _addon.camera_presets.LENS_PRESET_FIELDS],
        )

    def test_save_then_apply_restores_lens_values(self):
        self._save_preset()

        cam = self.camera_data
        cam.type = 'ORTHO'
        cam.lens = 24.0
        cam.ortho_scale = 2.0
        cam.sensor_fit = 'AUTO'
        cam.sensor_width = 36.0
        cam.sensor_height = 24.0
        cam.resolution_overwrite = False
        cam.resolution = (640, 480)

        self._apply_preset()

        self.assertEqual(cam.type, 'PERSP')
        self.assertEqual(cam.lens, 85.0)
        self.assertEqual(cam.ortho_scale, 7.0)
        self.assertEqual(cam.sensor_fit, 'VERTICAL')
        self.assertEqual(cam.sensor_width, 44.0)
        self.assertEqual(cam.sensor_height, 33.0)
        self.assertTrue(cam.resolution_overwrite)
        self.assertEqual(tuple(cam.resolution), (1600, 1200))
        render = bpy.context.scene.render
        self.assertEqual((render.resolution_x, render.resolution_y), (1600, 1200),
                         "the scene camera's preset resolution must reach the render settings")

    def test_saved_file_contains_only_lens_fields(self):
        self._save_preset()
        with open(self._preset_filepath) as f:
            assigned = {line.split('=')[0].strip()[len('cam.'):]
                        for line in f if line.startswith('cam.')}
        self.assertEqual(assigned, set(_addon.camera_presets.LENS_PRESET_FIELDS))

    def test_apply_leaves_other_settings_alone(self):
        self._save_preset()

        cam = self.camera_data
        cam.clip_start = 0.01
        cam.clip_end = 10.0
        cam.exposure = 1.5
        cam.dof.use_dof = True
        cam.dof.focus_distance = 3.0

        self._apply_preset()

        self.assertAlmostEqual(cam.clip_start, 0.01, places=5)
        self.assertEqual(cam.clip_end, 10.0)
        self.assertEqual(cam.exposure, 1.5)
        self.assertTrue(cam.dof.use_dof)
        self.assertEqual(cam.dof.focus_distance, 3.0)


class TestSensorFormatPresets(unittest.TestCase):
    """The "Sensor Format" dropdown reuses Blender's native camera presets,
    which write to bpy.context.camera - only set in the Properties Editor.
    They must still apply to the scene camera from the N-panel/pie menu."""

    def setUp(self):
        self.camera_data = bpy.data.cameras.new('SensorPresetTestCam')
        self.camera_obj = bpy.data.objects.new('SensorPresetTestCam', self.camera_data)
        bpy.context.scene.collection.objects.link(self.camera_obj)
        self._orig_scene_camera = bpy.context.scene.camera
        bpy.context.scene.camera = self.camera_obj

    def tearDown(self):
        bpy.context.scene.camera = self._orig_scene_camera
        bpy.data.objects.remove(self.camera_obj, do_unlink=True)
        bpy.data.cameras.remove(self.camera_data)

    def _preset_files(self):
        files = []
        for path in bpy.utils.preset_paths(_addon.camera_presets.CAM_MANAGER_MT_sensor_presets.preset_subdir):
            files += [os.path.join(path, f) for f in sorted(os.listdir(path)) if f.endswith('.py')]
        return files

    def test_menu_is_registered(self):
        self.assertTrue(_addon.camera_presets.CAM_MANAGER_MT_sensor_presets.is_registered)

    def test_native_presets_are_found(self):
        self.assertTrue(self._preset_files(), "no native Blender camera presets found")

    def test_every_native_preset_applies_to_scene_camera(self):
        for filepath in self._preset_files():
            self.camera_data.sensor_fit = 'AUTO'
            result = bpy.ops.cam_manager.apply_sensor_preset(filepath=filepath)
            self.assertEqual(result, {'FINISHED'}, f"{os.path.basename(filepath)} failed")
            self.assertNotEqual(self.camera_data.sensor_fit, 'AUTO',
                                f"{os.path.basename(filepath)} did not reach the scene camera")

    def test_aps_c_sets_expected_sensor_size(self):
        aps_c = next(f for f in self._preset_files() if os.path.basename(f) == 'APS-C.py')
        bpy.ops.cam_manager.apply_sensor_preset(filepath=aps_c)
        self.assertAlmostEqual(self.camera_data.sensor_width, 23.6, places=3)
        self.assertAlmostEqual(self.camera_data.sensor_height, 15.6, places=3)

    def test_no_scene_camera_cancels(self):
        bpy.context.scene.camera = None
        result = bpy.ops.cam_manager.apply_sensor_preset(filepath=self._preset_files()[0])
        self.assertEqual(result, {'CANCELLED'})


class TestBuiltinCameraPresets(unittest.TestCase):
    """Built-in presets must fully define the camera type, so switching from
    the orthographic preset to a perspective one turns the camera back to
    perspective."""

    def setUp(self):
        self.camera_data = bpy.data.cameras.new('BuiltinPresetTestCam')
        self.camera_obj = bpy.data.objects.new('BuiltinPresetTestCam', self.camera_data)
        bpy.context.scene.collection.objects.link(self.camera_obj)
        self._orig_scene_camera = bpy.context.scene.camera
        bpy.context.scene.camera = self.camera_obj

    def tearDown(self):
        bpy.context.scene.camera = self._orig_scene_camera
        bpy.data.objects.remove(self.camera_obj, do_unlink=True)
        bpy.data.cameras.remove(self.camera_data)

    def test_every_preset_sets_camera_type(self):
        for name, values in _addon.camera_presets.BUILTIN_CAMERA_PRESETS.items():
            self.assertIn('type', values, f"'{name}' does not set the camera type")

    def test_perspective_preset_after_orthographic_restores_perspective(self):
        for name, values in _addon.camera_presets.BUILTIN_CAMERA_PRESETS.items():
            if values.get('type', 'PERSP') != 'PERSP':
                continue
            bpy.ops.cam_manager.apply_builtin_camera_preset(preset='Studio Orthographic')
            self.assertEqual(self.camera_data.type, 'ORTHO')
            result = bpy.ops.cam_manager.apply_builtin_camera_preset(preset=name)
            self.assertEqual(result, {'FINISHED'}, f"'{name}' failed")
            self.assertEqual(self.camera_data.type, 'PERSP',
                             f"'{name}' left the camera orthographic")

    def test_builtin_presets_only_set_lens_fields(self):
        allowed = set(_addon.camera_presets.LENS_PRESET_FIELDS)
        for name, values in _addon.camera_presets.BUILTIN_CAMERA_PRESETS.items():
            self.assertLessEqual(set(values), allowed, f"'{name}' sets fields outside the Lens box")

    def test_every_preset_sets_the_resolution(self):
        """Built-in presets set the resolution like saved ones, so switching
        presets never keeps the previous preset's resolution."""
        for name, values in _addon.camera_presets.BUILTIN_CAMERA_PRESETS.items():
            self.assertTrue(values.get('resolution_overwrite'), f"'{name}' does not enable Resolution Overwrite")
            self.assertIn('resolution', values, f"'{name}' does not set the resolution")

    def test_builtin_preset_resolution_matches_sensor_aspect(self):
        for name, values in _addon.camera_presets.BUILTIN_CAMERA_PRESETS.items():
            if values['type'] != 'PERSP':
                continue
            width, height = values['resolution']
            self.assertAlmostEqual(width / height, values['sensor_width'] / values['sensor_height'], delta=0.02,
                                   msg=f"'{name}' resolution doesn't match its sensor")

    def test_builtin_preset_sets_scene_render_resolution(self):
        self.camera_data.resolution_overwrite = False
        bpy.ops.cam_manager.apply_builtin_camera_preset(preset='Full Frame 50mm Standard')
        render = bpy.context.scene.render
        self.assertTrue(self.camera_data.resolution_overwrite)
        self.assertEqual((render.resolution_x, render.resolution_y), (1920, 1280))
        bpy.ops.cam_manager.apply_builtin_camera_preset(preset='Studio Orthographic')
        self.assertEqual((render.resolution_x, render.resolution_y), (1920, 1080))


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
