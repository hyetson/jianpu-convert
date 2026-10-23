# 排版参数

在转换配置 JSON 中修改 `fonts` 和 `layout`，无需修改 TypeScript 源码。完整示例见 [configs/single-voice-layout.example.json](../configs/single-voice-layout.example.json)。该示例保留当前样张的 14 pt 数字、40 pt 页边距和全部样式默认值。

未填写的字段沿用默认值；嵌套对象也逐项合并。例如只填写 `layout.notation.accidentalGap`，其他符号参数继续沿用默认值。字段名拼错、非数值、非法尺寸或最低间距超过常规间距会报错，避免配置被静默忽略。

## 字体

| 字段 | 用途 | 省略时 |
| --- | --- | --- |
| `fonts.text` | 标题、调号/拍号、文字提示 | 必填 |
| `fonts.numbers` | 简谱数字、休止符 0、附点 | 使用 `fonts.text` |
| `fonts.music` | 升降号、还原号、音乐装饰符号 | 必填 |
| `fonts.termsRegular` / `termsBold` / `termsItalic` / `termsBoldItalic` | 西文音乐术语、节拍速度数值 | PDFKit Times 系列；完整梆笛配置使用本机 Times New Roman |
| `fonts.restCounts` | 多小节休止计数；支持单个文件或非空文件列表 | 使用 `fonts.text` |
| `fonts.measureNumbers` | 方框小节号；支持单个文件或非空文件列表 | 使用 `fonts.text` |

值为本地字体文件路径，支持项目相对路径或绝对路径。数字与符号按所选字体的实际字形边界重新定位。音乐字体需要包含当前使用的 SMuFL 字形，例如项目中的 Bravura。

完整示例显式填写了 `fonts.numbers`；如需让数字跟随文字字体，可删除这一项。修改文字字体时不会自动改掉显式指定的数字字体。配置不会安装或下载字体。

当前示例的数字字体已试换为本地 Arial Bold（`C:/Windows/Fonts/arialbd.ttf`），用来接近参考谱的粗体数字字形；原字体名称尚未确认。依据和边界见 [字体试配记录](REFERENCE_FONT_REVIEW.md)。

## 单位与基础项

大小、字号、间距及定位距离均为 **pt**，1 pt = 1/72 英寸。名称以 `Ratio` 结尾的字段和 `Scale` 为无单位比例，多数以简谱数字字号为基准。

| 字段 | 原有全局默认值 | 作用 |
| --- | --- | --- |
| `layout.fontSize` | 13 | 简谱数字字号；允许 8-36 pt |
| `layout.margin` | 35 | 页边距；允许 15-100 pt |
| `layout.pageSize` | A4 | A4 或 A3 |
| `layout.maxMeasuresPerSystem` | 4 | 每行优先四小节；最低可读宽度无法容纳时减少，末行保留剩余小节 |
| `layout.compressRests` | true | 是否合并连续整小节休止 |

## 常用细节

以下字段均放在 `layout` 对应子对象下。完整字段及其默认值已经列入示例配置；可删除不需要单独设置的项。

