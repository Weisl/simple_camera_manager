import bpy


def make_collection(collection_name, parent_collection):
    '''
    return existing collection if a collection with the according name exists, otherwise return a newly created one
    :param collection_name:
    :param parent_collection:
    :return:
    '''

    if collection_name in bpy.data.collections:
        col = bpy.data.collections[collection_name]
    else:
        col = bpy.data.collections.new(collection_name)
        parent_collection.children.link(col)
    return col


def moveToCollection(ob, collection):
    '''Moves an object to another collection'''
    ob_old_coll = ob.users_collection  # list of all collection the obj is in
    for col in ob_old_coll:  # unlink from all  precedent obj collections
        col.objects.unlink(ob)
    if ob.name not in collection.objects:
        collection.objects.link(ob)
    return ob


def cycleCamera(context, direction):
    '''Change the active camera to the previous or next camera one in the camera list'''
    scene = context.scene
    cam_objects = [ob for ob in scene.objects if ob.type == 'CAMERA']

    if len(cam_objects) == 0:
        return False

    try:
        idx = cam_objects.index(scene.camera)
        new_idx = (idx + 1 if direction == 'FORWARD' else idx - 1) % len(cam_objects)
    except ValueError:
        new_idx = 0

    bpy.ops.utilites.change_scene_camera(camera_name=cam_objects[new_idx].name)
    # scene.camera = cam_objects[new_idx]
    return True


def lock_camera(obj, lock):
    '''Locks or unlocks all transformation attributes of the camera. It further adds a custom property'''
    obj.lock_location[0] = lock
    obj.lock_location[1] = lock
    obj.lock_location[2] = lock

    obj.lock_rotation[0] = lock
    obj.lock_rotation[1] = lock
    obj.lock_rotation[2] = lock

    obj.lock_scale[0] = lock
    obj.lock_scale[1] = lock
    obj.lock_scale[2] = lock
    obj['lock'] = lock


class LockCameras(bpy.types.Operator):
    """Operator to lock and unlocl all camera transforms"""
    bl_idname = "utilities.lock_unlcok_camera"
    bl_label = "Lock/Unlock Camera"
    bl_description = "Lock or unlock location, rotation and scaling for a camera"

    camera_name: bpy.props.StringProperty()
    cam_lock: bpy.props.BoolProperty(name="lock", default=True)

    def execute(self, context):
        if self.camera_name and bpy.data.objects[self.camera_name]:
            obj = bpy.data.objects[self.camera_name]
            lock_camera(obj, self.cam_lock)

        return {'FINISHED'}


class VIEW3D_OT_cycle_cameras_next(bpy.types.Operator):
    """Cycle through available cameras"""
    bl_idname = "utilities.cycle_cameras_next"
    bl_label = "Next Camera"
    bl_description = ""
    bl_options = {'REGISTER'}

    direction: bpy.props.EnumProperty(
        name="Direction",
        items=(
            ('FORWARD', "Forward", "Next camera (alphabetically)"),
            ('BACKWARD', "Backward", "Previous camera (alphabetically)"),
        ),
        default='FORWARD'
    )

    def execute(self, context):
        if cycleCamera(context, self.direction):
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


class CreateCollectionOperator(bpy.types.Operator):
    """Creates a new collection"""
    bl_idname = "camera.create_collection"
    bl_label = "Create Collection"
    bl_options = {'REGISTER'}

    collection_name: bpy.props.StringProperty(name='Name', default='Cameras')

    def execute(self, context):
        parent_collection = context.scene.collection
        collection_name = self.collection_name
        make_collection(collection_name, parent_collection)
        return {'FINISHED'}


class VIEW3D_OT_cycle_cameras_backward(bpy.types.Operator):
    """Changes active camera to previous camera from Camera list"""
    bl_idname = "utilities.cycle_cameras_backward"
    bl_label = "Previous Cameras"
    bl_description = "Change active camera to previous camera"
    bl_options = {'REGISTER'}

    direction: bpy.props.EnumProperty(
        name="Direction",
        items=(
            ('FORWARD', "Forward", "Next camera (alphabetically)"),
            ('BACKWARD', "Backward", "Previous camera (alphabetically)"),
        ),
        default='BACKWARD'
    )

    def execute(self, context):
        if cycleCamera(context, self.direction):
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


class ResolutionFromBackgroundImg(bpy.types.Operator):
    """Sets camera resolution based on first background image assigned to the camera."""
    bl_idname = "utilites.camera_resolutio_from_image"
    bl_label = "Resolution from Background"
    bl_description = "Set the camera resolution to the camera background image"

    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.camera_name and bpy.data.cameras[self.camera_name]:
            camera = bpy.data.cameras[self.camera_name]

            if len(bpy.data.cameras[self.camera_name].background_images) > 0:
                resolution = camera.background_images[0].image.size
                camera.resolution = resolution
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, 'Camera has no background image')
                return {'CANCELLED'}

        self.report({'WARNING'}, 'Not valid camera')
        return {'CANCELLED'}


class Hide_Unhide_Camera(bpy.types.Operator):
    """Hides or unhides a camera"""
    bl_idname = "camera.hide_unhide"
    bl_label = "Hide/Unhide Camera"
    bl_description = "Hide or unhide the camera"

    camera_name: bpy.props.StringProperty()
    cam_hide: bpy.props.BoolProperty(name="hide", default=True)

    def execute(self, context):
        if self.camera_name and bpy.data.objects[self.camera_name]:
            obj = bpy.data.objects[self.camera_name]
            obj.hide_set(self.cam_hide)
        return {'FINISHED'}


