# Excel-cad

把展厅家具 Excel 清单、CAD 底图和家具库 DXF 自动整理成按分区归纳的家具索引图。

## 最终固化规则

- 家具编码只按 **前 6 位**匹配家具库。
- 不再把家具直接堆放到展厅实际区域内。
- 保持底图不动，在图纸空白处按 `01区 / 02区 / ...` 分区归纳。
- 同一家具型号每个分区只展示 1 个家具平面图块，数量用 `×N` 标注。
- 成品保留 Excel 中的**完整家具编码**。
- 成品保留家具库中的**品牌名**（能够识别时）。
- 家具编码与品牌名均放在家具图块的**几何中心**。
- 所有新增文字统一使用 **黑体 / SimHei**，CAD 文字样式名为 `HEITI`。
- 家具库中不存在或无法确定的型号，在对应分区用**红色** `MISSING + 编号 + 数量` 标出。
- 家具块尽量保持 `INSERT` 块，不炸开。

完整执行规范见 [`SKILL.md`](./SKILL.md)。

## 输入文件

建议准备 3 个文件：

```text
project/
├─ showroom.xlsx          # 区域 / 家具编号 / 数量
├─ base.dxf               # 展厅底图
└─ furniture_library.dxf  # 家具库
```

Excel 可以在同一张表中存在多组重复的 `区域 / 编号 / 数量` 列，脚本会尝试自动识别。

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python scripts/excel_cad.py \
  --excel showroom.xlsx \
  --base base.dxf \
  --library furniture_library.dxf \
  --output showroom_zone_index.dxf \
  --report showroom_zone_index_report.csv
```

Windows PowerShell 示例：

```powershell
python scripts/excel_cad.py `
  --excel "202609无锡展厅还原.xlsx" `
  --base "底图.dxf" `
  --library "家具库.dxf" `
  --output "无锡展厅_家具按分区归纳.dxf" `
  --report "无锡展厅_家具按分区归纳_匹配报告.csv"
```

## 匹配逻辑

脚本会先规范化编码，再提取常见的 `2字母 + 4数字` 作为 6 位匹配键。

例如：

```text
BF1182Z3       -> BF1182
PF0354-5-1Z2   -> PF0354
AC1234HZ       -> AC1234
```

类似 `CY` 这种不足 6 位、且无法唯一确定家具的编码不会强行匹配，会作为缺失/歧义项输出。

## 输出

默认生成：

1. `*.dxf`：按分区归纳后的最终 CAD；
2. `*.csv`：家具匹配报告，包含区域、原始编号、6 位匹配键、数量、家具库块名、品牌和状态。

## 关于品牌名

脚本优先读取块属性；若家具库品牌是独立 `TEXT / MTEXT`，则通过家具块附近文字进行启发式识别。不同公司的家具库结构可能不同，因此如果品牌命名规则非常固定，可以在 `detect_brand()` 中继续增加白名单或规则。

## CAD 字体

脚本创建文字样式：

```text
Style: HEITI
Font:  simhei.ttf
```

打开 CAD 的电脑需要安装黑体（SimHei）。Windows 中文环境通常已经具备；若 CAD 找不到该字体，请在本机字体配置中确认 `simhei.ttf` 可用。

## 设计目的

这个 Skill 面向家居品牌陈列 / 展厅还原工作流，重点不是自动做最终空间陈列方案，而是把 Excel 清单和家具 CAD 库快速整理成一张清晰、可核对、可继续编辑的分区家具索引图，减少人工逐个查找、复制、统计和标注的时间。
