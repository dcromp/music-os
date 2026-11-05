"use strict";
// Tests for strumalong/lib/library.js: search, shelves, similar songs and Surprise me.
// Run: node strumalong/test/run.js (or this file directly).
const assert = require("node:assert/strict");
const { search, shelves, similar, surprise, byGenre, knownShapes, shapeLine, commonLoop } = require("../lib/library.js");

const results = { passed: 0, failed: [] };
function test(name, fn) {
  try { fn(); results.passed++; }
  catch (error) { results.failed.push(name); console.error(`  FAIL ${name}\n    ${error && error.stack ? error.stack.split("\n").slice(0, 3).join("\n    ") : error}`); }
}

const S = (id, level, shapes, extra = {}) => ({ id, title: id, artist: "Band", group: `level-${level}`, level, order: 1, core_shapes: shapes, ...extra });
const songs = [
  S("wild-thing", 1, ["A", "D", "E"], { title: "Wild Thing", artist: "The Troggs", order: 2 }),
  S("thats-all-right", 1, ["A", "D", "E"], { title: "That's All Right", artist: "Elvis Presley", order: 1 }),
  S("achy", 1, ["E", "A", "Am"], { order: 3 }),
  S("yellow", 2, ["G", "C", "D"]),
  S("brown-eyed", 2, ["G", "C", "D", "Em"]),
  S("sweet-home", 2, ["D", "C", "G"]),
  S("creep", 5, ["G", "B", "C", "Cm"]),
  S("wonderwall", 3, ["Em", "G", "D", "A"], { title: "Wonderwall", artist: "Oasis" }),
];
const groups = [1, 2, 3, 4, 5].map(l => ({ id: `level-${l}`, level: l, title: `Level ${l}`, note: `note ${l}` }));
const ids = list => list.map(s => s.id);

test("search matches every word against title and artist, ignoring case, accents and apostrophes", () => {
  assert.deepEqual(ids(search(songs, "wild")), ["wild-thing"]);
  assert.deepEqual(ids(search(songs, "troggs THING")), ["wild-thing"]);
  assert.deepEqual(ids(search(songs, "thats all")), ["thats-all-right"]);
  assert.deepEqual(ids(search(songs, "Élvis")), ["thats-all-right"]);
  assert.deepEqual(ids(search(songs, "oasis wild")), []);
  assert.deepEqual(search(songs, "   "), []);
});

test("shelves: favourites, Easy to jump into, then themed shelves rising in difficulty", () => {
  const out = shelves({ groups, songs }, ["yellow", "gone", "wild-thing"]);
  assert.deepEqual(out.map(s => s.id), ["favourites", "three-chord", "campfire", "barre"], "no Easy shelf without change rates");
  assert.deepEqual(ids(out[0].songs), ["yellow", "wild-thing"]);
  assert.deepEqual(ids(out[1].songs), ["thats-all-right", "wild-thing", "achy"]);
  assert.deepEqual(ids(out[2].songs), ["brown-eyed", "sweet-home", "yellow", "wonderwall"], "levels 2-3, level then order then title");
  assert.deepEqual(ids(out[3].songs), ["creep"]);
  assert.ok(out.every(s => !/level/i.test(s.title)), "no level numbers in shelf titles");
  assert.equal(shelves({ groups, songs }, []).some(s => s.id === "favourites"), false);
});

test("Easy to jump into: up to ten songs at level 3 or below, fewest changes a minute first", () => {
  const many = songs.map((s, i) => ({ ...s, changes_per_min: [12, 8, 20, 9, 30, 11, 5, 10][i] }));
  const easy = shelves({ songs: many }, []).find(s => s.id === "easy");
  assert.deepEqual(ids(easy.songs), ["thats-all-right", "yellow", "wonderwall", "sweet-home", "wild-thing", "achy", "brown-eyed"]);
  assert.ok(!ids(easy.songs).includes("creep"), "barre songs are not easy, however calm");
  const lots = Array.from({ length: 15 }, (_, i) => S(`s${i}`, 1, ["A"], { changes_per_min: i }));
  assert.equal(shelves({ songs: lots }, []).find(s => s.id === "easy").songs.length, 10);
  assert.equal(shelves({ songs }, []).some(s => s.id === "easy"), false, "no shelf without change rates");
});

test("songs without a known level go on an 'Other songs' shelf", () => {
  const out = shelves({ songs: songs.concat({ id: "mystery", title: "Mystery", core_shapes: [] }) }, []);
  assert.deepEqual(ids(out[out.length - 1].songs), ["mystery"]);
});

test("similar: shares chords, at most one level harder, most shared first, never itself", () => {
  const out = ids(similar(songs, songs.find(s => s.id === "yellow"), 5));
  assert.deepEqual(out, ["sweet-home", "brown-eyed", "wonderwall", "thats-all-right", "wild-thing"]);
  assert.ok(!out.includes("creep"), "level 5 is too far above level 2");
  assert.ok(!out.includes("yellow"));
  assert.deepEqual(ids(similar(songs, songs[0], 2)), ["thats-all-right", "achy"]);
  assert.deepEqual(similar(songs, null, 5), []);
});

