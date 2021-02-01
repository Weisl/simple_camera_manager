import bpy


class CameraButtonsPanel:
    '''Properties Panel in the camera data tab'''
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        engine = context.engine
        return context.camera and (engine in cls.COMPAT_ENGINES)


class SceneButtonsPanel:
    '''Properties Panel in the scene tab'''
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"


class CameraManagerPanel(SceneButtonsPanel, bpy.types.Panel):
    bl_idname = "OBJECT_PT_camera_manager"
    bl_label = "Camera Manager"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Camera Manager")

        scene = context.scene

        row = layout.row()
        row.prop(scene, "camera")

        # row = layout.row()
        # row.prop(context.space_data, "lock_camera")

        row = layout.row()
        row.operator("utilities.cycle_cameras_next", text="previous", icon='TRIA_LEFT')
        row.operator("utilities.cycle_cameras_backward", text="next", icon='TRIA_RIGHT')
        # row = layout.row()
        # row.operator("utilities.modal_camera_dolly_zoom", text="Dolly Zoom", icon='CON_CAMERASOLVER')


        row = layout.row(align=True)
        row.prop_search(scene.cam_collection, "collection", bpy.data, "collections", text='Camera Collection')
        row.operator("camera.create_collection", text='', icon='COLLECTION_NEW')

        row = layout.row()
        row.operator('cameras.all_to_collection')

        layout.separator()

        row = layout.row()
        # template_list now takes two new args.
        # The first one is the identifier of the registered UIList to use (if you want only the default list,
        # with no custom draw code, use "UI_UL_list").
        layout.template_list("CAMERA_UL_cameras_scene", "", scene, "objects", scene, "camera_list_index")


class CameraManagerPopup(bpy.types.Panel):
    bl_idname = "OBJECT_PT_camera_manager_popup"
    bl_label = "Camera Manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = "empty"
    bl_ui_units_x = 40
    bl_options = {'DRAW_BOX'}

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Camera Manager")

        scene = context.scene
        split = layout.split(factor=0.5)
        col = split.column()
        row = col.row(align=True)
        row.prop_search(scene.cam_collection, "collection", bpy.data, "collections", text='Camera Collection')
        row.operator("camera.create_collection", text='', icon='COLLECTION_NEW')
        row = col.row()
        row.operator('cameras.all_to_collection')
        row = col.row()
        row.operator("view3d.view_camera", text="Camera", icon='VIEW_CAMERA')

        layout.separator()
        # template_list now takes two new args.
        # The first one is the identifier of the registered UIList to use (if you want only the default list,
        # with no custom draw code, use "UI_UL_list").
        layout.template_list("CAMERA_UL_cameras_popup", "", scene, "objects", scene, "camera_list_index")


class CameraPanel(CameraButtonsPanel, bpy.types.Panel):
    bl_label = "Camera Manager"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'}

    def draw(self, context):
        layout = self.layout

        cam = context.camera

        row = layout.row()
        row.prop(cam, "resolution")

        row = layout.row()
        op = layout.operator("utilites.camera_resolutio_from_image",
                             text="Resoltuion from image").camera_name = cam.name


class CameraCollectionProperty(bpy.types.PropertyGroup):
    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
    )


classes = (
    CameraCollectionProperty,
    CameraManagerPanel,
    CameraManagerPopup,
    CameraPanel,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    scene = bpy.types.Scene
    # The PointerProperty has to be after registering the classes to know about the custom property type
    scene.cam_collection = bpy.props.PointerProperty(name="Camera Collection", type=CameraCollectionProperty)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
