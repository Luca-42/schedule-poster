#!/usr/bin/env python
"""把编辑器模板打包成「单文件」网页：内嵌字体、人像、图标、导出库。

用法:
    python build_editor.py --template resources/editor_template.html \
        --out 项目/播表编辑器.html --fonts 项目/fonts \
        --portrait 项目/portrait.png --icons 项目/icons

要点:
  * 字体、人像、图标必须变成 data URL。file:// 下的本地图片会污染 canvas，
    不内嵌的话「存成图片」会直接报错。
  * 中文标题字体动辄 5MB，整个网页会到 8MB 左右，这是换来「一个文件就能发人」的代价。
"""
import argparse
import base64
import io
import os
import re
import urllib.request

from PIL import Image

H2C = "https://unpkg.com/html2canvas@1.4.1/dist/html2canvas.min.js"


def b64(path):
    return base64.b64encode(open(path, "rb").read()).decode()


def portrait_data(path, max_h=1284):
    """人像压到够用就行：导出是 2 倍图，高度 1284 足够清晰，体积小一个量级。"""
    im = Image.open(path)
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if has_alpha:
        im = im.convert("RGBA")
        if im.height > max_h:
            im = im.resize((int(im.width * max_h / im.height), max_h), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    im = im.convert("RGB")
    if im.height > max_h:
        im = im.resize((int(im.width * max_h / im.height), max_h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=90, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def ensure_html2canvas(cache_dir=".cache"):
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "html2canvas.min.js")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    try:
        data = urllib.request.urlopen(
            urllib.request.Request(H2C, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
        open(path, "wb").write(data)
        return data.decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        print("  导出库拉取失败（只能靠「存成 PDF」了）:", type(exc).__name__, exc)
        return "window.html2canvas=function(){return Promise.reject(new Error('no html2canvas'))};"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--portrait", required=True)
    ap.add_argument("--icons", required=True)
    ap.add_argument("--cache", default=".cache")
    a = ap.parse_args()

    html = open(a.template, encoding="utf-8").read()

    # 1) 图标：div(mask) -> img(data URL)
    def icon_repl(m):
        name = m.group(1)
        p = os.path.join(a.icons, name + ".svg")
        if not os.path.exists(p):
            print("  缺图标", name)
            return m.group(0)
        return ('<img class="ico" alt="" draggable="false" src="data:image/svg+xml;base64,'
                + b64(p) + '">')

    html, n = re.subn(
        r'<div class="ico" style="--m:url\(\'[^\']*/([a-z0-9\-]+)\.svg\'\)"></div>', icon_repl, html)
    print("图标内嵌:", n)

    # 2) 字体：任意 ../xxx/NAME.ttf -> data URL（按文件名去 --fonts 里找）
    def font_repl(m):
        name = os.path.basename(m.group(1))
        p = os.path.join(a.fonts, name)
        if not os.path.exists(p):
            print("  缺字体", name)
            return m.group(0)
        print(f"  字体 {name:36s} {os.path.getsize(p)/1024:7.0f}KB")
        return 'url("data:font/ttf;base64,' + b64(p) + '")'

    html = re.sub(r'url\("([^"]*\.ttf)"\)', font_repl, html)

    # 3) 人像
    html = html.replace("__PORTRAIT__", portrait_data(a.portrait))
    print("人像已内嵌")

    # 4) 导出库
    lib = ensure_html2canvas(a.cache).replace("</script>", "<\\/script>")
    if "__HTML2CANVAS__" in html:
        html = html.replace("__HTML2CANVAS__", lib)
        print("导出库内嵌:", round(len(lib) / 1024), "KB")

    open(a.out, "w", encoding="utf-8").write(html)
    print("输出", a.out, round(os.path.getsize(a.out) / 1024 / 1024, 2), "MB")


if __name__ == "__main__":
    main()
