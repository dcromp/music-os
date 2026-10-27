"use strict";
// Tests for strumalong/lib/session.js through its interface, using a fake player and Map storage.
// Run: node strumalong/test/run.js (or this file directly).
const assert = require("node:assert/strict");
const core = require("../lib/core.js");
const { createStore, createSession, mapStorage, PREFIX } = require("../lib/session.js");

const results = { passed: 0, failed: [] };
function test(name, fn) {
  try { fn(); results.passed++; }
  catch (error) { results.failed.push(name); console.error(`  FAIL ${name}\n    ${error && error.stack ? error.stack.split("\n").slice(0, 3).join("\n    ") : error}`); }
}
const close = (actual, expected, eps = 1e-9) => assert.ok(Math.abs(actual - expected) <= eps, `${actual} != ${expected}`);

// --- Adapters --------------------------------------------------------------------------------
// Fake player: scripted clock (time) and duration (length); records every call; any method named in `throws` throws.
function fakePlayer(init = {}) {
  const p = { time: 0, length: 0, rate: 1, rates: [0.5, 1], calls: [], throws: new Set(), ...init };
  const call = (name, value) => (...args) => {
    p.calls.push([name, ...args]);
    if (p.throws.has(name)) throw new Error(`${name} failed`);
    return typeof value === "function" ? value(...args) : value;
  };
  Object.assign(p, {
    currentTime: call("currentTime", () => p.time), duration: call("duration", () => p.length),
    playbackRate: call("playbackRate", () => p.rate), availableRates: call("availableRates", () => p.rates),
    seekTo: call("seekTo", s => { p.time = s; }), cue: call("cue"), play: call("play"), pause: call("pause"),
    setRate: call("setRate", r => { p.rate = r; }), destroy: call("destroy"),
  });
  p.called = name => p.calls.filter(c => c[0] === name);
  return p;
}
const raw = (map, key) => map.get(PREFIX + key);
const stored = (map, key) => JSON.parse(raw(map, key));

// --- Synthetic song ----------------------------------------------------------------------------
const vid = c => c.repeat(11);
function song(extra = {}) {
  return {
    id: "synthetic", capo: 0, recording: { duration_seconds: 120 },
    rhythm: { bpm: 120, beats_per_bar: 4, bar_phase: 0, bar_phase_confident: true },
    beats: Array.from({ length: 200 }, (_, i) => 1 + 0.5 * i),
    chords: [{ s: 0, e: 1, l: "N" }, { s: 1, e: 30, l: "G7" }, { s: 30, e: 120, l: "Am7" }],
    videos: [
      { video_id: vid("a"), kind: "analysed", offset_seconds: 0, duration_seconds: 120 },
      { video_id: vid("b"), kind: "official", offset_seconds: 1.5, duration_seconds: 125 },
    ],
    strumming: { patterns: [{ id: "start", counts: ["1", "2", "3", "4"], strokes: ["D", "D", "D", "D"] },
      { id: "next", counts: ["1", "&", "2", "&"], strokes: ["D", "U", "D", "U"] }, { id: "broken", strokes: [] }] },
    ...extra,
  };
}
function setup(opts = {}) {
  const map = opts.map || new Map();
  const store = createStore(mapStorage(map));
  const clock = { now: 0 };
  const session = createSession({ song: opts.song || song(), store, resume: opts.resume, now: () => clock.now });
  const player = fakePlayer(opts.player);
  if (opts.attach !== false) { session.attach(player); session.playerReady(); }
  return { map, store, session, player, clock };
}

