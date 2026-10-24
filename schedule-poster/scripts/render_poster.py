#!/usr/bin/env python
"""主题化播表渲染器：theme.json + content.json -> 3200×1800 PNG。

用法:
    python render_poster.py theme.json content.json out.png

设计上刻意不用浏览器截图：沙箱里常常起不了 Chrome，PIL 直画更稳。
"""
import io
import json
import os
import sys

import pymupdf
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- 工具


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Poster:
    def __init__(self, theme, content, base="."):
        self.t = theme
        self.c = content
        self.base = base
        self.S = theme.get("scale", 2)
        self.W = theme["canvas"][0] * self.S
        self.H = theme["canvas"][1] * self.S
        self._fc = {}

        col = theme["colors"]
        self.paper = hx(col["paper"])
        self.ink = hx(col["ink"])
        self.body = hx(col.get("body", col["ink"]))
        self.muted = hx(col.get("muted", "#6a727e"))
        self.accent = hx(col.get("accent", "#00a8c3"))
        self.accent2 = hx(col.get("accent2", "#e8006c"))
        self.highlight = hx(col.get("highlight", "#d68414"))
        self.gridc = hx(col.get("grid", "#e6eaf0"))
        self.card = hx(col.get("card", col["paper"]))
        self.hot = hx(col.get("hot", col["paper"]))

        self.dark = theme.get("effects", {}).get("dark", False)
        self.fx = theme.get("effects", {})
        self.ty = theme.get("type", {})
        self.fd = theme["fonts"].get("dir", "fonts")
        self.ic = theme.get("icons", {}).get("dir", "icons")

    # ---- 基础 ----
    def px(self, v):
        return int(round(v * self.S))

    def F(self, key, size=None):
        name = self.t["fonts"][key]
        size = size or self.ty.get(key, 16)
        k = (name, size)
        if k not in self._fc:
            self._fc[k] = ImageFont.truetype(os.path.join(self.fd, name), self.px(size))
        return self._fc[k]

    def UI(self, size, bold=False):
        """界面用中文字体（系统字体，小字号比装饰字体清楚）。"""
        cands = self.t["fonts"].get("ui")
        cands = cands if isinstance(cands, list) else [cands]
        for p in cands:
            if not p:
                continue
            path = p if os.path.isabs(p) else os.path.join(self.fd, p)
            if os.path.exists(path):
                k = (path, size, bold)
                if k not in self._fc:
                    self._fc[k] = ImageFont.truetype(path, self.px(size))
                return self._fc[k]
        return self.F("display", size)

    def text(self, d, xy, s, font, fill, tracking=0, alpha=255):
        x, y = xy
        if not tracking:
            d.text((x, y), s, font=font, fill=fill + (alpha,))
            return d.textlength(s, font=font)
        for ch in s:
            d.text((x, y), ch, font=font, fill=fill + (alpha,))
            x += d.textlength(ch, font=font) + self.px(tracking)
        return x - xy[0]

    def layer(self, base, fn):
        lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        fn(ImageDraw.Draw(lay), lay)
        return Image.alpha_composite(base, lay)

    def dashed(self, d, x0, y0, x1, y1, color, dash=5, gap=4, width=1):
        x0, y0, x1, y1 = self.px(x0), self.px(y0), self.px(x1), self.px(y1)
        ln = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        if not ln:
            return
        ux, uy = (x1 - x0) / ln, (y1 - y0) / ln
        t = 0.0
        while t < ln:
            e = min(t + self.px(dash), ln)
            d.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * e, y0 + uy * e)],
                   fill=color, width=width)
            t = e + self.px(gap)

    # ---- 面板 ----
    def poly(self, x, y, w, h, cut):
        return [(x, y), (x + w, y), (x + w, y + h - cut), (x + w - cut, y + h), (x, y + h)]

    def panel(self, base, x, y, w, h, tint=None, cut=None, border=None, shadow=None):
        X, Y, Wd, Ht = self.px(x), self.px(y), self.px(w), self.px(h)
        ct = self.px(cut if cut is not None else self.fx.get("cut", 20))
        border = border or self.ink
        fill = tint or self.card

        if shadow if shadow is not None else self.fx.get("shadow", True):
            off = self.px(6)

            def sh(d, _l):
                d.polygon([(a + off, b + off) for a, b in self.poly(X, Y, Wd, Ht, ct)],
                          fill=self.ink + (28,))
            base = self.layer(base, sh)

        mask = Image.new("L", (Wd, Ht), 0)
        ImageDraw.Draw(mask).polygon(
            [(0, 0), (Wd, 0), (Wd, Ht - ct), (Wd - ct, Ht), (0, Ht)], fill=255)
        grad = Image.new("RGBA", (Wd, Ht))
        gd = ImageDraw.Draw(grad)
        top, bot = self.paper, fill
        for i in range(Ht):
            gd.line([(0, i), (Wd, i)], fill=mix(top, bot, i / max(1, Ht - 1)) + (255,))
        base.paste(grad, (X, Y), mask)

        def stroke(d, _l):
            d.line(self.poly(X, Y, Wd, Ht, ct) + [(X, Y)], fill=border + (88,), width=max(1, self.px(0.9)))
        return self.layer(base, stroke)

    def icon(self, name, size):
        path = os.path.join(self.ic, f"{name}.svg")
        if not os.path.exists(path):
            return None
        doc = pymupdf.open(path)
        page = doc[0]
        z = self.px(size) / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=True)
        im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
        doc.close()
        solid = Image.new("RGBA", im.size, self.ink + (255,))
        solid.putalpha(im.getchannel("A"))
        return solid

    # ---- 各区块 ----
    def background(self):
        base = Image.new("RGBA", (self.W, self.H), self.paper + (255,))

        # 底图（AI 图 / 网图）：盖满画布，再压一层纸色蒙版
        img = self.fx.get("image")
        if img:
            ph = Image.open(os.path.join(self.base, img)).convert("RGBA")
            k = max(self.W / ph.width, self.H / ph.height)
            ph = ph.resize((int(ph.width * k) + 1, int(ph.height * k) + 1), Image.LANCZOS)
            left, top = (ph.width - self.W) // 2, (ph.height - self.H) // 2
            base = ph.crop((left, top, left + self.W, top + self.H))
            scrim = self.fx.get("scrim", 80)
            if scrim:
                a0, a1 = int(scrim * 0.7), min(250, int(scrim * 1.25))

                def sc(d, _l):
                    for i in range(self.H):
                        a = int(a0 + (a1 - a0) * (i / self.H))
                        d.line([(0, i), (self.W, i)], fill=self.paper + (a,))
                base = self.layer(base, sc)
        if self.dark and self.fx.get("glow", True):
            lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            d.ellipse([self.px(-300), self.px(-420), self.px(900), self.px(560)],
                      fill=self.accent + (30,))
            d.ellipse([self.px(900), self.px(430), self.px(1900), self.px(1400)],
                      fill=self.accent2 + (26,))
            base = Image.alpha_composite(base, lay.filter(ImageFilter.GaussianBlur(self.px(150))))
        if self.fx.get("grid", True):
            def g(d, _l):
                step = 40
                for x in range(0, self.t["canvas"][0] + 1, step):
                    d.line([(self.px(x), 0), (self.px(x), self.H)], fill=self.gridc + (255,), width=1)
                for y in range(0, self.t["canvas"][1] + 1, step):
                    d.line([(0, self.px(y)), (self.W, self.px(y))], fill=self.gridc + (255,), width=1)
            base = self.layer(base, g)
        return base

    def header(self, base):
        d = ImageDraw.Draw(base)
        m = self.t["layout"]["margin"]
        c = self.c

        d.rectangle([self.px(m), self.px(34), self.px(m + 8), self.px(46)], fill=self.accent2 + (255,))
        self.text(d, (self.px(m + 18), self.px(33)), c.get("kicker", ""),
                  self.F("mono", self.ty.get("kicker", 14)), self.ink, tracking=3.4)

        ft = self.F("display", self.ty.get("title", 82))
        title = c.get("title", "")
        ty = self.ty.get("title", 82)
        off = self.px(2.5)
        d.text((self.px(m) + off, self.px(55) + off), title, font=ft, fill=self.accent2 + (255,))
        d.text((self.px(m) - off, self.px(52) - off), title, font=ft, fill=self.accent + (255,))
        d.text((self.px(m), self.px(54)), title, font=ft, fill=self.ink + (255,))

        tw = d.textlength(title, font=ft)
        self.text(d, (self.px(m) + tw + self.px(12), self.px(58)), c.get("version", ""),
                  self.F("numBig", self.ty.get("version", 32)), self.accent2, tracking=1.2)
        self.text(d, (self.px(m), self.px(146)), c.get("subtitle", ""),
                  self.F("sub", self.ty.get("subtitle", 18)), self.muted, tracking=2.6)

        right = self.t["canvas"][0] - m
        for i, line in enumerate(c.get("hud", [])[:2]):
            f = self.F("mono", self.ty.get("hud", 13))
            w = d.textlength(line, font=f)
            d.text((self.px(right) - w, self.px(34 + i * 20)), line, font=f, fill=self.muted + (255,))
        bh = [16, 9, 22]
        for i in range(12):
            hh = bh[i % 3]
            col = (self.ink + (200,)) if i % 2 == 0 else (self.muted + (110,))
            x = right - 12 * 5.6 + i * 5.6
            d.rectangle([self.px(x), self.px(80 + (22 - hh)), self.px(x + 3), self.px(102)], fill=col)
        return base

    def days(self, base):
        d = ImageDraw.Draw(base)
        L = self.t["layout"]
        m, aside, gap = L["margin"], L.get("aside", 372), L.get("gap", 26)
        top, bottom = L.get("top", 180), self.t["canvas"][1] - L.get("footer", 48) - 30
        left_w = self.t["canvas"][0] - m * 2 - (aside + gap if self.c.get("portrait") else 0)

        items = list(self.c.get("days", []))
        notice = self.c.get("notice")
        n = len(items) + (1 if notice else 0)
        cols = L.get("cols") or (4 if n > 4 else max(1, n))
        rows = max(1, (n + cols - 1) // cols)
        cw = (left_w - (cols - 1) * 14) / cols
        ch = (bottom - top - (rows - 1) * 14) / rows

        def draw_card(i, data, is_notice=False):
            col, row = i % cols, i // cols
            X = m + col * (cw + 14)
            Y = top + row * (ch + 14)
            base2 = self.panel(base, X, Y, cw, ch,
                               tint=self.hot if (data.get("hot") and not is_notice) else
                               (mix(self.paper, self.accent2, 0.05) if is_notice else None))
            dd = ImageDraw.Draw(base2)

            tint_bar = self.accent2 if (data.get("hot") or is_notice) else self.ink
            dd.rectangle([self.px(X), self.px(Y), self.px(X + 44), self.px(Y + 2.5)],
                         fill=tint_bar + (255,))

            if not is_notice:
                num = data.get("no") or f"{i + 1:02d}"
                fn = self.F("numBig", self.ty.get("watermark", 74))
                nw = dd.textlength(num, font=fn)
                dd.text((self.px(X + cw - 18) - nw, self.px(Y + ch - 86)), num, font=fn,
                        fill=mix(self.paper, self.ink, 0.07) + (255,))
                if data.get("icon"):
                    ic = self.icon(data["icon"], 21)
                    if ic:
                        base2.alpha_composite(ic, (self.px(X + cw - 14 - 21), self.px(Y + 11)))
                        dd = ImageDraw.Draw(base2)

            fd = self.UI(self.ty.get("dow", 22), bold=True)
            dd.text((self.px(X + 14), self.px(Y + 13)), data.get("dow", ""), font=fd,
                    fill=self.ink + (255,))
            dw = dd.textlength(data.get("dow", ""), font=fd)
            dd.text((self.px(X + 14) + dw + self.px(9), self.px(Y + 20)), data.get("date", ""),
                    font=self.F("num", self.ty.get("date", 17)),
                    fill=(self.accent2 if data.get("hot") else self.accent) + (255,))

            sy = Y + 68
            for j, slot in enumerate(data.get("slots", [])):
                if j:
                    self.dashed(dd, X + 14, sy - 12, X + cw - 14, sy - 12,
                                mix(self.ink, self.paper, 0.75) + (255,), 5, 4, self.px(0.8))
                    sy += 8
                dd.text((self.px(X + 14), self.px(sy)), slot.get("time", ""),
                        font=self.F("mono", self.ty.get("time", 13.5)), fill=self.accent + (255,))
                sy += 22
                tag = slot.get("tag")
                if tag:
                    ftag = self.UI(self.ty.get("tag", 11.5), bold=True)
                    tw_ = dd.textlength(tag, font=ftag)
                    dd.rectangle([self.px(X + 14), self.px(sy), self.px(X + 14 + tw_ / self.S + 11),
                                  self.px(sy + 17)], fill=self.ink + (255,))
                    dd.text((self.px(X + 14 + 5), self.px(sy + 2)), tag, font=ftag,
                            fill=self.paper + (255,))
                    sy += 27
                for ln in slot.get("lines", []):
                    dd.text((self.px(X + 14), self.px(sy)),
                            ln, font=self.UI(self.ty.get("body", 17)), fill=self.body + (255,))
                    sy += 23
            return base2

        for i, data in enumerate(items):
            base = draw_card(i, data)
        if notice:
            base = draw_card(len(items), notice, is_notice=True)
        return base

    def portrait(self, base):
        P = self.c.get("portrait")
        if not P:
            return base
        L = self.t["layout"]
        m, aside = L["margin"], L.get("aside", 372)
        top, bottom = L.get("top", 180), self.t["canvas"][1] - L.get("footer", 48) - 30
        x0 = self.t["canvas"][0] - m - aside
        bleed = self.t.get("portrait", {}).get("bleed", True)
        target_w = (self.t["canvas"][0] - x0) if bleed else aside
        ph_ = bottom - top

        # 把这块的网格洗成纸色，人像才不会踩在格子上
        def wash(d, _l):
            ramp = self.px(70)
            for i in range(ramp):
                a = int(255 * i / ramp)
                d.line([(self.px(x0) - ramp + i, self.px(top - 30)),
                        (self.px(x0) - ramp + i, self.px(bottom + 30))],
                       fill=self.paper + (a,), width=1)
            d.rectangle([self.px(x0), self.px(top - 30), self.W, self.px(bottom + 30)],
                        fill=self.paper + (255,))
        base = self.layer(base, wash)

        p = Image.open(P).convert("RGBA")
        k = self.px(ph_) / p.height
        p = p.resize((int(p.width * k), self.px(ph_)), Image.LANCZOS)
        need = self.px(target_w)
        if p.width < need:
            canvas = Image.new("RGBA", (need, self.px(ph_)), self.paper + (255,))
            canvas.alpha_composite(p, ((need - p.width) // 2, 0))
            p = canvas
        else:
            left = (p.width - need) // 2
            p = p.crop((left, 0, left + need, self.px(ph_)))

        feather = self.t.get("portrait", {}).get("feather", 0)
        if feather:
            mask = Image.new("L", p.size, 255)
            md = ImageDraw.Draw(mask)
            fr = self.px(feather)
            for i in range(fr):
                a = int(255 * (i / fr) ** 1.5)
                md.line([(i, 0), (i, p.height)], fill=a)
                md.line([(p.width - 1 - i, 0), (p.width - 1 - i, p.height)], fill=a)
            p.putalpha(ImageChops.multiply(p.getchannel("A"), mask))

        base.alpha_composite(p, (self.px(x0), self.px(top)))

        if self.dark and self.fx.get("holo", True):
            def holo(d, _l):
                for y in range(top, bottom, 4):
                    d.line([(self.px(x0), self.px(y)), (self.W, self.px(y))],
                           fill=self.accent + (10,), width=1)
            base = self.layer(base, holo)
        return base

    def bonus(self, base):
        B = self.c.get("bonus")
        if not B:
            return base
        L = self.t["layout"]
        m, aside = L["margin"], L.get("aside", 372)
        top, bottom = L.get("top", 180), self.t["canvas"][1] - L.get("footer", 48) - 30
        x0 = self.t["canvas"][0] - m - aside
        h = B.get("height", 168)
        y0 = bottom - h
        base = self.panel(base, x0, y0, aside, h, cut=22,
                          tint=mix(self.paper, self.accent2, 0.06), border=self.accent2)
        d = ImageDraw.Draw(base)
        d.text((self.px(x0 + 17), self.px(y0 + 15)), B.get("title", ""),
               font=self.F("display", 21), fill=self.ink + (255,))
        self.text(d, (self.px(x0 + 17), self.px(y0 + 44)), B.get("tag", ""),
                  self.F("mono", 10.5), self.accent2, tracking=1.6)
        sy = y0 + 64
        for ln in B.get("lines", [])[:2]:
            d.text((self.px(x0 + 17), self.px(sy)), ln, font=self.UI(14.5),
                   fill=mix(self.ink, self.paper, 0.45) + (255,))
            sy += 24
        d.text((self.px(x0 + 17), self.px(y0 + 104)), B.get("big", ""),
               font=self.F("numBig", self.ty.get("big", 46)), fill=self.highlight + (255,))
        self.text(d, (self.px(x0 + 92), self.px(y0 + 130)), B.get("bigLabel", ""),
                  self.F("mono", 11), self.muted, tracking=1.4)

        if B.get("live"):
            lx, ly = x0 + aside - 76, top + 14
            d.rectangle([self.px(lx), self.px(ly), self.px(lx + 62), self.px(ly + 18)],
                        fill=self.accent2 + (255,))
            d.ellipse([self.px(lx + 7), self.px(ly + 7), self.px(lx + 12), self.px(ly + 12)],
                      fill=self.paper + (255,))
            d.text((self.px(lx + 17), self.px(ly + 3)), "LIVE", font=self.F("mono", 11.5),
                   fill=self.paper + (255,))
        return base

    def footer(self, base):
        d = ImageDraw.Draw(base)
        m = self.t["layout"]["margin"]
        right = self.t["canvas"][0] - m
        y = self.t["canvas"][1] - 48
        d.line([(self.px(m), self.px(y + 4)), (self.px(right), self.px(y + 4))],
               fill=mix(self.ink, self.paper, 0.8) + (255,), width=max(1, self.px(0.7)))
        left, rt = (self.c.get("footer") or ["", ""])[:2]
        self.text(d, (self.px(m), self.px(y + 16)), left, self.F("mono", self.ty.get("footer", 12.5)),
                  self.muted, tracking=2.4)
        f = self.F("mono", self.ty.get("footer", 12.5))
        w = sum(d.textlength(ch, font=f) + self.px(2.4) for ch in rt)
        self.text(d, (self.px(right) - w, self.px(y + 16)), rt, f, self.muted, tracking=2.4)
        return base

    def render(self, out):
        base = self.background()
        base = self.header(base)
        base = self.days(base)
        base = self.portrait(base)
        base = self.bonus(base)
        base = self.footer(base)
        if self.fx.get("scanlines"):
            def sc(d, _l):
                for y in range(0, self.t["canvas"][1], 4):
                    d.line([(0, self.px(y)), (self.W, self.px(y))],
                           fill=(255, 255, 255, 8) if self.dark else self.ink + (6,), width=1)
            base = self.layer(base, sc)

        flat = Image.alpha_composite(Image.new("RGBA", base.size, self.paper + (255,)), base)
        flat.convert("RGB").save(out)
        stem, _ = os.path.splitext(out)
        flat.convert("RGB").save(stem + ".jpg", quality=93, subsampling=0, optimize=True)
        print("saved", out, flat.size)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        raise SystemExit(1)
    theme = json.load(open(sys.argv[1], encoding="utf-8"))
    content = json.load(open(sys.argv[2], encoding="utf-8"))
    Poster(theme, content, os.path.dirname(os.path.abspath(sys.argv[1]))).render(sys.argv[3])


if __name__ == "__main__":
    main()
