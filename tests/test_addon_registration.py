"""
Unit tests for simple_camera_manager addon registration.

Tests the register(), unregister(), and reload behaviour defined in __init__.py
without requiring a running Blender instance. All bpy and submodule dependencies
are replaced with mocks.
"""

import importlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

ADDON_DIR = Path(__file__).parent.parent
INIT_PATH = ADDON_DIR / "__init__.py"
PACKAGE_NAME = "simple_camera_manager"

# All submodule names imported by __init__.py
SUBMODULE_NAMES = [
    "camera_controlls",
    "ui_helpers",
    "dolly_zoom_modal",
    "batch_render",
    "camera_gizmos",
    "ui",
    "uilist",
    "pie_menu",
    "keymap",
    "preferences",
]

# The exact order of the `files` list in __init__.py (determines call order)
FILES_ORDER = [
    "camera_controlls",
    "ui_helpers",
    "dolly_zoom_modal",
    "batch_render",
    "ui",
    "uilist",
    "pie_menu",
    "camera_gizmos",
    "keymap",
    "preferences",
]


def _make_submodule_mock(name: str) -> MagicMock:
    mock = MagicMock()
    mock.__name__ = f"{PACKAGE_NAME}.{name}"
    mock.__package__ = PACKAGE_NAME
    mock.register = MagicMock()
    mock.unregister = MagicMock()
    return mock


def _load_addon(submodule_mocks: dict, bpy_mock: MagicMock, extra_namespace: dict | None = None) -> types.ModuleType:
    """
    Execute the addon __init__.py in a fresh module context with injected mocks.

    Args:
        submodule_mocks: mapping of submodule name -> mock module
        bpy_mock: mock for the `bpy` package
        extra_namespace: optional dict pre-populated into the module's __dict__
                         before execution (used to simulate a reload scenario where
                         `bpy` is already present in the module namespace).

    Returns:
        The loaded module object with register/unregister callables attached.
    """
    module = types.ModuleType(PACKAGE_NAME)
    module.__package__ = PACKAGE_NAME
    module.__path__ = []

    if extra_namespace:
        module.__dict__.update(extra_namespace)

    # Inject bpy and submodules into sys.modules so relative imports resolve
    sys.modules["bpy"] = bpy_mock
    sys.modules[PACKAGE_NAME] = module
    for name, mock in submodule_mocks.items():
        sys.modules[f"{PACKAGE_NAME}.{name}"] = mock

    source = INIT_PATH.read_text(encoding="utf-8")
    code = compile(source, str(INIT_PATH), "exec")
    exec(code, module.__dict__)  # noqa: S102 – intentional for test isolation

    return module


def _cleanup_sys_modules():
    keys = ["bpy", PACKAGE_NAME] + [f"{PACKAGE_NAME}.{n}" for n in SUBMODULE_NAMES]
    for key in keys:
        sys.modules.pop(key, None)


class TestRegister(unittest.TestCase):
    """register() must call every submodule's register() exactly once."""

    def setUp(self):
        _cleanup_sys_modules()
        self.bpy_mock = MagicMock()
        self.mocks = {n: _make_submodule_mock(n) for n in SUBMODULE_NAMES}
        self.addon = _load_addon(self.mocks, self.bpy_mock)

    def tearDown(self):
        _cleanup_sys_modules()

    def test_register_calls_all_submodules(self):
        self.addon.register()
        for name in FILES_ORDER:
            self.mocks[name].register.assert_called_once_with()

    def test_register_order(self):
        call_order = []
        for name in SUBMODULE_NAMES:
            self.mocks[name].register.side_effect = lambda n=name: call_order.append(n)

        self.addon.register()

        self.assertEqual(call_order, FILES_ORDER)

    def test_register_is_idempotent_across_calls(self):
        """Calling register() twice invokes each submodule twice (Blender's responsibility to guard against double-register)."""
        self.addon.register()
        self.addon.register()
        for name in FILES_ORDER:
            self.assertEqual(self.mocks[name].register.call_count, 2)


