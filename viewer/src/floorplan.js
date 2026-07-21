/**
 * Blueprint-style SVG floor plans for shortlist cards.
 * Top = North, right = East (same as layout_sketch).
 */

const FURNITURE_FILL = {
  bed_frame: "#c4a574",
  bed_mattress: "#d4c4a8",
  bed_pillow: "#e8dcc8",
  wardrobe_body: "#8a9bb0",
  wardrobe_door: "#9aabbe",
  desk_body: "#8b7355",
  desk_top: "#c4a574",
  desk_leg: "#8b7355",
  default: "#a0a8b4",
};

const SKIP_ROLES = new Set([
  "label",
  "clearance",
  "room_floor",
  "room_wall",
  "room_opening",
  "room_fixed",
]);

function roleOf(obj) {
  return obj?.layoutlab?.role || obj?.custom_properties?.layoutlab_role || "default";
}

function aabbXY(obj) {
  const corners = obj?.world_bbox_corners;
  if (!Array.isArray(corners) || corners.length < 2) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const c of corners) {
    if (!c || c.length < 2) continue;
    const x = Number(c[0]);
    const y = Number(c[1]);
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  }
  if (!Number.isFinite(minX)) return null;
  return { minX, minY, maxX, maxY, w: maxX - minX, d: maxY - minY };
}

function escapeXml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Opening segment in room XY (Blender): along-wall start + width.
 * offset is distance from wall start (south/west origin convention in Core).
 */
function openingSpan(roomW, roomD, opening) {
  const side = String(opening.wall_side || "").toLowerCase();
  const offset = Number(opening.offset) || 0;
  const width = Math.max(0.2, Number(opening.width) || 0.9);
  if (side === "south") {
    return { side, x0: offset, y0: 0, x1: offset + width, y1: 0 };
  }
  if (side === "north") {
    return { side, x0: offset, y0: roomD, x1: offset + width, y1: roomD };
  }
  if (side === "west") {
    return { side, x0: 0, y0: offset, x1: 0, y1: offset + width };
  }
  if (side === "east") {
    return { side, x0: roomW, y0: offset, x1: roomW, y1: offset + width };
  }
  return null;
}

function doorSwingPath(span, roomW, roomD, toSvg) {
  // Quarter-circle into the room from the hinge at lower offset end.
  const side = span.side;
  const [sx, sy] = toSvg(span.x0, span.y0);
  const [ex, ey] = toSvg(span.x1, span.y1);
  const width = Math.hypot(ex - sx, ey - sy);
  if (width < 0.05) return "";
  // Hinge at start (offset end); swing into interior
  let hx = sx;
  let hy = sy;
  let sweep = 1;
  let dx = 0;
  let dy = 0;
  if (side === "east") {
    // wall at max X, interior -X; SVG x decreases into room
    dx = -width;
    dy = 0;
    sweep = 1;
  } else if (side === "west") {
    dx = width;
    dy = 0;
    sweep = 0;
  } else if (side === "south") {
    // wall at y=0 → SVG bottom; interior toward north = -svgY
    dx = 0;
    dy = -width;
    sweep = 0;
  } else if (side === "north") {
    dx = 0;
    dy = width;
    sweep = 1;
  }
  const mx = hx + dx;
  const my = hy + dy;
  // Arc from leaf end (ex,ey) approx — draw from hinge along wall to swing tip
  return (
    `<path class="fp-door-swing" d="M ${hx.toFixed(2)} ${hy.toFixed(2)} ` +
    `L ${ex.toFixed(2)} ${ey.toFixed(2)} ` +
    `A ${width.toFixed(2)} ${width.toFixed(2)} 0 0 ${sweep} ${mx.toFixed(2)} ${my.toFixed(2)} Z" />`
  );
}

/**
 * Build an SVG element (blueprint top-down) from slim viewer_preview.
 * @param {object} exportData
 * @returns {SVGSVGElement | null}
 */