test("surprise: random song up to the learner's level (at least 2), never the one just played", () => {
  const first = surprise(songs, { lastId: "achy", plays: {}, rng: () => 0 });
  assert.equal(first.id, "wild-thing");
  const pool = new Set();
  for (let i = 0; i < 40; i++) pool.add(surprise(songs, { lastId: "yellow", plays: {}, rng: () => i / 40 }).id);
  assert.deepEqual([...pool].sort(), ["achy", "brown-eyed", "sweet-home", "thats-all-right", "wild-thing"]);
  const played = new Set();
  for (let i = 0; i < 40; i++) played.add(surprise(songs, { plays: { wonderwall: 1 }, rng: () => i / 40 }).id);
  assert.ok(played.has("wonderwall") && !played.has("creep"));
  assert.equal(surprise([songs[0]], { lastId: "wild-thing", rng: () => 0 }).id, "wild-thing");
  assert.equal(surprise([], {}), null);
});

test("byGenre keeps one genre's songs; all, unknown or missing genres keep every song", () => {
  const tagged = [S("a", 1, ["A"], { genre: "rock" }), S("b", 2, ["G"], { genre: "pop" }), S("c", 2, ["G"])];
  assert.deepEqual(ids(byGenre(tagged, "rock")), ["a"]);
  assert.deepEqual(ids(byGenre(tagged, "pop")), ["b"]);
  assert.deepEqual(ids(byGenre(tagged, "all")), ["a", "b", "c"]);
  assert.deepEqual(ids(byGenre(tagged, "jazz")), ["a", "b", "c"]);
  assert.deepEqual(ids(byGenre(tagged, undefined)), ["a", "b", "c"]);
});

test("knownShapes collects the core shapes of finished songs only", () => {
  const list = [S("a", 1, ["A", "D"]), S("b", 2, ["G", "C"]), S("c", 2, ["Em"])];
  assert.deepEqual([...knownShapes(list, { a: 2, c: 1 })].sort(), ["A", "D", "Em"]);
  assert.equal(knownShapes(list, {}).size, 0);
  assert.equal(knownShapes(list, undefined).size, 0);
  assert.equal(knownShapes(list, { gone: 3 }).size, 0);
});

test("shapeLine says what is relevant: known, new, or nothing to compare yet", () => {
  assert.deepEqual(shapeLine(["A", "D", "E"], new Set(["A", "D", "E", "G"])), { text: "Three shapes you know", fresh: [] });
  assert.deepEqual(shapeLine(["A", "D", "E"], new Set(["A", "E"])), { text: "One new shape here: D", fresh: ["D"] });
  assert.deepEqual(shapeLine(["A", "D", "E"], new Set(["A"])), { text: "Two new shapes here: D, E", fresh: ["D", "E"] });
  assert.deepEqual(shapeLine(["A"], new Set(["A"])), { text: "One shape you know", fresh: [] });
  // No finished songs yet: every shape would read as new, so just name them.
  assert.deepEqual(shapeLine(["A", "D", "E"], new Set()), { text: "Three shapes: A, D, E", fresh: [] });
  assert.deepEqual(shapeLine([], new Set(["A"])), { text: "Song breakdown", fresh: [] });
  assert.equal(shapeLine(["A", "B", "C", "D", "E", "F", "G"], new Set()).text, "7 shapes: A, B, C, D, E, F, G");
});

const events = labels => labels.map((label, i) => ({ label, s: i * 2, e: i * 2 + 2 }));
const loopLabels = loop => loop.chords.map(c => c.label);

test("commonLoop finds the shortest sequence that covers the most of the song", () => {
  const loop = commonLoop(events(["G", "D", "Em", "C", "G", "D", "Em", "C", "G", "D", "Em", "C"]));
  assert.deepEqual(loopLabels(loop), ["G", "D", "Em", "C"]);
  assert.equal(loop.repeats, 3);
  assert.equal(loop.coverage, 1);
  assert.deepEqual(loopLabels(commonLoop(events(["A", "D", "A", "D", "A", "D"]))), ["A", "D"], "not A D A D");
});

test("commonLoop reports partial coverage, and the length of each chord in the loop", () => {
  const verse = [{ label: "A", s: 0, e: 8 }, { label: "D", s: 8, e: 10 }, { label: "A", s: 10, e: 14 }, { label: "D", s: 14, e: 20 }];
  const loop = commonLoop(verse.concat(events(["E", "F#", "B", "C#"]).map(e => ({ ...e, s: e.s + 20, e: e.e + 20 }))));
  assert.deepEqual(loop.chords, [{ label: "A", seconds: 6 }, { label: "D", seconds: 4 }]);
  assert.equal(loop.repeats, 2);
  assert.equal(loop.coverage, 0.5);
});

test("commonLoop skips no-chord events, merges what they split, and gives up when nothing repeats", () => {
  const gaps = events(["G", "N", "G", "C", "X", "G", "C", "N"]);
  assert.deepEqual(loopLabels(commonLoop(gaps)), ["G", "C"]);
  assert.equal(commonLoop(events(["A", "B", "C", "D", "E"])), null);
  assert.equal(commonLoop([]), null);
  assert.equal(commonLoop(undefined), null);
});

console.log(`library.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`library.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
