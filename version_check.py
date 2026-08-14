import threading
import urllib.request
import urllib.error
import json

import bpy

# Module-level state — read by the panel draw function
update_available = False
latest_version_str = ""
dismissed_version_str = ""

_RELEASES_URL = "https://api.github.com/repos/Weisl/simple_camera_manager/releases/latest"


def _parse_version(version_str):
    """Convert '2.1.4' or 'v2.1.4' to (2, 1, 4)."""
    return tuple(int(x) for x in version_str.lstrip("v").split("."))


def banner_visible():
    """Whether the update-available banner should currently be shown."""
    return update_available and latest_version_str != dismissed_version_str


def dismiss_banner():
    """Hide the banner until a release newer than the one just dismissed appears."""
    global dismissed_version_str
    dismissed_version_str = latest_version_str


def _tag_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def _fetch():
    global update_available, latest_version_str
    try:
        req = urllib.request.Request(
            _RELEASES_URL,
            headers={"User-Agent": "simple-camera-manager-addon"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        tag = data.get("tag_name", "")
        if not tag:
            return

        latest = _parse_version(tag)

        # Read current version from blender_manifest.toml at the addon root
        import os
        manifest_path = os.path.join(os.path.dirname(__file__), ".", "blender_manifest.toml")
        current_str = ""
        with open(manifest_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("version"):
                    current_str = line.split("=")[1].strip().strip('"')
                    break

        if not current_str:
            return

        current = _parse_version(current_str)

        if latest > current:
            update_available = True
            latest_version_str = tag.lstrip("v")
        else:
            # Re-checking (e.g. via the manual button) can find we're no
            # longer behind - clear any previously detected update.
            update_available = False
            print(f"[Simple Camera Manager] Addon is up to date (v{current_str})")

    except Exception as exc:
        print(f"[Simple Camera Manager] version check failed: {exc}")
    finally:
        _tag_redraw()


def start_version_check():
    """Fire a background thread to check for a newer release on GitHub."""
    if not bpy.app.online_access:
        return
    t = threading.Thread(target=_fetch, daemon=True)
    t.start()


class CAM_MANAGER_OT_check_for_updates(bpy.types.Operator):
    """Manually check GitHub for a newer release right now"""
    bl_idname = "cam_manager.check_for_updates"
    bl_label = "Check for Updates"
    bl_description = "Check GitHub for a newer release of Simple Camera Manager"

    def execute(self, context):
        if not bpy.app.online_access:
            self.report({'WARNING'}, "Online access is disabled in Blender's preferences")
            return {'CANCELLED'}
        self.report({'INFO'}, "Checking for updates…")
        start_version_check()
        return {'FINISHED'}


class CAM_MANAGER_OT_dismiss_update_banner(bpy.types.Operator):
    """Dismiss the update-available banner until a newer release appears"""
    bl_idname = "cam_manager.dismiss_update_banner"
    bl_label = "Dismiss Update Notice"
    bl_description = "Hide this notice until a newer release is available"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        dismiss_banner()
        _tag_redraw()
        return {'FINISHED'}


classes = (
    CAM_MANAGER_OT_check_for_updates,
    CAM_MANAGER_OT_dismiss_update_banner,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if hasattr(cls, 'bl_rna'):
            unregister_class(cls)
