"""Blender console diagnostic checks — structured report for sharing with Cursor."""

import json
from datetime import datetime

from .util import infer_generator_meta_from_code, parse_commands_payload

REPORT_BEGIN = "=== LAYOUTLAB DIAGNOSTIC REPORT BEGIN ==="
REPORT_END = "=== LAYOUTLAB DIAGNOSTIC REPORT END ==="
DIAG_COLLECTION = "layoutlab_diagnostics"
DIAG_PREFIX = "LAYOUTLAB_DIAG_"


class _Check:
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.details = []

    def ok(self, *lines):
        self.passed = True
        self.details.extend(lines)
        return self

    def fail(self, *lines):
        self.passed = False
        self.details.extend(lines)
        return self


def _run_check(name, fn):
    check = _Check(name)
    try:
        fn(check)
        if not check.details and check.passed:
            check.details.append("ok")
    except Exception as exc:
        check.fail(f"exception: {exc}")
    return check


def run_console_checks(context):
    import bpy

    from . import (
        addon_bundled_generators_dir,
        addon_root_dir,
        addon_user_dir,
        apply_commands_json,
        bl_info,
        execute_generator,
        generator_path,
        layout_export_json,
        load_bundled_generator_source,
        save_generator_code,
    )

    bed_name = f"{DIAG_PREFIX}BED"
    checks = []
    lines = []

    def header():
        version = ".".join(str(v) for v in bl_info["version"])
        lines.append(REPORT_BEGIN)
        lines.append(f"timestamp: {datetime.now().isoformat(timespec='seconds')}")
        lines.append(f"layoutlab_version: {version}")
        lines.append(f"blender_version: {bpy.app.version_string}")
        lines.append(f"scene: {context.scene.name}")
        lines.append(f"diag_collection: {DIAG_COLLECTION}")
        lines.append(f"diag_object_prefix: {DIAG_PREFIX}")
        lines.append("")

    def check_environment(check):
        bundled = addon_bundled_generators_dir()
        bed_bundled = bundled / "bed_basic.py"
        user_dir = addon_user_dir()
        check.ok(
            f"addon_root: {addon_root_dir()}",
            f"bundled_generators: {bundled}",
            f"bed_basic_bundled: {bed_bundled.exists()}",
            f"user_generators: {user_dir}",
        )

    def check_install_bed_basic(check):
        path = generator_path("bed_basic")
        if not path.exists():
            save_generator_code(load_bundled_generator_source("bed_basic"))
        check.ok(f"bed_basic_path: {path}", f"exists: {path.exists()}")

    def check_generator_metadata(check):
        code = load_bundled_generator_source("bed_basic")
        meta = infer_generator_meta_from_code(code, generator_path("bed_basic"))
        if meta["name"] != "bed_basic":
            check.fail(f"unexpected name: {meta['name']}")
            return
        check.ok(
            f"name: {meta['name']}",
            f"category: {meta['category']}",
            f"version: {meta['version']}",
        )

    def check_parse_commands(check):
        envelope = parse_commands_payload('{"commands":[{"action":"delete_prefix","prefix":"X"}]}')
        array = parse_commands_payload('[{"action":"delete"}]')
        if len(envelope) != 1 or len(array) != 1:
            check.fail("parse_commands_payload returned unexpected lengths")
            return
        check.ok("envelope_form: ok", "bare_array_form: ok")

    def check_run_generator_direct(check):
        result = execute_generator(
            "bed_basic",
            {
                "name": bed_name,
                "location": [1000, 1000, 0],
                "length": 12,
                "width": 20,
                "head_side": "y_max",
                "collection": DIAG_COLLECTION,
            },
        )
        objs = [o for o in bpy.data.objects if o.name.startswith(bed_name)]
        roles = sorted({o.get("layoutlab_role", "") for o in objs if o.get("layoutlab_role")})
        mattress = bpy.data.objects.get(f"{bed_name}_mattress")
        if len(objs) < 8:
            check.fail(f"expected >= 8 objects, got {len(objs)}", f"objects: {[o.name for o in objs]}")
            return
        if not mattress or not mattress.get("layoutlab_object_id"):
            check.fail("mattress missing layoutlab_object_id")
            return
        if result.get("object_id") != mattress.get("layoutlab_object_id"):
            check.fail("execute_generator object_id mismatch")
            return
        check.ok(
            f"object_count: {len(objs)}",
            f"roles: {roles}",
            f"object_id: {mattress.get('layoutlab_object_id')}",
            f"generator: {mattress.get('layoutlab_generator')}",
            f"component: {mattress.get('layoutlab_component')}",
        )

    def check_apply_commands_json(check):
        payload = json.dumps(
            {
                "commands": [
                    {"action": "delete_prefix", "prefix": bed_name},
                    {
                        "action": "run_generator",
                        "generator": "bed_basic",
                        "params": {
                            "name": bed_name,
                            "location": [1000, 1000, 0],
                            "length": 14,
                            "width": 20,
                            "head_side": "y_max",
                            "collection": DIAG_COLLECTION,
                        },
                    },
                    {
                        "action": "create_clearance",
                        "name": f"{DIAG_PREFIX}CLEARANCE",
                        "location": [1000, 1000, 0],
                        "dimensions": [14, 7, 0.1],
                        "collection": DIAG_COLLECTION,
                    },
                ]
            }
        )
        results, errors = apply_commands_json(context, payload)
        if errors:
            check.fail(f"errors: {errors}")
            return
        mattress = bpy.data.objects.get(f"{bed_name}_mattress")
        clearance = bpy.data.objects.get(f"{DIAG_PREFIX}CLEARANCE")
        if not mattress or not clearance:
            check.fail(
                f"mattress_found: {bool(mattress)}",
                f"clearance_found: {bool(clearance)}",
            )
            return
        check.ok(
            f"command_results: {len(results)}",
            f"mattress_dimensions: {list(mattress.dimensions)}",
            f"mattress_object_id: {mattress.get('layoutlab_object_id')}",
            f"clearance_role: {clearance.get('layoutlab_role')}",
            f"clearance_display: {clearance.display_type}",
        )

    def check_regenerate(check):
        mattress = bpy.data.objects.get(f"{bed_name}_mattress")
        if not mattress:
            check.fail("mattress not found for regenerate")
            return
        object_id = mattress.get("layoutlab_object_id")
        if not object_id:
            check.fail("mattress has no layoutlab_object_id")
            return
        before_dims = list(mattress.dimensions)
        payload = json.dumps(
            {
                "commands": [
                    {
                        "action": "regenerate",
                        "object_id": object_id,
                        "params": {"length": 16},
                    }
                ]
            }
        )
        results, errors = apply_commands_json(context, payload)
        if errors:
            check.fail(f"errors: {errors}")
            return
        new_mattress = bpy.data.objects.get(f"{bed_name}_mattress")
        if not new_mattress:
            check.fail("mattress missing after regenerate")
            return
        if new_mattress.get("layoutlab_object_id") != object_id:
            check.fail("object_id changed after regenerate")
            return
        after_dims = list(new_mattress.dimensions)
        if before_dims == after_dims:
            check.fail(f"dimensions unchanged: {before_dims}")
            return
        stored = json.loads(new_mattress.get("layoutlab_params", "{}"))
        if stored.get("length") != 16:
            check.fail(f"layoutlab_params length: {stored.get('length')}")
            return
        check.ok(
            f"object_id_preserved: {object_id}",
            f"dimensions_before: {before_dims}",
            f"dimensions_after: {after_dims}",
            f"params_length: {stored.get('length')}",
        )

    def check_scene_export(check):
        export = json.loads(layout_export_json(context, selected_only=False))
        required = {"layoutlab_version", "generators", "objects", "generator_dir", "note"}
        missing = required - set(export.keys())
        if missing:
            check.fail(f"missing_keys: {sorted(missing)}")
            return
        gen_names = [g["name"] for g in export.get("generators", [])]
        diag_objects = [o for o in export.get("objects", []) if o["name"].startswith(DIAG_PREFIX)]
        mattress_export = next((o for o in export.get("objects", []) if o["name"] == f"{bed_name}_mattress"), None)
        if not mattress_export or "layoutlab" not in mattress_export:
            check.fail("mattress missing layoutlab block in export")
            return
        layoutlab = mattress_export["layoutlab"]
        if layoutlab.get("generator") != "bed_basic":
            check.fail(f"export generator: {layoutlab.get('generator')}")
            return
        check.ok(
            f"layoutlab_version: {export['layoutlab_version']}",
            f"generator_count: {len(export.get('generators', []))}",
            f"bed_basic_listed: {'bed_basic' in gen_names}",
            f"diag_object_count_in_export: {len(diag_objects)}",
            f"export_object_id: {layoutlab.get('object_id')}",
            f"export_component: {layoutlab.get('component')}",
        )

    def check_cleanup(check):
        apply_commands_json(
            context,
            json.dumps({"commands": [{"action": "delete_prefix", "prefix": DIAG_PREFIX}]}),
        )
        remaining = [o.name for o in bpy.data.objects if o.name.startswith(DIAG_PREFIX)]
        if remaining:
            check.fail(f"remaining_objects: {remaining}")
            return
        check.ok("diag_objects_removed: yes")

    checks.extend(
        [
            _run_check("environment", check_environment),
            _run_check("install_bed_basic", check_install_bed_basic),
            _run_check("generator_metadata", check_generator_metadata),
            _run_check("parse_commands", check_parse_commands),
            _run_check("run_generator_direct", check_run_generator_direct),
            _run_check("apply_commands_json", check_apply_commands_json),
            _run_check("regenerate", check_regenerate),
            _run_check("scene_export", check_scene_export),
            _run_check("cleanup", check_cleanup),
        ]
    )

    header()
    passed = 0
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        if check.passed:
            passed += 1
        lines.append(f"[{status}] {check.name}")
        for detail in check.details:
            lines.append(f"  {detail}")
        lines.append("")

    lines.append(f"summary: {passed}/{len(checks)} passed")
    lines.append("")
    lines.append("Copy everything from BEGIN to END (inclusive) and send to Cursor.")
    lines.append(REPORT_END)

    report = "\n".join(lines)
    print(report)
    return report
