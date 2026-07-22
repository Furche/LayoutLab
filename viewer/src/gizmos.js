/**
 * Selection-based transform gizmos (FC-001):
 * Flat 2D overlay look (arrows / ring / discs) in the Blender XY plane.
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
const HANDLE_Z = 0.08;
const OUTSET = 0.14;
const GIZMO_RENDER_ORDER = 1000;

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
  if (w <= 0 || d <= 0) return null;
  return { ox, oy, oz, w, d, h };
}

/**
 * Union AABB of furniture parts for object_id (skip clearances).
 * @returns {{ min: number[], max: number[], center: number[], size: number[] } | null}
 */
export function furnitureBounds(exportData, objectId) {
  const objects = Array.isArray(exportData?.objects) ? exportData.objects : [];
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;
  let generator = "";
  for (const o of objects) {
    const id = o?.layoutlab?.object_id || o?.custom_properties?.layoutlab_object_id;
    if (id !== objectId) continue;
    const role = o?.layoutlab?.role || o?.custom_properties?.layoutlab_role || "";
    if (role === "clearance") continue;
    if (!generator) generator = o?.layoutlab?.generator || "";
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
    } else if (Array.isArray(o.location) && Array.isArray(o.dimensions)) {
      const x = Number(o.location[0]) || 0;
      const y = Number(o.location[1]) || 0;
      const z = Number(o.location[2]) || 0;
      const dx = Math.max(Number(o.dimensions[0]) || 0.01, 0.01);
      const dy = Math.max(Number(o.dimensions[1]) || 0.01, 0.01);
      const dz = Math.max(Number(o.dimensions[2]) || 0.01, 0.01);
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      minZ = Math.min(minZ, z);
      maxX = Math.max(maxX, x + dx);
      maxY = Math.max(maxY, y + dy);
      maxZ = Math.max(maxZ, z + dz);
    }
  }
  if (!Number.isFinite(minX)) return null;
  return {
    min: [minX, minY, minZ],
    max: [maxX, maxY, maxZ],
    center: [(minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2],
    size: [maxX - minX, maxY - minY, maxZ - minZ],
    generator,
  };
}

function fillMat(color, opts = {}) {
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: opts.opacity ?? 0.92,
    depthTest: false,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}

function lineMat(color, opts = {}) {
  return new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: opts.opacity ?? 1,
    depthTest: false,
    depthWrite: false,
  });
}

function styleOverlay(obj) {
  obj.renderOrder = GIZMO_RENDER_ORDER;
  obj.frustumCulled = false;
  return obj;
}

function tag(mesh, meta) {
  mesh.userData = { gizmo: true, ...meta };
  mesh.name = meta.label || meta.kind || "gizmo";
  return styleOverlay(mesh);
}

function invisibleHit(geo) {
  const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ visible: false }));
  styleOverlay(mesh);
  return mesh;
}

/** Flat disc in XY (scale / wall / corner handles). */
function makeDisc(color, radius, meta, opts = {}) {
  const group = new THREE.Group();
  const fill = new THREE.Mesh(
    new THREE.CircleGeometry(radius, 28),
    fillMat(color, { opacity: opts.fillOpacity ?? 0.88 }),
  );
  const rim = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(
      new THREE.EllipseCurve(0, 0, radius, radius, 0, Math.PI * 2, false, 0).getPoints(40),
    ),
    lineMat(0xffffff, { opacity: 0.55 }),
  );
  rim.position.z = 0.002;
  const hit = invisibleHit(new THREE.CircleGeometry(radius * 1.55, 16));
  group.add(fill, rim, hit);
  tag(group, meta);
  group.traverse((o) => {
    if (o.isMesh || o.isLine) o.userData = { ...group.userData };
  });
  return group;
}

