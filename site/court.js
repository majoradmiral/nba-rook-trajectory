/*!
 * court.js — NBA half-court renderer + shot layer
 * -----------------------------------------------------------------------------
 * Drop-in replacement for the old court fixture. No dependencies, no build step.
 *
 *   var chart = Court.create(document.getElementById('court-wrap'), {
 *     variant: 'full',                       // 'full' | 'mini' (small cards)
 *     onHover:  function (shot, info) {},    // info = { x, y, event }  (client px)
 *     onLeave:  function () {},
 *     onSelect: function (shot, info) {}
 *   });
 *   chart.setShots(shots);                   // [{ x, y, made, player, color, ... }]
 *   chart.focusPlayer('player-id');          // dim everyone else (null clears)
 *   chart.pinShot(shot);                     // ring around one shot (null clears)
 *
 * Pass `splitMisses: true` to render two half courts (Scored / Missed) inside
 * the same container instead of one crowded overlay. Locations, colours,
 * focus, pinning and hover/select callbacks all keep working in both lanes.
 *
 * COORDINATES (feet):  x = 0..50 across the court (left → right)
 *                      y = distance from the BASELINE (rim sits at y = 5.25)
 * If your feed uses another origin, pass `transform: function (shot) { return { x, y }; }`
 * to Court.create() and map it there — that is the only line you ever need to change.
 *
 * Geometry is real NBA: 50 x 47 ft half court, 16 ft lane, 19 ft free-throw line,
 * 6 ft FT circle, 4 ft restricted arc, 23.75 ft three with 22 ft corners.
 */
