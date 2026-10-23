# 技法上标、文字与连音组排版

2026-10-20 更新。直接由 PDFKit 绘制，不经过 LilyPond。

## 技法上标与文字层次

`tr`、上/下波音、延长号等先以音乐字形的实际边界定位，字形底部默认距音符及其八度点外轮廓 2 pt。颤音的辅助升降号位于 `tr` 上方，与颤音作为一个整体避让；它不改变主音的升降号。

普通乐句线从音符上方经过时，不再将整组上标推到弧线最高处。只有上标所属音符恰好是连线首尾时，才允许最多 3 pt 的额外上移；允许与端点附近的弧线有少量接近/重合。多个同音上标仍逐层避让。

换笛说明、速度词等文字最后排版，位于相应上标（包括辅助升降号）上方。文字和节拍速度在同一拍位时作为一组移动，保留原有并列关系。第 99 小节现在按“C梆笛 → 辅助降号 → tr → 八度点及音符”的层次排放。

## 连音组

连音组 `tuplet` 与圆滑线 `slur`、同音延音线 `tied` 分开建模。优先使用源 MusicXML 的连音组起止、组号、显示比例及线型；相同起止的已有圆滑线可复用，避免画两条重合线。

- 组线中央显示连音数，数字采用 Bravura 的 SMuFL `tuplet0` 至 `tuplet9` 字形，需要比例时用 `tupletColon`。组线在数字两侧留空，不用白色矩形覆盖已有内容。
- 默认简谱采用弧形组线；原谱明确指定 straight 时采用带端部短钩的直括线。`bracket=no`、`show-number=none/both` 等明确指令保留。
- 有明确端点的组允许混合时值。例如三连音可以由一个四分音符与一个八分音符构成，不能机械按“数到三个事件”确定结束。
- 没有显式端点时，仅对完整、连续、同记谱类型、等时值的比例音列回退分组。残缺组报告待校对，不跨缺口猜测。
- 跨行/跨页按源端点分段，延续段保留中央数字。倚音不参与普通连音组事件计数。
- 普通圆滑线没有时间比例证据时，不会被解释为三连音或五连音。

**连音数与占拍分别保留。** 样张的三个八分三连音 `3:2`、五个十六分五连音 `5:4` 都占一个四分音符拍。真实梆笛第 75 小节的七连音占一拍，第 107 小节的六连音占半拍；输出保留其原始精确时值，不将所有带数字的连音组强制改为一拍。

语义依据见 [MusicXML tuplet](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/tuplet/)；字形依据见 [SMuFL Tuplets](https://smufl.formats.music/latest/tables/tuplets.html)。前者区分显示分组与实际时间比例，后者提供连音数字字形并建议用矢量图元绘制组线。

## 参数

以下距离、线宽与字号均为 pt，保留 JSON 可配置性。

| 配置字段 | 默认值 | 用途 |
| --- | --- | --- |
| `layout.techniques.ornamentGap` | 2 | 技法字形底部与音符外轮廓的间隔 |
| `layout.techniques.endpointLift` | 3 | 连线首尾允许的额外上移量 |
| `layout.techniques.curveOverlap` | 1.5 | 首尾处上标与曲线的容许接近/重合量 |
| `layout.techniques.textGap` | 3 | 文字与上标之间的最小间隔 |
| `layout.tuplets.numberSize` | 16 | 连音数音乐字体字号；实际墨迹高度约 6 pt |
| `layout.tuplets.curveHeight` | 5 | 独立连音弧的基础拱高 |
| `layout.tuplets.clearance` | 3 | 连音弧与音符/上标的基础间隔 |
| `layout.tuplets.numberGap` | 2 | 数字左右各留出的组线空隙 |
| `layout.tuplets.lineWidth` | 0.65 | 连音组线宽 |

`annotationLayout` 记录 `noteTop`、`baseBottom` 和最终位置，便于核查上标贴近程度。`tupletLayout` 独立记录组的起止事件、音符集合、actual/normal、实际时长、字体、数字位置及续行信息。原始 XML 属性与显示比例保存在事件 marks 中。

## 复现与验证

```powershell
& .\scripts\build.ps1
& .\.venv\Scripts\python.exe scripts\make-ornament-tuplet-example.py
& .\.venv\Scripts\python.exe scripts\verify-ornament-tuplet-example.py
& .\.venv\Scripts\python.exe -m jianpu from-musicxml --config configs\bangdi-full.json --draft --overwrite output\jianpu\bangdi-full-source\bangdi-reviewed.musicxml
& .\.venv\Scripts\python.exe scripts\verify-bangdi-full.py
```

一页人工样张输出到 `output/jianpu/技法上标与连音组_排版示例.pdf`，包含四个上标、文字层次、三连音、五连音及混合时值三连音。它用于排版验收，不作为真实 PDF 的 OMR 识别证据。完整梆笛仍输出到原来的生成 PDF，保持 6 页、254 小节。
