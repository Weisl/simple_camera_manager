import bpy
import os

cam_collection_name = 'Cameras'


def make_collection(collection_name, parent_collection):
    """
    return existing collection if a collection with the according name exists, otherwise return a newly created one

    :param collection_name: name of the newly created collection
    :param parent_collection: parent collection of the newly created collection
    :return: the newly created collection
    """

    if collection_name in bpy.data.collections:
        col = bpy.data.collections[collection_name]
    else:
        col = bpy.data.collections.new(collection_name)
        parent_collection.children.link(col)
    return col


def moveToCollection(ob, collection):
    """
    Move an object to another scene collection
    :param ob: object to move
    :param collection: collection the object is moved to
    :return: the input object
    """
    ob_old_coll = ob.users_collection  # list of all collection the obj is in
    for col in ob_old_coll:  # unlink from all  precedent obj collections
        col.objects.unlink(ob)
    if ob.name not in collection.objects:
        collection.objects.link(ob)
    return ob


def cycleCamera(context, direction):
    """
    Change the active camera to the previous or next camera one in the camera list
    :param context:
    :param direction: string with 'FORWARD' or 'BACKWARD' to define the direction
    :return: Bool for either successful or unsuccessful try
    """

    scene = context.scene
    cam_objects = [ob for ob in scene.objects if ob.type == 'CAMERA']

    if len(cam_objects) == 0:
        return False

    try:
        idx = cam_objects.index(scene.camera)
        new_idx = (idx + 1 if direction == 'FORWARD' else idx - 1) % len(cam_objects)
    except ValueError:
        new_idx = 0

    bpy.ops.cam_manager.change_scene_camera(camera_name=cam_objects[new_idx].name)
    # scene.camera = cam_objects[new_idx]
    return True


def lock_camera(obj, lock):
    """ Locks or unlocks all transformation attributes of the camera. It further adds a custom property
    :param obj: object to lock/unlock
    :param lock: bool, defining if locking or unlocking
    :return: None
    """
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


class OBJECT_OT_create_camera_from_view(bpy.types.Operator):
    """Create a new camera matching the current viewport view"""
    bl_idname = "camera.create_camera_from_view"
    bl_label = "Create Camera from View"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Create a new camera
        bpy.ops.object.camera_add()
        camera = context.object  # Ensure we get the newly created camera
        camera.name = 'ViewportCamera'
        print(f"New camera created: {camera.name} at location {camera.location}")

        # Store the original active camera
        original_camera = context.scene.camera
        print(f"Original active camera: {original_camera.name if original_camera else 'None'}")

        # Set the new camera as the active scene camera
        context.scene.camera = camera
        print(f"Set active scene camera to: {context.scene.camera.name}")

        # Get the 3D view area and region
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        # Align the new camera to the viewport view
                        with context.temp_override(area=area, region=region, scene=context.scene):
                            bpy.ops.view3d.camera_to_view()
                        print(f"New camera aligned to viewport view. Location: {camera.location}")
                        break

        # Optionally, set the camera's lens to match the viewport
        camera.data.lens = context.space_data.lens
        print(f"Camera lens set to: {camera.data.lens}")

        # Restore the original active camera
        # context.scene.camera = original_camera
        # print(f"Restored active scene camera to: {context.scene.camera.name if context.scene.camera else 'None'}")

        self.report({'INFO'}, f"Camera '{camera.name}' created from the viewport view.")
        return {'FINISHED'}


class CAM_MANAGER_OT_lock_cameras(bpy.types.Operator):
    """Operator to lock and unlock all camera transforms"""
    bl_idname = "cam_manager.lock_unlock_camera"
    bl_label = "Lock/Unlock Camera"
    bl_description = "Lock/unlock location, rotation, and scaling of a camera"

    camera_name: bpy.props.StringProperty()
    cam_lock: bpy.props.BoolProperty(name="lock", default=True)

    def execute(self, context):
        if self.camera_name and bpy.data.objects[self.camera_name]:
            obj = bpy.data.objects[self.camera_name]
            lock_camera(obj, self.cam_lock)

        return {'FINISHED'}


class CAM_MANAGER_OT_cycle_cameras_next(bpy.types.Operator):
    """Cycle through available cameras"""
    bl_idname = "cam_manager.cycle_cameras_next"
    bl_label = "Next Camera"
    bl_description = "Change the active camera to the next camera"
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


class CAM_MANAGER_OT_cycle_cameras_backward(bpy.types.Operator):
    """Changes active camera to previous camera from Camera list"""
    bl_idname = "cam_manager.cycle_cameras_backward"
    bl_label = "Previous Cameras"
    bl_description = "Change the active camera to the previous camera"
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


class CAM_MANAGER_OT_create_collection(bpy.types.Operator):
    """Creates a new collection"""
    bl_idname = "camera.create_collection"
    bl_label = "Create Camera Collection"
    bl_description = "Create a cameras collection and add it to the scene"
    bl_options = {'REGISTER'}

    collection_name: bpy.props.StringProperty(name='Name', default='')

    def execute(self, context):
        global cam_collection_name

        'use default from global variable defined at the top'
        if not self.collection_name:
            self.collection_name = cam_collection_name

        parent_collection = context.scene.collection
        collection_name = self.collection_name
        col = make_collection(collection_name, parent_collection)

        context.scene.cam_collection.collection = col
        return {'FINISHED'}


