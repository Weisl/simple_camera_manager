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


for _name in ("draw", "draw_render_column", "draw_camera_column", "draw_display_column"):
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


def _header_operator_calls(pie):
    """Operator calls made on the North column's header row.

    col = pie.column() is a Mock attribute access, so every call returns
    the same `.return_value` object - col.row.return_value is therefore
    the header row regardless of how many times draw() calls .row() on it.
    """
    return pie.column.return_value.row.return_value.operator.call_args_list


class TestPieMenuNorthBoxHeader(unittest.TestCase):
    """View-camera / align-camera actions live in the North column's header.

    They used to be their own North West / North East pie slots, but those
    slots directly border the big North column and were stealing its
    clicks, so they moved into the header instead (see North West/East
    tests below for the now-empty slots)."""

    def _header_calls(self, view_perspective):
        with _build_menu(view_perspective, cam_obj=None) as (menu, context, pie):
            menu.draw(context)
            return _header_operator_calls(pie)

    def test_shows_view_camera_when_not_in_camera_view(self):
        calls = self._header_calls('PERSP')
        idnames = [c.args[0] for c in calls]
        self.assertIn("view3d.view_camera", idnames)
        self.assertIn("camera.create_camera_from_view", idnames)
        self.assertNotIn("camera.align_camera_to_view", idnames)
        view_call = next(c for c in calls if c.args[0] == "view3d.view_camera")
        self.assertEqual(view_call.kwargs.get("text"), "View Camera")

    def test_shows_exit_camera_view_when_in_camera_view(self):
        calls = self._header_calls('CAMERA')
        idnames = [c.args[0] for c in calls]
        self.assertIn("view3d.view_camera", idnames)
        self.assertIn("camera.align_camera_to_view", idnames)
        self.assertNotIn("camera.create_camera_from_view", idnames)
        view_call = next(c for c in calls if c.args[0] == "view3d.view_camera")
        self.assertEqual(view_call.kwargs.get("text"), "Exit Camera View")


class TestPieMenuNorthWestEastEmpty(unittest.TestCase):
    """North West/East pie slots are blank (pie.separator()) so they no
    longer border the North box with a competing clickable item."""

    def test_north_west_and_east_have_no_operators(self):
        with _build_menu('PERSP', cam_obj=None) as (menu, context, pie):
            menu.draw(context)
            idnames = [c.args[0] for c in pie.operator.call_args_list]

        self.assertNotIn("view3d.view_camera", idnames)
        self.assertNotIn("camera.align_camera_to_view", idnames)
        self.assertNotIn("camera.create_camera_from_view", idnames)

    def test_north_west_and_east_are_separators(self):
        # With no scene camera, South West is also a separator, so the
        # pie draws exactly 3 separators: North West, North East, South West.
        with _build_menu('PERSP', cam_obj=None) as (menu, context, pie):
            menu.draw(context)

        self.assertEqual(pie.separator.call_count, 3)


class TestPieMenuNorthColumnOrder(unittest.TestCase):
    """North box draws all three panels as side-by-side boxes inside a
    single split, in an order that swaps depending on view mode (this is
    purely visual - North West/East being empty is what keeps the whole
    box reliably clickable, see TestPieMenuNorthWestEastEmpty)."""

    def _column_order(self, view_perspective):
        cam_obj = MagicMock()
        order = []
        with _build_menu(view_perspective, cam_obj=cam_obj) as (menu, context, pie), \
             patch.object(_MenuHarness, "draw_render_column",
                          lambda self, context, col, cam_obj: order.append("render")), \
             patch.object(_MenuHarness, "draw_camera_column",
                          lambda self, context, col, cam_obj: order.append("camera")), \
             patch.object(_MenuHarness, "draw_display_column",
                          lambda self, context, col, cam_obj: order.append("display")):
            menu.draw(context)

        return order

    def test_order_outside_camera_view(self):
        self.assertEqual(self._column_order('PERSP'), ["render", "camera", "display"])

    def test_order_inside_camera_view(self):
        self.assertEqual(self._column_order('CAMERA'), ["display", "camera", "render"])


class TestPieMenuNoSceneCamera(unittest.TestCase):
    """With no active scene camera, the North box shows an error label
    while its header buttons stay mode-aware."""

    def test_no_camera_shows_error_label(self):
        with _build_menu('PERSP', cam_obj=None) as (menu, context, pie):
            menu.draw(context)
            label_calls = pie.column.return_value.label.call_args_list

        self.assertTrue(any(c.kwargs.get("text") == "Please specify a scene camera" for c in label_calls))

    def test_no_camera_header_still_mode_aware(self):
        with _build_menu('CAMERA', cam_obj=None) as (menu, context, pie):
            menu.draw(context)
            idnames = [c.args[0] for c in _header_operator_calls(pie)]
        self.assertIn("camera.align_camera_to_view", idnames)


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
