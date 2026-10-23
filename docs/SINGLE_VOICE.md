# 单声部五线谱 → 单声部简谱方案

版本 0.1.0，2026-10-20。当前交付为 Windows 本地命令行方案，沿用已核对的梆笛排版。统一入口为项目根目录的 `convert-single.ps1`，Python 入口为 `python -m jianpu single`，默认排版配置为 `configs/single-voice.json`。

## 转换流程与边界

```text
五线谱 PDF ── Audiveris ── MusicXML ── 精确时值与单声部检查 ── TypeScript/PDFKit ── 简谱 PDF
                              ↑
                    可以直接提供校正后的 XML/MXL
```

单声部指一个乐器 part 内只有一个 `staff:voice` 事件流。一个时刻的和弦/双音仍可保留为这个声部的同一事件；不会因此拆成多个声部。多个 part 必须显式选一个 MusicXML part；选定 part 内若仍有多个 `staff:voice`，则停止并报告。`-Draft` 也不会把多声部自动混成单声部。

当前保留：调号、拍号、精确时值与升降号、八度点、源符杠、拍内休止混排、多小节休止、连线、连音数字、前后倚音、渐强渐弱、力度/速度、常用技法。吹管跳音点默认隐藏，八度点与附点保留；未知乐器类别不隐藏跳音点。MIDI 尚未接入。

通用 PDF 路径包含真实 OMR，识别结果仍需校对。任意新 PDF 不会自动获得梆笛个案的专项修正；梆笛已有的音高、连组、倚音与小节号校正保存在原项目的 `output/jianpu/bangdi-full-source/`，不作为通用算法精度保证。

## 运行已有环境

在项目目录运行。入口不安装依赖、不启动系统安装器、不修改全局 PATH；缺少环境时明确报错。默认使用包内已编译渲染器；修改 TypeScript 源码后用 `-BuildRenderer` 或 `scripts/build.ps1` 显式编译。仅在编译产物缺失时尝试使用现有编译依赖，不根据解压后的文件时间戳判断。

### 新的单声部 PDF

```powershell
& .\convert-single.ps1 -InputPath 'D:\scores\笛子.pdf' -OutputPath 'D:\scores\笛子_简谱.pdf' -InstrumentName '梆笛' -InstrumentFamily wind
```

默认遇到拍数、缺失小节等语义错误不导出。只有需要查看校对初稿时加 `-Draft`。生成文件已经存在时，加 `-Overwrite` 才覆盖；不能覆盖输入或项目 `example` 中的原谱/参考 PDF。

### 已校正的 MusicXML/MXL

```powershell
& .\convert-single.ps1 -InputPath 'D:\scores\笛子.musicxml' -OutputPath 'D:\scores\笛子_简谱.pdf' -InstrumentName '梆笛' -InstrumentFamily wind
```

若输入 MusicXML 含多个 part，用 `-XmlPart P1` 明确选择 part；这不自动选择 part 内的某个 voice。

### 原项目完整梆笛复现

```powershell
& .\convert-single.ps1 -InputPath '.\example\Silk Road 2012 - 梆笛.pdf' -MusicXml '.\output\jianpu\bangdi-full-source\bangdi-reviewed.musicxml' -OutputPath '.\output\jianpu\丝绸之路_梆笛_完整简谱_校对稿.pdf' -PartId bangdi -InstrumentName '梆笛' -InstrumentFamily wind -Title '丝绸之路' -Composer '姜莹' -Draft -Overwrite
```

`-MusicXml` 表示显式复用属于此 PDF 的校正结果，跳过重新识别。调用方需确认两者对应；运行报告同时保留 PDF 和 MusicXML 的 SHA256。此复现使用原项目已有校对文件，源码压缩包不含原谱及识别缓存。

## 参数

| PowerShell 参数 | 用途 |
| --- | --- |
| `-InputPath` / `-OutputPath` | 必填；PDF/XML/MXL 输入与 PDF 输出 |
| `-MusicXml` | PDF 对应的校正 MusicXML，显式跳过 OMR |
| `-Profile` | 自定义配置；缺省 `configs/single-voice.json` |
| `-InstrumentName` / `-InstrumentFamily` | 乐器名称及 wind/bowed/plucked/struck-string/unknown；类别只决定显示策略，不猜移调 |
| `-PartId` / `-XmlPart` | 输出标识 / 输入 MusicXML part ID |
| `-Title` / `-Composer` | 标题与作曲者；默认标题为输入文件名 |
| `-NodeExe` / `-PythonExe` / `-Audiveris` | 已安装运行时的明确路径 |
| `-TimeoutSeconds` | OMR 超时，默认 1200 秒 |
| `-BuildRenderer` | 用现有依赖重新编译渲染器，不安装依赖 |
| `-Draft` / `-Overwrite` | 允许带语义错误的标记初稿 / 覆盖生成文件 |

