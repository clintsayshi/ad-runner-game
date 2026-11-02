"""Merge a Mixamo character + its animation FBXs into one GLB for three.js.

Run:
  blender -b --factory-startup -P mixamo_pack_to_glb.py -- <character.fbx> <out.glb> <tex_px> name=file.fbx [name=file.fbx ...]

Each animation file's action is renamed to `name` and stacked as an NLA track
on the character's armature, so the GLB carries every clip under its name.
Textures are scaled down to tex_px and stored as JPEG.
"""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
char_path, dst, tex_px = argv[0], argv[1], int(argv[2])
clips = [a.split("=", 1) for a in argv[3:]]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=char_path, automatic_bone_orientation=False)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm.name = "Hero"
for act in list(bpy.data.actions):  # the character file's own 2-frame T-pose action
    bpy.data.actions.remove(act)
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = None


def import_clip(name, path):
    before_objs = set(bpy.data.objects)
    before_acts = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False)
    new_acts = [a for a in bpy.data.actions if a not in before_acts]
    for o in [o for o in bpy.data.objects if o not in before_objs]:
        bpy.data.objects.remove(o, do_unlink=True)
    if not new_acts:
        print("WARN no action in", path)
        return None
    act = new_acts[0]
    for extra in new_acts[1:]:
        bpy.data.actions.remove(extra)
    act.name = name
    act.use_fake_user = True
    retarget_names(act)
    return act


def action_fcurves(act):
    """All F-curves of an action (Blender 4.4+ layered actions, or the legacy list)."""
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    if not out and hasattr(act, "fcurves"):
        out = list(act.fcurves)
    return out


HERO_PREFIX = next(b.name for b in arm.data.bones if b.name.endswith("Hips"))[:-len("Hips")]


def retarget_names(act):
    """Clips made on another Mixamo body use another bone prefix (mixamorig: vs
    mixamorig2:). Point every curve at this character's bones."""
    import re
    n = 0
    for fc in action_fcurves(act):
        new = re.sub(r'pose\.bones\["mixamorig\d*:', f'pose.bones["{HERO_PREFIX}', fc.data_path)
        if new != fc.data_path:
            fc.data_path = new
            n += 1
    for group in getattr(act, "groups", []):
        group.name = re.sub(r"^mixamorig\d*:", HERO_PREFIX, group.name)
    print("INFO retarget", act.name, "curves renamed", n)


for name, fname in clips:
    act = import_clip(name, fname)
    if not act:
        continue
    arm.animation_data.action = act  # binds a slot for this armature (Blender 4.4+)
    slot = getattr(arm.animation_data, "action_slot", None)
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, int(act.frame_range[0]), act)
    if slot is not None and hasattr(strip, "action_slot"):
        strip.action_slot = slot
    track.mute = True
    arm.animation_data.action = None
    print("INFO clip", name, tuple(int(x) for x in act.frame_range))

# Mixamo "nonPBR" skins plug a GLOSSINESS map into Roughness (backwards: shiny
# reads as rough) and a specular map into Specular. Use flat matte values.
for mat in bpy.data.materials:
    if not mat.node_tree:
        continue
    for node in mat.node_tree.nodes:
        if node.type != "BSDF_PRINCIPLED":
            continue
        for sock_name, value in (("Roughness", 0.78), ("Specular IOR Level", 0.3), ("Metallic", 0.0)):
            sock = node.inputs.get(sock_name)
            if sock is None:
                continue
            for link in list(sock.links):
                mat.node_tree.links.remove(link)
            sock.default_value = value

for img in bpy.data.images:
    if img.size[0] > tex_px or img.size[1] > tex_px:
        w, h = img.size
        s = tex_px / max(w, h)
        img.scale(max(1, int(w * s)), max(1, int(h * s)))

bpy.ops.export_scene.gltf(
    filepath=dst,
    export_format="GLB",
    export_image_format="JPEG",
    export_jpeg_quality=85,
    export_animations=True,
    export_animation_mode="NLA_TRACKS",
    export_skins=True,
    export_morph=False,
    export_yup=True,
)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
print("DONE", dst, os.path.getsize(dst), "meshes", len(meshes), "tris", tris)
