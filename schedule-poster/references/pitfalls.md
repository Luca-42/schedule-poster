# 踩过的坑 & 替代方案

按「会直接卡死流程」到「只是不好看」排序。

---

## 1. 沙箱里浏览器起不来

Chrome 报 `mojo platform_channel` / `crashpad OpenProcess 拒绝访问`，
Edge 一样，`git clone` 会报 `cannot create standard input pipe`。
根因是沙箱禁止命名管道，不是权限问题，换 `--no-sandbox` 也没用。

**结论**：不要规划「用浏览器截图出图」这条路。
出图走 `render_poster.py`（PIL 直画），网页只作为交付物交给用户，不参与渲染。
如果确实必须渲染 HTML，先问用户要不要放开沙箱。

## 2. PIL `paste` 忽略 alpha → 半透明面板变实心

```python
base.paste(grad, (x, y), mask)   # mask 只控制"混合多少"，grad 的 alpha 被丢弃
```

表现：设计成 8% 透明的卡片全是高饱和实心色块（我第一次就是整张图糊成粉紫）。

**修法**（二选一）：
- `base = Image.alpha_composite(base, layer)`，把每层半透明内容画在独立图层上；
- 或者最后统一压平：`Image.alpha_composite(Image.new("RGBA", size, paper+(255,)), base)`。

第二种最省事，一行修好所有直绘的半透明文字和线条。

## 3. Pillow 13 没有 `ImageDraw.floodfill`

抠白底不能用它。`scripts/cutout.py` 用 `deque` 做 BFS 找边界连通区，
在半分辨率上跑（快 4 倍），再把 alpha 放大回去。

**关键**：阈值取 250 而不是 255 附近，才不会把白色衣服一起抠掉；
只扩散「和画布边缘连通」的白，衣服内部的白色是封闭区域，安全。

## 4. Google Fonts 的坑

| 现象 | 原因 | 修法 |
| --- | --- | --- |
| 字体装不上，文件头是 `3c3e0000` | IE6 UA 返回 EOT | 换 Safari 3.1 UA |
| 拿到 woff2 | 现代 UA | 同上 |
| 中文只有 26KB | 只取了 unicode-range 切片之一 | 加 `&subset=chinese-simplified` |
| 多字重只回一个 | 可变字体被合并成默认字重 | 要么接受，要么用静态家族 |

## 5. 域名可达性（国内网络）

| 通道 | 状态 |
| --- | --- |
| `registry.npmjs.org` | 通，最稳，npm 包直下 |
| `unpkg.com` | 通 |
| `codeload.github.com` | 通（整仓 zip） |
| `kenney.nl` | 通，CC0 素材直链可抓 |
| `api.github.com` | 通 |
| `raw.githubusercontent.com` | 不通 |
| `cdn.jsdelivr.net` | 不通 |
| `fonts.google.com`（下载页） | 不通 |
| `upload.wikimedia.org` | 不通 |
| `itch.io` | 不通 |

所以素材走 **npm 包 + unpkg + Kenney 官网直链**，字体走 **fonts.googleapis.com 的 CSS 接口**。

## 6. 导出图片：本地图片会污染 canvas

`html2canvas` 把 DOM 画到 canvas 上，只要里面有一张 `file://` 的图，
canvas 就被标脏，`toDataURL()` 直接抛 `SecurityError`。

**修法**：字体、人像、图标全部转 data URL 内嵌（`build_editor.py` 已做）。
代价是单文件 8MB 左右（中文标题字体 5.5MB 占了大部分），换来「一个文件发给谁都能用」。

如果嫌大：把中文标题字体换成系统字体，能砍到 1MB 以内。

## 7. 小字号用错字体

- **Orbitron**：`8` 长得像 `B`，`0` 是个方框。小字号下 `08.08` 读起来像 `0B.0B`。
  → 日期换 Chakra Petch / Oxanium，Orbitron 只留给超大标题。
- **ZCOOL 庆科黄油体**：设计给大字的，14px 时「公」和「版」会糊成一团。
  → 16px 以下的中文一律换微软雅黑。

## 8. `clip-path` 在导出时会丢

卡片切角是用 `clip-path: polygon(...)` 做的，浏览器里显示正常，
但 `html2canvas` 不支持，导出的 PNG 会变成直角。

**处理**：交付时明确说「要完全一致就用存成 PDF」。
想两边一致的话，把切角改成「右下角贴一个旋转 45° 的纸色方块」，这是纯元素，导得出。

## 9. 白底人像到底要不要抠

不用。**浅色主题下白底人像直接贴，边缘天然融合**，比抠图干净得多——
抠图会在衣服浅色处留灰边，羽化过度还会出现一圈光晕。

只有深色主题才需要抠。这是选配色时最该先想清楚的一点。

## 10. 7 天排 4+3 会留一个洞

第二行只有 3 张卡，右下角空一格，视觉上很突兀。
补一张「公告 / NOTICE」卡正好填满，还多给了用户一个能写东西的地方。
