import bpy

class CAM_MANAGER_BaseOperator:
    _cameras = []
    _original_camera = None
    _original_output_path = None
    _current_index = 0
    _rendering = False

    def set_camera_settings(self, context, camera):
        print(f"Setting camera settings for: {camera.name}")
        bpy.ops.cam_manager.change_scene_camera(camera_name=camera.name, switch_to_cam=True)

    def cleanup(self, context, aborted=False):
        scene = context.scene
        print("Cleanup called")
        # Restore the original camera and output path
        if self._original_camera:
            bpy.ops.cam_manager.change_scene_camera(camera_name=self._original_camera.name, switch_to_cam=True)
        if self._original_output_path:
            scene.render.filepath = self._original_output_path

        # Remove handlers
        if self.render_complete_handler in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self.render_complete_handler)

        if aborted:
            self.report({'INFO'}, "Rendering aborted")
        else:
            self.report({'INFO'}, f"Rendering completed. {self._current_index} cameras rendered.")

    def initialize(self, context):
        scene = context.scene
        self._original_camera = scene.camera
        self._original_output_path = scene.render.filepath
        self._cameras = [obj for obj in bpy.data.objects if
                         obj.type == 'CAMERA' and getattr(obj.data, "render_selected", False)]

        if not self._cameras:
            self.report({'ERROR'}, "No cameras selected for rendering")
            return False

        print(f"Cameras to render: {[cam.name for cam in self._cameras]}")
        self.report({'INFO'}, f"Cameras to render: {[cam.name for cam in self._cameras]}")

        return True

class CAM_MANAGER_OT_multi_camera_rendering_modal(CAM_MANAGER_BaseOperator, bpy.types.Operator):
    """Render all selected cameras using modal operator"""
    bl_idname = "cam_manager.multi_camera_rendering_modal"
    bl_label = "Render All Selected Cameras (Modal)"
    bl_options = {'REGISTER', 'UNDO'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if not self._rendering:
                if self._current_index < len(self._cameras):
                    # Set camera settings for the next render
                    camera = self._cameras[self._current_index]
                    self.set_camera_settings(context, camera)
                    # Start the next render
                    print(f"Starting render for camera: {camera.name}")
                    self.report({'INFO'}, f"Starting render for camera: {camera.name}")
                    self._rendering = True
                    bpy.ops.render.render('INVOKE_DEFAULT', write_still=True, use_viewport=False)
                else:
                    self.cleanup(context)
                    return {'FINISHED'}
        elif event.type == 'ESC':
            self.cleanup(context, aborted=True)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        if not self.initialize(context):
            return {'CANCELLED'}

        # Register the render complete handler
        bpy.app.handlers.render_complete.append(self.render_complete_handler)

        # Start the modal operator
        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)

        # Set camera settings for the first render
        if self._cameras:
            first_camera = self._cameras[0]
            self.set_camera_settings(context, first_camera)

        # Start the first render
        print(f"Starting first render for camera: {first_camera.name}")
        self.report({'INFO'}, f"Starting first render for camera: {first_camera.name}")
        self._rendering = True
        bpy.ops.render.render('INVOKE_DEFAULT', write_still=True, use_viewport=False)

        # Instruct the user to open the console for detailed feedback
        self.report({'INFO'}, "Open the console (Window > Toggle System Console) to see detailed feedback.")

        return {'RUNNING_MODAL'}

    def render_complete_handler(self, scene, depsgraph):
        print(f"Render complete for camera: {self._cameras[self._current_index].name}")
        self.report({'INFO'}, f"Render complete for camera: {self._cameras[self._current_index].name}")
        self._rendering = False
        self._current_index += 1

        if self._current_index < len(self._cameras):
            # Add a delay before starting the next render
            bpy.app.timers.register(self.start_next_render, first_interval=1.0)
        else:
            # Add a delay before final cleanup
            bpy.app.timers.register(lambda: self.final_cleanup(bpy.context), first_interval=2.0)

    def start_next_render(self):
        if self._current_index < len(self._cameras):
            # Set camera settings for the next render
            camera = self._cameras[self._current_index]
            self.set_camera_settings(bpy.context, camera)
            print(f"Setting camera: {camera.name}")
            self.report({'INFO'}, f"Setting camera: {camera.name}")
            # Trigger the next render
            self._rendering = True
            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True, use_viewport=False)

    def final_cleanup(self, context):
        self.cleanup(context)
        # Ensure the handler is removed after the last render
        if self.render_complete_handler in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self.render_complete_handler)

class CAM_MANAGER_OT_multi_camera_rendering_handlers(CAM_MANAGER_BaseOperator, bpy.types.Operator):
    """Render all selected cameras using handlers"""
    bl_idname = "cam_manager.multi_camera_rendering_handlers"
    bl_label = "Render All Selected Cameras (Handlers)"
    bl_options = {'REGISTER', 'UNDO'}

    def render_complete_handler(self, scene, depsgraph):
        print(f"Render complete for camera: {self._cameras[self._current_index].name}")
        self.report({'INFO'}, f"Render complete for camera: {self._cameras[self._current_index].name}")
        self._rendering = False
        self._current_index += 1

        if self._current_index < len(self._cameras):
            # Add a delay before starting the next render
            bpy.app.timers.register(self.start_next_render, first_interval=1.0)
        else:
            # Add a delay before final cleanup
            bpy.app.timers.register(lambda: self.final_cleanup(bpy.context), first_interval=2.0)

    def start_next_render(self):
        if self._current_index < len(self._cameras):
            # Set camera settings for the next render
            camera = self._cameras[self._current_index]
            self.set_camera_settings(bpy.context, camera)
            print(f"Setting camera: {camera.name}")
            self.report({'INFO'}, f"Setting camera: {camera.name}")
            # Trigger the next render
            self._rendering = True
            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True, use_viewport=False)

    def final_cleanup(self, context):
        self.cleanup(context)
        # Ensure the handler is removed after the last render
        if self.render_complete_handler in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self.render_complete_handler)

    def execute(self, context):
        if not self.initialize(context):
            return {'CANCELLED'}

        # Register the render complete handler
        bpy.app.handlers.render_complete.append(self.render_complete_handler)

        try:
            # Set camera settings for the first render
            if self._cameras:
                first_camera = self._cameras[0]
                self.set_camera_settings(context, first_camera)

            # Start the first render
            print(f"Starting first render for camera: {first_camera.name}")
            self.report({'INFO'}, f"Starting first render for camera: {first_camera.name}")
            self._rendering = True
            bpy.ops.render.render('INVOKE_DEFAULT', write_still=True, use_viewport=False)
        except Exception as e:
            self.report({'ERROR'}, f"Rendering failed: {e}")
            self.cleanup(context, aborted=True)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

classes = (
    CAM_MANAGER_OT_multi_camera_rendering_modal,
    CAM_MANAGER_OT_multi_camera_rendering_handlers,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
