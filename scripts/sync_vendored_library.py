#!/usr/bin/env python3
"""Sync the vendored sungrow_modbus copy from library/sungrow-modbus.

`custom_components/sungrow_sg/sungrow_modbus/` is a committed mirror of
`library/sungrow-modbus/src/sungrow_modbus/` (see that copy's __init__.py
for why). Run this after editing anything under the library, then run
both test suites before committing:

    python scripts/sync_vendored_library.py
    pytest library/sungrow-modbus/tests
    pytest tests
"""

from __future__ import annotations

import filecmp
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "library" / "sungrow-modbus" / "src" / "sungrow_modbus"
DEST = REPO_ROOT / "custom_components" / "sungrow_sg" / "sungrow_modbus"


def main() -> None:
    source_files = sorted(p.name for p in SOURCE.glob("*.py"))
    dest_files = sorted(p.name for p in DEST.glob("*.py"))
    if source_files != dest_files:
        print(f"File sets differ - source: {source_files}, dest: {dest_files}")
        print("Copying source's file set as-is (removing anything dest-only).")

    for stale in set(dest_files) - set(source_files):
        (DEST / stale).unlink()
        print(f"removed {DEST / stale} (no longer in library)")

    changed = 0
    for name in source_files:
        src_file = SOURCE / name
        dest_file = DEST / name
        if dest_file.exists() and filecmp.cmp(src_file, dest_file, shallow=False):
            continue
        shutil.copyfile(src_file, dest_file)
        changed += 1
        print(f"synced {dest_file}")

    if changed == 0:
        print("Already in sync - nothing copied.")
    else:
        print(f"Synced {changed} file(s). Run both test suites before committing.")


if __name__ == "__main__":
    main()
