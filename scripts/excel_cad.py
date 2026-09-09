from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from openpyxl import load_workbook


HEITI_STYLE = "HEITI"
HEITI_FONT = "simhei.ttf"
MISSING_COLOR = 1  # AutoCAD red
TEXT_COLOR = 7     # black/white by background; typically black on light canvas
FRAME_COLOR = 8

ZONE_HEADERS = {"区域", "区域号", "分区", "area", "zone"}
CODE_HEADERS = {"编号", "家具编号", "产品编号", "code", "model", "型号"}
QTY_HEADERS = {"数量", "qty", "quantity", "数目"}

CODE_RE = re.compile(r"([A-Z]{2}\d{4})")


@dataclass
class ScheduleItem:
    zone: str
    code: str
    qty: int

    @property
    def key(self) -> Optional[str]:
        return match_key(self.code)


@dataclass
class LibraryItem:
    block_name: str
    key: str
    brand: str = ""


@dataclass
class MatchResult:
    zone: str
    code: str
    key: str
    qty: int
    matched_block: str = ""
    brand: str = ""
    status: str = "missing"


def norm_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def norm_header(value) -> str:
    return norm_text(value).lower().replace(" ", "")


def normalize_code(code: str) -> str:
    code = norm_text(code).upper()
    return re.sub(r"[^A-Z0-9]", "", code)


def match_key(code: str) -> Optional[str]:
    normalized = normalize_code(code)
    m = CODE_RE.search(normalized)
    if m:
        return m.group(1)
    if len(normalized) >= 6:
        candidate = normalized[:6]
        if any(ch.isdigit() for ch in candidate) and any(ch.isalpha() for ch in candidate):
            return candidate
    return None


def normalize_zone(value) -> str:
    s = norm_text(value)
    if not s:
        return ""
    m = re.search(r"(\d+)", s)
    if m:
        return f"{int(m.group(1)):02d}区"
    return s if s.endswith("区") else f"{s}区"


def safe_int(value, default=1) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return max(1, int(float(value)))
    except Exception:
        return default


def detect_column_groups(ws) -> list[tuple[int, int, int]]:
    """Detect repeated 区域/编号/数量 groups from the first rows."""
    groups: list[tuple[int, int, int]] = []
    max_scan_rows = min(ws.max_row, 12)
    for row in range(1, max_scan_rows + 1):
        headers = {col: norm_header(ws.cell(row, col).value) for col in range(1, ws.max_column + 1)}
        zone_cols = [c for c, h in headers.items() if h in ZONE_HEADERS]
        for zc in zone_cols:
            # Search to the right, bounded to avoid pairing with another group.
            cc = qc = None
            for c in range(zc + 1, min(ws.max_column, zc + 6) + 1):
                h = headers[c]
                if cc is None and h in CODE_HEADERS:
                    cc = c
                elif qc is None and h in QTY_HEADERS:
                    qc = c
            if cc and qc:
                tup = (zc, cc, qc)
                if tup not in groups:
                    groups.append(tup)
        if groups:
            return groups
    return groups


def parse_excel(path: Path, sheet_name: Optional[str] = None) -> list[ScheduleItem]:
    wb = load_workbook(path, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active
    groups = detect_column_groups(ws)
    if not groups:
        raise ValueError("未识别到 Excel 中的 区域/编号/数量 列组。")

    items: list[ScheduleItem] = []
    for zc, cc, qc in groups:
        started = False
        current_zone = ""
        for row in range(1, ws.max_row + 1):
            zval = norm_text(ws.cell(row, zc).value)
            cval = norm_text(ws.cell(row, cc).value)
            qval = ws.cell(row, qc).value

            if norm_header(zval) in ZONE_HEADERS or norm_header(cval) in CODE_HEADERS:
                started = True
                continue
            if not started:
                continue
            if zval:
                current_zone = normalize_zone(zval)
            if not cval:
                continue
            if norm_header(cval) in CODE_HEADERS:
                continue
            zone = normalize_zone(zval) if zval else current_zone
            if not zone:
                continue
            items.append(ScheduleItem(zone=zone, code=cval, qty=safe_int(qval)))
    return items


def entity_text(e) -> str:
    try:
        if e.dxftype() == "TEXT":
            return e.dxf.text.strip()
        if e.dxftype() == "MTEXT":
            return e.plain_text().strip()
        if e.dxftype() == "ATTRIB":
            return e.dxf.text.strip()
    except Exception:
        pass
    return ""


def block_insert_bbox(doc, insert):
    try:
        ext = bbox.extents([insert], fast=True)
        if ext.has_data:
            return ext.extmin, ext.extmax
    except Exception:
        pass
    p = insert.dxf.insert
    return p, p


def text_point(e):
    try:
        if e.dxftype() == "TEXT":
            return e.dxf.insert
        if e.dxftype() == "MTEXT":
            return e.dxf.insert
    except Exception:
        pass
    return None


def looks_like_brand(text: str, furniture_key: str) -> bool:
    t = text.strip()
    if not t or len(t) > 40:
        return False
    if furniture_key and furniture_key in normalize_code(t):
        return False
    if match_key(t):
        return False
    if re.fullmatch(r"[\d\s×xX*.+\-/]+", t):
        return False
    low = t.lower()
    if low in {"missing", "brand", "code", "model", "qty", "quantity"}:
        return False
    # Brand labels normally contain alphabetic characters.
    return any(ch.isalpha() for ch in t)


def detect_brand(doc, insert, key: str, radius_factor: float = 2.0) -> str:
    # 1) block attributes
    try:
        for attrib in insert.attribs:
            t = attrib.dxf.text.strip()
            if looks_like_brand(t, key):
                return t
    except Exception:
        pass

    # 2) nearby modelspace TEXT/MTEXT
    p = insert.dxf.insert
    candidates: list[tuple[float, str]] = []
    try:
        mn, mx = block_insert_bbox(doc, insert)
        diag = math.hypot(mx.x - mn.x, mx.y - mn.y)
    except Exception:
        diag = 1000.0
    radius = max(500.0, diag * radius_factor)
    for e in doc.modelspace():
        if e.dxftype() not in {"TEXT", "MTEXT"}:
            continue
        tp = text_point(e)
        if tp is None:
            continue
        d = math.hypot(tp.x - p.x, tp.y - p.y)
        if d <= radius:
            t = entity_text(e)
            if looks_like_brand(t, key):
                candidates.append((d, t))
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1] if candidates else ""


