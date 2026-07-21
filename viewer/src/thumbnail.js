/**
 * Offscreen 3D thumbnails from slim viewer_preview exports (shortlist cards).
 */

import * as THREE from "three";
import {
  buildSceneFromExport,
  clearGroup,
  computeFit,
  getPresetPose,
} from "./scene.js";

const THUMB_W = 220;
const THUMB_H = 150;

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
 * Render a slim export into a canvas element (iso view).
 * @param {object} exportData
 * @returns {HTMLCanvasElement | null}
 */
export function renderShortlistThumbnail(exportData) {
  if (!exportData || (!exportData.rooms?.length && !exportData.objects?.length)) {
    return null;
  }
  try {
    const built = buildSceneFromExport(exportData);
    // Drop grid for cleaner cards
    const grid = built.root.children.find((c) => c.type === "GridHelper");
    if (grid) built.root.remove(grid);

    const fit = computeFit(built.root, 1.25);
    if (!fit) {
      clearGroup(built.root);
      return null;
    }
    const pose = getPresetPose(fit, "iso");
    if (!pose) {
      clearGroup(built.root);
      return null;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0e1116);
    const hemi = new THREE.HemisphereLight(0xc8d2e0, 0x2a3038, 0.95);
    const key = new THREE.DirectionalLight(0xffffff, 0.65);
    key.position.set(4, 8, 3);
    scene.add(hemi, key, built.root);

    const camera = new THREE.PerspectiveCamera(40, THUMB_W / THUMB_H, 0.05, 200);
    camera.up.copy(pose.up);
    camera.position.copy(pose.position);
    camera.lookAt(pose.target);
    camera.updateProjectionMatrix();

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
