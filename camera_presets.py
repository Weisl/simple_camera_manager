import bpy
from bpy.types import Menu, Operator
from bl_operators.presets import AddPresetBase

# Built-in "starter" camera looks, distinct from the user-saved presets below
# (CAM_MANAGER_OT_camera_preset_add / preset_subdir): no files are written,
# nothing to add/remove - just a fixed set of realistic sensor/lens/aperture
# combos covering common photography and cinematography formats, drawn in
# the same combined "Camera Presets" menu as the user's own saved presets.
#
# Physical sensor sizes match real-world formats (and Blender's own bundled
# camera presets under scripts/presets/camera/*.py) so these numbers agree
# with the "Sensor Format" dropdown next to this menu, rather than inventing
# a second, possibly-inconsistent set of values for the same formats:
#   Full Frame        36.0 x 24.0 mm  (Canon/Sony/Nikon full-frame bodies)
#   APS-C              22.3 x 14.9 mm  (Canon APS-C crop sensor)
#   Micro Four Thirds  17.3 x 13.0 mm  (Panasonic/Olympus MFT)
#   Medium Format       44.0 x 33.0 mm  (Hasselblad X / Fujifilm GFX)
#   Super 35 (cinema)  24.89 x 18.66 mm (ARRI/RED-class digital cinema gauge)
#   1-inch (compact)   13.2 x 8.8 mm   (Sony RX100-class / drone / vlog cameras)
# Lens/aperture/focus-distance combos follow common shot-type conventions
# (e.g. 85mm f/1.4 for portraits, wide+deep-focus for establishing shots,
# shallow fast primes for cinematic coverage).
BUILTIN_CAMERA_PRESETS = {
    'Full Frame 50mm Standard f/1.8': {
        'lens': 50.0,
        'sensor_width': 36.0,
        'sensor_height': 24.0,
        'sensor_fit': 'HORIZONTAL',
        'clip_start': 0.1,
        'clip_end': 100.0,
        'dof': {'use_dof': True, 'aperture_fstop': 1.8, 'focus_distance': 1.5},
    },
    'Full Frame 85mm Portrait f/1.4': {
        'lens': 85.0,
        'sensor_width': 36.0,
        'sensor_height': 24.0,
        'sensor_fit': 'HORIZONTAL',
        'clip_start': 0.3,
        'clip_end': 100.0,
        'dof': {'use_dof': True, 'aperture_fstop': 1.4, 'focus_distance': 1.2},
    },
    'APS-C 90mm Macro f/2.8': {
        'lens': 90.0,
        'sensor_width': 22.3,
        'sensor_height': 14.9,
        'sensor_fit': 'HORIZONTAL',
        'clip_start': 0.01,
        'clip_end': 10.0,
        'dof': {'use_dof': True, 'aperture_fstop': 2.8, 'focus_distance': 0.3},
    },
    'APS-C 135mm Telephoto f/2.8': {
        'lens': 135.0,
        'sensor_width': 22.3,
        'sensor_height': 14.9,
        'sensor_fit': 'HORIZONTAL',
        'clip_start': 0.5,
        'clip_end': 300.0,
        'dof': {'use_dof': True, 'aperture_fstop': 2.8, 'focus_distance': 4.0},
    },
    'Micro Four Thirds 12mm Wide Establishing f/4': {
        'lens': 12.0,
        'sensor_width': 17.3,
        'sensor_height': 13.0,
        'sensor_fit': 'HORIZONTAL',
        'clip_start': 0.05,
        'clip_end': 1000.0,
        'dof': {'use_dof': False},
    },
    'Medium Format 80mm Studio f/4': {
        'lens': 80.0,
        'sensor_width': 44.0,
        'sensor_height': 33.0,
        'sensor_fit': 'HORIZONTAL',
        'clip_start': 0.3,
        'clip_end': 100.0,
        'dof': {'use_dof': True, 'aperture_fstop': 4.0, 'focus_distance': 1.5},
    },
    'Super 35 Cinema 32mm Wide T2.8': {
        'lens': 32.0,
        'sensor_width': 24.89,
        'sensor_height': 18.66,
        'sensor_fit': 'HORIZONTAL',
        'clip_start': 0.3,
        'clip_end': 1000.0,
        'dof': {'use_dof': True, 'aperture_fstop': 2.8, 'focus_distance': 3.0},
    },
    'Full Frame Cinema 50mm Shallow T1.5': {
        'lens': 50.0,
        'sensor_width': 36.0,
        'sensor_height': 24.0,
        'sensor_fit': 'HORIZONTAL',
        'clip_start': 0.3,
        'clip_end': 1000.0,
        'dof': {'use_dof': True, 'aperture_fstop': 1.5, 'focus_distance': 2.0},
    },
    'Compact 1-inch 9mm Vlog f/2.8': {
        'lens': 9.0,
        'sensor_width': 13.2,
        'sensor_height': 8.8,
        'sensor_fit': 'HORIZONTAL',
        'clip_start': 0.05,
        'clip_end': 1000.0,
        'dof': {'use_dof': True, 'aperture_fstop': 2.8, 'focus_distance': 2.0},
    },
    'Studio Orthographic': {
        'type': 'ORTHO',
        'ortho_scale': 5.0,
        'dof': {'use_dof': False},
    },
}

