"""Download a few NVIDIA SimReady props (CC-BY-4.0) from Hugging Face.

Saves each prop's USD + textures under chopper-run/assets/simready-src/<name>/.
Skips thumbnails and physics-engine payload variants we don't need.
"""
import json
import os
import urllib.parse
import urllib.request

PROPS = [
    "barrier_fence_metal_a02",
    "barrier_wall_plastic_orange_a03",
    "bin_waste_a01",
    "container_recycle_blue_wheeled_a01",
    "crate_plywood_b01",
    "crate_green_a01",
    "drum_steel_a01",
    "drum_plastic_blue_a01",
    "environment_fence_a01",
    "box_cardboard_large_a02",
]
BASE = "https://huggingface.co/datasets/nvidia/simready-assets"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "simready-src")


def files_for(prop):
    url = f"https://huggingface.co/api/datasets/nvidia/simready-assets/tree/main/{prop}?recursive=true"
    with urllib.request.urlopen(url, timeout=60) as r:
        items = json.load(r)
    for it in items:
        p = it["path"]
        if it.get("type") != "file":
            continue
        if "/.thumbs/" in p or "/.metadata/" in p and not p.endswith("LICENSE.txt"):
            continue
        if "/payloads/MuJoCo/" in p or "/payloads/PhysX" in p.replace("physx", "PhysX"):
            continue
        yield p


MIN_FREE = 600 * 1024 * 1024  # stop before the disk fills up


def main():
    import shutil

    for prop in PROPS:
        n = 0
        for p in files_for(prop):
            if shutil.disk_usage(OUT).free < MIN_FREE:
                print("stopped: disk almost full")
                return
            dest = os.path.join(OUT, p)
            if os.path.exists(dest):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            src = f"{BASE}/resolve/main/{urllib.parse.quote(p)}"
            urllib.request.urlretrieve(src, dest)
            n += 1
        print(prop, n, "files")


if __name__ == "__main__":
    main()
