/**
 * Build Three.js meshes from a LayoutLab viewer export (json_protocol §6.4).
 * Blender coords (Z-up) live under a root group rotated -90° about X → Three Y-up.
 *
 * Placement prefers world_bbox_corners (AABB) or viewer.mesh (world verts).
 * Never treat object.location as an AABB min corner — that is the origin and may be parent-local.
 */

import * as THREE from "three";

const ROLE_COLORS = {
  room_floor: 0x3a4554,
  room_wall: 0x9aa7b8,
  room_opening: 0x61afef,
  room_fixed: 0x7a6a58,
  clearance: 0xe5c07b,
  bed_frame: 0xc4a574,
  bed_mattress: 0xd4c4a8,
  desk_body: 0x8b7355,
  desk_top: 0xc4a574,
  desk_leg: 0x8b7355,
  default: 0xa0a8b4,
};

const SKIP_ROLES = new Set(["label"]);

export function createWorldRoot() {
  const root = new THREE.Group();
  root.name = "blender_z_up";
  root.rotation.x = -Math.PI / 2;
  return root;
}

export function clearGroup(group) {
  while (group.children.length) {
    const child = group.children[0];
    group.remove(child);
    child.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
        else obj.material.dispose();
      }
    });
  }
}

function roleOf(obj) {
  return (
    obj?.layoutlab?.role ||
    obj?.custom_properties?.layoutlab_role ||
    "default"
  );
}

function colorFor(role) {
  return ROLE_COLORS[role] ?? ROLE_COLORS.default;
}

/** @returns {{ min: number[], size: number[] } | null} */
export function aabbFromExportObject(obj) {
  const corners = obj?.world_bbox_corners;
  if (Array.isArray(corners) && corners.length >= 2) {
    let minX = Infinity;
    let minY = Infinity;
    let minZ = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    let maxZ = -Infinity;
    for (const c of corners) {
      if (!c || c.length < 3) continue;
      const x = Number(c[0]);
      const y = Number(c[1]);
      const z = Number(c[2]);
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (z < minZ) minZ = z;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
      if (z > maxZ) maxZ = z;
    }
    if (!Number.isFinite(minX)) return null;
    return {
      min: [minX, minY, minZ],
      size: [
        Math.max(maxX - minX, 0.001),
        Math.max(maxY - minY, 0.001),
        Math.max(maxZ - minZ, 0.001),
      ],
    };
  }
  // Last resort: dimensions only, anchored at world location (still better than local origin).
  const loc = obj?.location || [0, 0, 0];
  const dims = obj?.dimensions || [1, 1, 1];
  return {
    min: [Number(loc[0]) || 0, Number(loc[1]) || 0, Number(loc[2]) || 0],
    size: [
      Math.max(Number(dims[0]) || 0.001, 0.001),
      Math.max(Number(dims[1]) || 0.001, 0.001),
      Math.max(Number(dims[2]) || 0.001, 0.001),
    ],
  };
}

function boxMeshFromAabb(aabb, color, opts = {}) {
  const [dx, dy, dz] = aabb.size;
  const geo = new THREE.BoxGeometry(dx, dy, dz);
  let mesh;
  if (opts.wire) {
    const edges = new THREE.EdgesGeometry(geo);
    geo.dispose();
    mesh = new THREE.LineSegments(
      edges,
      new THREE.LineBasicMaterial({
        color,
        transparent: true,
        opacity: opts.opacity ?? 0.9,
        depthWrite: false,
      }),
    );
  } else {
    mesh = new THREE.Mesh(
      geo,
      new THREE.MeshStandardMaterial({
        color,
        roughness: 0.85,
        metalness: 0.05,
        transparent: Boolean(opts.opacity && opts.opacity < 1),
        opacity: opts.opacity ?? 1,
        side: opts.doubleSide ? THREE.DoubleSide : THREE.FrontSide,
      }),
    );
  }
  mesh.position.set(aabb.min[0] + dx / 2, aabb.min[1] + dy / 2, aabb.min[2] + dz / 2);
  return mesh;
}

function quadMesh(corners, color) {
  if (!corners || corners.length < 4) return null;
  const positions = new Float32Array(12);
  for (let i = 0; i < 4; i++) {
    positions[i * 3] = corners[i][0];
    positions[i * 3 + 1] = corners[i][1];
    positions[i * 3 + 2] = corners[i][2];
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setIndex([0, 1, 2, 0, 2, 3]);
  geo.computeVertexNormals();
  return new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({
      color,
      roughness: 0.9,
      metalness: 0.02,
      side: THREE.FrontSide,
      flatShading: true,
    }),
  );
}

