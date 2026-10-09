#!/usr/bin/env python3
"""Deploy the built overlay + CSS to the Leantime container.

Usage:
  python scripts/deploy.py [--css-only] [--overlay-only]

Deploys to the production Leantime instance defined by the SERVER/CONTAINER
constants below, then clears every cache layer that the language system uses
and restarts php-fpm (opcache). Requires SSH key access to the host.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SERVER = "65.109.210.40"
SSH_USER = "root"
SSH_KEY = os.path.expanduser("~/.ssh/hermes_desktop_key")
CONTAINER = "code-leantime-1"

OVERLAY_LOCAL = ROOT / "custom" / "Language" / "fa-IR.ini"
OVERLAY_REMOTE = "/var/www/html/custom/Language/fa-IR.ini"
CSS_LOCAL = ROOT / "css" / "custom-premium.min.css"
CSS_REMOTE = "/var/www/html/public/theme/default/css/custom.min.css"


def ssh(cmd: str, timeout: int = 120) -> tuple[int, str]:
    full = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
        f"{SSH_USER}@{SERVER}", cmd,
    ]
    proc = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, (proc.stdout + proc.stderr)


def _tmp_name(remote: str) -> str:
    return remote.rsplit("/", 1)[-1]


def upload(local: Path, remote: str) -> None:
    tmp = _tmp_name(remote)
    subprocess.run(
        ["scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
         str(local), f"{SSH_USER}@{SERVER}:/tmp/{tmp}"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
         f"{SSH_USER}@{SERVER}",
         f"docker cp /tmp/{tmp} {CONTAINER}:{remote}"],
        check=True, capture_output=True, text=True,
    )
    print(f"  deployed {local.name} -> {remote}")


def clear_caches() -> None:
    print("clearing caches...")
    purge = (
        "rm -rf /var/www/html/storage/framework/cache/* "
        "/var/www/html/storage/framework/views/*"
    )
    ssh(f"docker exec {CONTAINER} sh -c '{purge}'")
    ssh(f"docker exec {CONTAINER} php /var/www/html/bin/leantime cache:clear")
    ssh(f"docker exec {CONTAINER} sh -c 'pkill -o php-fpm'")
    print("  cache purged + php-fpm restarted (opcache)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--css-only", action="store_true")
    ap.add_argument("--overlay-only", action="store_true")
    args = ap.parse_args()

    do_css = not args.overlay_only
    do_overlay = not args.css_only

    if do_overlay:
        if not OVERLAY_LOCAL.exists():
            print(f"missing {OVERLAY_LOCAL}; run scripts/build_overlay.py first")
            return 1
        print("deploying translation overlay...")
        upload(OVERLAY_LOCAL, OVERLAY_REMOTE)
    if do_css:
        if not CSS_LOCAL.exists():
            print(f"missing {CSS_LOCAL}")
            return 1
        print("deploying theme CSS...")
        upload(CSS_LOCAL, CSS_REMOTE)

    clear_caches()

    print("\nverify with:")
    print("  curl -s https://leantime.ppsj.ir/auth/login | grep -o 'placeholder=\"[^\"]*\"'")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
