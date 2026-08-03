"""
Integration tests for simple_camera_manager's register()/unregister() lifecycle.

Loads and enables the addon inside a real headless Blender instance via
addon_utils (the same path Blender itself uses when a user ticks the
checkbox in Preferences), instead of mocking bpy and every submodule. A
mocked bpy can't catch real registration bugs - duplicate bl_idname,
missing RNA properties, or a submodule's register() silently forgetting
to call bpy.utils.register_class() on its own classes tuple.

Checks use `cls.is_registered` on the actual class objects rather than
`hasattr(bpy.types, "ClassName")` - Operators/Gizmos register under an
identifier derived from bl_idname, which can differ from the Python
class name, so a name-string lookup gives false negatives.

Run with headless Blender::

    blender --background --factory-startup --python tests/test_addon_registration.py
"""

import os
import sys
import unittest

import addon_utils
import bpy

_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_SOURCE = os.path.dirname(_ADDON_ROOT)
_ADDON_NAME = os.path.basename(_ADDON_ROOT)

if _ADDON_SOURCE not in sys.path:
    sys.path.insert(0, _ADDON_SOURCE)

import simple_camera_manager as _addon  # noqa: E402

# One representative registrable class per submodule (in __init__.py's
# `files` order), used to confirm enable()/disable() actually reaches
# every submodule. camera_gizmos is intentionally not covered here -
# GizmoGroup classes don't expose `is_registered` and gizmos need a real
# 3D viewport/GPU context that --background mode doesn't provide.
_REPRESENTATIVE_CLASSES = (
    _addon.camera_controlls.OBJECT_OT_create_camera_from_view,
    _addon.ui_helpers.EXPORTER_OT_open_preferences,
    _addon.dolly_zoom_modal.CAM_MANAGER_OT_dolly_zoom,
    _addon.batch_render.CAM_MANAGER_OT_multi_camera_rendering_modal,
    _addon.ui.VIEW3D_PT_SimpleCameraManager,
    _addon.uilist.CAMERA_UL_cameras_popup,
    _addon.pie_menu.CAMERA_MT_pie_menu,
    _addon.keymap.REMOVE_OT_hotkey,
    _addon.preferences.CAM_MANAGER_OT_renaming_preferences,
)


def _registered():
    return {cls for cls in _REPRESENTATIVE_CLASSES if cls.is_registered}


def _is_enabled():
    return _ADDON_NAME in bpy.context.preferences.addons


class TestEnable(unittest.TestCase):
    def tearDown(self):
        if _is_enabled():
            addon_utils.disable(_ADDON_NAME, default_set=True)

    def test_enable_registers_every_submodule(self):
        addon_utils.enable(_ADDON_NAME, default_set=True)
        self.assertTrue(_is_enabled(), "addon_utils did not report the addon as enabled")
        missing = set(_REPRESENTATIVE_CLASSES) - _registered()
        self.assertEqual(
            missing, set(),
            f"enabling the addon did not register: {[c.__name__ for c in missing]}",
        )


class TestDisable(unittest.TestCase):
    def setUp(self):
        addon_utils.enable(_ADDON_NAME, default_set=True)
        # Sanity check the fixture itself actually registered everything,
        # so a pass below can't be a vacuous "nothing was ever registered".
        assert not (set(_REPRESENTATIVE_CLASSES) - _registered())

    def test_disable_removes_every_submodule(self):
        addon_utils.disable(_ADDON_NAME, default_set=True)
        self.assertFalse(_is_enabled())
        still_present = _registered()
        self.assertEqual(
            still_present, set(),
            f"disabling the addon left classes registered: {[c.__name__ for c in still_present]}",
        )


class TestEnableDisableCycle(unittest.TestCase):
    """A real Blender addon-reload cycle (disable -> enable, e.g. toggling the
    Preferences checkbox twice) must work cleanly."""

    def tearDown(self):
        if _is_enabled():
            addon_utils.disable(_ADDON_NAME, default_set=True)

    def test_cycle_is_repeatable(self):
        for _ in range(2):
            addon_utils.enable(_ADDON_NAME, default_set=True)
            self.assertEqual(set(_REPRESENTATIVE_CLASSES) - _registered(), set())
            addon_utils.disable(_ADDON_NAME, default_set=True)
            self.assertEqual(_registered(), set())


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