export function renderFloorplanSvg(exportData) {
  const room = Array.isArray(exportData?.rooms) ? exportData.rooms[0] : null;
  if (!room?.footprint) return null;
  const roomW = Number(room.footprint.width) || 0;
  const roomD = Number(room.footprint.depth) || 0;
  if (roomW <= 0 || roomD <= 0) return null;

  const pad = 0.35;
  const viewW = roomW + pad * 2;
  const viewH = roomD + pad * 2;
  // Blender (x,y) → SVG: flip Y so north (max y) is top
  const toSvg = (x, y) => [pad + x, pad + (roomD - y)];

  const wallStroke = 0.06;
  const parts = [];

  // Floor
  const [fx0, fy0] = toSvg(0, roomD);
  parts.push(
    `<rect class="fp-floor" x="${fx0.toFixed(2)}" y="${fy0.toFixed(2)}" ` +
      `width="${roomW.toFixed(2)}" height="${roomD.toFixed(2)}" />`,
  );

  // Outer wall rectangle (full); openings punched visually as gaps
  const openings = Array.isArray(room.openings) ? room.openings : [];
  const walls = Array.isArray(room.walls) ? room.walls : [];

  function drawWallWithGaps(side, x0, y0, x1, y1) {
    const segs = openings
      .filter((o) => String(o.wall_side || "").toLowerCase() === side)
      .map((o) => openingSpan(roomW, roomD, o))
      .filter(Boolean)
      .sort((a, b) => (side === "south" || side === "north" ? a.x0 - b.x0 : a.y0 - b.y0));

    const horizontal = side === "south" || side === "north";
    const pieces = [];
    if (horizontal) {
      let cursor = Math.min(x0, x1);
      const end = Math.max(x0, x1);
      const y = y0;
      for (const g of segs) {
        const g0 = Math.min(g.x0, g.x1);
        const g1 = Math.max(g.x0, g.x1);
        if (g0 > cursor) pieces.push({ x0: cursor, y0: y, x1: g0, y1: y });
        cursor = Math.max(cursor, g1);
      }
      if (cursor < end) pieces.push({ x0: cursor, y0: y, x1: end, y1: y });
    } else {
      let cursor = Math.min(y0, y1);
      const end = Math.max(y0, y1);
      const x = x0;
      for (const g of segs) {
        const g0 = Math.min(g.y0, g.y1);
        const g1 = Math.max(g.y0, g.y1);
        if (g0 > cursor) pieces.push({ x0: x, y0: cursor, x1: x, y1: g0 });
        cursor = Math.max(cursor, g1);
      }
      if (cursor < end) pieces.push({ x0: x, y0: cursor, x1: x, y1: end });
    }

    for (const p of pieces) {
      const [sx, sy] = toSvg(p.x0, p.y0);
      const [ex, ey] = toSvg(p.x1, p.y1);
      parts.push(
        `<line class="fp-wall" x1="${sx.toFixed(2)}" y1="${sy.toFixed(2)}" ` +
          `x2="${ex.toFixed(2)}" y2="${ey.toFixed(2)}" />`,
      );
    }
  }

  if (walls.length) {
    for (const w of walls) {
      const side = String(w.side || "").toLowerCase();
      const s = w.segment?.start;
      const e = w.segment?.end;
      if (!s || !e) continue;
      drawWallWithGaps(side, Number(s[0]), Number(s[1]), Number(e[0]), Number(e[1]));
    }
  } else {
    drawWallWithGaps("south", 0, 0, roomW, 0);
    drawWallWithGaps("east", roomW, 0, roomW, roomD);
    drawWallWithGaps("north", 0, roomD, roomW, roomD);
    drawWallWithGaps("west", 0, 0, 0, roomD);
  }

  // Openings: doors + windows
  for (const op of openings) {
    const span = openingSpan(roomW, roomD, op);
    if (!span) continue;
    const [sx, sy] = toSvg(span.x0, span.y0);
    const [ex, ey] = toSvg(span.x1, span.y1);
    const kind = String(op.kind || "").toLowerCase();
    if (kind === "door") {
      parts.push(
        `<line class="fp-door-gap" x1="${sx.toFixed(2)}" y1="${sy.toFixed(2)}" ` +
          `x2="${ex.toFixed(2)}" y2="${ey.toFixed(2)}" />`,
      );
      parts.push(doorSwingPath(span, roomW, roomD, toSvg));
    } else {
      // Window: parallel glass lines slightly inset
      const side = span.side;
      let ix0 = span.x0;
      let iy0 = span.y0;
      let ix1 = span.x1;
      let iy1 = span.y1;
      const inset = 0.05;
      if (side === "south") {
        iy0 += inset;
        iy1 += inset;
      } else if (side === "north") {
        iy0 -= inset;
        iy1 -= inset;
      } else if (side === "west") {
        ix0 += inset;
        ix1 += inset;
      } else if (side === "east") {
        ix0 -= inset;
        ix1 -= inset;
      }
      const [wx0, wy0] = toSvg(ix0, iy0);
      const [wx1, wy1] = toSvg(ix1, iy1);
      parts.push(
        `<line class="fp-window" x1="${sx.toFixed(2)}" y1="${sy.toFixed(2)}" ` +
          `x2="${ex.toFixed(2)}" y2="${ey.toFixed(2)}" />`,
      );
      parts.push(
        `<line class="fp-window-glass" x1="${wx0.toFixed(2)}" y1="${wy0.toFixed(2)}" ` +
          `x2="${wx1.toFixed(2)}" y2="${wy1.toFixed(2)}" />`,
      );
    }
  }

  // Furniture (merge by object_id / prefer body over tiny parts)
  const byId = new Map();
  for (const obj of exportData.objects || []) {
    const role = roleOf(obj);
    if (SKIP_ROLES.has(role)) continue;
    const box = aabbXY(obj);
    if (!box || box.w < 0.05 || box.d < 0.05) continue;
    const oid =
      obj.layoutlab?.object_id ||
      obj.custom_properties?.layoutlab_object_id ||
      obj.name ||
      role;
    const prev = byId.get(oid);
    const area = box.w * box.d;
    if (!prev || area > prev.area) {
      byId.set(oid, { role, box, area, name: obj.name || oid });
    }
  }
  for (const item of byId.values()) {
    const { box, role, name } = item;
    const [x, y] = toSvg(box.minX, box.maxY);
    const fill = FURNITURE_FILL[role] || FURNITURE_FILL.default;
    parts.push(
      `<rect class="fp-furniture" data-role="${escapeXml(role)}" ` +
        `x="${x.toFixed(2)}" y="${y.toFixed(2)}" ` +
        `width="${box.w.toFixed(2)}" height="${box.d.toFixed(2)}" ` +
        `fill="${fill}"><title>${escapeXml(name)}</title></rect>`,
    );
  }

  // Compass
  const [cx, cy] = toSvg(roomW / 2, roomD + 0.12);
  parts.push(
    `<text class="fp-compass" x="${cx.toFixed(2)}" y="${(cy - 0.05).toFixed(2)}" ` +
      `text-anchor="middle">N</text>`,
  );

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${viewW.toFixed(2)} ${viewH.toFixed(2)}`);
  svg.setAttribute("class", "chat-shortlist-card-plan");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Grundriss-Vorschau");
  svg.innerHTML = `
    <style>
      .fp-floor { fill: #1c2430; stroke: none; }
      .fp-wall { stroke: #d7dee8; stroke-width: ${wallStroke}; stroke-linecap: square; }
      .fp-door-gap { stroke: #0e1116; stroke-width: ${wallStroke * 1.4}; }
      .fp-door-swing { fill: rgba(97, 175, 239, 0.18); stroke: #61afef; stroke-width: 0.03; }
      .fp-window { stroke: #98c379; stroke-width: ${wallStroke * 1.15}; }
      .fp-window-glass { stroke: #98c379; stroke-width: 0.03; opacity: 0.85; }
      .fp-furniture { stroke: #0e1116; stroke-width: 0.025; opacity: 0.95; }
      .fp-compass { fill: #8b97a8; font-size: 0.22px; font-family: system-ui, sans-serif; }
    </style>
    ${parts.join("\n")}
  `;
  return svg;
}
