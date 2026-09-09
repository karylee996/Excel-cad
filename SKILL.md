---
name: excel-cad
description: Convert a showroom furniture Excel schedule, CAD base drawing, and CAD furniture library into a clean zone-based DXF index. Match by the first 6 characters of the normalized code, preserve full codes and brands, center code and brand text, use SimHei/黑体, place zone indexes around the base near their area numbers, create true-size rectangular placeholder blocks from Excel length/width for unmatched furniture while keeping code/name red, and ALWAYS finalize/validate the returned DXF for AutoCAD 2021 compatibility.
---

# Excel-CAD Showroom Furniture Index Skill

## Purpose

Convert an Excel furniture schedule + showroom base DXF + furniture-library DXF into a clean, editable CAD furniture index for showroom restoration work.

The finished drawing must be convenient for the next manual step: quickly finding a zone's furniture and dragging / arranging it into the real showroom area.

## Required inputs

1. Excel schedule (`.xlsx`): zone / furniture code / quantity. Multiple repeated column groups are allowed.
2. Base drawing (`.dxf`): preserve original geometry and position.
3. Furniture library (`.dxf`): furniture preferably stored as `INSERT` blocks; model code may be in block name or attributes; brand may be an attribute or nearby text.

## Furniture matching rule

Match by the first usable **6-character furniture key**, normally `2 letters + 4 digits`.

Examples:
- `BF1182Z3` → `BF1182`
- `PF0354-5-1Z2` → `PF0354`
- `AC1234HZ` → `AC1234`

Normalize to uppercase and ignore spaces / separators while finding the key. Do not force-match short ambiguous codes such as `CY`.

## Excel parsing

Detect columns by meaning, not hard-coded letters:
- 区域 / 区域号 / 分区 / AREA / ZONE
- 编号 / 家具编号 / 产品编号 / CODE / MODEL / 型号
- 数量 / QTY / QUANTITY / 数目
- 备注 / 尺寸 / 规格 / SIZE / DIMENSION / SPEC
- optional product name: 名称 / 品名 / 产品名称 / NAME

For dimension text such as `277*109*76cm`, `64.5×35×54cm`, `295*106*74~100cm`:
- use the first numeric value as plan length;
- use the second numeric value as plan width;
- height is not used to draw the plan placeholder;
- convert centimetres to millimetres for CAD geometry;
- accept `*`, `×`, `x`, `X` and similar separators;
- if fewer than two reliable numeric dimensions are available, do not guess.

Normalize numeric zones to `01区`, `02区`, etc.

## Layout rules

### 1. Keep the base drawing unchanged

Do not put the furniture index directly inside the real showroom zones. Do not move, scale, explode, or delete the original floor plan.

### 2. Put each zone index near its real zone

Read zone-number text positions such as `01`, `02`, `01区`, `02区` from the base drawing.

For every zone:
1. Find its zone-number coordinate.
2. Determine the nearest drawing boundary: top / bottom / left / right.
3. Place the zone furniture index outside the base drawing on that nearest side.
4. Preserve the spatial order of zone numbers along each side.
5. Avoid overlap by packing the nearest row/column first; if needed expand outward to a second/third row instead of moving zones far away laterally.

If zone positions cannot be detected reliably, use a compact perimeter layout around the base drawing. Do not default to one long stack on the right.

### 3. Clean and minimal workspace

- One thin frame per zone.
- No dense cell grid unless necessary.
- Adaptive frame size based on furniture count.
- Consistent furniture thumbnail scale and spacing.
- Small zones stay small.
- Keep sufficient white space and avoid visual clutter.

### 4. One graphic per summarized furniture item

Show each furniture item/model once per zone. Do not repeat geometry just because quantity > 1. Show quantity as `×N`.

### 5. Preserve furniture geometry

For matched items:
- copy the complete furniture block from the library;
- keep it as an editable CAD `INSERT` whenever possible;
- do not explode into loose linework unless absolutely necessary;
- scale uniformly while preserving proportions.

### 6. Furniture code + brand at block center

For every matched item:
- display the complete original Excel furniture code;
- display detected brand name when available;
- place both code and brand at the geometric center of the displayed furniture block;
- stack them vertically around the center;
- keep text editable.

