# 民族乐器五线谱 → 简谱：特殊技法符号对应参考

版本：0.1；资料核查日期：2026-10-20。本文是项目的转换与排版参考，不是统一的民乐记谱国家标准，也不表示下列技法已经全部实现。

范围：吹管乐、拉弦乐、弹拨乐的常见记号。以单乐器分谱为起点，兼顾笙、弹拨乐和弦及将来的分声部。转换链路继续采用 PDF → Audiveris/MusicXML → 语义数据 → PDFKit 矢量 PDF。

乐器的多音能力、单人复调和乐团分部现已另列[乐器织体分类与证据](INSTRUMENT_TEXTURES.md)（2026-10-23）。这些是独立维度；笙、筝、扬琴及弹拨乐不能只归入“和弦类”，胡琴特殊复合技法也不能被单线惯例排除。

## 1. 已确认的项目规则

**吹管乐五线谱中的跳音点（staccato，上方一点），转换为简谱时暂不显示。**这是用户指定的项目显示规则，不是通行记谱规范。

- 作用条件：已确认乐器属于吹管乐，且记号语义确认为 `staccato`。
- 语义数据、原谱位置和校对记录仍保留，只在输出显示阶段隐藏。
- 不删除简谱的高低八度点、附点、双吐/三吐记号；不删除原谱的重音、保持音、换气或花舌说明。
- 不将该规则扩展到拉弦、弹拨乐；乐器归属或圆点含义不明时进入待校对，不按外形批量删除。
- **接入状态：已实现。** 配置 `parts[].instrumentFamily: "wind"` 后默认隐藏；未指定类别时保留。`techniques.windStaccato: "show"` 可显式恢复显示。

其余转换优先级为：**原谱明确图例/文字与作用范围 → 明确的 MusicXML 语义 → 经校对的乐器惯例 → 保留原文并报告待确认**。不能仅凭一个圆点、一条波线或三条斜线推断演奏动作。

下文“建议输出”是本项目拟采用的简谱表达；“待核样”表示须用实际输入及参考简谱确认专用字形。表内 `tr`、`///`、`○` 等为文字示意，PDF 应使用音乐字体或矢量图形，不能直接以普通字符代替正式字形。

## 2. 开源资料及其适用范围

