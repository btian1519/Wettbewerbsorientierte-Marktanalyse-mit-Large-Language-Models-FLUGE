"""Builds the self-contained HTML/JS for the animated Canvas map.

Rendering strategy for smoothness & scalability:
* The world (ocean, countries, all airports, route arcs, endpoints) is drawn
  **once** onto an offscreen static canvas.
* The animation loop only blits that static canvas and redraws the moving
  planes — so per-frame cost is O(number of routes), independent of map detail.
* Planes advance along a quadratic Bézier arc and are rotated to their tangent
  (true flight-direction heading).

The JS body is kept free of Python string formatting; the data payload is
injected as a single JSON token to avoid brace-escaping.
"""

from __future__ import annotations

import json

_JS_TEMPLATE = r"""
<div id="fs-map" style="width:100%;position:relative;">
  <canvas id="cv" style="width:100%;display:block;border-radius:14px;"></canvas>
</div>
<script>
const D = __PAYLOAD__;
const C = D.colors;
const host = document.getElementById('fs-map');
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');

let W = 0, H = D.height, dpr = 1;
let staticCv = document.createElement('canvas');
let sctx = staticCv.getContext('2d');
let proj = null;
let routes = [];

function computeProj() {
  const v = D.view;
  const lonSpan = Math.max(0.001, v.maxLon - v.minLon);
  const latSpan = Math.max(0.001, v.maxLat - v.minLat);
  const cx = (v.minLon + v.maxLon) / 2;
  const cy = (v.minLat + v.maxLat) / 2;
  const pad = 1.10;
  const scale = Math.min(W / (lonSpan * pad), H / (latSpan * pad));
  return { toXY: (lon, lat) => [ (lon - cx) * scale + W / 2, (cy - lat) * scale + H / 2 ] };
}

function drawStatic() {
  sctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  sctx.clearRect(0, 0, W, H);
  // Ocean
  sctx.fillStyle = C.ocean;
  sctx.fillRect(0, 0, W, H);

  // Countries
  sctx.lineWidth = 0.6;
  sctx.strokeStyle = C.white;
  for (const f of D.geojson.features) {
    const active = D.activeCountries && D.activeCountries.indexOf(f.properties.name) >= 0;
    sctx.fillStyle = active ? C.land_active : C.land;
    for (const poly of f.geometry.coordinates) {
      for (const ring of poly) {
        sctx.beginPath();
        for (let i = 0; i < ring.length; i++) {
          const p = proj.toXY(ring[i][0], ring[i][1]);
          if (i === 0) sctx.moveTo(p[0], p[1]); else sctx.lineTo(p[0], p[1]);
        }
        sctx.closePath();
        sctx.fill();
        sctx.stroke();
      }
    }
  }

  // All airports (small dots)
  sctx.fillStyle = C.airport_dot;
  for (const a of D.airports) {
    const p = proj.toXY(a[0], a[1]);
    if (p[0] < -5 || p[0] > W + 5 || p[1] < -5 || p[1] > H + 5) continue;
    sctx.globalAlpha = 0.55;
    sctx.beginPath();
    sctx.arc(p[0], p[1], 1.5, 0, 6.2832);
    sctx.fill();
  }
  sctx.globalAlpha = 1;

  // Route arcs + endpoints; also (re)build screen-space beziers for animation
  routes = [];
  for (const r of D.routes) {
    const p0 = proj.toXY(r.o[0], r.o[1]);
    const p1 = proj.toXY(r.d[0], r.d[1]);
    const mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2;
    let nx = -(p1[1] - p0[1]), ny = (p1[0] - p0[0]);
    const nl = Math.hypot(nx, ny) || 1;
    nx /= nl; ny /= nl;
    if (ny > 0) { nx = -nx; ny = -ny; }            // bow the arc upward
    const span = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
    const off = Math.min(0.22 * span, 90);
    const cp = [mx + nx * off, my + ny * off];
    routes.push({ p0, p1, cp, t: Math.random(), speed: 0.09 + 0.05 * Math.random() });

    // arc
    sctx.strokeStyle = C.route;
    sctx.lineWidth = 2.1;
    sctx.beginPath();
    sctx.moveTo(p0[0], p0[1]);
    sctx.quadraticCurveTo(cp[0], cp[1], p1[0], p1[1]);
    sctx.stroke();

    // endpoints
    for (const p of [p0, p1]) {
      sctx.beginPath(); sctx.fillStyle = C.airport_hl;
      sctx.arc(p[0], p[1], 4.2, 0, 6.2832); sctx.fill();
      sctx.lineWidth = 1.6; sctx.strokeStyle = C.white; sctx.stroke();
    }

    // rank badge near destination
    sctx.beginPath(); sctx.fillStyle = C.route;
    sctx.arc(p1[0], p1[1] - 13, 8, 0, 6.2832); sctx.fill();
    sctx.fillStyle = C.white; sctx.font = 'bold 11px Arial';
    sctx.textAlign = 'center'; sctx.textBaseline = 'middle';
    sctx.fillText(String(r.rank), p1[0], p1[1] - 13);
  }
}

function bez(r, t) {
  const u = 1 - t;
  return {
    x: u * u * r.p0[0] + 2 * u * t * r.cp[0] + t * t * r.p1[0],
    y: u * u * r.p0[1] + 2 * u * t * r.cp[1] + t * t * r.p1[1],
  };
}
function bezTan(r, t) {
  const u = 1 - t;
  return {
    x: 2 * u * (r.cp[0] - r.p0[0]) + 2 * t * (r.p1[0] - r.cp[0]),
    y: 2 * u * (r.cp[1] - r.p0[1]) + 2 * t * (r.p1[1] - r.cp[1]),
  };
}

function drawPlane(x, y, ang) {
  ctx.save();
  ctx.translate(x, y);
  // Glyph intrinsically points NE (~ -45°); offset so it faces the heading.
  ctx.rotate(ang + Math.PI / 4);
  ctx.font = '19px "Segoe UI Symbol","Apple Color Emoji",sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.shadowColor = 'rgba(0,0,0,0.25)'; ctx.shadowBlur = 3;
  ctx.fillStyle = C.plane;
  ctx.fillText('✈', 0, 0);
  ctx.restore();
}

let last = performance.now();
function loop(ts) {
  const dt = Math.min(0.05, (ts - last) / 1000);
  last = ts;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  ctx.drawImage(staticCv, 0, 0, W, H);
  for (const r of routes) {
    r.t += r.speed * dt;
    if (r.t > 1) r.t -= 1;
    const pt = bez(r, r.t);
    const tn = bezTan(r, r.t);
    drawPlane(pt.x, pt.y, Math.atan2(tn.y, tn.x));
  }
  requestAnimationFrame(loop);
}

function resize() {
  dpr = window.devicePixelRatio || 1;
  W = host.clientWidth || 700;
  cv.width = W * dpr; cv.height = H * dpr;
  cv.style.height = H + 'px';
  staticCv.width = W * dpr; staticCv.height = H * dpr;
  proj = computeProj();
  drawStatic();
}

window.addEventListener('resize', () => { resize(); });
resize();
requestAnimationFrame(loop);
</script>
"""


def build_map_html(payload: dict) -> str:
    return _JS_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")))