def scan_library(doc) -> dict[str, LibraryItem]:
    found: dict[str, LibraryItem] = {}
    for ins in doc.modelspace().query("INSERT"):
        name = ins.dxf.name
        key = match_key(name)
        if not key:
            # attributes can contain model code
            try:
                for a in ins.attribs:
                    key = match_key(a.dxf.text)
                    if key:
                        break
            except Exception:
                pass
        if not key:
            continue
        if key not in found:
            found[key] = LibraryItem(block_name=name, key=key, brand=detect_brand(doc, ins, key))
    return found


def ensure_heiti(doc):
    if HEITI_STYLE not in doc.styles:
        style = doc.styles.new(HEITI_STYLE)
    else:
        style = doc.styles.get(HEITI_STYLE)
    try:
        style.dxf.font = HEITI_FONT
    except Exception:
        pass


def force_text_style(doc):
    ensure_heiti(doc)
    for e in doc.modelspace():
        if e.dxftype() in {"TEXT", "MTEXT", "ATTRIB"}:
            try:
                e.dxf.style = HEITI_STYLE
            except Exception:
                pass


def extents_xy(doc):
    ext = bbox.extents(doc.modelspace(), fast=True)
    if not ext.has_data:
        return (0.0, 0.0, 10000.0, 10000.0)
    return (ext.extmin.x, ext.extmin.y, ext.extmax.x, ext.extmax.y)


