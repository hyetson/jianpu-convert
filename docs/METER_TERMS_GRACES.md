# 拍号、音乐术语与倚音

完整梆笛配置使用 PDFKit 直接绘制矢量符号，不经过 LilyPond。

## 拍号

初始主调仍置于第一小节号上方，旁边的初始拍号改为上下分数式。后续仅在拍号变化的小节起始处，紧随左小节线排上下叠放的拍号；不在换行处重复。分子、分母采用 Bravura 的 SMuFL 拍号字形，按用户要求加细分数横线。

拍号的总高度默认是小节线高度的 1.18 倍，并为它保留独立横向空间。休止横线、四分休止 0、倚音及普通音符均从拍号右边的音乐区域开始。多小节休止也保留这一空间。

`layout.meter` 参数（pt，Ratio 为比例）：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `heightRatio` | 1.18 | 拍号总高度相对小节线高度 |
| `stackGap` | 1.5 | 数字与分数横线的间隔 |
| `lineWidth` | 0.6 | 分数横线宽度 |
| `leftInset` / `rightGap` | 5 / 9 | 拍号距左小节线 / 距音符区域的间隔 |
| `initialGap` | 12 | 初始调号与初始拍号间距 |

## 力度与速度

f、p、mp、mf、fp、ff、fff、sf、sfz 等使用 Bravura 的力度专用字形；节拍速度采用音乐字体的音符和附点，等号与速度数值采用西文衬线体。Rubato、Moderato、Allegro、più mosso、presto 等速度词默认粗体；其他西文表情术语默认斜体。MusicXML 指定的粗体、斜体优先保留。中文换笛等说明继续使用中文字体。不会自动纠正原谱术语的拼写。

完整配置显式使用本机 Times New Roman，字体可分别通过 `fonts.termsRegular`、`termsBold`、`termsItalic`、`termsBoldItalic` 替换。未指定时使用 PDFKit 的 Times 字体。

力度默认在所属音符下方，以实际拍位的数字中心居中；其顶部距音符下缘 `layout.terms.dynamicsGap`（默认 4 pt），下缘包括减时线和低音点。顶层 `dynamicsPlacement: "below"` 为默认值；设为 `"source"` 可按源 above/below 绘制。`directionLayout` 同时记录源位置、最终位置、音乐起点及锚点，便于核对。

`layout.terms` 可调 `dynamicsSize`（18）、`tempoSize`（10）、`expressionSize`（9）、`metronomeSize`（12）、`metronomeTextSize`（10）、`laneGap`（14）、`offsetY`（34）。音乐字体字号与实际墨迹高度不同，不能直接与普通文字字号作高度比较。18 pt Bravura 的 f 可见高度约 10.7 pt，与 14 pt 简谱数字相近。速度数字从 15 pt 缩为 10 pt，按实际墨迹下缘对齐前方节拍音符的下缘。同一拍位的速度词和节拍速度并列排放；上标贴近音符；上方术语最后排版，位于上标及其辅助升降号上方，配对速度词与节拍速度共同移动。详见[上标与连音组](ORNAMENTS_TUPLETS.md)。

字形范围依据 [SMuFL 力度](https://smufl.formats.music/latest/tables/dynamics.html)、[节拍速度](https://smufl.formats.music/latest/tables/metronome-marks.html)与[拍号](https://smufl.formats.music/latest/tables/time-signatures.html)。

## 前倚音与后倚音

MusicXML `<grace>` 始终转换为零时值事件，不推进小节游标，也不参与拍数合计。普通的小字号提示音 `<cue>` 不会因此被当成倚音。

优先根据原谱显式连线确定主音；其次参考 `steal-time-previous` / `steal-time-following` 提示和音符顺序。位于主音前的组绑定后续主音，终端倚音组绑定同小节前一个主音。缺少足够信息时不凭空编造主音，会报告待校对。MusicXML 中的借时属性是播放建议，仍保留原值，不据此修改谱面主音时值，参见 [MusicXML grace 定义](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/grace/)。

倚音和主音使用 `anchorId` 绑定；如果显式源信息把两者记在相邻小节，排谱时将倚音移入主音小节。连接绘制参照参考简谱第 1 页的倚音样式：从临近主音的倚音减时线下方，画一条向主音侧面弯曲的小钩；后倚音反向处理，长音时靠主音最后一条延时线连接。一组多个倚音共用一个小钩，不占普通乐句线、延音线的上方层次。原谱明确记录的倚音连接也按这一专用样式绘制。

前倚音预留主音左侧空间，后倚音排在主音及其延时线之后，均在小节线以内。`notation.graceScale`、`graceOffsetY`（默认改为 12 pt）、`graceOffsetXRatio` 保留可配置。完整梆笛的 `spacing.systemGap` 从 34 调为 40 pt，使抬高后的倚音及跨行乐句线避开上一行的渐强线；续页首行上移 24 pt，并调整页眉校对提示的位置。加入按拍数动态小节宽度后，当前为 6 页、30 行。

专用小钩参数位于 `layout.graces`：`underlineGap`（距倚音下缘 0.7 pt）、`anchorGap`（距主音 1.2 pt）、`anchorHeightRatio`（连接主音字形高度的 0.25 位置）、`lineWidth`（0.55 pt）、`bendInset`（弯曲内收 0.5 pt）、`minimumDrop`（最小下弯 2.8 pt）、`maximumWidthRatio`（后倚音小钩最大宽度为主字号的 0.65）。历史字段 `curves.graceHeight` 保留兼容，专用小钩不再使用普通音符弧线的拱高。

本例共 19 个倚音：11 个前倚音，8 个后倚音（第 231、233 小节各四个），形成九组与主音相连的小弧线。倚音音头来自原始矢量 PDF 的小音符文字和符干/符杠坐标；任意扫描输入仍依赖 OMR 识别质量和校对。

渲染报告的 `meterLayout`、`directionLayout`、`graceLayout` 保存位置、使用字体、主音 ID、前后关系及小节边界。`graceConnectors` 独立记录九个下方小钩，普通上方连线仍记录在 `curveSegments`；`metronome-components` 记录速度音符与数字的实际墨迹边界，便于检查大小和对齐。
