"""Convert a Mixamo FBX (character + animation) to a GLB for three.js.

Run:  blender -b --factory-startup -P fbx_to_glb.py -- <in.fbx> <out.glb> [clip_name]

The animation clip is renamed to clip_name (default: file name) so the game
can find it by name. Prints bone names and mesh size for checking.
"""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
clip = argv[2] if len(argv) > 2 else os.path.splitext(os.path.basename(src))[0]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src, automatic_bone_orientation=False)

for i, act in enumerate(bpy.data.actions):
    act.name = clip if i == 0 else f"{clip}_{i}"

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if arm.animation_data is None:
    arm.animation_data_create()
if bpy.data.actions:
    arm.animation_data.action = bpy.data.actions[0]

bpy.ops.export_scene.gltf(
    filepath=dst,
    export_format="GLB",
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_skins=True,
    export_morph=False,
    export_yup=True,
)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for o in meshes:
    mats = [(s.material.name if s.material else None) for s in o.material_slots]
    print("INFO mesh", o.name, [round(d, 2) for d in o.dimensions], mats)
print("INFO arm scale", [round(s, 3) for s in arm.scale], "bones", [b.name for b in arm.data.bones][:65])
print("DONE", dst, os.path.getsize(dst))
