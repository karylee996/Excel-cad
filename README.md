# Excel-cad

把展厅家具 Excel 清单、CAD 底图和家具库 DXF 自动整理成**围绕底图、按区域就近归纳**的家具索引图，方便下一步手动把家具拖入对应展厅区域。

## 最终固化规则

- 家具编码按 **前 6 位**匹配家具库，常见格式为 `2字母 + 4数字`。
- 保持底图原位不动，不把家具索引直接塞进实际展厅区域。
- 自动读取底图中的 `01区 / 02区 / ...` 区域号位置。
- 每个区域的家具索引优先放到离该区域号最近的**上 / 下 / 左 / 右外围空白处**。
- 同一侧多个区域保持原有空间顺序；空间不足时向外扩成第二排/列，而不是全部堆到右侧。
- 每个区域只保留一个简洁外框，不画密集单元格边框，尽量保持工作空间干净。
- 同一家具型号在一个区域中只展示 1 个家具平面图块，数量用 `×N` 标注。
- 成品保留 Excel 中的**完整家具编码**。
- 成品保留家具库中的**品牌名**（能够识别时）。
- 家具编码和品牌名均放在家具图块的**几何中心**。
- 所有文字统一使用 **黑体 / SimHei**，CAD 文字样式名为 `HEITI`。
- 家具库中不存在或无法确定的型号，**只用红色显示家具编号**；不再显示 `MISSING`。数量大于 1 时保留红色 `×N`。
- 家具块尽量保持 `INSERT` 块，不炸开。

完整执行规范见 [`SKILL.md`](./SKILL.md)。

## 输入文件

```text
project/
├─ showroom.xlsx          # 区域 / 家具编号 / 数量
├─ base.dxf               # 展厅底图
└─ furniture_library.dxf  # 家具库
```

Excel 同一张表中可以存在多组重复的 `区域 / 编号 / 数量` 列，脚本会自动识别。

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

Windows PowerShell：

```powershell
python scripts/excel_cad.py `
  --excel "202609无锡展厅还原.xlsx" `
  --base "底图.dxf" `
  --library "家具库.dxf" `
  --output "无锡展厅_家具分区就近归纳.dxf" `
  --report "无锡展厅_家具分区就近归纳_匹配报告.csv"
```

## 匹配逻辑

```text
BF1182Z3       -> BF1182
PF0354-5-1Z2   -> PF0354
AC1234HZ       -> AC1234
```

类似 `CY` 这种不足 6 位、无法唯一确定型号的编码不会强行匹配，会在对应区域以红色原编号显示。

## 输出

1. `*.dxf`：围绕底图、按区域就近归纳的最终 CAD；
2. `*.csv`：匹配报告，包含区域、原始编号、6 位匹配键、数量、家具库块名、品牌和状态。

## 品牌识别

优先读取家具块属性；如果家具库把品牌作为独立 `TEXT / MTEXT`，脚本会通过家具块附近的文字进行识别，并保留原品牌写法。

## CAD 字体

```text
Style: HEITI
Font:  simhei.ttf
```

打开 CAD 的电脑需要能访问 `simhei.ttf`。

## 设计目的

这个 Skill 服务于家居品牌陈列 / 展厅还原工作流。重点不是直接完成最终空间陈列，而是把 Excel 清单和家具 CAD 库整理成一张**离对应区域近、容易查看、容易拖拽继续布置**的家具索引图，减少逐个查找、复制和核对的时间。
