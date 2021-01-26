import math

import bgl
import blf
import bpy
import gpu
from bpy.props import IntProperty, FloatProperty
from gpu_extras.batch import batch_for_shader
from mathutils import Vector


def make_collection(context, collection_name, parent_collection):
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


def distance_vec(point1: Vector, point2: Vector):
    """Calculate distance between two points."""
    return (point2 - point1).length


def draw_callback_px(self, context):
    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
    blf.position(font_id, 15, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "FOV" + str(math.degrees(self.current_camera_fov)))

    blf.position(font_id, 15, 60, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Focal Length" + str(self.camera_focal_length))

    blf.position(font_id, 15, 90, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "DISTANCE" + str(self.distance))

    scene = context.scene
    blf.position(font_id, 15, 120, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Mouse Sensitivity" + str(scene.dolly_zoom_sensitivity))

    # 50% alpha, 2 pixel width line
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(2)
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": self.mouse_path})
    shader.bind()
    shader.uniform_float("color", (0.0, 0.0, 0.0, 0.5))
    batch.draw(shader)

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)


class CAMERA_OT_dolly_zoom(bpy.types.Operator):
    """Dolly Zoom"""
    bl_idname = "utilities.modal_camera_dolly_zoom"
    bl_label = "Dolly Zoom"

    # Initial mouse position
    mouse_initial_x: IntProperty()

    # camera position. Only using Y Axis for now
    camera_location: FloatProperty()

    # FOV changes
    current_camera_fov: FloatProperty()
    initial_camera_fov: FloatProperty()

    # target object
    target_width: FloatProperty(default=4, name="Width")

    def modal(self, context, event):
        '''Calculate the FOV from the changed location to the target object '''

        camera = self.camera
        cameraObj = self.cameraObj

        scene = context.scene
        # cancel operator
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cameraObj.location.y = self.camera_location_initial
            return {'CANCELLED'}

        # apply operator
        elif event.type == 'LEFTMOUSE':
            return {'FINISHED'}



        elif event.type == 'UP_ARROW':
            # Increase Mouse sensitivity

            scene.dolly_zoom_sensitivity *= 1.5

        elif event.type == 'DOWN_ARROW':
            # Decrease Mouse Sensitivity
            scene.dolly_zoom_sensitivity /= 1.5

        elif event.type == 'MOUSEMOVE':

            # calculate mouse movement and offset camera
            delta = self.mouse_initial_x - event.mouse_x

            # Camera offset in y axis
            # cameraObj.location.y = self.camera_location + delta * self.mouse_sensitivity

            # one blender unit in x-direction
            vec = Vector((0.0, 0.0, delta * scene.dolly_zoom_sensitivity))

            # get world matrix and invert
            inv = cameraObj.matrix_world.copy()
            inv.invert()

            # vec aligned to local axis in Blender 2.8+
            vec_rot = vec @ inv

            cameraObj.location = cameraObj.location + vec_rot

            # get camera world position and target position
            cam_pos = self.cameraObj.matrix_world.to_translation()
            cam_vector = Vector(cam_pos)
            target_pos = self.target

            distance = distance_vec(cam_vector, target_pos)
            self.distance = distance
            print("distance = " + str(distance))

            # Dolly Zoom computation
            field_of_view = 2 * math.atan(self.target_width / distance)

            # Set camera field of view and
            camera.angle = field_of_view
            self.current_camera_fov = field_of_view
            self.camera_focal_length = camera.lens

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.scene.camera:
            camera = context.scene.camera

            self.cameraObj = camera
            self.camera = camera.data

            self.target = Vector((0.0, 0.0, 0.0))
            self.mouse_initial_x = event.mouse_x

            self.camera_location_initial = camera.location.y
            self.camera_location = camera.location.y

            # debug values
            self.current_camera_fov = camera.data.angle
            self.distance = 0

            # the arguments we pass the the callback
            args = (self, context)
            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:

            self.report({'WARNING'}, "No scene camera assigned")
            return {'CANCELLED'}


def cycleCamera(context, direction):
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
    obj.lock_location[0] = lock
    obj.lock_location[1] = lock
    obj.lock_location[2] = lock

    obj.lock_rotation[0] = lock
    obj.lock_rotation[1] = lock
    obj.lock_rotation[2] = lock

    obj.lock_scale[0] = lock
    obj.lock_scale[1] = lock
    obj.lock_scale[2] = lock


class LockCameras(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "utilities.lock_unlcok_camera"
    bl_label = "Lock/Unlock Camera"

    camera_name: bpy.props.StringProperty()
    cam_lock: bpy.props.BoolProperty(name="lock", default=True)

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        if self.camera_name and bpy.data.objects[self.camera_name]:
            obj = bpy.data.objects[self.camera_name]
            lock_camera(obj, self.cam_lock)

        return {'FINISHED'}


class VIEW3D_OT_cycle_cameras_next(bpy.types.Operator):
    """Cycle through available cameras"""
    bl_idname = "utilities.cycle_cameras_next"
    bl_label = "Next Camera"
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


class VIEW3D_OT_cycle_cameras_backward(bpy.types.Operator):
    """Cycle through available cameras"""
    bl_idname = "utilities.cycle_cameras_backward"
    bl_label = "Previous Cameras"
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
    """Tooltip"""
    bl_idname = "camera.hide_unhide"
    bl_label = "Hide Unhide Camera"

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
    bl_label = "Change Scene Camera"

    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        if self.camera_name and scene.objects[self.camera_name]:
            camera = scene.objects[self.camera_name]

            if camera.data.resolution:
                resolution = camera.data.resolution
                scene.render.resolution_x = resolution[0]
                scene.render.resolution_y = resolution[1]

            scene.camera = camera

            context.view_layer.objects.active = camera
            bpy.ops.object.select_all(action='DESELECT')
            camera.select_set(True)

            objectlist = list(bpy.context.scene.objects)
            idx = objectlist.index(camera)

            scene.camera_list_index = idx

        return {'FINISHED'}


class Camera_add_collection(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "cameras.add_collection"
    bl_label = "Simple Object Operator"

    camera_name: bpy.props.StringProperty()
    collection_name: bpy.props.StringProperty()

    def execute(self, context):

        return {'FINISHED'}


class CAMERA_UL_cameraslots(bpy.types.UIList):
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

        helper_funcs = bpy.types.UI_UL_list

        # Default return values.
        flt_flags = []
        flt_neworder = []

        # Get all objects from scene.
        objects = []
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

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        obj = item
        cam = item.data

        # draw_item must handle the three layout types... Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type == 'DEFAULT':
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
            # We use icon_value of label, as our given icon is an integer value, not an enum ID.
            # Note "data" names should never be translated!
            if obj.type == 'CAMERA':
                c = layout.column()
                row = c.row()

                split = row.split(factor=0.05)
                c = split.column()
                op = c.operator("utilites.change_scene_camera", text='', icon='FORWARD')
                op.camera_name = obj.name

                split = split.split(factor=0.3)
                c = split.column()
                c.prop(obj, 'name', text='')

                split = split.split(factor=0.2)
                c = split.column()
                c.prop(cam, 'lens', text='')

                split = split.split(factor=0.5, align=True)
                c = split.column(align=True)
                c.prop(cam, "resolution", text="")

                split = split.split()
                c = split.column()
                row = c.row(align=True)

                icon = 'HIDE_OFF' if obj.visible_get() else 'HIDE_ON'

                op = row.operator("camera.hide_unhide", icon=icon, text='')
                op.camera_name = obj.name
                op.cam_hide = obj.visible_get()

                op = row.prop(obj, "hide_viewport", text='')
                op = row.prop(obj, "hide_select", text='')

                op = row.operator("utilities.lock_unlcok_camera", icon='LOCKED', text='')
                op.camera_name = obj.name
                op.cam_lock = True
                op = row.operator("utilities.lock_unlcok_camera", icon='UNLOCKED', text='')
                op.camera_name = obj.name
                op.cam_lock = False

                op = row.operator("utilites.camera_resolutio_from_image", text="",
                                  icon='IMAGE_BACKGROUND').camera_name = cam.name

            else:
                layout.label(text=obj.name)

        elif self.layout_type == 'COMPACT':
            if obj.type == 'CAMERA':
                c = layout.column()
                row = c.row()

                split = row.split(factor=0.1)
                c = split.column()
                op = c.operator("utilites.change_scene_camera", text='', icon='FORWARD')
                op.camera_name = obj.name

                split = split.split(factor=0.6)
                c = split.column()
                c.prop(obj, 'name', text='')

                split = split.split(factor=0.8)
                c = split.column()
                c.prop(cam, "resolution", text="")

                split = split.split()
                c = split.column()
                op = c.operator("utilites.camera_resolutio_from_image", text="",
                                icon='IMAGE_BACKGROUND').camera_name = cam.name
            else:
                layout.label(text=obj.name)

        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=obj.name)


classes = (
    CAMERA_UL_cameraslots,
    ResolutionFromBackgroundImg,
    ChangeCamera,
    VIEW3D_OT_cycle_cameras_next,
    VIEW3D_OT_cycle_cameras_backward,
    CAMERA_OT_dolly_zoom,
    LockCameras,
    Hide_Unhide_Camera
)


def update_func(self, context):
    print("ENTERED" + bpy.context.scene.camera.name + " " + self.name)
    if bpy.context.scene.camera.data.name == self.name:
        bpy.context.scene.render.resolution_x = self.resolution[0]
        bpy.context.scene.render.resolution_y = self.resolution[1]


def register():
    scene = bpy.types.Scene
    scene.camera_list_index = bpy.props.IntProperty(name="Index for lis one", default=0)

    # properties stored in blender scene
    scene.dolly_zoom_sensitivity: FloatProperty(default=0.0008, name="Mouse Sensitivity")

    # data stored in camera
    cam = bpy.types.Camera
    cam.resolution = bpy.props.IntVectorProperty(name='Resolution', description='', default=(1920, 1080),
                                                 min=4, max=2 ** 31 - 1, soft_min=800, soft_max=8096,
                                                 subtype='COORDINATES', size=2, update=update_func, get=None, set=None)

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    cam = bpy.types.Camera
    del cam.resolution

    scene = bpy.types.Scene
    del scene.dolly_zoom_sensitivity