| 分组 / 字段 | 默认值 | 作用 |
| --- | --- | --- |
| `notation.accidentalGap` | 0.5 | 升降号与数字之间的水平空隙 |
| `notation.accidentalScale` | 0.8 | 升降号字号 / 数字字号 |
| `notation.accidentalTopOffsetRatio` | 0.12 | 升降号中心相对数字上缘向下的偏移比例；较小值使符号更靠上 |
| `notation.upperDotGap` | 3 | 高音点中心距数字上缘 |
| `notation.lowerDotGap` | 4 | 低音点中心距最下层减时线或数字下缘 |
| `notation.dotRadius` / `dotStackGap` | 1 / 3.5 | 八度点半径 / 多个八度点的中心间距 |
| `notation.underlineGap` / `underlineLayerGap` | 3 / 2.5 | 数字下缘到减时线 / 减时线层间距 |
| `notation.underlineWidth` | 0.8 | 减时线粗细 |
| `notation.underlineLengthRatio` / `underlineLeftExtension` | 0.7 / 1 | 减时线在末尾数字右侧的长度比例 / 向首个数字左侧延伸距离 |
| `notation.dashLengthRatio` / `dashWidth` | 0.5 / 0.9 | 延时横线长度比例 / 粗细；始终对齐数字中部 |
| `notation.graceScale` / `graceOffsetY` / `graceOffsetXRatio` | 0.67 / 12 / 0.5 | 倚音缩放、向上偏移、向左偏移比例 |
| `context.initialFontSize` | max(14, 数字字号) | 开头主调字号；上下拍号另按小节线高度设置 |
| `context.initialOffsetX` / `initialOffsetY` | 0 / 68 | 相对第一小节线向右偏移 / 相对数字定位行向上偏移 |
| `context.changeFontSize` | 8 | 变调处字号；变拍使用 `layout.meter` |
| `context.changeOffsetX` / `changeOffsetY` | 12 / 25 | 变化标注相对所在小节线向右偏移 / 向上偏移 |
| `measureNumbers.fontSize` | 全局 9；Maestro 示例 18 | 方框小节号字号；Maestro 数字实际高度约为字号一半 |
| `measureNumbers.minimumWidth` / `height` | 16 / 16 | 方框最小宽度 / 最小高度；根据字形和留白自动扩大 |
| `measureNumbers.paddingX` | 4 | 框内左右各侧留白；多位小节号按需扩宽 |
| `measureNumbers.paddingY` / `digitGap` | 2 / 0.6 | 框内上下各侧最小留白 / 数字原生字距之外的额外间隔 |
| `measureNumbers.offsetY` / `lineWidth` | 35 / 0.7 | 方框上缘距数字定位行的向上距离 / 框线粗细 |
| `barlines.halfHeightRatio` / `lineWidth` | 0.8 / 0.7 | 小节线半高相对数字字号 / 普通小节线粗细 |

如果省略 `context.initialFontSize`，它随数字字号自动取 max(14, 数字字号)。完整示例显式填了 14；希望自动跟随时删除此项。横向定位值为正表示向右；上述向上距离为正表示向上，可使用负值反向移动。

## 节内间距与行距

| `spacing` 字段 | 默认值 | 作用 |
| --- | --- | --- |
| `columnWidthRatio` / `minimumColumnWidthRatio` | 0.95 / 0.8 | 常规音符间隔的基准 / 压缩时的基准 |
| `beatGapRatio` / `minimumBeatGapRatio` | 0.6 / 0.28 | 拍边界额外空隙 / 压缩时的额外空隙 |
| `leftPaddingRatio` / `rightPaddingRatio` | 0.9 / 0.75 | 小节首尾预留空隙；居中时还会整体调整左右留白 |
| `durationSpacingRatio` | 1.35 | 按音符起始时间间隔的平方根计算空间时使用的系数 |
| `augmentationSpaceRatio` | 0.3 | 每个附点预留的额外宽度比例 |
| `accidentalSpaceRatio` / `doubleAccidentalSpaceRatio` / `microtoneSpaceRatio` | 0.3 / 0.5 / 1.3 | 普通变化音、重升降、其他变化音的预留宽度比例 |
| `minimumCompressionRatio` | 0.82 | 每个间隔至少保留常规宽度的此比例，范围 (0,1] |
| `rowHeight` / `systemGap` | 54 / 31 | 单声部行的基础高度 / 谱表行之间的附加空隙 |
| `baselineOffset` | 30 | 数字定位行相对谱表行顶的向下距离 |
| `chordSpacingRatio` | 1.55 | 堆叠和弦数字之间的纵向间隔比例 |

升降号的实际字形宽度、缩放和间隔也参与最小空间计算。即使调大 `accidentalGap` 或 `accidentalScale`，也会预留相应空间。

每行仍使用结束小节填满行宽。改变字号或间距会重新计算断行，因此小节数及分页可能改变。增大数字字号时，可以同时增大行距；小节号方框按实际字形扩大。

## 圆滑线与延音线

`fonts.measureNumbers` 在完整示例中使用与休止计数相同的 Maestro 子集；只改变小节号和休止计数，普通音符仍使用 Arial Bold。

以下字段放入 `layout.curves`，单位均为 pt，省略时使用默认值：

