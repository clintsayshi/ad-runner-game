#!/usr/bin/env python3
"""Build a deployable copy of Chopper Run 3D into dist/.

    python3 build.py            # uses site.config.json
    python3 build.py --check    # build, then check the output for leftovers and broken links

Fills in the site URL, Google Analytics ID, Sentry DSN and version, renders
the extra pages, writes sitemap.xml, robots.txt, site.webmanifest and host
config (_headers for Netlify / Cloudflare Pages, vercel.json for Vercel).
Dev-only files (tests, tools, backups, the 2D version) are left out.
Standard library only.
"""
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
COPY = ["favicon.svg", "assets", "vendor", "icons", "og-image.png"]   # copied as-is when present
PAGES = ["about.html", "credits.html", "privacy.html", "404.html"]
# models kept for later but not used by the game right now
UNUSED = {"assets/character/hero-ybot.glb", "assets/props/wheelie_bin.glb", "assets/props/bin_waste.glb",
          "assets/props/crate_green.glb", "assets/props/crate_plywood.glb", "assets/city/glass-skyscraper.glb",
          "assets/city/street-tree.glb"}


def fail(msg):
    sys.exit(f"build: {msg}")


def load_config():
    cfg = json.loads((ROOT / "site.config.json").read_text())
    url = cfg.get("siteUrl", "").rstrip("/")
    if not re.match(r"^https://[^/\s]+(/[^\s]*)?$", url):
        fail(f"siteUrl must look like https://yourdomain.com (got {url!r})")
    ga = cfg.get("gaId", "").strip()
    if ga and not re.match(r"^G-[A-Z0-9]{4,20}$", ga):
        fail(f"gaId must look like G-ABC123XYZ (got {ga!r})")
    dsn = cfg.get("sentryDsn", "").strip()
    if dsn and not re.match(r"^https://[0-9a-f]+@[\w.-]+/\d+$", dsn):
        fail(f"sentryDsn must look like https://<key>@o0.ingest.sentry.io/<id> (got {dsn!r})")
    return url, ga, dsn, cfg.get("contactEmail", "").strip()


def version():
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sha = ""
    return datetime.date.today().isoformat() + (f"-{sha}" if sha else "")


def fill(text, subs):
    for k, v in subs.items():
        text = text.replace(k, v)
    return text


def main():
    url, ga, dsn, email = load_config()
    today = datetime.date.today().isoformat()
    subs = {"__SITE_URL__": url, "__GA_ID__": ga, "__SENTRY_DSN__": dsn, "__VERSION__": version(),
            "__CONTACT_EMAIL__": email or "the site owner", "__BUILD_DATE__": today}

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    # the game
    (DIST / "index.html").write_text(fill((ROOT / "index.html").read_text(), subs))
    for name in COPY:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, DIST / name, ignore=lambda d, files: [f for f in files if (Path(d) / f).relative_to(ROOT).as_posix() in UNUSED or f == ".DS_Store"])
        elif src.exists():
            shutil.copy2(src, DIST / name)
        else:
            print(f"build: note: {name} not found, skipped")

    # extra pages: each file starts with <!-- title: ... | desc: ... -->
    shell = (ROOT / "pages" / "_page.html").read_text()
    for name in PAGES:
        raw = (ROOT / "pages" / name).read_text()
        m = re.match(r"\s*<!--\s*title:\s*(.*?)\s*\|\s*desc:\s*(.*?)\s*-->\s*", raw, re.S)
        if not m:
            fail(f"pages/{name} must start with <!-- title: ... | desc: ... -->")
        html = shell.replace("{{TITLE}}", m.group(1)).replace("{{DESC}}", m.group(2)) \
                    .replace("{{FILE}}", "" if name == "404.html" else name).replace("{{BODY}}", raw[m.end():])
        if name == "404.html":   # served from any path: make its links absolute and keep it out of search
            html = html.replace("<head>", '<head>\n<base href="/">\n<meta name="robots" content="noindex">', 1)
        (DIST / name).write_text(fill(html, subs))

    # sitemap + robots
    urls = [("", "1.0", "weekly"), ("about.html", "0.7", "monthly"), ("credits.html", "0.3", "yearly"), ("privacy.html", "0.2", "yearly")]
    body = "".join(f"  <url><loc>{url}/{p}</loc><lastmod>{today}</lastmod><changefreq>{f}</changefreq><priority>{pr}</priority></url>\n"
                   for p, pr, f in urls)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n'
                                      f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}</urlset>\n')
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {url}/sitemap.xml\n")

    # web app manifest: "Add to Home Screen" opens it full screen, sideways
    (DIST / "site.webmanifest").write_text(json.dumps({
        "name": "Chopper Run 3D", "short_name": "Chopper Run", "start_url": "./", "scope": "./",
        "display": "fullscreen", "orientation": "landscape", "background_color": "#111111", "theme_color": "#111111",
        "icons": [{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
                  {"src": "favicon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }, indent=2) + "\n")

    # host config: long cache for models / engine, short for pages; basic security headers
    sec = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "strict-origin-when-cross-origin",
           "X-Frame-Options": "SAMEORIGIN", "Permissions-Policy": "camera=(), microphone=(), geolocation=()"}
    rules = [("/*", {**sec, "Cache-Control": "public, max-age=300"}),
             ("/assets/*", {"Cache-Control": "public, max-age=2592000"}),
             ("/vendor/*", {"Cache-Control": "public, max-age=31536000, immutable"})]
    (DIST / "_headers").write_text("".join(f"{path}\n" + "".join(f"  {k}: {v}\n" for k, v in h.items()) + "\n" for path, h in rules))
    (DIST / "vercel.json").write_text(json.dumps({"cleanUrls": False, "headers": [
        {"source": p.replace("/*", "/(.*)"), "headers": [{"key": k, "value": v} for k, v in h.items()]} for p, h in rules]}, indent=2) + "\n")

    size = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"build: wrote {DIST} ({size/1e6:.1f} MB) for {url}"
          f" | analytics {'ON ' + ga if ga else 'off'} | errors {'ON' if dsn else 'off'}")
    if "--check" in sys.argv:
        check()


def check():
    """Look for unfilled placeholders, dev files and links to files that don't exist."""
    bad = []
    for f in DIST.rglob("*"):
        if f.suffix in (".html", ".xml", ".txt", ".json", ".webmanifest") and f.is_file():
            t = f.read_text()
            for ph in re.findall(r"__[A-Z_]+__", t):
                if ph not in ("__game",):
                    bad.append(f"{f.relative_to(DIST)}: placeholder {ph} left")
            if f.suffix == ".html":
                for ref in re.findall(r'(?:href|src)="([^"#:]+)"', t):
                    ref = ref.split("?")[0]
                    if ref in ("./", "/") or ref.startswith("//"):
                        continue
                    if not (DIST / ref.lstrip("/")).exists():
                        bad.append(f"{f.relative_to(DIST)}: links to missing {ref}")
    for dev in (".sim-test.js", ".tools", ".backup", "index-2d.html", "build.py", "site.config.json", "pages", ".git"):
        if (DIST / dev).exists():
            bad.append(f"dev file shipped: {dev}")
    print("check: OK" if not bad else "check: problems\n  " + "\n  ".join(bad))
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
