---
name: schedule-poster
description: "When the user wants a themed weekly schedule poster (播表/周历/直播日程) plus an editable web page, given a style/theme and a portrait image."
---

# 播表海报 / Schedule Poster

做主播周历、播表、日程图：**最终交付物是一个单文件网页 `播表编辑器.html`**，
用户在里面直接改字、存图。过程中出的成品图（3200×1800）只是用来挑风格的中间产物，
**不是交付物** —— 别把图当成果甩给用户。

用户只需要给两样：**风格**（赛博朋克 / 魔法 / 修仙……一句关键词或一张参考图）和**人像**。
内容给不给都行，没有就先放占位。

**基准长这样**：`resources/reference/基准-白底赛博.png`（白底赛博版，做到这个程度才算框架完成）。
`resources/reference/蓝黑粗框-海报.png` 和 `蓝黑粗框-模板/` 是另一个完成度参考（细框 → 粗框、缩卡片）。

---

## 开工前只问三件事

1. **风格**：一句关键词，或者直接甩一张参考图。
2. **人像**：图片路径。
3. **内容**：这周的日子、时段、节目名。不给就用模板内容先出图，让用户在网页里自己改。

**不要问**尺寸、配色、字体、几列几行 —— 这些你定。用户是来看结果的。

---

## 四步走

### 第 1 步：人像（**先问要不要抠图**）

开工第一句就问：**「人像要我帮你抠图吗？」** 等回答，别自作主张。

- 用户**要抠** → 跑 `python scripts/cutout.py 原图.png 项目/portrait.png 250 2`，
  抠完 `read_image` 看一眼：衣服里的白色有没有被吃掉、头发边缘有没有残留白边。
- 用户**不抠** → 直接用原图，并且**把主题改成浅色**。白底图放白纸主题里天然没有白边，
  硬抠反而容易伤细节。这条是 `pitfalls.md` 第 9 条。

判断依据：**白底图 + 浅色主题 = 不抠**；**透明底 / 深色主题 / 要压在照片或图案上 = 必须抠**。

### 第 2 步：收素材

按主题抓一轮，全部落在项目目录里，后面两步都要用：

```bash
python scripts/fetch_fonts.py 项目/fonts "Orbitron:400,700,900" "ZCOOL QingKe HuangYou:400:chinese-simplified"
python scripts/fetch_assets.py --out 项目/assets --icons --patterns
```

- 字体 4~6 款：中文标题字 1 个、等宽 1 个、数字/拉丁 1~2 个、正文用系统黑体。
- 图标从 `assets/icons/` 里挑 7~10 个贴主题的，复制到 `项目/icons/`。
- 图案（Kenney CC0，84 组）留着做背景，`assets/patterns/svg/` 里是纯黑矢量，改色只替换 `#000000`。
- 不要停在「下载完」——**第 4 步的夸张背景全靠这批素材**，所以这一步要贪心一点。

### 第 3 步：搭框架（做到基准图的完成度）

```bash
cp resources/theme.white-cyber.json 项目/theme.json   # 改配色和字体
cp resources/content.example.json   项目/content.json  # 改文案
python scripts/render_poster.py 项目/theme.json 项目/content.json 项目/播表.png
```

框架这一步**只做结构，不上重装饰**，验收标准是 `resources/reference/基准-白底赛博.png`：
页头 / 7 天 4+3 栅格 / 右侧人像列 / 页脚，字号层级对、卡片切角对、人像不出白边、文字不顶格。

**必须 `read_image` 看结果**，重点查四样：文字有没有顶出卡片、人像边缘干不干净、
数字认不认得出来（尤其 8、0、6）、底部有没有大片死白。

### 第 4 步：上背景 —— **首轮直接出三版**

框架过了才动背景。**第一次交付就给三个版本**，不要只给一版等反馈：

| 版本 | 打法 | 关键参数 |
| --- | --- | --- |
| **V1 撞色** | 从人像取 3 个主色做撞色，**定完色必须再用素材点缀背景**，否则就是一屏纯色块 | `palette.py` + 6%~15% 装饰层 |
| **V2 夸张图形** | 把第 2 步的素材**放大 6~10 倍**，旋转叠压，做成图形堆叠背景 | 在 `background()` 里加一层 |
| **V3 图片底** | AI 绘图（或合规网图）出一张主题图当底，再撒少量素材点缀 | `effects.image` + `scrim` |

三版都要摆在同一个项目里、同名不同后缀（`播表-V1撞色.png` / `-V2图形.png` / `-V3图底.png`），
让用户并排挑。具体配方和踩坑见 `references/versions.md`。

### 第 5 步：出网页编辑器

框架定了再做编辑器，别反过来 —— 编辑器是「框架的 HTML 版」，背景三版之后再按用户选中的那版同步。

