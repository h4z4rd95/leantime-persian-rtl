#!/usr/bin/env python3
"""Check a Leantime upgrade for new/changed English strings.

Usage:
  python scripts/check_upstream.py <path-to-new-en-US.ini>

After pulling a new Leantime image, dump the shipped English file and run this.
It reports:
  * keys NEW in upstream that are missing from our translation
  * keys whose English value CHANGED upstream (translation may be stale)

Exit code 0 = nothing to translate, 1 = work to do.

Then add the new keys to translations/fa-IR.json, bump translations/VERSION
(patch for new keys, minor for a changed upstream value set), and rerun
scripts/build_overlay.py.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "translations" / "fa-IR.json"


def parse_ini(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("["):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip('"')
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("en_us", help="path to the new shipped app/Language/en-US.ini")
    args = ap.parse_args()

    upstream = parse_ini(Path(args.en_us))
    ours = json.loads(SOURCE.read_text(encoding="utf-8"))

    new_keys = [k for k in upstream if k not in ours]
    changed = [
        k
        for k in upstream
        if k in ours and str(ours[k].get("en", "")) != upstream[k]
    ]

    print(f"upstream keys: {len(upstream)}   our keys: {len(ours)}")
    print(f"NEW keys to translate: {len(new_keys)}")
    for k in new_keys:
        print(f"  + {k} = {upstream[k][:70]}")
    print(f"CHANGED English values (translation may be stale): {len(changed)}")
    for k in changed:
        print(f"  ~ {k}\n      old en: {ours[k].get('en','')[:70]}\n      new en: {upstream[k][:70]}")

    if new_keys or changed:
        print("\nNext steps:")
        print("  1. Add the + keys to translations/fa-IR.json (with en + fa).")
        print("  2. Review the ~ keys and update fa if the meaning changed.")
        print("  3. Bump translations/VERSION.")
        print("  4. Run scripts/build_overlay.py and redeploy.")
        return 1
    print("\nNothing to do - our translation covers this upstream version.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
