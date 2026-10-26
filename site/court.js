/* Shared half-court fixture and shot renderer for the site's shot views.
 *
 * The weekly timeline (app.js) and the all-rookie shot map (shots.js) both
 * draw on the same court geometry, so it lives here once.
 */

(function (global) {
  "use strict";

  /* ── Court geometry (feet) ─────────────────────────────────────────────── */

  const COURT = {
    halfWidth: 25,
    baseline: 1.575,      // rim centre sits 1.575 ft inside the baseline
    backboard: 5.575,     // 4 ft behind the baseline
    paintHalf: 8,
    paintDepth: 19,
    ftCircle: 6,
    threeRadius: 23.75,
    cornerX: 22,
    restricted: 4,
    midCourt: 45.925,
    midY: -(45.925 - 1.575),
    viewBox: "-26.5 -47 53 53",
  };

  const sx = (courtX) => courtX;
  const sy = (courtY) => -(courtY - COURT.baseline);

  function escapeAttr(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function courtMarkup() {
    const b = COURT.baseline;
    const paintTop = sy(COURT.paintDepth);
    const arcY = sy(Math.sqrt(COURT.threeRadius * COURT.threeRadius - COURT.cornerX * COURT.cornerX));
    const midY = sy(COURT.midCourt);
    return [
      '<rect class="court-paint" x="-8" y="' + paintTop.toFixed(2) + '" width="16" height="19" rx="0.4"></rect>',
      '<circle class="court-lines" cx="0" cy="' + paintTop.toFixed(2) + '" r="6"></circle>',
      '<path class="court-lines" d="M -' + COURT.cornerX + ' ' + b.toFixed(2) +
        ' L -' + COURT.cornerX + ' ' + arcY.toFixed(2) +
        ' A ' + COURT.threeRadius + ' ' + COURT.threeRadius + ' 0 0 1 ' + COURT.cornerX + ' ' + arcY.toFixed(2) +
        ' L ' + COURT.cornerX + ' ' + b.toFixed(2) + '"></path>',
      '<path class="court-lines" d="M -4 0 A 4 4 0 0 0 4 0"></path>',
      '<path class="court-lines" d="M -25 ' + b.toFixed(2) + ' L 25 ' + b.toFixed(2) + '"></path>',
      '<path class="court-lines" d="M -25 ' + b.toFixed(2) + ' L -25 ' + midY.toFixed(2) + '"></path>',
      '<path class="court-lines" d="M 25 ' + b.toFixed(2) + ' L 25 ' + midY.toFixed(2) + '"></path>',
      '<path class="court-lines" d="M -6 ' + midY.toFixed(2) + ' A 6 6 0 0 0 6 ' + midY.toFixed(2) + '"></path>',
      '<path class="court-board" d="M -3 ' + COURT.backboard.toFixed(2) + ' L 3 ' + COURT.backboard.toFixed(2) + '"></path>',
      '<circle class="court-rim" cx="0" cy="0" r="0.75"></circle>',
    ].join("");
  }

  /* Renders one shot attempt.
   *
   * options.attrs  extra data-* attributes (keys are used verbatim)
   * options.style  inline style, used by the shot map to colour a shot by
   *                 its owner
   * options.tip    overrides the default tooltip text
   */
  function shotMarkup(shot, options) {
    const opts = options || {};
    let cx = sx(shot.x);
    let cy = sy(shot.y);
    const far = cy < COURT.midY || Math.abs(cx) > 24.6;
    if (cy < COURT.midY) cy = COURT.midY;
    if (cx > 24.6) cx = 24.6;
    if (cx < -24.6) cx = -24.6;

    const x = cx.toFixed(2);
    const y = cy.toFixed(2);
    const arm = 0.62;
    const label = shot.type + " · " + shot.distance + " ft · " + (shot.made ? "MADE" : "MISSED");
    const tip = opts.tip || shot.date + " · " + label + (far ? " · beyond half court" : "");
    const cross = [
      "M " + (cx - arm).toFixed(2) + " " + (cy - arm).toFixed(2),
      "L " + (cx + arm).toFixed(2) + " " + (cy + arm).toFixed(2),
      "M " + (cx + arm).toFixed(2) + " " + (cy - arm).toFixed(2),
      "L " + (cx - arm).toFixed(2) + " " + (cy + arm).toFixed(2),
    ].join(" ");
    const shape = shot.made
      ? '<circle class="shot-made" cx="' + x + '" cy="' + y + '" r="1.05"></circle>'
      : '<circle class="shot-missed" cx="' + x + '" cy="' + y + '" r="1.05"></circle>' +
        '<path class="shot-cross" d="' + cross + '"></path>';

    let attrs = ' class="shot' + (far ? " shot-far" : "") + '"' +
      ' data-tip="' + escapeAttr(tip) + '"' +
      ' data-type="' + escapeAttr(shot.type) + '"' +
      ' data-distance="' + escapeAttr(shot.distance) + '"' +
      ' data-date="' + escapeAttr(shot.date) + '"' +
      ' data-made="' + (shot.made ? "1" : "0") + '"';

    if (opts.attrs) {
      Object.keys(opts.attrs).forEach((key) => {
        attrs += ' data-' + key + '="' + escapeAttr(opts.attrs[key]) + '"';
      });
    }
    if (opts.style) {
      attrs += ' style="' + escapeAttr(opts.style) + '"';
    }

    return "<g" + attrs + ">" + shape + "</g>";
  }

  global.Court = { COURT, sx, sy, courtMarkup, shotMarkup, escapeAttr };
})(window);