### 7. All returned text in 黑体 / SimHei

Use CAD text style:
- style: `HEITI`
- font: `simhei.ttf`

Apply it to zone titles, furniture codes, brand names, quantities, red unmatched codes/names, dimension helper text, and generated annotations. When practical, convert returned `TEXT` / `MTEXT` / `ATTRIB` entities to the same style.

## Unmatched furniture: build a dimension placeholder instead of only text

If an item cannot be matched by the 6-character rule, first inspect the Excel remark/size/specification field.

### When valid length + width are available

Create an editable placeholder furniture block:
- block definition geometry is a simple clean rectangle using the real plan **length × width** in millimetres;
- block definition must be 1:1 true size, centered on the block origin;
- keep geometry black/neutral, not red, so the drawing stays visually clean;
- the displayed instance in the zone index may be uniformly scaled down to fit the same thumbnail area as normal library furniture;
- never distort X/Y independently;
- keep the **furniture code red**;
- if an Excel product name exists, keep the **product name red** as well;
- code/name stay centered on the placeholder graphic;
- quantity remains red when applicable;
- an optional small black `长×宽` helper label may be shown under the placeholder.

The red code/name indicate that this is still not a verified furniture-library block, even though a usable size-based placeholder now exists.

### When dimensions are missing or unreliable

- do not invent a rectangle size;
- do not guess from furniture category or image;
- keep only the red code (and red name if available) in the correct zone;
- do **not** write `MISSING`.

### Important block behavior

The placeholder block definition must retain true millimetre dimensions even if the index instance is visually scaled for layout. This keeps the source geometry available for later 1:1 placement/insertion.

## Brand detection

Priority:
1. block attributes;
2. nearby `TEXT` / `MTEXT` around the source furniture block;
3. preserve original spelling such as `Minotti`, `B&B`, `ARFLEX`.

Exclude furniture codes, dimensions, quantities, and generic labels from brand candidates.

# CRITICAL: AutoCAD 2021 DXF compatibility pipeline

A DXF must **never** be returned merely because `ezdxf.readfile()` can reopen it. That check is insufficient for AutoCAD.

The final returned DXF MUST pass the following compatibility pipeline every time:

1. Generate a working DXF.
2. Open it with `ezdxf.recover.readfile()`.
3. Run a document audit and repair recoverable issues.
4. Force DXF version to **`AC1027` (AutoCAD 2013 DXF)**.
5. Save as **ASCII DXF** (`fmt="asc"`).
6. Re-open the exact final bytes using `ezdxf.recover.readfile()`.
7. Reject the file if the final recovery auditor has structural errors.
8. Reject the file if modelspace is empty.
9. Reject the file if valid drawing extents cannot be calculated.
10. Reject the file if output size is suspiciously tiny/truncated.
11. Only after all checks pass may the DXF be returned.

Use `scripts/run_excel_cad_safe.py` as the default entry point. Any dimension-placeholder post-processing must happen **before** the final AutoCAD compatibility pass.

## Deliverables

Always generate:
1. **Validated final DXF**, passed through the AutoCAD 2021 compatibility pipeline.
2. Match report TXT/CSV with zone, original code, 6-character key, quantity, matched block, brand, status, and parsed dimensions when available.
3. Preview PNG when rendering is available.

## Final quality checks

Before returning any DXF:
- final file reports `dxfversion == AC1027`;
- final file passes `recover.readfile()` with no remaining structural errors;
- final modelspace entity count > 0;
- final drawing has valid non-empty extents;
- file size is not suspiciously small;
- original base drawing is still present;
- all expected zones exist;
- zone panels are outside / around the base drawing and near corresponding zone numbers where detectable;
- no unnecessary dense grids or clutter;
- full Excel code + brand are centered on matched furniture graphics;
- generated text uses `HEITI` / `simhei.ttf`;
- unmatched furniture contains no `MISSING` text;
- unmatched items with valid length+width have a true-size rectangular block definition and red code/name;
- unmatched items without reliable dimensions remain red text only;
- furniture remains as blocks where possible.

If any compatibility check fails, do **not** return the broken DXF. Repair/rebuild it in the same task and validate again.
