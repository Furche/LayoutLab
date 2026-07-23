/**
 * Selection-based transform gizmos (FC-001):
 * Opaque flat 2D overlays in the Blender XY plane, with prioritized hit targets.
 *
 * Coordinates are Blender Z-up (parented under the scene world root).
 */

import * as THREE from "three";

const MOVE_X = 0xe06c75;
const MOVE_Y = 0x98c379;
const MOVE_XY = 0xe5c07b;
const ROTATE = 0xc678dd;
const SCALE = 0x5b9fd4;
const CORNER = 0xe5c07b;
const HOVER_TINT = 0xffffff;
const HANDLE_Z = 0.1;
const OUTSET = 0.16;
const GIZMO_RENDER_ORDER = 1000;

/** Higher wins when several coplanar handles overlap under the cursor. */
const PICK = {
  move_axis: 50,
  move_xy: 45,
  rotate_room_z: 55, // room ring is large / easy to miss — prefer over wall discs
  scale_axis: 40,
  wall: 40,
  corner: 40,
  rotate_z: 35,
};

let hoveredRoot = null;

/**
 * @param {object} room
 */
export function roomRect(room) {
  if (!room || room.visible === false) return null;
  if (room.footprint?.kind && room.footprint.kind !== "rectangle") return null;
  const ox = Number(room.origin?.[0] ?? room.world_bounds?.min?.[0]) || 0;
  const oy = Number(room.origin?.[1] ?? room.world_bounds?.min?.[1]) || 0;
  const oz = Number(room.origin?.[2] ?? room.world_bounds?.min?.[2]) || 0;
  const w = Number(room.footprint?.width) || 0;
  const d = Number(room.footprint?.depth) || 0;
  const h = Number(room.height) || 2.5;
  const rz =
    Number(room.rotation_z_deg ?? room.transform?.rotation_z_deg ?? 0) || 0;
  if (w <= 0 || d <= 0) return null;
  return { ox, oy, oz, w, d, h, rz };
}

function rotateZxy(x, y, deg) {
  const r = (Number(deg) * Math.PI) / 180;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return [x * c - y * s, x * s + y * c];
}

/** Room-local (SW frame) → world XY. */
export function roomLocalToWorld(rect, lx, ly) {
  const [rx, ry] = rotateZxy(lx, ly, rect.rz || 0);
  return [rect.ox + rx, rect.oy + ry];
}

/**
 * Local footprint bounds for furniture gizmos (size/centre/rz — not world AABB).
 * Scale handles must track object-local edges after Z rotation.
 * @returns {{ min: number[], max: number[], center: number[], size: number[], generator: string, rotation_z_deg: number } | null}
 */
