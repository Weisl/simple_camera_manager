"""
Tests for the camera lists (issue #160): both lists get their filter and
sort options from one shared mixin, and filtering/sorting works the same
in both.

Run individually with::

    blender --background --factory-startup --python tests/test_uilist.py
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

uilist = _addon.uilist

_LISTS = (uilist.CAMERA_UL_cameras_popup, uilist.CAMERA_UL_cameras_scene)
_SHARED_PROPS = ('use_filter_name_reverse', 'use_filter_visible_only',
                 'use_filter_render_selected', 'sort_type')


class _FakeList:
    """Stands in for a drawn list: filter_list() only reads these values."""
    bitflag_filter_item = 1 << 30
    CAMERA_FILTER = uilist.CameraListFilterMixin.CAMERA_FILTER

    def __init__(self, **values):
        self.filter_name = ''
        self.use_filter_name_reverse = False
        self.use_filter_visible_only = False
        self.use_filter_render_selected = False
        self.sort_type = 'NAME'
        for key, value in values.items():
            setattr(self, key, value)


def _make_camera(name, lens=50.0, render_selected=False):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.render_selected = render_selected
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _shown_names(fake):
    """Names the list shows, in display order."""
    objects = bpy.context.scene.objects
    flags, order = uilist.filter_list(fake, bpy.context)
    shown = [i for i, flag in enumerate(flags) if flag]
    return [objects[i].name for i in sorted(shown, key=lambda i: order[i])]


class TestCameraLists(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj)
        _make_camera("Bravo", lens=85.0, render_selected=True)
        _make_camera("alpha", lens=35.0)
        _make_camera("Charlie", lens=24.0, render_selected=True)
        bpy.data.objects.new("Empty", None)
        bpy.context.scene.collection.objects.link(bpy.data.objects["Empty"])

    def test_both_lists_use_the_mixin(self):
        for cls in _LISTS:
            with self.subTest(cls=cls.__name__):
                self.assertTrue(issubclass(cls, uilist.CameraListFilterMixin))
                self.assertTrue(cls.is_registered)

    def test_both_lists_register_the_shared_properties(self):
        for cls in _LISTS:
            for prop in _SHARED_PROPS:
                with self.subTest(cls=cls.__name__, prop=prop):
                    self.assertIn(prop, cls.bl_rna.properties)

    def test_only_cameras_are_shown_sorted_by_name(self):
        self.assertEqual(_shown_names(_FakeList()), ["alpha", "Bravo", "Charlie"])

    def test_sort_by_focal_length(self):
        self.assertEqual(_shown_names(_FakeList(sort_type='FOCAL_LENGTH')),
                         ["Charlie", "alpha", "Bravo"])

    def test_render_selected_filter(self):
        self.assertEqual(_shown_names(_FakeList(use_filter_render_selected=True)),
                         ["Bravo", "Charlie"])

    def test_name_filter_and_invert(self):
        self.assertEqual(_shown_names(_FakeList(filter_name='a')),
                         ["alpha", "Bravo", "Charlie"])
        self.assertEqual(_shown_names(_FakeList(filter_name='br')), ["Bravo"])
        self.assertEqual(_shown_names(_FakeList(filter_name='br', use_filter_name_reverse=True)),
                         ["alpha", "Charlie"])


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