// --- Storage: keys, format, sanitising -----------------------------------------------------------
test("store reads the v1 keys and JSON a learner already has saved", () => {
  const map = new Map([
    [PREFIX + "settings", JSON.stringify({ quality: "full", view: "sounding", diagrams: false, patterns: { synthetic: "next" } })],
    [PREFIX + "latency", "120"],
    [PREFIX + "offset:" + vid("a"), "-350"],
    [PREFIX + "last", JSON.stringify({ id: "synthetic", t: 42 })],
  ]);
  const store = createStore(mapStorage(map));
  assert.deepEqual({ ...store.settings(), patterns: { ...store.settings().patterns } },
    { quality: "full", view: "sounding", diagrams: false, patterns: { synthetic: "next" } });
  assert.equal(store.latency(), 120);
  assert.equal(store.nudge(vid("a")), -350);
  assert.deepEqual(store.resumePoint([{ id: "synthetic", duration_seconds: 120 }]), { song: { id: "synthetic", duration_seconds: 120 }, t: 42 });
});

test("store writes exactly the v1 key names and JSON shapes", () => {
  const map = new Map();
  const store = createStore(mapStorage(map));
  store.setQuality("full");
  store.setPattern("song-1", "next");
  store.setLatency(75);
  store.setNudge(vid("a"), 250);
  store.saveLast("song-1", 33);
  assert.deepEqual([...map.keys()].sort(), [PREFIX + "last", PREFIX + "latency", PREFIX + "offset:" + vid("a"), PREFIX + "settings"].sort());
  assert.equal(raw(map, "settings"), JSON.stringify({ quality: "full", view: "shapes", diagrams: true, patterns: { "song-1": "next" } }));
  assert.equal(raw(map, "latency"), "75");
  assert.equal(raw(map, "offset:" + vid("a")), "250");
  assert.equal(raw(map, "last"), JSON.stringify({ id: "song-1", t: 33 }));
});

test("settings are sanitised: unknown values fall back, non-string patterns are dropped", () => {
  const map = new Map([[PREFIX + "settings", JSON.stringify({ quality: "max", view: 7, diagrams: 0, patterns: { a: "x", b: 3, c: null } })]]);
  const s = createStore(mapStorage(map)).settings();
  assert.equal(s.quality, "core");
  assert.equal(s.view, "shapes");
  assert.equal(s.diagrams, true); // only an explicit false turns diagrams off
  assert.deepEqual({ ...s.patterns }, { a: "x" });
  for (const bad of ["not json", "null", "[1,2]", '"text"']) {
    const t = createStore(mapStorage(new Map([[PREFIX + "settings", bad]]))).settings();
    assert.equal(t.quality, "core", bad);
    assert.deepEqual({ ...t.patterns }, {}, bad);
  }
  const store = createStore(mapStorage(new Map()));
  assert.equal(store.setQuality("bogus").quality, "core");
  assert.equal(store.setView("sounding").view, "sounding");
  assert.throws(() => { "use strict"; store.settings().quality = "full"; }, TypeError);
});

test("latency and per-video nudge are clamped integers; garbage reads as 0", () => {
  const map = new Map([[PREFIX + "latency", "5000"], [PREFIX + "offset:" + vid("a"), '"abc"'], [PREFIX + "offset:" + vid("b"), "-99999"]]);
  const store = createStore(mapStorage(map));
  assert.equal(store.latency(), 1000);
  assert.equal(store.nudge(vid("a")), 0);
  assert.equal(store.nudge(vid("b")), -30000);
  assert.equal(store.setLatency(-1234.6), -1000);
  assert.equal(store.setLatency(12.6), 13);
  assert.equal(store.nudge(null), 0);
});

test("a throwing or missing store forgets quietly instead of breaking the app", () => {
  const broken = { getItem() { throw new Error("SecurityError"); }, setItem() { throw new Error("QuotaExceeded"); } };
  const store = createStore(broken);
  assert.equal(store.settings().quality, "core");
  assert.equal(store.latency(), 0);
  assert.doesNotThrow(() => { store.setQuality("full"); store.saveLast("x", 1); store.setNudge(vid("a"), 50); });
  assert.equal(store.settings().quality, "full"); // still applies for this page view
  assert.equal(store.resumePoint([{ id: "x" }]), null);
});

