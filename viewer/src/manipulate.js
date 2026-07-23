/**
 * Viewer direct manipulation against Core preview/commit (DD-018 / DD-019).
 * Move = furniture XY or wall parallel drag; Rotate = furniture Z degrees.
 */

import * as THREE from "three";
import { footprintSizeFromObject } from "./gizmos.js";

const ROOM_FABRIC_ROLES = new Set([
  "room_floor",
  "room_wall",
  "room_opening",
  "room_fixed",
  "label",
]);

const MOVE_THROTTLE_MS = 120;
const ROTATE_DEG_PER_PX = 0.45;

/**
 * @param {THREE.Object3D | null | undefined} mesh
 */
export function isFurnitureMesh(mesh) {
  const ud = mesh?.userData || {};
  if (!ud.object_id) return false;
  if (ROOM_FABRIC_ROLES.has(ud.role)) return false;
  if (ud.role === "clearance") return true; // same object_id as furniture
  return true;
}

/**
 * @param {THREE.Object3D | null | undefined} mesh
 */
export function isWallMesh(mesh) {
  return mesh?.userData?.role === "room_wall" && Boolean(mesh.userData.wall_side);
}

/**
 * @param {THREE.Object3D | null | undefined} mesh
 * @param {"orbit"|"move"|"rotate"} editMode
 */
export function isManipulableMesh(mesh, editMode = "move") {
  if (isFurnitureMesh(mesh)) return true;
  if (editMode === "move" && isWallMesh(mesh)) return true;
  return false;
}

/**
 * Prefer a solid furniture mesh for a given object_id (skip clearance wires).
 * @param {THREE.Object3D[]} meshes
 * @param {string} objectId
 */
export function findMeshForObjectId(meshes, objectId) {
  if (!objectId) return null;
  const list = meshes.filter((m) => m?.userData?.object_id === objectId);
  return (
    list.find((m) => m.userData.role !== "clearance") || list[0] || null
  );
}

/**
 * @param {THREE.Object3D[]} meshes
 * @param {string} roomId
 * @param {string} wallSide
 */
export function findWallMesh(meshes, roomId, wallSide) {
  if (!roomId || !wallSide) return null;
  const side = String(wallSide).toLowerCase();
  return (
    meshes.find(
      (m) =>
        m?.userData?.role === "room_wall" &&
        m.userData.room_id === roomId &&
        String(m.userData.wall_side || "").toLowerCase() === side,
    ) || null
  );
}

/**
 * @param {object} exportData
 * @param {string} objectId
 */
export function poseFromExport(exportData, objectId) {
  const objects = Array.isArray(exportData?.objects) ? exportData.objects : [];
  const matches = objects.filter(
    (o) =>
      (o?.layoutlab?.object_id || o?.custom_properties?.layoutlab_object_id) ===
      objectId,
  );
  if (!matches.length) return null;
  const main =
    matches.find((o) => {
      const role = o?.layoutlab?.role || o?.custom_properties?.layoutlab_role;
      return role && role !== "clearance";
    }) || matches[0];
  const loc = main.location || [0, 0, 0];
  const rz =
    main.rotation_euler_deg?.[2] ??
    main.layoutlab?.rotation_z_deg ??
    0;
  return {
    location: [Number(loc[0]) || 0, Number(loc[1]) || 0, Number(loc[2]) || 0],
    rotation_z_deg: Number(rz) || 0,
    validity: main.layoutlab?.validity || null,
    support_ref: main.layoutlab?.support_ref || null,
    name: main.name || objectId,
  };
}

/**
 * Outward-positive delta for move_wall from a floor-plane drag (dx, dy in Blender XY).
 * @param {string} wallSide
 * @param {number} dx
 * @param {number} dy
 */
export function wallDeltaFromDrag(wallSide, dx, dy, roomRzDeg = 0) {
  // Project world drag into room-local axes when the room is rotated.
  const r = (-Number(roomRzDeg || 0) * Math.PI) / 180;
  const c = Math.cos(r);
  const s = Math.sin(r);
  const lx = dx * c - dy * s;
  const ly = dx * s + dy * c;
  const side = String(wallSide || "").toLowerCase();
  if (side === "north") return ly;
  if (side === "south") return -ly;
  if (side === "east") return lx;
  if (side === "west") return -lx;
  return 0;
}

