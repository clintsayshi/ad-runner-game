"""Convert one SimReady USD prop to a small GLB.

Run:  blender -b --factory-startup -P usd_to_glb.py -- <in.usd> <out.glb> [tex_px] [max_tris]

Textures are downscaled to tex_px (default 512) and saved as JPEG inside the GLB,
so a ~80 MB prop becomes ~1-3 MB.
"""
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
tex_px = int(argv[2]) if len(argv) > 2 else 512
MAX_TRIS = int(argv[3]) if len(argv) > 3 else 6000

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=src, import_materials=True, import_usd_preview=True)

# Drop anything that is not a visible mesh (physics colliders, cameras, lights).
for ob in list(bpy.data.objects):
    name = ob.name.lower()
    if ob.type != "MESH" or "collider" in name or "collision" in name:
        if ob.type != "EMPTY":
            bpy.data.objects.remove(ob, do_unlink=True)

# Simplify heavy props so dozens of copies stay cheap in the browser.
all_meshes = [o for o in bpy.data.objects if o.type == "MESH"]
total = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in all_meshes)
def tri_count():
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in all_meshes)


# Collapse decimation stops early on some meshes, so bake and repeat a few times.
for _ in range(4):
    now = tri_count()
    if now <= MAX_TRIS * 1.1:
        break
    for o in all_meshes:
        if o.data.users > 1:
            o.data = o.data.copy()  # instanced meshes: give each its own copy
        m = o.modifiers.new("decimate", "DECIMATE")
        m.ratio = max(0.02, MAX_TRIS / now)
        m.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    for o in all_meshes:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        o.modifiers.clear()
        o.data = me

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
    export_yup=True,
    export_apply=True,
    export_animations=False,  # props are static; also avoids an exporter crash
)
dg = bpy.context.evaluated_depsgraph_get()
tris = 0
dims = [0.0, 0.0, 0.0]
for o in all_meshes:
    ev = o.evaluated_get(dg)
    tris += sum(len(p.vertices) - 2 for p in ev.data.polygons)
    dims = [max(a, b) for a, b in zip(dims, o.dimensions)]
print(f"DONE {dst} meshes={len(all_meshes)} tris={tris} before={total} size_m={[round(d, 2) for d in dims]}")
