# 第三方组件与本地资料

## 项目代码

目前尚未指定项目代码的开源许可证。上传到 GitHub 不等同于授予开源许可；第三方组件继续遵守各自许可证。本文件不是对项目代码的重新授权。

## 随仓库提供的字体

- **Bravura**：Steinberg Media Technologies GmbH，SIL Open Font License 1.1；字体文件未修改。完整版权及许可证见 [Bravura-LICENSE.txt](tools/fonts/Bravura-LICENSE.txt)。来源为 [Bravura 官方仓库固定提交](https://github.com/steinbergmedia/bravura/tree/37b194378b710cc40e406ab6c4b07608bb9548ae)。

## 单独安装的组件

Python 与 npm 依赖分别记录在 `requirements-lock.txt`、`package-lock.json`；软件包中的许可证仍然适用。Audiveris、Tesseract 语言数据不随本仓库分发，应从各自官方项目取得并遵守许可。

- [Audiveris](https://github.com/Audiveris/audiveris)
- [music21](https://github.com/cuthbertLab/music21)
- [PDFKit](https://github.com/foliojs/pdfkit)
- [Tesseract tessdata](https://github.com/tesseract-ocr/tessdata)
- [Noto CJK](https://github.com/notofonts/noto-cjk)：可用于中文文字；安装后在配置中填写实际字体路径。

Windows 的 Arial、Times New Roman 等字体只通过本地文件路径引用，不随仓库分发。

## 不上传的本地资料

`example/` 中的原始乐谱、`output/` 中的转谱结果与校正 MusicXML、`tmp/` 中的识别资料，以及 `tools/fonts/reference-maestro/` 中从参考 PDF 提取的 Maestro 字体子集，均属于本地开发资料。提取或读取字体不产生再分发授权。仓库忽略这些资料，源码打包脚本也不包含这些字体。

`configs/single-voice.json`、`configs/dual-voice.json` 保留本地参考样式，使用上述未分发字体。新环境请使用 `*.portable.json`，其计数和小节号改用本地 Times New Roman 粗体，排版效果与参考字体有所不同。

历史开发文档中的真实乐曲、截图路径和测试结果是本地实验记录；相关原谱及校正数据未随仓库提供。仓库中的合成样例生成器不依赖这些原谱。