BUILTIN_CAMERA_PRESET_ITEMS = [(name, name, "") for name in BUILTIN_CAMERA_PRESETS]


class CAM_MANAGER_OT_apply_builtin_camera_preset(Operator):
    """Apply one of Simple Camera Manager's built-in camera presets"""
    bl_idname = "cam_manager.apply_builtin_camera_preset"
    bl_label = "Built-in Camera Preset"
    bl_description = "Apply one of Simple Camera Manager's built-in camera presets"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(
        name="Preset",
        items=BUILTIN_CAMERA_PRESET_ITEMS,
    )

    def execute(self, context):
        cam_obj = context.scene.camera
        if cam_obj is None:
            self.report({'WARNING'}, "No active scene camera")
            return {'CANCELLED'}

        cam = cam_obj.data
        for key, value in BUILTIN_CAMERA_PRESETS[self.preset].items():
            if key == 'dof':
                for dof_key, dof_value in value.items():
                    setattr(cam.dof, dof_key, dof_value)
            else:
                setattr(cam, key, value)

        return {'FINISHED'}


class CAM_MANAGER_OT_camera_preset_add(AddPresetBase, Operator):
    """Add or remove a Camera Manager camera preset"""
    bl_idname = "cam_manager.camera_preset_add"
    bl_label = "Add Camera Preset"
    preset_menu = "CAM_MANAGER_MT_camera_presets"
    preset_subdir = "simple_camera_manager/camera"

    # draw_camera_settings() is always called with context.scene.camera, not
    # necessarily the active/selected object - bpy.context.camera (what
    # Blender's own native camera presets use) isn't guaranteed to match that
    # from the 3D viewport N-panel or pie menu, only from the Properties
    # Editor's Camera Data tab.
    preset_defines = ["cam = bpy.context.scene.camera.data"]

    preset_values = [
        "cam.type",
        "cam.resolution_overwrite",
        "cam.resolution",
        "cam.lens",
        "cam.ortho_scale",
        "cam.clip_start",
        "cam.clip_end",
        "cam.exposure",
        "cam.dof.use_dof",
        "cam.dof.focus_distance",
        "cam.dof.focus_subtarget",
        "cam.show_rotation_gizmo",
        "cam.dolly_zoom_link_focus",
        # ID-pointer fields last: applying a preset re-executes it top to
        # bottom, so if the referenced datablock doesn't exist in the target
        # file that line raises and aborts the rest of the script - keeping
        # these last means only they are lost, not the fields above.
        "cam.dof.focus_object",
        "cam.world",
    ]


class CAM_MANAGER_MT_camera_presets(Menu):
    """Combined preset menu: built-in starter looks on top, the user's own
    saved presets (via the +/- buttons next to this menu) below - one
    dropdown instead of two separate ones for built-in vs. custom presets."""
    bl_label = "Camera Presets"
    preset_subdir = "simple_camera_manager/camera"
    preset_operator = "script.execute_preset"

    def draw(self, context):
        layout = self.layout

        layout.label(text="Built-in")
        for name in BUILTIN_CAMERA_PRESETS:
            op = layout.operator("cam_manager.apply_builtin_camera_preset", text=name)
            op.preset = name

        layout.separator()
        layout.label(text="Custom")
        # Lists every user-saved preset file under preset_subdir, each
        # invoking preset_operator with that file's path - the same logic
        # this class used to expose directly as `draw = Menu.draw_preset`,
        # now just one section of the combined menu. Saving (+) / removing
        # (-) via CAM_MANAGER_OT_camera_preset_add is unaffected.
        Menu.draw_preset(self, context)


classes = (
    CAM_MANAGER_OT_camera_preset_add,
    CAM_MANAGER_OT_apply_builtin_camera_preset,
    CAM_MANAGER_MT_camera_presets,
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