export function furnitureBounds(exportData, objectId) {
  const objects = Array.isArray(exportData?.objects) ? exportData.objects : [];
  const matches = objects.filter((o) => {
    const id = o?.layoutlab?.object_id || o?.custom_properties?.layoutlab_object_id;
    if (id !== objectId) return false;
    const role = o?.layoutlab?.role || o?.custom_properties?.layoutlab_role || "";
    return role !== "clearance";
  });
  if (!matches.length) return null;

  const main =
    matches.find((o) => {
      const pt = o?.layoutlab?.part_type || o?.custom_properties?.layoutlab_part_type;
      return pt === "main";
    }) || matches[0];

  const generator = main?.layoutlab?.generator || main?.custom_properties?.layoutlab_generator || "";
  const rz =
    Number(
      main.rotation_euler_deg?.[2] ??
        main.rotation_z_deg ??
        main.layoutlab?.rotation_z_deg ??
        0,
    ) || 0;
  const loc = main.location || [0, 0, 0];
  const dims = main.dimensions || [0.2, 0.2, 0.2];
  const sx = Math.max(Number(dims[0]) || 0.2, 0.05);
  const sy = Math.max(Number(dims[1]) || 0.2, 0.05);
  const sz = Math.max(Number(dims[2]) || 0.05, 0.05);
  const hx = sx * 0.5;
  const hy = sy * 0.5;
  const [ox, oy] = rotateZxy(hx, hy, rz);
  const cx = (Number(loc[0]) || 0) + ox;
  const cy = (Number(loc[1]) || 0) + oy;
  const cz = Number(loc[2]) || 0;

  // World AABB still useful for fit / diagnostics.
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;
  for (const o of matches) {
    const corners = o.world_bbox_corners;
    if (Array.isArray(corners) && corners.length) {
      for (const c of corners) {
        if (!c || c.length < 3) continue;
        minX = Math.min(minX, Number(c[0]));
        minY = Math.min(minY, Number(c[1]));
        minZ = Math.min(minZ, Number(c[2]));
        maxX = Math.max(maxX, Number(c[0]));
        maxY = Math.max(maxY, Number(c[1]));
        maxZ = Math.max(maxZ, Number(c[2]));
      }
    }
  }
  if (!Number.isFinite(minX)) {
    minX = cx - hx;
    minY = cy - hy;
    minZ = cz;
    maxX = cx + hx;
    maxY = cy + hy;
    maxZ = cz + sz;
  }

  return {
    min: [minX, minY, minZ],
    max: [maxX, maxY, maxZ],
    center: [cx, cy, cz],
    size: [sx, sy, sz],
    generator,
    rotation_z_deg: rz,
  };
}

function fillMat(color) {
  return new THREE.MeshBasicMaterial({
    color,
    depthTest: true,
    depthWrite: true,
    side: THREE.DoubleSide,
    fog: false,
    toneMapped: false,
  });
}

function lineMat(color) {
  return new THREE.LineBasicMaterial({
    color,
    depthTest: true,
    depthWrite: true,
    fog: false,
    toneMapped: false,
  });
}

function styleOverlay(obj) {
  obj.renderOrder = GIZMO_RENDER_ORDER;
  obj.frustumCulled = false;
  return obj;
}

function markVisual(mesh, baseColor) {
  mesh.userData.gizmoVisual = true;
  mesh.userData.baseColor = baseColor;
  styleOverlay(mesh);
  return mesh;
}

function pickPriorityFor(meta) {
  if (meta.kind === "move_axis" && meta.axis === "xy") return PICK.move_xy;
  if (meta.kind === "move_axis") return PICK.move_axis;
  if (meta.kind === "rotate_room_z") return PICK.rotate_room_z;
  if (meta.kind === "rotate_z") return PICK.rotate_z;
  if (meta.kind === "scale_axis") return PICK.scale_axis;
  if (meta.kind === "wall") return PICK.wall;
  if (meta.kind === "corner") return PICK.corner;
  return 10;
}

function finishHandle(group, meta) {
  group.userData = { gizmo: true, hoverRoot: group, ...meta };
  group.name = meta.label || meta.kind || "gizmo";
  styleOverlay(group);
  const priority = pickPriorityFor(meta);
  group.traverse((o) => {
    if (!o.isMesh && !o.isLine) return;
    o.userData = {
      ...group.userData,
      gizmoHit: Boolean(o.userData?.gizmoHit),
      gizmoVisual: Boolean(o.userData?.gizmoVisual),
      baseColor: o.userData?.baseColor,
      pickPriority: priority,
      hoverRoot: group,
    };
  });
  return group;
}

function makeHit(geo, meta) {
  // Must stay raycastable: material.visible=false is a common footgun, and FrontSide
  // rings miss from many camera angles. Opacity-0 + DoubleSide still receives picks.
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshBasicMaterial({
      transparent: true,
      opacity: 0,
      depthTest: false,
      depthWrite: false,
      side: THREE.DoubleSide,
      toneMapped: false,
    }),
  );
  mesh.userData.gizmoHit = true;
  styleOverlay(mesh);
  return mesh;
}

