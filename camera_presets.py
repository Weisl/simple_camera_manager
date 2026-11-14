import bpy
from bpy.types import Menu, Operator
from bl_operators.presets import AddPresetBase

# Built-in lens presets, listed in the same "Lens Presets" menu as the
# user's own saved presets (CAM_MANAGER_OT_camera_preset_add). No files are
# written and nothing can be added or removed here.
#
# Every lens preset, built-in or saved, sets exactly the same fields, all of
# which are visible in the Lens box (see LENS_PRESET_FIELDS):
#   camera type, focal length (or ortho scale), sensor fit, width and height.
# Clipping, depth of field, resolution and lighting are deliberately left
# alone so a preset never changes settings the user can't see next to it.
#
# Physical sensor sizes match real-world formats (and Blender's own bundled
# camera presets under scripts/presets/camera/*.py):
#   Full Frame         36.0 x 24.0 mm  (Canon/Sony/Nikon full-frame bodies)
#   APS-C              22.3 x 14.9 mm  (Canon APS-C crop sensor)
#   Micro Four Thirds  17.3 x 13.0 mm  (Panasonic/Olympus MFT)
#   Medium Format      44.0 x 33.0 mm  (Hasselblad X / Fujifilm GFX)
#   Super 35 (cinema)  24.89 x 18.66 mm (ARRI/RED-class digital cinema gauge)
#   1-inch (compact)   13.2 x 8.8 mm   (Sony RX100-class / drone / vlog cameras)
LENS_PRESET_FIELDS = ('type', 'lens', 'ortho_scale', 'sensor_fit', 'sensor_width', 'sensor_height')


def _perspective(lens, sensor_width, sensor_height):
    return {
        'type': 'PERSP',
        'lens': lens,
        'sensor_fit': 'HORIZONTAL',
        'sensor_width': sensor_width,
        'sensor_height': sensor_height,
    }


BUILTIN_CAMERA_PRESETS = {
    'Full Frame 24mm Wide': _perspective(24.0, 36.0, 24.0),
    'Full Frame 50mm Standard': _perspective(50.0, 36.0, 24.0),
    'Full Frame 85mm Portrait': _perspective(85.0, 36.0, 24.0),
    'APS-C 90mm Macro': _perspective(90.0, 22.3, 14.9),
    'APS-C 135mm Telephoto': _perspective(135.0, 22.3, 14.9),
    'Micro Four Thirds 12mm Wide': _perspective(12.0, 17.3, 13.0),
    'Medium Format 80mm Standard': _perspective(80.0, 44.0, 33.0),
    'Super 35 32mm Cinema': _perspective(32.0, 24.89, 18.66),
    'Compact 1-inch 9mm Vlog': _perspective(9.0, 13.2, 8.8),
    'Studio Orthographic': {
        'type': 'ORTHO',
        'ortho_scale': 5.0,
    },
}

BUILTIN_CAMERA_PRESET_ITEMS = [(name, name, "") for name in BUILTIN_CAMERA_PRESETS]


class CAM_MANAGER_OT_apply_builtin_camera_preset(Operator):
    """Apply one of Simple Camera Manager's built-in lens presets"""
    bl_idname = "cam_manager.apply_builtin_camera_preset"
    bl_label = "Built-in Lens Preset"
    bl_description = "Set the camera type, focal length and sensor size of the active scene camera"
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
            setattr(cam, key, value)

        return {'FINISHED'}


class CAM_MANAGER_OT_camera_preset_add(AddPresetBase, Operator):
    """Save or remove a lens preset (camera type, focal length and sensor size)"""
    bl_idname = "cam_manager.camera_preset_add"
    bl_label = "Add Lens Preset"
    preset_menu = "CAM_MANAGER_MT_camera_presets"
    preset_subdir = "simple_camera_manager/camera"

    # draw_camera_settings() is always called with context.scene.camera, not
    # necessarily the active/selected object - bpy.context.camera (what
    # Blender's own native camera presets use) isn't guaranteed to match that
    # from the 3D viewport N-panel or pie menu, only from the Properties
    # Editor's Camera Data tab.
    preset_defines = ["cam = bpy.context.scene.camera.data"]

    preset_values = [f"cam.{field}" for field in LENS_PRESET_FIELDS]


class CAM_MANAGER_MT_camera_presets(Menu):
    """Combined preset menu: built-in starter looks on top, the user's own
    saved presets (via the +/- buttons next to this menu) below - one
    dropdown instead of two separate ones for built-in vs. custom presets."""
    bl_label = "Lens Presets"
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


class CAM_MANAGER_OT_apply_sensor_preset(Operator):
    """Apply one of Blender's sensor format presets to the active scene camera"""
    bl_idname = "cam_manager.apply_sensor_preset"
    bl_label = "Apply Sensor Format"
    bl_description = "Set the sensor size of the active scene camera to this format"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})

    def execute(self, context):
        cam_obj = context.scene.camera
        if cam_obj is None:
            self.report({'WARNING'}, "No active scene camera")
            return {'CANCELLED'}

        # Blender's native sensor presets (scripts/presets/camera/*.py) write
        # to bpy.context.camera, which is only set in the Properties Editor's
        # Camera Data tab. Pointing it at the scene camera lets the same
        # files work from the 3D viewport N-panel and the pie menu.
        try:
            with context.temp_override(camera=cam_obj.data):
                bpy.utils.execfile(self.filepath)
        except Exception as ex:
            self.report({'ERROR'}, f"Failed to apply sensor format: {ex!r}")
            return {'CANCELLED'}

        return {'FINISHED'}


class CAM_MANAGER_MT_sensor_presets(Menu):
    """Blender's own sensor format presets (Full Frame, APS-C, MFT, Arri, RED,
    phone sensors, ...), reused as-is rather than duplicating that database.
    Sets sensor_width/height/fit only."""
    bl_label = "Sensor Format"
    preset_subdir = "camera"
    preset_operator = "cam_manager.apply_sensor_preset"
    preset_extensions = {".py"}
    draw = Menu.draw_preset


classes = (
    CAM_MANAGER_OT_camera_preset_add,
    CAM_MANAGER_OT_apply_builtin_camera_preset,
    CAM_MANAGER_MT_camera_presets,
    CAM_MANAGER_OT_apply_sensor_preset,
    CAM_MANAGER_MT_sensor_presets,
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
