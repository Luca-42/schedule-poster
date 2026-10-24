#!/usr/bin/env python
"""扣掉纯白背景（从四边做连通域扩散，不会误伤衣服里的白色）。

用法:
    python cutout.py 输入.png 输出.png [阈值=250] [降采样倍数=2]

为什么不用现成方案:
    Pillow 13 起 ImageDraw.floodfill 已移除；沙箱里通常没有 scipy/cv2，
    所以这里自己用 deque 做 BFS，顺便在半分辨率上跑，快很多。
"""
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter


def cutout(src, dst, thresh=250, downscale=2):
    im = Image.open(src).convert("RGB")
    d = max(1, int(downscale))
    small = im.resize((im.width // d, im.height // d), Image.LANCZOS)
    a = np.array(small)
    white = a.min(axis=2) >= thresh
    h, w = white.shape

    seen = np.zeros((h, w), dtype=bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if white[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if white[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))

    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and white[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))

    print("背景占比: %.1f%%" % (seen.mean() * 100))
    alpha = Image.fromarray(np.where(seen, 0, 255).astype(np.uint8))
    alpha = alpha.resize(im.size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
    out = im.convert("RGBA")
    out.putalpha(alpha)
    out.save(dst)
    print("saved", dst, out.size)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    cutout(sys.argv[1], sys.argv[2],
           float(sys.argv[3]) if len(sys.argv) > 3 else 250,
           int(sys.argv[4]) if len(sys.argv) > 4 else 2)