/** Opaque flat disc (scale / wall / corner). */
function makeDisc(color, radius, meta) {
  const group = new THREE.Group();
  const fill = markVisual(new THREE.Mesh(new THREE.CircleGeometry(radius, 28), fillMat(color)), color);
  const rim = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(
      new THREE.EllipseCurve(0, 0, radius, radius, 0, Math.PI * 2, false, 0).getPoints(48),
    ),
    lineMat(0x1a1d23),
  );
  rim.position.z = 0.002;
  styleOverlay(rim);
  // Hit only slightly larger than visual — avoid stealing rotate/move picks.
  const hit = makeHit(new THREE.CircleGeometry(radius * 1.15, 20), meta);
  group.add(fill, rim, hit);
  return finishHandle(group, meta);
}

/** Opaque flat arrow along +X or +Y. */
function makeArrow(axis, color, meta) {
  const group = new THREE.Group();
  const shaftLen = 0.42;
  const shaftW = 0.08;
  const headLen = 0.18;
  const headW = 0.18;

  const shaft = markVisual(
    new THREE.Mesh(
      new THREE.PlaneGeometry(axis === "x" ? shaftLen : shaftW, axis === "x" ? shaftW : shaftLen),
      fillMat(color),
    ),
    color,
  );
  if (axis === "x") shaft.position.set(shaftLen / 2, 0, 0);
  else shaft.position.set(0, shaftLen / 2, 0);

  const headShape = new THREE.Shape();
  if (axis === "x") {
    headShape.moveTo(0, -headW / 2);
    headShape.lineTo(headLen, 0);
    headShape.lineTo(0, headW / 2);
    headShape.closePath();
  } else {
    headShape.moveTo(-headW / 2, 0);
    headShape.lineTo(0, headLen);
    headShape.lineTo(headW / 2, 0);
    headShape.closePath();
  }
  const head = markVisual(new THREE.Mesh(new THREE.ShapeGeometry(headShape), fillMat(color)), color);
  if (axis === "x") head.position.set(shaftLen, 0, 0.001);
  else head.position.set(0, shaftLen, 0.001);

  const hit = makeHit(
    axis === "x"
      ? new THREE.PlaneGeometry(shaftLen + headLen, Math.max(shaftW, headW) * 1.15)
      : new THREE.PlaneGeometry(Math.max(shaftW, headW) * 1.15, shaftLen + headLen),
    meta,
  );
  if (axis === "x") hit.position.set((shaftLen + headLen) / 2, 0, 0);
  else hit.position.set(0, (shaftLen + headLen) / 2, 0);

  group.add(shaft, head, hit);
  return finishHandle(group, meta);
}

/** Opaque XY plane square. */
function makePlaneHandle(color, size, meta) {
  const group = new THREE.Group();
  const fill = markVisual(
    new THREE.Mesh(new THREE.PlaneGeometry(size, size), fillMat(color)),
    color,
  );
  const half = size / 2;
  const rim = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-half, -half, 0.002),
      new THREE.Vector3(half, -half, 0.002),
      new THREE.Vector3(half, half, 0.002),
      new THREE.Vector3(-half, half, 0.002),
    ]),
    lineMat(0x1a1d23),
  );
  styleOverlay(rim);
  const hit = makeHit(new THREE.PlaneGeometry(size * 1.1, size * 1.1), meta);
  group.add(fill, rim, hit);
  group.position.set(size * 0.62, size * 0.62, 0.01);
  return finishHandle(group, meta);
}

/**
 * Opaque annular ring.
 * @param {number} radius outer radius
 * @param {number} color
 * @param {object} meta
 * @param {{ band?: number, hitPad?: number }} [opts] — room rings need a wider hit band
 */
