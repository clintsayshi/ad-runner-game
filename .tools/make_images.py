"""Render the app icons (192, 512) and the social share image (1200x630).

Run:  blender -b --factory-startup -P make_images.py -- <out_dir>

Flat 2D art built from simple shapes and Blender's built-in font, rendered with
the light Workbench engine and an orthographic camera (no GPU-heavy lighting).
"""
import math
import os
import sys

import bpy

out = sys.argv[sys.argv.index("--") + 1]
os.makedirs(os.path.join(out, "icons"), exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "FLAT"
sh.color_type = "MATERIAL"
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w")
sh.background_type = "WORLD"
scene.world.color = (0.067, 0.067, 0.067)
scene.display.render_aa = "16"


def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    return m


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


RED, WHITE, DARK, GOLD, ROAD = (mat(n, srgb(h)) for n, h in
                                [("red", "c62a2a"), ("white", "f2f2f2"), ("dark", "1a1a1a"), ("gold", "ffcc66"), ("road", "2a2a2a")])


def box(x, y, w, h, m, z=0.0, rot=0.0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, y, z))
    o = bpy.context.object
    o.scale = (w, h, 1)
    o.rotation_euler[2] = rot
    o.data.materials.append(m)
    return o


def disc(x, y, r, m, z=0.0, sy=1.0):
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=r, fill_type="NGON", location=(x, y, z))
    o = bpy.context.object
    o.scale[1] = sy
    o.data.materials.append(m)
    return o


def chopper(cx, cy, s, m, z=0.2, tilt=0.0):
    """Side view of a helicopter, nose to the left. s = overall scale."""
    parts = [disc(cx, cy, 0.55 * s, m, z, sy=0.62),                       # body
             box(cx + 0.95 * s, cy + 0.05 * s, 1.1 * s, 0.16 * s, m, z),   # tail boom
             box(cx + 1.48 * s, cy + 0.2 * s, 0.13 * s, 0.5 * s, m, z),    # fin
             box(cx, cy + 0.62 * s, 2.5 * s, 0.07 * s, m, z),             # rotor
             box(cx, cy + 0.48 * s, 0.1 * s, 0.22 * s, m, z),             # mast
             box(cx - 0.05 * s, cy - 0.5 * s, 0.95 * s, 0.06 * s, m, z),   # skid
             box(cx - 0.3 * s, cy - 0.42 * s, 0.05 * s, 0.17 * s, m, z),
             box(cx + 0.22 * s, cy - 0.42 * s, 0.05 * s, 0.17 * s, m, z)]
    for p in parts:   # tilt the whole thing nose-down about its centre
        dx, dy = p.location.x - cx, p.location.y - cy
        p.location.x = cx + dx * math.cos(tilt) - dy * math.sin(tilt)
        p.location.y = cy + dx * math.sin(tilt) + dy * math.cos(tilt)
        p.rotation_euler[2] += tilt


def text(body, x, y, size, m, align="CENTER", bold=True, z=0.3):
    bpy.ops.object.text_add(location=(x, y, z))
    t = bpy.context.object
    t.data.body = body
    t.data.size = size
    t.data.align_x = align
    t.data.align_y = "CENTER"
    if bold:
        t.data.offset = 0.0
        t.data.extrude = 0.0
        t.data.bevel_depth = size * 0.012   # thickens the default font a little
    t.data.materials.append(m)
    return t


def camera(w, h, ortho):
    bpy.ops.object.camera_add(location=(0, 0, 10))
    c = bpy.context.object
    c.data.type = "ORTHO"
    c.data.ortho_scale = ortho
    scene.camera = c
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


# ---- app icon: a white chopper over a red sun on a dark rounded tile
for size in (512, 192):
    clear()
    camera(size, size, 2.0)
    disc(0, -0.15, 0.72, RED)
    chopper(-0.05, 0.12, 0.62, WHITE)
    scene.render.filepath = os.path.join(out, "icons", f"icon-{size}.png")
    bpy.ops.render.render(write_still=True)

# ---- share image 1200x630: title, tag line, chopper over a red sun, a road
clear()
camera(1200, 630, 12.0)   # 12 units wide -> 6.3 units tall
disc(3.2, -0.2, 2.35, RED)
box(0, -2.75, 12, 0.85, ROAD, z=0.1)
for i in range(-6, 7):
    box(i * 1.1, -2.75, 0.5, 0.07, GOLD, z=0.15)
chopper(3.4, 0.55, 1.45, WHITE, tilt=-0.18)
chopper(5.0, 1.9, 0.6, DARK, tilt=-0.1)
text("CHOPPER", -5.4, 1.35, 1.25, WHITE, align="LEFT")
text("RUN 3D", -5.4, 0.05, 1.25, GOLD, align="LEFT")
text("Run. Hide. Drive. Survive.", -5.4, -1.15, 0.46, WHITE, align="LEFT", bold=False)
text("Free in your browser", -5.4, -1.75, 0.34, GOLD, align="LEFT", bold=False)
scene.render.filepath = os.path.join(out, "og-image.png")
bpy.ops.render.render(write_still=True)
print("DONE", out)
