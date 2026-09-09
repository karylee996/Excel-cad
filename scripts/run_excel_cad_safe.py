from __future__ import annotations

import argparse
import json
from pathlib import Path

from excel_cad import build
from dxf_compat import finalize_for_autocad2021

BUILD_MARKER = "EXCEL_CAD_SAFE_BUILD_V2"


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Safe Excel-CAD pipeline: generate zone furniture index, then recover/audit/"
            "rewrite/validate as AutoCAD 2021 compatible AC1027 ASCII DXF."
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

    result = build(args.excel, args.base, args.library, temp, report, args.sheet)
    compat = finalize_for_autocad2021(temp, args.output)

    validation = {
        "build_marker": BUILD_MARKER,
        "output": str(args.output),
        "report": str(report),
        "compatibility": compat,
        "build": result,
        "passed": True,
    }

    validation_report.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        temp.unlink(missing_ok=True)
    except Exception:
        pass

    print(json.dumps(validation, ensure_ascii=False))
    print(str(validation_report))


if __name__ == "__main__":
    main()
