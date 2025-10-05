import bpy


def filter_list(self, context):
    """
    Filter cameras from all objects for the UI list and sort them
    :param self:
    :param context:
    :return: flt_flags is a bit-flag containing the filtering and flt
             flt_neworder defines the order of all cameras
    """
    helper_funcs = bpy.types.UI_UL_list

    # Default return values.
    flt_flags = []
    flt_neworder = []

    # Get all objects from scene.
    objects = context.scene.objects

    # Create bitmask for all objects
    flt_flags = [0] * len(objects)

    # Filter by object type and name.
    filter_name = self.filter_name.lower()
    invert_filter = self.use_filter_name_reverse
    filtered_cameras = []

    for idx, obj in enumerate(objects):
        if obj.type == "CAMERA":
            name_match = not filter_name or filter_name in obj.name.lower()
            if (name_match and not invert_filter) or (not name_match and invert_filter):
                flt_flags[idx] = self.bitflag_filter_item | self.CAMERA_FILTER
                filtered_cameras.append(idx)
            else:
                flt_flags[idx] = 0
        else:
            flt_flags[idx] = 0

    # Sort filtered cameras by name.
    if self.use_order_name:
        filtered_cameras.sort(key=lambda idx: objects[idx].name.lower())
        if self.use_filter_orderby_invert:
            filtered_cameras.reverse()

    # Create new order list.
    flt_neworder = filtered_cameras + [idx for idx in range(len(objects)) if idx not in filtered_cameras]

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

    use_filter_name_reverse: bpy.props.BoolProperty(
        name="Reverse Name",
        default=False,
        options=set(),
        description="Reverse name filtering",
    )

    # This allows us to have mutually exclusive options, which are also all disable-able!
    def _gen_order_update(name1, name2):
        def _u(self, ctxt):
            if (getattr(self, name1)):
                setattr(self, name2, False)

        return _u

    use_order_name: bpy.props.BoolProperty(
        name="Name", default=False, options=set(),
        description="Sort groups by their name (case-insensitive)",
        update=_gen_order_update("use_order_name", "use_order_importance"),
    )
    use_order_importance: bpy.props.BoolProperty(
        name="Importance",
        default=False,
        options=set(),
        description="Sort groups by their average weight in the mesh",
        update=_gen_order_update("use_order_importance", "use_order_name"),
    )

    def draw_filter(self, context, layout):
        # Nothing much to say here, it's usual UI code...
        row = layout.row()

        subrow = row.row(align=True)
        subrow.prop(self, "filter_name", text="")
        icon = 'ARROW_LEFTRIGHT'
        subrow.prop(self, "use_filter_name_reverse", text="", icon=icon)

    def filter_items(self, context, data, propname):
        flt_flags, flt_neworder = filter_list(self, context)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        obj = item
        cam = item.data

        # draw_item must handle the three layout types. Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The latter also enables ctrl-click rename.
            # We use icon_value of label, as our given icon is an integer value, not an enum ID.
            # Note "data" names should never be translated!
            if obj.type == 'CAMERA':

                split = layout.split(factor=0.6)
                split_left = split.column().split(factor=0.45)
                # Camera name
                col_01 = split_left.column()
                col_02 = split_left.column()
                split_right = split.column().split(factor=0.5)
                col_03 = split_right.column()
                split_right_02 = split_right.split(factor=0.5)
                col_04 = split_right_02.column()
                col_05 = split_right_02.column()

                ###### Col01 #####
                # Camera name and visibility

                row = col_01.row(align=True)
                icon = 'VIEW_CAMERA' if obj == bpy.context.scene.camera else 'FORWARD'
                op = row.operator("cam_manager.change_scene_camera", text='', icon=icon)
                op.camera_name = obj.name
                op.switch_to_cam = False
                row.prop(obj, 'name', text='')

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

                ###### Col02 #####
                row = col_02.row()
                c = row.column(align=True)
                c.prop(cam, 'lens', text='')
                c.prop(cam, 'angle', text='')
                c = row.column(align=True)
                c.prop(cam, 'resolution_overwrite')
                c = row.column(align=True)
                if not cam.resolution_overwrite:
                    c.enabled = False
                c.prop(cam, "resolution", text="")
                op = row.operator("cam_manager.camera_resolutio_from_image", text="", icon='IMAGE_BACKGROUND')
                op.camera_name = cam.name
                c = row.column(align=True)
                c.prop(cam, "clip_start", text="")
                c.prop(cam, "clip_end", text="")

                ###### Col03 #####
                row = col_03.row(align=True)
                row.prop_search(cam, "world", bpy.data, "worlds", text='')
                row.prop(cam, 'exposure', text='EXP')

                ###### Col04 #####
                row = col_04.row(align=True)
                op = row.operator("cameras.add_collection", icon='OUTLINER_COLLECTION')
                op.object_name = obj.name

                ###### Col05 #####
                row = col_05.row(align=True)
                row.prop(cam, "slot")
                op = row.operator('cameras.custom_render', text='', icon='RENDER_STILL')
                op.camera_name = obj.name


            else:
                layout.label(text=obj.name)

        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=obj.name)


