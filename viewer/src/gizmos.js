/**
 * Visible room edit gizmos (wall + corner handles) for Viewer Move mode (FC-001 §3).
 * Positions are Blender Z-up (parented under the scene world root).
 */

import * as THREE from "three";

const WALL_COLOR = 0x5b9fd4;
const CORNER_COLOR = 0xe5c07b;
const HANDLE_Z = 0.08;
const OUTSET = 0.14;

/**
 * @param {object} room export room block
 * @returns {{ ox: number, oy: number, oz: number, w: number, d: number, h: number } | null}
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

function makeHandleMesh(color, radius, meta) {
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 18, 14),
    new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.35,
      roughness: 0.45,
      metalness: 0.1,
      depthTest: true,
    }),
  );
  mesh.name = meta.label || "handle";
  mesh.userData = {
    gizmo: true,
    ...meta,
  };
  return mesh;
}

/**
 * @param {object} exportData
 * @param {{ roomId?: string | null }} [opts]
 * @returns {THREE.Group}
 */
export function buildRoomGizmos(exportData, opts = {}) {
  const group = new THREE.Group();
  group.name = "edit_gizmos";
  const rooms = Array.isArray(exportData?.rooms) ? exportData.rooms : [];
  const filterId = opts.roomId || null;

  for (const room of rooms) {
    if (filterId && room.room_id !== filterId) continue;
    if (room.locked) continue;
    const rect = roomRect(room);
    if (!rect) continue;
    const { ox, oy, oz, w, d } = rect;
    const z = oz + HANDLE_Z;
    const roomId = room.room_id;

    const walls = [
      { side: "south", x: ox + w * 0.5, y: oy - OUTSET },
      { side: "north", x: ox + w * 0.5, y: oy + d + OUTSET },
      { side: "west", x: ox - OUTSET, y: oy + d * 0.5 },
      { side: "east", x: ox + w + OUTSET, y: oy + d * 0.5 },
    ];
    for (const wall of walls) {
      const mesh = makeHandleMesh(WALL_COLOR, 0.11, {
        kind: "wall",
        roomId,
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
      const mesh = makeHandleMesh(CORNER_COLOR, 0.13, {
        kind: "corner",
        roomId,
        corner: c.corner,
        label: `${room.name || "room"}:${c.corner}`,
      });
      mesh.position.set(c.x, c.y, z);
      group.add(mesh);
    }
  }

  return group;
}

export function isGizmoMesh(mesh) {
  return Boolean(mesh?.userData?.gizmo);
}
