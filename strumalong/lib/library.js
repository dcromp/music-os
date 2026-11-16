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
  // Hand-picked collections (#103), by catalogue id. A song can sit in more than one. Order inside a
  // collection is easiest first. A collection with no songs left after the genre filter is dropped.
  const COLLECTIONS = [
    { id: "sixties-rock", title: "Rock 'n' roll and the 60s", note: "Where guitar rock started.", ids: [
      "elvis-presley-thats-all-right-youtube-20261026", "buddy-holly-peggy-sue-youtube-20261026", "ritchie-valens-la-bamba-youtube-20261026",
      "troggs-wild-thing-youtube-20261011", "everly-brothers-bye-bye-love-youtube-20261026", "beatles-eight-days-a-week-youtube-20261028",
      "beatles-twist-and-shout-youtube-20261011", "beatles-she-loves-you-youtube-20261028", "beatles-i-want-to-hold-your-hand-youtube-20261025",
      "beatles-help-youtube-20261025", "ccr-bad-moon-rising-youtube-20261024", "van-morrison-brown-eyed-girl-youtube-20261011",
      "mamas-and-the-papas-california-dreamin-youtube-20261028"] },
    { id: "classic-rock", title: "70s and 80s rock", note: "Classic rock radio.", ids: [
      "eric-clapton-lay-down-sally-youtube-20261026", "stealers-wheel-stuck-in-the-middle-with-you-youtube-20261025",
      "status-quo-rockin-all-over-the-world-youtube-20261028", "rolling-stones-dead-flowers-youtube-20261028", "rod-stewart-maggie-may-youtube-20261028",
      "ccr-wholl-stop-the-rain-youtube-20261028", "ccr-have-you-ever-seen-the-rain-youtube-20261024", "bob-dylan-knockin-heavens-door-youtube-20261011",
      "neil-young-heart-of-gold-youtube-20261025", "eagles-take-it-easy-youtube-20261025", "eagles-peaceful-easy-feeling-youtube-20261028",
      "fleetwood-mac-go-your-own-way-youtube-20261028", "kinks-lola-youtube-20261028", "queen-crazy-little-thing-called-love-youtube-20261025",
      "jam-thats-entertainment-youtube-20261028", "john-mellencamp-small-town-youtube-20261028", "traveling-wilburys-end-of-the-line-youtube-20261028",
      "traveling-wilburys-handle-with-care-youtube-20261028", "tom-petty-free-fallin-youtube-20261024", "tom-petty-learning-to-fly-youtube-20261025",
      "neil-young-rockin-in-the-free-world-youtube-20261028"] },
    { id: "harder-rock", title: "Harder rock", note: "Driving guitars. Dig in.", ids: [
      "troggs-wild-thing-youtube-20261011", "status-quo-rockin-all-over-the-world-youtube-20261028", "cranberries-zombie-youtube-20261024",
      "neil-young-rockin-in-the-free-world-youtube-20261028", "4-non-blondes-whats-up-youtube-20261025", "lifehouse-hanging-by-a-moment-youtube-20261028",
      "jake-bugg-lightning-bolt-youtube-20261028", "fratellis-chelsea-dagger-youtube-20261028", "spin-doctors-two-princes-youtube-20261028",
      "green-day-boulevard-of-broken-dreams-youtube-20261025"] },
    { id: "britpop-indie", title: "Britpop and indie", note: "Oasis, The Verve and friends.", ids: [
      "oasis-songbird-youtube-20261028", "oasis-wonderwall-youtube-20261010", "oasis-stand-by-me-youtube-20261028",
      "oasis-dont-look-back-in-anger-youtube-20261024", "verve-lucky-man-youtube-20261025", "verve-drugs-dont-work-youtube-20261028",
      "coldplay-yellow-youtube-20261025", "stereophonics-have-a-nice-day-youtube-20261028", "james-laid-youtube-20261028",
      "travis-why-does-it-always-rain-on-me-youtube-20261028", "jake-bugg-lightning-bolt-youtube-20261028", "fratellis-chelsea-dagger-youtube-20261028",
      "kooks-she-moves-in-her-own-way-youtube-20261028", "beautiful-south-rotterdam-or-anywhere-youtube-20261028", "amy-macdonald-this-is-the-life-youtube-20261028"] },
    { id: "pop-singalongs", title: "Pop singalongs", note: "Everyone knows the words.", ids: [
      "neil-diamond-sweet-caroline-youtube-20261025", "george-michael-faith-youtube-20261028", "bob-marley-three-little-birds-youtube-20261025",
      "hootie-and-the-blowfish-hold-my-hand-youtube-20261028", "smash-mouth-all-star-youtube-20261028", "taylor-swift-you-belong-with-me-youtube-20261028",
      "taylor-swift-we-are-never-getting-back-youtube-20261028", "taylor-swift-mine-youtube-20261028", "sugar-ray-every-morning-youtube-20261028",
      "uncle-kracker-follow-me-youtube-20261028", "barenaked-ladies-if-i-had-1000000-youtube-20261028", "magic-rude-youtube-20261028",
      "george-ezra-budapest-youtube-20261025", "jason-mraz-im-yours-youtube-20261025", "counting-crows-accidentally-in-love-youtube-20261028",
      "avril-lavigne-complicated-youtube-20261028", "eagle-eye-cherry-save-tonight-youtube-20261025", "natalie-imbruglia-torn-youtube-20261025",
      "lisa-loeb-stay-i-missed-you-youtube-20261028", "proclaimers-im-gonna-be-500-miles-youtube-20261025"] },
    { id: "country-folk", title: "Country and folk", note: "Storytelling songs with open chords.", ids: [
      "johnny-cash-jackson-youtube-20261026", "billy-ray-cyrus-achy-breaky-heart-youtube-20261026", "john-denver-country-roads-youtube-20261024",
      "old-crow-medicine-show-wagon-wheel-youtube-20261025", "jimmy-buffett-margaritaville-youtube-20261028", "shania-twain-youre-still-the-one-youtube-20261028",
      "harry-chapin-cats-in-the-cradle-youtube-20261028", "noah-kahan-stick-season-youtube-20261028", "lumineers-stubborn-love-youtube-20261028",
      "lumineers-ho-hey-youtube-20261025", "phillip-phillips-home-youtube-20261028", "paul-simon-me-and-julio-down-by-the-schoolyard-youtube-20261028",
      "cat-stevens-wild-world-youtube-20261025", "cat-stevens-peace-train-youtube-20261028", "james-blunt-bonfire-heart-youtube-20261028"] },
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
    if (favs.length) out.push({ id: "favourites", title: "Your favourites", note: favs.length === 1 ? "1 song" : `${favs.length} songs`, songs: favs });
    const easy = songs.filter(s => levelOf(s) <= EASY_MAX_LEVEL && changesOf(s) !== Infinity)
      .sort((a, b) => changesOf(a) - changesOf(b) || byLevelThenOrder(a, b)).slice(0, EASY_LIMIT);
    out.push({ id: "easy", title: "Easy to jump into", note: "Few chord changes: just strum.", songs: easy });
    for (const c of COLLECTIONS) {
      const members = c.ids.map(id => byId.get(id)).filter(Boolean).sort(byLevelThenOrder);
      out.push({ id: c.id, title: c.title, note: c.note, songs: members });
    }
    const themed = new Set();
    for (const t of THEMES) {
      const members = songs.filter(s => t.levels.includes(levelOf(s))).sort(byLevelThenOrder);
      members.forEach(s => themed.add(s.id));
      out.push({ id: t.id, title: t.title, note: t.note, songs: members });
    }
    out.push({ id: "other", title: "Other songs", note: "", songs: songs.filter(s => !themed.has(s.id)).sort(byOrder) });
    return out.filter(shelf => shelf.songs.length);
  }

  // One shelf by id with every song, for "See all" (null if it is empty or unknown).
  function shelf(catalogue, favouriteIds, id) {
    return shelves(catalogue, favouriteIds).find(x => x.id === id) || null;
  }

  // A–Z (#103): songs sorted by title or artist, ignoring a leading "The" or "A", grouped under their first letter
  // ("#" for digits). by: "title" | "artist". Returns [{letter, songs}].
  const sortKey = text => fold(text).replace(/^(the|a) /, "");
  function alphabetical(songs, by) {
    const field = by === "artist" ? "artist" : "title";
    const other = field === "title" ? "artist" : "title";
    const sorted = (songs || []).slice().sort((a, b) => sortKey(a[field]).localeCompare(sortKey(b[field])) || sortKey(a[other]).localeCompare(sortKey(b[other])));
    const groups = [];
    for (const s of sorted) {
      const first = sortKey(s[field]).charAt(0).toUpperCase();
      const letter = /[A-Z]/.test(first) ? first : "#";
      if (!groups.length || groups[groups.length - 1].letter !== letter) groups.push({ letter, songs: [] });
      groups[groups.length - 1].songs.push(s);
    }
    return groups;
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

  // Genre filter (home page): "rock" or "pop" keeps songs with that tag; anything else ("all") keeps every song.
  const GENRES = ["rock", "pop"];
  function byGenre(songs, genre) {
    return GENRES.includes(genre) ? songs.filter(s => s && s.genre === genre) : songs;
  }

  // Core shapes of the songs the learner has played to the end. plays: {id: count}.
  function knownShapes(songs, plays) {
    const known = new Set();
    for (const s of songs || []) if (plays && plays[s.id] > 0) shapesOf(s).forEach(c => known.add(c));
    return known;
  }

  // The one line under the video: {text, fresh}. With nothing played yet every shape would read as new, so it only names them.
  const COUNT_WORDS = ["", "One", "Two", "Three", "Four", "Five", "Six"];
  function shapeLine(shapes, known) {
    const list = Array.isArray(shapes) ? shapes : [];
    if (!list.length) return { text: "Song breakdown", fresh: [] };
    const count = n => COUNT_WORDS[n] || String(n);
    const noun = n => n === 1 ? "shape" : "shapes";
    if (!known || !known.size) return { text: `${count(list.length)} ${noun(list.length)}: ${list.join(", ")}`, fresh: [] };
    const fresh = list.filter(c => !known.has(c));
    if (!fresh.length) return { text: `${count(list.length)} ${noun(list.length)} you know`, fresh };
    return { text: `${count(fresh.length)} new ${noun(fresh.length)} here: ${fresh.join(", ")}`, fresh };
  }

  // The chord sequence covering the most of a timeline ({label, s, e} events), for the breakdown.
  // Shortest wins a tie, then earliest. Returns {chords: [{label, seconds}], repeats, coverage} or null if nothing repeats.
  const LOOP_MIN = 2, LOOP_MAX = 8;
  function commonLoop(events) {
    const seq = [];
    for (const e of events || []) {
      if (e.label === "N" || e.label === "X") continue;
      const prev = seq[seq.length - 1];
      if (prev && prev.label === e.label) prev.seconds += e.e - e.s;
      else seq.push({ label: e.label, seconds: e.e - e.s });
    }
    let best = null;
    for (let n = LOOP_MIN; n <= LOOP_MAX; n++) {
      const found = new Map(); // sequence -> start positions, none overlapping
      for (let i = 0; i + n <= seq.length; i++) {
        const key = seq.slice(i, i + n).map(c => c.label).join("|");
        const starts = found.get(key) || [];
        if (!starts.length || i >= starts[starts.length - 1] + n) starts.push(i);
        found.set(key, starts);
      }
      for (const starts of found.values()) {
        if (starts.length >= 2 && (!best || starts.length * n > best.starts.length * best.n)) best = { n, starts };
      }
    }
    if (!best) return null;
    const { n, starts } = best;
    const chords = seq.slice(starts[0], starts[0] + n).map((c, k) => ({ label: c.label,
      seconds: starts.reduce((sum, i) => sum + seq[i + k].seconds, 0) / starts.length }));
    return { chords, repeats: starts.length, coverage: starts.length * n / seq.length };
  }

  return { search, shelves, shelf, alphabetical, COLLECTIONS, similar, surprise, fold, byGenre, GENRES, knownShapes, shapeLine, commonLoop };
});
