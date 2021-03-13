import bpy
from bpy.app.handlers import persistent

@persistent
def PostRender(self):
    bpy.data.images['Render Result'].render_slots.active_index += 1
    bpy.data.images['Render Result'].render_slots.active_index %= 7

bpy.app.handlers.render_complete.append(PostRender)