#!/usr/bin/env python3
"""Regression check: the fa-IR calendar/datepicker locale keys must be Persian
with an Iranian (Saturday) week start.

Leantime's jQuery UI datepicker is configured straight from the fa-IR language
INI (public/assets/js/app/core/datePickers.js): monthNames, monthNames*,
dayNames*, firstDayOfWeek and the button texts. Upstream ships English values
for these keys, which renders a fully English Gregorian picker inside the
Persian RTL UI. The overlay must carry:

  * Persian month names (transliterations of the GREGORIAN months — the picker
    widget itself stays Gregorian; see the Jalali decision in README before
    assuming this is calendar-system work),
  * Persian weekday names, Sunday-first (the order jQuery UI expects),
  * firstDayOfWeek = 6 (Saturday — the Iranian work-week start),
  * Persian texts for the picker buttons.

This check fails if any of those keys revert to English, or if the week start
is not Saturday.

Usage:
  python scripts/check_calendar_locale.py [ini_file ...]

Exit codes: 0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILES = [ROOT / "custom" / "Language" / "fa-IR.ini"]

PERSIAN = re.compile(r"[؀-ۿ]")

# key -> (min_items, must_be_persian)
STRING_LIST_KEYS = {
    "language.monthNames": (12, True),
    "language.monthNamesShort": (12, True),
    "language.dayNames": (7, True),
    "language.dayNamesShort": (7, True),
    "language.dayNamesMin": (7, True),
}
PLAIN_KEYS = {
    "language.currentText": "اکنون",
    "language.closeText": "بستن",
    "language.nextText": "بعدی",
    "language.prevText": "قبلی",
    "language.buttonText": "انتخاب",
    "language.weekHeader": "هفته",
    "language.firstDayOfWeek": "6",
}


def parse_ini(path: Path) -> dict[str, str]:
    kv: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        kv[key.strip()] = value.strip().strip('"')
    return kv


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    kv = parse_ini(path)

    for key, (count, persian) in STRING_LIST_KEYS.items():
        value = kv.get(key)
        if value is None:
            problems.append(f"{path.name}: missing {key}")
            continue
        items = value.split(",")
        if len(items) != count:
            problems.append(
                f"{path.name}: {key} has {len(items)} items, expected {count}: {value[:60]}"
            )
        if persian and not PERSIAN.search(value):
            problems.append(
                f"{path.name}: {key} is not Persian (English months/weekdays leak "
                f"into the Persian picker): {value[:60]}"
            )

    for key, expected in PLAIN_KEYS.items():
        value = kv.get(key)
        if value is None:
            problems.append(f"{path.name}: missing {key}")
        elif value != expected:
            problems.append(
                f"{path.name}: {key}={value!r}, expected {expected!r} "
                "(English picker text or wrong week start)"
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
    print("RESULT: PASS — calendar/datepicker locale is Persian with Saturday week start")
    print("checked: " + ", ".join(str(f.relative_to(ROOT)) for f in files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
