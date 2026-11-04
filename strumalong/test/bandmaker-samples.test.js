'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
module.exports=(async()=>{
 const status={textContent:''},root={dataset:{},querySelectorAll:()=>[]},started=[];
 let fetches=0,decodes=0,fail=false,release;const handlers={};
 const names=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
 const bank=Array.from({length:88},(_,i)=>{const n=i+21;return '"'+names[n%12]+(Math.floor(n/12)-1)+'": "data:audio/mp3;base64,AQID",'}).join('\n');
 const ctx={handlers,setTimeout,clearTimeout,AbortController,atob,console,document:{querySelector:s=>s==='#sound-status'?status:root,querySelectorAll:()=>[],addEventListener(type,fn){(handlers[type]??=[]).push(fn)}},window:{addEventListener(type,fn){(handlers[type]??=[]).push(fn)}},fetch:async()=>{fetches++;if(release)await new Promise(r=>release=r);if(fail)throw Error('offline');return {ok:true,text:async()=>bank+'\nthrow new Error("must never execute");'}}};
 vm.createContext(ctx);for(const file of ['lib/preview-playback.js','bandmaker-samples.js','bandmaker-bass.js','bandmaker.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',file),'utf8'),ctx);
 ctx.fakeAudio={decodeAudioData:async()=>{decodes++;return {sample:true}},resume:async()=>{},currentTime:0,createGain:()=>({gain:{value:1,setValueAtTime(){},linearRampToValueAtTime(){}},connect(){},disconnect(){}}),createBufferSource:()=>({connect(){},start(){started.push(true)},stop(){}})};
 await vm.runInContext("prepareSamples(fakeAudio,[{instrument:'guitar',notes:[60,60,64]}])",ctx);
 assert.equal(fetches,1);assert.equal(decodes,2);assert.match(status.textContent,/FluidR3/);
 await vm.runInContext("prepareSamples(fakeAudio,[{instrument:'guitar',notes:[60]}])",ctx);assert.equal(fetches,1);assert.equal(decodes,2);
 fail=true;await vm.runInContext("prepareSamples(fakeAudio,[{instrument:'bass',notes:[28]}])",ctx);assert.match(status.textContent,/unavailable/);
 fail=false;await vm.runInContext("prepareSamples(fakeAudio,[{instrument:'bass',notes:[28]}])",ctx);assert.match(status.textContent,/FluidR3/);assert.equal(decodes,3);
 // A pending sample download must not start playback after Stop or a tab change.
 vm.runInContext('sampleAudio.banks.clear();sampleAudio.buffers.clear();window.AudioContext=function(){return fakeAudio}',ctx);release=true;
 const pending=vm.runInContext("playArrangement(['C'],90,'quarters','clean')",ctx);
 await new Promise(r=>setImmediate(r));assert.equal(typeof release,'function');vm.runInContext('stopGuidePreview()',ctx);release();await pending;assert.equal(started.length,0);
 // Exercise the actual Bass caller and navigation, not only the shared module.
 for(const cancelAction of ["stopGuidePreview()", "bassAction('member','rhythm')", "handlers.pagehide[0]()", "document.hidden=true;handlers.visibilitychange[0]();document.hidden=false", "handlers.change[0]({target:{id:'sound-engine',value:'synth'}})", "playArrangement(['C'],90,'quarters','clean')"]){
  vm.runInContext("sampleAudio.engine='samples';sampleAudio.banks.clear();sampleAudio.buffers.clear();applyRecipe('H1')",ctx);
  release=true;const before=started.length;
  const pendingBass=vm.runInContext("playBass('roots',false)",ctx);
  await new Promise(r=>setImmediate(r));const unblock=release;release=false;
  await vm.runInContext(cancelAction,ctx);const afterReplacement=started.length;
  unblock();await pendingBass;
  assert.equal(started.length,afterReplacement,'Stale Bass must never schedule notes');
  if(!cancelAction.startsWith('playArrangement'))assert.equal(started.length,before);
  vm.runInContext('stopGuidePreview()',ctx);
 }
 console.log('Sample loading, caching, data-only parsing, fallback/retry and cancelled playback passed');
})();
