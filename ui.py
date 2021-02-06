import bpy


def filter_list(self, context):
    '''
    Filter cameras from all objects for the UI list and soft them
    :param self:
    :param context:
    :return: flt_flags is a bit-flag containing the filtering and flt
            flt_neworder defines the order of all cameras
    '''

    # Default return values.
    flt_flags = []
    flt_neworder = []

    # Get all objects from scene.
    objects = context.scene.objects

    # Create bitmask for all objects
    flt_flags = [self.bitflag_filter_item] * len(objects)

    # Filter by object type.
    for idx, obj in enumerate(objects):
        if obj.type == "CAMERA":
            flt_flags[idx] |= self.CAMERA_FILTER
        else:
            flt_flags[idx] &= ~self.bitflag_filter_item

    return flt_flags, flt_neworder


class CAMERA_UL_cameras_popup(bpy.types.UIList):
    """UI list showing all cameras with associated resolution. The resolution can be changed directly from this list"""
    # The draw_item function is called for each item of the collection that is visible in the list.
    #   data is the RNA object containing the collection,
    #   item is the current drawn item of the collection,
    #   icon is the "computed" icon for the item (as an integer, because some objects like materials or textures
    #   have custom icons ID, which are not available as enum items).
    #   active_data is the RNA object containing the active property for the collection (i.e. integer pointing to the
    #   active item of the collection).
    #   active_propname is the name of the active property (use 'getattr(active_data, active_propname)').
    #   index is index of the current item in the collection.
    #   flt_flag is the result of the filtering process for this item.
    #   Note: as index and flt_flag are optional arguments, you do not have to use/declare them here if you don't
    #         need them.

    # Constants (flags)
    # Be careful not to shadow FILTER_ITEM!
    CAMERA_FILTER = 1 << 0

    def filter_items(self, context, data, propname):
        # This function gets the collection property (as the usual tuple (data, propname)), and must return two lists:
        # * The first one is for filtering, it must contain 32bit integers were self.bitflag_filter_item marks the
        #   matching item as filtered (i.e. to be shown), and 31 other bits are free for custom needs. Here we use the
        #   first one to mark CAMERA_FILTER.
        # * The second one is for reordering, it must return a list containing the new indices of the items (which
        #   gives us a mapping org_idx -> new_idx).
        # Please note that the default UI_UL_list defines helper functions for common tasks (see its doc for more info).
        # If you do not make filtering and/or ordering, return empty list(s) (this will be more efficient than
        # returning full lists doing nothing!).
        flt_flags, flt_neworder = filter_list(self, context)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        obj = item
        cam = item.data

        # draw_item must handle the three layout types. Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
            # We use icon_value of label, as our given icon is an integer value, not an enum ID.
            # Note "data" names should never be translated!
            if obj.type == 'CAMERA':

                split = layout.split(factor=0.7)
                split_left = split.column().split(factor=0.5)
                col_01 = split_left.column()
                col_02 = split_left.column()
                split_right = split.column().split(factor=0.5)
                col_03 = split_right.column()
                col_04 = split_right.column()

                # Col01
                row = col_01.row(align=True)
                icon = 'VIEW_CAMERA' if obj == bpy.context.scene.camera else 'FORWARD'
                op = row.operator("cam_manager.change_scene_camera", text='', icon=icon)
                op.camera_name = obj.name
                op.switch_to_cam = False
                row.prop(obj, 'name', text='')

                # Col02
                icon = 'HIDE_OFF' if obj.visible_get() else 'HIDE_ON'
                op = row.operator("camera.hide_unhide", icon=icon, text='')
                op.camera_name = obj.name
                op.cam_hide = obj.visible_get()
                row.prop(obj, "hide_viewport", text='')
                row.prop(obj, "hide_select", text='')

                if obj.get('lock'):
                    op = row.operator("cam_manager.lock_unlock_camera", icon='LOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = False
                else:
                    op = row.operator("cam_manager.lock_unlock_camera", icon='UNLOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = True

                # #COLUMN 03 Lens and resolution
                row = col_02.row()
                c = row.column(align=True)
                c.prop(cam, 'lens', text='')
                c = row.column(align=True)
                c.prop(cam, "resolution", text="")
                op = row.operator("cam_manager.camera_resolutio_from_image", text="", icon='IMAGE_BACKGROUND')
                op.camera_name = cam.name
                c = row.column(align=True)
                c.prop(cam, "clip_start", text="")
                c.prop(cam, "clip_end", text="")

                row = col_03.row(align=True)
                row.prop_search(cam.world, "world_material", bpy.data, "worlds", text='')

                row = col_04.row(align=True)
                # op = row.operator("cameras.add_collection", icon='OUTLINER_COLLECTION')
                # op.object_name = obj.name

                op = row.operator('cameras.custom_render', text='', icon='RENDER_STILL')
                op.camera_name = obj.name

                row.prop(cam, "slot")
                row.prop_search(bpy.data.images[0].render_slots, "active_index", text="Slot")


            else:
                layout.label(text=obj.name)

        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=obj.name)


class CAMERA_UL_cameras_scene(bpy.types.UIList):
    """UI list showing all cameras with associated resolution. The resolution can be changed directly from this list"""
    CAMERA_FILTER = 1 << 0

    def filter_items(self, context, data, propname):
        flt_flags, flt_neworder = filter_list(self, context)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        obj = item
        cam = item.data

        # draw_item must handle the three layout types. Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
            # We use icon_value of label, as our given icon is an integer value, not an enum ID.
            # Note "data" names should never be translated!
            if obj.type == 'CAMERA':
                c = layout.column()
                row = c.row()

                split = row.split(factor=0.6)
                col_01 = split.column()
                col_02 = split.column()

                # COLUMN 01
                row = col_01.row(align=True)
                # Change icon for already active cam
                icon = 'VIEW_CAMERA' if obj == bpy.context.scene.camera else 'FORWARD'
                op = row.operator("cam_manager.change_scene_camera", text='', icon=icon)
                op.camera_name = obj.name
                op.switch_to_cam = False
                row.prop(obj, 'name', text='')

                # COLUMN 02
                row = col_02.row(align=True)
                icon = 'HIDE_OFF' if obj.visible_get() else 'HIDE_ON'
                op = row.operator("camera.hide_unhide", icon=icon, text='')
                op.camera_name = obj.name
                op.cam_hide = obj.visible_get()
                op = row.prop(obj, "hide_viewport", text='')
                op = row.prop(obj, "hide_select", text='')

                if obj.get('lock'):
                    op = row.operator("cam_manager.lock_unlock_camera", icon='LOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = False
                else:
                    op = row.operator("cam_manager.lock_unlock_camera", icon='UNLOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = True

                op = row.operator("cameras.add_collection", icon='OUTLINER_COLLECTION', text='')
                op.object_name = obj.name

            else:
                layout.label(text=obj.name)

        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=obj.name)


class CAM_MANAGER_PT_camera_buttons_panel:
    '''Properties Panel in the camera data tab'''
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        engine = context.engine
        return context.camera and (engine in cls.COMPAT_ENGINES)


class CAM_MANAGER_PT_scene_panel:
    '''Properties Panel in the scene tab'''
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"


class CAM_MANAGER_PT_scene_properties(CAM_MANAGER_PT_scene_panel, bpy.types.Panel):
    bl_idname = "OBJECT_PT_camera_manager"
    bl_label = "Camera Manager"
    bl_options = {'HIDE_HEADER'}

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Camera Manager")

        scene = context.scene

        row = layout.row()
        row.prop(scene, "camera")

        row = layout.row()
        # template_list now takes two new args.
        # The first one is the identifier of the registered UIList to use (if you want only the default list,
        # with no custom draw code, use "UI_UL_list").
        layout.template_list("CAMERA_UL_cameras_scene", "", scene, "objects", scene, "camera_list_index")

        layout.separator()

        row = layout.row(align=True)
        row.operator("cam_manager.cycle_cameras_next", text="previous", icon='TRIA_LEFT')
        row.operator("cam_manager.cycle_cameras_backward", text="next", icon='TRIA_RIGHT')
        # row = layout.row()
        # row.operator("cam_manager.modal_camera_dolly_zoom", text="Dolly Zoom", icon='CON_CAMERASOLVER')
        if scene.camera:
            cam = scene.camera

            row = layout.row(align=True)
            row.prop(cam, "resolution", text="")
            op = row.operator("cam_manager.camera_resolutio_from_image", text="", icon='IMAGE_BACKGROUND')
            op.camera_name = cam.name

        row = layout.row(align=True)
        row.prop_search(scene.cam_collection, "collection", bpy.data, "collections", text='Camera Collection')
        row.operator("camera.create_collection", text='', icon='COLLECTION_NEW')

        row = layout.row()
        row.operator('cameras.all_to_collection')


class CAM_MANAGER_PT_popup(bpy.types.Panel):
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


class CAM_MANAGER_PT_camera_properties(CAM_MANAGER_PT_camera_buttons_panel, bpy.types.Panel):
    bl_label = "Camera Manager"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'}

    def draw(self, context):
        layout = self.layout

        cam = context.camera

        row = layout.row()
        row.prop(cam, "resolution")

        row = layout.row()
        op = layout.operator("cam_manager.camera_resolutio_from_image",
                             text="Resoltuion from image").camera_name = cam.name


class CameraCollectionProperty(bpy.types.PropertyGroup):
    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
    )


classes = (
    CameraCollectionProperty,
    CAMERA_UL_cameras_popup,
    CAMERA_UL_cameras_scene,
    CAM_MANAGER_PT_scene_properties,
    CAM_MANAGER_PT_popup,
    CAM_MANAGER_PT_camera_properties,
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