/** Flat 2D arrow along Blender +X or +Y. */
function makeArrow(axis, color, meta) {
  const group = new THREE.Group();
  const shaftLen = 0.48;
  const shaftW = 0.045;
  const headLen = 0.16;
  const headW = 0.13;

  const shaft = new THREE.Mesh(
    new THREE.PlaneGeometry(axis === "x" ? shaftLen : shaftW, axis === "x" ? shaftW : shaftLen),
    fillMat(color),
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
  const head = new THREE.Mesh(new THREE.ShapeGeometry(headShape), fillMat(color));
  if (axis === "x") head.position.set(shaftLen, 0, 0.001);
  else head.position.set(0, shaftLen, 0.001);

  const hit = invisibleHit(
    axis === "x"
      ? new THREE.PlaneGeometry(shaftLen + headLen + 0.08, 0.28)
      : new THREE.PlaneGeometry(0.28, shaftLen + headLen + 0.08),
  );
  if (axis === "x") hit.position.set((shaftLen + headLen) / 2, 0, 0);
  else hit.position.set(0, (shaftLen + headLen) / 2, 0);

  group.add(shaft, head, hit);
  tag(group, meta);
  group.traverse((o) => {
    if (o.isMesh) o.userData = { ...group.userData };
  });
  return group;
}

/** Flat XY plane square between the move arrows. */
function makePlaneHandle(color, size, meta) {
  const group = new THREE.Group();
  const fill = new THREE.Mesh(
    new THREE.PlaneGeometry(size, size),
    fillMat(color, { opacity: 0.45 }),
  );
  const half = size / 2;
  const rim = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-half, -half, 0.002),
      new THREE.Vector3(half, -half, 0.002),
      new THREE.Vector3(half, half, 0.002),
      new THREE.Vector3(-half, half, 0.002),
    ]),
    lineMat(color, { opacity: 0.95 }),
  );
  const hit = invisibleHit(new THREE.PlaneGeometry(size * 1.25, size * 1.25));
  group.add(fill, rim, hit);
  group.position.set(size * 0.55, size * 0.55, 0.01);
  tag(group, meta);
  group.traverse((o) => {
    if (o.isMesh || o.isLine) o.userData = { ...group.userData };
  });
  return group;
}

/** Flat annular ring for Z rotation. */
function makeRotateRing(radius, color, meta) {
  const group = new THREE.Group();
  const inner = Math.max(radius - 0.04, radius * 0.88);
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(inner, radius, 64),
    fillMat(color, { opacity: 0.75 }),
  );
  const outerRim = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(
      new THREE.EllipseCurve(0, 0, radius, radius, 0, Math.PI * 2, false, 0).getPoints(64),
    ),
    lineMat(0xffffff, { opacity: 0.4 }),
  );
  outerRim.position.z = 0.002;
  const hit = invisibleHit(new THREE.RingGeometry(Math.max(inner - 0.08, 0.05), radius + 0.1, 48));
  group.add(ring, outerRim, hit);
  tag(group, meta);
  group.traverse((o) => {
    if (o.isMesh || o.isLine) o.userData = { ...group.userData };
  });
  return group;
}

/**
 * Furniture: move arrows + rotate ring + scale discs at ±X / ±Y.
 * @param {object} bounds from furnitureBounds
 * @param {string} objectId
 */
export function buildFurnitureGizmo(bounds, objectId) {
  const group = new THREE.Group();
  group.name = "edit_gizmos";
  const [cx, cy, cz] = bounds.center;
  const [sx, sy] = bounds.size;
  const z = cz + HANDLE_Z;
  group.position.set(cx, cy, z);

  const base = { target: "furniture", objectId, generator: bounds.generator || "" };

  group.add(
    makeArrow("x", MOVE_X, {
      ...base,
      kind: "move_axis",
      axis: "x",
      label: "move-x",
    }),
  );
  group.add(
    makeArrow("y", MOVE_Y, {
      ...base,
      kind: "move_axis",
      axis: "y",
      label: "move-y",
    }),
  );
  group.add(
    makePlaneHandle(MOVE_XY, 0.22, {
      ...base,
      kind: "move_axis",
      axis: "xy",
      label: "move-xy",
    }),
  );

  const ringR = Math.max(Math.max(sx, sy) * 0.45, 0.45);
  group.add(
    makeRotateRing(ringR, ROTATE, {
      ...base,
      kind: "rotate_z",
      label: "rotate-z",
    }),
  );

  const hx = Math.max(sx * 0.5 + 0.05, 0.35);
  const hy = Math.max(sy * 0.5 + 0.05, 0.35);
  for (const [axis, sign, x, y] of [
    ["x", 1, hx, 0],
    ["x", -1, -hx, 0],
    ["y", 1, 0, hy],
    ["y", -1, 0, -hy],
  ]) {
    const b = makeDisc(SCALE, 0.09, {
      ...base,
      kind: "scale_axis",
      axis,
      sign,
      label: `scale-${axis}${sign > 0 ? "+" : "-"}`,
      startSizeX: sx,
      startSizeY: sy,
    });
    b.position.set(x, y, 0);
    group.add(b);
  }

  return group;
}

