---
name: excel-cad
description: Convert a showroom furniture Excel schedule, a CAD base drawing, and a CAD furniture library into a clean DXF furniture index grouped by zone. Match furniture by the first 6 characters of the normalized model code, preserve full Excel codes and detected brand names, center code and brand text on each furniture block, use SimHei/黑体 for all returned text, place zone indexes around the base drawing near their corresponding area numbers, show unmatched furniture as red codes only, and ALWAYS finalize/validate the returned DXF for AutoCAD 2021 compatibility. Use for showroom restoration, furniture schedule to CAD, Excel-to-DXF furniture indexing, zone-based CAD furniture summaries, or furniture-library matching workflows.
---

# Excel-CAD Showroom Furniture Index Skill

## Purpose

Convert an Excel furniture schedule + showroom base DXF + furniture-library DXF into a clean, editable CAD furniture index for showroom restoration work.

The finished drawing must be convenient for the next manual step: quickly finding a zone's furniture and dragging / arranging it into the real showroom area.

## Required inputs

1. Excel schedule (`.xlsx`): zone / furniture code / quantity. Multiple repeated `区域 / 编号 / 数量` column groups are allowed.
2. Base drawing (`.dxf`): preserve original geometry and position.
3. Furniture library (`.dxf`): furniture preferably stored as `INSERT` blocks; model code may be in block name or attributes; brand may be an attribute or nearby text.

## Furniture matching rule

Match by the first usable **6-character furniture key**, normally `2 letters + 4 digits`.

Examples:
- `BF1182Z3` → `BF1182`
- `PF0354-5-1Z2` → `PF0354`
- `AC1234HZ` → `AC1234`

Normalize to uppercase and ignore spaces / separators while finding the key. Do not force-match short ambiguous codes such as `CY`.

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

Apply it to zone titles, furniture codes, brand names, quantities, red missing codes, and generated annotations. When practical, convert returned `TEXT` / `MTEXT` / `ATTRIB` entities to the same style.

### 8. Missing furniture: red code only

If an item cannot be matched by the 6-character rule:
- do not substitute another model;
- keep it in the correct zone;
- show the furniture code itself in red;
- do **not** write `MISSING`;
- when quantity > 1, show a small red `×N`.

The red code itself is the missing indicator.

## Brand detection

Priority:
1. block attributes;
2. nearby `TEXT` / `MTEXT` around the source furniture block;
3. preserve original spelling such as `Minotti`, `B&B`, `ARFLEX`.

Exclude furniture codes, dimensions, quantities, and generic labels from brand candidates.

## Excel parsing

Detect columns by meaning, not hard-coded letters:
- 区域 / 区域号 / 分区 / AREA / ZONE
- 编号 / 家具编号 / 产品编号 / CODE / MODEL / 型号
- 数量 / QTY / QUANTITY / 数目

Normalize numeric zones to `01区`, `02区`, etc.

# CRITICAL: AutoCAD 2021 DXF compatibility pipeline

A DXF must **never** be returned merely because `ezdxf.readfile()` can reopen it. That check is insufficient for AutoCAD.

The final returned DXF MUST pass the following compatibility pipeline every time:

1. Generate a working DXF from `scripts/excel_cad.py`.
2. Open the working file with `ezdxf.recover.readfile()` rather than ordinary `readfile()`.
3. Run a document audit and allow repairable issues to be fixed.
4. Force DXF version to **`AC1027` (AutoCAD 2013 DXF)**. AutoCAD 2021 can open this version reliably.
5. Save the final file as **ASCII DXF** (`fmt="asc"`). Do not return a binary DXF.
6. Re-open the exact final bytes using `ezdxf.recover.readfile()`.
7. Reject the file if the final recovery auditor still has structural errors.
8. Reject the file if modelspace is empty.
9. Reject the file if valid drawing extents cannot be calculated.
10. Reject the file if output size is suspiciously tiny/truncated.
11. Only after all checks pass may the DXF be returned to the user.

Use `scripts/run_excel_cad_safe.py` as the **default and mandatory entry point**. It automatically generates a temporary working DXF, runs `scripts/dxf_compat.py`, validates the result, and returns only the validated final DXF.

Do NOT call `scripts/excel_cad.py` alone for a user-facing final artifact unless you subsequently run `scripts/dxf_compat.py` on its output.

### Why this is mandatory

Previous failures produced DXFs that a Python library could parse but AutoCAD 2021 opened as an empty `Drawing1`, failed to load, or required abnormal recovery. Therefore compatibility validation is part of the Skill's definition of success, not an optional cleanup step.

## Deliverables

Always generate:
1. **Validated final DXF**, passed through the mandatory AutoCAD 2021 compatibility pipeline.
2. Match report TXT/CSV with zone, original code, 6-character key, quantity, matched block, brand, status.
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
- unmatched furniture contains no `MISSING` text and is represented by red code only;
- furniture remains as blocks where possible.

If any compatibility check fails, do **not** return the broken DXF. Repair/rebuild it in the same task and validate again.

## Runtime

Dependencies:
- `ezdxf`
- `openpyxl`

Default command:

```bash
python scripts/run_excel_cad_safe.py \
  --excel showroom.xlsx \
  --base base.dxf \
  --library furniture_library.dxf \
  --output showroom_zone_index.dxf \
  --report showroom_zone_index_report.csv
```
