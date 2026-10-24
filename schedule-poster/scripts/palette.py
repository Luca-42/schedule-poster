"""从人像里取 3 个主色，给「撞色版」当主题色。

用法：
    python scripts/palette.py 人像.png
    python scripts/palette.py 人像.png --count 3

输出可直接粘进 theme.json 的 colors：
    {"accent": "#00a8c3", "accent2": "#e8006c", "highlight": "#f0b450"}

思路：先按透明度把背景剔掉，再量化成 24 色，按占比排序，
然后按色相拉开距离挑 3 个（避免三个颜色都是同一个蓝）。
"""
import colorsys
import json
import sys

from PIL import Image


def hx(rgb):
    return "#%02x%02x%02x" % rgb


def hue_dist(a, b):
    """粗略色相距离（0~255 环绕），用来保证三个色不撞在一起。"""
    def h(c):
        r, g, b2 = [v / 255 for v in c]
        mx, mn = max(r, g, b2), min(r, g, b2)
        if mx == mn:
            return 0
        d = mx - mn
        if mx == r:
            v = ((g - b2) / d) % 6
        elif mx == g:
            v = (b2 - r) / d + 2
        else:
            v = (r - g) / d + 4
        return v * 42.5

    d = abs(h(a) - h(b))
    return min(d, 255 - d)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = sys.argv[1]
    count = 3
    if "--count" in sys.argv:
        count = int(sys.argv[sys.argv.index("--count") + 1])

    im = Image.open(path).convert("RGBA")
    im.thumbnail((400, 400))

    # 只保留不透明、不是纯白的像素（白底 / 透明底都不会污染取色）
    px = [
        (r, g, b) for r, g, b, a in im.getdata()
        if a > 200 and not (r > 244 and g > 244 and b > 244)
    ]
    if not px:
        px = list(im.convert("RGB").getdata())

    tmp = Image.new("RGB", (len(px), 1))
    tmp.putdata(px)
    q = tmp.quantize(colors=24, method=Image.MEDIANCUT)
    pal = q.getpalette() or []
    counts = sorted(q.getcolors() or [], reverse=True)

    cands = []
    for n, idx in counts:
        c = tuple(pal[idx * 3: idx * 3 + 3])
        if sum(c) < 70:                       # 太黑，留给描边
            continue
        if max(c) > 232 and max(c) - min(c) < 32:   # 接近纯白，做不了强调色
            continue
        if max(c) - min(c) < 26:              # 灰得没脾气
            continue
        cands.append((n, c))
        if len(cands) >= 10:
            break

    picked = []
    for n, c in cands:
        if all(hue_dist(c, p[1]) > 28 for p in picked):
            picked.append((n, c))
        if len(picked) == count:
            break
    # 不够三个就用色相旋转补一个对比色，别拿接近白的凑数
    guard = 0
    while len(picked) < count and picked and guard < 8:
        r, g, b = [v / 255 for v in picked[0][1]]
        h, l, s2 = colorsys.rgb_to_hls(r, g, b)
        h = (h + 0.42 + 0.08 * guard) % 1.0
        c = tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, max(0.35, min(0.6, l)), max(0.55, s2)))
        picked.append((0, c))
        guard += 1

    keys = ["accent", "accent2", "highlight"]
    out = {keys[i]: hx(picked[i][1]) for i in range(len(picked))}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    for i, p in enumerate(picked):
        print(f"  {keys[i]:9s} {hx(p[1])}  占比 {p[0]}")


if __name__ == "__main__":
    main()