function makeRotateRing(radius, color, meta, opts = {}) {
  const group = new THREE.Group();
  const band = Math.max(Number(opts.band) || 0.055, 0.04);
  const hitPad = Math.max(Number(opts.hitPad) || 0.04, 0.02);
  const inner = Math.max(radius - band, 0.08);
  const ring = markVisual(
    new THREE.Mesh(new THREE.RingGeometry(inner, radius, 72), fillMat(color)),
    color,
  );
  const outerRim = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(
      new THREE.EllipseCurve(0, 0, radius, radius, 0, Math.PI * 2, false, 0).getPoints(72),
    ),
    lineMat(0x1a1d23),
  );
  outerRim.position.z = 0.002;
  styleOverlay(outerRim);
  // Generous invisible hit annulus — thin visuals are otherwise nearly unclickable.
  const hitInner = Math.max(inner - hitPad, 0.05);
  const hitOuter = radius + hitPad;
  const hit = makeHit(new THREE.RingGeometry(hitInner, hitOuter, 64), meta);
  hit.position.z = 0.01;
  group.add(ring, outerRim, hit);
  return finishHandle(group, meta);
}

/**
 * Furniture: compact move/rotate at centre; scale discs at footprint edges.
 * Ring must not grow with the object — a large hit annulus blocked empty-click deselect.
 */
export function buildFurnitureGizmo(bounds, objectId) {
  const group = new THREE.Group();
  group.name = "edit_gizmos";
  const [cx, cy, cz] = bounds.center;
  const [sx, sy] = bounds.size;
  group.position.set(cx, cy, cz + HANDLE_Z);
  group.rotation.z = ((Number(bounds.rotation_z_deg) || 0) * Math.PI) / 180;

  const base = { target: "furniture", objectId, generator: bounds.generator || "" };
  const halfX = Math.max(Number(sx) || 0.2, 0.05) * 0.5;
  const halfY = Math.max(Number(sy) || 0.2, 0.05) * 0.5;
  // Cap rotate ring so big desks don't create a huge click-steal annulus.
  const ringR = Math.min(0.7, Math.max(0.42, Math.min(halfX, halfY) * 0.9));
  const scalePad = 0.16;
  const scaleX = Math.max(halfX + scalePad, ringR + 0.18);
  const scaleY = Math.max(halfY + scalePad, ringR + 0.18);

  group.add(
    makeArrow("x", MOVE_X, { ...base, kind: "move_axis", axis: "x", label: "move-x" }),
  );
  group.add(
    makeArrow("y", MOVE_Y, { ...base, kind: "move_axis", axis: "y", label: "move-y" }),
  );
  group.add(
    makePlaneHandle(MOVE_XY, 0.2, {
      ...base,
      kind: "move_axis",
      axis: "xy",
      label: "move-xy",
    }),
  );
  group.add(
    makeRotateRing(ringR, ROTATE, {
      ...base,
      kind: "rotate_z",
      label: "rotate-z",
    }, { band: 0.07, hitPad: 0.08 }),
  );

  for (const [axis, sign, x, y] of [
    ["x", 1, scaleX, 0],
    ["x", -1, -scaleX, 0],
    ["y", 1, 0, scaleY],
    ["y", -1, 0, -scaleY],
  ]) {
    const disc = makeDisc(SCALE, 0.1, {
      ...base,
      kind: "scale_axis",
      axis,
      sign,
      label: `scale-${axis}${sign > 0 ? "+" : "-"}`,
      startSizeX: sx,
      startSizeY: sy,
    });
    disc.position.set(x, y, 0);
    group.add(disc);
  }

  return group;
}

/**
 * Room: move + rotate at center; wall/corner discs outside footprint (rotated).
 */
