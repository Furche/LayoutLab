/**
 * Offscreen 3D thumbnails from slim viewer_preview exports (shortlist cards).
 * Orthographic top-down, zoomed to fit the whole room.
 */

import * as THREE from "three";
import { buildSceneFromExport, clearGroup, computeFit } from "./scene.js";

const THUMB_W = 240;
const THUMB_H = 180;
const FIT_PAD = 1.1;

let sharedRenderer = null;

function getRenderer() {
  if (sharedRenderer) return sharedRenderer;
  sharedRenderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false,
    preserveDrawingBuffer: true,
  });
  sharedRenderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  sharedRenderer.setSize(THUMB_W, THUMB_H, false);
  sharedRenderer.setClearColor(0x0e1116, 1);
  return sharedRenderer;
}

/**
 * Orthographic frustum that fits the room's horizontal AABB into the thumb.
 * World root is Blender Z-up rotated -90°X → Three Y-up; floor lies in XZ.
 */
function topDownOrthoCamera(fit, aspect) {
  const { center, size } = fit;
  const halfX = Math.max(size.x * 0.5 * FIT_PAD, 0.4);
  const halfZ = Math.max(size.z * 0.5 * FIT_PAD, 0.4);
  let halfW;
  let halfH;
  if (halfX / halfZ > aspect) {
    halfW = halfX;
    halfH = halfX / aspect;
  } else {
    halfH = halfZ;
    halfW = halfZ * aspect;
  }
  const camera = new THREE.OrthographicCamera(-halfW, halfW, halfH, -halfH, 0.05, 500);
  // Match main viewport "top" preset: look down -Y, screen up = -Z (north-ish)
  camera.up.set(0, 0, -1);
  const lift = Math.max(size.y, 1) + 8;
  camera.position.set(center.x, center.y + lift, center.z);
  camera.lookAt(center.x, center.y, center.z);
  camera.updateProjectionMatrix();
  return camera;
}

/**
 * Render a slim export into a canvas element (orthographic top-down).
 * @param {object} exportData
 * @returns {HTMLCanvasElement | null}
 */
export function renderShortlistThumbnail(exportData) {
  if (!exportData || (!exportData.rooms?.length && !exportData.objects?.length)) {
    return null;
  }
  try {
    const built = buildSceneFromExport(exportData);
    const grid = built.root.children.find((c) => c.type === "GridHelper");
    if (grid) built.root.remove(grid);
    // Clearances/opening wires clutter top-down cards
    if (built.layers?.clearances) built.layers.clearances.visible = false;

    const fit = computeFit(built.root, 1.0);
    if (!fit) {
      clearGroup(built.root);
      return null;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0e1116);
    const hemi = new THREE.HemisphereLight(0xd0d8e4, 0x2a3038, 1.05);
    const key = new THREE.DirectionalLight(0xffffff, 0.45);
    key.position.set(2, 10, 1);
    scene.add(hemi, key, built.root);

    const aspect = THUMB_W / THUMB_H;
    const camera = topDownOrthoCamera(fit, aspect);

    const renderer = getRenderer();
    renderer.render(scene, camera);

    const canvas = document.createElement("canvas");
    canvas.width = THUMB_W;
    canvas.height = THUMB_H;
    canvas.className = "chat-shortlist-card-thumb";
    const ctx = canvas.getContext("2d");
    ctx.drawImage(renderer.domElement, 0, 0);

    clearGroup(built.root);
    scene.clear();
    return canvas;
  } catch (err) {
    console.warn("shortlist thumbnail failed", err);
    return null;
  }
}
