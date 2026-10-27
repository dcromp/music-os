/* Strum Along library: search, shelves, "Another like this" and "Surprise me" (Jukebox journey, #53).
 * UMD: window.StrumLibrary in the browser, module.exports under node. Pure: no DOM, storage or network.
 * Songs are catalogue summaries from songs/index.json ({id, title, artist, group, level, order, core_shapes}). */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.StrumLibrary = api;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";

  const SURPRISE_MIN_LEVEL = 2; // a new learner's Surprise me still reaches the open-chord songs
  const levelOf = s => Number.isInteger(s && s.level) ? s.level : 99;
  const orderOf = s => typeof (s && s.order) === "number" ? s.order : 999;
  const shapesOf = s => Array.isArray(s && s.core_shapes) ? s.core_shapes : [];
  const byOrder = (a, b) => orderOf(a) - orderOf(b) || String(a.title).localeCompare(String(b.title));

  // Lower case, accents and apostrophes removed, everything else non-alphanumeric is a space.
  function fold(text) {
    return String(text || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .replace(/['’`]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
  }

  // Songs whose title or artist contains every word of the query, in catalogue order. Empty query: [].
  function search(songs, query) {
    const words = fold(query).split(" ").filter(Boolean);
    if (!words.length) return [];
    return songs.filter(s => { const hay = ` ${fold(s.title)} ${fold(s.artist)}`; return words.every(w => hay.includes(w)); });
  }

  // Themed shelves (prototype A, #53). Difficulty still rises shelf by shelf, but by theme, not level number.
  const EASY_LIMIT = 10;
  const EASY_MAX_LEVEL = 3;
  const THEMES = [
    { id: "three-chord", title: "Three-chord classics", note: "First chords: A, D, E, Em and Am.", levels: [1] },
    { id: "campfire", title: "Campfire open chords", note: "G, C and friends, with more changes.", levels: [2, 3] },
    { id: "barre", title: "Barre-chord songs", note: "F, Bm and full barre shapes.", levels: [4, 5] },
  ];
  const changesOf = s => typeof (s && s.changes_per_min) === "number" ? s.changes_per_min : Infinity;
  const byLevelThenOrder = (a, b) => levelOf(a) - levelOf(b) || byOrder(a, b);

  // [{id, title, note, songs}]: favourites (saved order, listed songs only); "Easy to jump into" (the calmest
  // songs up to level 3, fewest chord changes a minute first); the themed level shelves; then "Other songs"
  // for any song without a known level. Songs appear on Easy and on their themed shelf. Empty shelves are dropped.
  function shelves(catalogue, favouriteIds) {
    const songs = Array.isArray(catalogue && catalogue.songs) ? catalogue.songs : [];
    const byId = new Map(songs.map(s => [s.id, s]));
    const out = [];
    const favs = (favouriteIds || []).map(id => byId.get(id)).filter(Boolean);
    if (favs.length) out.push({ id: "favourites", title: "★ Your favourites", note: "", songs: favs });
    const easy = songs.filter(s => levelOf(s) <= EASY_MAX_LEVEL && changesOf(s) !== Infinity)
      .sort((a, b) => changesOf(a) - changesOf(b) || byLevelThenOrder(a, b)).slice(0, EASY_LIMIT);
    out.push({ id: "easy", title: "Easy to jump into", note: "Few chord changes: just strum.", songs: easy });
    const themed = new Set();
    for (const t of THEMES) {
      const members = songs.filter(s => t.levels.includes(levelOf(s))).sort(byLevelThenOrder);
      members.forEach(s => themed.add(s.id));
      out.push({ id: t.id, title: t.title, note: t.note, songs: members });
    }
    out.push({ id: "other", title: "Other songs", note: "", songs: songs.filter(s => !themed.has(s.id)).sort(byOrder) });
    return out.filter(shelf => shelf.songs.length);
  }

  // Up to `limit` songs sharing at least one core shape with `song` and at most one level harder:
  // most shared shapes first, then fewest new shapes, then easier, then catalogue order.
  function similar(songs, song, limit) {
    if (!song) return [];
    const mine = new Set(shapesOf(song));
    return songs.filter(o => o.id !== song.id && levelOf(o) <= levelOf(song) + 1)
      .map(o => { const shared = shapesOf(o).filter(c => mine.has(c)).length; return { o, shared, fresh: shapesOf(o).length - shared }; })
      .filter(x => x.shared > 0)
      .sort((a, b) => b.shared - a.shared || a.fresh - b.fresh || levelOf(a.o) - levelOf(b.o) || byOrder(a.o, b.o))
      .slice(0, limit === undefined ? 5 : limit).map(x => x.o);
  }

  // A random song no harder than the hardest level the learner has played (at least SURPRISE_MIN_LEVEL),
  // avoiding the song just played when anything else qualifies. options: {lastId, plays: {id: count}, rng}.
  function surprise(songs, options) {
    const o = options || {};
    if (!songs || !songs.length) return null;
    const rng = typeof o.rng === "function" ? o.rng : Math.random;
    const levels = new Map(songs.map(s => [s.id, levelOf(s)]));
    const played = Object.keys(o.plays || {}).map(id => levels.get(id)).filter(l => l !== undefined && l !== 99);
    const cap = Math.max(SURPRISE_MIN_LEVEL, ...played);
    const fresh = songs.filter(s => s.id !== o.lastId);
    const atLevel = fresh.filter(s => levelOf(s) <= cap);
    const pool = atLevel.length ? atLevel : fresh.length ? fresh : songs;
    return pool[Math.min(pool.length - 1, Math.floor(rng() * pool.length))];
  }

  return { search, shelves, similar, surprise, fold };
});
