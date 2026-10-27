"use strict";
// Schema checks for the generated catalogue: strumalong/songs/index.json and strumalong/songs/<id>.json.
// Run with plain node:  node strumalong/test/data.test.js   (also picked up by test/run.js)
// Generate the data first:  node strumalong/tools/build-songs.js

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SONGS_DIR = path.join(__dirname, "..", "songs");
const LEVELS = [1, 2, 3, 4, 5];
const GROUPS = LEVELS.map(n => `level-${n}`);
const LEVEL_LABELS = { 1: "First chords", 2: "Open chords", 3: "More changes", 4: "First barre (F / Bm)", 5: "Barre chords" };
const CAPO_SOURCES = ["catalogue", "suggested", "none"];
const VIDEO_KINDS = ["analysed", "alternate"];
const STROKES = ["D", "U", "—"];
const SONG_BYTES_TARGET = 30 * 1024, SONG_BYTES_LIMIT = 60 * 1024;
const SHA256 = /^[a-f0-9]{64}$/, VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;

let passed = 0;
const failures = [];
function check(name, fn) {
  try { fn(); passed++; }
  catch (error) { failures.push(`${name}: ${error.message.split("\n")[0]}`); }
}
const isNum = x => typeof x === "number" && Number.isFinite(x);
const str = x => typeof x === "string" && x.trim().length > 0;
const hasKeys = (o, keys) => keys.every(k => Object.prototype.hasOwnProperty.call(o, k));
const decimals3 = x => Math.abs(x * 1000 - Math.round(x * 1000)) < 1e-6;

