from __future__ import annotations

import csv
from pathlib import Path

import ezdxf

MATCHED_CODE_COLOR = 2  # AutoCAD indexed yellow
MISSING_CODE_COLOR = 1  # AutoCAD indexed red
BRAND_COLOR = 7         # neutral black/white by background


def _text_value(entity) -> str:
    try:
        if entity.dxftype() == "TEXT":
            return entity.dxf.text.strip()
        if entity.dxftype() == "MTEXT":
            return entity.plain_text().strip()
    except Exception:
        return ""
    return ""


def enforce_label_colors(dxf_path: Path, report_csv: Path) -> dict:
    matched_codes: set[str] = set()
    missing_codes: set[str] = set()
    brands: set[str] = set()

    with report_csv.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("原始编码") or row.get("Excel完整编码") or row.get("编号") or "").strip()
            status = (row.get("状态") or "").strip().lower()
            brand = (row.get("品牌") or "").strip()
            if code:
                if status == "matched":
                    matched_codes.add(code)
                else:
                    missing_codes.add(code)
            if brand:
                brands.add(brand)

    doc = ezdxf.readfile(dxf_path)
    changed = {"matched_yellow": 0, "missing_red": 0, "brand_neutral": 0}

    for layout in doc.layouts:
        for e in layout:
            if e.dxftype() not in {"TEXT", "MTEXT"}:
                continue
            value = _text_value(e)
            if not value:
                continue
            if value in missing_codes:
                e.dxf.color = MISSING_CODE_COLOR
                changed["missing_red"] += 1
            elif value in matched_codes:
                e.dxf.color = MATCHED_CODE_COLOR
                changed["matched_yellow"] += 1
            elif value in brands:
                e.dxf.color = BRAND_COLOR
                changed["brand_neutral"] += 1

    doc.saveas(dxf_path, fmt="asc")
    return changed
