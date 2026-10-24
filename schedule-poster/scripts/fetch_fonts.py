#!/usr/bin/env python
"""抓 Google Fonts 的 TTF（不是 woff2，也不是 EOT）。

关键点:
  * 用老 Safari 3.1 的 UA，Google 才会给真 truetype。现代 UA 给 woff2，
    IE6 的 UA 给 EOT（文件头和 TTF 完全不一样，装不上）。
  * 中文家族必须加 &subset=chinese-simplified，否则拿到的是几十个
    unicode-range 切片里的一小片（几万字只剩几十 KB）。

用法:
    python fetch_fonts.py 输出目录 "Orbitron:400,700,900" "ZCOOL QingKe HuangYou:400:chinese-simplified"
"""
import os
import re
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.19 "
      "(KHTML, like Gecko) Version/3.1 Safari/525.19")
HDR = {"User-Agent": UA}


def fetch(url, timeout=90):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=timeout).read()


def kind(b):
    return {b"\x00\x01\x00\x00": "TTF", b"true": "TTF", b"OTTO": "OTF",
            b"wOFF": "WOFF", b"wOF2": "WOFF2"}.get(b[:4], "?")


def grab(family, weights="400", subset=None, out="fonts"):
    os.makedirs(out, exist_ok=True)
    url = "https://fonts.googleapis.com/css?family=" + urllib.parse.quote(family) + ":" + weights
    if subset:
        url += "&subset=" + subset
    css = fetch(url).decode()
    blocks = re.findall(r"@font-face\s*{(.*?)}", css, re.S)
    if not blocks:
        print("  空 CSS:", family)
        return 0
    n = 0
    for b in blocks:
        wm = re.search(r"font-weight:\s*(\d+)", b)
        um = re.search(r"url\((https://[^)]+)\)", b)
        if not um:
            continue
        data = fetch(um.group(1))
        w = wm.group(1) if wm else "400"
        ext = ".ttf" if kind(data) == "TTF" else ".otf"
        name = f"{family.replace(' ', '')}-{w}{ext}"
        with open(os.path.join(out, name), "wb") as f:
            f.write(data)
        print(f"  {name:38s} {len(data)/1024:7.0f}KB  {kind(data)}")
        n += 1
    return n


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    out = sys.argv[1]
    for spec in sys.argv[2:]:
        parts = spec.split(":")
        fam = parts[0]
        w = parts[1] if len(parts) > 1 and parts[1] else "400"
        sub = parts[2] if len(parts) > 2 and parts[2] else None
        try:
            grab(fam, w, sub, out)
        except Exception as exc:  # noqa: BLE001
            print("  ERR", fam, type(exc).__name__, exc)