function main() {
  const files = fs.existsSync(SONGS_DIR) ? fs.readdirSync(SONGS_DIR).filter(f => f.endsWith(".json")).sort() : [];
  const songFiles = files.filter(f => f !== "index.json");
  if (!songFiles.length) {
    console.log("data.test: SKIP - strumalong/songs/ has no song files (run node strumalong/tools/build-songs.js)");
    return;
  }

  // ---- index.json
  let index = null;
  check("index.json parses", () => { index = JSON.parse(fs.readFileSync(path.join(SONGS_DIR, "index.json"), "utf8")); });
  if (!index) return finish();
  check("index: schema", () => assert.equal(index.schema, "strumalong-catalogue-2"));
  check("index: groups are levels in order", () => {
    assert.ok(Array.isArray(index.groups) && index.groups.length > 0);
    const ids = new Set();
    let previous = 0;
    for (const g of index.groups) {
      assert.ok(GROUPS.includes(g.id), `unknown group ${g.id}`);
      assert.ok(!ids.has(g.id), `duplicate group ${g.id}`);
      ids.add(g.id);
      assert.equal(g.id, `level-${g.level}`);
      assert.ok(g.level > previous, "levels ascend");
      previous = g.level;
      assert.equal(g.title, `Level ${g.level} · ${LEVEL_LABELS[g.level]}`);
      assert.ok(str(g.note), `group ${g.id} needs a one-line explanation`);
      assert.ok((index.songs || []).some(s => s.group === g.id), `group ${g.id} is empty`);
    }
  });
  check("index: songs listed level by level, in within-level order", () => {
    const keys = (index.songs || []).map(s => [s.level, s.order]);
    for (let i = 1; i < keys.length; i++) assert.ok(keys[i][0] > keys[i - 1][0] || (keys[i][0] === keys[i - 1][0] && keys[i][1] === keys[i - 1][1] + 1), `song ${i} out of order`);
  });
  check("index: songs array", () => assert.ok(Array.isArray(index.songs) && index.songs.length > 0));
  const indexIds = (index.songs || []).map(s => s.id);
  check("index: unique ids", () => assert.equal(new Set(indexIds).size, indexIds.length));
  check("index: lists every song file and nothing else", () => {
    const fileIds = songFiles.map(f => f.replace(/\.json$/, ""));
    const notInIndex = fileIds.filter(x => !indexIds.includes(x)), noFile = indexIds.filter(x => !fileIds.includes(x));
    assert.ok(!notInIndex.length && !noFile.length, `song files missing from index: [${notInIndex}]; index entries without a file: [${noFile}]`);
  });
  check("index: membership follows strumalong/data/catalogue.json (exclusions and level overrides)", () => {
    const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "catalogue.json"), "utf8"));
    const excluded = new Set((cfg.exclude || []).map(x => x.recording_id));
    for (const x of cfg.exclude || []) assert.ok(str(x.reason), `exclusion ${x.recording_id} needs a reason`);
    const listed = indexIds.filter(x => excluded.has(x));
    assert.deepEqual(listed, [], "excluded recordings must not ship");
    for (const o of cfg.level_overrides || []) {
      const card = (index.songs || []).find(x => x.id === o.recording_id);
      if (!card) continue;
      assert.equal(card.level, o.level, `${o.recording_id}: override level`);
    }
  });
  const groupIds = new Set((index.groups || []).map(g => g.id));
  const seenOrder = new Set();
  for (const card of index.songs || []) {
    check(`index[${card.id}]: fields`, () => {
      assert.ok(hasKeys(card, ["id", "title", "artist", "group", "order", "level", "level_label", "video_id", "duration_seconds", "bpm", "meter_label", "capo",
        "core_shapes", "changes_per_min", "playable_embed", "embed_note"]), "missing keys");
      assert.ok(LEVELS.includes(card.level), `level ${card.level}`);
      assert.equal(card.group, `level-${card.level}`);
      assert.equal(card.level_label, LEVEL_LABELS[card.level]);
      assert.ok(str(card.id) && str(card.title) && str(card.artist));
      assert.ok(groupIds.has(card.group), `group ${card.group} not declared in groups`);
      assert.ok(Number.isInteger(card.order) && card.order >= 1);
      const slot = `${card.group}/${card.order}`;
      assert.ok(!seenOrder.has(slot), `duplicate order ${slot}`);
      seenOrder.add(slot);
      assert.match(card.video_id, VIDEO_ID);
      assert.ok(isNum(card.duration_seconds) && card.duration_seconds > 0);
      assert.ok(Number.isInteger(card.bpm) && card.bpm >= 20 && card.bpm <= 300);
      assert.ok(str(card.meter_label));
      assert.ok(Number.isInteger(card.capo) && card.capo >= 0 && card.capo <= 12);
      assert.ok(Array.isArray(card.core_shapes) && card.core_shapes.length > 0, "core_shapes empty");
      assert.equal(new Set(card.core_shapes).size, card.core_shapes.length, "duplicate core shapes");
      assert.ok(card.core_shapes.every(s => str(s) && s !== "N" && s !== "X"), "N/X in core_shapes");
      assert.equal(typeof card.playable_embed, "boolean");
      assert.equal(typeof card.embed_note, "string");
      assert.equal(card.playable_embed, card.embed_note === "", "embed_note must be set exactly when playable_embed is false");
    });
  }

  // Optional soft cross-check against lib/core.js (another module; mismatches are reported, not failed).
  let core = null;
  try { core = require(path.join(__dirname, "..", "lib", "core.js")); } catch { core = null; }

  // ---- song files
  for (const file of songFiles) {
    const id = file.replace(/\.json$/, "");
    const full = path.join(SONGS_DIR, file), bytes = fs.statSync(full).size;
    let song = null;
    check(`${id}: parses`, () => { song = JSON.parse(fs.readFileSync(full, "utf8")); });
    if (!song) continue;
    const card = (index.songs || []).find(s => s.id === id);

    check(`${id}: size`, () => {
      assert.ok(bytes <= SONG_BYTES_LIMIT, `${bytes} bytes exceeds hard limit ${SONG_BYTES_LIMIT}`);
      if (bytes > SONG_BYTES_TARGET) console.warn(`data.test: note - ${file} is ${bytes} bytes (target < ${SONG_BYTES_TARGET})`);
    });
    check(`${id}: header`, () => {
      assert.equal(song.schema, "strumalong-song-2");
      assert.equal(song.id, id, "id must equal file name");
      assert.ok(str(song.title) && str(song.artist));
      assert.ok(GROUPS.includes(song.group), `group ${song.group}`);
      assert.ok(Number.isInteger(song.order) && song.order >= 1);
      assert.ok(LEVELS.includes(song.level) && song.group === `level-${song.level}`);
      assert.equal(song.riff, undefined, "riff songs are no longer part of the catalogue");
    });
    check(`${id}: recording`, () => {
      assert.ok(song.recording && song.recording.id === id);
      assert.ok(isNum(song.recording.duration_seconds) && song.recording.duration_seconds > 0);
      assert.match(song.recording.audio_sha256, SHA256);
    });
    const duration = song.recording && song.recording.duration_seconds;

    check(`${id}: videos`, () => {
      assert.ok(Array.isArray(song.videos) && song.videos.length >= 1);
      song.videos.forEach((v, i) => {
        assert.match(v.video_id, VIDEO_ID, `videos[${i}].video_id`);
        assert.ok(str(v.uploader), `videos[${i}].uploader`);
        assert.ok(VIDEO_KINDS.includes(v.kind), `videos[${i}].kind`);
        assert.ok(isNum(v.duration_seconds) && v.duration_seconds > 0, `videos[${i}].duration_seconds`);
        assert.ok(isNum(v.offset_seconds) && Math.abs(v.offset_seconds) < 60, `videos[${i}].offset_seconds`);
        assert.equal(typeof v.timing_checked, "boolean", `videos[${i}].timing_checked`);
        assert.ok(str(v.note), `videos[${i}].note`);
        assert.ok(v.embeddable === undefined || v.embeddable === false, `videos[${i}].embeddable is only ever written as false`);
      });
      assert.equal(new Set(song.videos.map(v => v.video_id)).size, song.videos.length, "duplicate video ids");
      const first = song.videos[0];
      assert.ok(first.kind === "analysed" && first.offset_seconds === 0 && first.timing_checked === true, "first video must be the analysed upload at offset 0");
      assert.equal(song.videos.filter(v => v.kind === "analysed").length, 1);
      for (const v of song.videos) if (v.kind === "alternate" && !v.timing_checked) assert.ok(/timing|nudge|unchecked/i.test(v.note), "unchecked alternate needs a visible timing note");
      assert.ok(Math.abs(first.duration_seconds - duration) < 2, "analysed upload duration should be within 2 s of the recording");
    });
    check(`${id}: chart`, () => {
      assert.ok(song.chart && str(song.chart.source));
      assert.match(song.chart.sha256, SHA256);
      assert.equal(song.chart.status, "provisional");
      assert.ok(Array.isArray(song.chart.corrections));
      const labelFixes = song.chart.corrections.filter(k => k.kind !== "timing");
      for (const k of labelFixes) {
        assert.ok(str(k.id) && str(k.from) && str(k.to) && str(k.note));
        assert.ok(isNum(k.start) && isNum(k.end) && k.start >= 0 && k.end > k.start && k.end <= duration + 1);
        assert.ok(song.chords.some(e => e.c === 1 && e.s >= k.start - 1e-9 && e.e <= k.end + 1e-9 && e.l === k.to), `correction ${k.id} has no marked chord event`);
      }
      assert.equal(song.chords.filter(e => e.c === 1).length >= labelFixes.length, true);
    });
    check(`${id}: timing fix entry`, () => {
      // docs/STRUMALONG_APP.md "Timing fix": one summary entry listing every moved change; each move flags its chord t:1.
      const entries = song.chart.corrections.filter(k => k.kind === "timing");
      const flagged = song.chords.filter(e => e.t === 1);
      assert.ok(entries.length <= 1, "at most one timing entry");
      if (!entries.length) { assert.equal(flagged.length, 0, "t:1 chords without a timing entry"); return; }
      const k = entries[0];
      assert.equal(k.id, "auto-timing");
      assert.ok(Number.isInteger(k.count) && k.count > 0 && Array.isArray(k.moves) && k.moves.length === k.count, "count matches moves");
      assert.equal(flagged.length, k.count, "one t:1 chord per move");
      assert.ok(str(k.note) && k.note.startsWith(`${k.count} chord change`) && /raw chart unchanged/.test(k.note));
      assert.ok(isNum(k.start) && isNum(k.end) && k.start >= 0 && k.end >= k.start && k.end <= duration + 1);
      for (const m of k.moves) {
        assert.ok(isNum(m.at) && isNum(m.was) && decimals3(m.at) && m.at !== m.was && m.at >= k.start && m.at <= k.end, "move times");
        assert.ok(str(m.from) && str(m.to) && m.from !== m.to && (m.shift === 1 || m.shift === -1) && /^\d+\/\d+$/.test(m.agree), "move fields");
        const i = song.chords.findIndex(e => e.s === m.at);
        assert.ok(i > 0 && song.chords[i].t === 1 && song.chords[i - 1].e === m.at, `move at ${m.at} has no t:1 chord with a contiguous predecessor`);
        assert.equal(Math.sign(m.at - m.was), m.shift, "the move goes the way its shift says");
      }
    });
    check(`${id}: capo and setup`, () => {
      assert.ok(Number.isInteger(song.capo) && song.capo >= 0 && song.capo <= 12);
      assert.ok(CAPO_SOURCES.includes(song.capo_source), `capo_source ${song.capo_source}`);
      assert.equal(song.capo_source === "none", song.capo === 0, "capo_source 'none' exactly when capo is 0");
      assert.ok(str(song.setup_note));
    });

    const r = song.rhythm || {};
    check(`${id}: rhythm`, () => {
      assert.equal(r.status, "estimated");
      assert.ok(isNum(r.bpm) && r.bpm >= 20 && r.bpm <= 300);
      assert.ok(Number.isInteger(r.beats_per_bar) && r.beats_per_bar >= 2 && r.beats_per_bar <= 6, "beats_per_bar");
      assert.equal(typeof r.beats_per_bar_assumed, "boolean");
      assert.ok(str(r.meter_label));
      assert.ok(Number.isInteger(r.bar_phase) && r.bar_phase >= 0 && r.bar_phase < r.beats_per_bar, "bar_phase in [0, beats_per_bar)");
      assert.equal(typeof r.bar_phase_confident, "boolean");
      if (r.beats_per_bar_assumed) assert.equal(r.bar_phase_confident, false, "assumed meter cannot have confident bar lines");
      assert.equal(r.bar_model, "anchored-1");
      assert.ok(isNum(r.bar_confident_pct) && r.bar_confident_pct >= 0 && r.bar_confident_pct <= 100, "bar_confident_pct");
      if (r.beats_per_bar_assumed) assert.equal(r.bar_confident_pct, 0, "assumed meter: every bar is approx");
    });
    check(`${id}: beats`, () => {
      assert.ok(Array.isArray(song.beats) && song.beats.length >= 2);
      song.beats.forEach((b, i) => {
        assert.ok(isNum(b) && b >= 0 && b <= duration + 1, `beat ${i} out of range`);
        assert.ok(decimals3(b), `beat ${i} not rounded to 3 decimals`);
        if (i) assert.ok(b > song.beats[i - 1], `beats not strictly increasing at ${i}`);
      });
    });
    check(`${id}: chords`, () => {
      assert.ok(Array.isArray(song.chords) && song.chords.length > 0);
      let previousEnd = 0;
      song.chords.forEach((e, i) => {
        assert.ok(isNum(e.s) && isNum(e.e) && str(e.l), `chord ${i} fields`);
        assert.ok(decimals3(e.s) && decimals3(e.e), `chord ${i} not rounded to 3 decimals`);
        assert.ok(e.s >= 0 && e.e <= duration + 1, `chord ${i} outside [0, duration+1]`);
        assert.ok(e.e > e.s, `chord ${i} has no length`);
        assert.ok(e.s >= previousEnd - 1e-9, `chord ${i} overlaps the previous one`);
        assert.ok(e.c === undefined || e.c === 1, `chord ${i} c flag`);
        assert.ok(e.t === undefined || e.t === 1, `chord ${i} t flag (timing fix)`);
        assert.ok(e.b === undefined || (Number.isInteger(e.b) && e.b >= 0 && e.b < r.beats_per_bar), `chord ${i} bar anchor b`);
        assert.ok(e.a === undefined || (e.a === 1 && e.b !== undefined), `chord ${i} approx flag a`);
        assert.deepEqual(Object.keys(e).filter(k => !["s", "e", "l", "c", "t", "b", "a"].includes(k)), [], `chord ${i} unexpected keys`);
        previousEnd = e.e;
      });
      assert.ok(song.chords[0].s <= 0.001 || song.chords[0].s < song.beats[0], "chart should start at the beginning of the recording");
    });
    check(`${id}: strumming`, () => {
      assert.ok(song.strumming && typeof song.strumming.note === "string" && Array.isArray(song.strumming.patterns));
      assert.ok(["authored", "level-default"].includes(song.strumming.source), `strumming.source ${song.strumming.source}`);
      assert.ok(song.strumming.patterns.length >= 1, "every song needs at least one practice pattern");
      for (const p of song.strumming.patterns) {
        assert.ok(str(p.id) && str(p.name) && str(p.description), "pattern text fields");
        assert.ok(Array.isArray(p.counts) && Array.isArray(p.strokes), "pattern arrays");
        assert.equal(p.counts.length, p.strokes.length, `pattern ${p.id}: counts/strokes length`);
        assert.ok(p.counts.length > 0 && p.counts.every(str), `pattern ${p.id}: counts`);
        assert.ok(p.strokes.every(s => STROKES.includes(s)), `pattern ${p.id}: stroke symbols`);
        assert.equal(p.counts.length % r.beats_per_bar, 0, `pattern ${p.id}: ${p.counts.length} steps do not divide into ${r.beats_per_bar} beats`);
      }
      assert.equal(new Set(song.strumming.patterns.map(p => p.id)).size, song.strumming.patterns.length, "duplicate pattern ids");
    });
    check(`${id}: difficulty`, () => {
      const d = song.difficulty;
      assert.ok(d && LEVELS.includes(d.level) && d.level === song.level, "difficulty.level");
      assert.equal(d.label, LEVEL_LABELS[d.level]);
      assert.ok(Array.isArray(d.main_shapes) && d.main_shapes.length > 0 && d.main_shapes.every(str), "main_shapes");
      assert.ok(d.main_shapes.includes(d.hardest_shape), "hardest_shape is a main shape");
      assert.ok(str(d.tier_reason), "tier_reason");
      assert.ok(isNum(d.changes_per_min) && d.changes_per_min >= 0, "changes_per_min");
      assert.ok(isNum(d.median_hold_beats) && d.median_hold_beats >= 1, "median_hold_beats");
      if (d.computed_level !== undefined) {
        assert.ok(LEVELS.includes(d.computed_level) && d.computed_level !== d.level, "an override changes the level");
        assert.ok(str(d.override_reason), "an override needs a reason");
      } else assert.equal(d.override_reason, undefined);
    });
    check(`${id}: learning`, () => {
      const l = song.learning;
      assert.ok(l && typeof l.skill_focus === "string" && typeof l.prerequisites === "string" && Array.isArray(l.sources));
      for (const s of l.sources) {
        assert.ok(str(s.title), "source title");
        assert.match(s.url, /^https:\/\//, "source url must be https");
      }
    });
    check(`${id}: provenance`, () => {
      const p = song.provenance;
      assert.ok(p && str(p.pack));
      for (const k of ["manifest_sha256", "rhythm_sha256", "practice_sha256", "learning_sha256"]) assert.match(p[k], SHA256, k);
    });
    check(`${id}: matches its index card`, () => {
      assert.ok(card, "no index card");
      assert.equal(card.title, song.title);
      assert.equal(card.artist, song.artist);
      assert.equal(card.group, song.group);
      assert.equal(card.order, song.order);
      assert.equal(card.level, song.level);
      assert.equal(card.video_id, song.videos[0].video_id);
      assert.ok(Math.abs(card.duration_seconds - duration) <= 0.006, "duration_seconds");
      assert.ok(Math.abs(card.bpm - r.bpm) <= 0.55, "bpm");
      assert.equal(card.meter_label, r.meter_label);
      assert.equal(card.capo, song.capo);
      if (!card.playable_embed) {
        assert.ok(song.videos.some(v => v.embeddable === false), "unplayable catalogue upload must be marked embeddable:false");
        assert.ok(song.videos.some(v => v.kind === "alternate" && v.embeddable !== false), "unplayable catalogue upload needs an embeddable alternate video");
      } else assert.ok(song.videos.every(v => v.embeddable !== false), "playable_embed card with a video marked embeddable:false");
    });

    if (core && typeof core.shapeLabel === "function") {
      // One Arrangement profile: the card chips are exactly the main shapes the level was computed on, and every chip
      // is a shape lib/core.js draws for this chart.
      check(`${id}: core_shapes are the level's main shapes`, () => {
        const chips = card ? card.core_shapes : [];
        assert.deepEqual(chips, song.difficulty.main_shapes, "card chips differ from difficulty.main_shapes");
        const drawn = new Set(song.chords.map(e => core.shapeLabel(e.l, { capo: song.capo, view: "shapes", quality: "core" })));
        const undrawn = chips.filter(c => !drawn.has(c));
        assert.equal(undrawn.length, 0, `chips lib/core.js shapeLabel does not produce: ${undrawn.join(" ")}`);
      });
    }
  }
  finish(songFiles.length);
}

function finish(songCount) {
  if (failures.length) {
    console.error(`data.test: ${failures.length} FAILED, ${passed} passed`);
    for (const f of failures) console.error("  FAIL " + f);
    throw new Error(`${failures.length} data check(s) failed`);
  }
  console.log(`data.test: ${passed} checks passed${songCount ? ` (${songCount} songs + index)` : ""}`);
}

main();
