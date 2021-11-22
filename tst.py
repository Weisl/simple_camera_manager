#Script to get vertices from Mesh

import bpy
import bmesh

data = bpy.context.object.data

print('')

bm = bmesh.from_edit_mesh(data)
tuple = ()
for e in bm.edges:
    tuple += ((e.verts[0].co.x, e.verts[0].co.y, e.verts[0].co.z),(e.verts[1].co.x, e.verts[1].co.y, e.verts[1].co.z))

print(str(tuple))