/**
 * Room: move arrows at center + wall/corner discs.
 * @param {object} room
 */
export function buildRoomGizmo(room) {
  const group = new THREE.Group();
  group.name = "edit_gizmos";
  const rect = roomRect(room);
  if (!rect) return group;
  if (room.locked) return group;

  const { ox, oy, oz, w, d } = rect;
  const roomId = room.room_id;
  const z = oz + HANDLE_Z;
  const cx = ox + w * 0.5;
  const cy = oy + d * 0.5;

  const moveRoot = new THREE.Group();
  moveRoot.position.set(cx, cy, z);
  const base = { target: "room", roomId };

  moveRoot.add(
    makeArrow("x", MOVE_X, { ...base, kind: "move_axis", axis: "x", label: "room-move-x" }),
  );
  moveRoot.add(
    makeArrow("y", MOVE_Y, { ...base, kind: "move_axis", axis: "y", label: "room-move-y" }),
  );
  moveRoot.add(
    makePlaneHandle(MOVE_XY, 0.24, {
      ...base,
      kind: "move_axis",
      axis: "xy",
      label: "room-move-xy",
    }),
  );
  group.add(moveRoot);

  const walls = [
    { side: "south", x: ox + w * 0.5, y: oy - OUTSET },
    { side: "north", x: ox + w * 0.5, y: oy + d + OUTSET },
    { side: "west", x: ox - OUTSET, y: oy + d * 0.5 },
    { side: "east", x: ox + w + OUTSET, y: oy + d * 0.5 },
  ];
  for (const wall of walls) {
    const mesh = makeDisc(SCALE, 0.1, {
      ...base,
      kind: "wall",
      wallSide: wall.side,
      label: `${room.name || "room"}:${wall.side}`,
    });
    mesh.position.set(wall.x, wall.y, z);
    group.add(mesh);
  }

  const corners = [
    { corner: "sw", x: ox - OUTSET * 0.6, y: oy - OUTSET * 0.6 },
    { corner: "se", x: ox + w + OUTSET * 0.6, y: oy - OUTSET * 0.6 },
    { corner: "nw", x: ox - OUTSET * 0.6, y: oy + d + OUTSET * 0.6 },
    { corner: "ne", x: ox + w + OUTSET * 0.6, y: oy + d + OUTSET * 0.6 },
  ];
  for (const c of corners) {
    const mesh = makeDisc(CORNER, 0.11, {
      ...base,
      kind: "corner",
      corner: c.corner,
      label: `${room.name || "room"}:${c.corner}`,
    });
    mesh.position.set(c.x, c.y, z);
    group.add(mesh);
  }

  return group;
}

/**
 * @param {object} exportData
 * @param {{ type: 'furniture'|'room', objectId?: string, roomId?: string } | null} selection
 */
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

/** Map furniture scale axis drag to resize params. */
export function resizeParamsForAxis(generator, axis, startSize, delta) {
  const g = String(generator || "").toLowerCase();
  const size = Math.max(0.25, (axis === "x" ? startSize[0] : startSize[1]) + delta);
  if (axis === "x") {
    return { width: Number(size.toFixed(4)) };
  }
  // Y axis
  if (g.includes("bed")) {
    return { length: Number(size.toFixed(4)) };
  }
  return { depth: Number(size.toFixed(4)) };
}

export function roomMoveCommand(roomId, dx, dy) {
  return { action: "move_room", room_id: roomId, dx, dy };
}

export function resizeCommand(objectId, params) {
  return { action: "resize", object_id: objectId, params };
}
