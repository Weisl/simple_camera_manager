"""
Unit tests for the view-mode-aware behaviour of CAMERA_MT_pie_menu (issue #92).

Loads the real pie_menu.py module (a real bpy.types.Menu subclass, no bpy
stubbing) inside headless Blender. bpy_struct subclasses can't be freely
instantiated outside Blender's own UI draw callback
(`bpy_struct.__new__(type): expected a single argument`), so draw() is
called as an unbound function against a small duck-typed harness object
that only stands in for `self.layout` and the menu's own column-drawing
methods - a normal testing technique, not a bpy mock.
"""

import contextlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_SOURCE = os.path.dirname(_ADDON_ROOT)

if _ADDON_SOURCE not in sys.path:
    sys.path.insert(0, _ADDON_SOURCE)

import simple_camera_manager.pie_menu as pie_menu  # noqa: E402

_CAMERA_MT_pie_menu = pie_menu.CAMERA_MT_pie_menu


class _MenuHarness:
    """Duck-typed stand-in for a CAMERA_MT_pie_menu instance."""

    def __init__(self, layout):
        self.layout = layout


for _name in ("draw", "draw_left_column", "draw_center_column", "draw_right_column"):
    setattr(_MenuHarness, _name, getattr(_CAMERA_MT_pie_menu, _name))


@contextlib.contextmanager
def _build_menu(view_perspective, cam_obj):
    """Build a harness + mocked layout/context ready for draw().

    bpy.context.space_data is a genuine read-only RNA property (unlike a
    MagicMock, real bpy.context can't just have attributes assigned onto
    it), so bpy.context itself is swapped out for the duration of the
    `with` block instead.
    """
    mock_pie = MagicMock()
    mock_layout = MagicMock()
    mock_layout.menu_pie.return_value = mock_pie

    mock_region_3d = MagicMock()
    mock_region_3d.view_perspective = view_perspective

    mock_space = MagicMock()
    mock_space.region_3d = mock_region_3d

    mock_bpy_context = MagicMock()
    mock_bpy_context.space_data = mock_space

    mock_scene = MagicMock()
    mock_scene.camera = cam_obj
    mock_context = MagicMock()
    mock_context.scene = mock_scene

    menu = _MenuHarness(mock_layout)
    with patch.object(pie_menu.bpy, "context", mock_bpy_context):
        yield menu, mock_context, mock_pie


class TestPieMenuNorthWest(unittest.TestCase):
    """North-West slot: view3d.view_camera toggle, label depends on view mode."""

    def _nw_calls(self, view_perspective):
        with _build_menu(view_perspective, cam_obj=None) as (menu, context, pie):
            menu.draw(context)
            return [c for c in pie.operator.call_args_list if c.args[0] == "view3d.view_camera"]

    def test_shows_view_camera_when_not_in_camera_view(self):
        calls = self._nw_calls('PERSP')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].kwargs.get("text"), "View Camera")

    def test_shows_exit_camera_view_when_in_camera_view(self):
        calls = self._nw_calls('CAMERA')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].kwargs.get("text"), "Exit Camera View")


class TestPieMenuNorthEast(unittest.TestCase):
    """North-East slot: create-camera-from-view outside camera view, align-to-view inside it."""

    def _ne_idnames(self, view_perspective):
        with _build_menu(view_perspective, cam_obj=None) as (menu, context, pie):
            menu.draw(context)
            return [c.args[0] for c in pie.operator.call_args_list]

    def test_shows_create_camera_from_view_when_not_in_camera_view(self):
        idnames = self._ne_idnames('PERSP')
        self.assertIn("camera.create_camera_from_view", idnames)
        self.assertNotIn("camera.align_camera_to_view", idnames)

    def test_shows_align_camera_to_view_when_in_camera_view(self):
        idnames = self._ne_idnames('CAMERA')
        self.assertIn("camera.align_camera_to_view", idnames)
        self.assertNotIn("camera.create_camera_from_view", idnames)


class TestPieMenuNorthColumnOrder(unittest.TestCase):
    """North box column order swaps depending on view mode."""

    def _column_order(self, view_perspective):
        cam_obj = MagicMock()
        order = []
        with _build_menu(view_perspective, cam_obj=cam_obj) as (menu, context, pie), \
             patch.object(_MenuHarness, "draw_left_column",
                          lambda self, context, col, cam_obj: order.append("left")), \
             patch.object(_MenuHarness, "draw_center_column",
                          lambda self, context, col, cam_obj: order.append("center")), \
             patch.object(_MenuHarness, "draw_right_column",
                          lambda self, context, col, cam_obj: order.append("right")):
            menu.draw(context)

        return order

    def test_order_outside_camera_view(self):
        self.assertEqual(self._column_order('PERSP'), ["left", "center", "right"])

    def test_order_inside_camera_view(self):
        self.assertEqual(self._column_order('CAMERA'), ["right", "center", "left"])


class TestPieMenuNoSceneCamera(unittest.TestCase):
    """With no active scene camera, the North box shows an error label while NW/NE stay mode-aware."""

    def test_no_camera_not_in_camera_view(self):
        with _build_menu('PERSP', cam_obj=None) as (menu, context, pie):
            menu.draw(context)
            idnames = [c.args[0] for c in pie.operator.call_args_list]
        self.assertIn("camera.create_camera_from_view", idnames)

    def test_no_camera_in_camera_view(self):
        with _build_menu('CAMERA', cam_obj=None) as (menu, context, pie):
            menu.draw(context)
            idnames = [c.args[0] for c in pie.operator.call_args_list]
        self.assertIn("camera.align_camera_to_view", idnames)


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
