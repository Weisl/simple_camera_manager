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

## Simple Camera Manager v1.8.0

This release adds camera presets, a camera roll gizmo, automatic render slot
cycling, and a reworked update checker. It is tested on Blender 4.2 through
5.3.

### Features & Improvements

- [#161](https://github.com/Weisl/simple_camera_manager/issues/161): Added
  **Camera Presets**. A single dropdown offers built-in looks (Full Frame,
  APS-C, Micro Four Thirds, Medium Format, Super 35, 1-inch, orthographic)
  and your own saved presets. Use **+** / **−** to save or remove the active
  camera's settings.
- Added a **Sensor Format** dropdown that applies Blender's built-in sensor
  sizes (Full Frame, APS-C, MFT, Arri, RED, Blackmagic, phone sensors, …) to
  the scene camera from the 3D Viewport sidebar and the pie menu.
- [#67](https://github.com/Weisl/simple_camera_manager/issues/67): Added a
  **camera roll gizmo**. Drag the ring to roll the camera around its view
  axis; hold Shift to snap in 5° steps.
- Added an option to **automatically cycle Render Result slots** after each
  render, so repeated renders no longer overwrite each other (off by default,
  enable it in the add-on preferences).
- The update checker now shows a dismissible banner when a newer release is
  available.
- The pie menu now shows all of Blender's camera composition guides,
  including the golden and harmony triangles and safe areas.
- Added a **Show** button next to the "Camera is hidden" warning. It unhides
  the camera and only the collections containing it.
- Added Blender 5.3 to the tested versions.

### Bug Fixes

- Fixed the add-on's **Open Preferences** button not expanding the add-on's
  preferences when it is installed through the Extensions platform.

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
