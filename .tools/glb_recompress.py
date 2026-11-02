"""Re-save a (Draco-compressed) GLB as a plain GLB that three.js loads without
the Draco decoder. Vertex colours and materials are kept.

Run:  blender -b --factory-startup -P glb_recompress.py -- <in.glb> <out.glb>
"""
import os
import sys

import bpy

src, dst = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_draco_mesh_compression_enable=False,
                          export_vertex_color="ACTIVE", export_apply=True, export_animations=False)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
print("DONE", os.path.basename(dst), os.path.getsize(dst), "tris", tris)
