# 环境安装与复现

本文是新环境安装指南；`ENVIRONMENT.md` 为开发机历史审计记录。

## 支持环境

当前已验证 Windows x64、PowerShell 7、Python 3.12.5、Node.js 24.12.0、npm 11.6.2。`.python-version` 与 `.node-version` 记录验证版本，不会自动安装运行时。Linux/macOS 的 Audiveris 启动与字体配置尚未验证。

| 组件 | 必要性 | 配置文件或位置 |
| --- | --- | --- |
| Python 3.12 | 必需 | `requirements.txt` 直接依赖；`requirements-lock.txt` 完整版本快照 |
| Node.js 24 | 必需 | `package.json` 与 `package-lock.json` |
| Bravura | 必需，已随源码提供 | `tools/fonts/Bravura.otf`，OFL 1.1 |
| Noto Serif SC | 中文标题/乐器名 | `fonts.text`，默认 `C:/Windows/Fonts/NotoSerifSC-VF.ttf` |
| Arial Bold、Times New Roman | Windows 便携配置使用 | `fonts.numbers`、`fonts.terms*`、计数字体 |
| Audiveris 5.11.0 Windows Console x64 | 仅 PDF 识别需要 | `-Audiveris` 或进程变量 `AUDIVERIS_EXE` |
| Tesseract 英文数据 | PDF 中英文文字 OCR | `tools/tessdata/eng.traineddata` |

`requirements-lock.txt` 是已验证 Windows/Python 3.12 环境的固定版本清单，不是含哈希的跨平台解析锁。使用其他平台或升级依赖后需要重新验证。无需安装 LilyPond、数据库或 Web 服务。

## 项目依赖

在仓库根目录运行，先检查计划，再按需要执行安装。执行安装命令会联网下载依赖；不会自动运行系统安装器或修改全局 PATH。

```powershell
# 只预览
& .\scripts\prepare-environment.ps1

# 安装锁定的 Python/npm 依赖；仅从 MusicXML 转换时可跳过 OMR 安装包下载
& .\scripts\prepare-environment.ps1 -Execute -SkipAudiverisDownload

# Python/npm 不在 PATH 时显式传路径
& .\scripts\prepare-environment.ps1 -Execute -SkipAudiverisDownload `
  -PythonExe 'D:\Python312\python.exe' -NpmCmd 'D:\nodejs\npm.cmd'
```

等价的手动安装步骤：

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm.cmd ci --ignore-scripts --no-audit --no-fund
```

安装脚本默认使用 PATH 上的 `python` 与 `npm.cmd`，检查 Python 主次版本为 3.12。Bravura 文件若缺失，会从脚本中固定的官方提交下载并保留许可证。

## 字体配置

在 [Noto CJK 官方项目](https://github.com/notofonts/noto-cjk) 取得并安装 Noto Serif SC，或指定已合法取得、包含所需中文字形且可被 PDFKit 嵌入的字体。字体文件名随安装方式而变化，配置必须填写真实路径。

先复制公开配置，避免覆盖本地参考样式：

```powershell
Copy-Item configs\single-voice.portable.json configs\single-voice.local.json
Copy-Item configs\dual-voice.portable.json configs\dual-voice.local.json
```

编辑复制后的 `fonts.text` 及其他 `fonts` 路径；相对路径以配置文件所在目录为基准。`*.local.json` 不会被 Git 上传。`fonts.music` 保持 `../tools/fonts/Bravura.otf`。便携配置不依赖 Maestro 字体，计数使用 Times New Roman 粗体。

渲染测试默认使用 `C:/Windows/Fonts/NotoSerifSC-VF.ttf`；安装在其他位置时，设置当前 PowerShell 进程变量：

```powershell
$env:JIANPU_TEST_TEXT_FONT = 'D:\fonts\NotoSerifSC-VF.ttf'
```

此变量只供测试使用；转换使用所选 JSON 配置中的 `fonts.text`。

## PDF 识别环境

1. 从 [Audiveris 5.11.0 官方发布页](https://github.com/Audiveris/audiveris/releases/tag/5.11.0) 获取 Windows Console x64 MSI；安装位置可自行选择。项目脚本省略 `-SkipAudiverisDownload` 时也可仅下载该包并校验，不会执行安装器。
2. 官方 MSI 下载校验值：`5f1b4e96a12c53c7da426814b76e599363c4181e291855996e0a6878dda95f71`。Windows 安装包自带 JRE，无需为本流程额外更改 JAVA_HOME。
3. 从 [tessdata 4.0.0 的 eng.traineddata](https://github.com/tesseract-ocr/tessdata/blob/4.0.0/eng.traineddata) 取得兼容 legacy 的英文数据，保存为 `tools/tessdata/eng.traineddata`。不要替换成仅支持 LSTM 的 `tessdata_fast` 数据。本地验证文件 SHA256：`daa0c97d651c19fba3b25e81317cd697e9908c8208090c94c3905381c23fc047`。
4. 转换时传 `-Audiveris 'C:\Program Files\Audiveris\Audiveris.exe'`，或设置 `$env:AUDIVERIS_EXE`。管线仅对子进程设置 OCR 路径与项目内缓存。

需要系统管理员权限的安装由使用者批准并执行。MusicXML/MXL 直接转换不调用 Audiveris，也不需要 OCR 数据。

## 构建与检查

```powershell
& .\scripts\build.ps1
# 也可以分开执行
npm.cmd run build
npm.cmd run test:layout
New-Item -ItemType Directory -Path tmp -Force | Out-Null
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m jianpu doctor
```

`build.ps1` 支持 `-NodeExe`、`-PythonExe`。`JIANPU_NODE` 可供 PowerShell 转换/构建入口选择 Node。`doctor` 输出组件状态，缺失的可选 OMR 环境会显示 `null`，不代表识别或全部字体已经验证。

Node 渲染集成测试会启动编译后的渲染器生成 PDF，并检查布局报告；Python 测试使用项目依赖。仅测试本地参考 Maestro 字体覆盖率的用例在这些字体缺失时明确跳过，其余布局测试仍须通过。