| 字段 | 默认值 | 作用 |
| --- | --- | --- |
| `slurHeight` / `tieHeight` | 12 / 6 | 圆滑线 / 延音线控制点的初始拱高 |
| `maximumHeight` | 44 | 避让时控制点拱高的上限；仍有碰撞时整条连线各段统一增大端点间隔 |
| `clearance` | 3.5 | 曲线与数字、八度点、减时线的间隔；梆笛完整配置为 2.5，装饰记号另排在曲线上方 |
| `laneGap` | 5 | 嵌套连线的层间距 |
| `lineWidth` | 0.7 | 曲线线宽 |
| `edgeInset` | 12 | 跨行接续端距行边界的内缩；行首同时避开小节号框 |
| `dashLength` / `dashSpace` | 3 / 2 | 虚线段长度 / 间隔；点线采用短点 |
| `collisionStep` | 2 | 避让迭代中每次增加的拱高 |
| `annotationGap` / `annotationStackGap` | 3 / 2 | 上方记号距连线的最小间隙 / 多个记号的堆叠间隙 |

连线保留源事件起止、上下位置和实/虚/点线。源五线谱的几何坐标保留作审计信息，简谱按自己的断行重算曲线。详见 [连线排版与核对](CURVE_LAYOUT.md)。

`layout.justifyLastSystem` 默认 `false`，末行保留自然宽度；设为 `true` 则末行也拉满。其余行保持铺满。

## 按拍数调整小节宽度

`spacing.measureWidthRatio` 默认 9，定义 4/4 稀疏小节的基础宽度为主字号的 9 倍；`spacing.meterWidthBias` 默认 1，给每小节保留相当于一个四分音符的固定空间。若小节长度以四分音符计为 L，其基础比例为 `(L + bias) / (4 + bias)`：2/4 为 0.6，3/4 为 0.8，3/8 为 0.5。bias 可设为 0，得到纯拍数比例。

基础宽度和音符所需宽度取较大值；数字、升降号、附点、拍间留白和倚音的最低可读间隔继续生效。多小节休止横线也按拍数比例调整，但不能短于计数的实际字形宽度。

`layout.meterAwarePacking` 默认 true，使 `maxMeasuresPerSystem` 成为等效 4/4 小节容量。例如默认容量 4 可排六个 2/4 小节，也可以排混合拍号的小节；内容密集时实际数量减少。设为 false 可恢复小节数硬上限，值为 1 时始终保持单小节一行。整行仍按各小节的内容需求分配留白，末行默认按自然长度收尾。

`measureLayout` 在渲染报告中记录基础宽度、实际宽度、最低可读宽度、拍数比例、拍号和小节位置，方便核对断行结果。

`layout.wedges` 控制渐强、渐弱：`height`（最大开口，默认 8 pt）、`offsetY`（相对音符行的下移，默认 36 pt）、`lineWidth`（0.7 pt）、`edgeInset`（换行接续处内缩，3 pt）。长度由原谱起止小节及拍位决定，不提供固定长度。换行和换页时按全段进度计算开口，保持连续。

`layout.meter` 设置小节起始处的上下分数式拍号；`layout.terms` 设置音乐术语及节拍速度的字号和位置；`layout.graces` 控制倚音下方连接到主音的小钩。详见 [拍号、音乐术语与倚音](METER_TERMS_GRACES.md)。

## 文字与页眉

新增 `layout.rests` 可配置短休止段的合并阈值、休止横线宽度与粗细、端线高度、计数字距和四个 0 的内缩。字段、默认值与 Maestro 配置见 [空小节排版](REST_LAYOUT.md)。

`typography` 设置标题、续页标题、副标题、作曲者、状态文字、乐器名、提示文字、页码、连音组数字、微分音回退文字、连续休止计数和反复符号的字号，字段分别为 `titleSize`、`continuedTitleSize`、`subtitleSize`、`composerSize`、`statusSize`、`partLabelSize`、`annotationSize`、`pageNumberSize`、`tupletSize`、`microtoneSize`、`restCountSize`、`repeatSize`。

`header` 设置这些固定区域的距离：`subtitleOffsetY`、`composerOffsetY`、`statusOffsetY`、`continuedStatusOffsetY` 是相对页边距的向下距离；`firstSystemOffsetY`、`continuedSystemOffsetY` 是首条谱表行相对页边距的向下距离；`footerOffsetY` 是页码相对下边距的向上距离。

## 只覆盖需要改变的项

下面是配置的局部片段，合并到已有转换配置中：