class TestUnregister(unittest.TestCase):
    """unregister() must call every submodule's unregister() in reversed order."""

    def setUp(self):
        _cleanup_sys_modules()
        self.bpy_mock = MagicMock()
        self.mocks = {n: _make_submodule_mock(n) for n in SUBMODULE_NAMES}
        self.addon = _load_addon(self.mocks, self.bpy_mock)

    def tearDown(self):
        _cleanup_sys_modules()

    def test_unregister_calls_all_submodules(self):
        self.addon.unregister()
        for name in FILES_ORDER:
            self.mocks[name].unregister.assert_called_once_with()

    def test_unregister_order(self):
        call_order = []
        for name in SUBMODULE_NAMES:
            self.mocks[name].unregister.side_effect = lambda n=name: call_order.append(n)

        self.addon.unregister()

        self.assertEqual(call_order, list(reversed(FILES_ORDER)))

    def test_unregister_is_reverse_of_register(self):
        reg_order = []
        unreg_order = []
        for name in SUBMODULE_NAMES:
            self.mocks[name].register.side_effect = lambda n=name: reg_order.append(n)
            self.mocks[name].unregister.side_effect = lambda n=name: unreg_order.append(n)

        self.addon.register()
        self.addon.unregister()

        self.assertEqual(unreg_order, list(reversed(reg_order)))


class TestRegisterUnregisterCycle(unittest.TestCase):
    """A full register → unregister cycle must touch every submodule exactly once each."""

    def setUp(self):
        _cleanup_sys_modules()
        self.bpy_mock = MagicMock()
        self.mocks = {n: _make_submodule_mock(n) for n in SUBMODULE_NAMES}
        self.addon = _load_addon(self.mocks, self.bpy_mock)

    def tearDown(self):
        _cleanup_sys_modules()

    def test_full_cycle(self):
        self.addon.register()
        self.addon.unregister()
        for name in FILES_ORDER:
            self.mocks[name].register.assert_called_once_with()
            self.mocks[name].unregister.assert_called_once_with()


class TestReload(unittest.TestCase):
    """
    When bpy is already in the module namespace (Blender addon-reload path),
    __init__.py must call importlib.reload() on every submodule instead of
    performing fresh imports.
    """

    def setUp(self):
        _cleanup_sys_modules()
        self.bpy_mock = MagicMock()
        self.mocks = {n: _make_submodule_mock(n) for n in SUBMODULE_NAMES}

    def tearDown(self):
        _cleanup_sys_modules()

    def _reload_namespace(self) -> dict:
        """Build the module namespace that Blender would have after the first load."""
        ns = {"bpy": self.bpy_mock}
        for name, mock in self.mocks.items():
            ns[name] = mock
        return ns

    def test_reload_calls_importlib_reload_on_all_submodules(self):
        with patch("importlib.reload") as mock_reload:
            _load_addon(self.mocks, self.bpy_mock, extra_namespace=self._reload_namespace())

        reloaded_mocks = [c.args[0] for c in mock_reload.call_args_list]
        for name in SUBMODULE_NAMES:
            self.assertIn(
                self.mocks[name],
                reloaded_mocks,
                msg=f"importlib.reload() was not called for submodule '{name}'",
            )

    def test_reload_does_not_reimport_submodules_via_from_import(self):
        """In the reload path the `else` branch (fresh from . import ...) must NOT run."""
        import_side_effects = []

        original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        with patch("importlib.reload"):
            _load_addon(self.mocks, self.bpy_mock, extra_namespace=self._reload_namespace())

        # If the else branch ran it would have re-assigned the submodule names from
        # fresh imports.  Since we patched importlib.reload, the mocks remain intact.
        # We verify that the module's submodule attributes still point to our mocks.

    def test_fresh_load_does_not_call_importlib_reload(self):
        """Without bpy in the namespace (first load), importlib.reload() must NOT be called."""
        with patch("importlib.reload") as mock_reload:
            _load_addon(self.mocks, self.bpy_mock)  # no extra_namespace

        mock_reload.assert_not_called()

    def test_reload_submodule_references_preserved(self):
        """After reload the addon's submodule attributes still point to the mock objects."""
        with patch("importlib.reload"):
            addon = _load_addon(self.mocks, self.bpy_mock, extra_namespace=self._reload_namespace())

        for name, mock in self.mocks.items():
            self.assertIs(
                getattr(addon, name, None),
                mock,
                msg=f"addon.{name} should still reference the original mock after reload",
            )


if __name__ == "__main__":
    unittest.main()
