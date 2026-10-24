#!/usr/bin/env python
"""抓可商用素材：Lucide 图标 + Kenney 图案/准星（CC0）。

用法:
    python fetch_assets.py --out assets --icons --patterns
    python fetch_assets.py --out assets --kenney pattern-pack-extra,crosshair-pack

产出的目录结构正好喂给 render_poster.py（theme.icons.dir / 图案底纹）。
"""
import argparse
import os
import re
import tarfile
import urllib.request
import zipfile

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
LUCIDE = "https://registry.npmjs.org/lucide-static/-/lucide-static-1.61.0.tgz"


def fetch(url, timeout=90):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def lucide(out):
    dst = os.path.join(out, "icons")
    os.makedirs(dst, exist_ok=True)
    raw = fetch(LUCIDE)
    n = 0
    with tarfile.open(fileobj=__import__("io").BytesIO(raw)) as t:
        for m in t.getmembers():
            if m.isfile() and m.name.startswith("package/icons/") and m.name.endswith(".svg"):
                with open(os.path.join(dst, os.path.basename(m.name)), "wb") as f:
                    f.write(t.extractfile(m).read())
                n += 1
        try:
            lic = t.extractfile("package/LICENSE").read()
            open(os.path.join(out, "LICENSE-Lucide.txt"), "wb").write(lic)
        except Exception:  # noqa: BLE001
            pass
    print(f"Lucide 图标 {n} 枚 -> {dst}")


def kenney(out, slugs):
    for slug in slugs:
        page = fetch(f"https://kenney.nl/assets/{slug}").decode("utf-8", "ignore")
        zips = re.findall(r'href=[\'"]([^\'"]+\.zip)[\'"]', page)
        if not zips:
            print("  找不到 zip:", slug)
            continue
        raw = fetch(zips[0])
        target = os.path.join(out, slug)
        os.makedirs(target, exist_ok=True)
        n = 0
        with zipfile.ZipFile(__import__("io").BytesIO(raw)) as z:
            for name in z.namelist():
                base = os.path.basename(name)
                if name.lower().endswith("license.txt"):
                    open(os.path.join(out, f"LICENSE-{slug}.txt"), "wb").write(z.read(name))
                if not name.lower().endswith((".png", ".svg")):
                    continue
                if name.startswith("Preview") or "Tilesheet" in name:
                    continue
                part = "svg" if name.lower().endswith(".svg") else "png"
                d = os.path.join(target, part)
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, base), "wb") as f:
                    f.write(z.read(name))
                n += 1
        print(f"Kenney {slug}: {n} 个文件 -> {target}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets")
    ap.add_argument("--icons", action="store_true", help="抓 Lucide 全套图标")
    ap.add_argument("--patterns", action="store_true", help="抓 Kenney 几何图案")
    ap.add_argument("--kenney", default="", help="额外指定 Kenney slug，逗号分隔")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    if a.icons:
        lucide(a.out)
    slugs = []
    if a.patterns:
        slugs.append("pattern-pack-extra")
    if a.kenney:
        slugs += [s.strip() for s in a.kenney.split(",") if s.strip()]
    if slugs:
        kenney(a.out, slugs)