/**
 * Intersect a horizontal Blender floor plane (z = planeZ) under the Z-up root.
 * @returns {{ x: number, y: number, z: number } | null}
 */
export function hitBlenderFloorXY(raycaster, camera, sceneRoot, clientX, clientY, domElement, planeZ = 0) {
  if (!sceneRoot || !domElement) return null;
  const rect = domElement.getBoundingClientRect();
  if (rect.width < 1 || rect.height < 1) return null;
  const ndc = new THREE.Vector2(
    ((clientX - rect.left) / rect.width) * 2 - 1,
    -((clientY - rect.top) / rect.height) * 2 + 1,
  );
  raycaster.setFromCamera(ndc, camera);

  const localPoint = new THREE.Vector3(0, 0, planeZ);
  const localNormal = new THREE.Vector3(0, 0, 1);
  sceneRoot.localToWorld(localPoint);
  const worldNormal = localNormal
    .clone()
    .transformDirection(sceneRoot.matrixWorld)
    .normalize();
  const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(worldNormal, localPoint);
  const hit = new THREE.Vector3();
  if (!raycaster.ray.intersectPlane(plane, hit)) return null;
  const local = sceneRoot.worldToLocal(hit.clone());
  return { x: local.x, y: local.y, z: local.z };
}

export function moveCommand(objectId, location) {
  return {
    action: "move",
    object_id: objectId,
    location: [location[0], location[1], location[2] ?? 0],
  };
}

export function placeOnCommand(objectId, hostObjectId, surfaceId, location) {
  const cmd = {
    action: "place_on",
    object_id: objectId,
    host_object_id: hostObjectId,
    surface_id: surfaceId || "surface_top",
  };
  if (location) {
    cmd.location = [location[0], location[1], location[2] ?? 0];
  }
  return cmd;
}

export function setSupportCommand(objectId, supportRef) {
  return {
    action: "set_support",
    object_id: objectId,
    support_ref: supportRef || "room_floor",
  };
}

/** Default XY margin (m) for magnet snap onto host surfaces. */
export const MAGNET_MARGIN_M = 0.08;

function _rotateZ(x, y, deg) {
  const r = (Number(deg) || 0) * (Math.PI / 180);
  const c = Math.cos(r);
  const s = Math.sin(r);
  return [x * c - y * s, x * s + y * c];
}

function _worldToHostLocal(hostLoc, hostRz, worldXY) {
  const wx = Number(worldXY[0]) - Number(hostLoc[0] || 0);
  const wy = Number(worldXY[1]) - Number(hostLoc[1] || 0);
  return _rotateZ(wx, wy, -(Number(hostRz) || 0));
}

/**
 * Collect host surfaces from export (main parts with layoutlab.surfaces).
 * @param {object} exportData
 * @returns {Array<{hostId:string, surface:object, location:number[], rz:number, name:string}>}
 */
export function listHostSurfaces(exportData) {
  const objects = Array.isArray(exportData?.objects) ? exportData.objects : [];
  const out = [];
  const seen = new Set();
  for (const o of objects) {
    const hostId = o?.layoutlab?.object_id || o?.custom_properties?.layoutlab_object_id;
    if (!hostId || seen.has(hostId)) continue;
    const partType = o?.layoutlab?.part_type || o?.custom_properties?.layoutlab_part_type;
    const surfaces = o?.layoutlab?.surfaces;
    if (!Array.isArray(surfaces) || !surfaces.length) continue;
    if (partType && partType !== "main") continue;
    seen.add(hostId);
    const loc = o.location || [0, 0, 0];
    const rz = o.rotation_euler_deg?.[2] ?? o.layoutlab?.rotation_z_deg ?? 0;
    for (const surface of surfaces) {
      if (!surface?.id) continue;
      out.push({
        hostId,
        surface,
        location: [Number(loc[0]) || 0, Number(loc[1]) || 0, Number(loc[2]) || 0],
        rz: Number(rz) || 0,
        name: o.name || hostId,
      });
    }
  }
  return out;
}

/**
 * Find magnet host under a world XY sample point (typically furniture footprint centre).
 * Prefers the highest surface Z when several overlap.
 * @returns {{ hostId: string, surfaceId: string, worldZ: number, localXy: number[], hostName: string } | null}
 */
