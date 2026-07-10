from pathlib import Path

import bpy

from ..util import (
    generator_version_tuple,
    infer_generator_meta_from_code,
    infer_generator_name_from_code,
    sanitize_generator_name,
)


def addon_root_dir():
    return Path(__file__).resolve().parent.parent


def addon_bundled_generators_dir():
    return addon_root_dir() / "generators"


def addon_user_dir():
    base = Path(bpy.utils.user_resource("SCRIPTS", path="addons"))
    d = base / "layoutlab_generators"
    d.mkdir(parents=True, exist_ok=True)
    return d


def generator_path(name):
    return addon_user_dir() / f"{sanitize_generator_name(name)}.py"


def load_bundled_generator_source(name):
    path = addon_bundled_generators_dir() / f"{sanitize_generator_name(name)}.py"
    if not path.exists():
        raise FileNotFoundError(f"Bundled generator not found: {name}")
    return path.read_text(encoding="utf-8")


def default_generator_template():
    return load_bundled_generator_source("bed_basic")


def sync_bundled_generators():
    """Copy bundled generators into the user dir; upgrade when bundled version is newer."""
    bundled_dir = addon_bundled_generators_dir()
    if not bundled_dir.is_dir():
        return []
    updated = []
    for src in sorted(bundled_dir.glob("*.py")):
        dest = generator_path(src.stem)
        bundled_code = src.read_text(encoding="utf-8")
        bundled_ver = generator_version_tuple(infer_generator_meta_from_code(bundled_code).get("version"))
        if not dest.exists():
            dest.write_text(bundled_code, encoding="utf-8")
            updated.append((src.stem, "installed"))
            continue
        user_ver = generator_version_tuple(
            infer_generator_meta_from_code(dest.read_text(encoding="utf-8")).get("version")
        )
        if bundled_ver > user_ver:
            dest.write_text(bundled_code, encoding="utf-8")
            updated.append((src.stem, f"upgraded {'.'.join(map(str, user_ver))} -> {'.'.join(map(str, bundled_ver))}"))
    return updated


def list_generator_files():
    return sorted(addon_user_dir().glob("*.py"))


def list_generators_meta():
    metas = []
    for p in list_generator_files():
        try:
            metas.append(infer_generator_meta_from_code(p.read_text(encoding="utf-8"), p))
        except Exception:
            metas.append({
                "name": p.stem,
                "category": "Broken",
                "description": "Could not parse generator metadata.",
                "version": "",
                "icon": "ERROR",
                "path": str(p),
            })
    metas.sort(key=lambda m: (m["category"].lower(), m["name"].lower()))
    return metas


def read_generator_code(name):
    p = generator_path(name)
    if not p.exists():
        raise ValueError(f"Generator not found: {name}")
    return p.read_text(encoding="utf-8")


def save_generator_code(code):
    name = infer_generator_name_from_code(code)
    p = generator_path(name)
    p.write_text(code, encoding="utf-8")
    return name, p