test("resume point: the 5 s minimum and the 5 s end window", () => {
  const songs = [{ id: "s", duration_seconds: 100 }, { id: "nodur" }];
  const at = (id, t) => createStore(mapStorage(new Map([[PREFIX + "last", JSON.stringify({ id, t })]]))).resumePoint(songs);
  assert.equal(at("s", 4.9).t, 0);
  assert.equal(at("s", 5).t, 5);
  assert.equal(at("s", 94.9).t, 94.9);
  assert.equal(at("s", 95).t, 0);
  assert.equal(at("s", "12").t, 0);
  assert.equal(at("nodur", 500).t, 500);
  assert.equal(at("gone", 30), null);
  assert.equal(createStore(mapStorage(new Map())).resumePoint(songs), null);
});

// --- Session: start, resume, cue time ------------------------------------------------------------
test("starts on the first embeddable video and loads its saved nudge", () => {
  const s = song();
  s.videos.unshift({ video_id: vid("z"), kind: "analysed", embeddable: false }, { video_id: "short", kind: "bad" });
  const map = new Map([[PREFIX + "offset:" + vid("a"), "400"]]);
  const { session } = setup({ song: s, map, attach: false });
  assert.equal(session.video.video_id, vid("a"));
  assert.equal(session.videos.length, 3); // the malformed id is dropped
  assert.equal(session.nudgeMs, 400);
  assert.deepEqual(session.patterns.map(p => p.id), ["start", "next"]);
  assert.equal(session.patternId, "start");
});

test("a resumed start stands in for the player clock until playback begins", () => {
  const { session, player } = setup({ resume: 42 });
  assert.equal(session.startAt, 42);
  player.time = 0; // YouTube reports 0 before the first play even with playerVars.start
  assert.equal(session.tick().pt, 42);
  player.time = 0.4;
  assert.equal(session.tick().pt, 42);
  player.time = 0.6; // a real position (the learner sought) wins
  assert.equal(session.tick().pt, 0.6);
  session.stateChange(1);
  player.time = 0.1;
  assert.equal(session.tick().pt, 0.1);
});

test("before the player is ready the session keeps its own position", () => {
  const { session, player } = setup({ resume: 12, attach: false });
  assert.equal(session.tick().pt, 12);
  assert.equal(session.controllable, false);
  assert.equal(session.play(), false);
  assert.equal(session.seek(3), false);
  session.attach(player);
  assert.equal(session.controllable, false); // attached but not ready
  session.playerReady();
  assert.equal(session.controllable, true);
});

test("cue time composes player time, video offset, nudge, latency and rate", () => {
  const s = song();
  s.videos = [s.videos[1]]; // offset 1.5 s
  const map = new Map([[PREFIX + "latency", "100"], [PREFIX + "offset:" + vid("b"), "200"]]);
  const { session, player } = setup({ song: s, map, player: { time: 10, rate: 0.5 } });
  session.stateChange(1);
  const { pt, t, cue } = session.tick();
  assert.equal(pt, 10);
  close(t, 10 + 1.5 + 0.2 - 0.1 * 0.5);
  close(t, core.cueTime(10, 1.5, 200, 100, 0.5));
  assert.deepEqual(cue, core.cueAt(session.timeline, s, t));
  session.nudgeBy(-50);
  close(session.tick().t, 10 + 1.5 + 0.15 - 0.05);
  player.time = 20;
  session.rateChange(2);
  close(session.tick().t, 20 + 1.5 + 0.15 - 0.2);
  session.rateChange(-1); // not a positive number: counts as 1
  assert.equal(session.rate, 1);
});

test("nudge is saved per video and clamped", () => {
  const { session, map } = setup();
  session.nudgeBy(50);
  session.nudgeBy(50);
  assert.equal(stored(map, "offset:" + vid("a")), 100);
  assert.equal(session.nudgeBy(1e9), 30000);
  assert.equal(session.resetNudge(), 0);
  assert.equal(stored(map, "offset:" + vid("a")), 0);
});

