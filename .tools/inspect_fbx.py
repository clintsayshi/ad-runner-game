"""Print what an FBX holds: meshes, armature bones, animation clips.

Run:  blender -b --factory-startup -P inspect_fbx.py -- <file.fbx>
"""
import sys

import bpy

src = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
print("INFO meshes", len(meshes), "tris", tris, "images", len(bpy.data.images))
for a in arms:
    bones = [b.name for b in a.data.bones]
    fingers = [b for b in bones if "Index" in b or "Middle" in b]
    print("INFO armature", a.name, "bones", len(bones), "finger_bones", len(fingers))
for act in bpy.data.actions:
    print("INFO action", act.name, "frames", tuple(int(x) for x in act.frame_range))
