"""
Unit tests for the Alt+C camera pie (CAMERA_MT_pie_menu), the camera popover
(CAM_MANAGER_PT_camera_popover) and their helper menus.

Loads the real pie_menu.py module (real bpy.types subclasses, no bpy
stubbing) inside headless Blender. bpy_struct subclasses can't be freely
instantiated outside Blender's own UI draw callback
(`bpy_struct.__new__(type): expected a single argument`), so draw() is
called as an unbound function against a small duck-typed harness object
that only stands in for `self.layout` - a normal testing technique, not a
bpy mock. Where a draw function reads camera data, a real camera is used.

Run with headless Blender::

    blender --background --factory-startup --python tests/test_pie_menu.py
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_SOURCE = os.path.dirname(_ADDON_ROOT)
_ADDON_NAME = os.path.basename(_ADDON_ROOT)

if _ADDON_SOURCE not in sys.path:
    sys.path.insert(0, _ADDON_SOURCE)

import addon_utils  # noqa: E402
import bpy  # noqa: E402
import simple_camera_manager.pie_menu as pie_menu  # noqa: E402

addon_utils.enable(_ADDON_NAME, default_set=True)


class _Harness:
    """Duck-typed stand-in for a Menu/Panel instance: only `self.layout`."""

    def __init__(self, layout):
        self.layout = layout


class _PieHarness(_Harness):
    draw = pie_menu.CAMERA_MT_pie_menu.draw
    draw_quick_settings = staticmethod(pie_menu.CAMERA_MT_pie_menu.draw_quick_settings)


class _PopoverHarness(_Harness):
    draw = pie_menu.CAM_MANAGER_PT_camera_popover.draw


class _MenuHarness(_Harness):
    pass


def _context(view_perspective='PERSP', cam_obj=None, space_type='VIEW_3D'):
    space = MagicMock()
    space.type = space_type
    space.region_3d.view_perspective = view_perspective
    context = MagicMock()
    context.space_data = space
    context.scene.camera = cam_obj
    return context


def _draw_pie(context):
    layout = MagicMock()
    pie = layout.menu_pie.return_value
    _PieHarness(layout).draw(context)
    return pie


class _RealCameraCase(unittest.TestCase):
    """Provides a real camera object linked to the scene."""

    def setUp(self):
        self.camera_data = bpy.data.cameras.new('PieTestCam')
        self.camera_obj = bpy.data.objects.new('PieTestCam', self.camera_data)
        bpy.context.scene.collection.objects.link(self.camera_obj)

    def tearDown(self):
        bpy.data.objects.remove(self.camera_obj, do_unlink=True)
        bpy.data.cameras.remove(self.camera_data)


class TestPieSlots(_RealCameraCase):
    """Pie items are added in Blender's fixed slot order:
    W, E, S, N, NW, NE, SW, SE."""

    def _operator_idnames(self, view_perspective):
        pie = _draw_pie(_context(view_perspective, self.camera_obj))
        return [c.args[0] for c in pie.operator.call_args_list], pie

    def test_slot_order_outside_camera_view(self):
        idnames, _pie = self._operator_idnames('PERSP')
        self.assertEqual(idnames, [
            "cam_manager.cycle_cameras_backward",   # W
            "cam_manager.cycle_cameras_next",       # E
            "view3d.view_camera",                   # S
            "camera.create_camera_from_view",       # SW
            "wm.call_panel",                        # SE: Camera Settings…
        ])

    def test_slot_order_inside_camera_view(self):
        idnames, _pie = self._operator_idnames('CAMERA')
        self.assertEqual(idnames[3], "camera.align_camera_to_view")
        self.assertNotIn("camera.create_camera_from_view", idnames)

    def test_previous_and_next_labels_match_their_operators(self):
        pie = _draw_pie(_context('PERSP', self.camera_obj))
        texts = {c.args[0]: c.kwargs.get("text") for c in pie.operator.call_args_list}
        self.assertEqual(texts["cam_manager.cycle_cameras_backward"], "Previous Camera")
        self.assertEqual(texts["cam_manager.cycle_cameras_next"], "Next Camera")

    def test_view_camera_label_follows_view_mode(self):
        for perspective, label in (('PERSP', "View Camera"), ('CAMERA', "Exit Camera View")):
            pie = _draw_pie(_context(perspective, self.camera_obj))
            call = next(c for c in pie.operator.call_args_list if c.args[0] == "view3d.view_camera")
            self.assertEqual(call.kwargs.get("text"), label)

    def test_north_west_and_east_are_empty(self):
        pie = _draw_pie(_context('PERSP', self.camera_obj))
        self.assertEqual(pie.separator.call_count, 2)

    def test_north_is_a_single_box(self):
        pie = _draw_pie(_context('PERSP', self.camera_obj))
        self.assertEqual(pie.box.call_count, 1)


class TestPieQuickSettings(_RealCameraCase):
    def _box(self, cam_obj, view_perspective='PERSP'):
        return _draw_pie(_context(view_perspective, cam_obj)).box.return_value

    def test_camera_settings_in_south_east_opens_popover_that_stays_open(self):
        pie = _draw_pie(_context('PERSP', self.camera_obj))
        call = pie.operator.call_args_list[-1]
        self.assertEqual(call.args[0], "wm.call_panel")
        self.assertEqual(call.kwargs.get("text"), "Camera Settings…")
        op = pie.operator.return_value
        self.assertEqual(op.name, pie_menu.CAM_MANAGER_PT_camera_popover.bl_idname)
        self.assertTrue(op.keep_open)

    def test_viewport_tools_sit_in_the_north_box(self):
        box = self._box(self.camera_obj)
        tools = [c.args[0] for c in box.column.return_value.operator.call_args_list]
        self.assertEqual(tools, ["cam_manager.modal_camera_dolly_zoom", "cam_manager.modal_focus_distance"])

    def test_menus_open_as_popovers_so_they_show_a_dropdown_arrow(self):
        # A plain layout.menu() gets no dropdown arrow inside a pie.
        box = self._box(self.camera_obj)
        col = box.column.return_value
        self.assertFalse(col.menu.called)
        self.assertEqual([c.args[0] for c in col.popover.call_args_list],
                         [pie_menu.CAM_MANAGER_PT_lens_presets.bl_idname,
                          pie_menu.CAM_MANAGER_PT_composition_guides.bl_idname])

    def test_focal_length_menu_shows_current_value(self):
        self.camera_data.lens = 35.0
        box = self._box(self.camera_obj)
        col = box.column.return_value
        texts = [c.kwargs.get("text") for c in col.operator_menu_enum.call_args_list]
        self.assertIn("Focal Length  35 mm", texts)

    def test_orthographic_camera_has_no_focal_length_menu(self):
        self.camera_data.type = 'ORTHO'
        box = self._box(self.camera_obj)
        col = box.column.return_value
        ops = [c.args[0] for c in col.operator_menu_enum.call_args_list]
        self.assertNotIn("cam_manager.apply_focal_length_preset", ops)

    def test_resolution_label(self):
        box = self._box(self.camera_obj)
        texts = [c.kwargs.get("text") for c in box.column.return_value.operator_menu_enum.call_args_list]
        self.assertIn("Resolution  (scene)", texts)

        self.camera_data.resolution_overwrite = True
        self.camera_data.resolution = (1280, 720)
        box = self._box(self.camera_obj)
        texts = [c.kwargs.get("text") for c in box.column.return_value.operator_menu_enum.call_args_list]
        self.assertIn("Resolution  1280 × 720", texts)

    def test_no_scene_camera_shows_error_and_no_settings(self):
        box = self._box(None)
        self.assertTrue(any(c.kwargs.get("text") == "Please specify a scene camera"
                            for c in box.label.call_args_list))
        self.assertFalse(box.operator.called)
        # The action slots still work without a camera (e.g. New Camera from View).
        pie = _draw_pie(_context('PERSP', None))
        self.assertIn("camera.create_camera_from_view", [c.args[0] for c in pie.operator.call_args_list])

    def test_outside_3d_viewport_draws_without_view_toggles(self):
        pie = _draw_pie(_context('PERSP', self.camera_obj, space_type='PROPERTIES'))
        grid = pie.box.return_value.grid_flow.return_value
        props = [c.args[1] for c in grid.prop.call_args_list]
        self.assertNotIn("lock_camera", props)
        self.assertNotIn("show_overlays", props)

    def test_toggles_start_with_overlays(self):
        pie = _draw_pie(_context('PERSP', self.camera_obj))
        grid = pie.box.return_value.grid_flow.return_value
        props = [c.args[1] for c in grid.prop.call_args_list]
        self.assertEqual(props, ["show_overlays", "show_passepartout", "lock_camera"])


class TestCameraPopover(_RealCameraCase):
    def _draw(self, cam_obj, view_perspective='PERSP'):
        layout = MagicMock()
        layout.panel.return_value = (MagicMock(), MagicMock())
        calls = []
        with patch.object(pie_menu, "draw_camera_settings",
                          lambda context, body, cam, **kw: calls.append(("camera", kw))), \
             patch.object(pie_menu, "draw_background_image_settings",
                          lambda context, body, cam: calls.append("background")), \
             patch.object(pie_menu, "draw_display_settings", lambda context, body, cam: calls.append("display")), \
             patch.object(pie_menu, "draw_render_settings", lambda context, body, cam: calls.append("render")):
            _PopoverHarness(layout).draw(_context(view_perspective, cam_obj))
        return layout, calls

    def test_sections_in_order_with_render_collapsed(self):
        layout, calls = self._draw(self.camera_obj)
        # Background images get their own section, so the Camera section leaves them out.
        self.assertEqual(calls, [("camera", {"use_subpanel": True, "include_background_images": False}),
                                 "background", "display", "render"])
        closed = {c.args[0]: c.kwargs.get("default_closed") for c in layout.panel.call_args_list}
        self.assertEqual(closed, {
            "CAM_MANAGER_POPOVER_CAMERA": False,
            "CAM_MANAGER_POPOVER_BACKGROUND": False,
            "CAM_MANAGER_POPOVER_DISPLAY": False,
            "CAM_MANAGER_POPOVER_RENDER": True,
        })

    def test_camera_picker_goes_through_set_active_camera_menu(self):
        layout, _calls = self._draw(self.camera_obj)
        row = layout.row.return_value
        call = row.menu.call_args
        self.assertEqual(call.args[0], pie_menu.CAM_MANAGER_MT_scene_cameras.bl_idname)
        self.assertEqual(call.kwargs.get("text"), self.camera_obj.name)

    def test_view_actions_follow_view_mode(self):
        for perspective, view_label, sync_op in (
                ('PERSP', "View Camera", "camera.create_camera_from_view"),
                ('CAMERA', "Exit Camera View", "camera.align_camera_to_view")):
            layout, _calls = self._draw(self.camera_obj, perspective)
            row = layout.column.return_value.row.return_value
            ops = {c.args[0]: c.kwargs.get("text") for c in row.operator.call_args_list}
            self.assertEqual(ops["view3d.view_camera"], view_label)
            self.assertIn(sync_op, ops)
            tools = [c.args[0] for c in layout.column.return_value.operator.call_args_list]
            self.assertEqual(tools, ["cam_manager.modal_camera_dolly_zoom", "cam_manager.modal_focus_distance"])

    def test_no_scene_camera_shows_error_and_no_sections(self):
        layout, calls = self._draw(None)
        self.assertEqual(calls, [])
        self.assertFalse(layout.panel.called)
        self.assertTrue(any(c.kwargs.get("text") == "Please specify a scene camera"
                            for c in layout.label.call_args_list))


class TestBackgroundImages(_RealCameraCase):
    def _add_background(self, name="SCM_bg_test"):
        image = bpy.data.images.new(name, 64, 32)
        self.addCleanup(bpy.data.images.remove, image)
        bg = self.camera_data.background_images.new()
        bg.image = image
        return bg

    def test_each_image_gets_its_controls(self):
        self._add_background("SCM_bg_a")
        self._add_background("SCM_bg_b")
        layout = MagicMock()
        pie_menu.draw_background_image_settings(_context('CAMERA', self.camera_obj), layout, self.camera_obj)
        col = layout.box.return_value.column.return_value
        toggles = [c.kwargs.get("text") for c in col.prop.call_args_list if c.args[1] == "show_background_image"]
        self.assertEqual(toggles, ["SCM_bg_a", "SCM_bg_b"])
        sub = col.column.return_value
        self.assertEqual([c.args[1] for c in sub.prop.call_args_list], ["alpha"] * 2)
        self.assertEqual([c.args[1] for c in sub.row.return_value.prop.call_args_list],
                         ["display_depth", "frame_method"] * 2)
        # Resolution from Background uses the first image, so it is drawn once.
        res_calls = [c for c in layout.operator.call_args_list
                     if c.args[0] == "cam_manager.camera_resolutio_from_image"]
        self.assertEqual(len(res_calls), 1)

    def test_no_images_shows_info(self):
        layout = MagicMock()
        pie_menu.draw_background_image_settings(_context('CAMERA', self.camera_obj), layout, self.camera_obj)
        labels = [c.kwargs.get("text") for c in layout.column.return_value.row.return_value.label.call_args_list]
        self.assertIn("Camera has no Background Images", labels)
        self.assertFalse(layout.box.called)

    def test_pie_has_an_opacity_slider_per_image(self):
        self._add_background("SCM_bg_a")
        self._add_background("SCM_bg_b")
        col = _draw_pie(_context('CAMERA', self.camera_obj)).box.return_value.column.return_value
        sliders = [c for c in col.row.return_value.prop.call_args_list if c.args[1] == "alpha"]
        self.assertEqual([c.kwargs.get("text") for c in sliders], ["SCM_bg_a", "SCM_bg_b"])
        self.assertTrue(all(c.kwargs.get("slider") for c in sliders))
        # Back / Front sits on a row of its own under each slider.
        depth = [c for c in col.row.return_value.prop.call_args_list if c.args[1] == "display_depth"]
        self.assertEqual(len(depth), 2)
        self.assertTrue(all(c.kwargs.get("expand") for c in depth))

    def test_pie_toggle_only_when_camera_has_images(self):
        def toggled():
            col = _draw_pie(_context('CAMERA', self.camera_obj)).box.return_value.column.return_value
            return any(c.args[1] == "show_background_images" for c in col.prop.call_args_list)

        self.assertFalse(toggled())
        self._add_background()
        self.assertTrue(toggled())

    def test_camera_settings_can_leave_background_images_out(self):
        for include, expected in ((True, True), (False, False)):
            layout = MagicMock()
            layout.panel.return_value = (MagicMock(), MagicMock())
            pie_menu.draw_camera_settings(_context('CAMERA', self.camera_obj), layout, self.camera_obj,
                                          use_subpanel=True, include_background_images=include)
            ids = [c.kwargs.get("idname") for c in layout.panel.call_args_list]
            self.assertEqual("BACKGROUND_IMG" in ids, expected)


class TestViewportTools(unittest.TestCase):
    def test_tools_are_stacked_in_taller_buttons(self):
        layout = MagicMock()
        pie_menu.draw_viewport_tools(layout)
        col = layout.column.return_value
        self.assertEqual([c.args[0] for c in col.operator.call_args_list],
                         ["cam_manager.modal_camera_dolly_zoom", "cam_manager.modal_focus_distance"])
        self.assertFalse(col.row.called)  # one below the other, not side by side
        self.assertGreater(col.scale_y, 1.0)


class TestPiePopovers(_RealCameraCase):
    """The pie opens its menus as popovers. Each one must point at a menu
    that is really registered, and draw without errors."""

    def test_lens_presets_popover_shows_the_registered_preset_menu(self):
        layout = MagicMock()
        _Harness.draw = pie_menu.CAM_MANAGER_PT_lens_presets.draw
        _Harness(layout).draw(bpy.context)
        menu_id = layout.menu_contents.call_args.args[0]
        self.assertTrue(hasattr(bpy.types, menu_id), f"{menu_id} is not a registered menu")

    def test_composition_guides_popover_draws_every_guide(self):
        layout = MagicMock()
        bpy.context.scene.camera = self.camera_obj
        _Harness.draw = pie_menu.CAM_MANAGER_PT_composition_guides.draw
        _Harness(layout).draw(bpy.context)
        drawn = [c.args[1] for c in layout.column.return_value.prop.call_args_list]
        self.assertEqual(drawn, [prop for prop, _text in pie_menu.COMPOSITION_GUIDES])

    def test_menus_used_by_the_pie_and_popover_are_registered(self):
        for menu_id in ("CAM_MANAGER_MT_camera_presets", "CAM_MANAGER_MT_sensor_presets",
                        pie_menu.CAM_MANAGER_MT_scene_cameras.bl_idname):
            self.assertTrue(hasattr(bpy.types, menu_id), menu_id)


class TestSceneCamerasMenu(unittest.TestCase):
    def setUp(self):
        self.objects = []
        for name in ("SCM_Test_b", "SCM_Test_A", "SCM_Test_c"):
            obj = bpy.data.objects.new(name, bpy.data.cameras.new(name))
            bpy.context.scene.collection.objects.link(obj)
            self.objects.append(obj)
        # Newly linked objects only show up in view_layer.objects after an update.
        bpy.context.view_layer.update()

    def tearDown(self):
        for obj in self.objects:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.cameras.remove(data)

    def test_lists_cameras_alphabetically_via_set_active_camera(self):
        layout = MagicMock()
        _MenuHarness.draw = pie_menu.CAM_MANAGER_MT_scene_cameras.draw
        _MenuHarness(layout).draw(bpy.context)
        calls = [c for c in layout.operator.call_args_list if c.kwargs.get("text", "").startswith("SCM_Test_")]
        self.assertTrue(all(c.args[0] == "cam_manager.change_scene_camera" for c in calls))
        self.assertEqual([c.kwargs["text"] for c in calls], ["SCM_Test_A", "SCM_Test_b", "SCM_Test_c"])


class TestDisplaySettings(_RealCameraCase):
    def test_every_composition_guide_is_drawn(self):
        layout = MagicMock()
        pie_menu.draw_display_settings(_context('CAMERA', self.camera_obj), layout, self.camera_obj)
        grid = layout.grid_flow.return_value
        drawn = [c.args[1] for c in grid.prop.call_args_list]
        self.assertEqual(drawn, [prop for prop, _text in pie_menu.COMPOSITION_GUIDES])
        # Every listed guide is a real camera property.
        for prop, _text in pie_menu.COMPOSITION_GUIDES:
            self.assertTrue(hasattr(self.camera_data, prop), prop)


class TestHeaderButton(unittest.TestCase):
    def test_header_button_is_registered(self):
        self.assertIn(pie_menu.draw_view3d_header_button,
                      getattr(bpy.types.VIEW3D_HT_header.draw, "_draw_funcs", []))

    def test_header_button_follows_preference(self):
        prefs = bpy.context.preferences.addons[_ADDON_NAME].preferences
        harness = _Harness(MagicMock())
        try:
            prefs.show_header_button = False
            pie_menu.draw_view3d_header_button(harness, bpy.context)
            self.assertFalse(harness.layout.popover.called)

            prefs.show_header_button = True
            pie_menu.draw_view3d_header_button(harness, bpy.context)
            self.assertEqual(harness.layout.popover.call_args.args[0],
                             pie_menu.CAM_MANAGER_PT_camera_popover.bl_idname)
        finally:
            prefs.show_header_button = True


class TestApplyBuiltinCameraPreset(unittest.TestCase):
    """Real-Blender tests (not the mock harness above) - applying a preset
    sets real properties on a real camera, which a MagicMock can't verify."""

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

    def test_every_builtin_preset_applies_without_error(self):
        for name in pie_menu.BUILTIN_CAMERA_PRESETS:
            result = bpy.ops.cam_manager.apply_builtin_camera_preset(preset=name)
            self.assertEqual(result, {'FINISHED'}, f"preset {name!r} failed to apply")

    def test_full_frame_50mm_sets_expected_values(self):
        bpy.ops.cam_manager.apply_builtin_camera_preset(preset='Full Frame 50mm Standard')
        cam = self.camera_data
        self.assertEqual(cam.type, 'PERSP')
        self.assertEqual(cam.lens, 50.0)
        self.assertEqual(cam.sensor_width, 36.0)
        self.assertEqual(cam.sensor_height, 24.0)
        self.assertEqual(cam.sensor_fit, 'HORIZONTAL')

    def test_preset_leaves_clipping_and_focus_alone(self):
        cam = self.camera_data
        cam.clip_start = 0.02
        cam.clip_end = 50.0
        cam.dof.use_dof = True
        cam.dof.aperture_fstop = 4.0
        bpy.ops.cam_manager.apply_builtin_camera_preset(preset='Full Frame 85mm Portrait')
        self.assertAlmostEqual(cam.clip_start, 0.02, places=5)
        self.assertEqual(cam.clip_end, 50.0)
        self.assertTrue(cam.dof.use_dof)
        self.assertAlmostEqual(cam.dof.aperture_fstop, 4.0, places=5)

    def test_studio_orthographic_switches_camera_type(self):
        bpy.ops.cam_manager.apply_builtin_camera_preset(preset='Studio Orthographic')
        cam = self.camera_data
        self.assertEqual(cam.type, 'ORTHO')
        self.assertEqual(cam.ortho_scale, 5.0)

    def test_no_scene_camera_reports_warning_not_crash(self):
        bpy.context.scene.camera = None
        result = bpy.ops.cam_manager.apply_builtin_camera_preset(preset='Full Frame 50mm Standard')
        self.assertEqual(result, {'CANCELLED'})


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
