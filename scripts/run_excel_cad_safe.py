from __future__ import annotations

import argparse
import json
from pathlib import Path

from excel_cad import build
from dxf_compat import finalize_for_autocad2021
from enforce_colors import enforce_label_colors
from enforce_placeholder_scale import enforce_true_size_placeholder_instances

BUILD_MARKER = "EXCEL_CAD_SAFE_BUILD_V4"


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Safe Excel-CAD pipeline: generate zone furniture index, force dimension-placeholder "
            "instances to true 1:1 scale, enforce label colors, then recover/audit/rewrite/validate "
            "as AutoCAD 2021 compatible AC1027 ASCII DXF."
        )
    )
    p.add_argument("--excel", required=True, type=Path)
    p.add_argument("--base", required=True, type=Path)
    p.add_argument("--library", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--report", type=Path)
    p.add_argument("--validation-report", type=Path)
    p.add_argument("--sheet")
    args = p.parse_args()

    report = args.report or args.output.with_name(args.output.stem + "_match_report.csv")
    validation_report = args.validation_report or args.output.with_name(args.output.stem + "_validation.json")
    temp = args.output.with_name(args.output.stem + "__working.dxf")
    scaled = args.output.with_name(args.output.stem + "__scaled.dxf")
    recolored = args.output.with_name(args.output.stem + "__recolored.dxf")

    result = build(args.excel, args.base, args.library, temp, report, args.sheet)

    # First compatibility rewrite creates a stable AC1027 ASCII working file.
    compat_stage1 = finalize_for_autocad2021(temp, scaled)

    # CRITICAL size rule:
    # generated unmatched dimension-placeholder blocks are true-size millimetre blocks,
    # and their displayed modelspace instances must also remain 1:1. Large furniture
    # must never be shrunk merely to fit a compact zone-index cell.
    placeholder_scale_result = enforce_true_size_placeholder_instances(scaled)

    # Stabilize again after scale enforcement before recoloring.
    compat_stage2 = finalize_for_autocad2021(scaled, recolored)

    # Enforce final annotation colors on stable DXF bytes:
    # matched furniture code = ACI 2 yellow; missing code/name = ACI 1 red; brand = ACI 7.
    color_result = enforce_label_colors(recolored, report)

    # Run compatibility pipeline again AFTER recoloring so no later save step can alter colors.
    compat = finalize_for_autocad2021(recolored, args.output)

    validation = {
        "build_marker": BUILD_MARKER,
        "output": str(args.output),
        "report": str(report),
        "placeholder_scale_rules": {
            "dimension_placeholder_insert_scale": 1.0,
            "large_placeholders_may_not_be_shrunk_for_layout": True,
        },
        "placeholder_scale_enforcement": placeholder_scale_result,
        "color_rules": {
            "matched_furniture_code_aci": 2,
            "missing_furniture_code_name_aci": 1,
            "brand_aci": 7,
        },
        "color_enforcement": color_result,
        "compatibility_stage1": compat_stage1,
        "compatibility_stage2": compat_stage2,
        "compatibility": compat,
        "build": result,
        "passed": True,
    }

    validation_report.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for pth in (temp, scaled, recolored):
        try:
            pth.unlink(missing_ok=True)
        except Exception:
            pass

    print(json.dumps(validation, ensure_ascii=False))
    print(str(validation_report))


if __name__ == "__main__":
    main()
