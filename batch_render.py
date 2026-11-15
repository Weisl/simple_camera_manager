"""Batch render: render every camera marked with ``render_selected`` one
after another.

Each camera is rendered with Blender's own render job. The add-on listens
for ``render_complete`` to start the next camera and for ``render_cancel``
to stop the whole batch when you press Esc (issue #159). Both handlers
are only installed while a batch runs.

Render handlers run on the render thread, so they only schedule work;
switching cameras and starting the next render happens in a timer on the
main thread.
"""

import bpy
from bpy.app.handlers import persistent

# Seconds to wait after a render before touching the scene again, so the
# finished render job has fully ended.
_NEXT_RENDER_DELAY = 1.0


class _BatchState:
    """The batch that is currently rendering, if any."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.active = False
        self.camera_names = []
        self.index = 0
        self.original_camera_name = None
        self.original_filepath = None


_state = _BatchState()


def is_batch_rendering():
    return _state.active


def _defer(func, delay=_NEXT_RENDER_DELAY):
    """Run ``func`` on the main thread after ``delay`` seconds."""
    bpy.app.timers.register(func, first_interval=delay)


def _start_render():
    bpy.ops.render.render('INVOKE_DEFAULT', write_still=True, use_viewport=False)


def _set_scene_camera(camera_name):
    bpy.ops.cam_manager.change_scene_camera(camera_name=camera_name, switch_to_cam=True)


def _render_current_camera():
    """Switch to the current camera and start its render. Timer callback."""
    if not _state.active:
        return None

    scene = bpy.context.scene
    while _state.index < len(_state.camera_names):
        name = _state.camera_names[_state.index]
        if scene.objects.get(name) is not None:
            break
        print(f"Batch render: skipping '{name}', it is no longer in the scene")
        _state.index += 1
    else:
        _finish()
        return None

    name = _state.camera_names[_state.index]
    print(f"Batch render: camera {_state.index + 1}/{len(_state.camera_names)}: {name}")
    try:
        # The output path may have been changed per camera (Use Camera Name),
        # so every camera starts from the path the batch started with.
        scene.render.filepath = _state.original_filepath
        _set_scene_camera(name)
        _start_render()
    except Exception as error:  # noqa: BLE001 - always clean up the batch
        print(f"Batch render: rendering '{name}' failed: {error}")
        _finish(aborted=True)
    return None


def _finish(aborted=False):
    """Restore the scene camera and output path and stop listening for renders."""
    rendered = _state.index
    total = len(_state.camera_names)
    original_camera_name = _state.original_camera_name
    original_filepath = _state.original_filepath
    _state.reset()
    _remove_handlers()

    scene = bpy.context.scene
    if original_camera_name and scene.objects.get(original_camera_name) is not None:
        _set_scene_camera(original_camera_name)
    if original_filepath is not None:
        scene.render.filepath = original_filepath

    if aborted:
        print(f"Batch render cancelled after {rendered} of {total} cameras")
    else:
        print(f"Batch render finished: {rendered} cameras rendered")
    return None


def _on_render_complete(scene, depsgraph=None):
    if not _state.active:
        return
    _state.index += 1
    _defer(_render_current_camera)


def _on_render_cancel(scene, depsgraph=None):
    if not _state.active:
        return
    _defer(lambda: _finish(aborted=True), delay=0.0)


_HANDLERS = (
    (bpy.app.handlers.render_complete, _on_render_complete),
    (bpy.app.handlers.render_cancel, _on_render_cancel),
)


def _add_handlers():
    for handlers, func in _HANDLERS:
        if func not in handlers:
            handlers.append(func)


def _remove_handlers():
    for handlers, func in _HANDLERS:
        while func in handlers:
            handlers.remove(func)


@persistent
def _forget_batch_on_load(*_args):
    """A new file has other cameras; drop a batch that was still running."""
    _state.reset()
    _remove_handlers()


class CAM_MANAGER_OT_multi_camera_rendering_handlers(bpy.types.Operator):
    """Render all cameras marked for rendering, one after another. Press Esc during a render to stop the batch"""
    bl_idname = "cam_manager.multi_camera_rendering_handlers"
    bl_label = "Batch Render Selected Cameras"

    def execute(self, context):
        if _state.active:
            self.report({'WARNING'}, "A batch render is already running")
            return {'CANCELLED'}

        scene = context.scene
        cameras = [obj for obj in scene.objects
                   if obj.type == 'CAMERA' and getattr(obj.data, "render_selected", False)]
        if not cameras:
            self.report({'ERROR'}, "No cameras selected for rendering")
            return {'CANCELLED'}

        _state.active = True
        _state.camera_names = [cam.name for cam in cameras]
        _state.index = 0
        _state.original_camera_name = scene.camera.name if scene.camera else None
        _state.original_filepath = scene.render.filepath
        _add_handlers()

        self.report({'INFO'}, f"Batch rendering {len(cameras)} cameras. Press Esc to stop")
        _render_current_camera()
        return {'FINISHED'}


classes = (
    CAM_MANAGER_OT_multi_camera_rendering_handlers,
)


def register():
    """Register the operators with Blender."""
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    if _forget_batch_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_forget_batch_on_load)


def unregister():
    """Unregister the operators from Blender."""
    from bpy.utils import unregister_class

    _state.reset()
    _remove_handlers()
    if _forget_batch_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_forget_batch_on_load)

    for cls in reversed(classes):
        if hasattr(cls, 'bl_rna'):
            unregister_class(cls)