export function buildRoomGizmo(room) {
  const group = new THREE.Group();
  group.name = "edit_gizmos";
  const rect = roomRect(room);
  if (!rect) return group;
  if (room.locked) return group;

  const { oz, w, d, rz } = rect;
  const roomId = room.room_id;
  const z = oz + HANDLE_Z;
  const [cx, cy] = roomLocalToWorld(rect, w * 0.5, d * 0.5);
  const base = { target: "room", roomId, roomRz: rz };

  const moveRoot = new THREE.Group();
  moveRoot.position.set(cx, cy, z);
  moveRoot.rotation.z = (rz * Math.PI) / 180;
  moveRoot.add(
    makeArrow("x", MOVE_X, { ...base, kind: "move_axis", axis: "x", label: "room-move-x" }),
  );
  moveRoot.add(
    makeArrow("y", MOVE_Y, { ...base, kind: "move_axis", axis: "y", label: "room-move-y" }),
  );
  moveRoot.add(
    makePlaneHandle(MOVE_XY, 0.22, {
      ...base,
      kind: "move_axis",
      axis: "xy",
      label: "room-move-xy",
    }),
  );
  const half = Math.max(w, d) * 0.5;
  // Inside wall discs; wide band so top-view picks are reliable on large rooms.
  const ringR = Math.max(half * 0.78, 0.9);
  moveRoot.add(
    makeRotateRing(
      ringR,
      ROTATE,
      {
        ...base,
        kind: "rotate_room_z",
        label: "room-rotate-z",
        startRotationZ: rz,
        ringRadius: ringR,
        ringBand: 0.2,
      },
      { band: 0.2, hitPad: 0.28 },
    ),
  );
  group.add(moveRoot);

  const walls = [
    { side: "south", lx: w * 0.5, ly: -OUTSET },
    { side: "north", lx: w * 0.5, ly: d + OUTSET },
    { side: "west", lx: -OUTSET, ly: d * 0.5 },
    { side: "east", lx: w + OUTSET, ly: d * 0.5 },
  ];
  for (const wall of walls) {
    const [x, y] = roomLocalToWorld(rect, wall.lx, wall.ly);
    const mesh = makeDisc(SCALE, 0.11, {
      ...base,
      kind: "wall",
      wallSide: wall.side,
      label: `${room.name || "room"}:${wall.side}`,
    });
    mesh.position.set(x, y, z);
    group.add(mesh);
  }

  const corners = [
    { corner: "sw", lx: -OUTSET * 0.7, ly: -OUTSET * 0.7 },
    { corner: "se", lx: w + OUTSET * 0.7, ly: -OUTSET * 0.7 },
    { corner: "nw", lx: -OUTSET * 0.7, ly: d + OUTSET * 0.7 },
    { corner: "ne", lx: w + OUTSET * 0.7, ly: d + OUTSET * 0.7 },
  ];
  for (const c of corners) {
    const [x, y] = roomLocalToWorld(rect, c.lx, c.ly);
    const mesh = makeDisc(CORNER, 0.12, {
      ...base,
      kind: "corner",
      corner: c.corner,
      label: `${room.name || "room"}:${c.corner}`,
    });
    mesh.position.set(x, y, z);
    group.add(mesh);
  }

  return group;
}

export function buildSelectionGizmos(exportData, selection) {
  if (!selection) {
    const empty = new THREE.Group();
    empty.name = "edit_gizmos";
    return empty;
  }
  if (selection.type === "furniture" && selection.objectId) {
    const bounds = furnitureBounds(exportData, selection.objectId);
    if (!bounds) {
      const empty = new THREE.Group();
      empty.name = "edit_gizmos";
      return empty;
    }
    return buildFurnitureGizmo(bounds, selection.objectId);
  }
  if (selection.type === "room" && selection.roomId) {
    const room = (exportData?.rooms || []).find((r) => r?.room_id === selection.roomId);
    if (!room) {
      const empty = new THREE.Group();
      empty.name = "edit_gizmos";
      return empty;
    }
    return buildRoomGizmo(room);
  }
  const empty = new THREE.Group();
  empty.name = "edit_gizmos";
  return empty;
}

export function isGizmoMesh(mesh) {
  return Boolean(mesh?.userData?.gizmo);
}

/**
 * Screen/world fallback when raycast misses a thin room rotate ring.
 * @returns {object | null} synthetic handle carrying gesture meta
 */
