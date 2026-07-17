/**
 * Build Three.js meshes from a LayoutLab viewer export (json_protocol §6.4).
 * Blender coords (Z-up) live under a root group rotated -90° about X → Three Y-up.
 */

import * as THREE from "three";

const ROLE_COLORS = {
  room_floor: 0x3a4554,
  room_wall: 0x9aa7b8,
  room_opening: 0x61afef,
  room_fixed: 0x7a6a58,
  clearance: 0xe5c07b,
  bed_frame: 0xc4a574,
  desk_body: 0x8b7355,
  default: 0xa0a8b4,
};

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

function boxMesh(location, dimensions, color, opts = {}) {
  const [lx, ly, lz] = location;
  const [dx, dy, dz] = dimensions.map((v) => Math.max(Number(v) || 0.001, 0.001));
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
  mesh.position.set(lx + dx / 2, ly + dy / 2, lz + dz / 2);
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
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({
      color,
      roughness: 0.9,
      metalness: 0.02,
      side: THREE.FrontSide,
      flatShading: true,
    }),
  );
  return mesh;
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
    const role = roleOf(obj);
    const color = colorFor(role);
    const viewer = obj.viewer || {};
    const displayWire = viewer.display === "wire" || role === "clearance" || role === "room_opening";
    const loc = obj.location || [0, 0, 0];
    const dims = obj.dimensions || [1, 1, 1];

    let mesh = null;
    if (viewer.primitive === "quad" && viewer.corners) {
      mesh = quadMesh(viewer.corners, color);
    } else if (displayWire) {
      mesh = boxMesh(loc, dims, color, { wire: true, opacity: role === "clearance" ? 0.85 : 0.7 });
    } else {
      mesh = boxMesh(loc, dims, color, {
        opacity: role === "room_floor" ? 0.95 : 1,
      });
    }

    if (!mesh) continue;
    mesh.name = obj.name || role;
    mesh.userData = { role, object_id: obj.layoutlab?.object_id };

    if (role === "clearance") clearances.add(mesh);
    else if (role === "room_opening") openings.add(mesh);
    else solids.add(mesh);
  }

  // Soft ground grid helper in Blender XY (after root rotate → Three XZ)
  const grid = new THREE.GridHelper(12, 12, 0x3a4554, 0x2a3340);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = -0.01;
  root.add(grid);

  return { root, layers: { clearances, openings, solids } };
}

export function fitCameraToRoot(camera, controls, root, margin = 1.35) {
  const box = new THREE.Box3().setFromObject(root);
  if (box.isEmpty()) return;
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
}
