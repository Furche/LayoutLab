/**
 * Build a portable room snapshot for clipboard copy/paste.
 * Includes recreate commands (create_room, generators, rotate, place_on).
 */

function parseParams(obj) {
  const raw =
    obj?.custom_properties?.layoutlab_params ||
    obj?.layoutlab?.params ||
    null;
  if (!raw) return {};
  if (typeof raw === "object") return { ...raw };
  try {
    return JSON.parse(String(raw));
  } catch {
    return {};
  }
}

function parseSupportRef(ref) {
  const s = String(ref || "room_floor");
  if (!s || s === "room_floor") return { kind: "room_floor" };
  const m = /^object:([^#]+)#(.+)$/.exec(s);
  if (!m) return { kind: "room_floor" };
  return { kind: "object", hostId: m[1], surfaceId: m[2] };
}

function mainFurniture(exportData, roomId) {
  const objects = Array.isArray(exportData?.objects) ? exportData.objects : [];
  const mains = [];
  const seen = new Set();
  for (const o of objects) {
    const ll = o?.layoutlab || {};
    if (ll.part_type && ll.part_type !== "main") continue;
    const role = ll.role || o?.custom_properties?.layoutlab_role || "";
    if (role === "clearance" || role === "label") continue;
    const rid = ll.room_id || o?.custom_properties?.layoutlab_room_id;
    if (rid !== roomId) continue;
    const oid = ll.object_id || o?.custom_properties?.layoutlab_object_id;
    if (!oid || seen.has(oid)) continue;
    if (!ll.generator && !o?.custom_properties?.layoutlab_generator) continue;
    seen.add(oid);
    mains.push(o);
  }
  return mains;
}

/** Hosts before children that sit on them. */
function sortForRecreate(mains) {
  const byId = new Map();
  for (const o of mains) {
    const id = o.layoutlab?.object_id || o.custom_properties?.layoutlab_object_id;
    byId.set(id, o);
  }
  const deps = new Map();
  for (const o of mains) {
    const id = o.layoutlab?.object_id || o.custom_properties?.layoutlab_object_id;
    const support = parseSupportRef(o.layoutlab?.support_ref);
    deps.set(id, support.kind === "object" && byId.has(support.hostId) ? support.hostId : null);
  }
  const out = [];
  const visiting = new Set();
  const done = new Set();
  function visit(id) {
    if (done.has(id) || !byId.has(id)) return;
    if (visiting.has(id)) return;
    visiting.add(id);
    const host = deps.get(id);
    if (host) visit(host);
    visiting.delete(id);
    done.add(id);
    out.push(byId.get(id));
  }
  for (const id of byId.keys()) visit(id);
  return out;
}

function uniqueCopyName(base, index, used) {
  const cleaned = String(base || "OBJ")
    .replace(/_body$/i, "")
    .replace(/[^A-Za-z0-9_]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 24) || "OBJ";
  let name = `Copy_${cleaned}_${index}`;
  let n = 0;
  while (used.has(name)) {
    n += 1;
    name = `Copy_${cleaned}_${index}_${n}`;
  }
  used.add(name);
  return name;
}

/**
 * @param {object} exportData
 * @param {string} roomId
 * @param {{ offset?: number[] }} [opts]
 * @returns {{ payload: object, objectCount: number, roomName: string }}
 */
export function buildRoomCopyClipboard(exportData, roomId, opts = {}) {
  const rooms = Array.isArray(exportData?.rooms) ? exportData.rooms : [];
  const room = rooms.find((r) => r?.room_id === roomId);
  if (!room) throw new Error("No room selected to copy");

  const ox = Number(opts.offset?.[0]) || 0;
  const oy = Number(opts.offset?.[1]) || 0;
  const oz = Number(opts.offset?.[2]) || 0;

  const origin = Array.isArray(room.origin) ? [...room.origin] : [0, 0, 0];
  while (origin.length < 3) origin.push(0);
  const newOrigin = [origin[0] + ox, origin[1] + oy, origin[2] + oz];

  const roomName = String(room.name || "ROOM");
  const copyRoomName = `${roomName}_copy`;
  const collection = `layoutlab_${copyRoomName}`.replace(/[^A-Za-z0-9_]+/g, "_");

  const footprint = room.footprint || {};
  const width = Number(footprint.width) || Number(room.width) || 4;
  const depth = Number(footprint.depth) || Number(room.depth) || 3;
  const height = Number(room.height) || 2.6;
  const wallThickness = Number(room.wall_thickness) || 0.02;
  const roomRz = Number(room.rotation_z_deg ?? room.transform?.rotation_z_deg ?? 0) || 0;

  const commands = [];
  commands.push({
    action: "create_room",
    params: {
      name: copyRoomName,
      location: newOrigin,
      width,
      depth,
      height,
      wall_thickness: wallThickness,
      collection,
      rotation_z_deg: roomRz,
    },
  });

  for (const op of room.openings || []) {
    if (op?.state && String(op.state).startsWith("INACTIVE")) continue;
    commands.push({
      action: "add_opening",
      params: {
        room: copyRoomName,
        wall_side: op.wall_side,
        kind: op.kind || "door",
        width: op.width,
        height: op.height,
        offset: op.offset,
        sill_height: op.sill_height ?? 0,
        name: op.name,
      },
    });
  }

  for (const fe of room.fixed_elements || []) {
    if (fe?.state && String(fe.state).startsWith("INACTIVE")) continue;
    commands.push({
      action: "add_fixed_element",
      params: {
        room: copyRoomName,
        kind: fe.kind || "radiator",
        wall_side: fe.wall_side,
        offset: fe.offset,
        width: fe.width,
        depth: fe.depth,
        height: fe.height,
        name: fe.name,
      },
    });
  }

  const mains = sortForRecreate(mainFurniture(exportData, roomId));
  const idToCopyName = new Map();
  const usedNames = new Set();
  const objectsOut = [];

  mains.forEach((o, index) => {
    const oid = o.layoutlab?.object_id || o.custom_properties?.layoutlab_object_id;
    const generator =
      o.layoutlab?.generator || o.custom_properties?.layoutlab_generator || "";
    const params = parseParams(o);
    const loc = Array.isArray(o.location) ? o.location.map(Number) : [0, 0, 0];
    const rz = Number(o.rotation_euler_deg?.[2] ?? params.rotation_z_deg ?? 0) || 0;
    const copyName = uniqueCopyName(params.name || o.name || generator, index, usedNames);
    idToCopyName.set(oid, copyName);

    const nextParams = {
      ...params,
      name: copyName,
      collection,
      location: [loc[0] + ox, loc[1] + oy, loc[2] + (loc[2] != null ? oz : 0)],
      rotation_z_deg: rz,
    };
    // Don't bake host support into generator params — place_on handles it.
    delete nextParams.support_ref;
    delete nextParams.support_local_xy;

    objectsOut.push({
      source_object_id: oid,
      generator,
      name: copyName,
      params: nextParams,
      rotation_z_deg: rz,
      support_ref: o.layoutlab?.support_ref || "room_floor",
      support_local_xy: o.layoutlab?.support_local_xy ?? null,
      locked: Boolean(o.layoutlab?.locked),
      visible: o.visible !== false,
    });
  });

  // Generators first (hosts already sorted before children).
  // Export location is the min-corner *after* rotation. Generators spawn
  // unrotated, so rotate_z would pivot the corner — restore with move.
  for (const item of objectsOut) {
    commands.push({
      action: "run_generator",
      generator: item.generator,
      params: item.params,
    });
    if (Math.abs(item.rotation_z_deg) > 1e-6) {
      commands.push({
        action: "rotate_z",
        object: `${item.name}_body`,
        degrees: item.rotation_z_deg,
        absolute: true,
      });
      commands.push({
        action: "move",
        object: `${item.name}_body`,
        location: item.params.location,
      });
    }
  }

  // Support attachments (place_on) after all meshes exist.
  for (const item of objectsOut) {
    const support = parseSupportRef(item.support_ref);
    if (support.kind !== "object") continue;
    const hostName = idToCopyName.get(support.hostId);
    if (!hostName) continue;
    const loc = item.params.location || [0, 0, 0];
    commands.push({
      action: "place_on",
      object: `${item.name}_body`,
      host: `${hostName}_body`,
      surface_id: support.surfaceId || "surface_top",
      location: [loc[0], loc[1]],
    });
  }

  for (const item of objectsOut) {
    if (item.locked || item.visible === false) {
      commands.push({
        action: "set_flags",
        object: `${item.name}_body`,
        locked: item.locked,
        visible: item.visible,
      });
    }
  }

  const payload = {
    layoutlab_clipboard: "room_copy",
    schema: "0.1",
    source: {
      room_id: room.room_id,
      room_name: roomName,
      project_id: exportData.project_id || null,
      revision: exportData.revision ?? null,
      object_count: objectsOut.length,
    },
    room: {
      name: copyRoomName,
      origin: newOrigin,
      width,
      depth,
      height,
      wall_thickness: wallThickness,
      rotation_z_deg: roomRz,
      collection,
      openings: room.openings || [],
      fixed_elements: room.fixed_elements || [],
    },
    objects: objectsOut,
    commands,
  };

  return { payload, objectCount: objectsOut.length, roomName };
}

export function isRoomCopyClipboard(data) {
  return (
    data &&
    typeof data === "object" &&
    data.layoutlab_clipboard === "room_copy" &&
    Array.isArray(data.commands)
  );
}
