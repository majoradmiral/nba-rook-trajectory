/* Rookie Shot Timeline — weekly featured players with court shot charts.
 *
 * Data comes from site/data/timeline.json (written by `python -m src.timeline`).
 * The page polls that file so the timeline stays current without a reload, and
 * falls back to data/timeline.js when opened straight from disk (file://).
 */

(function () {
  "use strict";

  const DATA_URL = "data/timeline.json";
  const POLL_MS = 60000;
  const PLAY_MS = 3200;

  const state = {
    data: null,
    weeks: [],
    index: 0,
    phase: "competitive",
    playing: false,
    playTimer: null,
    lastSeen: null,
  };

  const el = {
    seasonTitle: document.getElementById("season-title"),
    rankingNote: document.getElementById("ranking-note"),
    statusPill: document.getElementById("status-pill"),
    statusText: document.getElementById("status-text"),
    weekLabel: document.getElementById("week-label"),
    weekMeta: document.getElementById("week-meta"),
    rail: document.getElementById("week-rail"),
    grid: document.getElementById("featured-grid"),
    leaderTable: document.querySelector("#leaderboard-table tbody"),
    leaderNote: document.getElementById("leaderboard-note"),
    limitedTable: document.querySelector("#limited-table tbody"),
    limitedNote: document.getElementById("limited-note"),
    games: document.getElementById("recent-games"),
    recentNote: document.getElementById("recent-note"),
    footerStats: document.getElementById("footer-stats"),
    tooltip: document.getElementById("tooltip"),
    toast: document.getElementById("toast"),
    prev: document.getElementById("prev-week"),
    next: document.getElementById("next-week"),
    play: document.getElementById("play-btn"),
    refresh: document.getElementById("refresh-btn"),
  };

  /* ── Court geometry ─────────────────────────────────────────────────────── */

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /* ── Formatting ────────────────────────────────────────────────────────── */

  const one = (value) => (value == null ? "—" : Number(value).toFixed(1));
  const pct = (value) => (value == null ? "—" : (Number(value) * 100).toFixed(1) + "%");
  const plusMinus = (value) => {
    if (value == null) return "—";
    const number = Number(value);
    return (number > 0 ? "+" : "") + number.toFixed(1);
  };

  /* ── Rendering ─────────────────────────────────────────────────────────── */

  function visibleWeeks() {
    const weeks = (state.data && state.data.weeks) || [];
    if (state.phase === "all") return weeks.slice();
    return weeks.filter((week) =>
      (week.season_types || []).some((type) => type === "regular" || type === "playoffs")
    );
  }

  function phaseLabel(week) {
    const types = week.season_types || [];
    if (types.indexOf("playoffs") !== -1) return "playoffs";
    if (types.indexOf("regular") !== -1) return "regular season";
    return "preseason";
  }

  function renderRail() {
    el.rail.innerHTML = state.weeks
      .map((week, index) => {
        const active = index === state.index ? " is-active" : "";
        const phase = phaseLabel(week);
        const phaseClass = phase === "regular season" ? "is-regular" : phase === "playoffs" ? "is-playoffs" : "";
        return (
          '<button type="button" class="week-chip' + active + '" role="tab" data-index="' + index + '">' +
          '<span class="wk">Week ' + week.index + "</span>" +
          '<span class="wk-dates">' + escapeHtml(week.label) + "</span>" +
          '<span class="wk-names">' + escapeHtml((week.headline || []).join(" · ")) + "</span>" +
          '<span class="wk-phase ' + phaseClass + '">' + escapeHtml(phase) + "</span>" +
          "</button>"
        );
      })
      .join("");
  }

  function statCell(label, value, tone) {
    return (
      '<div class="stat"><span class="label">' + label + "</span>" +
      '<span class="value' + (tone ? " " + tone : "") + '">' + value + "</span></div>"
    );
  }

  function zoneRow(label, zone) {
    const attempts = (zone && zone.attempts) || 0;
    const made = (zone && zone.made) || 0;
    const ratio = attempts ? (made / attempts) * 100 : 0;
    return (
      '<div class="zone"><span>' + label + "</span>" +
      '<span class="zone-track"><span class="zone-fill" style="width:' + ratio.toFixed(0) + '%"></span></span>' +
      '<span class="zone-val">' + made + "/" + attempts + "</span></div>"
    );
  }

  function renderCard(player) {
    const week = player.week || {};
    const season = player.season || {};
    const shots = player.shots || [];
    const pmTone = Number(week.plus_minus) > 0 ? "pos" : Number(week.plus_minus) < 0 ? "neg" : "";

    const chart = shots.length
      ? '<svg class="court" viewBox="' + Court.COURT.viewBox + '" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Shot chart">' +
        Court.courtMarkup() +
        shots.map((shot) => Court.shotMarkup(shot)).join("") +
        "</svg>"
      : '<div class="chart-empty">' +
        (player.played === false
          ? "Did not play this week — ranked on season-to-date impact."
          : "No tracked shot attempts for this player this week.") +
        "</div>";

    return (
      '<article class="card">' +
      '<div class="card-head">' +
      "<div>" +
      '<span class="rank-badge">#' + player.rank + " · " + escapeHtml(player.team || "") + "</span>" +
      '<h3 class="player-name">' + escapeHtml(player.name) + "</h3>" +
      '<p class="player-team">' + escapeHtml(player.position || "") + " · week " + (week.games || 0) + " game(s)" +
      (player.is_rookie ? " · rookie" : "") +
      (player.overall_rank ? " · overall #" + player.overall_rank : "") + "</p>" +
      "</div>" +
      '<div class="stat-strip">' +
      statCell("PPG", one(week.points)) +
      statCell("RPG", one(week.rebounds)) +
      statCell("APG", one(week.assists)) +
      statCell("+/-", plusMinus(week.plus_minus), pmTone) +
      "</div>" +
      "</div>" +
      '<div class="court-wrap">' + chart + "</div>" +
      '<div class="zone-bar">' +
      zoneRow("Rim", player.zones && player.zones.rim) +
      zoneRow("Mid-range", player.zones && player.zones.mid) +
      zoneRow("Three", player.zones && player.zones.three) +
      "</div>" +
      '<div class="card-foot">' +
      "<span>Season " + one(season.points) + " PPG · " + one(season.rebounds) + " RPG · " +
      one(season.assists) + " APG · " + plusMinus(season.plus_minus) + " +/- · " +
      one(season.score) + " score</span>" +
      "<span>" + (player.shot_totals ? player.shot_totals.made : 0) + "/" +
      (player.shot_totals ? player.shot_totals.attempts : 0) + " FGA</span>" +
      "</div>" +
      "</article>"
    );
  }

  function renderFeatured() {
    const week = state.weeks[state.index];
    if (!week) {
      el.grid.innerHTML = '<div class="empty-state">No weeks match this filter yet.</div>';
      return;
    }
    el.weekLabel.textContent = "Week " + week.index + " · " + week.label;
    const phases = (week.season_types || []).join(" + ");
    el.weekMeta.textContent =
      phaseLabel(week) + " · " + week.games + " game" + (week.games === 1 ? "" : "s") +
      " · " + phases + " · " + (week.featured || []).length + " featured";
    el.grid.innerHTML = (week.featured || []).map(renderCard).join("");
  }

  function leaderRow(row, featuredIds) {
    const pm = Number(row.plus_minus);
    const tone = pm > 0 ? "pm-pos" : pm < 0 ? "pm-neg" : "";
    return (
      "<tr" + (featuredIds.has(row.player_id) ? ' class="is-featured"' : "") + ">" +
      "<td>" + row.rank + "</td>" +
      '<td class="player-cell">' + escapeHtml(row.name) + "</td>" +
      '<td class="team-cell">' + escapeHtml(row.team) + "</td>" +
      '<td class="num">' + row.games + "</td>" +
      '<td class="num">' + one(row.minutes) + "</td>" +
      '<td class="num">' + one(row.points) + "</td>" +
      '<td class="num">' + one(row.rebounds) + "</td>" +
      '<td class="num">' + one(row.assists) + "</td>" +
      '<td class="num">' + pct(row.fg_pct) + "</td>" +
      '<td class="num">' + pct(row.three_pct) + "</td>" +
      '<td class="num ' + tone + '">' + plusMinus(row.plus_minus) + "</td>" +
      '<td class="num">' + one(row.score) + "</td>" +
      "</tr>"
    );
  }

  function renderLeaderboard() {
    const rows = (state.data && state.data.leaderboard) || [];
    const limited = (state.data && state.data.limited_sample) || [];
    const featuredIds = new Set(
      ((state.weeks[state.index] || {}).featured || []).map((player) => player.player_id)
    );
    el.leaderNote.textContent = rows.length
      ? "season to date · " + ((state.data && state.data.ranking_metric) || "performance score")
      : "no data yet";
    el.leaderTable.innerHTML = rows.map((row) => leaderRow(row, featuredIds)).join("");

    const limitedNote = (state.data && state.data.limited_note) || "under 3 GP or under 10 MPG";
    el.limitedNote.textContent = limited.length
      ? "small sample · " + limitedNote
      : "no limited-sample players yet";
    el.limitedTable.innerHTML = limited
      .map((row) => leaderRow(row, featuredIds))
      .join("");
  }

  function renderGames() {
    const games = (state.data && state.data.recent_games) || [];
    el.recentNote.textContent = games.length ? "latest " + games.length + " completed" : "no games yet";
    if (!games.length) {
      el.games.innerHTML = '<div class="empty-state">No completed games tracked yet.</div>';
      return;
    }
    el.games.innerHTML = games
      .map((game) => {
        const awayWin = game.away.score > game.home.score;
        const lines = (game.lines || [])
          .map((line) => {
            const pm = Number(line.plus_minus);
            const tone = pm > 0 ? "pm-pos" : pm < 0 ? "pm-neg" : "";
            return (
              '<span class="game-line">' + escapeHtml(line.name) + " (" + escapeHtml(line.team) + ") " +
              "<b>" + line.points + "</b> pts · <b>" + line.rebounds + "</b> reb · <b>" +
              line.assists + "</b> ast · <span class='" + tone + "'>" +
              (pm > 0 ? "+" : "") + pm + "</span></span>"
            );
          })
          .join("");
        return (
          '<div class="game">' +
          '<div class="game-top"><span>' + escapeHtml(game.date) + "</span>" +
          "<span>" + escapeHtml(game.season_type) + "</span></div>" +
          '<div class="game-teams">' +
          '<span class="abbr away' + (awayWin ? " winner" : "") + '">' + escapeHtml(game.away.abbr) + "</span>" +
          '<span class="score' + (awayWin ? " winner" : "") + '">' + game.away.score + "</span>" +
          '<span class="vs">@</span>' +
          '<span class="score' + (!awayWin ? " winner" : "") + '">' + game.home.score + "</span>" +
          '<span class="abbr' + (!awayWin ? " winner" : "") + '">' + escapeHtml(game.home.abbr) + "</span>" +
          "</div>" +
          (lines ? '<div class="game-lines">' + lines + "</div>" : "") +
          "</div>"
        );
      })
      .join("");
  }

  function renderStatus() {
    const data = state.data;
    if (!data) return;
    const generated = data.generated_at ? new Date(data.generated_at) : null;
    const ago = generated ? Math.max(0, Math.round((Date.now() - generated.getTime()) / 1000)) : null;
    const age = ago == null ? "unknown" : ago < 60 ? "just now" : ago < 3600 ? Math.round(ago / 60) + " min ago" : Math.round(ago / 3600) + " h ago";
    el.statusText.textContent = "updated " + age;
    el.statusPill.classList.toggle("is-stale", ago != null && ago > 86400);
  }

  function render() {
    state.weeks = visibleWeeks();
    if (state.index >= state.weeks.length) state.index = Math.max(0, state.weeks.length - 1);
    if (state.index < 0) state.index = 0;

    const data = state.data;
    if (data) {
      el.seasonTitle.textContent = "Rookie Shot Timeline · " + (data.season_label || "");
      const metric = data.ranking_metric || "performance score";
      el.rankingNote.textContent = data.scope === "rookies"
        ? "ranked by " + metric + " (rookies)"
        : "ranked by " + metric + " (all players)";
      if (data.ranking_formula) el.rankingNote.title = data.ranking_formula;
      const totals = data.totals || {};
      el.footerStats.textContent =
        (totals.games || 0) + " games tracked · " + (totals.players || 0) + " players · " +
        (totals.shots || 0) + " shots · " + (totals.weeks || 0) + " weeks";
    }

    renderRail();
    renderFeatured();
    renderLeaderboard();
    renderGames();
    renderStatus();
  }

  /* ── Navigation ────────────────────────────────────────────────────────── */

  function readUrlState() {
    const params = new URLSearchParams(window.location.search);
    const phase = params.get("phase");
    if (phase === "all" || phase === "competitive") {
      state.phase = phase;
      document.querySelectorAll(".chip-btn[data-phase]").forEach((button) => {
        button.classList.toggle("is-active", button.dataset.phase === phase);
      });
    }
    const week = Number(params.get("week"));
    return Number.isFinite(week) && week > 0 ? week : null;
  }

  function writeUrlState() {
    const week = state.weeks[state.index];
    if (!week || !window.history || !window.history.replaceState) return;
    const params = new URLSearchParams(window.location.search);
    params.set("phase", state.phase);
    params.set("week", String(week.index));
    window.history.replaceState({}, "", window.location.pathname + "?" + params.toString());
  }

  function selectWeek(index, scroll) {
    if (!state.weeks.length) return;
    state.index = Math.min(Math.max(index, 0), state.weeks.length - 1);
    renderRail();
    renderFeatured();
    renderLeaderboard();
    writeUrlState();
    if (scroll !== false) {
      const chip = el.rail.querySelector(".week-chip.is-active");
      if (chip && chip.scrollIntoView) chip.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }
  }

  function togglePlay(force) {
    const shouldPlay = force == null ? !state.playing : force;
    state.playing = shouldPlay;
    el.play.innerHTML = state.playing ? "&#10073;&#10073;" : "&#9654;";
    el.play.setAttribute("aria-label", state.playing ? "Pause timeline" : "Play timeline");
    if (state.playTimer) {
      clearInterval(state.playTimer);
      state.playTimer = null;
    }
    if (state.playing) {
      state.playTimer = setInterval(() => {
        const next = state.index + 1;
        if (next >= state.weeks.length) {
          selectWeek(0);
        } else {
          selectWeek(next);
        }
      }, PLAY_MS);
    }
  }

  /* ── Data loading ──────────────────────────────────────────────────────── */

  function applyData(data, announce) {
    if (!data) return;
    const changed = state.lastSeen !== (data.generated_at || null);
    state.data = data;
    state.lastSeen = data.generated_at || null;
    if (changed || !state.rendered) {
      render();
      state.rendered = true;
    }
    if (announce && changed) toast("Timeline updated — new data loaded");
  }

  async function loadData(announce) {
    try {
      const response = await fetch(DATA_URL + "?t=" + Date.now(), { cache: "no-store" });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      applyData(data, announce);
      return true;
    } catch (error) {
      if (window.TIMELINE_DATA) {
        applyData(window.TIMELINE_DATA, announce);
        return true;
      }
      el.statusText.textContent = "data unavailable";
      el.statusPill.classList.add("is-error");
      return false;
    }
  }

  let toastTimer = null;
  function toast(message) {
    el.toast.textContent = message;
    el.toast.classList.add("is-visible");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.toast.classList.remove("is-visible"), 4200);
  }

  /* ── Events ────────────────────────────────────────────────────────────── */

  el.rail.addEventListener("click", (event) => {
    const chip = event.target.closest(".week-chip");
    if (!chip) return;
    togglePlay(false);
    selectWeek(Number(chip.dataset.index));
  });

  el.prev.addEventListener("click", () => { togglePlay(false); selectWeek(state.index - 1); });
  el.next.addEventListener("click", () => { togglePlay(false); selectWeek(state.index + 1); });
  el.play.addEventListener("click", () => togglePlay());
  el.refresh.addEventListener("click", () => loadData(false));

  document.querySelectorAll(".chip-btn[data-phase]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".chip-btn[data-phase]").forEach((other) => {
        other.classList.toggle("is-active", other === button);
      });
      state.phase = button.dataset.phase;
      const previous = state.weeks[state.index];
      state.weeks = visibleWeeks();
      const same = previous ? state.weeks.findIndex((week) => week.start === previous.start) : -1;
      state.index = same >= 0 ? same : Math.max(0, state.weeks.length - 1);
      render();
      writeUrlState();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") { togglePlay(false); selectWeek(state.index - 1); }
    if (event.key === "ArrowRight") { togglePlay(false); selectWeek(state.index + 1); }
    if (event.key === " ") { event.preventDefault(); togglePlay(); }
  });

  document.addEventListener("mouseover", (event) => {
    const shot = event.target.closest(".shot");
    if (!shot) return;
    const made = shot.dataset.made === "1";
    const far = shot.classList.contains("shot-far");
    el.tooltip.innerHTML =
      '<div class="tt-title">' + escapeHtml(shot.dataset.type || "shot") + " · " +
      escapeHtml(shot.dataset.distance || "0") + " ft</div>" +
      '<div class="tt-meta">' + escapeHtml(shot.dataset.date || "") +
      (far ? " · beyond half court" : "") + "</div>" +
      '<div class="' + (made ? "tt-made" : "tt-missed") + '">' +
      (made ? "✓ made" : "✕ missed") + "</div>";
    el.tooltip.classList.add("is-visible");
  });

  document.addEventListener("mousemove", (event) => {
    if (!el.tooltip.classList.contains("is-visible")) return;
    el.tooltip.style.left = event.clientX + "px";
    el.tooltip.style.top = event.clientY - 10 + "px";
  });

  document.addEventListener("mouseout", (event) => {
    if (event.target.closest(".shot")) el.tooltip.classList.remove("is-visible");
  });

  /* ── Boot ──────────────────────────────────────────────────────────────── */

  loadData(false).then((ok) => {
    if (!ok) return;
    const requestedWeek = readUrlState();
    const weeks = visibleWeeks();
    state.weeks = weeks;
    if (requestedWeek) {
      const found = weeks.findIndex((week) => week.index === requestedWeek);
      selectWeek(found >= 0 ? found : weeks.length - 1, false);
    } else {
      selectWeek(weeks.length - 1, false);
    }
    setInterval(() => loadData(true), POLL_MS);
    setInterval(renderStatus, 30000);
  });
})();
