#!/usr/bin/env python3
"""Build a Blender-installable zip from the layoutlab/ addon folder."""

import re
import zipfile
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
ADDON_DIR = ROOT / "layoutlab"
DIST_DIR = ROOT / "dist"

SKIP_DIR_NAMES = {"__pycache__", ".DS_Store"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def read_addon_version():
    text = (ADDON_DIR / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'"version"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', text)
    if not match:
        raise ValueError("Could not read bl_info version from layoutlab/__init__.py")
    return ".".join(match.groups())


def should_skip(path: Path) -> bool:
    if path.name in SKIP_DIR_NAMES:
        return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def build_zip(output_path: Optional[Path] = None) -> Path:
    if not ADDON_DIR.is_dir():
        raise FileNotFoundError(f"Addon folder not found: {ADDON_DIR}")

    version = read_addon_version()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    output_path = output_path or DIST_DIR / f"layoutlab-{version}.zip"

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(ADDON_DIR.rglob("*")):
            if file_path.is_dir() or should_skip(file_path):
                continue
            arcname = file_path.relative_to(ROOT)
            zf.write(file_path, arcname)

    return output_path


if __name__ == "__main__":
    out = build_zip()
    print(f"Created: {out}")
    print("Install in Blender: Edit → Preferences → Add-ons → Install… → select this zip")
