from __future__ import annotations

import argparse
import re
from pathlib import Path

import ezdxf
from ezdxf import bbox

# Placeholder blocks created by this Skill are named like:
# UNMATCHED_PF1926Z3_2500x920
# The final two numbers are the true plan length/width in millimetres.
PLACEHOLDER_RE = re.compile(
    r"^UNMATCHED_(?P<code>.+?)_(?P<length>\d+(?:\.\d+)?)x(?P<width>\d+(?:\.\d+)?)$",
    re.IGNORECASE,
)


def enforce_true_size_placeholder_instances(path: Path) -> dict:
    """Force all generated dimension-placeholder INSERT instances to 1:1 scale.

    A placeholder block definition is already created at its real millimetre size.
    Therefore its modelspace INSERT must remain xscale=yscale=zscale=1.0.
    Shrinking a large placeholder just to fit a compact index cell makes the CAD
    graphic visually lie about the furniture size and is forbidden.
    """
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    changed = []
    checked = 0
    mismatches = []

    for ins in msp.query("INSERT"):
        name = ins.dxf.name
        match = PLACEHOLDER_RE.match(name)
        if not match:
            continue

        checked += 1
        expected_length = float(match.group("length"))
        expected_width = float(match.group("width"))

        # Confirm the block definition itself still has true-size extents.
        try:
            block = doc.blocks.get(name)
            ext = bbox.extents(block)
            actual_length = float(ext.size.x)
            actual_width = float(ext.size.y)
            tol = 1e-6
            if abs(actual_length - expected_length) > tol or abs(actual_width - expected_width) > tol:
                mismatches.append(
                    {
                        "block": name,
                        "expected_mm": [expected_length, expected_width],
                        "actual_block_extents_mm": [actual_length, actual_width],
                    }
                )
                continue
        except Exception as exc:
            mismatches.append({"block": name, "error": str(exc)})
            continue

        old = [
            float(getattr(ins.dxf, "xscale", 1.0) or 1.0),
            float(getattr(ins.dxf, "yscale", 1.0) or 1.0),
            float(getattr(ins.dxf, "zscale", 1.0) or 1.0),
        ]
        if any(abs(v - 1.0) > 1e-9 for v in old):
            ins.dxf.xscale = 1.0
            ins.dxf.yscale = 1.0
            ins.dxf.zscale = 1.0
            changed.append(
                {
                    "block": name,
                    "code": match.group("code"),
                    "true_size_mm": [expected_length, expected_width],
                    "old_scale": old,
                    "new_scale": [1.0, 1.0, 1.0],
                }
            )

    if mismatches:
        raise RuntimeError(
            "Dimension placeholder block definitions are not true-size; refusing to continue: "
            + repr(mismatches[:10])
        )

    doc.saveas(path, fmt="asc")

    return {
        "checked_placeholders": checked,
        "changed_placeholders": len(changed),
        "rule": "dimension_placeholder_insert_scale_must_equal_1_1",
        "changes": changed,
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Force Excel-CAD generated dimension-placeholder INSERTs to true 1:1 scale."
    )
    p.add_argument("dxf", type=Path)
    args = p.parse_args()
    print(enforce_true_size_placeholder_instances(args.dxf))


if __name__ == "__main__":
    main()
