// Drums (#98): five beginner beats on a one-bar grid, played by a small synthesized kit. No samples or network.
const drumState={selected:'rock',done:false};
// Each beat is a grid of `steps` per bar; rows list the steps that sound. The top row is hi-hat or ride.
const drumPatterns=[
 {id:'rock',name:'Straight rock',note:'The classic beat',steps:8,cymbal:'hat',top:[0,1,2,3,4,5,6,7],snare:[2,6],kick:[0,4],tip:'Hi-hat on every count, snare on 2 and 4, kick on 1 and 3.'},
 {id:'half',name:'Half-time',note:'Big and slow',steps:8,cymbal:'hat',top:[0,1,2,3,4,5,6,7],snare:[4],kick:[0,7],tip:'Snare only on 3. The song feels half as fast.'},
 {id:'four',name:'Four on the floor',note:'Kick every beat',steps:8,cymbal:'hat',top:[1,3,5,7],snare:[2,6],kick:[0,2,4,6],tip:'Kick on every beat, hi-hat between. Made for dancing.'},
 {id:'shuffle',name:'Shuffle',note:'Swung and bouncy',steps:12,cymbal:'hat',top:[0,2,3,5,6,8,9,11],snare:[3,9],kick:[0,6],tip:'Long-short, long-short. Good for blues.'},
 {id:'ride',name:'Quiet ride',note:'Soft and gentle',steps:4,cymbal:'ride',top:[0,1,2,3],snare:[1,3],kick:[0],tip:'Ride cymbal on each beat, soft snare on 2 and 4.'}
];
// General MIDI percussion numbers name each drum in the note list.
const drumKit={kick:{midi:36,name:'Kick',length:.4,level:.9},snare:{midi:38,name:'Snare',length:.3,level:.55},hat:{midi:42,name:'Hi-hat',length:.08,level:.22},ride:{midi:51,name:'Ride',length:1,level:.2}};
function drumHits(pattern){const p=drumPatterns.find(x=>x.id===pattern)||drumPatterns[0],quiet=p.id==='ride'?.6:1,hits=[];
 for(const [row,drum] of [['kick','kick'],['snare','snare'],['top',p.cymbal]])for(const step of p[row])hits.push({drum,beat:step*4/p.steps,level:drumKit[drum].level*quiet*(drum==='hat'&&step*4%p.steps!==0?.7:1)});
 return hits.sort((a,b)=>a.beat-b.beat)}
function drumNotes(pattern,bars,beat){const notes=[];for(let bar=0;bar<bars;bar++)for(const h of drumHits(pattern))notes.push({instrument:'drums',midi:drumKit[h.drum].midi,time:(bar*4+h.beat)*beat,duration:drumKit[h.drum].length,level:h.level});return notes}
// Deterministic kit: a falling sine for the kick, noise plus a body tone for the snare, bright noise for cymbals.
function drumBuffer(ctx,midi,seconds){const sr=ctx.sampleRate,len=Math.max(1,Math.ceil(seconds*sr)),buf=ctx.createBuffer(1,len,sr),out=buf.getChannelData(0);let seed=99991+midi,last=0,phase=0;const noise=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/2147483648-1};
 for(let i=0;i<len;i++){const t=i/sr,n=noise(),bright=n-last;last=n;let v;
  if(midi===36){phase+=2*Math.PI*(48+110*Math.exp(-t/.035))/sr;v=Math.sin(phase)*Math.exp(-t/.16)+bright*.15*Math.exp(-t/.004)}
  else if(midi===38){phase+=2*Math.PI*185/sr;v=Math.sin(phase)*.5*Math.exp(-t/.05)+n*.7*Math.exp(-t/.09)}
  else if(midi===51){v=bright*.5*Math.exp(-t/.45)+(Math.sin(2*Math.PI*3150*t)+Math.sin(2*Math.PI*4730*t))*.12*Math.exp(-t/.6)}
  else v=bright*.6*Math.exp(-t/.025);
  out[i]=v*Math.min(1,i/(sr*.001))}
 return buf}
function drumGrid(p,active){const rows=[['top',drumKit[p.cymbal].name],['snare','Snare'],['kick','Kick']],per=p.steps/4;
 const description=rows.map(([row,name])=>`${name}: ${p[row].map(s=>s%per?'and':'beat '+(s/per+1)).join(', ')}`).join('; ');
 return `<section class="card"><div class="row between"><b>One bar · repeats</b><small>count 1 2 3 4</small></div><div class="drum-grid" role="img" aria-label="${esc(description)}" style="--steps:${p.steps}"><span></span>${Array.from({length:p.steps},(_,s)=>`<span class="drum-count ${Math.floor(s/per)===active?'on':''}">${s%per?'':s/per+1}</span>`).join('')}${rows.map(([row,name])=>`<span class="drum-name">${name}</span>${Array.from({length:p.steps},(_,s)=>`<span class="drum-cell ${p[row].includes(s)?'hit':''} ${Math.floor(s/per)===active?'on':''}"></span>`).join('')}`).join('')}</div></section>`}
function drumsView(){const p=drumPatterns.find(x=>x.id===drumState.selected),playing=bassState.playing||'',solo=playing==='drum:'+p.id+':solo',mix=playing==='drum:'+p.id+':mix',active=playing.startsWith('drum:'+p.id)?bassState.playingBeat:-1;
 return `<section class="screen"><section class="stack"><span class="label">Pick a beat</span><div class="bass-grid">${drumPatterns.map(x=>`<button type="button" class="bass-pick" data-action="drum-select:${x.id}" aria-pressed="${drumState.selected===x.id}"><b>${x.name}</b><small>${x.note}</small></button>`).join('')}</div></section>${drumGrid(p,active)}<p class="tip"><b>${p.name}:</b> ${p.tip}</p>${statusLine()}<div class="bass-actions"><button type="button" class="wide" data-action="drum-play:${p.id},solo">${solo?'■ Stop':'▶ Hear drums'}</button><button type="button" class="wide strong" data-action="drum-play:${p.id},mix">${mix?'■ Stop':'▶ Hear with guitar'}</button></div>${cta('Bring in the bass','member:bass')}</section>`}
function playDrums(id,mix){const s=currentSection(),beat=60/rhythm.bpm,progress=[],notes=drumNotes(id,s.bars,beat);
 if(mix)arrangementNotes(s.chords,rhythm.bpm,s.pattern||'quarters',s.sound||'clean').notes.forEach(n=>notes.push({...n,level:n.level*.73}));
 s.chords.forEach((_,bar)=>{for(let tick=0;tick<4;tick++)progress.push({bar,beat:tick,time:(bar*4+tick)*beat})});
 return previewPlayback.play({notes,progress,tag:{bass:'drum:'+id+':'+(mix?'mix':'solo')},level:.3,release:.02,duration:s.bars*4*beat+1})}
function drumAction(action,value){if(!action.startsWith('drum-'))return false;feelUI.message='';
 if(action==='drum-select'){if(!drumPatterns.some(p=>p.id===value))return true;stopGuidePreview();drumState.selected=value;drumState.done=true;render();return true}
 if(action==='drum-play'){const [id,mode]=value.split(',');if(!drumPatterns.some(p=>p.id===id))return true;drumState.selected=id;drumState.done=true;if(bassState.playing==='drum:'+id+':'+mode){stopGuidePreview();render()}else playDrums(id,mode==='mix');return true}
 return false}
