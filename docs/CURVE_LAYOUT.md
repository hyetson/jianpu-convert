# 单声部连线排版

直接由 PDFKit 绘制三次贝塞尔矢量曲线，不经过 LilyPond。与已有音符、休止排版共用布局参数和分页。

## 保留的语义

- MusicXML `slur` 表示圆滑/乐句线；`tied` 表示延音线，保留两者区别。
- 按声部、连线编号配对，延音线还按记谱音高拼写配对，避免把不同音高接成延音线。只提供发声语义 `tie` 的文件也可回退处理。
- 保留上下方位置（`placement`，或 `orientation=under`）、实/虚/点线和隐藏属性。原始 `bezier-*`、`default-*`、`relative-*` 属性保存为 `sourceGeometry`，供回查输入。五线谱与简谱字形和行宽不同，输出端不照搬五线谱坐标。
- 同行时连接起止数字的横向中心；两端分别相对各自音符的外轮廓保留相同垂直间距；高音点计入上缘，无上点时以数字上缘为准；两端连成的基线可倾斜，弧线相对基线的两侧拱高保持均衡；上下方连线避开相应数字、八度点和减时线。嵌套长乐句线放在短延音线外层。
- tr、波音、延长号等贴近音符，普通经过弧线不再将其推向高处；仅连线首尾可略微上移并允许适当重合。文字排在上标及其辅助升降号上方。连音组数字位于专用组线中央，采用音乐字体。参数及说明见[上标与连音组](ORNAMENTS_TUPLETS.md)。完整梆笛配置的普通连线基础端点间隔仍为 2.5 pt。
- 跨行时，在行尾和下行行首分别绘制接续弧段；每个弧段相对自身端点基线保持均衡；整条连线统一额外避让间距，跨行、跨页的实际起止端仍与各自音符保持相同间距；跨多行及跨页同样按事件边界拆段。每段保留同一组起止事件 ID。
- 圆滑线的 `continue` 保留整条乐句；延音线的 `continue` 按前后音拆成两条相接的延音线。
- 缺少起点/终点会记录警告并省略不完整连线，不把它任意延长到曲末。不会凭音高或相邻位置猜测 OMR 遗漏的连线。

## 本次与原谱核对

输入 `example/Silk Road 2012 - 梆笛.pdf` 第 1 页，第 44-48 小节，人工录入音符及片段内完整连线：

| 类型 | 起点 | 终点 | 简谱核对 |
| --- | --- | --- | --- |
| 圆滑线 | 44 小节 B4，第 2 个音 | 47 小节 D5，第 1 个音 | 7 → 上点 2，同行 |
| 延音线 | 46 小节 D5（全音符） | 47 小节 D5（八分） | 上点 2 → 上点 2，同行，处于乐句线内层 |
| 圆滑线 | 47 小节 B4，第 2 个音 | 48 小节 D5，第 1 个音 | 7 → 上点 2，跨行 |

47 小节第 1 个 D5 同时是前一条乐句线与延音线的终点。44 小节第一个 C5 另有来自截取范围外的连线；样张只包含起止均在片段内的三条完整连线，未伪造这条外来连线的起点。

样张采用 4 小节/行的上限，得到 44-47、48 两行，曲线随新的断行重新拆段；这与原五线谱断行不同，但连接的音符保持一致。输出 `output/jianpu/梆笛_44-48小节_连线核对.pdf` 是人工录入的局部排版验证，不代表整曲自动 OMR 已校验通过。

另有 `output/jianpu/连线_排版样张.pdf`，为 12 小节模拟样例，包含同行、跨行、下方低音点避让和虚线。`output/jianpu/空小节_排版样张.pdf` 展示加长休止横线和花体方框小节号。

## 复现

```powershell
& .\scripts\build.ps1
& .\.venv\Scripts\python.exe scripts\make-curve-layout-fixture.py
& .\.venv\Scripts\python.exe -m jianpu from-musicxml --config tmp\curve-layout\source-excerpt.json --overwrite tmp\curve-layout\source-excerpt.musicxml
& .\.venv\Scripts\python.exe -m jianpu from-musicxml --config tmp\curve-layout\synthetic.json --overwrite tmp\curve-layout\synthetic.musicxml
& .\.venv\Scripts\python.exe scripts\verify-pdf.py 'output\jianpu\梆笛_44-48小节_连线核对.pdf' --preview-dir tmp\curve-layout\source-pages
& .\.venv\Scripts\python.exe scripts\verify-pdf.py 'output\jianpu\连线_排版样张.pdf' --preview-dir tmp\curve-layout\synthetic-pages
& .\.venv\Scripts\python.exe scripts\verify-curve-layout.py
```

本次构建 38 项 Node 测试、25 项 Python 测试通过，覆盖同音延音配对、和弦成员识别、上下位置/虚线/隐藏属性、嵌套、缺失端点、跨行多段以及跨页。两份连线样张共 11 段曲线均检查端点等距及相对基线的拱高均衡；避让时统一整条连线的额外间距。模拟样张包含无上点到有上点、以及有上点到无上点的连接。样张逐页渲染检查，并检查无谱面位图、字体已嵌入。

`rendered.render.json` 与运行报告中包含 `curveSegments`，记录每段的起止事件 ID、行、页、控制点坐标、接续方向、两端参考边界 `startBound` / `endBound` 与实际端点间隔 `endpointGap`。参数见 [LAYOUT_PARAMETERS.md](LAYOUT_PARAMETERS.md)。复杂装饰、文字方向与极密集谱面仍需按原谱校对，并可调整行距与曲线参数。
