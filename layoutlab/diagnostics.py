"""Blender console diagnostic checks — structured report for sharing with Cursor."""

import json
from datetime import datetime

from .util import infer_generator_meta_from_code, parse_commands_payload

REPORT_BEGIN = "=== LAYOUTLAB DIAGNOSTIC REPORT BEGIN ==="
REPORT_END = "=== LAYOUTLAB DIAGNOSTIC REPORT END ==="
DIAG_COLLECTION = "layoutlab_diagnostics"
DIAG_PREFIX = "LAYOUTLAB_DIAG_"
TRANSFORM_TOL = 0.08
REL_TOL = 0.05


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


def emit_diagnostic_report(report):
    """Print report to the system console (Window → Toggle System Console)."""
    print("\nLayoutLab diagnostics — full report:\n", flush=True)
    print(report, flush=True)
    print("", flush=True)


def run_console_checks(context):
    import bpy

    from .engine.registry import sync_bundled_generators
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
    from .api.collections import delete_prefix
    from .util import generator_version_tuple, infer_generator_meta_from_code

    bed_name = f"{DIAG_PREFIX}BED"
    delete_prefix(DIAG_PREFIX)
    sync_bundled_generators()
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
        desk_bundled = bundled / "desk_basic.py"
        user_dir = addon_user_dir()
        check.ok(
            f"addon_root: {addon_root_dir()}",
            f"bundled_generators: {bundled}",
            f"bed_basic_bundled: {bed_bundled.exists()}",
            f"desk_basic_bundled: {desk_bundled.exists()}",
            f"user_generators: {user_dir}",
        )

    def check_install_bed_basic(check):
        path = generator_path("bed_basic")
        bundled_code = load_bundled_generator_source("bed_basic")
        bundled_meta = infer_generator_meta_from_code(bundled_code)
        if not path.exists():
            save_generator_code(bundled_code)
        else:
            user_meta = infer_generator_meta_from_code(path.read_text(encoding="utf-8"))
            user_ver = generator_version_tuple(user_meta.get("version"))
            bundled_ver = generator_version_tuple(bundled_meta.get("version"))
            if user_ver < bundled_ver:
                save_generator_code(bundled_code)
                check.ok(
                    f"bed_basic_path: {path}",
                    f"upgraded: {'.'.join(map(str, user_ver))} -> {'.'.join(map(str, bundled_ver))}",
                )
                return
        user_meta = infer_generator_meta_from_code(path.read_text(encoding="utf-8"))
        check.ok(
            f"bed_basic_path: {path}",
            f"user_version: {user_meta.get('version')}",
            f"bundled_version: {bundled_meta.get('version')}",
        )

    def check_install_desk_basic(check):
        path = generator_path("desk_basic")
        bundled_code = load_bundled_generator_source("desk_basic")
        bundled_meta = infer_generator_meta_from_code(bundled_code)
        if not path.exists():
            save_generator_code(bundled_code)
        else:
            user_meta = infer_generator_meta_from_code(path.read_text(encoding="utf-8"))
            user_ver = generator_version_tuple(user_meta.get("version"))
            bundled_ver = generator_version_tuple(bundled_meta.get("version"))
            if user_ver < bundled_ver:
                save_generator_code(bundled_code)
                check.ok(
                    f"desk_basic_path: {path}",
                    f"upgraded: {'.'.join(map(str, user_ver))} -> {'.'.join(map(str, bundled_ver))}",
                )
                return
        user_meta = infer_generator_meta_from_code(path.read_text(encoding="utf-8"))
        check.ok(
            f"desk_basic_path: {path}",
            f"user_version: {user_meta.get('version')}",
            f"bundled_version: {bundled_meta.get('version')}",
        )

    def check_generator_metadata(check):
        path = generator_path("bed_basic")
        code = path.read_text(encoding="utf-8")
        meta = infer_generator_meta_from_code(code, path)
        bundled_meta = infer_generator_meta_from_code(load_bundled_generator_source("bed_basic"))
        if meta["name"] != "bed_basic":
            check.fail(f"unexpected name: {meta['name']}")
            return
        if generator_version_tuple(meta.get("version")) < generator_version_tuple(bundled_meta.get("version")):
            check.fail(
                f"user version stale: {meta.get('version')} (bundled {bundled_meta.get('version')})",
                f"path: {path}",
            )
            return
        check.ok(
            f"name: {meta['name']}",
            f"category: {meta['category']}",
            f"version: {meta['version']}",
            f"source: user_generators",
        )

    def check_parse_commands(check):
        envelope = parse_commands_payload('{"commands":[{"action":"delete_prefix","prefix":"X"}]}')
        array = parse_commands_payload('[{"action":"delete"}]')
        if len(envelope) != 1 or len(array) != 1:
            check.fail("parse_commands_payload returned unexpected lengths")
            return
        check.ok("envelope_form: ok", "bare_array_form: ok")

    def check_run_generator_direct(check):
        delete_prefix(bed_name)
        try:
            result = execute_generator(
                "bed_basic",
                {
                    "name": bed_name,
                    "location": [1000, 1000, 0],
                    "length": 1.2,
                    "width": 2.0,
                    "head_side": "y_max",
                    "collection": DIAG_COLLECTION,
                },
            )
        except Exception as exc:
            check.fail(f"execute_generator raised: {exc}")
            return
        objs = [o for o in bpy.data.objects if o.get("layoutlab_object_id") == result.get("object_id")]
        body = bpy.data.objects.get(f"{bed_name}_body")
        mattress = bpy.data.objects.get(f"{bed_name}_mattress")
        roles = sorted({o.get("layoutlab_role", "") for o in objs if o.get("layoutlab_role")})
        if len(objs) < 4:
            check.fail(f"expected >= 4 part objects, got {len(objs)}", f"objects: {[o.name for o in objs]}")
            return
        if not body or body.get("layoutlab_part_type") != "main":
            check.fail(f"main part missing or wrong type: {getattr(body, 'name', None)}")
            return
        if not mattress or not mattress.get("layoutlab_object_id"):
            check.fail("mattress missing layoutlab_object_id")
            return
        if mattress.parent != body:
            check.fail(f"mattress not parented to body (parent={getattr(mattress.parent, 'name', None)})")
            return
        from .api.transforms import parenting_local_matches_world

        if not parenting_local_matches_world(mattress, body):
            check.fail("mattress parenting matrix inconsistent (world/local mismatch)")
            return
        from .api.transforms import child_local_looks_like_world_coords

        if child_local_looks_like_world_coords(mattress):
            check.fail(
                f"mattress local coords look like world coords: {tuple(mattress.location)}",
                f"body_world={tuple(body.matrix_world.translation)}",
            )
            return
        if result.get("object_id") != mattress.get("layoutlab_object_id"):
            check.fail("execute_generator object_id mismatch")
            return
        if result.get("main_part") != f"{bed_name}_body":
            check.fail(f"main_part: {result.get('main_part')}")
            return
        check.ok(
            f"part_object_count: {len(objs)}",
            f"parts: {result.get('parts', [])}",
            f"main_part: {result.get('main_part')}",
            f"roles: {roles}",
            f"object_id: {mattress.get('layoutlab_object_id')}",
            f"generator: {mattress.get('layoutlab_generator')}",
            f"layoutlab_part: {mattress.get('layoutlab_part')}",
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
                            "length": 1.4,
                            "width": 2.0,
                            "head_side": "y_max",
                            "collection": DIAG_COLLECTION,
                        },
                    },
                    {
                        "action": "create_clearance",
                        "name": f"{DIAG_PREFIX}CLEARANCE",
                        "location": [1000, 1000, 0],
                        "dimensions": [1.4, 0.7, 0.01],
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
        if not mattress.get("layoutlab_object_id"):
            check.fail("mattress missing layoutlab_object_id (stale generator in layoutlab_generators?)")
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
                        "params": {"length": 1.6},
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
        if stored.get("length") != 1.6:
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
        if layoutlab.get("part") != "mattress":
            check.fail(f"export part: {layoutlab.get('part')}")
            return
        check.ok(
            f"layoutlab_version: {export['layoutlab_version']}",
            f"generator_count: {len(export.get('generators', []))}",
            f"bed_basic_listed: {'bed_basic' in gen_names}",
            f"diag_object_count_in_export: {len(diag_objects)}",
            f"export_object_id: {layoutlab.get('object_id')}",
            f"export_part: {layoutlab.get('part')}",
            f"export_part_type: {layoutlab.get('part_type')}",
        )

    def _world_bbox_y_extents(obj):
        from mathutils import Vector

        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        ys = [c.y for c in corners]
        return min(ys), max(ys)

    def check_part_bed_world_layout(check):
        from .api.transforms import (
            child_local_looks_like_world_coords,
            parenting_local_matches_world,
            relative_translation_tuple,
            translations_close,
        )

        prefix = f"{DIAG_PREFIX}BED_XFORM"
        rels = []
        for loc in ([0.0, 0.0, 0.0], [68.3, 197.7, 0.0]):
            delete_prefix(prefix)
            execute_generator(
                "bed_basic",
                {
                    "name": prefix,
                    "location": loc,
                    "length": 1.2,
                    "width": 2.0,
                    "head_side": "y_max",
                    "collection": DIAG_COLLECTION,
                },
            )
            body = bpy.data.objects.get(f"{prefix}_body")
            mattress = bpy.data.objects.get(f"{prefix}_mattress")
            if not body or not mattress:
                check.fail(f"parts missing at location {loc}")
                return
            if mattress.parent != body:
                check.fail(f"mattress not parented at {loc}")
                return
            if not parenting_local_matches_world(mattress, body):
                check.fail(f"parent matrix inconsistent at {loc}")
                return
            if child_local_looks_like_world_coords(mattress):
                check.fail(f"mattress local looks like world at {loc}: {tuple(mattress.location)}")
                return
            rel = relative_translation_tuple(mattress, body)
            if abs(rel[0]) > 5 or abs(rel[1]) > 5 or rel[2] < 0 or rel[2] > 15:
                check.fail(f"mattress too far from body at {loc}: rel={rel}")
                return
            rels.append(rel)

        if len(rels) != 2 or not translations_close(rels[0], rels[1], REL_TOL):
            check.fail(f"relative layout differs: origin={rels[0] if rels else None} offset={rels[1] if len(rels) > 1 else None}")
            return

        loc = [68.3, 197.7, 0.0]
        delete_prefix(f"{DIAG_PREFIX}BED_XFORM_ABS")
        execute_generator(
            "bed_basic",
            {
                "name": f"{DIAG_PREFIX}BED_XFORM_ABS",
                "location": loc,
                "length": 1.2,
                "width": 2.0,
                "head_side": "y_max",
                "collection": DIAG_COLLECTION,
            },
        )
        body = bpy.data.objects.get(f"{DIAG_PREFIX}BED_XFORM_ABS_body")
        mattress = bpy.data.objects.get(f"{DIAG_PREFIX}BED_XFORM_ABS_mattress")
        rail = min(0.035, 2.0 * 0.2, 1.2 * 0.2)
        expected = (loc[0] + rail, loc[1] + rail, loc[2] + 0.25 + 0.1 * 0.55)
        actual = mattress.matrix_world.translation
        actual_t = (float(actual.x), float(actual.y), float(actual.z))
        if not translations_close(actual_t, expected, tolerance=0.08):
            check.fail(
                f"mattress world mismatch: expected={expected} actual={actual_t}",
                f"body_world={tuple(body.matrix_world.translation)}",
            )
            return
        check.ok(
            f"relative_at_origin: {rels[0]}",
            f"relative_at_offset: {rels[1]}",
            f"mattress_world_expected: {expected}",
            f"mattress_world_actual: {actual_t}",
            "world_offset_independent: yes",
        )

    def check_part_follows_main_transform(check):
        import math

        from .api.transforms import relative_translation_tuple, translations_close

        prefix = f"{DIAG_PREFIX}BED_MOVE"
        delete_prefix(prefix)
        execute_generator(
            "bed_basic",
            {
                "name": prefix,
                "location": [100.0, 100.0, 0.0],
                "length": 1.2,
                "width": 2.0,
                "head_side": "y_max",
                "collection": DIAG_COLLECTION,
            },
        )
        body = bpy.data.objects.get(f"{prefix}_body")
        mattress = bpy.data.objects.get(f"{prefix}_mattress")
        if not body or not mattress:
            check.fail("bed parts missing for transform follow test")
            return

        mw0 = mattress.matrix_world.translation.copy()
        delta = (5.0, -3.0, 0.0)
        body.location = (
            body.location.x + delta[0],
            body.location.y + delta[1],
            body.location.z + delta[2],
        )
        context.view_layer.update()
        mw1 = mattress.matrix_world.translation.copy()
        moved = (mw1.x - mw0.x, mw1.y - mw0.y, mw1.z - mw0.z)
        if not translations_close(moved, delta, TRANSFORM_TOL):
            check.fail(f"translate follow mismatch: delta={delta} moved={moved}")
            return

        dist_before = math.sqrt(sum(v * v for v in relative_translation_tuple(mattress, body)))
        body.rotation_euler[2] = math.radians(25.0)
        context.view_layer.update()
        dist_after = math.sqrt(sum(v * v for v in relative_translation_tuple(mattress, body)))
        if abs(dist_before - dist_after) > TRANSFORM_TOL:
            check.fail(f"rotate follow mismatch: before={dist_before} after={dist_after}")
            return
        check.ok(
            f"translate_delta: {delta}",
            f"mattress_moved: {moved}",
            f"rotate_distance_before: {round(dist_before, 4)}",
            f"rotate_distance_after: {round(dist_after, 4)}",
        )

    def check_wardrobe_clearance_layout(check):
        from .api.transforms import translations_close

        prefix = f"{DIAG_PREFIX}WARDROBE"
        gaps = []
        for loc in ([0.0, 0.0, 0.0], [50.0, 120.0, 0.0]):
            delete_prefix(prefix)
            execute_generator(
                "wardrobe_basic",
                {
                    "name": prefix,
                    "location": loc,
                    "width": 0.8,
                    "depth": 0.4,
                    "height": 1.5,
                    "show_clearance": True,
                    "collection": DIAG_COLLECTION,
                },
            )
            body = bpy.data.objects.get(f"{prefix}_body")
            clearance = bpy.data.objects.get(f"{prefix}_clearance_front_access")
            if not body or not clearance:
                check.fail(f"wardrobe parts missing at {loc}")
                return
            if clearance.parent != body:
                check.fail(f"clearance not parented at {loc}")
                return
            if clearance.get("layoutlab_clearance_name") != "front_access":
                check.fail(f"unexpected clearance_name at {loc}: {clearance.get('layoutlab_clearance_name')}")
                return
            if clearance.get("layoutlab_clearance_requirement") != "preferred":
                check.fail(f"unexpected requirement at {loc}")
                return
            if not clearance.get("layoutlab_clearance_id"):
                check.fail(f"missing clearance_id at {loc}")
                return
            body_ymin, _ = _world_bbox_y_extents(body)
            _, clearance_ymax = _world_bbox_y_extents(clearance)
            gap = body_ymin - clearance_ymax
            if gap < -0.05 or gap > 0.1:
                check.fail(f"clearance front gap unexpected at {loc}: gap={gap}")
                return
            gaps.append(round(gap, 4))
        if not translations_close((gaps[0], 0, 0), (gaps[1], 0, 0), REL_TOL):
            check.fail(f"clearance gap differs by world location: {gaps}")
            return
        check.ok(
            f"clearance_gap_origin: {gaps[0]}",
            f"clearance_gap_offset: {gaps[1]}",
            "front_side: y_min",
        )

    def check_regenerate_layout_policy(check):
        from .api.transforms import relative_translation_tuple

        body = bpy.data.objects.get(f"{bed_name}_body")
        mattress = bpy.data.objects.get(f"{bed_name}_mattress")
        if not body or not mattress:
            check.fail("bed parts missing after regenerate")
            return
        rel = relative_translation_tuple(mattress, body)
        if abs(rel[0]) > 5 or abs(rel[1]) > 5:
            check.fail(f"post-regenerate mattress offset too large: {rel}")
            return
        stored = json.loads(mattress.get("layoutlab_params", "{}"))
        check.ok(
            f"params_location: {stored.get('location')}",
            f"mattress_rel_to_body: {tuple(round(v, 4) for v in rel)}",
            "policy: regenerate uses params.location (not manual main-part move)",
            "no_double_offset: yes",
        )

    def check_clearance_export(check):
        prefix = f"{DIAG_PREFIX}WARDROBE_EXPORT"
        delete_prefix(prefix)
        loc = [50.0, 120.0, 0.0]
        execute_generator(
            "wardrobe_basic",
            {
                "name": prefix,
                "location": loc,
                "width": 0.8,
                "depth": 0.4,
                "height": 1.5,
                "show_clearance": True,
                "collection": DIAG_COLLECTION,
            },
        )
        export = json.loads(layout_export_json(context, selected_only=False))
        clearance_obj = next(
            (o for o in export.get("objects", []) if o["name"] == f"{prefix}_clearance_front_access"),
            None,
        )
        if not clearance_obj:
            check.fail("clearance object missing from export")
            return
        layoutlab = clearance_obj.get("layoutlab") or {}
        clearance = layoutlab.get("clearance")
        if not clearance:
            check.fail("layoutlab.clearance block missing from export")
            return
        if clearance.get("clearance_name") != "front_access":
            check.fail(f"export clearance_name: {clearance.get('clearance_name')}")
            return
        if clearance.get("requirement") != "preferred":
            check.fail(f"export requirement: {clearance.get('requirement')}")
            return
        local_bounds = clearance.get("local_bounds")
        world_bounds = clearance.get("world_bounds")
        if not local_bounds or not world_bounds:
            check.fail("export missing local_bounds or world_bounds")
            return
        local_min = local_bounds.get("min", [])
        if len(local_min) < 2 or local_min[1] >= -0.5:
            check.fail(f"local_bounds.min y expected negative, got {local_min}")
            return
        world_min = world_bounds.get("min", [])
        if not world_min or abs(float(world_min[0]) - loc[0]) > 0.5:
            check.fail(f"world_bounds.min x unexpected: {world_min} for loc {loc}")
            return
        check.ok(
            f"clearance_name: {clearance.get('clearance_name')}",
            f"clearance_id: {clearance.get('clearance_id', '')[:8]}…",
            f"local_bounds.min: {local_min}",
            f"world_bounds.min: {world_min}",
            f"shape: {clearance.get('shape')}",
        )

    def check_analyze_layout_clear(check):
        from .protocol.layout_analysis import analyze_layout

        prefix = f"{DIAG_PREFIX}ANALYZE_CLR"
        delete_prefix(DIAG_PREFIX)
        execute_generator(
            "wardrobe_basic",
            {
                "name": prefix,
                "location": [0, 0, 0],
                "width": 0.8,
                "depth": 0.4,
                "height": 1.5,
                "show_clearance": True,
                "collection": DIAG_COLLECTION,
            },
        )
        result = analyze_layout(
            context,
            {"action": "analyze_layout", "scope": "collection", "collection": DIAG_COLLECTION},
        )
        if not result.get("analyzed"):
            check.fail("analyzed=false")
            return
        findings = result.get("findings", [])
        summary = result.get("summary", {})
        if findings:
            check.fail(f"expected no findings, got {findings}")
            return
        if any(summary.get(k, 0) for k in ("errors", "warnings", "info")):
            check.fail(f"expected zero summary counts, got {summary}")
            return
        check.ok(
            f"clearance_count: {result.get('clearance_count')}",
            f"findings: 0",
            f"summary: {summary}",
        )

    def check_analyze_layout_blocked(check):
        from .protocol.layout_analysis import analyze_layout

        prefix = f"{DIAG_PREFIX}ANALYZE_BLK"
        delete_prefix(DIAG_PREFIX)
        wardrobe_name = f"{prefix}_WARDROBE"
        execute_generator(
            "wardrobe_basic",
            {
                "name": wardrobe_name,
                "location": [0, 0, 0],
                "width": 0.8,
                "depth": 0.4,
                "height": 1.5,
                "show_clearance": True,
                "collection": DIAG_COLLECTION,
            },
        )
        execute_generator(
            "bed_basic",
            {
                "name": f"{prefix}_BED",
                "location": [0, -1.0, 0],
                "length": 1.2,
                "width": 2.0,
                "head_side": "y_max",
                "collection": DIAG_COLLECTION,
            },
        )
        result = analyze_layout(
            context,
            {"action": "analyze_layout", "scope": "collection", "collection": DIAG_COLLECTION},
        )
        if not result.get("analyzed"):
            check.fail("analyzed=false")
            return
        findings = result.get("findings", [])
        front = [
            f
            for f in findings
            if f.get("clearance_ref", {}).get("clearance_name") == "front_access"
            and f.get("clearance_ref", {}).get("furniture_name") == wardrobe_name
        ]
        if len(front) != 1:
            check.fail(f"expected 1 front_access finding, got {len(front)}: {findings}")
            return
        finding = front[0]
        if finding.get("severity") != "warning":
            check.fail(f"expected warning (preferred), got {finding.get('severity')}")
            return
        if finding.get("constraint_type") != "zone_must_be_clear":
            check.fail(f"constraint_type: {finding.get('constraint_type')}")
            return
        overlaps = finding.get("overlaps", [])
        if not overlaps:
            check.fail("expected overlaps")
            return
        if not any("BED" in o.get("object_name", "") and "body" in o.get("object_name", "") for o in overlaps):
            check.fail(f"bed body not in overlaps: {overlaps}")
            return
        check.ok(
            f"severity: {finding.get('severity')}",
            f"clearance_name: front_access",
            f"overlap_count: {len(overlaps)}",
            f"summary: {result.get('summary')}",
        )

    def check_analyze_layout_bed_clear(check):
        from .protocol.layout_analysis import analyze_layout

        bed_name = f"{DIAG_PREFIX}BED_ENTRY_CLR"
        delete_prefix(DIAG_PREFIX)
        execute_generator(
            "bed_basic",
            {
                "name": bed_name,
                "location": [0, 0, 0],
                "length": 1.2,
                "width": 2.0,
                "head_side": "y_max",
                "collection": DIAG_COLLECTION,
                "clearances": [
                    {
                        "clearance_name": "bed_entry",
                        "side": "foot",
                        "requirement": "preferred",
                        "depth": 0.6,
                    }
                ],
            },
        )
        clearance = bpy.data.objects.get(f"{bed_name}_clearance_bed_entry")
        if not clearance or clearance.get("layoutlab_clearance_name") != "bed_entry":
            check.fail(f"bed_entry clearance missing: {getattr(clearance, 'name', None)}")
            return
        result = analyze_layout(
            context,
            {"action": "analyze_layout", "scope": "collection", "collection": DIAG_COLLECTION},
        )
        if result.get("findings"):
            check.fail(f"expected no findings, got {result.get('findings')}")
            return
        check.ok(
            f"clearance_count: {result.get('clearance_count')}",
            f"bed_entry: {clearance.get('layoutlab_clearance_name')}",
            f"findings: 0",
        )

    def check_analyze_layout_bed_blocked(check):
        from .protocol.layout_analysis import analyze_layout

        bed_name = f"{DIAG_PREFIX}BED_ENTRY_BLK"
        delete_prefix(DIAG_PREFIX)
        execute_generator(
            "bed_basic",
            {
                "name": bed_name,
                "location": [0, 0, 0],
                "length": 1.2,
                "width": 2.0,
                "head_side": "y_max",
                "collection": DIAG_COLLECTION,
                "clearances": [
                    {
                        "clearance_name": "bed_entry",
                        "side": "foot",
                        "requirement": "preferred",
                        "depth": 0.6,
                    }
                ],
            },
        )
        apply_commands_json(
            context,
            json.dumps(
                {
                    "commands": [
                        {
                            "action": "create_box",
                            "name": f"{DIAG_PREFIX}BED_ENTRY_OBSTACLE",
                            "location": [0, -0.5, 0],
                            "dimensions": [1.2, 0.3, 0.4],
                            "collection": DIAG_COLLECTION,
                        }
                    ]
                }
            ),
        )
        result = analyze_layout(
            context,
            {"action": "analyze_layout", "scope": "collection", "collection": DIAG_COLLECTION},
        )
        bed_findings = [
            f
            for f in result.get("findings", [])
            if f.get("clearance_ref", {}).get("clearance_name") == "bed_entry"
            and f.get("clearance_ref", {}).get("furniture_name") == bed_name
        ]
        if len(bed_findings) != 1:
            check.fail(f"expected 1 bed_entry finding, got {len(bed_findings)}: {result.get('findings')}")
            return
        finding = bed_findings[0]
        if finding.get("severity") != "warning":
            check.fail(f"expected warning, got {finding.get('severity')}")
            return
        overlaps = finding.get("overlaps", [])
        if not any("OBSTACLE" in o.get("object_name", "") for o in overlaps):
            check.fail(f"obstacle not in overlaps: {overlaps}")
            return
        check.ok(
            f"severity: {finding.get('severity')}",
            f"clearance_name: bed_entry",
            f"overlap_count: {len(overlaps)}",
        )

    def check_desk_clearance_layout(check):
        from .api.transforms import translations_close

        prefix = f"{DIAG_PREFIX}DESK"
        gaps = []
        for loc in ([0.0, 0.0, 0.0], [50.0, 120.0, 0.0]):
            delete_prefix(prefix)
            execute_generator(
                "desk_basic",
                {
                    "name": prefix,
                    "location": loc,
                    "width": 1.0,
                    "depth": 0.5,
                    "height": 0.75,
                    "show_clearance": True,
                    "collection": DIAG_COLLECTION,
                },
            )
            body = bpy.data.objects.get(f"{prefix}_body")
            clearance = bpy.data.objects.get(f"{prefix}_clearance_chair_access")
            if not body or not clearance:
                check.fail(f"desk parts missing at {loc}")
                return
            if clearance.parent != body:
                check.fail(f"clearance not parented at {loc}")
                return
            if clearance.get("layoutlab_clearance_name") != "chair_access":
                check.fail(f"unexpected clearance_name at {loc}: {clearance.get('layoutlab_clearance_name')}")
                return
            if clearance.get("layoutlab_clearance_requirement") != "required":
                check.fail(f"unexpected requirement at {loc}")
                return
            if not clearance.get("layoutlab_clearance_id"):
                check.fail(f"missing clearance_id at {loc}")
                return
            body_ymin, _ = _world_bbox_y_extents(body)
            _, clearance_ymax = _world_bbox_y_extents(clearance)
            gap = body_ymin - clearance_ymax
            if gap < -0.05 or gap > 0.1:
                check.fail(f"clearance front gap unexpected at {loc}: gap={gap}")
                return
            gaps.append(round(gap, 4))
        if not translations_close((gaps[0], 0, 0), (gaps[1], 0, 0), REL_TOL):
            check.fail(f"clearance gap differs by world location: {gaps}")
            return
        check.ok(
            f"clearance_gap_origin: {gaps[0]}",
            f"clearance_gap_offset: {gaps[1]}",
            "front_side: y_min",
            "clearance_name: chair_access",
        )

    def check_analyze_layout_desk_clear(check):
        from .protocol.layout_analysis import analyze_layout

        prefix = f"{DIAG_PREFIX}DESK_CLR"
        delete_prefix(DIAG_PREFIX)
        execute_generator(
            "desk_basic",
            {
                "name": prefix,
                "location": [0, 0, 0],
                "width": 1.0,
                "depth": 0.5,
                "height": 0.75,
                "show_clearance": True,
                "collection": DIAG_COLLECTION,
            },
        )
        result = analyze_layout(
            context,
            {"action": "analyze_layout", "scope": "collection", "collection": DIAG_COLLECTION},
        )
        if not result.get("analyzed"):
            check.fail("analyzed=false")
            return
        findings = result.get("findings", [])
        if findings:
            check.fail(f"expected no findings, got {findings}")
            return
        check.ok(
            f"clearance_count: {result.get('clearance_count')}",
            f"findings: 0",
            f"summary: {result.get('summary')}",
        )

    def check_analyze_layout_desk_blocked(check):
        from .protocol.layout_analysis import analyze_layout

        prefix = f"{DIAG_PREFIX}DESK_BLK"
        desk_name = f"{prefix}_DESK"
        delete_prefix(DIAG_PREFIX)
        execute_generator(
            "desk_basic",
            {
                "name": desk_name,
                "location": [0, 0, 0],
                "width": 1.0,
                "depth": 0.5,
                "height": 0.75,
                "show_clearance": True,
                "collection": DIAG_COLLECTION,
            },
        )
        apply_commands_json(
            context,
            json.dumps(
                {
                    "commands": [
                        {
                            "action": "create_box",
                            "name": f"{prefix}_OBSTACLE",
                            "location": [0, -0.45, 0],
                            "dimensions": [1.0, 0.3, 0.5],
                            "collection": DIAG_COLLECTION,
                        }
                    ]
                }
            ),
        )
        result = analyze_layout(
            context,
            {"action": "analyze_layout", "scope": "collection", "collection": DIAG_COLLECTION},
        )
        if not result.get("analyzed"):
            check.fail("analyzed=false")
            return
        findings = result.get("findings", [])
        chair = [
            f
            for f in findings
            if f.get("clearance_ref", {}).get("clearance_name") == "chair_access"
            and f.get("clearance_ref", {}).get("furniture_name") == desk_name
        ]
        if len(chair) != 1:
            check.fail(f"expected 1 chair_access finding, got {len(chair)}: {findings}")
            return
        finding = chair[0]
        if finding.get("severity") != "error":
            check.fail(f"expected error (required), got {finding.get('severity')}")
            return
        if finding.get("constraint_type") != "zone_must_be_clear":
            check.fail(f"constraint_type: {finding.get('constraint_type')}")
            return
        overlaps = finding.get("overlaps", [])
        if not any("OBSTACLE" in o.get("object_name", "") for o in overlaps):
            check.fail(f"obstacle not in overlaps: {overlaps}")
            return
        check.ok(
            f"severity: {finding.get('severity')}",
            f"clearance_name: chair_access",
            f"overlap_count: {len(overlaps)}",
            f"summary: {result.get('summary')}",
        )

    def check_room_model_create(check):
        from .protocol.export import layout_export_json

        prefix = f"{DIAG_PREFIX}ROOM"
        delete_prefix(prefix)
        results, errors = apply_commands_json(
            context,
            json.dumps(
                {
                    "commands": [
                        {
                            "action": "create_room",
                            "params": {
                                "name": prefix,
                                "location": [0, 0, 0],
                                "width": 4.0,
                                "depth": 2.5,
                                "height": 2.5,
                                "wall_thickness": 0.02,
                                "collection": DIAG_COLLECTION,
                            },
                        },
                        {
                            "action": "add_opening",
                            "params": {
                                "room": prefix,
                                "opening_name": "door_east",
                                "kind": "door",
                                "wall_side": "east",
                                "offset": 0.2,
                                "width": 0.9,
                                "height": 2.0,
                            },
                        },
                        {
                            "action": "add_opening",
                            "params": {
                                "room": prefix,
                                "opening_name": "window_west",
                                "kind": "window",
                                "wall_side": "west",
                                "offset": 0.3,
                                "width": 0.8,
                                "height": 1.2,
                                "sill_height": 0.8,
                            },
                        },
                        {
                            "action": "add_fixed_element",
                            "params": {
                                "room": prefix,
                                "fixed_name": "heizung",
                                "kind": "radiator",
                                "wall_side": "west",
                                "offset": 0.4,
                                "width": 0.6,
                                "depth": 0.1,
                                "height": 0.7,
                            },
                        },
                    ]
                }
            ),
        )
        if errors:
            check.fail(f"command errors: {errors[0][:200]}")
            return
        floor = bpy.data.objects.get(f"{prefix}_floor")
        if not floor:
            check.fail("room floor missing")
            return
        if floor.get("layoutlab_role") != "room_floor":
            check.fail(f"floor role: {floor.get('layoutlab_role')}")
            return
        walls = [o for o in bpy.data.objects if o.name.startswith(f"{prefix}_wall_")]
        if len(walls) < 4:
            check.fail(f"expected >= 4 wall panels, got {len(walls)}")
            return
        sides = {o.get("layoutlab_wall_side") for o in walls}
        if sides != {"south", "east", "north", "west"}:
            check.fail(f"wall sides incomplete: {sides}")
            return
        # Openings cut panels: east door + west window → more than 4 panels
        if len(walls) <= 4:
            check.fail(f"expected constructive opening cuts (>4 panels), got {len(walls)}")
            return
        export = json.loads(layout_export_json(context))
        rooms = export.get("rooms") or []
        room = next((r for r in rooms if r.get("name") == prefix), None)
        if not room:
            check.fail(f"room missing from export rooms[]: {[r.get('name') for r in rooms]}")
            return
        if room.get("footprint", {}).get("kind") != "rectangle":
            check.fail(f"footprint: {room.get('footprint')}")
            return
        if len(room.get("walls", [])) != 4:
            check.fail(f"export walls: {len(room.get('walls', []))}")
            return
        if len(room.get("openings", [])) != 2:
            check.fail(f"export openings: {room.get('openings')}")
            return
        if len(room.get("fixed_elements", [])) != 1:
            check.fail(f"export fixed: {room.get('fixed_elements')}")
            return
        check.ok(
            f"room_id: {str(room.get('room_id', ''))[:8]}…",
            f"walls: {len(room.get('walls', []))}",
            f"openings: {len(room.get('openings', []))}",
            f"fixed_elements: {len(room.get('fixed_elements', []))}",
            f"command_results: {len(results)}",
        )

    def check_analyze_layout_room_wall(check):
        """Wardrobe clearance through south wall → finding; floor must not be a blocker."""
        from .protocol.layout_analysis import analyze_layout

        prefix = f"{DIAG_PREFIX}ROOM_AN"
        delete_prefix(DIAG_PREFIX)
        results, errors = apply_commands_json(
            context,
            json.dumps(
                {
                    "commands": [
                        {
                            "action": "create_room",
                            "params": {
                                "name": prefix,
                                "location": [0, 0, 0],
                                "width": 3.0,
                                "depth": 3.0,
                                "height": 2.5,
                                "wall_thickness": 0.02,
                                "collection": DIAG_COLLECTION,
                            },
                        }
                    ]
                }
            ),
        )
        if errors:
            check.fail(f"create_room errors: {errors[0][:200]}")
            return
        wardrobe_name = f"{prefix}_WARDROBE"
        execute_generator(
            "wardrobe_basic",
            {
                "name": wardrobe_name,
                "location": [1.0, 0.05, 0],
                "width": 0.8,
                "depth": 0.4,
                "height": 1.5,
                "show_clearance": True,
                "front_side": "y_min",
                "collection": DIAG_COLLECTION,
            },
        )
        result = analyze_layout(
            context,
            {"action": "analyze_layout", "scope": "collection", "collection": DIAG_COLLECTION},
        )
        findings = [
            f
            for f in result.get("findings", [])
            if f.get("clearance_ref", {}).get("clearance_name") == "front_access"
            and f.get("clearance_ref", {}).get("furniture_name") == wardrobe_name
        ]
        if len(findings) != 1:
            check.fail(f"expected 1 front_access finding vs room wall, got {len(findings)}: {result.get('findings')}")
            return
        overlaps = findings[0].get("overlaps", [])
        if any(o.get("role") == "room_floor" for o in overlaps):
            check.fail(f"room_floor must not be a blocker: {overlaps}")
            return
        if not any(o.get("role") == "room_wall" for o in overlaps):
            check.fail(f"expected room_wall in overlaps: {overlaps}")
            return
        check.ok(
            f"severity: {findings[0].get('severity')}",
            f"wall_overlaps: {sum(1 for o in overlaps if o.get('role') == 'room_wall')}",
            "floor_excluded: yes",
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
            _run_check("install_desk_basic", check_install_desk_basic),
            _run_check("generator_metadata", check_generator_metadata),
            _run_check("parse_commands", check_parse_commands),
            _run_check("run_generator_direct", check_run_generator_direct),
            _run_check("part_bed_world_layout", check_part_bed_world_layout),
            _run_check("part_follows_main_transform", check_part_follows_main_transform),
            _run_check("wardrobe_clearance_layout", check_wardrobe_clearance_layout),
            _run_check("clearance_export", check_clearance_export),
            _run_check("analyze_layout_clear", check_analyze_layout_clear),
            _run_check("analyze_layout_blocked", check_analyze_layout_blocked),
            _run_check("analyze_layout_bed_clear", check_analyze_layout_bed_clear),
            _run_check("analyze_layout_bed_blocked", check_analyze_layout_bed_blocked),
            _run_check("desk_clearance_layout", check_desk_clearance_layout),
            _run_check("analyze_layout_desk_clear", check_analyze_layout_desk_clear),
            _run_check("analyze_layout_desk_blocked", check_analyze_layout_desk_blocked),
            _run_check("room_model_create", check_room_model_create),
            _run_check("analyze_layout_room_wall", check_analyze_layout_room_wall),
            _run_check("apply_commands_json", check_apply_commands_json),
            _run_check("regenerate", check_regenerate),
            _run_check("regenerate_layout_policy", check_regenerate_layout_policy),
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
    emit_diagnostic_report(report)
    return report
