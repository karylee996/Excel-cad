---
name: excel-cad
description: Convert a showroom furniture Excel schedule, CAD base drawing, and CAD furniture library into a clean zone-based DXF index. Match by the first 6 characters of the normalized code, preserve full codes and brands, center code and brand text, use SimHei/黑体, keep matched furniture codes ACI 2 yellow, keep unmatched furniture codes/names ACI 1 red, place zone indexes around the base near their area numbers, create true-size rectangular placeholder blocks from Excel length/width for unmatched furniture, and ALWAYS execute the repository safe runner and validate the returned DXF for AutoCAD 2021 compatibility.
---

# Excel-CAD Showroom Furniture Index Skill

## Non-negotiable execution contract

This Skill is not just a prompt specification. The repository scripts are part of the Skill and MUST be executed.

When this Skill is invoked from a new chat:

1. Read this `SKILL.md` from `karylee996/Excel-cad`.
2. Read the actual repository files:
   - `scripts/excel_cad.py`
   - `scripts/dxf_compat.py`
   - `scripts/enforce_colors.py`
   - `scripts/run_excel_cad_safe.py`
3. Use the uploaded Excel, base DXF and furniture-library DXF as the real input files.
4. Execute **`scripts/run_excel_cad_safe.py`** as the only approved user-facing pipeline.
5. Do NOT reimplement the workflow ad hoc in a fresh temporary script unless the repository script itself cannot run and is first repaired.
6. Do NOT return the intermediate working/recolored DXFs.
7. The safe runner must produce both the final validated DXF and a `*_validation.json` manifest.
8. The validation manifest must contain `build_marker == "EXCEL_CAD_SAFE_BUILD_V3"` and `passed == true`.
9. If the validation manifest is missing, malformed, or fails any check, the DXF MUST NOT be returned as a finished file.
10. Before sharing the final artifact, confirm the final path exists and corresponds to the validated file referenced in the manifest.

## Furniture matching rule

Match by the first usable 6-character furniture key, normally `2 letters + 4 digits`.

Examples:
- `BF1182Z3` → `BF1182`
- `PF0354-5-1Z2` → `PF0354`
- `AC1234HZ` → `AC1234`

Normalize to uppercase and ignore spaces/separators while finding the key. Do not force-match short ambiguous codes such as `CY`.

## Excel parsing

Detect columns by meaning, not hard-coded letters:
- 区域 / 区域号 / 分区 / AREA / ZONE
- 编号 / 家具编号 / 产品编号 / CODE / MODEL / 型号
- 数量 / QTY / QUANTITY / 数目
- 备注 / 尺寸 / 规格 / SIZE / DIMENSION / SPEC
- optional product name: 名称 / 品名 / 产品名称 / NAME

For dimension text such as `277*109*76cm`, `64.5×35×54cm`, `295*106*74~100cm`:
- use first numeric value as plan length;
- second numeric value as plan width;
- convert cm to mm;
- if fewer than two reliable numeric dimensions are available, do not guess.

## Layout rules

- Keep the original base drawing unchanged.
- Read zone-number positions (`01`, `02`, `01区`, `02区`).
- Put each zone index outside the base drawing on the nearest top/bottom/left/right side.
- Preserve spatial order along each side.
- Expand outward to additional rows/columns when necessary.
- Keep one thin zone frame, no dense cell grids, adaptive compact sizes.
- Show one furniture graphic per summarized item/model and quantity as `×N`.

## Furniture geometry and labels

For matched items:
- copy the complete furniture block from the library;
- keep it as an editable CAD `INSERT` whenever possible;
- preserve proportions when scaling for the index;
- display the complete Excel code and detected brand at the geometric center of the displayed furniture block.

### FINAL COLOR RULES — mandatory

Use AutoCAD indexed colors, not TrueColor, for all code-status annotations:

- **Matched furniture code: ACI 2 = yellow.**
- **Unmatched / placeholder furniture code: ACI 1 = red.**
- **Unmatched product name (when Excel supplies one): ACI 1 = red.**
- Brand name: ACI 7 neutral.
- Quantity for matched furniture may remain neutral unless a project-specific rule says otherwise.
- Quantity for unmatched furniture remains red.

These colors must survive the final compatibility rewrite. Therefore the safe runner must execute `scripts/enforce_colors.py` before the final compatibility pass, and the validation manifest must record:

```json
"color_rules": {
  "matched_furniture_code_aci": 2,
  "missing_furniture_code_name_aci": 1,
  "brand_aci": 7
}
```

Do not rely on layer color or BYLAYER for the furniture code status. Set the TEXT/MTEXT entity's ACI color explicitly so AutoCAD 2021 displays matched codes as yellow.

## Font

All returned text uses:
- style: `HEITI`
- font: `simhei.ttf`

## Unmatched furniture dimension placeholders

If an item cannot be matched, inspect Excel remark/size/specification.

When valid length + width are available:
- create an editable true-size rectangular placeholder block in millimetres;
- center the true-size block on its origin;
- keep placeholder geometry black/neutral;
- index instance may be uniformly scaled down for display;
- keep code and product name red and centered on the placeholder;
- quantity remains red when applicable.

When dimensions are unavailable/unreliable:
- do not invent a rectangle;
- keep only red code/name in the correct zone;
- never write `MISSING`.

## AutoCAD 2021 compatibility pipeline

A DXF must never be returned merely because `ezdxf.readfile()` can reopen it.

The final returned DXF MUST:
1. be generated through the repository safe runner;
2. be recovery-read and audited;
3. be written as AC1027 AutoCAD 2013 ASCII DXF;
4. have colors enforced after the first stable compatibility rewrite;
5. pass the compatibility finalizer again after color enforcement;
6. be recovery-read again with no structural errors;
7. have non-empty modelspace, valid extents, and non-trivial file size;
8. produce a validation JSON with `EXCEL_CAD_SAFE_BUILD_V3`.

## Deliverables

Always generate:
1. validated final DXF;
2. match report CSV/TXT;
3. validation JSON from the safe runner;
4. preview PNG when possible.

## Final quality checks

Before returning any DXF:
- actual repository safe runner executed;
- validation manifest contains `build_marker == EXCEL_CAD_SAFE_BUILD_V3` and `passed == true`;
- final DXF is AC1027 ASCII and passes recovery audit;
- modelspace entity count > 0 and extents valid;
- original base drawing is present;
- zone panels are near corresponding zones and do not overlap excessively;
- generated text uses HEITI / simhei.ttf;
- matched furniture codes are explicitly ACI 2 yellow;
- unmatched code/name are explicitly ACI 1 red;
- brand names are neutral ACI 7;
- no `MISSING` text exists;
- unmatched items with reliable dimensions use true-size rectangle block definitions;
- furniture remains blocks where possible.

If any execution, color, or compatibility check fails, do not return the DXF as finished.