from __future__ import annotations

import argparse
import os
from pathlib import Path

import ezdxf
from ezdxf import bbox, recover

TARGET_DXF_VERSION = "AC1027"  # AutoCAD 2013 DXF; opens in AutoCAD 2021
MIN_OUTPUT_BYTES = 1024


def validate_nonempty(doc) -> tuple[int, tuple[float, float, float, float] | None]:
    msp = doc.modelspace()
    entity_count = len(msp)
    if entity_count == 0:
        raise RuntimeError("DXF modelspace is empty; refusing to return a blank Drawing1-style file.")

    ext = bbox.extents(msp)
    if not ext.has_data:
        raise RuntimeError("DXF has no valid geometric extents; refusing to return the file.")

    minx, miny = float(ext.extmin.x), float(ext.extmin.y)
    maxx, maxy = float(ext.extmax.x), float(ext.extmax.y)
    if not all(map(lambda v: abs(v) < 1e15, (minx, miny, maxx, maxy))):
        raise RuntimeError("DXF extents are invalid or excessively large.")
    if maxx <= minx and maxy <= miny:
        raise RuntimeError("DXF extents collapsed to a point/line; refusing to return the file.")

    return entity_count, (minx, miny, maxx, maxy)


def finalize_for_autocad2021(src: Path, dst: Path) -> dict:
    if not src.exists() or src.stat().st_size < MIN_OUTPUT_BYTES:
        raise RuntimeError(f"Source DXF is missing or too small: {src}")

    # 1) Recover-read is stricter and repairs recoverable structural issues.
    doc, recovery_auditor = recover.readfile(src)
    validate_nonempty(doc)

    # 2) Force a conservative AutoCAD-compatible DXF version.
    doc.dxfversion = TARGET_DXF_VERSION

    # 3) Run an in-memory audit; ezdxf fixes repairable issues during audit.
    pre_save_auditor = doc.audit()
    if pre_save_auditor.has_errors:
        # Remaining errors are not safe to ship as a final file.
        raise RuntimeError(
            "DXF still contains unrepaired structural errors before save: "
            + "; ".join(str(e) for e in pre_save_auditor.errors[:10])
        )

    # 4) ASCII DXF is intentionally used for maximum interoperability.
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    doc.saveas(tmp, fmt="asc")

    if not tmp.exists() or tmp.stat().st_size < MIN_OUTPUT_BYTES:
        raise RuntimeError("Compatibility write produced an empty/truncated DXF.")

    # 5) Re-open the exact bytes that will be returned to the user.
    check_doc, check_auditor = recover.readfile(tmp)
    entity_count, extents = validate_nonempty(check_doc)

    if check_doc.dxfversion != TARGET_DXF_VERSION:
        raise RuntimeError(
            f"Unexpected DXF version after save: {check_doc.dxfversion}; "
            f"expected {TARGET_DXF_VERSION}"
        )
    if check_auditor.has_errors:
        raise RuntimeError(
            "Final DXF failed recovery audit: "
            + "; ".join(str(e) for e in check_auditor.errors[:10])
        )

    # 6) Make the validated file the final artifact atomically.
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, dst)

    return {
        "path": str(dst),
        "dxfversion": check_doc.dxfversion,
        "modelspace_entities": entity_count,
        "file_size": dst.stat().st_size,
        "extents": extents,
        "recovery_fixes": len(recovery_auditor.fixes),
        "final_fixes": len(check_auditor.fixes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finalize and validate a DXF for AutoCAD 2021 compatibility."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()

    output = args.output or args.input.with_name(args.input.stem + "_AutoCAD2021.dxf")
    result = finalize_for_autocad2021(args.input, output)
    print(result)


if __name__ == "__main__":
    main()
