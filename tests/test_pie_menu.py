"""
Unit tests for the view-mode-aware behaviour of CAMERA_MT_pie_menu (issue #92).

Unlike test_addon_registration.py (which mocks pie_menu as an opaque module),
these tests load pie_menu.py directly so CAMERA_MT_pie_menu.draw() actually runs,
using a minimal bpy stub whose bpy.types.Menu/Operator are real subclassable
classes rather than MagicMock instances.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ADDON_DIR = Path(__file__).parent.parent
PIE_MENU_PATH = ADDON_DIR / "pie_menu.py"


class _DummyMenu:
    pass


class _DummyOperator:
    pass


def _load_pie_menu_module():
    """Load pie_menu.py fresh with a minimal, subclassable bpy stub injected."""
    bpy_stub = MagicMock()
    bpy_types = types.ModuleType("bpy.types")
    bpy_types.Menu = _DummyMenu
    bpy_types.Operator = _DummyOperator
    bpy_stub.types = bpy_types
    bpy_stub.props = MagicMock()

    sys.modules["bpy"] = bpy_stub
    sys.modules["bpy.types"] = bpy_types

    spec = importlib.util.spec_from_file_location("pie_menu", PIE_MENU_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["pie_menu"] = module
    spec.loader.exec_module(module)
    return module, bpy_stub


def _cleanup_sys_modules():
    for key in ("bpy", "bpy.types", "pie_menu"):
        sys.modules.pop(key, None)


def _build_menu(module, bpy_stub, view_perspective, cam_obj):
    """Instantiate CAMERA_MT_pie_menu with a mocked layout/context ready for draw()."""
    mock_pie = MagicMock()
    mock_layout = MagicMock()
    mock_layout.menu_pie.return_value = mock_pie

    mock_region_3d = MagicMock()
    mock_region_3d.view_perspective = view_perspective

    mock_space = MagicMock()
    mock_space.region_3d = mock_region_3d
    bpy_stub.context.space_data = mock_space

    mock_scene = MagicMock()
    mock_scene.camera = cam_obj
    mock_context = MagicMock()
    mock_context.scene = mock_scene

    menu = module.CAMERA_MT_pie_menu()
    menu.layout = mock_layout
    return menu, mock_context, mock_pie


class TestPieMenuNorthWest(unittest.TestCase):
    """North-West slot: view3d.view_camera toggle, label depends on view mode."""

    def setUp(self):
        _cleanup_sys_modules()
        self.module, self.bpy_stub = _load_pie_menu_module()

    def tearDown(self):
        _cleanup_sys_modules()

    def _nw_calls(self, view_perspective):
        menu, context, pie = _build_menu(self.module, self.bpy_stub, view_perspective, cam_obj=None)
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

    def setUp(self):
        _cleanup_sys_modules()
        self.module, self.bpy_stub = _load_pie_menu_module()

    def tearDown(self):
        _cleanup_sys_modules()

    def _ne_idnames(self, view_perspective):
        menu, context, pie = _build_menu(self.module, self.bpy_stub, view_perspective, cam_obj=None)
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

    def setUp(self):
        _cleanup_sys_modules()
        self.module, self.bpy_stub = _load_pie_menu_module()

    def tearDown(self):
        _cleanup_sys_modules()

    def _column_order(self, view_perspective):
        cam_obj = MagicMock()
        menu, context, pie = _build_menu(self.module, self.bpy_stub, view_perspective, cam_obj=cam_obj)

        order = []
        with patch.object(self.module.CAMERA_MT_pie_menu, "draw_left_column",
                           lambda self, context, col, cam_obj: order.append("left")), \
             patch.object(self.module.CAMERA_MT_pie_menu, "draw_center_column",
                           lambda self, context, col, cam_obj: order.append("center")), \
             patch.object(self.module.CAMERA_MT_pie_menu, "draw_right_column",
                           lambda self, context, col, cam_obj: order.append("right")):
            menu.draw(context)

        return order

    def test_order_outside_camera_view(self):
        self.assertEqual(self._column_order('PERSP'), ["left", "center", "right"])

    def test_order_inside_camera_view(self):
        self.assertEqual(self._column_order('CAMERA'), ["right", "center", "left"])


class TestPieMenuNoSceneCamera(unittest.TestCase):
    """With no active scene camera, the North box shows an error label while NW/NE stay mode-aware."""

    def setUp(self):
        _cleanup_sys_modules()
        self.module, self.bpy_stub = _load_pie_menu_module()

    def tearDown(self):
        _cleanup_sys_modules()

    def test_no_camera_not_in_camera_view(self):
        menu, context, pie = _build_menu(self.module, self.bpy_stub, 'PERSP', cam_obj=None)
        menu.draw(context)
        idnames = [c.args[0] for c in pie.operator.call_args_list]
        self.assertIn("camera.create_camera_from_view", idnames)

    def test_no_camera_in_camera_view(self):
        menu, context, pie = _build_menu(self.module, self.bpy_stub, 'CAMERA', cam_obj=None)
        menu.draw(context)
        idnames = [c.args[0] for c in pie.operator.call_args_list]
        self.assertIn("camera.align_camera_to_view", idnames)


if __name__ == "__main__":
    unittest.main()