test("ad / wrong-video guard follows the player's duration while playing", () => {
  const { session, player } = setup({ player: { length: 30 } });
  session.tick();
  assert.equal(session.ad, false); // not playing yet: not checked
  session.stateChange(1);
  session.tick();
  assert.equal(session.ad, true);
  player.length = 121;
  session.tick();
  assert.equal(session.ad, false);
  player.length = 0; // unknown never trips it
  session.tick();
  assert.equal(session.ad, false);
});

// --- Session: errors and fallback ----------------------------------------------------------------
test("errors 100/101/150/152 switch to the next listed video and reset its timing", () => {
  for (const code of [100, 101, 150, 152]) {
    const map = new Map([[PREFIX + "offset:" + vid("b"), "-700"]]);
    const { session, player } = setup({ resume: 30, map, player: { time: 25 } });
    session.stateChange(1);
    session.tick();
    const epoch = session.epoch;
    const decision = session.error(code);
    assert.equal(decision.action, "switch", String(code));
    assert.equal(decision.video.video_id, vid("b"));
    assert.deepEqual(player.called("cue").pop(), ["cue", vid("b"), 0]);
    assert.equal(session.videoIdx, 1);
    assert.equal(session.nudgeMs, -700);
    assert.equal(session.state, -1);
    assert.equal(session.startAt, 0);
    assert.equal(session.pt, 0);
    assert.equal(session.failed, null);
    assert.notEqual(session.epoch, epoch);
  }
});

test("with no video left the error decides the failure reason", () => {
  const one = () => { const s = song(); s.videos = [s.videos[0]]; return s; };
  for (const [code, reason] of [[100, "unavailable"], [101, "no-embed"], [150, "no-embed"], [152, "no-embed"]]) {
    const { session, player } = setup({ song: one() });
    assert.deepEqual(session.error(code), { action: "fail", reason });
    assert.equal(session.failed, reason);
    assert.equal(session.controllable, false);
    assert.equal(player.called("cue").length, 0);
  }
});

test("153 fails without trying another video; other codes ask for a retry", () => {
  const a = setup();
  assert.deepEqual(a.session.error(153), { action: "fail", reason: "referrer" });
  assert.equal(a.session.videoIdx, 0);
  const b = setup({ player: { time: 17 } });
  b.session.tick();
  for (const code of [2, 5, 999]) assert.deepEqual(b.session.error(code), { action: "retry", code });
  assert.equal(b.session.failed, null);
  b.session.retry();
  assert.deepEqual(b.player.called("cue").pop(), ["cue", vid("a"), 17]);
});

test("a switch whose cue call throws fails as no-embed", () => {
  const { session, player } = setup();
  player.throws.add("cue");
  assert.deepEqual(session.error(150), { action: "fail", reason: "no-embed" });
  assert.equal(session.failed, "no-embed");
});

test("after a failure the player is no longer read or driven", () => {
  const { session, player } = setup({ player: { time: 50 } });
  session.tick();
  session.fail("Some message");
  player.time = 80;
  player.calls.length = 0;
  assert.equal(session.tick().pt, 50);
  assert.equal(session.play(), false);
  assert.equal(session.pause(), false);
  assert.equal(session.seek(10), false);
  assert.deepEqual(player.calls, []);
});

// --- Session: transport and a throwing player -----------------------------------------------------
test("seek clamps at 0 and moves the position; a throwing player keeps the last values", () => {
  const { session, player, clock } = setup({ player: { time: 30 } });
  assert.equal(session.seek(-4), true);
  assert.deepEqual(player.called("seekTo").pop(), ["seekTo", 0]);
  assert.equal(session.pt, 0);
  player.time = 33;
  clock.now += 1500; // past the pending-seek window, so the player clock counts again
  session.tick();
  player.throws.add("currentTime").add("playbackRate").add("seekTo").add("play");
  assert.equal(session.tick().pt, 33);
  session.refreshRate();
  assert.equal(session.rate, 1);
  assert.equal(session.seek(5), false);
  assert.equal(session.pt, 33);
  assert.equal(session.play(), false);
});

