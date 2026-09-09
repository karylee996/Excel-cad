---
name: excel-cad
description: Convert a showroom furniture Excel schedule, a CAD base drawing, and a CAD furniture library into a clean DXF furniture index grouped by zone. Match furniture by the first 6 characters of the normalized model code, preserve full Excel codes and detected brand names, center code and brand text on each furniture block, use SimHei/黑体 for all returned text, place zone indexes around the base drawing near their corresponding area numbers, and show unmatched furniture as red codes only. Use for showroom restoration, furniture schedule to CAD, Excel-to-DXF furniture indexing, zone-based CAD furniture summaries, or furniture-library matching workflows.
---

# Excel-CAD Showroom Furniture Index Skill

## Purpose

Convert an Excel furniture schedule + showroom base DXF + furniture-library DXF into a clean CAD furniture index for showroom restoration work.

The final drawing is optimized for the next manual step: quickly finding a zone's furniture and dragging / arranging it into the real showroom area.

## Required inputs

1. Excel schedule (`.xlsx`): zone / furniture code / quantity. Multiple repeated `区域 / 编号 / 数量` column groups are allowed.
2. Base drawing (`.dxf`): preserve all original geometry and locations.
3. Furniture library (`.dxf`): furniture preferably stored as `INSERT` blocks; model code may be in block name or attributes; brand may be an attribute or nearby text.

## Matching rule

Match by the first usable **6-character furniture key**, normally `2 letters + 4 digits`.

Examples:
- `BF1182Z3` → `BF1182`
- `PF0354-5-1Z2` → `PF0354`
- `AC1234HZ` → `AC1234`

Normalize to uppercase and ignore spaces / separators while finding the key. Do not force-match short ambiguous codes such as `CY`.

## Final layout rules

### 1. Keep the base drawing unchanged

Do not place the index furniture directly inside the real showroom zones. Do not move, scale, explode, or delete the original floor plan.

### 2. Put each zone index near its real zone

Read the actual zone-number text positions (`01`, `02`, ... or `01区`, `02区`, ... ) from the base drawing.

For each zone:
1. Find its zone-number coordinate.
2. Determine which base-drawing boundary is nearest: top / bottom / left / right.
3. Place that zone's furniture index **outside the base drawing on that nearest side**.
4. Preserve the spatial order of zone numbers along each side.
5. Avoid overlap by packing panels in the nearest row/column first; if necessary, expand outward into a second/third row rather than moving a zone far away laterally.

Goal: the zone index should visually correspond to the real zone so the user can quickly move furniture into the plan.

If zone-number coordinates cannot be detected reliably, fall back to a compact perimeter layout around the base drawing. Do not default to one very long stack on the right.

### 3. Clean and minimal workspace

The workspace must remain visually quiet and easy to scan.

- One thin frame per zone is enough.
- Do not draw dense cell grids unless needed.
- Use compact adaptive zone-frame sizes based on item count.
- Keep consistent furniture thumbnail scale and spacing.
- Prefer the smallest layout that remains readable.
- Zone frames with few items should remain small.

### 4. One graphic per furniture record / model

Within a zone, show each summarized furniture item once. Do not draw repeated copies just because quantity > 1. Show quantity as `×N`.

### 5. Preserve furniture geometry

For matched items:
- Copy the complete furniture block from the library.
- Keep it as an editable CAD `INSERT` block whenever possible.
- Do not explode linework unless there is no alternative.
- Scale uniformly to fit the index cell while preserving proportions.

### 6. Furniture code + brand at block center

For every matched item:
- Display the **complete original Excel furniture code**.
- Display the detected **brand name** when available.
- Put both code and brand at the **geometric center of the displayed furniture block**.
- Stack them vertically around the center.
- Keep all text editable.

### 7. All text in 黑体 / SimHei

Use a CAD text style:
- style: `HEITI`
- font: `simhei.ttf`

Apply it to zone titles, furniture codes, brand names, quantities, red missing codes, and all newly generated annotation text. When practical, convert returned TEXT/MTEXT/ATTRIB entities to the same style.

### 8. Missing furniture: red code only

If a furniture item cannot be matched by the 6-character rule:
- do not substitute another model;
- keep it in the correct zone index;
- show the **furniture code itself in red**;
- **do not write `MISSING`**;
- if quantity > 1, retain a small red `×N` near/below the red code.

The red code alone is the missing indicator.

## Brand detection

Priority:
1. block attributes;
2. nearby `TEXT` / `MTEXT` around the source furniture block;
3. preserve original spelling such as `Minotti`, `B&B`, `ARFLEX`.

Exclude model codes, dimensions, quantities, and generic labels from brand candidates.

## Excel parsing

Detect columns by header meaning, not fixed column letters:
- 区域 / 区域号 / 分区 / AREA / ZONE
- 编号 / 家具编号 / 产品编号 / CODE / MODEL / 型号
- 数量 / QTY / QUANTITY / 数目

Normalize numeric zones to `01区`, `02区`, etc.

## Deliverables

Always generate:
1. Final DXF.
2. Match report TXT/CSV containing zone, original code, 6-character key, quantity, matched block, brand, and status.
3. Preview PNG when DXF rendering is available.

## Quality checks

Before returning:
- Re-open the generated DXF with `ezdxf`.
- Confirm the original base drawing remains unchanged.
- Confirm all zone indexes are outside / around the base and spatially near the corresponding zone numbers when detectable.
- Confirm zone panels do not overlap.
- Confirm the drawing is compact and has no unnecessary dense grid lines.
- Confirm full Excel code + brand are centered on matched furniture graphics.
- Confirm all generated text uses `HEITI` / `simhei.ttf`.
- Confirm unmatched furniture contains **no `MISSING` text** and is represented by red code only.
- Confirm furniture remains as blocks where possible.

## Runtime

Recommended Python dependencies:
- `ezdxf`
- `openpyxl`

Use `scripts/excel_cad.py` as the reference implementation.