```json
{
  "fonts": {
    "text": "C:/Windows/Fonts/NotoSerifSC-VF.ttf",
    "numbers": "C:/Windows/Fonts/arial.ttf",
    "music": "tools/fonts/Bravura.otf"
  },
  "layout": {
    "fontSize": 16,
    "notation": {
      "accidentalGap": 0.8,
      "upperDotGap": 3.5,
      "lowerDotGap": 4.5
    },
    "context": { "initialFontSize": 16 },
    "spacing": { "rowHeight": 62, "systemGap": 34 }
  }
}
```

复现当前默认样张：

```powershell
& .\scripts\build.ps1
& .\.venv\Scripts\python.exe scripts\make-beat-layout-fixture.py
& .\.venv\Scripts\python.exe -m jianpu from-musicxml --config configs\single-voice-layout.example.json --overwrite tmp\beat-layout\single-voice.musicxml
```

每次运行的 `.render.json` 和 `report.json` 中的 `render` 会保存 `layoutResolved`、字体路径和实际断行，便于复现。完整示例的 `parts` 与输出仍是梆笛布局练习的配置；应用到其他谱面时修改标题、输入、输出和对应乐器信息。

当前构建共 128 项测试通过（79 项 Node、49 项 Python），覆盖参数合并、错误参数拒绝、字体独立设置、实际字号和定位变化、行距影响分页、连线配对及跨行跨页接续，以及吹管跳音过滤、技法字形、震音语义、力度下标锚点、单声部入口和局部双声部布局。字体试配依据另见字体试配记录。

力度下标的距离使用 `layout.terms.dynamicsGap`（默认 4 pt），按音符的实际下缘（包括减时线和低音点）计算。力度字号仍为 `layout.terms.dynamicsSize`。顶层 `dynamicsPlacement` 默认为 `below`；设为 `source` 时保留原 above/below。统一入口与默认配置见[单声部方案](SINGLE_VOICE.md)。

## 特殊技法

`parts[].instrumentFamily` 指定 `wind / bowed / plucked / struck-string / unknown`，缺省 `unknown`。顶层 `techniques.windStaccato` 为 `hide`（默认）或 `show`；隐藏仅作用于已指定为吹管的跳音点，不影响其他音乐点。

`layout.techniques` 的可配置参数如下。距离、线宽、字号单位为 pt，Ratio 为比例；未指定时使用下列默认值。

| 参数 | 默认值 | 用途 |
| --- | --- | --- |
| `symbolSizeRatio` | 1 | 音乐技法字形字号相对当前数字字号 |
| `textSize` | 8 | 中文技法和指法等文字标注字号 |
| `aboveGap` | 4 | 技法字形与音符/八度点外轮廓的基础间隔 |
| `lineWidth` | 0.7 | 震音、琶音矢量线宽 |
| `tremoloWidth` / `tremoloGap` / `tremoloRise` | 9 / 3 / 4 | 单音震音斜线宽、各短杠间隔、倾斜高度 |
| `arpeggioGap` / `arpeggioWidth` | 4 / 4 | 琶音距音符/升降号的间隔、曲线控制点偏移 |
| `arpeggioWaveHeight` / `arpeggioArrowSize` | 5 / 3 | 琶音单波高度、方向箭头尺寸 |

`techniqueLayout` 记录画出的字形/矢量图形、文字回退及被隐藏的原记号；`noteSymbols` 记录八度点与短音附点，供核对隐藏范围。对应规则、来源及样张复现命令见[特殊技法参考](CHINESE_INSTRUMENT_TECHNIQUES.md)。

上标的贴近间隔、连线首尾上移量、文字上层间隔，以及连音数字字号、组线高度、线宽与数字空隙，见[上标与连音组参数](ORNAMENTS_TUPLETS.md)。

局部双声部的最小行距、完整行头名称字号、名称距小节线的间隔分别为 `layout.localVoices.rowGap`（72 pt）、`labelSize`（10 pt）、`labelGap`（10 pt），在 `local-dual-voice` 模式下使用。标签按“乐器名I / 乐器名II”生成，双行组内上下声部位置固定。完全单声部的谱行仍使用原来的 `spacing.rowHeight`，和弦额外高度仍由 `spacing.chordSpacingRatio` 控制。默认配置无和弦时组内为 72 pt、组间为 112 pt。见[局部双声部规则](LOCAL_DUAL_VOICE.md)。