```bash
cp resources/editor_template.html 项目/editor_template.html
# 改三处：:root 配色、@font-face 路径、正文文案
python scripts/build_editor.py --template 项目/editor_template.html \
  --out 项目/播表编辑器.html --fonts 项目/fonts \
  --portrait 项目/portrait.png --icons 项目/icons --cache .cache
```

产物是 8MB 左右的**单文件**：字体、人像、图标、导出库全内嵌，发给谁双击都能用。

### 第 6 步：交付 —— **交的是网页，不是图片**

主交付物永远是 `项目/播表编辑器.html`。三张候选图只是让用户挑风格的过程产物；
用户挑完、配色同步进编辑器之后，**回复里必须写清这个网页的完整路径**，并说清四件事：

1. **路径**：`D:/…/项目/播表编辑器.html`，写到文件名，别只说「在项目文件夹里」。
2. **怎么开**：双击，用 Chrome / Edge。单个文件，直接发人也行，不用带别的文件。
3. **怎么存**：「存成 PDF」最保真；「存成图片」的切角会变直角（坑 #8）。
4. **怎么留**：改字自动存在本机浏览器，换电脑或清缓存就没了。

图片可以顺带给，但**摆在第二句**。第一句必须是这个网页在哪。

README 另写三件事：怎么改字、授权（字体 OFL / 图标 ISC / Kenney CC0）、
以及「存成图片」和「存成 PDF」的区别。

---

## 硬规则 —— 这几条不遵守会翻车

1. **不要试图用浏览器截图出图。** 这类沙箱常禁命名管道，Chrome/Edge/git 都起不来。
   用 `render_poster.py` 直画，稳得多。真需要浏览器，先问用户。
2. **PIL 的 `paste` 会忽略源图 alpha。** 半透明面板会变成实心色块。
   要么 `alpha_composite`，要么最后把整张图压到不透明纸色上再存。
3. **Pillow 13 已移除 `ImageDraw.floodfill`。** 抠图用 `scripts/cutout.py`，别找现成 API。
4. **Google Fonts 要老 UA。** Safari 3.1 的 UA 才给 TTF；现代 UA 给 woff2，IE6 给 EOT。
   中文家族必须加 `:400:chinese-simplified`，否则只拿到几万字里的一小片。
5. **注意哪些域名能通。** `raw.githubusercontent`、`cdn.jsdelivr`、`fonts.google.com` 常常不通；
   `registry.npmjs.org`、`unpkg.com`、`codeload.github.com`、`kenney.nl` 一般可用。先探测再下。
6. **导出图片要求资源是 data URL。** `file://` 下的本地图片会污染 canvas，
   `toDataURL` 直接抛错。`build_editor.py` 已经全部内嵌，别手动改回去。
7. **小字号别用装饰字体。** Orbitron 的 8 像 B、0 像方框；站酷庆科黄油体小字看不清。
   数字用 Chakra Petch / Oxanium，中文正文用系统黑体。
8. **切角在图片导出里会丢。** `clip-path` 不被 html2canvas 支持，「存成图片」出来是直角；
   `存成 PDF` 才是 1:1 保真。交付时要跟用户讲清楚。
9. **先框架后背景。** 背景一上就很难再判断栅格和字号问题，返工成本翻倍。

更细的排查和替代方案见 `references/pitfalls.md`。

---

## 参数速查

所有字号在 `theme.type` 里，一处改全局生效：

| 用户怎么说 | 怎么调 |
| --- | --- |
| 「字体调大」 | 全部 +2~3，正文和时段优先 |
| 「标题再大」 | 只改 `title`、`version` |
| 「太挤」 | 加 `layout.gap`，或减 `cols` |
| 「换个颜色」 | 只改 `colors.accent` / `accent2` |
| 「人像太小」 | 加 `layout.aside`，或把人像挪到左侧 |
| 「再花哨些」 | 加 `effects.decor` 层数，别加字号 |
| 「卡片小一点」 | 减 `layout.card`，同时加 `gap` 保持居中 |
| 「边框粗一点」 | 加 `layout.border`，投影跟着加 |

---

## 自检清单

交付前逐条过：

- [ ] 问过用户要不要抠图，并且按回答执行了
- [ ] 素材真的落盘在项目里，不是「凭印象画」
- [ ] 框架达到 `resources/reference/基准-白底赛博.png` 的完成度
- [ ] 首轮给了三个版本，且三版**明显不同**（不是同一个底换个色）
- [ ] 撞色版也撒了素材（页头/页边/卡片缝/水印），不是只有颜色没有细节
- [ ] 成品图里每行文字都没顶出卡片（最长的两行重点看）
- [ ] 人像没有硬切边、没有白边、没被卡片挡住脸
- [ ] 时间、日期一眼能读
- [ ] 编辑器能打开、能改字、能存图片
- [ ] **回复里写了 `播表编辑器.html` 的完整路径**，并明确交付物是这个网页而不是图片
- [ ] README 写了授权和「图片 vs PDF」的区别
- [ ] 没有留下 `__PORTRAIT__`、`__HTML2CANVAS__` 这类占位符