test("repeated −10 s presses build on the pending seek until the player's cached clock catches up", () => {
  // The embed reports the old time for ~100 ms after seekTo (measured in desktop Chromium, #31).
  const { session, player, clock } = setup({ player: { time: 61.9 } });
  player.seekTo = s => { player.calls.push(["seekTo", s]); }; // lagging: currentTime() keeps the old value
  session.tick();
  for (let i = 0; i < 3; i++) { session.seek(session.pt - 10); session.tick(); clock.now += 30; } // as app.js seekTo() + frame()
  close(session.pt, 31.9, 1e-6);
  assert.deepEqual(player.called("seekTo").map(c => Math.round(c[1] * 10) / 10), [51.9, 41.9, 31.9]);
  close(session.tick().pt, 31.9, 1e-6); // a paused poll still shows the target, so the cue panel is current
  player.time = 31.8; // the player catches up (within 0.3 s): its clock takes over again
  close(session.tick().pt, 31.8, 1e-6);
  player.time = 32.5;
  close(session.tick().pt, 32.5, 1e-6);
});

test("a pending seek the player never reaches gives way to the player clock after 1.5 s", () => {
  const { session, player, clock } = setup({ player: { time: 50 } });
  player.seekTo = () => {};
  session.seek(10);
  clock.now += 1499;
  assert.equal(session.tick().pt, 10);
  clock.now += 1;
  assert.equal(session.tick().pt, 50);
});

test("playback rate and available rates come from the player", () => {
  const { session, player } = setup({ player: { rate: 0.75, rates: [0.25, "x", 1, NaN] } });
  assert.equal(session.rate, 0.75); // read on ready
  assert.deepEqual(session.availableRates(), [0.25, 1]);
  player.rate = null; // a non-number reply counts as 1
  session.refreshRate();
  assert.equal(session.rate, 1);
  session.setRate(0.5);
  assert.deepEqual(player.called("setRate").pop(), ["setRate", 0.5]);
});

// --- Session: last-played ---------------------------------------------------------------------
test("last-played: nothing before the first play; saved on pause, end, every 5 s and on leave", () => {
  const { session, map } = setup({ player: { time: 12.7 } });
  session.tick();
  session.stateChange(2);
  session.leave();
  assert.equal(map.has(PREFIX + "last"), false, "never played: keeps the previous last-played entry");

  const b = setup({ player: { time: 10 } });
  b.clock.now = 100000;
  b.session.stateChange(1);
  b.session.tick();
  assert.deepEqual(stored(b.map, "last"), { id: "synthetic", t: 10 });
  b.player.time = 13.9; b.clock.now += 4000; b.session.tick();
  assert.equal(stored(b.map, "last").t, 10, "throttled");
  b.clock.now += 1001; b.session.tick();
  assert.equal(stored(b.map, "last").t, 13);
  b.player.time = 20.2; b.session.tick(); b.session.stateChange(2);
  assert.equal(stored(b.map, "last").t, 20);
  b.session.stateChange(0);
  assert.equal(stored(b.map, "last").t, 0, "ended: start over next time");
  b.player.time = 44.4; b.session.tick();
  b.session.leave();
  assert.equal(stored(b.map, "last").t, 44);
  assert.equal(b.player.called("destroy").length, 1);
});

test("paused ticks never save; the throttle runs only while playing", () => {
  const { session, player, clock, map } = setup({ player: { time: 30 } });
  session.stateChange(1);
  session.tick();
  session.stateChange(2);
  map.clear();
  player.time = 40; clock.now += 60000;
  session.tick();
  assert.equal(map.has(PREFIX + "last"), false);
});