def add_centered_text(msp, text: str, x: float, y: float, height: float, color=TEXT_COLOR):
    t = msp.add_text(text, dxfattribs={"height": height, "style": HEITI_STYLE, "color": color})
    try:
        t.set_placement((x, y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    except Exception:
        t.dxf.insert = (x, y)
    return t


def copy_source_block_definition(source_doc, target_doc, block_name: str):
    if block_name in target_doc.blocks:
        return
    importer = Importer(source_doc, target_doc)
    importer.import_block(block_name, rename=False)
    importer.finalize()


def find_library_insert_by_block(lib_doc, block_name: str):
    for ins in lib_doc.modelspace().query("INSERT"):
        if ins.dxf.name == block_name:
            return ins
    return None


def source_block_size(lib_doc, source_insert) -> tuple[float, float, tuple[float, float]]:
    try:
        mn, mx = block_insert_bbox(lib_doc, source_insert)
        w = max(1.0, mx.x - mn.x)
        h = max(1.0, mx.y - mn.y)
        center = ((mn.x + mx.x) / 2.0, (mn.y + mx.y) / 2.0)
        return w, h, center
    except Exception:
        p = source_insert.dxf.insert
        return 1000.0, 1000.0, (p.x, p.y)


def aggregate_schedule(items: Iterable[ScheduleItem]) -> dict[str, list[ScheduleItem]]:
    grouped: dict[tuple[str, str], int] = defaultdict(int)
    display_code: dict[tuple[str, str], str] = {}
    for item in items:
        normalized = normalize_code(item.code) or item.code.upper()
        k = (item.zone, normalized)
        grouped[k] += item.qty
        display_code[k] = item.code
    zones: dict[str, list[ScheduleItem]] = defaultdict(list)
    for (zone, _), qty in grouped.items():
        code = display_code[(zone, _)]
        zones[zone].append(ScheduleItem(zone, code, qty))
    for z in zones:
        zones[z].sort(key=lambda i: (i.key or "ZZZZZZ", normalize_code(i.code)))
    return zones


def zone_sort_key(zone: str):
    m = re.search(r"\d+", zone)
    return (int(m.group()) if m else 999999, zone)


def build_index(base_doc, lib_doc, schedule: list[ScheduleItem], output: Path, report: Path,
                columns: int = 4, cell_w: float = 4500.0, cell_h: float = 3500.0,
                zone_gap: float = 1200.0, margin: float = 3000.0):
    ensure_heiti(base_doc)
    lib_index = scan_library(lib_doc)
    msp = base_doc.modelspace()
    zones = aggregate_schedule(schedule)

    minx, miny, maxx, maxy = extents_xy(base_doc)
    start_x = maxx + margin
    cursor_y = maxy

    report_rows: list[MatchResult] = []

    for zone in sorted(zones, key=zone_sort_key):
        entries = zones[zone]
        rows = max(1, math.ceil(len(entries) / columns))
        title_h = 900.0
        frame_w = columns * cell_w
        frame_h = title_h + rows * cell_h
        zone_top = cursor_y
        zone_bottom = zone_top - frame_h

        # frame
        msp.add_lwpolyline([
            (start_x, zone_top),
            (start_x + frame_w, zone_top),
            (start_x + frame_w, zone_bottom),
            (start_x, zone_bottom),
            (start_x, zone_top),
        ], dxfattribs={"color": FRAME_COLOR})
        add_centered_text(msp, zone, start_x + frame_w / 2, zone_top - title_h / 2, 450.0)

        for idx, item in enumerate(entries):
            row, col = divmod(idx, columns)
            cx = start_x + col * cell_w + cell_w / 2
            cy = zone_top - title_h - row * cell_h - cell_h / 2
            key = item.key or ""
            lib_item = lib_index.get(key) if key else None

            if lib_item:
                source_insert = find_library_insert_by_block(lib_doc, lib_item.block_name)
                if source_insert is not None:
                    copy_source_block_definition(lib_doc, base_doc, lib_item.block_name)
                    sw, sh, _ = source_block_size(lib_doc, source_insert)
                    target_w = cell_w * 0.72
                    target_h = cell_h * 0.62
                    scale = min(target_w / sw, target_h / sh)
                    scale = max(scale, 0.0001)

                    new_ins = msp.add_blockref(
                        lib_item.block_name,
                        (cx, cy),
                        dxfattribs={
                            "xscale": source_insert.dxf.xscale * scale,
                            "yscale": source_insert.dxf.yscale * scale,
                            "zscale": source_insert.dxf.zscale * scale,
                            "rotation": source_insert.dxf.rotation,
                        },
                    )

                    # Code and brand are deliberately centered on the displayed block.
                    text_h = min(330.0, cell_h * 0.09)
                    add_centered_text(msp, item.code, cx, cy + text_h * 0.65, text_h)
                    if lib_item.brand:
                        add_centered_text(msp, lib_item.brand, cx, cy - text_h * 0.65, text_h * 0.9)
                    add_centered_text(msp, f"×{item.qty}", cx + cell_w * 0.36, cy - cell_h * 0.38, text_h * 0.9)

                    report_rows.append(MatchResult(zone, item.code, key, item.qty,
                                                   lib_item.block_name, lib_item.brand, "matched"))
                    continue

            # Missing / ambiguous
            status = "ambiguous" if not key else "missing"
            msg = f"MISSING  {item.code}  ×{item.qty}"
            add_centered_text(msp, msg, cx, cy, min(340.0, cell_h * 0.1), color=MISSING_COLOR)
            report_rows.append(MatchResult(zone, item.code, key, item.qty, status=status))

        cursor_y = zone_bottom - zone_gap

    force_text_style(base_doc)
    base_doc.saveas(output)

    with report.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["区域", "Excel完整编号", "前6位匹配键", "数量", "家具库块名", "品牌", "状态"])
        for r in report_rows:
            writer.writerow([r.zone, r.code, r.key, r.qty, r.matched_block, r.brand, r.status])

    # Structural validation
    check = ezdxf.readfile(output)
    if HEITI_STYLE not in check.styles:
        raise RuntimeError("输出验证失败：HEITI 文字样式不存在。")
    return report_rows


def main():
    parser = argparse.ArgumentParser(description="Excel 家具清单 + CAD 底图 + 家具库 -> 按分区归纳家具索引 DXF")
    parser.add_argument("--excel", required=True, type=Path)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--sheet", default=None)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--cell-width", type=float, default=4500.0)
    parser.add_argument("--cell-height", type=float, default=3500.0)
    parser.add_argument("--zone-gap", type=float, default=1200.0)
    parser.add_argument("--margin", type=float, default=3000.0)
    args = parser.parse_args()

    schedule = parse_excel(args.excel, args.sheet)
    if not schedule:
        raise SystemExit("Excel 中没有读取到有效家具记录。")

    base_doc = ezdxf.readfile(args.base)
    lib_doc = ezdxf.readfile(args.library)
    rows = build_index(
        base_doc, lib_doc, schedule, args.output, args.report,
        columns=max(1, args.columns), cell_w=args.cell_width, cell_h=args.cell_height,
        zone_gap=args.zone_gap, margin=args.margin,
    )

    matched = sum(1 for r in rows if r.status == "matched")
    missing = sum(1 for r in rows if r.status != "matched")
    print(f"完成：{args.output}")
    print(f"匹配型号：{matched}；缺失/歧义型号：{missing}")
    print(f"报告：{args.report}")


if __name__ == "__main__":
    main()
