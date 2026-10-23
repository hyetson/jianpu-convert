# 单乐器局部双声部

2026-10-22，第二阶段的首版实现。入口为根目录 `convert-dual.ps1` 或 `python -m jianpu dual`，默认配置为 `configs/dual-voice.json`。沿用 PDF → Audiveris → MusicXML → Python 语义检查 → TypeScript/PDFKit 的流程，不增加依赖。

## 双声部与和弦的区别

| 输入含义 | 数据表示 | 简谱布局 |
| --- | --- | --- |
| 一个声部内同时出现多个音，如笙的和声、弹拨和弦 | 一个 `staff:voice` 事件，包含多个 pitches；MusicXML 通常使用 `<chord/>` | 同一节奏事件内竖排音高，保留原和弦/琶音标记 |
| 同一乐器的两个独立旋律或节奏 | 两个 `staff:voice` 事件流，各自保留起点、时值、休止、连线和减时线 | 局部展开两行，共用小节线的水平位置和拍位坐标 |

判定依据是原始事件归属，不按“同一时刻有几个音”拆声部。两个独立声部即使同音、同节奏，也保留各自声部身份；每个声部内部仍可包含和弦和琶音。OMR 错把独立声部识别成和弦时，需要在 MusicXML 中校正；本版不会根据排版猜测重写音乐。

## 局部展开规则

- 以完整小节为最小展开触发单位；包含双声部的谱行形成一个上下对齐的双行谱组，完全单声部的谱行保持原版式。
- 每个双行谱组的行头分别写“乐器名I”“乐器名II”，例如“曲笛I”“曲笛II”。名称来自 `-InstrumentName`，在换行/换页后的双行谱组重复标注。
- 同一个双行谱组内，I 固定上行、II 固定下行。即使 II 单独演奏也留在下行，I 已编码的休止符显示在上行；不会把 II 移到标为 I 的位置。
- 组内保留两条源事件流及各自已编码的休止；没有编码该声部的小节不凭空补事件。整行没有双声部需求时，整小节休止的第二声部仍可收起；只有一个声部演奏时使用单行。
- 同一时点按数字的可见中心对齐；两行共用水平时间网格，减时线仍按各自声部独立分组。
- 行头标签位于第一条小节线左侧，预留专用空间；用组首竖线连接上下两行，表明两行同时演奏。同一时点的不同声部不作为反复、复奏段或和弦合并。
- 含双声部的谱行需预留两行高度；完全单声部的谱行保持原有高度。不是整份谱面固定双行，也不在同一小节中途切换行数。
- 调号、拍号及没有指定声部的力度/速度术语只在上方显示一次。MusicXML 显式指定 `<voice>` 的方向标记归属对应声部。
- 两个声部的连线分别处理，保留原端点及跨行接续；渐强/渐弱保留源拍位。共享渐强线跟随上方行，指定声部的渐强线跟随其所属行。

## 使用

新 PDF：

```powershell
& .\convert-dual.ps1 -InputPath 'D:\scores\二胡.pdf' -OutputPath 'D:\scores\二胡_简谱.pdf' -InstrumentName '二胡' -InstrumentFamily bowed
```

已经校正的 MusicXML：

```powershell
& .\convert-dual.ps1 -InputPath 'D:\scores\二胡.musicxml' -OutputPath 'D:\scores\二胡_简谱.pdf' -InstrumentName '二胡' -InstrumentFamily bowed -PrimaryVoice '1:1'
```

`-PrimaryVoice` 指定双声部时置于上方的源 `staff:voice`，缺省使用排序后的第一个 ID；只影响显示顺序，不移动或改写源事件。`-XmlPart` 显式选择多 part 文件中的一个乐器。`-MusicXml` 可为 PDF 提供对应的校正文件，从而跳过重新识别。其他参数与[单声部入口](SINGLE_VOICE.md)相同。

该入口只接受一个 part、全曲最多两个 `staff:voice` 事件流。多于两个、指定主声部不存在等情况，即使 `-Draft` 也会停止。每个实际编码的声部仍需满足原有精确时值和缺口检查；不自动填音或缩放时值。原 `convert-single.ps1` 默认仍是严格单声部模式。

配置中的字体相对路径以配置目录为基准；排版参数继续沿用单声部配置，新增：

```json
{
  "workflow": "local-dual-voice",
  "localVoices": {"primaryVoice":"1:1"},
  "layout": {"localVoices":{"rowGap":72,"labelSize":10,"labelGap":10}}
}
```

`rowGap` 是双声部时上方行的最小基线间距，单位 pt；实际布局还会给该行的和弦增加高度。`labelSize` 控制完整行头名称的字号；`labelGap` 控制名称右侧到第一条小节线的间隔。断行计算包含标签宽度，完全单声部行不预留这段空白。改后用配置传参即可，不需要改渲染源码。

当前组内声部基线距离由 96 pt 缩至 72 pt；默认配置无和弦时，相邻谱组之间的基线距离为 112 pt（`spacing.rowHeight` 72 + `systemGap` 40）。组内间隔明显较小，和弦仍按所需高度额外留白。

## 样例与验证

```powershell
& .\scripts\build.ps1
& .\.venv\Scripts\python.exe scripts\make-local-dual-example.py
& .\convert-dual.ps1 -InputPath tmp\local-dual-example\local-dual.musicxml -OutputPath 'output\jianpu\单乐器_局部双声部_排版示例.pdf' -Title '单乐器 · 局部双声部示例' -InstrumentName '演示乐器' -PartId local-dual -Overwrite
& .\.venv\Scripts\python.exe scripts\verify-local-dual-example.py
& .\.venv\Scripts\python.exe scripts\verify-pdf.py 'output\jianpu\单乐器_局部双声部_排版示例.pdf' --preview-dir tmp\local-dual-example\pages
```

样张为人工构造的 16 小节：第 5、6、8、9 小节有双声部需求，所在第 2、3 组谱行显示双行及完整行头名称，其余谱行维持单行；第 3、14 小节展示同声部和弦/琶音。第 12 小节 II 单独演奏时仍在下行，I 在上行显示休止。第 8–9 小节展示跨行连线及渐强。

运行报告增加 `localDualVoice`、`voiceLayout`、`voiceLabelLayout`、`eventLayout` 和每行的 `visibleLanes`，可核对源声部身份、完整行头名称、显示行、音符中心和实际显示范围。专项检查验证所有发声音符都保留、同拍对齐、方向标记不重复、组内声部位置固定，以及跨行端点与渐强接续。

本轮通过 78 项 Node、42 项 Python 测试。完整梆笛通过原单声部入口重新渲染为 6 页、254 小节；其小节几何、上下文、连线、力度、拍号、倚音、休止、减时线、渐强、连音数、技法和八度点，与上一版逐项一致。记录在 `tmp/local-dual-example/single-regression-verification.json`。

此双声部样张验证的是 MusicXML 解析和排版，没有验证任意真实 PDF 的双声部识别准确率；真实输入仍需对照源谱校对。此前交付的单声部 0.1.0 ZIP 保持原样，新功能位于当前工作区源码。
