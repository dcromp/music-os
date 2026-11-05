'use strict';
// Feel-first Bandmaker (#86): key ranking, scale notes, the chords step in every key, and the guided flow.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root={dataset:{},querySelectorAll:()=>[],innerHTML:''};
const ctx={setTimeout,clearTimeout,console,root,document:{querySelector:()=>root,querySelectorAll:()=>[],addEventListener(){}},window:{addEventListener(){}}};
vm.createContext(ctx);
for(const file of ['lib/preview-playback.js','bandmaker-samples.js','bandmaker-bass.js','bandmaker.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',file),'utf8'),ctx);
const run=code=>JSON.parse(vm.runInContext(`JSON.stringify(${code})`,ctx));
const act=(action,value='')=>vm.runInContext(`feelAction(${JSON.stringify(action)},${JSON.stringify(value)})`,ctx);
const html=()=>root.innerHTML;

// Scale notes are spelled with one letter each, home note first.
assert.deepEqual(run("scaleNotes({key:'G',mode:'major'})"),['G','A','B','C','D','E','F♯']);
assert.deepEqual(run("scaleNotes({key:'E',mode:'minor'})"),['E','F♯','G','A','B','C','D']);
assert.deepEqual(run("scaleNotes({key:'D',mode:'minor'})"),['D','E','F','G','A','B♭','C']);
assert.equal(run("scaleNotes({key:'E',mode:'power'})"),null);
for(const mode of ['major','minor'])for(const key of run(`keyGroups.${mode}.keys`)){
 const notes=run(`scaleNotes({key:${JSON.stringify(key)},mode:'${mode}'})`);
 assert.equal(new Set(notes.map(n=>n[0])).size,7,`${key} ${mode} uses each letter once`);
 // Each of the seven chords is built on the matching scale note.
 const chords=run(`keyChords({key:${JSON.stringify(key)},mode:'${mode}'})`);
 assert.equal(chords.length,7);
 chords.forEach((c,i)=>assert.ok(c.startsWith(notes[i]),`${key} ${mode}: ${c} sits on ${notes[i]}`));
}
assert.deepEqual(run("keyChords({key:'G',mode:'major'})"),['G','Am','Bm','C','D','Em','F♯dim']);
assert.deepEqual(run("keyChords({key:'E',mode:'minor'})"),['Em','F♯dim','G','Am','Bm','C','D']);

// Keys are ranked for a beginner: an easy home chord first, then the most easy shapes.
assert.deepEqual(run("rankedKeys('major').slice(0,5)"),['G','C','D','A','E']);
assert.deepEqual(run("rankedKeys('minor').slice(0,5)"),['E','A','D','B','F♯']);
assert.deepEqual(run("rankedKeys('power').slice(0,3)"),['E','A','D']);
for(const mode of ['major','minor','power'])assert.equal(new Set(run(`rankedKeys('${mode}')`)).size,12,`${mode} keeps every key`);
assert.deepEqual(run("keyEase('G','major')"),{easy:5,level:3,home:true});
assert.deepEqual(run("keyEase('D','major')"),{easy:4,level:2,home:true});
assert.deepEqual(run("keyEase('B♭','major')"),{easy:1,level:1,home:false});

// Every key offers its chords step, with a role or a reason for every chord.
for(const mode of ['major','minor','power'])for(const key of run(`keyGroups.${mode}.keys`)){
 const cards=run(`chordCards({key:${JSON.stringify(key)},mode:'${mode}'})`);
 assert.equal(cards.length,mode==='power'?6:7,`${key} ${mode}`);
 assert.equal(cards[0].tag,'home');assert.ok(cards[0].starter);
 assert.equal(cards.filter(c=>c.starter).length,mode==='power'?3:4);
 for(const c of cards)assert.ok(c.tag&&c.name&&c.degree,`${key} ${mode} ${c.name}`);
}
assert.deepEqual(run("chordCards({key:'G',mode:'major'}).map(c=>[c.degree,c.name,c.tag])"),[['I','G','home'],['IV','C','lift'],['V','D','pull home'],['vi','Em','softer'],['ii','Am','later'],['iii','Bm','barre'],['vii°','F♯dim','tension']]);

// Flow: nothing moves on until there is a feel, and Bass waits for chords.
assert.equal(run("feelUI.screen"),'feel');
assert.match(html(),/How should it feel\?/);
act('feel-go','key');assert.equal(run("feelUI.screen"),'feel','no feel chosen yet');
assert.equal(run("bandReady()"),false);
act('feel-pick','sad');
assert.deepEqual(run("[currentSection().mode,currentSection().key,rhythm.bpm,feelUI.seq]"),['minor','E',72,'S1']);
act('feel-pick','heavy');assert.deepEqual(run("[currentSection().mode,currentSection().key]"),['power','E']);
act('feel-pick','happy');assert.deepEqual(run("[currentSection().mode,currentSection().key,rhythm.bpm]"),['major','G',108]);
act('feel-go','build');assert.equal(run("feelUI.screen"),'feel','no sequence chosen yet');
act('feel-go','key');assert.equal(run("feelUI.screen"),'key');assert.match(html(),/Pick a home for your song/);assert.match(html(),/G major/);

// Changing mode or key follows through to the chords and sequences.
act('feel-group','minor');assert.equal(run("feelUI.screen"),'key','stays on the key step');assert.equal(run("feelUI.seq"),'S1');
act('key-pick','A');assert.deepEqual(run("[currentSection().mode,currentSection().key]"),['minor','A']);
act('feel-go','chords');assert.match(html(),/Seven chords live in A minor/);
assert.equal(run("visibleRecipes('minor').length"),4);assert.equal(run("visibleRecipes('major').length"),8);assert.equal(run("visibleRecipes('power').length"),4);
act('seq-pick','S2');assert.equal(run("feelUI.seq"),'S2');assert.match(html(),/E7/,'the sequence is transposed to A minor');
act('feel-use','S2');
assert.equal(run("feelUI.screen"),'build');assert.equal(run("bandReady()"),true);assert.deepEqual(run("currentSection().chords"),['Am','Dm','E7','Am']);
assert.match(html(),/Make it yours/);

// The editor still works; undo steps back through it.
vm.runInContext("guide.selectedBar=1;currentSection().barDegrees[1]=0;syncGuide(currentSection())",ctx);
assert.deepEqual(run("currentSection().chords"),['Am','Am','E7','Am']);
act('feel-reset');assert.deepEqual(run("currentSection().chords"),['Am','Dm','E7','Am']);
act('feel-undo');assert.deepEqual(run("currentSection().chords"),['Am','Am','E7','Am']);

// Bass follows the song; choosing a new feel starts over and locks it again.
vm.runInContext("bassAction('member','bass')",ctx);assert.match(html(),/Pick a bass line/);assert.match(html(),/Bass follows your chords: Am Am E7 Am/);
for(const p of run("bassPatterns.map(p=>p.name)"))assert.ok(html().includes(p),p);
vm.runInContext("bassAction('bass-select','fifths')",ctx);assert.match(html(),/tab-staff/);
vm.runInContext("bassAction('member','rhythm')",ctx);
act('feel-go','feel');act('feel-pick','heavy');assert.equal(run("bandReady()"),false);
vm.runInContext("bassAction('member','bass')",ctx);assert.equal(run("bassState.tab"),'rhythm','Bass stays locked without chords');
act('feel-undo');assert.equal(run("bandReady()"),true,'undo brings the song back');
console.log('Bandmaker flow: key ranking, scale notes, chords in every key, guided steps and band unlock pass');
