"use strict";
const assert = require("node:assert/strict");
const {seekTime,validateEdits, overlayEdits, startSession, sessionElapsed, sessionTick, endSession, reviewEffort, validateDraft} = require("./app.js");
let checks = 0;
function test(name, callback) { callback(); checks++; console.log("ok " + name); }
const native = [{start_seconds:0,end_seconds:4,label:"C"}, {start_seconds:4,end_seconds:5,label:"Am"}, {start_seconds:6,end_seconds:10,label:"G"}];
test("review seek positions clamp to the recording and reject invalid clocks",()=>{
  assert.equal(seekTime(-1,10),0); assert.equal(seekTime(11,10),10); assert.equal(seekTime(4.1,10),4.1);
  assert.throws(()=>seekTime(NaN,10)); assert.throws(()=>seekTime(1,0));
});
test("a boundary correction changes only the explicit replacement interval", () => {
  const before = structuredClone(native);
  const result = overlayEdits(native,[{start_seconds:4,end_seconds:4.2,label:"C"}],10);
  assert.deepEqual(result.map(e=>[e.start_seconds,e.end_seconds,e.label,e.origin]),[[0,4,"C","native"],[4,4.2,"C","review-edit"],[4.2,5,"Am","native"],[6,10,"G","native"]]);
  assert.deepEqual(native,before);
});
test("correction overlays preserve gaps and never invent a complete chart", () => {
  const result = overlayEdits(native,[],10);
  assert.equal(result.some(e=>e.start_seconds <=5.5 &&5.5<e.end_seconds),false);
  const explicit = overlayEdits(native,[{start_seconds:5,end_seconds:6,label:"X"}],10);
  assert.equal(explicit.find(e=>e.start_seconds===5).label,"X");
});
test("rich labels and deliberate silence stay distinct from unknown coverage", () => {
  const result=overlayEdits(native,[{start_seconds:1,end_seconds:2,label:"A7sus4"},{start_seconds:2,end_seconds:3,label:"N"}],10);
  assert.deepEqual(result.filter(e=>e.origin==="review-edit").map(e=>e.label),["A7sus4","N"]);
  assert.ok(result.every(e=>!Object.hasOwn(e,"confidence")));
});
test("overlap nonfinite bounds code labels and out-of-recording edits reject",()=>{
  for(const edits of [[{start_seconds:0,end_seconds:11,label:"C"}],[{start_seconds:0,end_seconds:2,label:"C"},{start_seconds:1,end_seconds:3,label:"G"}],[{start_seconds:NaN,end_seconds:2,label:"C"}],[{start_seconds:0,end_seconds:2,label:"<script>"}]]) assert.throws(()=>validateEdits(edits,10));
});
test("active review time counts the chosen actor and does not start from page load",()=>{
  assert.throws(()=>startSession("",1000,"2026-10-14T10:00:00Z","one","chords"));
  const active=startSession("human",1000,"2026-10-14T10:00:00Z","one","chords");
  assert.equal(sessionElapsed(active,3500),2.5);
  const saved=endSession(active,3500,"2026-10-14T10:00:03Z");
  assert.equal(saved.active_seconds,2.5); assert.equal(saved.actor,"human"); assert.equal(sessionElapsed(null,900000),0);
});
test("pauses and later resumes create separate sessions without counting the gap",()=>{
  const first=endSession(startSession("human",1000,"2026-10-14T10:00:00Z","one","chords"),4000,"2026-10-14T10:00:03Z");
  const second=endSession(startSession("human",100000,"2026-10-14T10:02:00Z","two","chords"),103000,"2026-10-14T10:02:03Z");
  assert.equal(reviewEffort([first,second]).human.seconds,6);
});
test("QA and agent sessions never contribute to measured human cost",()=>{
  const sessions=[{actor:"agent",active_seconds:10},{actor:"qa",active_seconds:20}];
  assert.deepEqual(reviewEffort(sessions),{human:{measured:false,seconds:0},agent:{measured:true,seconds:10},qa:{measured:true,seconds:20}});
});
test("backward review clocks reject and long sessions are capped",()=>{
  const active=startSession("qa",1000,"2026-10-14T10:00:00Z","one","chords");
  assert.throws(()=>sessionElapsed(active,999)); assert.equal(sessionElapsed(active,3601000),1800);
});
test("automatic song endings preserve all preceding listening time",()=>{
  let active=startSession("qa",0,"2026-10-14T10:00:00Z","one","chords");
  for(let now=1000;now<=240000;now+=1000) {
    const tick=sessionTick(active,now,true); active=tick.session; assert.equal(tick.cutoff,null);
  }
  const ended=sessionTick(active,300900,false);
  assert.equal(ended.cutoff,300000); assert.equal(ended.session.began,0);
  assert.equal(endSession(ended.session,ended.cutoff,"2026-10-14T10:05:01Z").active_seconds,300);
});
test("idle checks omit delayed timer wakeups beyond the idle grace",()=>{
  const active=startSession("human",1000,"2026-10-14T10:00:00Z","one","chords");
  const tick=sessionTick(active,301000,false);
  assert.equal(tick.cutoff,61000); assert.equal(sessionElapsed(tick.session,tick.cutoff),60);
  assert.equal(sessionTick(null,301000,false).cutoff,null);
});
test("continuous playback still stops at the 30-minute review limit",()=>{
  const active=startSession("agent",1000,"2026-10-14T10:00:00Z","one","chords");
  const tick=sessionTick(active,1802500,true);
  assert.equal(tick.cutoff,1801000); assert.equal(sessionElapsed(tick.session,tick.cutoff),1800);
});
const recording={id:"song",audio_sha256:"a".repeat(64),duration_seconds:10,sample_rate_hz:100};
const manifest={pack_id:"pack"},item={recording,artifacts:{primary_sha256:"b".repeat(64),crema_sha256:"c".repeat(64)}};
const review={points:[{id:"sample-1"}]};
const draft={schema_version:"catalogue-curation-draft-1.0",status:"model-exposed-curation-draft",gold:false,pack_id:"pack",recording,base_artifacts:item.artifacts,revision:0,chord_edits:[],checked_points:[],sessions:[]};
test("saved corrections remain bound to exact audio model bytes and pack",()=>{
  assert.equal(validateDraft(draft,manifest,item,review),draft);
  assert.equal(validateDraft({...draft,base_artifacts:{crema_sha256:item.artifacts.crema_sha256,primary_sha256:item.artifacts.primary_sha256}},manifest,item,review).gold,false);
  for(const change of [{recording:{...recording,audio_sha256:"f".repeat(64)}},{base_artifacts:{...item.artifacts,primary_sha256:"f".repeat(64)}},{pack_id:"other"},{gold:true}]) assert.throws(()=>validateDraft({...draft,...change},manifest,item,review));
});
test("reviewed windows do not grant reference status or approve an arrangement",()=>{
  const value={...draft,checked_points:["sample-1"]}; validateDraft(value,manifest,item,review); assert.equal(value.gold,false); assert.equal(value.status,"model-exposed-curation-draft");
  assert.throws(()=>validateDraft({...draft,checked_points:["invented"]},manifest,item,review));
});
console.log(`${checks} curation checks passed`);
