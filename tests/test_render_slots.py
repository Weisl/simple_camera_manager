"""
Tests for "Render to New Slot" (issue #64): every render must land in a
new Render Result slot, picked before the render starts, instead of
overwriting an earlier one.

Uses real, tiny Cycles renders. Python can't read a slot's pixels, so
whether a slot holds a render is checked by saving it (save_render fails
for an empty slot).

Run individually with::

    blender --background --factory-startup --python tests/test_render_slots.py
"""

import os
import sys
import tempfile
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

controls = _addon.camera_controlls


def _slots():
    return bpy.data.images['Render Result'].render_slots


def _filled_slots():
    image = bpy.data.images['Render Result']
    slots = image.render_slots
    original = slots.active_index
    filled = []
    with tempfile.TemporaryDirectory() as tmp:
        for index in range(len(slots)):
            slots.active_index = index
            try:
                image.save_render(os.path.join(tmp, f"slot_{index}.png"))
            except RuntimeError:
                continue
            filled.append(index)
    slots.active_index = original
    return filled


class TestRenderToNewSlot(unittest.TestCase):
    """"Render to New Slot" (issue #64): the slot is picked *before* each
    render, so the render you just made is the one shown and earlier
    renders are kept."""

    @classmethod
    def setUpClass(cls):
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 1
        scene.cycles.device = 'CPU'
        scene.render.resolution_x = scene.render.resolution_y = 16
        scene.render.resolution_percentage = 100
        scene.output_render = False
        cls.camera = scene.camera

    def setUp(self):
        render_result = bpy.data.images.get('Render Result')
        if render_result:
            bpy.data.images.remove(render_result)
        controls.set_auto_cycle_render_slot(True)

    def tearDown(self):
        controls.set_auto_cycle_render_slot(False)

    def _render_f12(self, times=1):
        """What F12 runs while the option is on."""
        for _ in range(times):
            self.assertEqual(bpy.ops.cam_manager.render_to_new_slot(), {'FINISHED'})

    def _render_camera_with_addon(self, times=1):
        """What the camera list's Render button does before starting the render."""
        for _ in range(times):
            bpy.ops.cam_manager.change_scene_camera(camera_name=self.camera.name, switch_to_cam=False)
            bpy.ops.render.render()

    def test_each_render_goes_to_a_new_slot_and_stays_visible(self):
        for expected_slot in range(4):
            self._render_f12()
            self.assertEqual(_slots().active_index, expected_slot,
                             "the slot shown after rendering must be the one with the new render")
        self.assertEqual(_filled_slots(), [0, 1, 2, 3])

    def test_rendering_the_same_camera_from_the_addon_never_overwrites(self):
        self.camera.data.slot = 1
        for expected_slot in range(4):
            self._render_camera_with_addon()
            self.assertEqual(_slots().active_index, expected_slot)
        self.assertEqual(_filled_slots(), [0, 1, 2, 3])

    def test_mixed_f12_and_addon_renders_never_overwrite(self):
        self._render_f12()
        self._render_camera_with_addon(2)
        self._render_f12()
        self.assertEqual(_filled_slots(), [0, 1, 2, 3])
        self.assertEqual(_slots().active_index, 3)

    def test_new_slot_is_added_when_all_are_used(self):
        self._render_f12()
        slot_count = len(_slots())
        self._render_f12(slot_count)  # one more render than there are slots
        self.assertEqual(len(_slots()), slot_count + 1)
        self.assertEqual(_slots().active_index, slot_count)
        self.assertEqual(_filled_slots(), list(range(slot_count + 1)))

    def test_viewing_an_old_slot_then_rendering_keeps_it(self):
        self._render_f12(3)  # slots 0, 1, 2
        _slots().active_index = 0  # look at the first render again
        self._render_f12()
        self.assertEqual(_slots().active_index, 3)
        self.assertEqual(_filled_slots(), [0, 1, 2, 3])

    def test_blender_render_menu_is_not_redirected_but_is_remembered(self):
        """Render > Render Image calls Blender's operator directly, so it
        renders into the active slot; the next F12 still avoids that slot."""
        self._render_f12(2)  # slots 0, 1; slot 1 shown
        bpy.ops.render.render()  # overwrites slot 1
        self._render_f12()
        self.assertEqual(_slots().active_index, 2)
        self.assertEqual(_filled_slots(), [0, 1, 2])

    def test_disabled_keeps_blenders_default(self):
        controls.set_auto_cycle_render_slot(False)
        self.assertFalse(controls.is_auto_cycle_render_slot_enabled())
        self._render_camera_with_addon(3)
        self.assertEqual(_filled_slots(), [0])
        self.assertEqual(_slots().active_index, 0)

    def test_loading_a_file_forgets_used_slots(self):
        self._render_f12(2)
        controls._forget_rendered_slots()
        self.assertEqual(controls._rendered_slots, set())


if __name__ == "__main__":
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