class CAMERA_UL_cameras_scene(bpy.types.UIList):
    """UI list showing all cameras with associated resolution. The resolution can be changed directly from this list"""
    CAMERA_FILTER = 1 << 0

    use_filter_name_reverse: bpy.props.BoolProperty(
        name="Reverse Name",
        default=False,
        options=set(),
        description="Reverse name filtering",
    )

    # This allows us to have mutually exclusive options, which are also all disable-able!
    def _gen_order_update(name1, name2):
        def _u(self, ctxt):
            if (getattr(self, name1)):
                setattr(self, name2, False)

        return _u

    use_order_name: bpy.props.BoolProperty(
        name="Name", default=False, options=set(),
        description="Sort groups by their name (case-insensitive)",
        update=_gen_order_update("use_order_name", "use_order_importance"),
    )
    use_order_importance: bpy.props.BoolProperty(
        name="Importance",
        default=False,
        options=set(),
        description="Sort groups by their average weight in the mesh",
        update=_gen_order_update("use_order_importance", "use_order_name"),
    )

    def draw_filter(self, context, layout):
        # Nothing much to say here, it's usual UI code...
        row = layout.row()

        subrow = row.row(align=True)
        subrow.prop(self, "filter_name", text="")
        icon = 'ARROW_LEFTRIGHT'
        subrow.prop(self, "use_filter_name_reverse", text="", icon=icon)

    def filter_items(self, context, data, propname):
        flt_flags, flt_neworder = filter_list(self, context)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        obj = item
        cam = item.data

        # draw_item must handle the three layout types. Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The latter also enables ctrl-click rename.
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

                # Checkbox for selecting the collection for export
                row.prop(cam, "render_selected", text="")

                # Change icon for already active cam
                icon = 'VIEW_CAMERA' if obj == bpy.context.scene.camera else 'FORWARD'
                op = row.operator("cam_manager.change_scene_camera", text='', icon=icon)
                op.camera_name = obj.name
                op.switch_to_cam = False
                row.prop(obj, 'name', text='')

                # COLUMN 02
                row = col_02.row(align=True)

                if obj.get('lock'):
                    op = row.operator("cam_manager.lock_unlock_camera", icon='LOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = False
                else:
                    op = row.operator("cam_manager.lock_unlock_camera", icon='UNLOCKED', text='')
                    op.camera_name = obj.name
                    op.cam_lock = True

                row = row.row(align=True)

                row.prop(cam, 'slot', text='')
                op = row.operator('cameras.custom_render', text='', icon='RENDER_STILL')
                op.camera_name = obj.name


            else:
                layout.label(text=obj.name)

        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=obj.name)


class UIListDropdownMenu(bpy.types.Menu):
    bl_label = "Camera List Operators"
    bl_idname = "OBJECT_MT_camera_list_dropdown_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("cam_manager.select_all_cameras", text='Select All', icon='CHECKBOX_HLT').invert = False
        layout.operator("cam_manager.select_all_cameras", text='Select None', icon='CHECKBOX_DEHLT').invert = True


classes = (
    CAMERA_UL_cameras_popup,
    CAMERA_UL_cameras_scene,
    UIListDropdownMenu,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