class CAM_MANAGER_OT_resolution_from_img(bpy.types.Operator):
    """Sets camera resolution based on first background image assigned to the camera."""
    bl_idname = "cam_manager.camera_resolutio_from_image"
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


class CAM_MANAGER_OT_hide_unhide_camera(bpy.types.Operator):
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


class CAM_MANAGER_OT_switch_camera(bpy.types.Operator):
    """Set camera as scene camera and update the resolution accordingly. The camera is set as active object and selected."""
    bl_idname = "cam_manager.change_scene_camera"
    bl_label = "Set active Camera"
    bl_description = "Set the active camera"

    camera_name: bpy.props.StringProperty()
    switch_to_cam: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        scene = context.scene
        if self.camera_name and scene.objects.get(self.camera_name):
            camera = scene.objects[self.camera_name]

            if camera.data.resolution:
                resolution = camera.data.resolution
                scene.render.resolution_x = resolution[0]
                scene.render.resolution_y = resolution[1]

            # if camera.data.exposure: #returns 0 when exposure = 0
            scene.view_settings.exposure = camera.data.exposure

            if camera.data.world:
                try:
                    world = camera.data.world
                    scene.world = world
                except KeyError:
                    self.report({'WARNING'}, 'World material could not be found')
                    pass

            scene.camera = camera
            context.view_layer.objects.active = camera
            bpy.ops.object.select_all(action='DESELECT')
            camera.select_set(True)

            objectlist = list(context.scene.objects)
            idx = objectlist.index(camera)

            if self.switch_to_cam:
                found_view_3d = False
                for screen in bpy.data.screens:
                    for area in screen.areas:
                        if area.type == 'VIEW_3D':
                            for space in area.spaces:
                                if space.type == 'VIEW_3D':
                                    space.region_3d.view_perspective = 'CAMERA'
                                    space.camera = camera
                                    found_view_3d = True
                                    break
                            if found_view_3d:
                                break
                    if found_view_3d:
                        break

            scene.camera_list_index = idx

            if camera.data.slot <= len(bpy.data.images['Render Result'].render_slots):
                # subtract by one to make 1 the first slot 'Slot1' and not user input 0
                bpy.data.images['Render Result'].render_slots.active_index = camera.data.slot - 1

            if scene.output_use_cam_name:
                old_path = bpy.context.scene.render.filepath
                path, basename = os.path.split(old_path)
                new_path = os.path.join(path, self.camera_name)
                bpy.context.scene.render.filepath = new_path

        return {'FINISHED'}


class CAM_MANAGER_OT_camera_to_collection(bpy.types.Operator):
    """Moves a camera to another collection"""
    bl_idname = "cameras.add_collection"
    bl_label = "To Collection"
    bl_description = "Move the camera to a another collection"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene

        if not scene.cam_collection.collection:
            global cam_collection_name

            'use default from global variable defined at the top'
            self.report({'INFO'}, 'A new camera collection was created')
            parent_collection = context.scene.collection
            scene.cam_collection.collection = make_collection(cam_collection_name, parent_collection)

        if self.object_name and scene.objects[self.object_name]:
            camera = scene.objects[self.object_name]
            cam_collection = scene.cam_collection.collection
            moveToCollection(camera, cam_collection)

        return {'FINISHED'}


class CAM_MANAGER_OT_select_active_cam(bpy.types.Operator):
    """Selects the currently active camera and sets it to be the active object"""
    bl_idname = "cameras.select_active_cam"
    bl_label = "Select active camera"

    @classmethod
    def poll(cls, context):
        return context.scene.camera is not None

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')

        cam = context.scene.camera
        cam.select_set(True)
        context.view_layer.objects.active = cam
        return {'FINISHED'}


class CAM_MANAGER_OT_all_cameras_to_collection(bpy.types.Operator):
    """Moves all camera to another collection"""
    bl_idname = "cameras.all_to_collection"
    bl_label = "All to collection "
    bl_description = "Move all cameras to a specified collection"

    def execute(self, context):
        scene = context.scene

        if not scene.cam_collection.collection:
            global cam_collection_name

            'use default from global variable defined at the top'
            self.report({'INFO'}, 'A new camera collection was created')
            parent_collection = context.scene.collection
            scene.cam_collection.collection = make_collection(cam_collection_name, parent_collection)

        for obj in bpy.data.objects:
            if obj.type == 'CAMERA':
                cam_collection = scene.cam_collection.collection
                moveToCollection(obj, cam_collection)

        return {'FINISHED'}