(function (global) {
  'use strict';

  // ── Court constants (feet) ────────────────────────────────────────────────
  var G = {
    W: 50, L: 47, CX: 25,
    RIM_D: 5.25, RIM_R: 0.75, BOARD_D: 4, BOARD_HALF: 3,
    LANE_HALF: 8, FT_D: 19, FT_R: 6,
    RA_R: 4, THREE_R: 23.75, CORNER_X: 3
  };
  G.CORNER_D = G.RIM_D + Math.sqrt(G.THREE_R * G.THREE_R - (G.CX - G.CORNER_X) * (G.CX - G.CORNER_X)); // ≈ 14.20
  var VIEW = { x: -2.5, y: -1.5, w: 55, h: 51 };

  var uid = 0;
  function n(v) { return (Math.round(v * 1000) / 1000).toString(); }
  function sy(d) { return G.L - d; }                    // distance-from-baseline → svg y

  // ── Styles (injected once, scoped to .nbc so nothing in styles.css can fight it) ─
  var CSS = [
    '.nbc{display:block;width:100%;height:auto;user-select:none;-webkit-user-select:none;touch-action:manipulation}',
    '.nbc .nbc-out{fill:rgba(3,6,14,.32)}',
    '.nbc .nbc-line{fill:none;stroke:var(--court-line,rgba(188,208,250,.66));stroke-linecap:round;stroke-linejoin:round}',
    '.nbc .nbc-line.is-soft{stroke:var(--court-line-soft,rgba(188,208,250,.38))}',
    '.nbc .nbc-line.is-three{stroke:var(--court-three,rgba(150,196,255,.95))}',
    '.nbc .nbc-fillline{fill:var(--court-line,rgba(188,208,250,.5));stroke:none}',
    '.nbc .nbc-glow{fill:none;stroke:var(--accent,#60a5fa);stroke-linecap:round;opacity:.3}',
    '.nbc .nbc-board{fill:none;stroke:#e8f0ff;stroke-linecap:round;opacity:.95}',
    '.nbc .nbc-rim{fill:rgba(255,123,84,.1);stroke:#ff8a5c;filter:drop-shadow(0 0 .5px rgba(255,138,92,.9))}',
    '.nbc .nbc-net{fill:none;stroke:rgba(255,255,255,.5);stroke-linecap:round}',
    '.nbc .nbc-label{font:600 1.15px Inter,system-ui,sans-serif;letter-spacing:.2px;fill:rgba(188,208,250,.26);text-anchor:middle;text-transform:uppercase}',

    '.nbc .shot{cursor:pointer}',
    '.nbc .shot .hit{fill:transparent;stroke:none;pointer-events:all}',
    '.nbc .shot .dot{fill:var(--c,var(--made,#34d399));fill-opacity:.9;stroke:rgba(255,255,255,.85);stroke-width:.1;transition:stroke-width .12s ease}',
    '.nbc .shot .x{fill:none;stroke:var(--c,var(--missed,#fb7185));stroke-width:.2;stroke-linecap:round;opacity:.8;transition:stroke-width .12s ease,opacity .12s ease}',
    '.nbc .shot .ring{fill:none;stroke:var(--gold,#fbbf24);stroke-width:.14;opacity:.9}',
    '.nbc .shot:hover .dot{stroke:#fff;stroke-width:.3}',
    '.nbc .shot:hover .x{stroke-width:.42;opacity:1}',

    '.nbc .player-shots{transition:opacity .18s ease}',
    '.nbc .player-shots.is-dimmed{opacity:.1;pointer-events:none}',
    '.nbc .player-shots.is-active .dot{stroke:#fff}',
    '.nbc .player-shots.is-active .x{opacity:1}',

    // split-miss lanes: two real half courts inside one chart card
    '.nbc-split{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;align-items:start}',
    '.nbc-panel{min-width:0}',
    '.nbc-panel-head{display:flex;align-items:baseline;justify-content:space-between;gap:6px;padding:1px 3px 6px;font:700 .68rem Inter,system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:var(--muted,#9aa5bd)}',
    '.nbc-panel-head .nbc-count{font-family:var(--mono,ui-monospace,monospace);font-size:.66rem;font-weight:500;letter-spacing:0;color:var(--muted-dim,#64748b)}',
    '.nbc-panel--made .nbc-panel-head span:first-child{color:var(--made,#34d399)}',
    '.nbc-panel--missed .nbc-panel-head span:first-child{color:var(--missed,#fb7185)}',
    '@media (max-width:620px){.nbc-split{grid-template-columns:minmax(0,1fr)}}',

    '.nbc .nbc-pin circle{fill:none;stroke:#fff;stroke-width:.22}',
    '.nbc .nbc-pin .pulse{stroke:var(--accent,#60a5fa);stroke-width:.2;transform-box:fill-box;transform-origin:center;animation:nbcPulse 1.8s ease-out infinite}',
    '@keyframes nbcPulse{0%{transform:scale(.7);opacity:.9}100%{transform:scale(1.8);opacity:0}}',
    '@media (prefers-reduced-motion:reduce){.nbc .nbc-pin .pulse{animation:none;opacity:.6}.nbc .shot .dot,.nbc .shot .x,.nbc .player-shots{transition:none}}'
  ].join('\n');

  function ensureStyles() {
    if (typeof document === 'undefined' || document.getElementById('nbc-styles')) return;
    var s = document.createElement('style');
    s.id = 'nbc-styles';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

//__SPLIT1__
  // ── Static court markup ───────────────────────────────────────────────────
  function courtMarkup(opts) {
    var mini = opts.variant === 'mini';
    var id = 'nbc' + (++uid);
    var ls = mini ? 1.45 : 1;            // line-weight multiplier so mini courts stay legible
    var L = G.L, CX = G.CX;
    var rimY = sy(G.RIM_D), boardY = sy(G.BOARD_D), ftY = sy(G.FT_D), cornerY = sy(G.CORNER_D);
    var lx = CX - G.LANE_HALF, rx = CX + G.LANE_HALF;

    var threeArc = 'M' + G.CORNER_X + ' ' + L + 'L' + G.CORNER_X + ' ' + n(cornerY) +
      'A' + G.THREE_R + ' ' + G.THREE_R + ' 0 0 1 ' + (G.W - G.CORNER_X) + ' ' + n(cornerY) +
      'L' + (G.W - G.CORNER_X) + ' ' + L;
    var raPath = 'M' + (CX - G.RA_R) + ' ' + n(boardY) + 'L' + (CX - G.RA_R) + ' ' + n(rimY) +
      'A' + G.RA_R + ' ' + G.RA_R + ' 0 0 1 ' + (CX + G.RA_R) + ' ' + n(rimY) +
      'L' + (CX + G.RA_R) + ' ' + n(boardY);

    var h = [];
    h.push('<svg class="nbc nbc-' + (mini ? 'mini' : 'full') + ' shotmap-court" xmlns="http://www.w3.org/2000/svg" viewBox="' +
      [VIEW.x, VIEW.y, VIEW.w, VIEW.h].join(' ') + '" preserveAspectRatio="xMidYMid meet" role="img" aria-label="NBA half court">');
    h.push('<title>NBA half court (50 × 47 ft)</title>');

    // defs
    h.push('<defs>' +
      '<linearGradient id="' + id + 'f" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0" style="stop-color:var(--court-floor-a,#0d1530)"/><stop offset="1" style="stop-color:var(--court-floor-b,#111b38)"/></linearGradient>' +
      '<radialGradient id="' + id + 'g" cx="' + n(CX) + '" cy="' + n(rimY) + '" r="32" gradientUnits="userSpaceOnUse">' +
        '<stop offset="0" style="stop-color:var(--accent,#60a5fa);stop-opacity:.20"/>' +
        '<stop offset=".55" style="stop-color:var(--accent-2,#a78bfa);stop-opacity:.05"/>' +
        '<stop offset="1" style="stop-color:var(--accent-2,#a78bfa);stop-opacity:0"/></radialGradient>' +
      '<linearGradient id="' + id + 'p" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0" style="stop-color:var(--accent,#60a5fa);stop-opacity:.10"/>' +
        '<stop offset="1" style="stop-color:var(--accent-2,#a78bfa);stop-opacity:.24"/></linearGradient>' +
      '<radialGradient id="' + id + 'v" cx="' + n(CX) + '" cy="' + n(L * 0.62) + '" r="40" gradientUnits="userSpaceOnUse">' +
        '<stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".42"/></radialGradient>' +
      '<linearGradient id="' + id + 'e" x1="0" y1="0" x2="1" y2="1">' +
        '<stop offset="0" style="stop-color:var(--accent,#60a5fa)"/><stop offset="1" style="stop-color:var(--accent-2,#a78bfa)"/></linearGradient>' +
      '<pattern id="' + id + 'w" width="3" height="' + L + '" patternUnits="userSpaceOnUse">' +
        '<rect width="1.5" height="' + L + '" fill="#fff" fill-opacity=".01"/>' +
        '<rect x="1.5" width="1.5" height="' + L + '" fill="#000" fill-opacity=".035"/></pattern>' +
      '<filter id="' + id + 'b" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation=".55"/></filter>' +
      '<clipPath id="' + id + 'c"><rect x="0" y="0" width="' + G.W + '" height="' + L + '" rx="1.1"/></clipPath>' +
      '</defs>');

    // surround + floor
    h.push('<rect class="nbc-out" x="' + VIEW.x + '" y="' + VIEW.y + '" width="' + VIEW.w + '" height="' + VIEW.h + '"/>');
    h.push('<g clip-path="url(#' + id + 'c)">' +
      '<rect width="' + G.W + '" height="' + L + '" fill="url(#' + id + 'f)"/>' +
      '<rect width="' + G.W + '" height="' + L + '" fill="url(#' + id + 'w)"/>' +
      '<rect width="' + G.W + '" height="' + L + '" fill="url(#' + id + 'g)"/>' +
      // area inside the three-point line sits a touch brighter than the perimeter
      '<path d="' + threeArc + 'Z" fill="#9fc3ff" fill-opacity=".035"/>' +
      // painted lane + restricted area
      '<rect x="' + lx + '" y="' + n(ftY) + '" width="' + (G.LANE_HALF * 2) + '" height="' + G.FT_D + '" fill="url(#' + id + 'p)"/>' +
      '<path d="' + raPath + 'Z" fill="#a78bfa" fill-opacity=".13"/>' +
      '<path d="M' + (CX - 6) + ' 0A6 6 0 0 0 ' + (CX + 6) + ' 0Z" fill="#9fc3ff" fill-opacity=".05"/>' +
      '<rect width="' + G.W + '" height="' + L + '" fill="url(#' + id + 'v)"/>' +
      '</g>');

    // neon bloom under the three-point line
    h.push('<path class="nbc-glow" d="' + threeArc + '" stroke-width="' + n(0.75 * ls) + '" filter="url(#' + id + 'b)"/>');

    // lines
    var lw = n(0.3 * ls), lw3 = n(0.38 * ls), lws = n(0.22 * ls);
    h.push('<g>');
    h.push('<rect class="nbc-line" x="0" y="0" width="' + G.W + '" height="' + L + '" rx="1.1" stroke-width="' + n(0.45 * ls) + '" style="stroke:url(#' + id + 'e);stroke-opacity:.4"/>');
    h.push('<rect class="nbc-line" x="' + lx + '" y="' + n(ftY) + '" width="' + (G.LANE_HALF * 2) + '" height="' + G.FT_D + '" stroke-width="' + lw + '"/>');
    h.push('<path class="nbc-line" d="M' + (CX - G.FT_R) + ' ' + n(ftY) + 'A' + G.FT_R + ' ' + G.FT_R + ' 0 0 1 ' + (CX + G.FT_R) + ' ' + n(ftY) + '" stroke-width="' + lw + '"/>');
    h.push('<path class="nbc-line is-soft" d="M' + (CX - G.FT_R) + ' ' + n(ftY) + 'A' + G.FT_R + ' ' + G.FT_R + ' 0 0 0 ' + (CX + G.FT_R) + ' ' + n(ftY) + '" stroke-width="' + lws + '" stroke-dasharray="' + n(0.9 * ls) + ' ' + n(0.75 * ls) + '"/>');
    h.push('<path class="nbc-line" d="' + raPath + '" stroke-width="' + lw + '"/>');
    h.push('<path class="nbc-line is-three" d="' + threeArc + '" stroke-width="' + lw3 + '"/>');
    if (!mini) {
      h.push('<path class="nbc-line" d="M' + (CX - 6) + ' 0A6 6 0 0 0 ' + (CX + 6) + ' 0" stroke-width="' + lw + '"/>');
      h.push('<path class="nbc-line is-soft" d="M' + (CX - 2) + ' 0A2 2 0 0 0 ' + (CX + 2) + ' 0" stroke-width="' + lws + '"/>');
      // lane hash marks: block at 7 ft, ticks at 11 / 14 / 17 ft
      h.push('<rect class="nbc-fillline" x="' + (lx - 1.5) + '" y="' + n(sy(8)) + '" width="1.5" height="1"/>');
      h.push('<rect class="nbc-fillline" x="' + rx + '" y="' + n(sy(8)) + '" width="1.5" height="1"/>');
      [11, 14, 17].forEach(function (d) {
        h.push('<path class="nbc-line is-soft" d="M' + (lx - 1) + ' ' + n(sy(d)) + 'H' + lx + 'M' + rx + ' ' + n(sy(d)) + 'H' + (rx + 1) + '" stroke-width="' + lws + '"/>');
      });
    }
    // backboard, neck, rim
    h.push('<path class="nbc-board" d="M' + (CX - G.BOARD_HALF) + ' ' + n(boardY) + 'H' + (CX + G.BOARD_HALF) + '" stroke-width="' + n(0.5 * ls) + '"/>');
    h.push('<path class="nbc-net" d="M' + CX + ' ' + n(boardY) + 'V' + n(rimY + G.RIM_R) + '" stroke-width="' + n(0.18 * ls) + '"/>');
    h.push('<circle class="nbc-rim" cx="' + CX + '" cy="' + n(rimY) + '" r="' + G.RIM_R + '" stroke-width="' + n(0.26 * ls) + '"/>');
    h.push('</g>');

    // shots go here
    h.push('<g class="nbc-shots"></g><g class="nbc-pin-layer"></g>');
    h.push('</svg>');
    return h.join('');
}

  // ── Helpers ───────────────────────────────────────────────────────────────
  function isBad(v) { return typeof v !== 'number' || !isFinite(v) || Math.abs(v) > 1000; } // ESPN sentinel ≈ -2.1e8
  function distFromRim(x, d) { return Math.sqrt((x - G.CX) * (x - G.CX) + (d - G.RIM_D) * (d - G.RIM_D)); }
  function isThree(x, d) {
    if (d <= G.CORNER_D) return x <= G.CORNER_X + 0.001 || x >= G.W - G.CORNER_X - 0.001;
    return distFromRim(x, d) >= G.THREE_R - 0.001;
  }

  var ZONES = ['Restricted area', 'Paint (non-RA)', 'Mid-range', 'Corner 3', 'Above-break 3'];
  function zoneOf(x, d) {
    if (isThree(x, d)) return d <= G.CORNER_D ? 'Corner 3' : 'Above-break 3';
    if (distFromRim(x, d) <= G.RA_R) return 'Restricted area';
    if (x >= G.CX - G.LANE_HALF && x <= G.CX + G.LANE_HALF && d <= G.FT_D) return 'Paint (non-RA)';
    return 'Mid-range';
  }

  function defaultTransform(s) { return { x: s.x, y: s.y }; }

  function normalise(shots, transform) {
    var out = [];
    for (var i = 0; i < shots.length; i++) {
      var s = shots[i], p = transform(s);
      if (!p || isBad(p.x) || isBad(p.y)) continue;
      var x = Math.max(-1.6, Math.min(G.W + 1.6, p.x));
      var d = Math.max(-1.2, Math.min(G.L + 1.2, p.y));
      out.push({ shot: s, x: x, d: d, made: !!(s.made || s.isMade || s.scoringPlay), far: distFromRim(p.x, p.y) >= 30 });
    }
    return out;
  }

  // Zone breakdown for the little .zone-bar rows. Returns [{zone, fga, fgm, pct, share}]
  function zoneStats(shots, transform) {
    var items = normalise(shots || [], transform || defaultTransform);
    var acc = {}; ZONES.forEach(function (z) { acc[z] = { zone: z, fga: 0, fgm: 0 }; });
    items.forEach(function (it) { var z = acc[zoneOf(it.x, it.d)]; z.fga++; if (it.made) z.fgm++; });
    return ZONES.map(function (z) {
      var r = acc[z];
      r.pct = r.fga ? r.fgm / r.fga : 0;
      r.share = items.length ? r.fga / items.length : 0;
      return r;
    });
  }

  // ── Instance ──────────────────────────────────────────────────────────────
  function create(container, options) {
    ensureStyles();
    var o = options || {};
    var variant = o.variant === 'mini' ? 'mini' : 'full';
    var transform = o.transform || defaultTransform;
    var dotScale = o.dotScale || (variant === 'mini' ? 1.5 : 1);
    var splitMisses = o.splitMisses === true;

    function lane(kind, label) {
      return '<div class="nbc-panel nbc-panel--' + kind + '">' +
        '<div class="nbc-panel-head"><span>' + label + '</span>' +
        '<span class="nbc-count" data-count="' + kind + '">0 shots</span></div>' +
        courtMarkup({ variant: variant }) + '</div>';
    }
    container.innerHTML = splitMisses
      ? '<div class="nbc-split">' + lane('made', 'Scored') + lane('missed', 'Missed') + '</div>'
      : courtMarkup({ variant: variant });

    // One view per court. Every view shares the same normalised shot list,
    // so data-index based hover/select/pin keeps working in both lanes.
    var views = [];
    var svgs = container.querySelectorAll('svg.nbc');
    for (var v = 0; v < svgs.length; v++) {
      var svg = svgs[v];
      var panel = svg.parentNode && svg.parentNode.classList ? svg.parentNode : null;
      views.push({
        kind: splitMisses
          ? (panel && panel.classList.contains('nbc-panel--made') ? 'made' : 'missed')
          : 'all',
        svg: svg,
        shots: svg.querySelector('.nbc-shots'),
        pin: svg.querySelector('.nbc-pin-layer'),
        count: panel ? panel.querySelector('.nbc-count') : null
      });
    }
    var items = [];

    function shotMarkup(it, idx) {
      var r = 0.31 * dotScale, cls = 'shot ' + (it.made ? 'is-made' : 'is-missed') + (it.far ? ' is-far' : '');
      var g = '<g class="' + cls + '" data-i="' + idx + '" transform="translate(' + n(it.x) + ' ' + n(sy(it.d)) + ')">' +
        '<circle class="hit" r="' + n(1.05 * dotScale) + '"/>';
      g += it.made
        ? '<circle class="dot" r="' + n(r) + '"/>'
        : '<path class="x" d="M' + n(-r) + ' ' + n(-r) + 'L' + n(r) + ' ' + n(r) + 'M' + n(r) + ' ' + n(-r) + 'L' + n(-r) + ' ' + n(r) + '"/>';
      if (it.far) g += '<circle class="ring" r="' + n(r + 0.38) + '"/>';
      return g + '</g>';
    }

    function setShots(shots, opts) {
      opts = opts || {};
      items = normalise(shots || [], transform);
      var buckets = {};
      views.forEach(function (view) { buckets[view.kind] = { groups: {}, order: [], count: 0 }; });
      items.forEach(function (it, idx) {
        var s = it.shot;
        var key = String(s.player != null ? s.player : (s.playerId != null ? s.playerId : (s.athleteId != null ? s.athleteId : 'all')));
        var bucket = buckets[splitMisses ? (it.made ? 'made' : 'missed') : 'all'];
        if (!bucket.groups[key]) { bucket.groups[key] = { color: s.color || null, misses: [], makes: [] }; bucket.order.push(key); }
        if (!bucket.groups[key].color && s.color) bucket.groups[key].color = s.color;
        (it.made ? bucket.groups[key].makes : bucket.groups[key].misses).push(shotMarkup(it, idx));
        bucket.count++;
      });
      views.forEach(function (view) {
        var bucket = buckets[view.kind];
        view.shots.innerHTML = bucket.order.map(function (k) {
          var g = bucket.groups[k];
          var style = g.color ? ' style="--c:' + String(g.color).replace(/[^#\w(),.%\s-]/g, '') + '"' : '';
          // misses first so made shots always sit on top
          return '<g class="player-shots" data-player="' + String(k).replace(/"/g, '&quot;') + '"' + style + '>' + g.misses.join('') + g.makes.join('') + '</g>';
        }).join('');
        if (view.count) view.count.textContent = bucket.count + (bucket.count === 1 ? ' shot' : ' shots');
      });
      if (opts.focus != null) focusPlayer(opts.focus);
      return api;
    }

    function focusPlayer(id) {
      views.forEach(function (view) {
        var groups = view.shots.querySelectorAll('.player-shots');
        for (var i = 0; i < groups.length; i++) {
          var g = groups[i], on = id != null && g.getAttribute('data-player') === String(id);
          g.classList.toggle('is-active', on);
          g.classList.toggle('is-dimmed', id != null && !on);
        }
      });
      return api;
    }

    function pinShot(shot) {
      views.forEach(function (view) { view.pin.innerHTML = ''; });
      if (shot == null) return api;
      var it = null;
      for (var i = 0; i < items.length; i++) { if (items[i].shot === shot || (shot.id != null && items[i].shot.id === shot.id)) { it = items[i]; break; } }
      if (!it) return api;
      var target = views[0];
      if (splitMisses) {
        for (var k = 0; k < views.length; k++) {
          if (views[k].kind === (it.made ? 'made' : 'missed')) { target = views[k]; break; }
        }
      }
      target.pin.innerHTML = '<g class="nbc-pin" transform="translate(' + n(it.x) + ' ' + n(sy(it.d)) + ')">' +
        '<circle class="pulse" r="1.1"/><circle r="1.15"/></g>';
      return api;
    }

    function clear() {
      views.forEach(function (view) {
        view.shots.innerHTML = '';
        view.pin.innerHTML = '';
        if (view.count) view.count.textContent = '0 shots';
      });
      items = [];
      return api;
    }

    function itemFromEvent(e, view) {
      var t = e.target && e.target.closest ? e.target.closest('.shot') : null;
      if (!t || !view.svg.contains(t)) return null;
      return items[+t.getAttribute('data-i')] || null;
    }
    views.forEach(function (view) {
      var hovering = null;
      function onMove(e) {
        var it = itemFromEvent(e, view);
        if (it === hovering) { if (it && o.onHover) o.onHover(it.shot, { x: e.clientX, y: e.clientY, event: e }); return; }
        hovering = it;
        if (it) { if (o.onHover) o.onHover(it.shot, { x: e.clientX, y: e.clientY, event: e }); }
        else if (o.onLeave) o.onLeave();
      }
      function onOut() { if (hovering) { hovering = null; if (o.onLeave) o.onLeave(); } }
      function onClick(e) {
        var it = itemFromEvent(e, view);
        if (it && o.onSelect) o.onSelect(it.shot, { x: e.clientX, y: e.clientY, event: e });
      }
      view.svg.addEventListener('pointermove', onMove);
      view.svg.addEventListener('pointerleave', onOut);
      view.svg.addEventListener('click', onClick);
      view.unbind = function () {
        view.svg.removeEventListener('pointermove', onMove);
        view.svg.removeEventListener('pointerleave', onOut);
        view.svg.removeEventListener('click', onClick);
      };
    });

    function destroy() {
      views.forEach(function (view) { if (view.unbind) view.unbind(); });
      container.innerHTML = '';
    }

    var api = {
      el: views.length ? views[0].svg : null,
      els: views.map(function (view) { return view.svg; }),
      setShots: setShots, focusPlayer: focusPlayer, pinShot: pinShot, clear: clear, destroy: destroy,
      get shots() { return items.map(function (it) { return it.shot; }); }
    };
    return api;
  }

  global.Court = {
    create: create,
    markup: function (opts) { ensureStyles(); return courtMarkup(opts || {}); },
    zoneOf: zoneOf, zoneStats: zoneStats, zones: ZONES, isThree: isThree, distFromRim: distFromRim,
    geometry: G, viewBox: VIEW
  };
})(typeof window !== 'undefined' ? window : this);