# 民乐五线谱 PDF → 简谱 PDF

面向民乐分谱的本地命令行转换工具。通过 Audiveris 识别五线谱 PDF，保留 MusicXML 中间结果，再由 Python 解析音乐语义、TypeScript 排版、PDFKit **直接生成矢量简谱 PDF**，无需 LilyPond。

目前主要支持**单乐器单声部**和**单乐器局部双声部**。输出用于校对；PDF 识别结果需要结合原谱审查，不能将生成成功等同于识谱准确。

## 功能

- 音高、调号、八度点、升降号、拍号变化及精确分数时值；保留输入符杠分组，缺失时按拍补充。
- 自适应小节宽度、拍内音符/休止分组、连续空小节合并、方框小节号、同行及跨行连线。
- 倚音、连音组、力度、速度、渐强渐弱及部分民族乐器技法；吹管跳音点按当前规则隐藏。
- 局部双声部共享时间位置，标注“乐器I / 乐器II”；单声部段落保持单行。
- **独立声部与同声部和弦分别保存**，允许两个声部各自含和弦或琶音。
- 18 类乐器能力配置，分别描述单人多音、独立声部和乐团分部；不凭乐器名称猜测原谱声部含义。
- 可调整字体、字号、点线间距、行距、连线、空小节和小节宽度；保存每次运行的中间文件与问题报告。

## 技术栈

```text
五线谱 PDF ── Audiveris 5.11.0 / OCR ──┐
                                      ↓
已校正的 MusicXML / MXL ──────────── MusicXML
                                      ↓
                       Python 3.12：精确时值、声部、音高、语义校验
                       music21：独立导入诊断
                                      ↓
                       score.json → TypeScript 排版 → PDFKit → 简谱 PDF
```

PDF 证据提取与结果检查使用 pdfplumber、pypdfium2、Pillow。Python 直接依赖在 `requirements.txt`，完整版本清单在 `requirements-lock.txt`；Node 依赖由 `package-lock.json` 锁定。

## 安装与构建

已验证环境：**Windows x64、PowerShell 7、Python 3.12.5、Node.js 24.12.0、npm 11.6.2**。PDF 识别还需 Audiveris 5.11.0 和兼容的英文 OCR 数据；直接输入 MusicXML 时可省略这两项。

详细步骤、字体配置、OCR 下载来源见 [安装指南](docs/INSTALLATION.md)。运行以下命令前需先安装运行时，并准备中文字体。默认配置使用 `C:/Windows/Fonts/NotoSerifSC-VF.ttf`；Arial 和 Times New Roman 使用 Windows 本地字体。

```powershell
# 在仓库根目录：预览安装范围，不写入文件
& .\scripts\prepare-environment.ps1

# 安装项目依赖；此处先跳过 PDF 识别引擎安装包下载
& .\scripts\prepare-environment.ps1 -Execute -SkipAudiverisDownload

# 编译 TypeScript，并执行 Node/Python 测试与环境检查
& .\scripts\build.ps1
```

Bravura 音乐字体及其 OFL 许可证随源码提供。`*.portable.json` 配置使用本地 Times New Roman 粗体绘制休止计数和小节号，不依赖从参考谱提取的 Maestro 字体。需要更改字体路径时，复制配置为 `*.local.json`，再编辑 `fonts` 字段。

## 快速尝试：无需原始乐谱的合成样例

下面的样例由代码生成，演示单行与双行切换、和弦和琶音，不代表真实 PDF 的识别效果。

```powershell
& .\.venv\Scripts\python.exe scripts\make-local-dual-example.py
& .\convert-dual.ps1 `
  -InputPath tmp\local-dual-example\local-dual.musicxml `
  -OutputPath output\demo\局部双声部_简谱.pdf `
  -Profile configs\dual-voice.portable.json `
  -InstrumentName '曲笛' -InstrumentFamily wind
```

重复转换时可添加 `-Overwrite`。如果复制并修改过字体配置，将 `-Profile` 改为相应的本地文件路径。

## 转换真实分谱

### 单乐器单声部

```powershell
& .\convert-single.ps1 `
  -InputPath 'D:\scores\梆笛.pdf' `
  -OutputPath 'D:\scores\梆笛_简谱.pdf' `
  -Profile configs\single-voice.portable.json `
  -InstrumentName '梆笛' -InstrumentFamily wind `
  -Audiveris 'C:\Program Files\Audiveris\Audiveris.exe'