class CAM_MANAGER_OT_render(bpy.types.Operator):
    """Switch camera and render"""
    bl_idname = "cameras.custom_render"
    bl_label = "Render"
    bl_description = "Switch camera and start a render"

    camera_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return context.scene.camera is not None

    def execute(self, context):
        scene = context.scene
        bpy.ops.cam_manager.change_scene_camera(camera_name=self.camera_name, switch_to_cam=False)
        bpy.ops.render.render('INVOKE_DEFAULT', animation=False, write_still=scene.output_render, use_viewport=False)
        return {'FINISHED'}


def resolution_update_func(self, context):
    """
    Updating scene resolution when changing the resolution of the active camera
    :param self:
    :param context:
    :return: None
    """
    if context.scene.camera.data.name == self.name:
        context.scene.render.resolution_x = self.resolution[0]
        context.scene.render.resolution_y = self.resolution[1]


def exposure_update_func(self, context):
    """
    Updating scene exposure when changing the exposure of the active camera
    :param self:
    :param context:
    :return: None
    """

    if context.scene.camera.data.name == self.name:
        context.scene.view_settings.exposure = self.exposure


def world_update_func(self, context):
    """
    Updating the world material when changing the world material for the active camera
    :param self:
    :param context:
    :return: None
    """

    if context.scene.camera.data.name == self.name:
        context.scene.world = self.world
        self.world.use_fake_user = True

    return None


def render_slot_update_funce(self, context):
    """
    Update the render slot when changing render slot for the active camera. A new render slot will
    be created if the number is higher than the number of current render slots. The newly created
    render slots gets assigned automatically.
    :param self:
    :param context:
    :return: None
    """

    new_slot = False
    render_result = bpy.data.images['Render Result']

    # Create new slot if the input is higher than the current number of render slots
    if self.slot > len(bpy.data.images['Render Result'].render_slots):
        render_result.render_slots.new()
        new_slot = True
        self.slot = len(bpy.data.images['Render Result'].render_slots)

    if context.scene.camera.data.name == self.name:
        if new_slot:
            new_render_slot_nr = len(bpy.data.images['Render Result'].render_slots)
            render_result.render_slots.active_index = new_render_slot_nr
            self.slot = new_render_slot_nr
        else:
            # subtract by one to make 1 the first slot 'Slot1' and not user input 0
            render_result.render_slots.active_index = self.slot - 1


def update_func(self, context):
    self.show_limits = not self.show_limits
    self.show_limits = not self.show_limits


classes = (
    CAM_MANAGER_OT_camera_to_collection,
    CAM_MANAGER_OT_create_collection,
    CAM_MANAGER_OT_render,
    CAM_MANAGER_OT_resolution_from_img,
    CAM_MANAGER_OT_switch_camera,
    CAM_MANAGER_OT_cycle_cameras_next,
    CAM_MANAGER_OT_cycle_cameras_backward,
    CAM_MANAGER_OT_lock_cameras,
    CAM_MANAGER_OT_hide_unhide_camera,
    CAM_MANAGER_OT_all_cameras_to_collection,
    CAM_MANAGER_OT_select_active_cam,
    OBJECT_OT_create_camera_from_view,
)


def load_post_handler(dummy):
    """Ensure all collections have the 'use_root_object' and 'root_object' properties set."""
    for cam in bpy.data.cameras:
        if not hasattr(cam, "render_selected"):
            cam.root_object = False  # Ensure property exists


def register():
    # Register handler to ensure properties are set when loading an older .blend file
    bpy.app.handlers.load_post.append(load_post_handler)

    scene = bpy.types.Scene
    scene.camera_list_index = bpy.props.IntProperty(name="Index for lis one", default=0)

    # data stored in camera
    cam = bpy.types.Camera

    cam.resolution = bpy.props.IntVectorProperty(name='Camera Resolution', description='Camera resolution in px',
                                                 default=(1920, 1080),
                                                 min=4, soft_min=800, soft_max=8096,
                                                 subtype='COORDINATES', size=2, update=resolution_update_func, get=None,
                                                 set=None)

    cam.render_selected = bpy.props.BoolProperty(name="Select Camera",
                                                 description="Select this camera for rendering",
                                                 default=False)

    cam.exposure = bpy.props.FloatProperty(name='exposure', description='Camera exposure', default=0, soft_min=-10,
                                           soft_max=10, update=exposure_update_func)

    cam.slot = bpy.props.IntProperty(name="Slot", default=1, description='Render slot, used when rendering this camera',
                                     min=1, soft_max=15, update=render_slot_update_funce)

    cam.dolly_zoom_target_scale = bpy.props.FloatProperty(name='Target Scale', description='', default=2, min=0,
                                                          update=update_func)
    cam.dolly_zoom_target_distance = bpy.props.FloatProperty(name='Target Distance', description='', default=10, min=0,
                                                             update=update_func)

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    # The PointerProperty has to be after registering the classes to know about the custom property type
    cam.world = bpy.props.PointerProperty(update=world_update_func, type=bpy.types.World,
                                          name="World Material")  # type=WorldMaterialProperty, name="World Material", description='World material assigned to the camera',


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    cam = bpy.types.Camera

    del cam.resolution
    del cam.render_selected
    del cam.slot
    del cam.exposure
    del cam.world
