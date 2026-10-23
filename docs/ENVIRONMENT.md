# 本地环境检查与待批准操作

初查日期：2026-10-14。以下“已有环境/待批准补全”为初查时记录；经用户批准后的实际安装与验证状态见文末。

## 技术栈与范围

三份笛子五线谱 PDF → Audiveris → MusicXML → music21/原始 XML → 三声部数据模型 → TypeScript 专用排版 → PDFKit 直接生成简谱 PDF。首轮忽略其他乐器的提示谱。

先做本地命令行流程。Vite/编辑器、FastAPI、数据库、任务队列、MIDI 导入、LilyPond、Docker 均不属于本轮环境补全。

## 已有环境

| 项目 | 实测结果 |
| --- | --- |
| 本地 Python | `E:\Re Software\Python312\python.exe`，3.12.5 x64 |
| pip | 24.2，可运行 |
| Node | `E:\ProSoftware\Node\node.exe`，24.12.0 |
| npm | `E:\ProSoftware\Node\npm.cmd`，11.6.2 |
| Java 21 | `E:\Re Software\Java21\bin\java.exe`，21.0.7，可运行；未在 PATH 中发现 java |
| 其他 Java | Java 11.0.12、17.0.8，可运行 |
| 中文字体 | Windows Fonts 下发现 NotoSansSC-VF.ttf、NotoSerifSC-VF.ttf、simsun.ttc、msyh.ttc；嵌入兼容性待验证 |
| Audiveris | PATH、常见软件目录和已查询的卸载登记中未发现；不等于全盘搜索结论 |
| 项目代码 | 原目录无 Python/Node 依赖清单和转换实现；本轮新建待审核清单 |

Codex 自带 Python 3.12.14 已有 pdfplumber 0.11.9、pypdfium2 5.14.0、Pillow 12.3.0 等，但没有 music21。它可以用于只读检查；正式项目使用独立 .venv，不向 Codex 运行环境安装软件。

## 待批准补全

1. 使用本地 Python 创建项目 `.venv`，安装 requirements.txt 中的 music21 10.5.0、pdfplumber 0.11.10、pypdfium2 5.14.0、Pillow 12.3.0 及其传递依赖。顶层版本已根据 PyPI 元数据核对 Python 要求；实际解析与导入测试尚未执行。
2. 使用已有 npm 安装 package.json：PDFKit 0.20.2、TypeScript 7.0.2、@types/pdfkit 0.17.6、@types/node 24.19.2 及传递依赖；生成 node_modules 和 package-lock.json。禁用依赖生命周期脚本，不进行全局安装。
3. 从官方 GitHub 下载 Audiveris 5.11.0 Windows Console x64 MSI 到 `tools/downloads/`。精确大小 85,062,430 字节。SHA256：`5f1b4e96a12c53c7da426814b76e599363c4181e291855996e0a6878dda95f71`。仅下载并校验，不运行安装器。
4. 从 Bravura 官方仓库的固定提交 `37b194378b710cc40e406ab6c4b07608bb9548ae` 下载 Bravura.otf（889,228 字节）和许可证到 `tools/fonts/`。不注册系统字体。

Python 包落在项目 .venv，pip 缓存设为项目 tmp/pip-cache；npm 缓存设为项目 tmp/npm-cache。不会修改 PATH、JAVA_HOME 或升级现有 Python/Node/Java。现有 example 文件和 output 中的其他 PDF 不修改。

Audiveris 官方安装器附带 JRE，因此无需另外安装 Java。官方说明 OCR 语言数据不随安装器提供；首轮拟使用英文文字识别，中文标题/乐器名可由输入配置提供。OCR 语言数据的具体路径和下载会在 Audiveris 安装阶段单独审阅，不隐含在当前下载批准范围内。

## 可审阅脚本

`scripts/prepare-environment.ps1` 默认只输出计划。只有显式传入 `-Execute` 才创建环境、安装依赖和下载资产。脚本不会运行 MSI 安装器。

```powershell
# 只预览，不安装，不下载
& .\scripts\prepare-environment.ps1

# 仅在用户批准上述 1–4 项后执行
& .\scripts\prepare-environment.ps1 -Execute
```

依赖与下载完成后，验证 pip check、库导入、TypeScript 编译器、PDFKit 中文/音乐字体嵌入；随后另行确认 Audiveris 安装位置与安装批准，再运行输入首页 OMR。

## 官方来源

- Audiveris 发布：https://github.com/Audiveris/audiveris/releases/tag/5.11.0
- Audiveris 安装：https://audiveris.github.io/audiveris/_pages/tutorials/install/binaries/
- music21：https://pypi.org/project/music21/10.5.0/
- PDFKit：https://pdfkit.org/docs/getting_started.html
- Bravura：https://github.com/steinbergmedia/bravura/tree/37b194378b710cc40e406ab6c4b07608bb9548ae

## 经批准后的实际状态

用户分别批准了项目依赖安装/字体与安装包下载，以及 Audiveris 系统安装/英文 OCR 数据下载。

- 项目 .venv 和 node_modules 已安装；pip check 通过，顶层及传递依赖见 requirements-lock.txt 和 package-lock.json。
- Audiveris 5.11.0 已安装于 C:\Program Files\Audiveris。首次静默安装因 Windows 1925 权限错误失败；用户 Windows 管理员授权后的重试返回 0。
- Bravura.otf 已下载，许可证保留于 tools/fonts/Bravura-LICENSE.txt。
- tools/tessdata/eng.traineddata 为 Tesseract tessdata 4.0.0 legacy 兼容数据，大小 23,466,654 字节；SHA256 为 daa0c97d651c19fba3b25e81317cd697e9908c8208090c94c3905381c23fc047。
- Audiveris 子进程的配置、JavaCPP/PDFBox 缓存和临时目录定位到项目 tmp。没有修改系统 PATH 或 JAVA_HOME。
- TypeScript 构建及 16 项单元测试通过；三份真实 PDF 已识别并导出带错误标记的简谱初稿，详见 BUILD_REPORT.md。
- 沙箱中 Java ZIP 文件系统的写权限判断导致 .omr 保存失败；本轮已获批流程在沙箱外执行后成功。普通本地终端可运行转换，不涉及新软件安装。
