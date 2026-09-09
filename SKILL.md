---
name: excel-cad
description: Convert a showroom furniture Excel schedule, a CAD base drawing, and a CAD furniture library into a clean DXF furniture index grouped by zone. Match furniture by the first 6 characters of the normalized model code, preserve full Excel codes and detected brand names, center code and brand text on each furniture block, use SimHei/黑体 for all returned text, and mark unmatched furniture in red. Use for showroom restoration, furniture schedule to CAD, Excel-to-DXF furniture indexing, zone-based CAD furniture summaries, or furniture-library matching workflows.
---

# Excel-CAD Showroom Furniture Index Skill

## Purpose

Convert an Excel furniture schedule plus a CAD base drawing and a CAD furniture library into a clean showroom furniture index drawing.

This Skill is designed for showroom restoration / display design workflows where furniture must be grouped by showroom zone rather than placed directly over the floor plan.

## Required Inputs

1. **Excel schedule** (`.xlsx`)
   - Contains zone/area number, furniture code, and quantity.
   - The sheet may contain more than one repeated group of columns such as `区域 / 编号 / 数量`.

2. **Base drawing** (`.dxf`)
   - Existing showroom floor plan.
   - Must be preserved without moving or altering its geometry.

3. **Furniture library** (`.dxf`)
   - Furniture is preferably stored as `INSERT` blocks.
   - Block names or nearby text contain the furniture model code.
   - Nearby text may contain the brand name.

## Final Matching Rule

### Furniture code matching

Use only the **first 6 characters of the normalized furniture code** for matching.

Examples:
- `BF1182Z3` → `BF1182`
- `PF0354-5-1Z2` → `PF0354`
- `AC1234HZ` → `AC1234`

Normalization:
- Convert to uppercase.
- Remove spaces and separators when determining the 6-character key.
- Prefer the common pattern `2 letters + 4 digits` when present.
- Do not force-match short ambiguous codes such as `CY`.

## Output Layout Rules

### 1. Do NOT place furniture inside the actual showroom zones

Keep the original base drawing unchanged.

Place the generated furniture index in a large blank area outside / beside the base drawing.

### 2. Group by zone

Create a separate framed group for every zone, for example:
- 01区
- 02区
- 03区
- ...

Each zone is an independent furniture index block.

### 3. One graphic per furniture model

Within each zone:
- Display each furniture model only once.
- Do not duplicate the same plan block just because quantity > 1.
- Show quantity as `×N`.

### 4. Preserve furniture geometry

When matched:
- Copy the complete furniture `INSERT` block from the furniture library.
- Keep it editable as a CAD block whenever possible.
- Do not explode furniture into linework unless absolutely necessary.

### 5. Furniture code and brand placement

For every matched furniture item:
- Show the **complete furniture code from Excel**, not only the 6-character matching key.
- Show the corresponding **brand name from the furniture library** when available.
- Place **both the furniture code and brand name at the geometric center of the displayed furniture block**.
- Stack code and brand vertically around the center so they stay visually associated with the block.
- Keep the text editable.

### 6. Font

All returned text must use **黑体 / SimHei**.

Create / use a CAD text style such as:
- Style name: `HEITI`
- Font: `simhei.ttf`

Apply it to:
- Zone titles
- Furniture codes
- Brand names
- Quantities
- Missing-item labels
- Any newly generated annotation text

If practical, convert existing TEXT/MTEXT in the returned drawing to the same HEITI text style as well.

### 7. Missing furniture

If a furniture code cannot be matched by the first-6-character rule:
- Do not substitute a visually similar item.
- List it in its correct zone.
- Display the missing furniture code in **red**.
- Add a clear marker such as `MISSING`.
- Include quantity.

Recommended format:
`MISSING  BF1234Z2  ×2`

### 8. Clean layout

The index must be easy to read and should not look crowded.

Recommended behavior:
- Auto-calculate blank space to the right or below the existing base drawing.
- Use consistent zone frames.
- Use a grid within each zone.
- Scale furniture graphics to fit a consistent cell size while preserving aspect ratio.
- Keep reasonable white space between items.
- Allow zone frame height to adapt to item count so zones with few items do not waste excessive space.

## Brand Detection

Brand names may exist as nearby `TEXT`/`MTEXT` entities rather than block attributes.

When extracting brand data from the furniture library:
1. Prefer explicit block attributes if present.
2. Otherwise inspect nearby text around the source furniture block.
3. Exclude text that is clearly the furniture code itself, dimensions, quantities, or generic labels.
4. Preserve the original brand spelling, e.g. `Minotti`, `B&B`, `ARFLEX`.

## Excel Parsing

The parser must support sheets that contain multiple repeated column groups.

Detect columns by header meaning rather than fixed column letters whenever possible:
- 区域 / 区域号 / 分区 / AREA / ZONE
- 编号 / 家具编号 / 产品编号 / CODE / MODEL
- 数量 / QTY / QUANTITY

Normalize zone values to a sortable display form such as `01区`, `02区`, etc.

## Deliverables

Always generate:

1. **Final DXF**
   - Base drawing preserved.
   - Furniture grouped by zone in blank space.
   - Complete furniture codes retained.
   - Brand names retained when available.
   - Code + brand centered on furniture graphic.
   - All text in SimHei/黑体.
   - Missing models marked red.

2. **Match report TXT or CSV**
   - Zone
   - Original Excel code
   - 6-character match key
   - Quantity
   - Matched library block/code
   - Brand
   - Status: matched / missing / ambiguous

3. Optional preview image if the environment can render DXF.

## Quality Checks Before Returning

Before returning the final drawing:
- Re-open the generated DXF with `ezdxf` to verify that it is structurally readable.
- Confirm all expected zones are present.
- Confirm matched items use the correct first-6-character key.
- Confirm missing items are red.
- Confirm furniture code + brand are positioned at the center of their furniture graphic.
- Confirm all generated text entities use the `HEITI` style.
- Confirm furniture geometry remains as blocks where possible.
- Confirm the original base drawing was not unintentionally moved, deleted, exploded, or scaled.

## Recommended Runtime

Use Python with:
- `ezdxf`
- `openpyxl`

Run the included script from `scripts/excel_cad.py` and adjust its layout parameters only when the specific drawing requires it.
