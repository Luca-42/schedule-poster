"""SVG -> transparent PNG 批量转换（PyMuPDF 渲染）。

用法: python convert.py <src_dir> <dst_dir> <px>
"""
import glob
import os
import sys
import time

import pymupdf

src, dst, size = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(dst, exist_ok=True)

files = sorted(glob.glob(os.path.join(src, "*.svg")))
total = len(files)
t0 = time.time()
done = skipped = failed = 0

for f in files:
    out = os.path.join(dst, os.path.splitext(os.path.basename(f))[0] + ".png")
    if os.path.exists(out):
        skipped += 1
        continue
    try:
        doc = pymupdf.open(f)
        page = doc[0]
        z = size / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=True)
        pix.save(out)
        doc.close()
    except Exception as exc:  # noqa: BLE001
        failed += 1
        print("ERR", os.path.basename(f), type(exc).__name__, exc, flush=True)
        continue
    done += 1
    if done % 250 == 0:
        print(f"{done}/{total} {time.time() - t0:.0f}s", flush=True)

print(f"DONE total={total} converted={done} skipped={skipped} failed={failed} {time.time() - t0:.0f}s", flush=True)