class ChangeCamera(bpy.types.Operator):
    """Set camera as scene camera and update the resolution accordingly. The camera is set as active object and selected."""
    bl_idname = "utilites.change_scene_camera"
    bl_label = "Set active Camera"
    bl_description = "Set the active camera"

    camera_name: bpy.props.StringProperty()
    switch_to_cam: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        scene = context.scene
        if self.camera_name and scene.objects[self.camera_name]:
            camera = scene.objects[self.camera_name]

            if camera.data.resolution:
                resolution = camera.data.resolution
                scene.render.resolution_x = resolution[0]
                scene.render.resolution_y = resolution[1]

            if camera.data.world.world_material:
                try:
                    world = camera.data.world.world_material
                    bpy.context.scene.world = world
                except KeyError:
                    pass

            scene.camera = camera

            context.view_layer.objects.active = camera
            bpy.ops.object.select_all(action='DESELECT')
            camera.select_set(True)

            objectlist = list(bpy.context.scene.objects)
            idx = objectlist.index(camera)

            if self.switch_to_cam:
                if context.area.type == 'VIEW_3D':
                    bpy.context.screen.areas.spaces[0].region_3d.view_perspective = 'CAMERA'
            scene.camera_list_index = idx

        return {'FINISHED'}


class Camera_add_collection(bpy.types.Operator):
    """Moves a camera to a user collection"""
    bl_idname = "cameras.add_collection"
    bl_label = "To Collection"
    bl_description = "Move the camera to a specified collection"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene

        if not scene.cam_collection.collection:
            self.report({'WARNING'}, 'Please specify a collection')
            return {'CANCELLED'}

        if self.object_name and scene.objects[self.object_name]:
            camera = scene.objects[self.object_name]
            cam_collection = scene.cam_collection.collection
            moveToCollection(camera, cam_collection)

        return {'FINISHED'}


class All_Cameras_add_collection(bpy.types.Operator):
    """Moves a camera to a user collection"""
    bl_idname = "cameras.all_to_collection"
    bl_label = "Move all to collection "
    bl_description = "Move all cameras to a specified collection"

    def execute(self, context):
        scene = context.scene

        if not scene.cam_collection.collection:
            self.report({'WARNING'}, 'Please specify a collection')
            return {'CANCELLED'}
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA':
                cam_collection = scene.cam_collection.collection
                moveToCollection(obj, cam_collection)

        return {'FINISHED'}


def filter_list(self, context):
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

        # draw_item must handle the three layout types... Usually 'DEFAULT' and 'COMPACT' can share the same code.
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
                op = row.operator("utilites.change_scene_camera", text='', icon=icon)
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
                    op = row.operator("utilities.lock_unlcok_camera", icon='LOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = False
                else:
                    op = row.operator("utilities.lock_unlcok_camera", icon='UNLOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = True

                # #COLUMN 03 Lens and resolution
                row = col_02.row()
                c = row.column(align=True)
                c.prop(cam, 'lens', text='')
                c = row.column(align=True)
                c.prop(cam, "resolution", text="")
                op = row.operator("utilites.camera_resolutio_from_image", text="", icon='IMAGE_BACKGROUND')
                op.camera_name = cam.name
                c = row.column(align=True)
                c.prop(cam, "clip_start", text="")
                c.prop(cam, "clip_end", text="")

                row = col_03.row(align=True)
                row.prop_search(cam.world, "world_material", bpy.data, "worlds", text='')

                row = col_04.row(align=True)
                op = row.operator("cameras.add_collection", icon='OUTLINER_COLLECTION')
                op.object_name = obj.name

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

        # draw_item must handle the three layout types... Usually 'DEFAULT' and 'COMPACT' can share the same code.
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
                op = row.operator("utilites.change_scene_camera", text='', icon=icon)
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
                    op = row.operator("utilities.lock_unlcok_camera", icon='LOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = False
                else:
                    op = row.operator("utilities.lock_unlcok_camera", icon='UNLOCKED', text='')
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


class WorldMaterialProperty(bpy.types.PropertyGroup):
    world_material: bpy.props.PointerProperty(
        name="World",
        type=bpy.types.World,
    )


def resolution_update_func(self, context):
    print("ENTERED" + bpy.context.scene.camera.name + " " + self.name)
    if bpy.context.scene.camera.data.name == self.name:
        bpy.context.scene.render.resolution_x = self.resolution[0]
        bpy.context.scene.render.resolution_y = self.resolution[1]


def world_update_funce(self, context):
    if bpy.context.scene.camera.data.name == self.name:
        bpy.context.scene.world = self.world.world_material


def world_set_func(self, value):
    return


classes = (
    Camera_add_collection,
    CreateCollectionOperator,
    WorldMaterialProperty,
    CAMERA_UL_cameras_popup,
    CAMERA_UL_cameras_scene,
    ResolutionFromBackgroundImg,
    ChangeCamera,
    VIEW3D_OT_cycle_cameras_next,
    VIEW3D_OT_cycle_cameras_backward,
    LockCameras,
    Hide_Unhide_Camera,
    All_Cameras_add_collection
)


def register():
    scene = bpy.types.Scene
    scene.camera_list_index = bpy.props.IntProperty(name="Index for lis one", default=0)

    # data stored in camera
    cam = bpy.types.Camera
    cam.resolution = bpy.props.IntVectorProperty(name='Resolution', description='', default=(1920, 1080),
                                                 min=4, max=2 ** 31 - 1, soft_min=800, soft_max=8096,
                                                 subtype='COORDINATES', size=2, update=resolution_update_func, get=None,
                                                 set=None)

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    # The PointerProperty has to be after registering the classes to know about the custom property type
    cam.world = bpy.props.PointerProperty(name="World", type=WorldMaterialProperty, update=world_update_funce)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    cam = bpy.types.Camera
    del cam.resolution