| 资料 | 已查到的相关内容 | 本项目如何使用 |
| --- | --- | --- |
| [MusicXML 源码仓库](https://github.com/w3c-cg/musicxml)及 [4.0 参考规范][mx] | 区分技术记号、装饰音、奏法、方向文字和跨音符线段 | 作为语义层依据；MusicXML 保留了什么，和 OMR 实际识别到了什么，分别检查 |
| [SMuFL 源码仓库](https://github.com/w3c-cg/smufl)及[字形规范][smufl] | 吐音、弓向、泛音、震音、拨弦、琶音和波线的命名与编码 | 作为字形层依据；字形存在不等于它有通用的中国乐器技法含义 |
| [Bravura][bravura]（OFL-1.1） | SMuFL 的参考音乐字体 | 沿用项目已有字体，嵌入 PDF；中文技法仍由中文字体或经确认的自定义矢量图形补充 |
| [MuseScore Studio][musescore] | 开源记谱软件、MusicXML 导入导出与排版实现 | 用作后续构造测试谱、交叉核对的参考；不据此声称全部民乐指法可自动转换 |
| [ssb22/jianpu-ly][jianpu-ly]（Apache-2.0） | 提供二胡指法 `Fr=0/4`、滑音 `slideUp/slideDown`、`harmonic` 等符号入口，以及琶音 `arpUp/arpDown/arp`、单/双音震音语法；依赖 LilyPond | 参考记号表达和测试思路；本项目继续直接生成 PDF |
| [Kai2510/mxml2jp][mxml2jp]（Apache-2.0） | MusicXML → jianpu-ly 输入；列出空弦、泛音、指法的 `Fr=`/命令映射，以及 tremolo 数据处理 | 参考解析路径；它不是完整的民族乐器符号标准，也不证明 PDF 识别正确 |

开源实现也存在项目特定的替代画法。例如 [mxml2jp 的映射表][mxml2jp]把 `staccato` 输出为三角形标记，这不符合本项目的吹管隐藏规则，不能照搬；其表中也将 `snap-pizzicato` 与左手拨弦关联，而 [SMuFL][sf-plucked] 将 snap pizzicato 和 left-hand pizzicato 列为不同字形。这里应保留区别并核对原谱，不沿用未经验证的同义映射。`jianpu-ly` 中某个自定义符号命令的名称，也不能单独证明它对应所有出版社的同名民族技法。

补充使用香港康乐及文化事务署音乐事务处的[笛子][dizi]、[二胡][erhu]、[琵琶][pipa]、[古筝][guzheng]教材要求，以及张冀文《[胡琴声部乐队训练艺术的异同][huqin]》。这些是官方公开可读资料，**不等同于开源授权的图形素材**。它们用于核对常见技法种类；不能据此推导所有出版物都采用同一个符号。本文不复制教材谱例或符号图片。

检索得到的组合方案是：MusicXML 管语义，SMuFL/Bravura 管通用字形，乐器配置和原谱图例管民族乐器的具体解释。上述资料没有提供可直接套用、覆盖所有民乐技法的五线谱—简谱一一对应表。

## 3. 各组通用的记号

本表是转换约定。源语义参考 [MusicXML][mx]；装饰音、震音和跨音符线段分别保留，不能因外观相似而合并。

| 编号 | 五线谱输入 | 简谱建议输出 | 约束 |
| --- | --- | --- | --- |
| C01 | 不同音高间的圆滑线 `slur` | 对应数字上方的连线，保留起止事件 | 不凭连线推断具体吐法、弓法或弹拨指序 |
| C02 | 同音延音线 `tied` | 对应同音数字间延音线 | 与乐句线分开；和弦中须绑定到具体音高 |
| C03 | 前/后倚音 `grace` | 小号数字及其减时线，倚音下方小钩接主音 | 零记谱时值，与主音同小节；不擅自把全部倚音解释为打音 |
| C04 | `trill-mark`，可带延续波线及辅助音升降号 | 主音上方音乐字形 `tr`，需要时延伸波线 | 辅助音变化单独保留；不自动展开成若干实音 |
| C05 | `mordent` / `inverted-mordent` | 保留原装饰音种类的专用字形 | 保留原类型、升降号和图例，避免仅凭“上/下波音”中文名称反推类型 |
| C06 | 单音/双音震音斜线 `tremolo` | 单音斜线或双音间震音短杠，数量与类型忠于原谱 | 不改变小节拍数；与音符减时线分离，详见第 7 节 |
| C07 | `fermata` 延长记号 | 音符或休止上方的延长字形 | 不直接修改谱面时值 |
| C08 | `accent`、`strong-accent`、`tenuto` | 音符上方重音/强重音/保持音字形 | 保持音短横不放在数字中线，避免与延时线混淆 |
| C09 | 换气 `breath-mark` | 对应节拍位置上方的换气记号 | 以原谱为准，不增补休止或移动节拍 |
| C10 | 力度、速度、表情文字、渐强渐弱 | 沿用专用力度字体、西文术语字体和有起止拍位的线段 | 技法文字与 `p`、`f` 等力度分开；不得把 `pizz.` 的 p 当弱奏 |

## 4. 吹管乐对应表

覆盖梆笛、曲笛、新笛，并为箫、唢呐、管子、笙保留入口。笛子的常见技法类别依据[音乐事务处笛子教材][dizi]；双吐、三吐及指孔字形参考 [SMuFL 吹管技法][sf-wind]。下表的简谱位置及中文回退方式属于项目建议。

| 编号 | 技法/适用对象 | 五线谱中应查找的证据 | 简谱建议输出与处理 |
| --- | --- | --- | --- |
| W01 | 跳音，吹管组 | 明确的 `staccato` 上方点 | **暂不显示该跳音点**；保留内部语义，不影响八度点与附点 |
| W02 | 连奏 | 圆滑线、`legato` 或中文说明 | 对应音组上方连线；不把缺少跳音点的音自动判断为连奏 |
| W03 | 单吐 | “单吐”、T 等明确文字/图例 | 保留原文或确认后的单吐标记；普通无连线音符不自动添加 T |
| W04 | 双吐 | `technical/double-tongue`，或明确“双吐” | 音符上方双吐音乐字形；文字回退“双吐”。不是两个高音点 |
| W05 | 三吐 | `technical/triple-tongue`，或明确“三吐” | 音符上方三吐音乐字形；文字回退“三吐”，保留原音组范围 |
| W06 | 花舌 | “花舌”、flutter-tongue、Flz. 等文字/图例；有时另配震音斜线 | 明确时写“花舌”并保留原有斜线/范围；孤立 `tremolo` 不自动改称花舌。专用简谱字形待核样 |
| W07 | 颤指/指颤音 | `tr`、辅助音信息、颤指说明 | `tr` 及相应延续波线；不能与气震音归为同一技法 |
| W08 | 气震音/气颤音 | 明确文字、vibrato 或原谱图例 | 标“气震音”等原文；有明确持续范围时加范围线，不凭一般波线推断 |
| W09 | 波音 | 明确的波音装饰记号 | 保留 C05 的专用字形，不改成吐音符号 |
| W10 | 打音、叠音、赠音、垛音等 | 原谱短音、倚音组、文字和作品图例 | 已写出的音按实际倚音/实音转换；原文补充动作信息。各名称不统一替换为同一种倚音，特殊字形待核样 |
| W11 | 上/下历音、滑音 | 明确音列、斜线/波线、`slide` / `glissando` 或文字 | 已写出的音列保留；连接型记号按源起止音连接。无终止音的箭头保留为开放滑音，不捏造终点 |
| W12 | 换气、循环换气 | 换气符、明确“循环换气”等文字 | 换气用 C09；循环换气用原文及其范围，两者不互相替换 |
| W13 | 指孔、特殊指法、超吹等 | 指法图、孔位、文字说明 | 保留图例或可读文字；指孔图需单独建模，不能将西洋木管孔位字形直接套成笛子指法 |
| W14 | 笙的和弦及特殊发音 | 明确同时音头、分声部，以及技法文字 | 和弦数字纵向对齐、共享拍位；和弦本身不自动解释成“复音特殊技法”。呼吸/舌法须另有源证据 |

W13、W14 是覆盖范围与保留策略，不代表已核定各类笙、唢呐、管子的专用符号全集；后续按实际分谱图例扩充。

## 5. 拉弦乐对应表

重点为高胡、二胡、中胡。常见弓法、揉弦类别可参考[胡琴声部训练资料][huqin]和[二胡教材][erhu]；弓向及泛音字形参考 [SMuFL 弦乐技法][sf-string]。同族乐器可共享记号语义，不能共享猜测出来的定弦、指法和移调。

| 编号 | 技法/信息 | 五线谱中应查找的证据 | 简谱建议输出与处理 |
| --- | --- | --- | --- |
| B01 | 弓向 | `down-bow` / `up-bow` 或明确弓向符号 | 保留对应音乐字形，置于音符/音组上方；换成“拉/推”前核对原谱图例与乐器约定 |
| B02 | 连弓 | 明确弓法连线或“连弓”说明 | 保留音组连线；只有一般 `slur` 时先保留为连线，不追加“一弓”解释 |
| B03 | 分弓、快弓 | 明确文字、弓向序列或图例 | 保留已标内容；无连线不构成自动补交替弓向的依据 |
| B04 | 顿弓、跳弓 | 跳音/楔形奏法、文字及弓法上下文 | 保留相应奏法字形和文字；**不适用吹管跳音隐藏规则**。单个点不足以区分顿弓与跳弓 |
| B05 | 连顿弓、抛弓等复合弓法 | 连线内多个奏法点、jete 字形或明确说明 | 组内点与弓法线同时保留；不能删掉点只剩连奏线，专门的抛弓组合待核样 |
| B06 | 颤弓/震音 | `tremolo` 斜线及明确弓法文字 | 按单音/双音震音绘制斜线；有“颤弓”原文则保留，不改为揉弦波线 |
| B07 | 揉弦及滚揉、压揉、滑揉等 | vibrato、揉弦类型文字或作品指定波线 | 保留类型文字与作用范围；不默认所有长音都补揉弦，也不将“揉弦”改写成 `tr` |
| B08 | 滑音、滑指 | 连至另一音的滑线、开放滑音或文字 | 保留方向与两个锚点；连接数字侧边，避开倚音小钩和乐句线 |
| B09 | 自然/人工泛音 | 泛音圆圈、菱形音头、`harmonic` 及基音/触点/实音属性 | 使用独立泛音圈/文字，不能作八度点；保留各音高角色，不能把人工泛音触点与实音当普通和弦 |
| B10 | 拨弦及恢复弓奏 | `pizz.`、“拨弦”、`arco` 或其他明确恢复标记 | 起始处标文字并维护持续状态；遇 `arco` 等明确指令恢复。不可只标一个音后默认结束 |
| B11 | 左手拨弦等细分 | 明确左手拨弦符号/文字 | 保留专用字形或“左手拨弦”；普通加号须先排除其他图例含义 |
| B12 | 指法、空弦、弦号、把位 | `fingering`、`string`、原文/图例 | 指法用小字号独立层；空弦指法 0 不作休止，弦号与把位不作简谱音级 |
| B13 | 弱音、近琴码等特殊音色 | 原文说明、mute 或明确专用符号 | 保留开始/解除状态与原文；不根据音区、力度推断。扩展字形逐项核样 |

## 6. 弹拨乐及扬琴对应表

琵琶的弹挑、轮、扫及组合指法类别参考[琵琶教材][pipa]；筝的勾托抹、撮、摇与按滑类别参考[古筝教材][guzheng]。通用琶音、拨弦和止音字形参考 [SMuFL 弹拨技法][sf-plucked]。对阮、柳琴、三弦等，本版先给出保留策略；各乐器专用手势符号仍须核对分谱图例。

| 编号 | 技法/适用对象 | 五线谱中应查找的证据 | 简谱建议输出与处理 |
| --- | --- | --- | --- |
| P01 | 琵琶弹、挑；阮/柳琴拨弦方向 | 明确手势字形、弹/挑文字及乐器图例 | 优先保留经确认的手势符号；未核定时写“弹”“挑”等原文，不将不同乐器的上下拨统一成琵琶弹挑 |
| P02 | 轮指、长轮、短轮 | 轮指文字、专用轮指记号，或有图例支持的震音斜线 | 保留轮指类型与范围；按源斜线数量绘制，不把所有长音自动加轮指 |
| P03 | 琶音 | 和弦旁竖向波线、`arpeggiate`，可含方向 | 和弦左侧绘制覆盖相应音高范围的波线，方向明确才加箭头；不自行分解成占拍的新音符 |
| P04 | 扫、拂、扫弦 | 方向箭头、扫/拂文字及作品图例 | 保留手势方向、音组范围和原文；“音高由低到高”与“手指向上/下”分开，不凭箭头改写成琶音 |
| P05 | 扫轮、夹扫、勾轮、挑轮等 | 明确复合指法、组合文字/符号 | 保留先后次序及各段范围，不合并为一个没有区分的 tremolo |
| P06 | 双弹、分、摭弹、摭分等 | 原谱专用字形或明确文字 | 先以原文小字号输出；具体指法字形待核样，不能只由和弦音程反推手势 |
| P07 | 古筝勾、托、抹等指法 | 指法符号、文字、左右手区分 | 原手势符号经核样后使用，否则保留中文；`pluck` 的指名字母不自动翻译成这些动作 |
| P08 | 古筝大撮、小撮 | 撮的符号、明确手势说明与同时音 | 和弦仍按实际音高纵排，手势独立标于上方；不能仅从八度或其他双音断定大撮/小撮 |
| P09 | 古筝摇指、短摇、扫摇 | 摇指/扫摇文字、专用符号或有图例的斜线 | 保留类别与范围；与琵琶轮指使用不同语义 ID，即使最终斜线外观相似 |
| P10 | 按音、上/下滑音、推挽 | 按滑文字、方向线、`bend` 或明确音高端点 | 有目标音时绑定目标；只有弯音幅度时保留幅度/文字，不虚构目标数字，不改写主音时值 |
| P11 | 颤音、吟揉类变化 | 明确技法文字、波线及图例 | 保留原文与持续范围；须与相邻音交替的 `trill` 分开，专用字形待核样 |
| P12 | 泛音 | 圆圈、菱形音头、`harmonic` | 采用 B09 的音高角色保留规则；泛音圈独立于八度点 |
| P13 | 止音、煞音、制音 | 明确 damp 符号或文字 | 专用止音字形或中文，绑定终止拍位；不凭短时值推断止音 |
| P14 | 左手拨弦、击勾弦等 | 明确手法文字，或含义已核对的 `hammer-on` / `pull-off` 等 | 保留动作类别与两音关系；不将其他乐器的 H/P 字母直接等同于某个民族指法 |
| P15 | 并弦、绞弦、拍板、敲击等扩展技法 | 原谱图例、特殊音头及文字 | 保留图例与非普通音高属性；不把叉形音头任意解释成某种敲击。字形和音高转换待专题确认 |
| P16 | 扬琴轮竹、左右竹及特殊击弦 | 明确扬琴文字、震音、左右手/竹标记 | 可随乐团弹拨声部管理，但按击弦语义处理；不解释为琵琶弹挑，手/竹符号须按图例保留 |

MusicXML 的 [`pluck`][mx-pluck] 描述拨弦所用的手指，常见值如 p、i、m、a；它不是琵琶“弹/挑”的通用编码。专用中文指法可以使用保留原文的 `other-technical`，但仍需保留乐器和作品图例，不能只存一个通用“技法”字符串。

## 7. 容易混淆的符号及音高/时值规则

| 外观相近的情况 | 必须区分的语义 | 项目处理 |
| --- | --- | --- |
| 音符上方的点 | 跳音、简谱高八度、双吐/三吐中的组成部分 | 先分类，再应用 W01；八度点紧邻数字，奏法在独立上方层 |
| 音符右侧的点 | 时值附点与附近的技法点 | 附点参与时值且必须保留 |
| 小圆圈或数字 0 | 泛音圈、空弦指法、简谱休止 | 三种独立对象，不按轮廓互相替换 |
| 横线 | 减时线、延时线、保持音、震音短杠 | 减时线在数字下方、延时线在字高中间；其余使用独立标记层 |
| 波线/斜线 | 颤指、揉弦、气震音、花舌、颤弓、轮指、琶音、滑音 | 结合文字、乐器、锚点判断；不能只按“波线/三斜线”归一化 |
| 连线 | 延音、乐句/连弓、倚音专用小钩、滑音线 | 分别维护类型和起止锚点；倚音仍用下方小钩 |
| 和弦/特殊音头 | 普通和弦、泛音触点与实音、特殊无固定音高音头 | 转换前确定每个音头的角色，避免生成错误数字和弦 |

[`tremolo` 的 MusicXML 定义][mx-tremolo]区分 `single`、`start/stop` 双音和 `unmeasured`；内容表示震音短杠数量，既有符杠由 `beam` 另行描述。双音震音还涉及记谱类型与实际时值的特定关系。因此后续实现必须保留类型、短杠数、实际 duration、type、beam 和 time-modification，不能简单将“3”当文字打印，也不能统一替换成 `///` 后丢失时值信息。

[`harmonic` 定义][mx-harmonic]允许区分自然/人工泛音，以及基音、触点音、实际发声音。延续项目当前 written 音高策略，但遇泛音先保留这些角色；**尚未明确显示的是触点还是实音时报告待校对**，不自动换算八度或把所有音头并成和弦。

[`arpeggiate`][mx-arpeggiate]、[`slide`][mx-slide] 与 [`glissando`][mx-glissando]分别保留。琶音是和弦演奏方式，滑音有自己的起止关系，已有分解音列则按原音符转换，不在这些表达之间任意改写。

## 8. 可直接采用的通用音乐字形

以下名称和编码取自 SMuFL；这是字形候选清单，具体接入状态见第 10 节。字符位于私用区，Markdown 阅读器可能无法显示，因此列名称和码位。

| 用途 | SMuFL 名称及码位 | 使用注意与来源 |
| --- | --- | --- |
| 双吐/三吐（上方） | `doubleTongueAbove` U+E5F0；`tripleTongueAbove` U+E5F2 | 独立音乐字形，不能拿八度点拼；[字形表][sf-wind] |
| 下弓/上弓 | `stringsDownBow` U+E610；`stringsUpBow` U+E612 | 依原谱语义使用，不从演奏姿势猜弓向；[字形表][sf-string] |
| 泛音 | `stringsHarmonic` U+E614 | 不等同于数字上方八度点；[字形表][sf-string] |
| 左手拨弦 | `pluckedLeftHandPizzicato` U+E633 | 原谱确认为左手拨弦后使用；[字形表][sf-plucked] |
| 止音 | `pluckedDamp` U+E638；`pluckedDampAll` U+E639 | 单音止音与全部止音分开；[字形表][sf-plucked] |
| 单音震音短杠 | `tremolo1` U+E220；`tremolo2` U+E221；`tremolo3` U+E222 | 简谱可用矢量短杠，位置与减时线分离；[字形表][sf-tremolo] |
| 颤音延续波线 | `wiggleTrill` U+EAA4 | 按起止位置拼接，不靠拉伸单个字形；[字形表][sf-lines] |
| 琶音波线及箭头 | `wiggleArpeggiatoUp` U+EAA9、`wiggleArpeggiatoDown` U+EAAA；箭头 U+EAAD/U+EAAE | 按和弦覆盖高度拼接；[SMuFL 推荐可变长度实现][sf-plucked] |
| 滑音/揉弦波线 | `wiggleGlissando` U+EAAF；`wiggleVibrato` U+EAB0 | 外形不负责判定具体民族技法；[字形表][sf-lines] |

琵琶弹挑、筝勾托抹、某些轮指/摇指和笛子专用装饰符号，在本次核查的通用表中没有确定的通用对应。应先以中文明确表达，再根据参考简谱建立有出处的矢量字形；不能用形似的西洋技法字形冒充。字号、间距、线宽、位置和文字回退策略均应可配置。

## 9. PDF 识别与排版接入建议

### 识别与保留

1. 每份分谱明确乐器及 `wind / bowed / plucked / struck-string` 语义类别；乐团声部归组与发声方式分别记录。
2. OMR 之后检查 MusicXML 中是否确实存在技法。若原 PDF 有符号而 XML 没有，属于识别遗漏，不应靠渲染器凭空补齐。
3. 原谱矢量文字、字形和线段可作核对证据；扫描 PDF 则依赖 OMR、局部图像和人工校对。单凭字体码位或形状不能保证正确分类。
4. 未知记号保留原文、XML 片段/文件位置、页码和区域，进入待校对清单；结构化不了的指法图可保留截图作为证据，不能静默忽略。

建议未来的完整技法记录至少包含：`techniqueId`、乐器、事件/和弦成员、起止事件及拍位、原 XML 类型与属性、原文、原 PDF 位置、语义确认依据、渲染策略和待校对原因。目前已保留技术记号的 `sourceXml`、`sourceAttributes`、泛音类别/音高角色及震音短杠数，显示结果记录在 `techniqueLayout`。下例是**完整语义结构的建议，不是现有配置接口**：

```json
{
  "techniqueId": "wind.staccato",
  "instrumentFamily": "wind",
  "instrumentId": "bangdi",
  "anchorEventId": "example-note-1",
  "source": {
    "xmlKind": "staccato",
    "placement": "above",
    "originalMusicXml": "retained-in-run-directory"
  },
  "renderPolicy": "suppress",
  "policyReason": "user-rule-wind-staccato-2026-10-20"
}
```

### 排版

- 单音记号绑定音符中心；和弦技法可绑定某一个音或整个和弦，必须明确。
- 八度点贴近数字；`tr`、波音等上标贴近音符，只有连线首尾可略上移并允许适当重合；文字置于上标和辅助升降号上方。连音数单独放在组线中央。最新细则与参数见[上标与连音组](ORNAMENTS_TUPLETS.md)。
- 倚音连接继续使用下方小钩。琶音波线在和弦侧面，滑音线连接数字侧缘，均不占用八度点位置。
- 持续技法维护开始/停止状态。跨行线段按音乐起止拍位拆段，不在每个音上重复整段技法文字；续行提示可配置。
- 和弦、双音震音、扫弦方向及指法会增加横向空间，需要参与小节最小宽度计算；不能靠压缩到与数字重叠来维持四小节一行。
- 专用符号按实际墨迹高度与数字协调；中文技法、音乐字形和西文术语分别配置字体。后续参数并入现有[排版参数说明](LAYOUT_PARAMETERS.md)。

## 10. 与当前实现的对照

核查文件：[解析器](../jianpu/musicxml.py)、[PDF 渲染器](../renderer/render.ts)。以下为 2026-10-20 当前状态；解析器内部的 `supported` 集合只表示某些标签不触发回退警告，不能视为完整的图形支持。

| 项目 | 当前行为 | 后续缺口 |
| --- | --- | --- |
| 连线、延音、前/后倚音 | 已有起止与专用绘制 | 扩充技法组合的避让样例 |
| `trill-mark`、波音、延长 | 已使用音乐字形；颤音附属降号有专项处理 | 其他装饰升降号、延续波线及更多组合待补齐 |
| `staccato` | 已按显式乐器类别过滤；吹管默认隐藏，数据保留，报告记录隐藏原因 | 当前梆笛实例隐藏 53 个跳音点；未知类别不隐藏 |
| 双吐/三吐、上下弓 | 已用 Bravura 专用音乐字形并参与连线/文字避让 | 更复杂的组合记号和下方放置策略待扩充 |
| `tremolo` | 已结构化短杠数；有拍单音绘制斜线，双音按起止配对并支持跨行/跨页分段 | 自由震音暂用文字并报告；不从斜线猜花舌、轮指或颤弓 |
| 双音震音时值 | 保留实际 duration 和原 time-modification；其中震音本身的 2:1 因子不再显示成二连音数字 | 复杂嵌套连音与特殊出版社写法继续核样 |
| `arpeggiate` | 已按和弦音域高度绘制矢量波线；明确 up/down 才加箭头；重复和弦成员记号去重 | 多谱表共用一条琶音线尚待支持 |
| 泛音、左右手拨弦、止音 | 自然泛音圈、left-hand/snap pizzicato、damp/damp-all 已用独立字形 | 人工泛音保留类别/音高角色并明确报告待校对，不自动改写音高 |
| `fingering`、`pluck`、`other-technical` | 保留原文、XML 与属性，使用可配置的小字号标注；弹/挑/扫/轮先用中文 | 专用民族手势字形、状态型技法和长范围线仍待核样实现 |
| 弯音、滑音、专用指法图 | 尚无完整结构化与连线支持；部分标签仅作回退 | 从保留的原 XML 补足端点等数据；不能宣称无损支持 |

本轮已将上述通用符号和吹管过滤接入渲染器，并重新输出完整梆笛 PDF。2 页的人工构造样张用于展示三组技法，不作为真实 PDF 识别准确性的证据。

### 现有配置与复现

```json
{
  "parts": [{"id":"bangdi", "name":"梆笛", "instrumentFamily":"wind"}],
  "techniques": {"windStaccato":"hide"},
  "layout": {"techniques": {"symbolSizeRatio":1, "textSize":8, "aboveGap":4,
    "lineWidth":0.7, "tremoloWidth":9, "tremoloGap":3, "tremoloRise":4,
    "arpeggioGap":4, "arpeggioWidth":4, "arpeggioWaveHeight":5, "arpeggioArrowSize":3}}
}
```

乐器类别支持 `wind / bowed / plucked / struck-string / unknown`。这只是技法显示分类，不决定定弦、移调或指法。图形距离和文字字号均为 pt，`symbolSizeRatio` 相对简谱数字字号。

```powershell
& .\scripts\build.ps1
& .\.venv\Scripts\python.exe scripts\make-technique-example.py
& .\.venv\Scripts\python.exe -m jianpu from-musicxml --config configs\bangdi-full.json --draft --overwrite output\jianpu\bangdi-full-source\bangdi-reviewed.musicxml
& .\.venv\Scripts\python.exe scripts\verify-technique-example.py
& .\.venv\Scripts\python.exe scripts\verify-bangdi-full.py
```

输出为 `output/jianpu/民族乐器_特殊技法_转换示例.pdf`（人工构造）和 `output/jianpu/丝绸之路_梆笛_完整简谱_校对稿.pdf`（真实输入的完整转换）。样张源 MusicXML、配置及最新运行报告入口保存在 `tmp/technique-example/`。

## 11. 后续实现顺序与验收样例

建议先处理已确认的吹管规则与通用符号，再逐件乐器核定手势字形：

| 顺序 | 范围 | 最小验收内容 |
| --- | --- | --- |
| P0 | 吹管跳音过滤、点的区分、原始技法保留 | 同一吹管高音同时有八度点和跳音点：只隐藏后者；附点时值不变；双/三吐不消失；二胡跳音仍保留 |
| P1 | 双/三吐、弓向、单/双音震音、和弦琶音、滑音 | 专用字形正确，绑定源事件；震音不改变小节总拍数；琶音覆盖正确和弦；跨行起止不丢失 |
| P2 | 琵琶/筝/阮等手势、泛音细分、状态型技法 | 核定原谱与参考简谱样例；手势与音级分层；泛音角色不混为和弦；拨弦至恢复弓奏的范围正确 |

每类至少准备“输入五线谱局部 → 原 MusicXML → 语义记录 → 输出简谱局部”的可核对样例。优先选真实原谱，再用人工构造谱验证边界；不能用合成测试代替真实 PDF 的识别审查。

## 资料链接

全部链接核查于 2026-10-20。仓库的使用方式与许可证以其实际文件为准；公开教学资料只作为文献依据。上文每节区分了源资料支持的语义/类别和本项目建议的输出方式。

- 通用语义：[MusicXML 4.0][mx]；[`technical` 元素][mx-technical]；[`other-technical` 元素][mx-other]。
- 重点语义：[`tremolo`][mx-tremolo]、[`harmonic`][mx-harmonic]、[`pluck`][mx-pluck]、[`arpeggiate`][mx-arpeggiate]、[`slide`][mx-slide]、[`glissando`][mx-glissando]。
- 字形：[SMuFL][smufl]；[吹管][sf-wind]、[弦乐][sf-string]、[弹拨][sf-plucked]、[震音][sf-tremolo]、[可拼接线段][sf-lines]；[Bravura][bravura]。
- 开源实现：[MuseScore][musescore]、[jianpu-ly][jianpu-ly]、[mxml2jp][mxml2jp]。
- 民乐类别依据：音乐事务处[笛子（2025-09 修订）][dizi]、[二胡（2023-09 修订）][erhu]、[琵琶（2012-01 修订）][pipa]、[古筝（2012-01 修订）][guzheng]；张冀文《[胡琴声部乐队训练艺术的异同][huqin]》，香港中乐团网站公开文档。

[mx]: https://www.w3.org/2021/06/musicxml40/
[mx-technical]: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/technical/
[mx-other]: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/other-technical/
[mx-tremolo]: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/tremolo/
[mx-harmonic]: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/harmonic/
[mx-pluck]: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/pluck/
[mx-arpeggiate]: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/arpeggiate/
[mx-slide]: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/slide/
[mx-glissando]: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/glissando/
[smufl]: https://smufl.formats.music/latest/
[sf-wind]: https://smufl.formats.music/latest/tables/wind-techniques.html
[sf-string]: https://smufl.formats.music/latest/tables/string-techniques.html
[sf-plucked]: https://smufl.formats.music/latest/tables/plucked-techniques.html
[sf-tremolo]: https://smufl.formats.music/latest/tables/tremolos.html
[sf-lines]: https://smufl.formats.music/latest/tables/multi-segment-lines.html
[bravura]: https://github.com/steinbergmedia/bravura
[musescore]: https://github.com/musescore/MuseScore
[jianpu-ly]: https://github.com/ssb22/jianpu-ly
[mxml2jp]: https://github.com/Kai2510/mxml2jp
[dizi]: https://www.lcsd.gov.hk/en/mo/common/doc/faq/faq_01_syb_0301.pdf
[erhu]: https://www.lcsd.gov.hk/en/mo/common/others/faq/imts/faq_01_syb_0101.pdf
[pipa]: https://www.lcsd.gov.hk/en/mo/common/doc/faq/faq_01_syb_0203.pdf
[guzheng]: https://www.lcsd.gov.hk/en/mo/common/doc/faq/faq_01_syb_0206.pdf
[huqin]: https://www.hkco.org/uploads/docs/55e02ebda62881.pdf
