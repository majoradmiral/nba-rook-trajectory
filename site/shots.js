/* All Rookie Shots — every shot attempt by every rookie on one half court.
 *
 * Data comes from site/data/shots.json (written by `python -m src.shot_map`).
 * The page polls that file so the view stays current without a reload, and
 * falls back to data/shots.js when opened straight from disk (file://).
 *
 * The court carries every shot in the current scope; each rookie owns a
 * colour, hovering a shot names the shooter and clicking a rookie isolates
 * their attempts.
 */

(function () {
  "use strict";

  const DATA_URL = "data/shots.json";
  const POLL_MS = 60000;
  const GOLDEN_ANGLE = 137.508;

  const state = {
    data: null,
    scope: { kind: "season" },
    player: null,
    search: "",
    pinned: null,
    lastSeen: null,
    rendered: false,
  };

  const el = {
    seasonTitle: document.getElementById("season-title"),
    scopeNote: document.getElementById("scope-note"),
    statusPill: document.getElementById("status-pill"),
    statusText: document.getElementById("status-text"),
    scopeTitle: document.getElementById("scope-title"),
    scopeMeta: document.getElementById("scope-meta"),
    courtWrap: document.getElementById("court-wrap"),
    playersList: document.getElementById("players-list"),
    search: document.getElementById("player-search"),
    clearPlayer: document.getElementById("clear-player"),
    scopeStats: document.getElementById("scope-stats"),
    rail: document.getElementById("week-rail"),
    weekNote: document.getElementById("week-note"),
    games: document.getElementById("games-list"),
    detailBody: document.getElementById("detail-body"),
    detailNote: document.getElementById("detail-note"),
    footerStats: document.getElementById("footer-stats"),
    tooltip: document.getElementById("tooltip"),
    toast: document.getElementById("toast"),
    refresh: document.getElementById("refresh-btn"),
  };

  const playersById = new Map();
  const colorByPlayer = new Map();

  /* ── Formatting ────────────────────────────────────────────────────────── */

  const one = (value) => (value == null ? "—" : Number(value).toFixed(1));
  const pct = (value) => (value == null ? "—" : (Number(value) * 100).toFixed(1) + "%");
  const plusMinus = (value) => {
    if (value == null) return "—";
    const number = Number(value);
    return (number > 0 ? "+" : "") + number.toFixed(1);
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* ── Data helpers ──────────────────────────────────────────────────────── */

  function weeks() {
    return (state.data && state.data.weeks) || [];
  }

  function games() {
    return (state.data && state.data.games) || [];
  }

  function players() {
    return (state.data && state.data.players) || [];
  }

  function shots() {
    return (state.data && state.data.shots) || [];
  }

  function playerName(playerId) {
    const player = playersById.get(playerId);
    return player ? player.name : playerId;
  }

  function colorFor(playerId) {
    return colorByPlayer.get(playerId) || "hsl(210 80% 62%)";
  }

  function assignColors(list) {
    colorByPlayer.clear();
    const ordered = list.slice().sort((a, b) =>
      b.shots - a.shots || a.name.localeCompare(b.name)
    );
    ordered.forEach((player, index) => {
      const hue = (index * GOLDEN_ANGLE) % 360;
      colorByPlayer.set(player.player_id, "hsl(" + hue.toFixed(1) + " 78% 62%)");
    });
  }

  function scopeShots() {
    const all = shots();
    if (state.scope.kind === "game") {
      return all.filter((shot) => shot.game_id === state.scope.gameId);
    }
    if (state.scope.kind === "week") {
      const week = weeks().find((item) => item.index === state.scope.index);
      if (!week) return all;
      return all.filter((shot) => shot.date >= week.start && shot.date <= week.end);
    }
    return all;
  }

  function scopeLabel() {
    if (state.scope.kind === "game") {
      const game = games().find((item) => item.game_id === state.scope.gameId);
      if (!game) return { title: "Game", meta: "" };
      return {
        title: game.away.abbr + " @ " + game.home.abbr,
        meta: game.date + " · " + game.season_type + " · " +
          game.away.score + "-" + game.home.score + " · " + game.shots + " rookie shot" +
          (game.shots === 1 ? "" : "s") + " · " + game.players + " rookie" +
          (game.players === 1 ? "" : "s"),
      };
    }
    if (state.scope.kind === "week") {
      const week = weeks().find((item) => item.index === state.scope.index);
      if (!week) return { title: "Week", meta: "" };
      return {
        title: "Week " + week.index + " · " + week.label,
        meta: week.season_types.join(" + ") + " · " + week.games + " game" +
          (week.games === 1 ? "" : "s") + " · " + week.shots + " rookie shot" +
          (week.shots === 1 ? "" : "s") + " · " + week.players + " rookie" +
          (week.players === 1 ? "" : "s"),
      };
    }
    const totals = (state.data && state.data.totals) || {};
    return {
      title: "Season " + ((state.data && state.data.season_label) || ""),
      meta: totals.shots + " rookie shot" + (totals.shots === 1 ? "" : "s") + " · " +
        totals.players_with_shots + " rookies · " + totals.games_with_shots + " games",
    };
  }

  /* ── Rendering ─────────────────────────────────────────────────────────── */

  function statCell(label, value, tone) {
    return (
      '<div class="stat"><span class="label">' + label + "</span>" +
      '<span class="value' + (tone ? " " + tone : "") + '">' + value + "</span></div>"
    );
  }

  function zoneCounts(list) {
    const zones = { rim: 0, mid: 0, three: 0 };
    let made = 0;
    list.forEach((shot) => {
      const distance = Number(shot.distance);
      if (shot.three || distance >= 22) zones.three += 1;
      else if (distance <= 8) zones.rim += 1;
      else zones.mid += 1;
      if (shot.made) made += 1;
    });
    return { zones, made };
  }

  function renderCourt(list) {
    if (!list.length) {
      el.courtWrap.innerHTML = '<div class="chart-empty">No rookie shot attempts in this scope.</div>';
      return;
    }

    // Only dim the others when the selected rookie actually shot in this
    // scope; otherwise the court would go fully faint and look broken.
    const isolate = state.player && list.some((shot) => shot.player_id === state.player)
      ? state.player
      : null;

    const byPlayer = new Map();
    list.forEach((shot) => {
      if (!byPlayer.has(shot.player_id)) byPlayer.set(shot.player_id, []);
      byPlayer.get(shot.player_id).push(shot);
    });

    const groups = [];
    byPlayer.forEach((playerShots, playerId) => {
      const dim = isolate && isolate !== playerId ? " is-dimmed" : "";
      const active = isolate === playerId ? " is-active" : "";
      const owner = playersById.get(playerId);
      const ownerLabel = owner ? owner.name + (owner.team ? " (" + owner.team + ")" : "") : playerId;
      const marks = playerShots.map((shot) =>
        Court.shotMarkup(shot, {
          attrs: {
            player: playerId,
            game: shot.game_id,
            period: shot.period,
            clock: shot.clock,
          },
          style: "--c:" + colorFor(playerId),
          tip: ownerLabel + " · " + shot.date,
        })
      );
      groups.push(
        '<g class="player-shots' + dim + active + '" data-player="' + escapeHtml(playerId) + '">' +
        marks.join("") +
        "</g>"
      );
    });

    el.courtWrap.innerHTML =
      '<svg class="court shotmap-court" viewBox="' + Court.COURT.viewBox +
      '" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Rookie shot chart">' +
      Court.courtMarkup() +
      groups.join("") +
      "</svg>";
  }

  function renderPlayers() {
    const needle = state.search.trim().toLowerCase();
    const list = players()
      .filter((player) => player.shots > 0)
      .filter((player) => {
        if (!needle) return true;
        return (
          player.name.toLowerCase().indexOf(needle) !== -1 ||
          String(player.team || "").toLowerCase().indexOf(needle) !== -1
        );
      })
      .sort((a, b) => b.shots - a.shots || a.name.localeCompare(b.name));

    if (!list.length) {
      el.playersList.innerHTML = '<div class="empty-state">No rookie matches that search.</div>';
      return;
    }

    el.playersList.innerHTML = list
      .map((player) => {
        const selected = state.player === player.player_id;
        const made = player.made;
        const ratio = player.shots ? (made / player.shots) * 100 : 0;
        return (
          '<button type="button" class="player-row' + (selected ? " is-selected" : "") + '"' +
          ' data-player="' + escapeHtml(player.player_id) + '">' +
          '<i class="swatch" style="background:' + colorFor(player.player_id) + '"></i>' +
          '<span class="pr-name">' + escapeHtml(player.name) + "</span>" +
          '<span class="pr-team">' + escapeHtml(player.team || "") + "</span>" +
          '<span class="pr-shots">' + player.shots + "</span>" +
          '<span class="pr-pct">' + ratio.toFixed(0) + "%</span>" +
          "</button>"
        );
      })
      .join("");

    const selected = el.playersList.querySelector(".player-row.is-selected");
    if (selected && selected.scrollIntoView) selected.scrollIntoView({ block: "nearest" });
  }

  function renderStats(list) {
    const { zones, made } = zoneCounts(list);
    const playersInScope = new Set(list.map((shot) => shot.player_id));
    const tone = made > list.length / 2 ? "pos" : made < list.length / 2 ? "neg" : "";
    el.scopeStats.innerHTML =
      statCell("FGA", list.length) +
      statCell("Made", made, tone) +
      statCell("FG%", list.length ? pct(made / list.length) : "—") +
      statCell("Rim", zones.rim) +
      statCell("Mid", zones.mid) +
      statCell("Three", zones.three) +
      statCell("Rookies", playersInScope.size);
  }

  function renderRail() {
    const chips = [];
    chips.push(
      '<button type="button" class="week-chip' +
      (state.scope.kind === "season" ? " is-active" : "") +
      '" role="tab" data-week="all">' +
      '<span class="wk">Full season</span>' +
      '<span class="wk-dates">' + escapeHtml((state.data && state.data.season_label) || "") + "</span>" +
      '<span class="wk-names">' + ((state.data && state.data.totals) || {}).shots + " rookie shots</span>" +
      '<span class="wk-phase">all weeks</span>' +
      "</button>"
    );
    weeks().forEach((week) => {
      const active = state.scope.kind === "week" && state.scope.index === week.index;
      const phase = week.season_types.indexOf("playoffs") !== -1
        ? "playoffs"
        : week.season_types.indexOf("regular") !== -1 ? "regular season" : "preseason";
      const phaseClass = phase === "regular season" ? "is-regular" : phase === "playoffs" ? "is-playoffs" : "";
      chips.push(
        '<button type="button" class="week-chip' + (active ? " is-active" : "") +
        '" role="tab" data-week="' + week.index + '">' +
        '<span class="wk">Week ' + week.index + "</span>" +
        '<span class="wk-dates">' + escapeHtml(week.label) + "</span>" +
        '<span class="wk-names">' + week.shots + " shots · " + week.players + " rookies</span>" +
        '<span class="wk-phase ' + phaseClass + '">' + escapeHtml(phase) + "</span>" +
        "</button>"
      );
    });
    el.rail.innerHTML = chips.join("");
  }

  function renderGames() {
    let list = games();
    if (state.scope.kind === "week") {
      const week = weeks().find((item) => item.index === state.scope.index);
      if (week) {
        list = list.filter((game) => game.date >= week.start && game.date <= week.end);
      }
    } else if (state.scope.kind === "game") {
      list = list.filter((game) => game.game_id === state.scope.gameId);
    }
    const withShots = list.filter((game) => game.shots > 0);
    el.weekNote.textContent = withShots.length
      ? withShots.length + " game" + (withShots.length === 1 ? "" : "s") + " with rookie shots"
      : "no games yet";
    if (!withShots.length) {
      el.games.innerHTML = '<div class="empty-state">No completed games with rookie shots in this scope.</div>';
      return;
    }
    el.games.innerHTML = withShots
      .slice()
      .reverse()
      .map((game) => {
        const active = state.scope.kind === "game" && state.scope.gameId === game.game_id;
        const awayWin = game.away.score > game.home.score;
        return (
          '<button type="button" class="game game-btn' + (active ? " is-active" : "") +
          '" data-game="' + escapeHtml(game.game_id) + '">' +
          '<span class="game-top"><span>' + escapeHtml(game.date) + "</span>" +
          "<span>" + escapeHtml(game.season_type) + "</span></span>" +
          '<span class="game-teams">' +
          '<span class="abbr away' + (awayWin ? " winner" : "") + '">' + escapeHtml(game.away.abbr) + "</span>" +
          '<span class="score' + (awayWin ? " winner" : "") + '">' + game.away.score + "</span>" +
          '<span class="vs">@</span>' +
          '<span class="score' + (!awayWin ? " winner" : "") + '">' + game.home.score + "</span>" +
          '<span class="abbr' + (!awayWin ? " winner" : "") + '">' + escapeHtml(game.home.abbr) + "</span>" +
          "</span>" +
          '<span class="game-shotcount">' + game.shots + " shots · " + game.players + " rookies</span>" +
          "</button>"
        );
      })
      .join("");
  }

  function renderDetail() {
    const shot = state.pinned;
    if (!shot) {
      el.detailNote.textContent = "hover or click a shot";
      el.detailBody.innerHTML = '<div class="empty-state">Pick a shot to see who took it.</div>';
      return;
    }
    const player = playersById.get(shot.player_id);
    const scopeList = scopeShots().filter((item) => item.player_id === shot.player_id);
    const { zones, made } = zoneCounts(scopeList);

    el.detailNote.textContent = shot.date + (shot.period ? " · Q" + shot.period : "") +
      (shot.clock ? " · " + shot.clock : "");
    el.detailBody.innerHTML =
      '<div class="detail-card">' +
      '<div class="detail-head">' +
      '<i class="swatch big" style="background:' + colorFor(shot.player_id) + '"></i>' +
      "<div>" +
      '<h3 class="player-name">' + escapeHtml(player ? player.name : shot.player_id) + "</h3>" +
      '<p class="player-team">' + escapeHtml(player ? player.team + " · " + player.position : "") + "</p>" +
      "</div>" +
      '<span class="detail-result ' + (shot.made ? "is-made" : "is-missed") + '">' +
      (shot.made ? "MADE" : "MISSED") + "</span>" +
      "</div>" +
      '<p class="detail-desc">' + escapeHtml(shot.description || (shot.type + " · " + shot.distance + " ft")) + "</p>" +
      '<div class="stat-strip">' +
      statCell("Type", escapeHtml(shot.type)) +
      statCell("Distance", one(shot.distance) + " ft") +
      statCell("FGA", scopeList.length) +
      statCell("FG%", scopeList.length ? pct(made / scopeList.length) : "—") +
      "</div>" +
      '<div class="zone-bar">' +
      zoneRow("Rim", zones.rim, scopeList.length) +
      zoneRow("Mid-range", zones.mid, scopeList.length) +
      zoneRow("Three", zones.three, scopeList.length) +
      "</div>" +
      (player
        ? '<div class="card-foot">' +
          "<span>Season " + one(player.points) + " PPG · " + one(player.rebounds) + " RPG · " +
          one(player.assists) + " APG · " + plusMinus(player.plus_minus) + " +/-</span>" +
          "<span>" + player.games + " game(s)</span>" +
          "</div>"
        : "") +
      "</div>";
  }

  function zoneRow(label, count, total) {
    const denominator = total || 1;
    const ratio = Math.min(100, (count / denominator) * 100);
    return (
      '<div class="zone"><span>' + label + "</span>" +
      '<span class="zone-track"><span class="zone-fill" style="width:' + ratio.toFixed(0) + '%"></span></span>' +
      '<span class="zone-val">' + count + "</span></div>"
    );
  }

  function renderStatus() {
    const data = state.data;
    if (!data) return;
    const generated = data.generated_at ? new Date(data.generated_at) : null;
    const ago = generated ? Math.max(0, Math.round((Date.now() - generated.getTime()) / 1000)) : null;
    const age = ago == null
      ? "unknown"
      : ago < 60
        ? "just now"
        : ago < 3600
          ? Math.round(ago / 60) + " min ago"
          : Math.round(ago / 3600) + " h ago";
    el.statusText.textContent = "updated " + age;
    el.statusPill.classList.toggle("is-stale", ago != null && ago > 86400);
  }

  function render() {
    const data = state.data;
    if (data) {
      el.seasonTitle.textContent = "All Rookie Shots · " + (data.season_label || "");
      el.scopeNote.textContent = data.scope === "rookies"
        ? "rookies only · colour-coded by shooter"
        : "all players · colour-coded by shooter";
      const totals = data.totals || {};
      el.footerStats.textContent =
        (totals.shots || 0) + " shots · " + (totals.players_with_shots || 0) + " rookies · " +
        (totals.games_with_shots || 0) + " games · " + (totals.weeks || 0) + " weeks";
    }

    playersById.clear();
    players().forEach((player) => playersById.set(player.player_id, player));
    assignColors(players());

    const list = scopeShots();
    const label = scopeLabel();
    el.scopeTitle.textContent = label.title;
    let meta = label.meta;
    if (state.player && !list.some((shot) => shot.player_id === state.player)) {
      meta += " · " + playerName(state.player) + " has no shots in this scope";
    }
    el.scopeMeta.textContent = meta;

    renderRail();
    renderCourt(list);
    renderPlayers();
    renderStats(list);
    renderGames();
    renderDetail();
    renderStatus();
  }

  /* ── State changes ─────────────────────────────────────────────────────── */

  function setScope(kind, value) {
    state.scope = kind === "week" ? { kind: "week", index: value } : kind === "game"
      ? { kind: "game", gameId: value }
      : { kind: "season" };
    state.pinned = null;
    render();
    writeUrlState();
  }

  function selectPlayer(playerId) {
    state.player = state.player === playerId ? null : playerId;
    render();
    writeUrlState();
  }

  /* ── Navigation ────────────────────────────────────────────────────────── */

  function readUrlState() {
    const params = new URLSearchParams(window.location.search);
    const week = Number(params.get("week"));
    const game = params.get("game");
    const player = params.get("player");
    return {
      week: Number.isFinite(week) && week > 0 ? week : null,
      game: game || null,
      player: player || null,
    };
  }

  function writeUrlState() {
    if (!window.history || !window.history.replaceState) return;
    const params = new URLSearchParams();
    if (state.scope.kind === "week") params.set("week", String(state.scope.index));
    if (state.scope.kind === "game") params.set("game", state.scope.gameId);
    if (state.player) params.set("player", state.player);
    const query = params.toString();
    window.history.replaceState(
      {},
      "",
      window.location.pathname + (query ? "?" + query : "")
    );
  }

  /* ── Tooltip ───────────────────────────────────────────────────────────── */

  function shotTipHtml(shot) {
    const player = playersById.get(shot.player_id);
    const owner = player ? player.name + (player.team ? " · " + player.team : "") : shot.player_id;
    return (
      '<div class="tt-title" style="color:' + colorFor(shot.player_id) + '">' + escapeHtml(owner) + "</div>" +
      '<div class="tt-meta">' + escapeHtml(shot.type) + " · " + escapeHtml(shot.distance) + " ft · " +
      escapeHtml(shot.date) + (shot.period ? " · Q" + shot.period : "") +
      (shot.clock ? " " + escapeHtml(shot.clock) : "") + "</div>" +
      '<div class="' + (shot.made ? "tt-made" : "tt-missed") + '">' +
      (shot.made ? "✓ made" : "✕ missed") + "</div>"
    );
  }

  function findShot(node) {
    const group = node.closest ? node.closest(".shot") : null;
    if (!group) return null;
    const playerId = group.getAttribute("data-player");
    const gameId = group.getAttribute("data-game");
    const distance = Number(group.getAttribute("data-distance"));
    const made = group.getAttribute("data-made") === "1";
    const type = group.getAttribute("data-type");
    const date = group.getAttribute("data-date");
    const period = Number(group.getAttribute("data-period")) || 0;
    const clock = group.getAttribute("data-clock") || "";
    const candidates = scopeShots().filter((shot) =>
      shot.player_id === playerId &&
      shot.game_id === gameId &&
      shot.made === (made ? 1 : 0) &&
      shot.type === type &&
      shot.date === date &&
      Math.abs(Number(shot.distance) - distance) < 0.05
    );
    return candidates[0] || null;
  }

  /* ── Events ────────────────────────────────────────────────────────────── */

  el.rail.addEventListener("click", (event) => {
    const chip = event.target.closest(".week-chip");
    if (!chip) return;
    if (chip.dataset.week === "all") {
      setScope("season");
      return;
    }
    setScope("week", Number(chip.dataset.week));
  });

  el.games.addEventListener("click", (event) => {
    const row = event.target.closest("[data-game]");
    if (!row) return;
    if (state.scope.kind === "game" && state.scope.gameId === row.dataset.game) {
      setScope("season");
      return;
    }
    setScope("game", row.dataset.game);
  });

  el.playersList.addEventListener("click", (event) => {
    const row = event.target.closest("[data-player]");
    if (!row) return;
    selectPlayer(row.dataset.player);
  });

  el.search.addEventListener("input", () => {
    state.search = el.search.value;
    renderPlayers();
  });

  el.clearPlayer.addEventListener("click", () => {
    state.player = null;
    state.pinned = null;
    render();
    writeUrlState();
  });

  el.courtWrap.addEventListener("mouseover", (event) => {
    const shot = findShot(event.target);
    if (!shot) return;
    el.tooltip.innerHTML = shotTipHtml(shot);
    el.tooltip.classList.add("is-visible");
  });

  el.courtWrap.addEventListener("mousemove", (event) => {
    if (!el.tooltip.classList.contains("is-visible")) return;
    el.tooltip.style.left = event.clientX + "px";
    el.tooltip.style.top = event.clientY - 10 + "px";
  });

  el.courtWrap.addEventListener("mouseout", (event) => {
    if (event.target.closest && event.target.closest(".shot")) {
      el.tooltip.classList.remove("is-visible");
    }
  });

  el.courtWrap.addEventListener("click", (event) => {
    const shot = findShot(event.target);
    if (!shot) return;
    state.pinned = shot;
    renderDetail();
    el.detailNote.textContent = shot.date + (shot.period ? " · Q" + shot.period : "") +
      (shot.clock ? " · " + shot.clock : "");
  });

  el.refresh.addEventListener("click", () => loadData(false));

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      state.player = null;
      state.pinned = null;
      render();
      writeUrlState();
      return;
    }
    if (event.key === "/" && document.activeElement !== el.search) {
      event.preventDefault();
      el.search.focus();
      return;
    }
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    const list = weeks();
    const current = state.scope.kind === "week"
      ? list.findIndex((week) => week.index === state.scope.index)
      : -1;
    const step = event.key === "ArrowRight" ? 1 : -1;
    const next = current + step;
    if (next < 0) {
      setScope("season");
      return;
    }
    if (next >= list.length) return;
    setScope("week", list[next].index);
  });

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
    if (announce && changed) toast("Shot map updated — new data loaded");
  }

  async function loadData(announce) {
    try {
      const response = await fetch(DATA_URL + "?t=" + Date.now(), { cache: "no-store" });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      applyData(data, announce);
      return true;
    } catch (error) {
      if (window.SHOTS_DATA) {
        applyData(window.SHOTS_DATA, announce);
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

  /* ── Boot ──────────────────────────────────────────────────────────────── */

  loadData(false).then((ok) => {
    if (!ok) return;
    const requested = readUrlState();
    if (requested.game && games().some((game) => game.game_id === requested.game)) {
      state.scope = { kind: "game", gameId: requested.game };
    } else if (requested.week && weeks().some((week) => week.index === requested.week)) {
      state.scope = { kind: "week", index: requested.week };
    }
    if (requested.player && playersById.has(requested.player)) {
      state.player = requested.player;
    }
    render();
    writeUrlState();
    setInterval(() => loadData(true), POLL_MS);
    setInterval(renderStatus, 30000);
  });
})();
