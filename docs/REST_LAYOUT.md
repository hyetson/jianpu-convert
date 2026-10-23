# 空小节排版

本轮以单声部 4/4 为准，示例配置见 [configs/rest-layout.example.json](../configs/rest-layout.example.json)。

- 连续 1-3 个完整休止小节逐小节写成 `| 0 0 0 0 |`。四个 0 等距排列，整体在两侧小节线之间居中，数字中线与小节线中点对齐。
- 连续 4 小节起合并为多小节休止横线，两端加短竖线。横线水平、垂直居中，计数放在横线上方并按实际字形居中。
- 合并阈值可改；`compressRests: false` 时所有完整休止小节均逐小节显示。
- 不修改底层事件、时值或原小节号。合并 25 小节仍跨越原来的 25 个小节，后续小节号按真实位置继续。
- 缺失识别、空事件列表、拍数不足、休止重叠、弱起均不猜成整小节休止。变调、变拍、方向文字、技法、反复或终止边界会阻止跨越合并；合并段末尾的终止小节线保留。

## 拍内短休止与音符合并

短休止可与同拍普通短音符共用减时线，保留 `0` 和每个事件的实际时值。例如八分休止与八分音符共用一条线，十六分休止与八分音符混排时按每层时值连接；不跨拍、不跨缺口，整拍休止仍独立显示。含休止的拍采用这项规则；纯音符组仍优先源符杠，倚音与连音组继续单独处理。

这项规则与整小节/多小节休止压缩分别处理，完整空小节仍沿用前述居中 `0` 和计数横线。说明、样张及复现命令见[拍内排版](LAYOUT_RULES.md)。

## 参考花体数字

多小节休止的计数使用参考 PDF 内嵌的 **Maestro** 字形。原字体被拆成多个子集，三份子集联合覆盖十进制数字 0-9，渲染时逐字选择有该字形的子集。普通音符数字继续用 Arial Bold；两种字体分别配置。

来源记录和恢复方法见 [tools/fonts/reference-maestro/SOURCE.md](../tools/fonts/reference-maestro/SOURCE.md)。没有安装系统字体或新增依赖。

## 参数

| 字段 | 默认 / 示例 | 作用 |
| --- | --- | --- |
| `fonts.restCounts` | 示例配置中的三份 Maestro 子集 | 可设单个字体路径或非空路径列表，按顺序选择可用字形；省略时沿用文字字体 |
| `layout.typography.restCountSize` | 全局 11；Maestro 示例 20.5 | 休止计数字号，pt；Maestro 的字形约占半个 em，示例实际字形高度接近 14 pt 普通音符 |
| `layout.rests.minimumMeasuresToCompress` | 4 | 开始合并的连续小节数，整数且至少 2 |
| `layout.rests.widthRatio` / `minimumWidthRatio` | 6 / 5 | 合并小节的首选 / 最低宽度，相对音符字号；同时保证容纳计数字形 |
| `layout.rests.symbolInset` | 6 | 横线两端距小节线的距离，pt；由 12 减为 6，相同小节宽度下横线加长 12 pt |
| `layout.rests.lineWidth` | 2.2 | 休止横线粗细，pt |
| `layout.rests.capHeight` / `capWidth` | 10 / 1.3 | 两端短竖线的高度 / 粗细，pt |
| `layout.rests.countGap` | 4 | 计数字形下缘到横线中心的距离，pt |
| `layout.rests.countDigitGap` | 1.3 | 计数相邻数字在字体原生字距之外的额外间隔，pt |
| `layout.rests.zeroInset` | 8 | 四个 0 等分排列区域的左右内缩，pt |

## 复现样张

```powershell
& .\scripts\build.ps1
& .\.venv\Scripts\python.exe scripts\make-rest-layout-fixture.py
& .\.venv\Scripts\python.exe -m jianpu from-musicxml --config configs\rest-layout.example.json --overwrite tmp\rest-layout\rests.musicxml
& .\.venv\Scripts\python.exe scripts\verify-pdf.py 'output\jianpu\空小节_排版样张.pdf' --preview-dir tmp\rest-layout\pages
```

样张是 62 小节的合成谱，包含连续 1、2、3、4、8、11、25 个休止小节，间隔插入短旋律。最终 1 页、5 行、18 个可见小节单元，按 4、4、4、4、2 个单元断行；合并休止段算一个可见单元，保留原始计数；前 6 个短休止小节显示 24 个 0，长段计数为 4、8、11、25。源数据仍有 62 小节、32 个旋律音符事件。

方框小节号也已采用 Maestro 粗体花体，使用独立的 `fonts.measureNumbers` 与 `layout.measureNumbers` 参数。增大字体时方框按实际字形扩展。

检查：当前构建 63 项测试通过；样张语义检查 0 错误、0 警告，字体嵌入且无谱面位图。四条休止横线仍处于两侧小节线的水平、垂直中点，两端内缩各为 6 pt。24 个普通 0 与 4/8/11/25 的 Maestro 字符保持不变。
