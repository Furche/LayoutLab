/**
 * Viewer direct manipulation against Core preview/commit (DD-018 / DD-019).
 * Move = room XY drag; Rotate = horizontal drag → absolute Z degrees.
 */

import * as THREE from "three";

const NON_FURNITURE_ROLES = new Set([
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
 * @returns {boolean}
 */
export function isManipulableMesh(mesh) {
  const ud = mesh?.userData || {};
  if (!ud.object_id) return false;
  if (NON_FURNITURE_ROLES.has(ud.role)) return false;
  return true;
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
    name: main.name || objectId,
  };
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

  // Plane in Blender local space: z = planeZ (normal +Z).
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

export function rotateCommand(objectId, degrees) {
  return {
    action: "rotate_z",
    object_id: objectId,
    degrees,
    absolute: true,
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