Python 等价入口：

```powershell
& .\.venv\Scripts\python.exe -m jianpu single 'D:\scores\笛子.pdf' --output 'D:\scores\笛子_简谱.pdf' --instrument-name '梆笛' --instrument-family wind
```

配置文件内的字体相对路径，以配置文件所在目录为基准；输入、输出等命令行路径以调用时的目录为基准。`single` 会保存解析后的绝对路径配置，之后切换工作目录也不会改变该次运行的路径含义。

## 力度下标与可调排版

力度字形的可见中心对齐其实际拍位，顶部默认距对应音符下缘 4 pt；下缘计算包含减时线和低音点。默认所有力度放在谱下，消除因源 OMR 的 above 位置造成的悬空；原始 placement 继续保留。

梆笛原数据的 `sf` 实际绑定第 68 小节 7/2 拍，被 OMR 标成 above，所以旧输出看起来悬在第 47 小节下方。本轮修正其显示位置，保留原音乐拍位；不凭排版外观将它改绑到第 47 小节。

```json
{
  "dynamicsPlacement": "below",
  "layout": {"terms": {"dynamicsGap":4, "dynamicsSize":18}},
  "techniques": {"windStaccato":"hide"}
}
```

需要保留源 above/below 时，将 `dynamicsPlacement` 设为 `source`。字号、间隔、字体、小节宽度等继续可配，见[排版参数](LAYOUT_PARAMETERS.md)、[上标与连音组](ORNAMENTS_TUPLETS.md)、[休止混排](LAYOUT_RULES.md)和[特殊技法](CHINESE_INSTRUMENT_TECHNIQUES.md)。

## 输出与审计

单声部 0.1.0 交付时通过 112 项测试（72 项 Node、40 项 Python）。通过新入口复现完整梆笛为 6 页、254 小节、30 行，语义校验 0 错误、0 警告；16 处力度下标均核对中心及下缘间隔，六页已渲染检查。此复现显式使用已有校正 MusicXML，没有重跑 OMR。后续[局部双声部阶段](LOCAL_DUAL_VOICE.md)的当前构建为 128 项测试通过，原单声部入口继续保留。

- 最终 PDF 位于指定输出路径。
- `输出目录/runs/运行编号/` 保留 `score.json`、`report.json`、`render.log`、渲染 PDF 与几何报告；出错时保留 `failure.json`。
- 新入口解析后的配置位于 `tmp/single-voice/运行编号/config.json`，终端摘要打印该路径。
- `directionLayout` 记录力度的原始/实际 placement、起始拍位、锚定事件、锚点下缘和最终字形边界。

验证：

```powershell
& .\scripts\build.ps1
& .\.venv\Scripts\python.exe scripts\verify-bangdi-full.py
& .\.venv\Scripts\python.exe scripts\verify-pdf.py '.\output\jianpu\丝绸之路_梆笛_完整简谱_校对稿.pdf' --preview-dir '.\tmp\single-voice-release\pages'
```

## 源码包

```powershell
& .\.venv\Scripts\python.exe scripts\package-single-voice.py
# 已存在同名生成包时，可加 --overwrite
```

生成 `output/releases/jianpu-single-voice-0.1.0.zip` 和 `.zip.sha256`。包含 Python 源码、TypeScript 源码与编译产物、配置、测试、说明和现有音乐字体/来源记录；`MANIFEST.json` 列出每个文件的 SHA256。不含 `.venv`、`node_modules`、安装包、OCR 数据、原谱 PDF 或识谱缓存。

历史样张配置及生成/验证脚本随源码保留，供开发回归；默认转换仍仅通过 `convert-single.ps1` 和 `configs/single-voice.json`。梆笛个案脚本需要原项目的原谱与识别记录，解压包本身不带这些输入。

这是可复现的源码/渲染器包，不是独立 exe。解压到新电脑后仍需配置 Python 3.12、Node 24、锁定依赖、Audiveris 5.11（仅 PDF OMR 需要）、英文 OCR 数据及配置中指定的 Windows 字体。安装或下载缺失项应先由用户批准；入口本身不会自动补环境。当前配置的中文字体为 NotoSerifSC，需按实际安装位置调整；字体来源与许可记录随文件保留。
