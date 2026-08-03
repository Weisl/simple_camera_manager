# Changelog

All notable changes to Simple Camera Manager are documented here. Dates are
set when a version is actually tagged/released.

Each version below mirrors the structure used on the
[documentation site's release notes page](https://weisl.github.io/simple_camera_manager/camera_manager_release_notes/):
a short summary of the release, followed by "Features & Improvements" and
"Bug Fixes" lists whose entries link back to their GitHub issue. New releases
are added as a new section above the previous one — existing entries are
never overwritten, so this file (like the docs page) accumulates the full
release history over time.

## Simple Camera Manager v1.7.1 (Unreleased)

This release fixes two Blender 5.0+ compatibility issues found during a
compatibility audit, and adds a new operator to align an existing camera to
the current viewport view.

### Features & Improvements

- Added **Align Camera to View** (`camera.align_camera_to_view`) — snaps the
  active scene camera to match the current viewport view, without creating a
  new camera.
- [#151](https://github.com/Weisl/simple_camera_manager/issues/151): The pie
  menu now shows `ortho_scale` instead of focal length for Orthographic
  cameras.

### Bug Fixes

- [#152](https://github.com/Weisl/simple_camera_manager/issues/152): Fixed
  **Open Render Folder** crashing on Blender 5.0+ — `bpy.ops.file.external_operation`
  dropped its `filepath` property in 5.0; switched to `bpy.ops.wm.path_open`.
- [#153](https://github.com/Weisl/simple_camera_manager/issues/153): Fixed
  the camera properties panel being hidden on Blender 4.2–4.5 when using the
  default render engine, whose identifier was `BLENDER_EEVEE_NEXT` in that
  range instead of `BLENDER_EEVEE`.
