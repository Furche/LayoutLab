/**
 * World-anchored fine grid under the dragged object.
 * Line positions stay on world multiples; fade centre follows the object.
 */

import * as THREE from "three";

const STEP = 0.1; // 10 cm — finer than the scene 1 m GridHelper
const HALF = 2.4; // visible extent before fade dies (±m)
const INNER = 0.55;
const OUTER = 2.1;
const Z_BIAS = 0.003;

/**
 * @returns {{ root: THREE.Group, setFadeCenter: Function, setHeight: Function, show: Function, hide: Function, dispose: Function }}
 */
export function createDragGrid() {
  const root = new THREE.Group();
  root.name = "drag_grid";
  root.visible = false;
  root.renderOrder = 20;

  const n = Math.ceil(HALF / STEP);
  const positions = [];
  for (let i = -n; i <= n; i++) {
    const t = i * STEP;
    positions.push(-HALF, t, 0, HALF, t, 0);
    positions.push(t, -HALF, 0, t, HALF, 0);
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));

  const mat = new THREE.ShaderMaterial({
    transparent: true,
    depthTest: true,
    depthWrite: false,
    toneMapped: false,
    uniforms: {
      uCenter: { value: new THREE.Vector2(0, 0) },
      uInner: { value: INNER },
      uOuter: { value: OUTER },
      uColor: { value: new THREE.Color(0x9fd4f0) },
      uOpacity: { value: 0.55 },
    },
    vertexShader: /* glsl */ `
      varying vec2 vLocalXy;
      void main() {
        vLocalXy = position.xy;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec2 uCenter;
      uniform float uInner;
      uniform float uOuter;
      uniform vec3 uColor;
      uniform float uOpacity;
      varying vec2 vLocalXy;
      void main() {
        float d = length(vLocalXy - uCenter);
        float a = 1.0 - smoothstep(uInner, uOuter, d);
        if (a < 0.01) discard;
        gl_FragColor = vec4(uColor, a * uOpacity);
      }
    `,
  });

  const lines = new THREE.LineSegments(geo, mat);
  lines.frustumCulled = false;
  lines.renderOrder = 20;
  root.add(lines);

  let windowOx = 0;
  let windowOy = 0;

  function rebuildWindow(cx, cy) {
    const ox = Math.round(cx / STEP) * STEP;
    const oy = Math.round(cy / STEP) * STEP;
    if (ox === windowOx && oy === windowOy) return;
    windowOx = ox;
    windowOy = oy;
    const arr = geo.getAttribute("position").array;
    let p = 0;
    for (let i = -n; i <= n; i++) {
      const t = i * STEP;
      arr[p++] = ox - HALF;
      arr[p++] = oy + t;
      arr[p++] = 0;
      arr[p++] = ox + HALF;
      arr[p++] = oy + t;
      arr[p++] = 0;
      arr[p++] = ox + t;
      arr[p++] = oy - HALF;
      arr[p++] = 0;
      arr[p++] = ox + t;
      arr[p++] = oy + HALF;
      arr[p++] = 0;
    }
    geo.getAttribute("position").needsUpdate = true;
    geo.computeBoundingSphere();
  }

  function setFadeCenter(cx, cy) {
    rebuildWindow(cx, cy);
    mat.uniforms.uCenter.value.set(cx, cy);
  }

  function setHeight(z) {
    root.position.z = Number(z) + Z_BIAS;
  }

  function show(cx, cy, z) {
    setFadeCenter(cx, cy);
    setHeight(z);
    root.visible = true;
  }

  function hide() {
    root.visible = false;
  }

  function dispose() {
    geo.dispose();
    mat.dispose();
  }

  return { root, setFadeCenter, setHeight, show, hide, dispose };
}

export { STEP as DRAG_GRID_STEP };