export function pickRoomRotateAnnulus(exportData, selection, floorHit) {
  if (!selection || selection.type !== "room" || !selection.roomId || !floorHit) return null;
  const room = (exportData?.rooms || []).find((r) => r?.room_id === selection.roomId);
  if (!room || room.locked) return null;
  const rect = roomRect(room);
  if (!rect) return null;
  const half = Math.max(rect.w, rect.d) * 0.5;
  const ringR = Math.max(half * 0.78, 0.9);
  const band = 0.2;
  const pad = 0.28;
  const [cx, cy] = roomLocalToWorld(rect, rect.w * 0.5, rect.d * 0.5);
  const dx = floorHit.x - cx;
  const dy = floorHit.y - cy;
  const dist = Math.hypot(dx, dy);
  const inner = Math.max(ringR - band - pad, 0.05);
  const outer = ringR + pad;
  if (dist < inner || dist > outer) return null;
  return {
    userData: {
      gizmo: true,
      gizmoHit: true,
      kind: "rotate_room_z",
      target: "room",
      roomId: selection.roomId,
      roomRz: rect.rz,
      startRotationZ: rect.rz,
      label: "room-rotate-z",
    },
  };
}

/**
 * Prefer dedicated hit meshes, then higher pickPriority (avoids rotate↔scale mixups).
 * @param {THREE.Intersection[]} hits
 * @returns {THREE.Object3D | null}
 */
export function resolveGizmoPick(hits) {
  if (!hits?.length) return null;
  const scored = hits
    .map((h) => h.object)
    .filter((o) => o?.userData?.gizmo)
    .map((o) => ({
      obj: o,
      hit: o.userData.gizmoHit ? 1 : 0,
      pri: Number(o.userData.pickPriority) || 0,
    }));
  if (!scored.length) return hits[0]?.object || null;
  scored.sort((a, b) => b.hit - a.hit || b.pri - a.pri);
  return scored[0].obj;
}

export function clearGizmoHover() {
  if (!hoveredRoot) return;
  hoveredRoot.traverse((o) => {
    if (!o.userData?.gizmoVisual || !o.material?.color) return;
    const base = o.userData.baseColor;
    if (base != null) o.material.color.setHex(base);
  });
  hoveredRoot = null;
}

/**
 * Highlight the handle under the cursor (brighten its visual meshes).
 * @param {THREE.Object3D | null} mesh
 */
export function setGizmoHover(mesh) {
  const root = mesh?.userData?.hoverRoot || (mesh?.userData?.gizmo ? mesh : null);
  if (root === hoveredRoot) return;
  clearGizmoHover();
  if (!root) return;
  hoveredRoot = root;
  root.traverse((o) => {
    if (!o.userData?.gizmoVisual || !o.material?.color) return;
    o.material.color.setHex(HOVER_TINT);
  });
}

export function resizeParamsForAxis(generator, axis, startSize, delta) {
  const g = String(generator || "").toLowerCase();
  const size = Math.max(0.25, (axis === "x" ? startSize[0] : startSize[1]) + delta);
  const rounded = Number(size.toFixed(4));
  // bed_basic: length = X extent, width = Y extent (see bed_basic.md).
  if (g.includes("bed")) {
    return axis === "x" ? { length: rounded } : { width: rounded };
  }
  if (axis === "x") {
    return { width: rounded };
  }
  return { depth: rounded };
}

/** Opposite local edge stays fixed when dragging a scale handle (room-like). */
export function resizeAnchorForHandle(axis, sign) {
  if (axis === "x") return Number(sign) >= 0 ? "min_x" : "max_x";
  return Number(sign) >= 0 ? "min_y" : "max_y";
}

export function roomMoveCommand(roomId, dx, dy) {
  return { action: "move_room", room_id: roomId, dx, dy };
}

export function roomRotateCommand(roomId, degrees) {
  return { action: "rotate_room", room_id: roomId, degrees };
}

export function resizeCommand(objectId, params, { anchor } = {}) {
  const cmd = { action: "resize", object_id: objectId, params };
  if (anchor) cmd.anchor = anchor;
  return cmd;
}
