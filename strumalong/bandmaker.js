"use strict";
// Personal iPhone pilot, #73 and #86. Guided steps: feel, key, chords, song. Sampled previews; no input recording or persisted projects.
const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function button(label,action,active=false){return `<button type="button" data-action="${action}" class="${active?'active':''}">${label}</button>`}
const rhythm={selected:0,bpm:92,clips:[],sections:[{name:'Verse',bars:4,key:'G',mode:'major',barDegrees:[0,3,4,0]}]};
const currentSection=()=>rhythm.sections[rhythm.selected];
const guide={selectedBar:0,playing:false,playingBar:-1};
const degrees=['I','ii','iii','IV','V','vi','♭VII','♭VI','♭III','II','III','iv'];
// One audio context for every player: the band and one-shot chord pads sound together.
let sharedAudio;const audioContext=()=>sharedAudio??=new (window.AudioContext||window.webkitAudioContext)();
const previewPlayback=createPreviewPlayback({
 createAudio:audioContext,
 prepare:prepareSamples, buffer:instrumentBuffer,
 changed:state=>{guide.playing=state.playing;guide.playingBar=state.bar??-1;feelUI.playingRecipe=state.playing?state.tag?.recipeId??null:null;bassState.playing=state.playing?state.tag?.bass??null:null;bassState.playingBeat=state.beat??-1;render()},
 failed:()=>soundStatus('Audio could not start. Tap Hear again.')
});
function stopClick(){}
const padPlayback=createPreviewPlayback({createAudio:audioContext,prepare:prepareSamples,buffer:instrumentBuffer});
function stopGuidePreview(){previewPlayback.stop();padPlayback.stop()}
function render(){const root=document.querySelector('#recommender'),open=root.dataset?.screen===bassState.tab+feelUI.screen?[...root.querySelectorAll('details')].map((d,i)=>d.open?i:-1).filter(i=>i>=0):[];if(!bandReady())bassState.tab='rhythm';root.innerHTML=bassState.tab==='rhythm'&&feelUI.screen==='path'?pathView():songHeader()+(bassState.tab==='tracks'?viewToggle()+tracksView():bandSelector()+viewToggle()+(bassState.tab==='bass'?bassView():bassState.tab==='drums'?drumsView():stepsBar()+screenView()));const moved=root.dataset&&root.dataset.screen!==bassState.tab+feelUI.screen;if(root.dataset)root.dataset.screen=bassState.tab+feelUI.screen;if(moved)window.scrollTo?.(0,0);const details=root.querySelectorAll('details');open.forEach(i=>{if(details[i])details[i].open=true})}
const chordRows={"C♯": ["C♯", "D♯m", "E♯m", "F♯", "G♯", "A♯m", "B", "A", "E", "D♯", "E♯", "F♯m"], "F♯": ["F♯", "G♯m", "A♯m", "B", "C♯", "D♯m", "E", "D", "A", "G♯", "A♯", "Bm"], "B": ["B", "C♯m", "D♯m", "E", "F♯", "G♯m", "A", "G", "D", "C♯", "D♯", "Em"], "E": ["E", "F♯m", "G♯m", "A", "B", "C♯m", "D", "C", "G", "F♯", "G♯", "Am"], "A": ["A", "Bm", "C♯m", "D", "E", "F♯m", "G", "F", "C", "B", "C♯", "Dm"], "D": ["D", "Em", "F♯m", "G", "A", "Bm", "C", "B♭", "F", "E", "F♯", "Gm"], "G": ["G", "Am", "Bm", "C", "D", "Em", "F", "E♭", "B♭", "A", "B", "Cm"], "C": ["C", "Dm", "Em", "F", "G", "Am", "B♭", "A♭", "E♭", "D", "E", "Fm"], "F": ["F", "Gm", "Am", "B♭", "C", "Dm", "E♭", "D♭", "A♭", "G", "A", "B♭m"], "B♭": ["B♭", "Cm", "Dm", "E♭", "F", "Gm", "A♭", "G♭", "D♭", "C", "D", "E♭m"], "E♭": ["E♭", "Fm", "Gm", "A♭", "B♭", "Cm", "D♭", "C♭", "G♭", "F", "G", "A♭m"], "A♭": ["A♭", "B♭m", "Cm", "D♭", "E♭", "Fm", "G♭", "F♭", "C♭", "B♭", "C", "D♭m"], "D♭": ["D♭", "E♭m", "Fm", "G♭", "A♭", "B♭m", "C♭", "B♭♭", "F♭", "E♭", "F", "G♭m"], "G♭": ["G♭", "A♭m", "B♭m", "C♭", "D♭", "E♭m", "F♭", "E♭♭", "B♭♭", "A♭", "B♭", "C♭m"], "C♭": ["C♭", "D♭m", "E♭m", "F♭", "G♭", "A♭m", "B♭♭", "A♭♭", "E♭♭", "D♭", "E♭", "F♭m"]};
const feelRecipes=[
{id:'H1',feel:'happy',name:'Open and buoyant',key:'G',mode:'major',chords:['G','C','D','G'],bpm:108,pattern:'quarters',tone:'clean',why:'Three familiar open shapes give you movement and a return to G.',easy:'One downstroke per beat. Let the chords ring.'},
{id:'H2',feel:'happy',name:'Lift with contrast',key:'G',mode:'major',chords:['G','D','Em','C'],bpm:108,pattern:'eighths',tone:'clean',why:'Em adds a minor-chord contrast inside this major-key starting point.',easy:'Try quarter-note downstrokes first; add lighter upstrokes later.'},
{id:'S1',feel:'sad',name:'Quiet reflection',key:'E',mode:'minor',chords:['Em','C','Am','Em'],bpm:72,pattern:'space',tone:'soft',why:'Em, C and Am use open shapes. Space and a softer attack help explore a quieter sound.',easy:'One soft downstroke per bar. Let it ring.'},
{id:'S2',feel:'sad',name:'Pull back home',key:'E',mode:'minor',chords:['Em','Am','B7','Em'],bpm:72,pattern:'picked',tone:'soft',why:'B7 adds D♯ and a stronger pull back to Em. Try the other example if B7 feels too difficult.',easy:'Alternate the low note on beat 1 and upper strings on beat 3.'},
{id:'R1',feel:'heavy',name:'Stomping riff',key:'E',mode:'power',chords:['E5','G5','A5','E5'],bpm:96,pattern:'stomp',tone:'drive',why:'Start around low E with two-note shapes. Rhythm, damping and drive shape this version; power chords have no major/minor third.',easy:'Quarter-note downstrokes. Mute beats 1–3; let beat 4 ring.'},
{id:'R2',feel:'heavy',name:'Driving climb home',key:'E',mode:'power',chords:['E5','C5','D5','E5'],bpm:120,pattern:'drive',tone:'drive',why:'C5 and D5 climb back to E5, with more frequent attacks. These are power chords, not an E-minor triad sequence.',easy:'Start at 84 BPM with quarter notes. Add the faster eighths when comfortable.'}
];
// Original four-bar practice ideas using the saved table's degree vocabulary.
for(const [id,mode,name,pattern,why] of [
 ['H3','major','Classic circle',[0,5,3,4],'I–vi–IV–V: start at home and build toward a return.'],
 ['H4','major','Stepwise lift',[0,1,3,4],'I–ii–IV–V: add the minor ii before IV and V.'],
 ['H5','major','Rock colour',[0,8,3,0],'I–♭III–IV–I: ♭III is an extra colour from the table.'],
 ['H6','major','Climb back home',[0,7,6,0],'I–♭VI–♭VII–I: two borrowed chords lead back to home.'],
 ['H7','major','Minor-four turn',[0,3,11,0],'I–IV–iv–I: change IV to minor before returning home.'],
 ['H8','major','Pull toward the relative minor',[0,10,5,3],'I–III–vi–IV: major III can pull toward vi in this context.'],
 ['H9','major','Rock turnaround',[0,6,3,0],'I–♭VII–IV–I: a flat-degree rock move from the chord table.'],
 ['H10','major','Hard-rock climb',[0,3,4,6],'I–IV–V–♭VII: the hard-rock formula from the chord table.'],
 ['S3','minor','Descending colour',[0,5,1,4],'i–♭VI–♭III–♭VII: a loop using natural-minor chords.'],
 ['S4','minor','Bright fourth in minor',[0,7,5,0],'i–IV–♭VI–i: major IV adds a raised sixth, a Dorian colour.'],
 ['R3','power','Two-shape practice',[0,2,0,2],'Alternate home and fourth-root power chords.'],
 ['R4','power','Wide climb',[0,1,3,4],'Root positions 1–♭3–♭6–♭7: try steady downstrokes.'],
 ['S5','minor','Walk down and back',[0,4,5,4],'i–♭VII–♭VI–♭VII: step down from home and back up.'],
 ['S6','minor','Falling to tension',[0,4,5,6],'i–♭VII–♭VI–V7: step down, then V7 pulls back home.'],
 ['S7','minor','Slow rise',[0,2,4,1],'i–iv–♭VII–♭III: climbs toward the brighter ♭III.'],
 ['R5','power','Three-chord rock',[0,2,5,2],'1–4–5–4: the classic three root positions.'],
 ['R6','power','Dark drop',[0,4,3,4],'1–♭7–♭6–♭7: step down from home and back up.'],
 ['R7','power','Punk push',[0,5,3,2],'1–5–♭6–4: four different roots, steady downstrokes.']
]){const key=mode==='major'?'G':'E',base=feelRecipes.find(r=>r.mode===mode);feelRecipes.push({...base,id,name,key,chords:pattern.map(i=>mode==='major'?chordRows[key][i]:mode==='minor'?['Em','G','Am','Bm','D','C','B7','A'][i]:['E5','G5','A5','C5','D5','B5'][i]),why,pattern:'quarters',easy:'Start with one downstroke per beat; slow down if needed.'})}
// A feel is a starting point: it suggests a chord family, key and first sequence, all of which can change.
const feels={happy:{name:'Happy and bright',note:'Major key, mid tempo',recipe:'H1'},sad:{name:'Reflective',note:'Minor colour, slower',recipe:'S1'},heavy:{name:'Heavy',note:'Power chords, driving',recipe:'R1'}};
const shapeMap={G:'320003',C:'x32010',D:'xx0232',Em:'022000',Am:'x02210',A:'x02220',E:'022100',Dm:'xx0231',B7:'x21202',E5:'02xxxx',G5:'35xxxx',A5:'x02xxx',C5:'x35xxx',D5:'x57xxx'};
const feelUI={screen:'path',pathSel:null,seq:null,allSeq:false,playingRecipe:null,undo:[],message:'',lastPreview:null};
const modes={minor:{labels:['i','♭III','iv','v','♭VII','♭VI','V7','IV'],spec:[[0,0,'m'],[3,2,''],[5,3,'m'],[7,4,'m'],[10,6,''],[8,5,''],[7,4,'7'],[5,3,'']]},power:{labels:['1','♭3','4','♭6','♭7','5'],spec:[[0,0,'5'],[3,2,'5'],[5,3,'5'],[8,5,'5'],[10,6,'5'],[7,4,'5']]}};
function rootPc(name){const m=name.match(/^([A-G])([♯♭#b]*)/);let p={C:0,D:2,E:4,F:5,G:7,A:9,B:11}[m[1]];for(const a of m[2])p+=a==='♯'||a==='#'?1:-1;return (p+24)%12}
function spellFrom(key,semitones,steps){const letters='CDEFGAB',letter=letters[(letters.indexOf(key[0])+steps)%7],natural={C:0,D:2,E:4,F:5,G:7,A:9,B:11}[letter],want=(rootPc(key)+semitones)%12;let delta=(want-natural+18)%12-6;return letter+(delta>=0?'♯'.repeat(delta):'♭'.repeat(-delta))}
function palette(s){return (s.mode||'major')==='major'?[...chordRows[s.key],spellFrom(s.key,11,6)+'dim']:s.mode==='minor'?[...modes.minor.spec.map(([n,d,q])=>spellFrom(s.key,n,d)+q),spellFrom(s.key,2,1)+'dim']:modes.power.spec.map(([n,d,q])=>spellFrom(s.key,n,d)+q)}
function labelsFor(s){return (s.mode||'major')==='major'?[...degrees,'vii°']:s.mode==='minor'?[...modes.minor.labels,'ii°']:modes.power.labels}
function keyName(s){return s.mode==='power'?s.key+'-centred power chords':s.key+' '+(s.mode||'major')}
function syncGuide(s){s.chords=s.barDegrees.map(i=>palette(s)[i])}
for(const s of rhythm.sections){s.mode='major';s.recipe=null;s.pattern='quarters';s.sound='clean';s.focusPalette=null;syncGuide(s)}
function rememberGuide(){feelUI.undo.push({section:rhythm.selected,data:JSON.parse(JSON.stringify(currentSection())),bpm:rhythm.bpm});if(feelUI.undo.length>20)feelUI.undo.shift()}
function applyRecipe(id){const r=recipeForKey(id);rememberGuide();stopClick();const s=currentSection();s.comparison=null;s.key=r.key;s.mode=r.mode;s.recipe=r.id;s.pattern=r.pattern;s.sound=r.tone;const end=Math.max(0,...rhythm.clips.filter(c=>c.section===rhythm.selected).map(c=>c.start+c.out-c.in));s.bars=end>4?Math.max(s.bars,Math.ceil(end)):4;const row=palette(s),p=r.chords.map(c=>row.indexOf(c));s.barDegrees=Array.from({length:s.bars},(_,i)=>p[i%4]);s.focusPalette=[...new Set(p)];syncGuide(s);rhythm.bpm=r.bpm;guide.selectedBar=0;s.started=true;feelUI.seq=r.id;feelUI.screen='build';feelUI.message=''}
const keyGroups={major:{title:'Major keys',feel:'Often bright, open or uplifting.',keys:['G','C','D','A','E','F','B♭','E♭','A♭','D♭','F♯','B'],tip:'G, C and D are familiar starting points for open-chord guitar.'},minor:{title:'Minor keys',feel:'Often reflective, melancholy or tense.',keys:['E','A','D','B','G','C','F','F♯','C♯','G♯','B♭','E♭'],tip:'E minor and A minor are useful starting points with familiar open shapes.'},power:{title:'Power-chord approach',feel:'Useful for heavy, driving sounds.',keys:['E','A','D','G','C','B','F','F♯','B♭','E♭','A♭','D♭'],tip:'A separate approach, rather than a key type. Two-note power chords omit the major/minor third; rhythm and tone shape the feeling.'}};
function inKeyIndices(s){return s.mode==='major'?[0,1,2,3,4,5,12]:s.mode==='minor'?[0,8,1,2,3,5,4]:[0,1,2,3,4,5]}
function recipeForKey(id){const r=feelRecipes.find(r=>r.id===id),s=currentSection(),base=palette({key:r.key,mode:r.mode}),row=palette(s);return {...r,key:s.key,chords:r.chords.map(c=>row[base.indexOf(c)])}}
// Open shapes a beginner meets first. Ease is about these shapes, not about the music.
const easyShapes=['G','C','D','A','E','Em','Am','Dm'];
const scaleSteps={major:[0,2,4,5,7,9,11],minor:[0,2,3,5,7,8,10]};
function scaleNotes(s){return scaleSteps[s.mode]?scaleSteps[s.mode].map((n,i)=>spellFrom(s.key,n,i)):null}
function keyChords(s){const row=palette(s);return inKeyIndices(s).map(i=>row[i])}
function keyEase(key,mode){const chords=keyChords({key,mode}),easy=chords.filter(c=>easyShapes.includes(c)).length;return {easy,level:easy>=5?3:easy>=4?2:1,home:easyShapes.includes(chords[0])}}
// An easy home chord comes first: a key is hard to live in if its home chord is a barre.
function rankedKeys(mode){const keys=keyGroups[mode].keys;if(mode==='power')return keys.slice();const score=k=>{const e=keyEase(k,mode);return (e.home?10:0)+e.easy};return keys.slice().sort((a,b)=>score(b)-score(a))}
function keyWhy(s){if(s.mode==='power')return 'Two-note shapes you can move along the neck.';const e=keyEase(s.key,s.mode);return e.easy>=5?`${e.easy} of 7 chords are easy open shapes`:e.easy>=4?`${e.easy} easy shapes, the rest need barres`:'Fewer easy shapes: try a capo'}
function keyHearChords(s){const row=palette(s);return ({major:[0,3,4,0],minor:[0,2,6,0],power:[0,2,5,0]})[s.mode].map(i=>row[i])}
function visibleRecipes(mode){return feelRecipes.filter(r=>r.mode===mode)}
function chordName(c){return c.replace('dim','°')}
function bandReady(){return Boolean(currentSection().started)}
const diceIcon='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="4"></rect><circle cx="8" cy="8" r="1.3" fill="currentColor"></circle><circle cx="16" cy="16" r="1.3" fill="currentColor"></circle><circle cx="12" cy="12" r="1.3" fill="currentColor"></circle><circle cx="16" cy="8" r="1.3" fill="currentColor"></circle><circle cx="8" cy="16" r="1.3" fill="currentColor"></circle></svg>';
const playIcon='<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 4l13 8-13 8z"></path></svg>',stopIcon='<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="1"></rect></svg>',backIcon='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7"></path></svg>';
function hearButton(label,action,playing){return `<button type="button" class="hear" data-action="${action}" aria-label="${playing?'Stop':'Hear'} ${esc(label)}">${playing?stopIcon:playIcon}</button>`}
function cta(label,action,disabled=false){return `<button type="button" class="cta" data-action="${action}"${disabled?' disabled':''}>${label}</button>`}
function statusLine(){return feelUI.message?`<p class="status" role="status">${esc(feelUI.message)}</p>`:''}
const stepNames=[['path','Path'],['feel','Feel'],['key','Key'],['chords','Chords'],['build','Song']];
function stepReached(step){const s=currentSection();return step==='path'||step==='feel'||(step==='build'?bandReady():Boolean(s.feel))}
function stepsBar(){const at=stepNames.findIndex(([id])=>id===feelUI.screen);return `<nav class="steps" aria-label="Steps">${stepNames.map(([id,name],i)=>`<button type="button" class="step ${i<=at?'done':''}" data-action="feel-go:${id}"${i===at?' aria-current="step"':''}${stepReached(id)?'':' disabled'}>${name}</button>`).join('')}</nav>`}
// Song path (9 November design, step 1 alternative): the whole song as a trail. Built steps open in order; the rest say when they arrive.
const pathIcons={feel:'M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z',key:'M9 18V5l10-2v13M9 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0zM19 16a2 2 0 1 1-4 0 2 2 0 0 1 4 0z',loop:'M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3',drums:'M4 9c0-2 3.6-3 8-3s8 1 8 3-3.6 3-8 3-8-1-8-3zM4 9v6c0 2 3.6 3 8 3s8-1 8-3V9',bass:'M15 3l6 6M18 6l-7 7M10 13a4 4 0 1 0-1 5 4 4 0 0 0 1-5z',sections:'M4 6h7v5H4zM13 6h7v5h-7zM4 13h16v5H4z',lead:'M13 3L5 14h6l-1 7 8-11h-6z',vocals:'M9 4a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0zM5 11a7 7 0 0 0 14 0M12 18v3'};
const pathSteps=[
 {id:'feel',name:'Feel',line:'Happy, moody or heavy?',unit:'Foundation',built:true},
 {id:'key',name:'Key',line:'Find where your song lives',built:true},
 {id:'loop',name:'Chords',line:'Pick a sequence and make it yours',built:true},
 {id:'drums',name:'Drums',line:'Add a beat',unit:'Band',built:true},
 {id:'bass',name:'Bass',line:'Lock in the low end',built:true},
 {id:'sections',name:'Sections',line:'Verse, chorus, repeat',unit:'Song',built:false},
 {id:'lead',name:'Lead',line:'A riff or a solo',built:false},
 {id:'vocals',name:'Vocals',line:'Hum a melody',built:false}];
const PATH_ZIG=[0,-70,-20,60,0,-70,10,70];
function pathDone(id){const s=currentSection();return id==='feel'?Boolean(s.feel):id==='key'?Boolean(s.keyDone||s.started):id==='loop'?bandReady():id==='drums'?Boolean(drumState.done&&bandReady()):id==='bass'?Boolean(bassState.done&&bandReady()):false}
// A built step opens once every built step before it is done. Steps not built yet stay closed.
function pathStatus(i){const st=pathSteps[i];if(!st.built)return 'later';if(pathDone(st.id))return 'done';return pathSteps.slice(0,i).every(p=>!p.built||pathDone(p.id))?'open':'locked'}
function pathCurrent(){const i=pathSteps.findIndex((_,k)=>pathStatus(k)==='open');return i<0?pathSteps.findIndex(p=>p.built&&!pathDone(p.id)):i}
const tickIcon='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5L20 7"></path></svg>',lockIcon='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"></rect><path d="M8 11V8a4 4 0 0 1 8 0v3"></path></svg>';
function pathView(){const done=pathSteps.filter(p=>pathDone(p.id)).length,cur=pathCurrent(),sel=feelUI.pathSel??(cur<0?pathSteps.length-1:cur),st=pathSteps[sel],status=pathStatus(sel),before=pathSteps.slice(0,sel).reverse().find(p=>p.built&&!pathDone(p.id));
 const buddy=done===0?"Let's make a song!":cur<0?'Your band is ready!':'Next up: '+pathSteps[cur].name;
 const units=[],nodes=pathSteps.map((p,i)=>{const k=pathStatus(i),label=`${p.name}, ${{done:'done',open:'start here',locked:'locked',later:'coming later'}[k]}`;return `${p.unit?`<div class="path-unit ${pathSteps.findIndex(q=>q.unit===p.unit)<=Math.max(cur,0)||k==='done'?'on':''}">${p.unit}</div>`:''}<div class="path-node ${k} ${sel===i?'selected':''}" style="--zig:${PATH_ZIG[i]}px"><button type="button" data-action="path-pick:${i}" aria-label="${label}" aria-pressed="${sel===i}"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${pathIcons[p.id]}"></path></svg>${k==='done'?`<i class="path-tick">${tickIcon}</i>`:''}</button></div>`}).join('');
 const line=status==='later'?'Coming later':status==='locked'?'Unlocks after '+before.name:status==='done'?'Done · tap to revisit':st.line;
 const go=status==='open'||status==='done'?`<button type="button" class="path-start" data-action="path-start:${st.id}">${status==='done'?'Open':'Start'}</button>`:`<span class="path-locked">${lockIcon}${status==='later'?'Soon':'Locked'}</span>`;
 return `<section class="path-screen"><header class="path-head"><a class="round" href="./" aria-label="Back to home">${backIcon}</a><div class="path-progress"><span>New song</span><div class="path-bar" role="progressbar" aria-valuemin="0" aria-valuemax="${pathSteps.length}" aria-valuenow="${done}"><i style="width:${Math.max(4,done/pathSteps.length*100)}%"></i></div></div><span class="mono path-count">${done} / ${pathSteps.length}</span></header>
 <div class="path"><div class="path-buddy" aria-hidden="true"><div class="bubble">${esc(buddy)}</div><svg width="64" height="70" viewBox="0 0 60 64"><path d="M30 4C14 4 4 12 4 22c0 14 13 31 26 38 13-7 26-24 26-38C56 12 46 4 30 4z" fill="#F2A93B"></path><circle cx="22" cy="24" r="4" fill="#14110E"></circle><circle cx="38" cy="24" r="4" fill="#14110E"></circle><circle cx="23.3" cy="22.7" r="1.3" fill="#F5EEE4"></circle><circle cx="39.3" cy="22.7" r="1.3" fill="#F5EEE4"></circle><path d="M23 34c4 4 10 4 14 0" fill="none" stroke="#14110E" stroke-width="2.6" stroke-linecap="round"></path></svg></div>${nodes}</div>
 <div class="path-sheet" role="status"><div><b>${st.name}</b><span>${line}</span></div>${go}</div></section>`}
function pathAction(action,value){if(!action.startsWith('path-'))return false;
 if(action==='path-pick'){const i=Number(value);if(pathSteps[i])feelUI.pathSel=i;render();return true}
 const st=pathSteps.find(p=>p.id===value),i=pathSteps.indexOf(st);if(!st||!['open','done'].includes(pathStatus(i)))return true;
 stopGuidePreview();feelUI.pathSel=null;feelUI.message='';
 if(st.id==='bass'||st.id==='drums'){bassState.tab=st.id;render();return true}
 feelUI.screen=st.id==='loop'?(bandReady()?'build':'chords'):st.id;render();return true}
function songHeader(){
 const s=currentSection(),tab=bassState.tab,member=tab!=='rhythm',screen=feelUI.screen,named=member||screen==='chords'||screen==='build',feel=s.feel?feels[s.feel].name:'';
 const back=member?'member:rhythm':{feel:'feel-go:path',key:'feel-go:feel',chords:'feel-go:key',build:'feel-go:chords'}[screen];
 const sub=tab==='drums'?[keyName(s),rhythm.bpm+' BPM','4/4'].join(' · '):tab==='bass'?'Bass follows your chords: '+s.chords.map(c=>chordName(c)+' '+numeral(s,c)).join(' · '):tab==='tracks'?[keyName(s),rhythm.bpm+' BPM','4/4'].join(' · '):named?[feel,keyName(s),rhythm.bpm+' BPM'].filter(Boolean).join(' · '):screen==='key'?feel:'Not saved yet';
 const action=member?'':screen==='build'?hearButton('my song','r-guide-hear',guide.playing&&!feelUI.playingRecipe&&!bassState.playing):screen==='key'?`<button type="button" class="round dice" data-action="key-dice" aria-label="Surprise me with a key">${diceIcon}</button>`:screen==='chords'?`<button type="button" class="round dice" data-action="loop-dice" aria-label="Surprise me with a sequence">${diceIcon}</button>`:'';
 return `<header class="song-head">${back?`<button type="button" class="round" data-action="${back}" aria-label="Back">${backIcon}</button>`:`<a class="round" href="./" aria-label="Back to home">${backIcon}</a>`}<div class="song-title"><h1>${named?'Untitled in '+s.key:'New song'}</h1><p>${esc(sub)}</p></div>${action}</header>`}
function viewToggle(){if(!bandReady()||(bassState.tab==='rhythm'&&feelUI.screen!=='build'))return '';const tracks=bassState.tab==='tracks';return `<div class="view-seg" role="group" aria-label="View"><button type="button" data-action="member:${tracks?'rhythm':'tracks'}" aria-pressed="${!tracks}">Members</button><button type="button" data-action="member:tracks" aria-pressed="${tracks}">Tracks</button></div>`}
function bandSelector(){const ready=bandReady(),members=[['Singer','Vo'],['Drums','Dr','drums'],['Rhythm','Rh','rhythm'],['Bass','Ba','bass'],['Lead','Ld']];
 return `<nav class="band" aria-label="Band members">${members.map(([name,short,tab])=>{const active=tab===bassState.tab,usable=tab==='rhythm'||(tab&&ready);return usable?`<button type="button" class="member ${active?'active':''}" data-action="member:${tab}" aria-pressed="${active}"><span class="disc">${short}</span><span>${name}</span></button>`:`<span class="member unavailable" aria-label="${name}: ${tab?'needs chords first':'not available yet'}"><span class="disc">${short}</span><span>${name}</span></span>`}).join('')}</nav>${ready?'':'<p class="band-note">The rest of the band joins once you have chords</p>'}`}
function feelView(){const s=currentSection(),chosen=s.feel&&feels[s.feel];
 return `<section class="screen"><div class="intro"><h2>How should it feel?</h2></div><div class="feel-grid">${Object.entries(feels).map(([id,f])=>{const r=feelRecipes.find(x=>x.id===f.recipe),on=s.feel===id;return `<div class="feel-card ${on?'on':''}"><button type="button" class="feel-pick" data-action="feel-pick:${id}" aria-pressed="${on}"><b>${f.name}</b><small>${f.note}</small></button><div class="row between"><span class="mono">${[...new Set(r.chords)].join(' ')}</span>${hearButton(f.name,'feel-hear:'+id,feelUI.playingRecipe==='feel-'+id)}</div></div>`}).join('')}</div>${statusLine()}${cta(chosen?chosen.name+': pick a key':'Pick a feel to go on','feel-go:key',!chosen)}</section>`}
// Key wheel: the circle of fifths, each minor key beside its relative major. Power chords follow the major circle.
const wheelOrder={major:['C','G','D','A','E','B','F♯','D♭','A♭','E♭','B♭','F'],minor:['A','E','B','F♯','C♯','G♯','E♭','B♭','F','C','G','D']};
wheelOrder.power=wheelOrder.major;
function wheelKeys(mode){return wheelOrder[mode]}
function relativeKey(from,key,to){return wheelOrder[to][wheelOrder[from].indexOf(key)]||keyGroups[to].keys[0]}
// Four pads to jam on in the chosen key: the most used chords of each family.
const padDegrees={major:[0,4,5,3],minor:[0,5,1,4],power:[0,1,2,4]};
function padChords(s){const row=palette(s);return padDegrees[s.mode].map(i=>row[i])}
const keyNoun=(s,k)=>k+(s.mode==='minor'?'m':s.mode==='power'?'5':'');
function keyView(){const s=currentSection(),power=s.mode==='power',notes=scaleNotes(s),friendly=rankedKeys(s.mode).slice(0,5),looping=feelUI.playingRecipe==='key-loop',title=keyName(s),now=keyNoun(s,s.key);
 const wheel=wheelKeys(s.mode).map((k,i)=>{const on=k===s.key,easy=friendly.includes(k),size=on?60:easy?52:40,a=(i*30-90)*Math.PI/180,x=150+118*Math.cos(a)-size/2,y=150+118*Math.sin(a)-size/2;return `<button type="button" class="wheel-key ${on?'on':easy?'easy':''}" style="left:${x.toFixed(1)}px;top:${y.toFixed(1)}px;width:${size}px;height:${size}px" data-action="key-pick:${k}" aria-pressed="${on}" aria-label="${k}${power?' power chords':' '+s.mode}${easy?', guitar friendly':''}">${keyNoun(s,k)}</button>`}).join('');
 return `<section class="screen"><div class="intro"><h2>Find where your song lives</h2><p>Tap a key to hear the band in it.</p></div><div class="wheel">${wheel}<button type="button" class="wheel-centre ${looping?'playing':''}" data-action="key-play" aria-label="${looping?'Stop the band':'Play the band in '+title}"><b>${now}</b><span>${power?'power chords':s.mode==='minor'?'minor · moody':'major · bright'}</span><small>${looping?'playing · tap to stop':'tap to play'}</small></button></div><div class="mode-row"><span>Brighter</span><div class="mode-seg slim" role="group" aria-label="Chord family">${['major','minor','power'].map(m=>`<button type="button" data-action="feel-group:${m}" aria-pressed="${s.mode===m}">${{major:'Major',minor:'Minor',power:'Power'}[m]}</button>`).join('')}</div><span>Moodier</span></div><div class="pad-grid four">${padChords(s).map((c,i)=>{const lit=looping&&guide.playingBar>=0&&guide.playingBar%4===i;return `<button type="button" class="pad ${i?'':'home'} ${lit?'lit':''}" data-action="key-pad:${i}" aria-label="Play ${c}"><small class="mono">${labelsFor(s)[padDegrees[s.mode][i]]}</small><b>${chordName(c)}</b><small>${power?'two notes':easyShapes.includes(c)?'easy shape':'barre'}</small></button>`}).join('')}</div><p class="hint">Teal keys have the easiest shapes.</p>
 <details class="more"><summary>What's a key?</summary><p>A key is the note your song keeps coming home to, plus the notes and chords that belong with it.</p><div class="card"><div class="row between"><div class="key-title"><b>${title}</b><small>${keyWhy(s)}</small></div><button type="button" class="pill" data-action="key-hear">${feelUI.playingRecipe==='key'?stopIcon+' Stop':playIcon+' Hear home'}</button></div>${notes?`<div class="block"><span class="label">The 7 notes · home note first</span><div class="note-row">${notes.map((n,i)=>`<span class="${i?'':'home'}">${n}</span>`).join('')}</div></div>`:''}<div class="block"><span class="label">${power?'Power chords to explore':'Chords you get · easy open shapes in teal'}</span><div class="chord-row">${keyChords(s).map(c=>`<span class="${easyShapes.includes(c)?'easy':''}">${chordName(c)}</span>`).join('')}</div></div></div></details>${statusLine()}${cta(`${now} feels like home →`,'feel-go:chords')}</section>`}
// Chords step: pick a proven sequence. Popular ones come first, then the easiest shapes in this key.
const SEQ_FIRST=4,POPULAR=['H1','H2','H3','S2','S3','R1','R5'];
function sequencesFor(s){return visibleRecipes(s.mode).map((x,i)=>{const r=recipeForKey(x.id);return {r,i,pop:POPULAR.includes(r.id)?0:1,hard:r.mode==='power'?0:r.chords.filter(c=>!easyShapes.includes(c)).length}}).sort((a,b)=>a.pop-b.pop||a.hard-b.hard||a.i-b.i).map(x=>x.r)}
function recipeDegrees(id){const row=palette(currentSection());return recipeForKey(id).chords.map(c=>row.indexOf(c))}
// Every chord shows its Roman numeral underneath.
function numeral(s,chord){const i=palette(s).indexOf(chord);return i<0?'':labelsFor(s)[i]}
function chordStack(s,chords){return `<span class="chord-stack">${chords.map(c=>`<span><b>${chordName(c)}</b><small class="mono">${numeral(s,c)}</small></span>`).join('')}</span>`}
function sequenceCard(s,r){const on=s.started&&s.recipe===r.id,pop=POPULAR.includes(r.id);return `<div class="seq ${on?'on':''} ${pop?'popular':''}"><button type="button" class="seq-pick" data-action="loop-seq:${r.id}" aria-pressed="${on}" aria-label="Use ${r.chords.join(' ')}, ${esc(r.name)}${pop?', popular':''}">${chordStack(s,r.chords)}<small>${pop?'<i class="badge">Popular</i> ':''}${esc(r.name)}</small></button>${hearButton(r.chords.join(' '),'r-feel-preview:'+r.id,feelUI.playingRecipe===r.id)}</div>`}
function chordsView(){const s=currentSection(),all=sequencesFor(s),open=feelUI.allSeq||all.findIndex(r=>s.started&&r.id===s.recipe)>=SEQ_FIRST,list=open?all:all.slice(0,SEQ_FIRST);
 return `<section class="screen"><div class="intro"><h2>Pick a sequence</h2><p>Tap one to use it. You can change any bar next.</p></div><div class="stack">${list.map(r=>sequenceCard(s,r)).join('')}</div>${open||all.length<=SEQ_FIRST?'':'<button type="button" class="wide" data-action="loop-more">More sequences</button>'}${statusLine()}</section>`}
// Replacements from the Song Chords reference (docs/reference): each rule names the chord it replaces and, where the book ties it to a place, the chord before or after.
const bookRules={
 major:[
  {from:4,to:6,label:'Bluesier way home'},
  {from:3,to:11,label:'Tender, romantic'},
  {from:1,to:9,next:[3,4],label:'Brief lift before IV or V'},
  {from:2,to:10,next:[5],label:'Pulls toward vi'},
  {from:5,to:7,label:'Harder rock edge'},
  {from:'any',to:6,next:[0],label:'Rock ending into home'},
  {from:'any',to:8,prev:[0],next:[3],label:'Bluesy hard-rock step'}],
 minor:[
  {from:3,to:6,label:'Stronger pull home'},
  {from:6,to:3,label:'Softer'},
  {from:2,to:7,label:'Brighter (Dorian)'},
  {from:7,to:2,label:'Darker'},
  {from:4,to:6,next:[0],label:'Stronger pull home'}],
 power:[
  {from:5,to:4,label:'Rock way home'},
  {from:'any',to:4,next:[0],label:'Rock ending into home'},
  {from:'any',to:1,prev:[2],next:[0],label:'Bluesy step down'}]};
function baseDegrees(s){return (originalDegrees(s)||s.barDegrees).slice(0,4)}
function bookSuggestions(s){const base=baseDegrees(s),n=base.length,out=[];base.forEach((cur,bar)=>{const prev=base[(bar+n-1)%n],next=base[(bar+1)%n];if(bar===0&&cur===0)return;for(const r of bookRules[s.mode]||[]){if(r.from==='any'?(cur===0||cur===r.to):r.from!==cur)continue;if(r.next&&!r.next.includes(next))continue;if(r.prev&&!r.prev.includes(prev))continue;if(!out.some(o=>o.bar===bar&&o.to===r.to))out.push({bar,from:cur,to:r.to,label:r.label})}});return out}
function sugApplied(s,o){return s.barDegrees.every((d,i)=>i%4!==o.bar||d===o.to)}
function withSuggestion(s,o){const row=palette(s),base=baseDegrees(s);return base.map((d,i)=>row[i===o.bar?o.to:d])}
function originalDegrees(s){if(!s.recipe)return null;const p=recipeDegrees(s.recipe);return s.barDegrees.map((_,i)=>p[i%4])}
function altered(s){const o=originalDegrees(s);return Boolean(o)&&o.join()!==s.barDegrees.join()}
// The whole chord table, grouped as the book groups its columns.
const chordGroups={major:[['Basic',[0,1,2,3,4,5]],['Rock / blues',[6,7,8]],['Reverse polarity',[9,10,11]]],minor:[['Natural minor',[0,1,2,3,4,5]],['Colour',[6,7]]],power:[['Power chords',[0,1,2,3,4,5]]]};
function songView(){const s=currentSection(),row=palette(s),labels=labelsFor(s);guide.selectedBar=Math.min(guide.selectedBar,s.bars-1);const bar=guide.selectedBar,now=s.barDegrees[bar],sugs=bookSuggestions(s),field=(label,control)=>`<label>${label}${control}</label>`;
 const sugRow=o=>{const on=sugApplied(s,o),id=`sug-${o.bar}-${o.to}`;return `<div class="sug ${on?'on':''}"><div class="sug-text"><b>Bar ${o.bar+1} · ${chordName(row[o.from])} → ${chordName(row[o.to])}</b><small><span class="mono">${labels[o.from]} → ${labels[o.to]}</span> · ${o.label}</small></div>${hearButton(`bar ${o.bar+1} as ${row[o.to]}`,`r-feel-sughear:${o.bar},${o.to}`,feelUI.playingRecipe===id)}<button type="button" class="use" data-action="r-feel-sug:${o.bar},${o.to}" aria-pressed="${on}">${on?'Undo':'Use'}</button></div>`};
 return `<section class="screen"><div class="intro"><h2>Make it yours</h2><p>Try a suggestion, or tap a bar to swap any chord.</p></div>${statusLine()}<div class="bar-grid">${s.barDegrees.map((d,i)=>`<button type="button" data-action="r-feel-bar:${i}" class="bar-cell ${bar===i?'selected':''} ${guide.playingBar===i&&!bassState.playing?'sounding':''}" aria-pressed="${bar===i}" aria-label="Bar ${i+1}, ${row[d]}, ${labels[d]}"><small>Bar ${i+1}</small><b>${chordName(row[d])}</b><small class="mono">${labels[d]}</small></button>`).join('')}</div>
 <div class="chips">${button('Undo','r-feel-undo')}${altered(s)?button(feelUI.playingRecipe==='original'?'■ Stop':'▶ Hear original','r-feel-original'):''}</div>
 ${sugs.length?`<section class="stack"><span class="label">Suggestions from the book</span><div class="sug-list">${sugs.map(sugRow).join('')}</div></section>`:''}
 <section class="stack"><span class="label">Swap bar ${bar+1} · ${chordName(row[now])} ${labels[now]}</span>${chordGroups[s.mode].map(([name,ids])=>`<div class="swap-group"><small>${name}</small><div class="swap-grid">${ids.map(i=>`<button type="button" class="swap-chord ${now===i?'on':''}" data-action="r-feel-swap:${i}" aria-pressed="${now===i}" aria-label="${row[i]}, ${labels[i]}"><b>${chordName(row[i])}</b><small class="mono">${labels[i]}</small></button>`).join('')}</div></div>`).join('')}</section>
 <details class="more"><summary>Tempo and sound</summary><div class="fields">${field('Bars',`<select data-r-field="bars">${[4,8,12,16].map(n=>`<option ${n===s.bars?'selected':''}>${n}</option>`).join('')}</select>`)}${field('Tempo (BPM)',`<input type="number" min="40" max="220" value="${rhythm.bpm}" data-r-field="bpm">`)}${field('Rhythm',`<select data-feel-field="pattern">${Object.entries({quarters:'Quarter-note strums',eighths:'Eighth-note strums',space:'One ringing strum per bar',picked:'Low / upper strings',stomp:'Muted quarters, open beat 4',drive:'Muted eighths, open beat 1'}).map(([v,n])=>`<option value="${v}" ${s.pattern===v?'selected':''}>${n}</option>`).join('')}</select>`)}${field('Tone',`<select data-feel-field="sound">${Object.entries({clean:'Clean',soft:'Soft clean',drive:'Driven'}).map(([v,n])=>`<option value="${v}" ${s.sound===v?'selected':''}>${n}</option>`).join('')}</select>`)}</div>${button('Slow practice: 60 BPM, one strum per bar','r-feel-slow')}</details>
 ${cta('Bring in the drums','member:drums')}<small class="hint">Not saved yet: this song lasts for this visit.</small></section>`}
function screenView(){return ({feel:feelView,key:keyView,chords:chordsView,build:songView})[feelUI.screen]()}
// Deterministic, self-contained plucked strings; no samples, network or microphone.
function voicedNotes(chord){if(shapeMap[chord])return [...shapeMap[chord]].flatMap((f,i)=>f==='x'?[]:[40+[0,5,10,15,19,24][i]+Number(f)]);const p=rootPc(chord),quality=chord.endsWith('dim')?'dim':chord.endsWith('5')?'power':chord.endsWith('m')?'minor':chord.endsWith('7')?'seven':'major';return (quality==='dim'?[0,3,6]:quality==='power'?[0,7]:quality==='minor'?[0,3,7]:quality==='seven'?[0,4,7,10]:[0,4,7]).map(n=>48+p+n)}
function pluckBuffer(ctx,midi,seconds,muted){const sr=ctx.sampleRate,len=Math.ceil(seconds*sr),period=Math.max(2,Math.round(sr/(440*2**((midi-69)/12)))),buf=ctx.createBuffer(1,len,sr),out=buf.getChannelData(0),ring=new Float32Array(period);let seed=1701+midi;for(let j=0;j<period;j++){seed=(1664525*seed+1013904223)>>>0;ring[j]=seed/2147483648-1}for(let i=0;i<len;i++){let at=i%period,next=(at+1)%period;const v=ring[at];ring[at]=.5*(v+ring[next])*.995;out[i]=v*Math.exp(-i/(sr*(muted?.055:1.5)))*Math.min(1,i/(sr*.003))}return buf}
function strumSchedule(pattern){if(pattern==='space')return [{beat:0}];if(pattern==='picked')return [{beat:0,part:'low'},{beat:2,part:'upper'}];const eighth=['eighths','drive'].includes(pattern);return Array.from({length:eighth?8:4},(_,i)=>({beat:i/(eighth?2:1),up:pattern==='eighths'&&i%2===1,muted:pattern==='stomp'?i<3:pattern==='drive'?i>0:false,velocity:pattern==='quarters'&&(i===1||i===3)?1.08:pattern==='eighths'&&i%2===1?.65:1}))}
function arrangementNotes(chords,bpm,pattern,tone){
 const beat=60/bpm,notes=[],progress=[],manifest=[];
 chords.forEach((chord,bar)=>{const voiced=chord?voicedNotes(chord):[];for(const stroke of strumSchedule(pattern)){
  let ns=stroke.part==='low'?voiced.slice(0,1):stroke.part==='upper'?voiced.slice(1):voiced.slice();if(stroke.up)ns.reverse();
  ns.forEach((midi,j)=>{const time=bar*4*beat+stroke.beat*beat+j*.012,duration=stroke.muted?.18:Math.min(2.4,4*beat-stroke.beat*beat+.2);
   notes.push({instrument:'guitar',midi,time,duration,muted:stroke.muted,level:(tone==='soft'?.65:1)*(stroke.velocity||1)/Math.max(2,voiced.length)});
   manifest.push({bar:bar+1,midi,onsetSeconds:+time.toFixed(4),durationSeconds:+duration.toFixed(4),muted:!!stroke.muted});
  });
 }progress.push({bar,time:bar*4*beat})});
 return {notes,progress,manifest};
}
function playArrangement(chords,bpm,pattern,tone,recipeId=null){
 const beat=60/bpm,{notes,progress,manifest}=arrangementNotes(chords,bpm,pattern,tone);
 feelUI.lastPreview={renderer:sampleAudio.engine==='samples'?'fluidr3-with-synth-fallback':'deterministic-plucked-string-v1',recipeId,chords:chords.slice(),bpm,pattern,tone,coreSeconds:chords.length*4*beat,tailSeconds:2.5,loudness:'Fixed gain with driven-output compensation; perceptual matching not validated',events:manifest};
 return previewPlayback.play({notes,progress,tag:{recipeId},level:.22,release:.035,driven:tone==='drive',duration:chords.length*4*beat+2.5});
}
// The band loops only after you press play; a change while it plays restarts it from bar 1.
const LOOP_REPEATS=8;
function playLoop(chords,id){const s=currentSection();return playArrangement(Array.from({length:LOOP_REPEATS},()=>chords).flat(),rhythm.bpm,s.pattern||'quarters',s.sound||'clean',id)}
function playKeyLoop(){return playLoop(padChords(currentSection()),'key-loop')}
function playPad(chord){const s=currentSection(),{notes}=arrangementNotes([chord],rhythm.bpm,'space',s.sound||'clean');return padPlayback.play({notes,progress:[],tag:{},level:.22,release:.035,driven:s.sound==='drive',duration:4*60/rhythm.bpm+2})}
function playGuide(){const s=currentSection();playArrangement(s.chords,rhythm.bpm,s.pattern||'quarters',s.sound||'clean')}
// Starting over from a feel or chord family keeps the old song on the undo stack.
function startFrom(s,mode,key,recipeId){stopGuidePreview();rememberGuide();const r=feelRecipes.find(x=>x.id===recipeId);s.mode=mode;s.key=key;s.comparison=null;s.recipe=null;s.started=false;s.keyDone=false;s.pattern=r.pattern;s.sound=r.tone;s.barDegrees=Array(s.bars).fill(0);syncGuide(s);rhythm.bpm=r.bpm;feelUI.seq=r.id;feelUI.allSeq=false;feelUI.message=''}
function loopAction(action,value){if(!action.startsWith('loop-'))return false;const s=currentSection(),current=x=>s.started&&s.recipe===x.id;feelUI.message='';
 if(action==='loop-more'){feelUI.allSeq=true;render();return true}
 const list=visibleRecipes(s.mode),fresh=list.filter(x=>!current(x)),r=action==='loop-dice'?fresh[Math.floor(Math.random()*fresh.length)]:action==='loop-seq'?list.find(x=>x.id===value):null;if(!r)return true;
 // Tapping the sequence you already have returns to your song without undoing your changes.
 stopGuidePreview();if(current(r))feelUI.screen='build';else applyRecipe(r.id);render();return true}
function keyAction(action,value){if(!action.startsWith('key-'))return false;const s=currentSection();
 if(action==='key-hear'){if(feelUI.playingRecipe==='key'){stopGuidePreview();render()}else playArrangement(keyHearChords(s),90,'quarters','clean','key');return true}
 if(action==='key-play'){if(feelUI.playingRecipe==='key-loop'){stopGuidePreview();render()}else playKeyLoop();return true}
 if(action==='key-pad'){const c=padChords(s)[Number(value)];if(c)playPad(c);return true}
 if(action==='key-dice'){const options=rankedKeys(s.mode).slice(0,5).filter(k=>k!==s.key);value=options[Math.floor(Math.random()*options.length)]}
 if(!keyGroups[s.mode].keys.includes(value))return true;
 const was=feelUI.playingRecipe==='key-loop';stopGuidePreview();rememberGuide();s.key=value;s.comparison=null;syncGuide(s);render();if(was)playKeyLoop();return true}
function feelAction(action,value){if(pathAction(action,value)||keyAction(action,value)||loopAction(action,value))return true;if(!action.startsWith('feel-'))return false;const s=currentSection();if(action==='feel-pick'){if(s.feel!==value){const r=feelRecipes.find(x=>x.id===feels[value].recipe);startFrom(s,r.mode,r.key,r.id);s.feel=value}render();return true}if(action==='feel-hear'){const r=feelRecipes.find(x=>x.id===feels[value].recipe),id='feel-'+value;if(feelUI.playingRecipe===id){stopGuidePreview();render()}else playArrangement(r.chords,r.bpm,r.pattern,r.tone,id);return true}if(action==='feel-go'){if(stepReached(value)){if(feelUI.screen==='key'&&value==='chords')s.keyDone=true;feelUI.pathSel=null;stopGuidePreview();feelUI.message='';feelUI.screen=value;render()}return true}if(action==='feel-preview'){const r=recipeForKey(value);if(feelUI.playingRecipe===value){stopGuidePreview();render()}else playArrangement(r.chords,r.bpm,r.pattern,r.tone,r.id);return true}if(action==='feel-original'){const o=originalDegrees(s);if(feelUI.playingRecipe==='original'||!o){stopGuidePreview();render()}else playArrangement(o.map(d=>palette(s)[d]),rhythm.bpm,s.pattern,s.sound,'original');return true}if(action==='feel-sughear'){const [b,t]=value.split(',').map(Number),o=bookSuggestions(s).find(x=>x.bar===b&&x.to===t),id=`sug-${b}-${t}`;if(feelUI.playingRecipe===id||!o){stopGuidePreview();render()}else playArrangement(withSuggestion(s,o),rhythm.bpm,s.pattern,s.sound,id);return true}const songPlaying=guide.playing&&!feelUI.playingRecipe&&!bassState.playing;stopGuidePreview();feelUI.message='';if(action==='feel-bar')guide.selectedBar=Math.max(0,Math.min(s.bars-1,Number(value)||0));if(action==='feel-sug'){const [b,t]=value.split(',').map(Number),o=bookSuggestions(s).find(x=>x.bar===b&&x.to===t);if(!o)return true;const back=sugApplied(s,o);rememberGuide();s.barDegrees=s.barDegrees.map((d,i)=>i%4===b?(back?o.from:o.to):d);syncGuide(s);render();if(songPlaying)playGuide();return true}if(action==='feel-swap'){const d=Number(value),was=songPlaying;if(!palette(s)[d])return true;rememberGuide();s.barDegrees[guide.selectedBar]=d;syncGuide(s);render();if(was)playGuide();return true}if(action==='feel-slow'){rememberGuide();rhythm.bpm=60;s.pattern='space';feelUI.message='60 BPM, one downstroke per bar. Build up at your pace.'}if(action==='feel-group'&&s.mode!==value){const r=feelRecipes.find(x=>x.mode===value),was=feelUI.playingRecipe==='key-loop';startFrom(s,value,relativeKey(s.mode,s.key,value),r.id);if(feelUI.screen==='key'){render();if(was)playKeyLoop();return true}}if(action==='feel-undo'){const old=feelUI.undo.pop();if(old){rhythm.sections[old.section]=old.data;rhythm.selected=old.section;rhythm.bpm=old.bpm;feelUI.seq=old.data.recipe||feelUI.seq;feelUI.message='Restored the previous version.'}else feelUI.message='Nothing to undo yet.'}render();return true}
document.addEventListener('change',e=>{const field=e.target.dataset.feelField;if(!field)return;stopGuidePreview();rememberGuide();const s=currentSection();if(field==='mode'){s.mode=e.target.value;s.comparison=null;s.recipe=null;s.focusPalette=null;s.barDegrees=s.barDegrees.map(()=>0);syncGuide(s);feelUI.message='Chord family changed. Bars now start on home; Undo restores the previous progression.'}else s[field]=e.target.value;render()});


document.addEventListener('click',e=>{
 const el=e.target.closest('[data-action]');if(!el)return;
 const [raw,...rest]=el.dataset.action.split(':');const action=raw.replace(/^r-/,''),value=rest.join(':');
 try {
  if(bassAction(action,value))return;
  if(feelAction(action,value))return;
  if(action==='guide-hear'){if(guide.playing){stopGuidePreview();render()}else playGuide();return}
  stopGuidePreview();const s=currentSection();
  render();
 }catch(error){stopGuidePreview();feelUI.message='The sound preview could not start. Try again in Safari.';console.error(error);render()}
});
document.addEventListener('change',e=>{
 if(e.target.dataset.feelField)return;
 const s=currentSection();if(!e.target.dataset.guide&&!e.target.dataset.rField)return;
 stopGuidePreview();rememberGuide();
 if(e.target.dataset.guide==='key'){s.key=e.target.value;s.comparison=null;syncGuide(s)}
 if(e.target.dataset.rField==='bars'){const old=s.barDegrees.slice();s.bars=Number(e.target.value);s.barDegrees=Array.from({length:s.bars},(_,i)=>old[i%old.length]);guide.selectedBar=Math.min(guide.selectedBar,s.bars-1);syncGuide(s)}
 if(e.target.dataset.rField==='bpm')rhythm.bpm=Math.max(40,Math.min(220,Number(e.target.value)||92));
 render();
});
window.addEventListener('pagehide',stopGuidePreview);
document.addEventListener('visibilitychange',()=>{if(document.hidden){stopGuidePreview();render()}});
render();
