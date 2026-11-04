'use strict';
const assert=require('node:assert/strict');
const create=require('../lib/preview-playback');
module.exports=(async()=>{
 let release,failBuffer=false;const events=[],started=[],stopped=[],disconnected=[],timers=[];
 const audio={currentTime:2,destination:{},resume:async()=>{},createGain(){return {gain:{setValueAtTime(){},linearRampToValueAtTime(){}},connect(){return this},disconnect(){disconnected.push(true)}}},createBufferSource(){return {connect(){return this},start(t){started.push(t)},stop(t){stopped.push(t)}}}};
 const player=create({createAudio:()=>audio,prepare:async()=>{if(release)await new Promise(r=>release=r)},buffer:()=>{if(failBuffer)throw Error('decode');return {}},changed:s=>events.push(s),failed:e=>events.push(e.message),later:(fn,ms)=>{const t={fn,ms,cancelled:false};timers.push(t);return t},cancel:t=>t.cancelled=true});
 const plan=tag=>({tag,notes:[{instrument:'bass',midi:28,time:0,duration:1,level:.75}],progress:[{bar:0,beat:0,time:0}],duration:1,level:.3,release:.04});
 release=true;const pending=player.play(plan('old'));await new Promise(setImmediate);player.stop();release();await pending;assert.equal(started.length,0);
 release=true;const old=player.play(plan('old'));await new Promise(setImmediate);const unblock=release;release=false;await player.play(plan('new'));unblock();await old;assert.equal(started.length,1);assert.equal(events.at(-1).tag,'new');
 timers.at(-2).fn();assert.equal(events.at(-1).beat,0);
 player.stop();assert(timers.every(t=>t.cancelled));const count=events.length;timers.forEach(t=>t.fn());assert.equal(events.length,count);assert(disconnected.length>=2);
 failBuffer=true;await player.play(plan('broken'));assert.equal(events.at(-1),'decode');assert(stopped.includes(undefined));
 failBuffer=false;await player.play(plan('recovered'));timers.at(-1).fn();assert.equal(events.at(-1).playing,false);
 console.log('Preview lifetime: pending stop, replacement, progress, cleanup, failure and recovery passed');
})();