function meshFromViewer(viewer, color, opts = {}) {
  const verts = viewer?.vertices;
  const faces = viewer?.faces;
  if (!Array.isArray(verts) || !Array.isArray(faces) || verts.length < 3 || faces.length < 1) {
    return null;
  }
  const positions = new Float32Array(verts.length * 3);
  for (let i = 0; i < verts.length; i++) {
    positions[i * 3] = Number(verts[i][0]) || 0;
    positions[i * 3 + 1] = Number(verts[i][1]) || 0;
    positions[i * 3 + 2] = Number(verts[i][2]) || 0;
  }
  const indices = [];
  for (const face of faces) {
    if (!face || face.length < 3) continue;
    indices.push(face[0], face[1], face[2]);
  }
  if (!indices.length) return null;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({
      color,
      roughness: 0.8,
      metalness: 0.05,
      flatShading: true,
      transparent: Boolean(opts.opacity && opts.opacity < 1),
      opacity: opts.opacity ?? 1,
      side: THREE.DoubleSide,
    }),
  );
}

/**
 * @returns {{ root: THREE.Group, layers: { clearances: THREE.Group, openings: THREE.Group } }}
 */
export function buildSceneFromExport(data) {
  const root = createWorldRoot();
  const clearances = new THREE.Group();
  clearances.name = "clearances";
  const openings = new THREE.Group();
  openings.name = "openings";
  const solids = new THREE.Group();
  solids.name = "solids";
  root.add(solids, clearances, openings);

  const objects = Array.isArray(data?.objects) ? data.objects : [];
  for (const obj of objects) {
    if (obj.visible === false) continue;
    if (obj.type === "FONT" || obj.type === "EMPTY") continue;
    const role = roleOf(obj);
    if (SKIP_ROLES.has(role)) continue;

    const color = colorFor(role);
    const viewer = obj.viewer || {};
    const displayWire = viewer.display === "wire" || role === "clearance" || role === "room_opening";

    let mesh = null;
    if (viewer.primitive === "quad" && viewer.corners) {
      mesh = quadMesh(viewer.corners, color);
    } else if (!displayWire && viewer.primitive === "mesh") {
      mesh = meshFromViewer(viewer, color, {
        opacity: role === "room_floor" ? 0.95 : 1,
      });
    }

    if (!mesh) {
      const aabb = aabbFromExportObject(obj);
      if (!aabb) continue;
      mesh = boxMeshFromAabb(aabb, color, {
        wire: displayWire,
        opacity: displayWire ? (role === "clearance" ? 0.85 : 0.7) : role === "room_floor" ? 0.95 : 1,
      });
    }

    mesh.name = obj.name || role;
    mesh.userData = {
      role,
      object_id: obj.layoutlab?.object_id || obj.custom_properties?.layoutlab_object_id || "",
      clearance_name:
        obj.layoutlab?.clearance?.clearance_name ||
        obj.custom_properties?.layoutlab_clearance_name ||
        "",
      exportName: obj.name || "",
      baseColor: color,
    };

    if (role === "clearance") clearances.add(mesh);
    else if (role === "room_opening") openings.add(mesh);
    else solids.add(mesh);
  }

  const grid = new THREE.GridHelper(12, 12, 0x3a4554, 0x2a3340);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = -0.01;
  root.add(grid);

  return { root, layers: { clearances, openings, solids } };
}

export function fitCameraToRoot(camera, controls, root, margin = 1.35) {
  const box = new THREE.Box3().setFromObject(root);
  if (box.isEmpty()) return null;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 1);
  const dist = maxDim * margin;
  camera.near = Math.max(0.01, dist / 100);
  camera.far = dist * 20;
  camera.position.set(center.x + dist * 0.7, center.y + dist * 0.55, center.z + dist * 0.7);
  camera.lookAt(center);
  camera.updateProjectionMatrix();
  if (controls) {
    controls.target.copy(center);
    controls.update();
  }
  return { center, size, maxDim, dist };
}

/** Presets relative to a fitted scene: iso (default), top, front, side. */
export function setCameraPreset(camera, controls, fit, preset) {
  if (!fit) return;
  const { center, dist } = fit;
  const d = dist;
  if (preset === "top") {
    camera.position.set(center.x, center.y + d * 1.1, center.z + 0.001);
  } else if (preset === "front") {
    // Looking along +Y in Blender → after Z-up→Y-up root, Blender Y is -Z in three? 
    // Root has rotation.x = -PI/2, so Blender (x,y,z) → Three (x,z,-y) roughly via the group.
    // Camera is in Three space; content is under rotated root. Target is already in Three space from Box3.
    camera.position.set(center.x, center.y + d * 0.25, center.z + d);
  } else if (preset === "side") {
    camera.position.set(center.x + d, center.y + d * 0.25, center.z);
  } else {
    // iso
    camera.position.set(center.x + d * 0.7, center.y + d * 0.55, center.z + d * 0.7);
  }
  camera.lookAt(center);
  if (controls) {
    controls.target.copy(center);
    controls.update();
  }
}