```

识别后若有音乐语义错误，默认停止导出并保留问题报告。仅在需要检查带问题的初稿时使用 `-Draft`；单声部入口仍拒绝多个源声部。

### 使用已校正 MusicXML

可以直接将 `.musicxml`、`.xml`、`.mxl` 作为 `-InputPath`。也可以保留原 PDF 作为输入证据，并通过 `-MusicXml` 指定校正结果，跳过重复识别：

```powershell
& .\convert-single.ps1 `
  -InputPath 'D:\scores\梆笛.pdf' -MusicXml 'D:\scores\梆笛_校正.musicxml' `
  -OutputPath 'D:\scores\梆笛_简谱.pdf' `
  -Profile configs\single-voice.portable.json `
  -InstrumentName '梆笛' -InstrumentFamily wind
```

### 单乐器局部双声部

改用 `convert-dual.ps1` 和 `configs/dual-voice.portable.json`。`-PrimaryVoice '1:1'` 可指定源 `staff:voice` 为上声部；超过两个源流会报错。双声部的两行表示独立源声部，不表示反复。同声部和弦、琶音继续在同一声部内排版。

两种入口均支持 `-Title`、`-Composer`、`-XmlPart`、`-NodeExe`、`-PythonExe`、`-TimeoutSeconds`。源码更新后使用 `-BuildRenderer` 或重新运行构建；已存在 `dist` 时不会自动按时间戳重新编译。Python CLI 可通过 `python -m jianpu single --help` / `dual --help` 查看参数。

## 输出与排版配置

最终 PDF 写入 `-OutputPath`。同目录的 `runs/<运行标识>/` 保存识别文件、`score.json`、`report.json`、渲染报告和日志；入口解析后的配置保存在项目 `tmp/single-voice/` 或 `tmp/dual-voice/`。失败运行也会保留诊断资料。已有生成 PDF 默认拒绝覆盖，输入与参考 PDF 不允许被覆盖。

| 设置 | 位置 |
| --- | --- |
| 字体、字号、点线、间距 | `fonts`、`layout`；见[参数说明](docs/LAYOUT_PARAMETERS.md) |
| 双声部组内间距 | `layout.localVoices.rowGap` |
| 连续休止合并阈值 | `layout.rests.minimumMeasuresToCompress` |
| 每行容量与末行铺满 | `layout.maxMeasuresPerSystem`、`meterAwarePacking`、`justifyLastSystem` |
| 显式乐器能力配置 | 顶层 `instrumentProfileId`；见[乐器分类](docs/INSTRUMENT_TEXTURES.md) |

## 验证与限制

构建包含音乐语义单元测试和实际 PDF 渲染集成测试。公开环境不包含参考 Maestro 字体时，其专用字形覆盖测试会跳过；休止、连线等功能测试仍使用可用字体执行。真实 PDF 的 OMR 正确率不能由合成测试推断。

- 当前按输入记谱音转换；不猜测笛子指法、筒音或乐器移调。
- MIDI 导入、交互校谱、多乐器成熟合谱、任意多声部排版尚未完成。
- 特殊技法只有部分已映射为音乐字形或矢量符号；未知记号可能文字回退或进入报告。复杂异时值和弦等情况仍需逐谱核对。
- 既有真实曲目实验使用了针对具体输入的校正结果；这些私有乐谱和校正资料不随仓库发布。

## 源码与文档

```text
jianpu/       MusicXML 解析、语义模型、识别管线与命令行入口
renderer/     TypeScript 简谱排版及 PDFKit 渲染
configs/      单/双声部样式与乐器能力配置
scripts/      环境准备、构建、合成样例与检查工具
tests/        Python 语义测试、Node 布局及 PDF 集成测试
tools/fonts/  Bravura 与完整字体许可证
docs/         规则、参数、实现边界及历史实验记录
```

进一步阅读：[单声部方案](docs/SINGLE_VOICE.md)、[局部双声部](docs/LOCAL_DUAL_VOICE.md)、[小节排版](docs/LAYOUT_RULES.md)、[连线](docs/CURVE_LAYOUT.md)、[倚音与音乐术语](docs/METER_TERMS_GRACES.md)、[技法符号](docs/CHINESE_INSTRUMENT_TECHNIQUES.md)、[乐器织体分类](docs/INSTRUMENT_TEXTURES.md)。历史文档可能引用未发布的本地文件或参考字体；新环境复现以本 README 和安装指南为准。

## 许可与资料

项目代码尚未指定开源许可证。第三方组件按各自许可证使用，详见 [第三方说明](THIRD_PARTY_NOTICES.md)。原谱、生成结果、参考谱字体、虚拟环境、缓存和安装包均由 `.gitignore` 排除。