// --- Session: settings and timeline ------------------------------------------------------------
test("quality and view rebuild the timeline and invalidate cached rendering", () => {
  const capo = song({ capo: 2 });
  const { session, store, map } = setup({ song: capo });
  const before = session.timeline.map(e => e.label);
  const epoch = session.epoch;
  assert.deepEqual(before, core.buildTimeline(capo, { view: "shapes", quality: "core" }).map(e => e.label));
  session.setQuality("full");
  assert.notEqual(session.epoch, epoch);
  assert.deepEqual(session.timeline.map(e => e.label), core.buildTimeline(capo, { view: "shapes", quality: "full" }).map(e => e.label));
  session.setView("sounding");
  assert.equal(session.view(), "sounding");
  assert.deepEqual(session.timeline.map(e => e.label), core.buildTimeline(capo, { view: "sounding", quality: "full" }).map(e => e.label));
  assert.equal(stored(map, "settings").view, "sounding");
  assert.equal(store.settings().quality, "full");
  // Without a capo the view setting is remembered but the song always shows shapes.
  const plain = createSession({ song: song(), store });
  assert.equal(plain.view(), "shapes");
});

test("practice pattern choice is validated and remembered per song", () => {
  const { session, map, store } = setup();
  assert.equal(session.setPattern("broken"), false);
  assert.equal(session.setPattern("nope"), false);
  assert.equal(session.patternId, "start");
  assert.equal(session.setPattern("next"), true);
  assert.deepEqual(stored(map, "settings").patterns, { synthetic: "next" });
  assert.equal(createSession({ song: song(), store }).patternId, "next");
});

test("the epoch only moves when cached cue rendering must be redrawn", () => {
  const { session } = setup();
  const e0 = session.epoch;
  session.tick(); session.stateChange(1); session.tick(); session.nudgeBy(50); session.seek(4);
  assert.equal(session.epoch, e0);
  session.rateChange(0.5);
  assert.equal(session.epoch, e0 + 1);
  session.fail("x");
  assert.equal(session.epoch, e0 + 2);
});

test("favourites and play counts persist under their own keys and tolerate garbage", () => {
  const map = new Map();
  const store = createStore(mapStorage(map));
  assert.deepEqual(store.favourites(), []);
  assert.equal(store.toggleFavourite("song-1"), true);
  assert.equal(store.toggleFavourite("song-2"), true);
  assert.equal(store.toggleFavourite("song-1"), false);
  assert.deepEqual(store.favourites(), ["song-2"]);
  assert.equal(raw(map, "favourites"), JSON.stringify(["song-2"]));
  assert.equal(store.recordPlay("song-2"), 1);
  assert.equal(store.recordPlay("song-2"), 2);
  assert.deepEqual(store.plays(), { "song-2": 2 });
  assert.equal(raw(map, "plays"), JSON.stringify({ "song-2": 2 }));
  const reread = createStore(mapStorage(map));
  assert.deepEqual(reread.favourites(), ["song-2"]);
  assert.deepEqual(reread.plays(), { "song-2": 2 });
  const junk = createStore(mapStorage(new Map([[PREFIX + "favourites", '{"a":1}'], [PREFIX + "plays", '["x"]']])));
  assert.deepEqual(junk.favourites(), []);
  assert.deepEqual(junk.plays(), {});
  const mixed = createStore(mapStorage(new Map([[PREFIX + "favourites", '["ok", 3, null, "ok"]'], [PREFIX + "plays", '{"a": 2, "b": "x", "c": -1}']])));
  assert.deepEqual(mixed.favourites(), ["ok"]);
  assert.deepEqual(mixed.plays(), { a: 2 });
});

console.log(`session.test.js: ${results.passed} passed, ${results.failed.length} failed`);
if (results.failed.length) throw new Error(`session.test.js: ${results.failed.length} failing test(s): ${results.failed.join("; ")}`);
