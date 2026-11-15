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
  **Lens Presets** in a new **Lens** box. A preset sets the camera type,
  focal length (or orthographic scale), sensor size and resolution, all
  shown in the same box. Choose from built-in lenses (Full Frame, APS-C,
  Micro Four Thirds, Medium Format, Super 35, 1-inch, orthographic), which
  render at 1920 px wide in the sensor's aspect ratio, or your own: use
  **+** / **−** to save or remove the active camera's lens.
- Added a **Sensor Format** dropdown to the Lens box that applies Blender's
  built-in sensor sizes (Full Frame, APS-C, MFT, Arri, RED, Blackmagic,
  phone sensors, …) to the scene camera from the 3D Viewport sidebar and the
  pie menu.
- [#66](https://github.com/Weisl/simple_camera_manager/issues/66), [#179](https://github.com/Weisl/simple_camera_manager/issues/179):
  Added a **camera roll gizmo**. Drag the ring to roll the camera around its view
  axis; hold Ctrl to snap in 5° steps. Rolls can be undone with Ctrl+Z,
  as can drags of the Dolly Zoom target gizmo.
- [#64](https://github.com/Weisl/simple_camera_manager/issues/64): Added
  **Render to New Slot** (off by default, enable it in the add-on
  preferences). Every render goes into a Render Result slot that doesn't
  hold a render yet, picked before the render starts, so you see the new
  render and earlier ones are kept, also when rendering the same camera
  again. A slot is added when all are used. Works for F12, the camera
  list's Render button and Batch Render.
- [#157](https://github.com/Weisl/simple_camera_manager/issues/157): The
  update checker now shows a dismissible banner when a newer release is
  available, and a **Check for Updates** button in the add-on preferences
  checks on demand.
- [#167](https://github.com/Weisl/simple_camera_manager/issues/167): The pie
  menu now shows all of Blender's camera composition guides, including the
  golden and harmony triangles and safe areas.
- [#165](https://github.com/Weisl/simple_camera_manager/issues/165): Added a
  **Show** button next to the "Camera is hidden" warning. It unhides the
  camera and only the collections containing it.
- [#171](https://github.com/Weisl/simple_camera_manager/issues/171), [#178](https://github.com/Weisl/simple_camera_manager/issues/178):
  **Dolly Zoom** now works like the modal tools in Simple Collider. Nothing
  changes until you press a key: **F** focal length, **V** field of view,
  **D** target distance, **W** target width; press the key again to stop.
  Changing the focal length or field of view moves the camera so the target
  keeps its size in the frame (perspective cameras only; on an orthographic
  camera F and V are greyed out). While no key is active you can drag the
  target gizmo. The viewport overlay got the same look as Simple Collider's.
  A dashed frame shows the framing the camera started with (**R** toggles
  it), and the target plane shows where the target distance cuts through the
  scene. **P** switches the plane between a see-through plane with a cut
  line, only the cut line, and off; the choice is kept for the next run.
- [#175](https://github.com/Weisl/simple_camera_manager/issues/175): Reworked
  the **Alt+C pie menu**. A pie menu closes after any click, so it
  now only holds one-click actions: **Previous / Next Camera**, **View
  Camera**, **New Camera from View** (or **Align Camera to View** in camera
  view), **Dolly Zoom**, and a small box with lens preset, focal length,
  resolution and composition guide menus, Passepartout, Lock to View, Lock
  Camera and Select. **Camera Settings…** opens the new camera popover.
- [#176](https://github.com/Weisl/simple_camera_manager/issues/176): Added a
  **camera popover** for the scene camera. It stays open while you
  change settings and has Camera, Background Image, Viewport Display and
  Render sections. The Background Image section shows each image's
  visibility, opacity, front/back and framing, with a checkbox to show or
  hide all of them. Open the popover from the camera button in the 3D
  Viewport header (can be turned off in the add-on preferences) or from the
  pie menu, which also has a one-click Background Images toggle.
- [#177](https://github.com/Weisl/simple_camera_manager/issues/177): Added
  **Focus Distance**, a modal tool that works like Dolly Zoom. **D**
  drags the focus distance, **A** the f-stop, and **E** focuses on the surface
  under the mouse. A see-through plane at the focus distance shows where the
  focus cuts through the scene (**P** switches between plane, cut line and
  off), and dashed frames mark the near and far limits of the sharp range
  (**R** toggles them). Start it from the pie menu, the camera popover or the
  sidebar.
- Added Blender 5.3 to the tested versions.

### Bug Fixes

- [#174](https://github.com/Weisl/simple_camera_manager/issues/174): Fixed the
  pie menu's **previous** and **next** buttons switching cameras in
  the wrong direction.
- [#158](https://github.com/Weisl/simple_camera_manager/issues/158): Fixed
  the add-on's **Open Preferences** button not expanding the add-on's
  preferences when it is installed through the Extensions platform.
- [#170](https://github.com/Weisl/simple_camera_manager/issues/170): Fixed
  the Preferences window closing as soon as the add-on is enabled or the
  popup width is changed. Separate render and file browser windows were
  closed as well.

## Simple Camera Manager v1.7.1

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
