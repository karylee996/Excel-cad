from __future__ import annotations

import argparse
import json
from pathlib import Path

from excel_cad import build
from dxf_compat import finalize_for_autocad2021
from enforce_colors import enforce_label_colors

BUILD_MARKER = "EXCEL_CAD_SAFE_BUILD_V3"


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Safe Excel-CAD pipeline: generate zone furniture index, enforce label colors, "
            "then recover/audit/rewrite/validate as AutoCAD 2021 compatible AC1027 ASCII DXF."
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
    recolored = args.output.with_name(args.output.stem + "__recolored.dxf")

    result = build(args.excel, args.base, args.library, temp, report, args.sheet)

    # First compatibility rewrite creates a stable AC1027 ASCII working file.
    compat_stage1 = finalize_for_autocad2021(temp, recolored)

    # Enforce final annotation colors on the stable DXF bytes:
    # matched furniture code = ACI 2 yellow; missing code/name = ACI 1 red; brand = ACI 7.
    color_result = enforce_label_colors(recolored, report)

    # Run the compatibility pipeline again AFTER recoloring so no later save step can alter colors.
    compat = finalize_for_autocad2021(recolored, args.output)

    validation = {
        "build_marker": BUILD_MARKER,
        "output": str(args.output),
        "report": str(report),
        "color_rules": {
            "matched_furniture_code_aci": 2,
            "missing_furniture_code_name_aci": 1,
            "brand_aci": 7,
        },
        "color_enforcement": color_result,
        "compatibility_stage1": compat_stage1,
        "compatibility": compat,
        "build": result,
        "passed": True,
    }

    validation_report.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for pth in (temp, recolored):
        try:
            pth.unlink(missing_ok=True)
        except Exception:
            pass

    print(json.dumps(validation, ensure_ascii=False))
    print(str(validation_report))


if __name__ == "__main__":
    main()