export function findMagnetHost(exportData, worldXY, { excludeObjectId = null, margin = MAGNET_MARGIN_M } = {}) {
  const hosts = listHostSurfaces(exportData);
  let best = null;
  for (const h of hosts) {
    if (excludeObjectId && h.hostId === excludeObjectId) continue;
    const [lx, ly] = _worldToHostLocal(h.location, h.rz, worldXY);
    const mn = h.surface.local_min_xy || [0, 0];
    const mx = h.surface.local_max_xy || [0, 0];
    const m = Number(margin) || 0;
    if (
      lx < Number(mn[0]) - m ||
      ly < Number(mn[1]) - m ||
      lx > Number(mx[0]) + m ||
      ly > Number(mx[1]) + m
    ) {
      continue;
    }
    const worldZ = Number(h.location[2] || 0) + Number(h.surface.local_z || 0);
    if (!best || worldZ >= best.worldZ) {
      best = {
        hostId: h.hostId,
        surfaceId: String(h.surface.id),
        worldZ,
        localXy: [lx, ly],
        hostName: h.name,
      };
    }
  }
  return best;
}

/**
 * Footprint centre from min-corner location + half extents (approx from export dims).
 */
export function footprintCentreFromPose(pose, halfX = 0.1, halfY = 0.1) {
  const loc = pose?.location || [0, 0, 0];
  const rz = pose?.rotation_z_deg || 0;
  const [ox, oy] = _rotateZ(halfX, halfY, rz);
  return [Number(loc[0]) + ox, Number(loc[1]) + oy, Number(loc[2]) || 0];
}

export function furnitureHalfXyFromExport(exportData, objectId) {
  const objects = Array.isArray(exportData?.objects) ? exportData.objects : [];
  const main =
    objects.find(
      (o) =>
        (o?.layoutlab?.object_id || o?.custom_properties?.layoutlab_object_id) === objectId &&
        (o?.layoutlab?.part_type === "main" ||
          o?.custom_properties?.layoutlab_part_type === "main"),
    ) ||
    objects.find(
      (o) => (o?.layoutlab?.object_id || o?.custom_properties?.layoutlab_object_id) === objectId,
    );
  if (!main) return [0.1, 0.1];
  const [sx, sy] = footprintSizeFromObject(main);
  return [sx * 0.5, sy * 0.5];
}

export function rotateCommand(objectId, degrees) {
  return {
    action: "rotate_z",
    object_id: objectId,
    degrees,
    absolute: true,
  };
}

export function wallMoveCommand(roomId, wallSide, delta) {
  return {
    action: "move_wall",
    room_id: roomId,
    wall_side: wallSide,
    delta,
  };
}

export function cornerMoveCommand(roomId, corner, dx, dy) {
  return {
    action: "move_corner",
    room_id: roomId,
    corner,
    dx,
    dy,
  };
}

/**
 * @param {object} api
 * @param {(path: string, body?: object) => Promise<object>} api.post
 */
export function createPreviewClient(api) {
  let active = false;
  let inflight = Promise.resolve();

  function enqueue(fn) {
    inflight = inflight.then(fn, fn);
    return inflight;
  }

  return {
    get active() {
      return active;
    },
    begin(commands, description = "viewer gesture") {
      return enqueue(async () => {
        if (active) {
          await api.post("/v1/preview/cancel", {});
          active = false;
        }
        const result = await api.post("/v1/preview/begin", {
          commands: commands || [],
          actor: "user",
          description,
        });
        active = Boolean(result?.ok && result?.preview);
        return result;
      });
    },
    update(commands) {
      return enqueue(async () => {
        if (!active) {
          return { ok: false, error: "no active preview" };
        }
        return api.post("/v1/preview/update", { commands });
      });
    },
    commit(description = "viewer gesture") {
      return enqueue(async () => {
        if (!active) {
          return { ok: false, error: "no active preview" };
        }
        const result = await api.post("/v1/preview/commit", {
          action: "gesture",
          description,
        });
        if (result?.ok) active = false;
        return result;
      });
    },
    cancel() {
      return enqueue(async () => {
        if (!active) {
          return { ok: true, cancelled: false, preview: false };
        }
        const result = await api.post("/v1/preview/cancel", {});
        active = false;
        return result;
      });
    },
    resetLocal() {
      active = false;
    },
  };
}

export { MOVE_THROTTLE_MS, ROTATE_DEG_PER_PX };
