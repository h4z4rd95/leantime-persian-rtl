#!/usr/bin/env python3
"""Regression check: the RTL legacy-grid gutter must NOT be flipped.

The shipped Leantime 3.10.0 grid is single-sided (`.row{margin-left:-20px}`,
`margin-left:-30px` under `@media (min-width:1200px)`) and direction-neutral:
with an auto-width block the row's right edge stays flush with the container's
content box in both LTR and RTL. Mirroring the gutter to the right side
(`margin-left:0; margin-right:-20/-30px`) makes rows wider than their
container and anchored left, pushing rows and columns 15-50px past the right
viewport edge (clipped right-side controls; verified 2026-10-21 on
/setting/editCompanySettings and the public login page).

This check fails if any RTL-scoped rule re-introduces a negative right margin
on .row/.row-fluid/.thumbnails, or if the shipped-geometry pin is missing.

Usage:
  python scripts/check_rtl_row_gutter.py [css_file ...]

Exit codes: 0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILES = [
    ROOT / "css" / "shared-rtl-foundation.css",
    ROOT / "css" / "custom-premium.min.css",
]

GRID_CLASSES = (".row", ".row-fluid", ".thumbnails")


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")

    # Any RTL-scoped rule that sets a negative margin-right on a grid class.
    # Matches rules like `html[dir="rtl"] .row{...margin-right:-20px...}`.
    for m in re.finditer(r"([^\n{}]*\[dir[=\"']?rtl[=\"']?\][^\n{}]*)\{([^{}]*)\}", text):
        selector, body = m.group(1), m.group(2)
        if not any(cls in selector for cls in GRID_CLASSES):
            continue
        for prop in re.finditer(r"margin-right\s*:\s*(-?\d+px)", body):
            if prop.group(1).lstrip("-").isdigit() and prop.group(1).startswith("-"):
                problems.append(
                    f"{path.name}: RTL grid rule flips gutter to the right: "
                    f"`{selector.strip()} {{ ... margin-right:{prop.group(1)} ... }}`"
                )

    # The shipped-geometry pin must exist for .row (margin-left:-20px scoped to RTL).
    row_pin = re.search(
        r'html\[dir="rtl"\][^{}]*\.row[^{}]*\{[^{}]*margin-left:\s*-20px', text
    )
    if not row_pin:
        problems.append(
            f"{path.name}: missing RTL `.row` shipped-geometry pin "
            "(expected `html[dir=\"rtl\"] .row { margin-left:-20px ... }`)"
        )
    return problems


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv] or DEFAULT_FILES
    all_problems: list[str] = []
    for p in files:
        if not p.exists():
            print(f"FAIL {p}: file not found")
            return 1
        all_problems += check_file(p)
    for prob in all_problems:
        print("FAIL " + prob)
    if all_problems:
        print(f"\nRESULT: FAIL ({len(all_problems)} problem(s))")
        return 1
    print("RESULT: PASS — RTL grid gutter keeps shipped single-sided geometry")
    print("checked: " + ", ".join(str(f.relative_to(ROOT) if str(f).startswith(str(ROOT)) else f) for f in files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
