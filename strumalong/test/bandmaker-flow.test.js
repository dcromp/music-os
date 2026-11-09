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

// Every key offers sequences, transposed, with the easiest shapes first.
for(const mode of ['major','minor','power'])for(const key of run(`keyGroups.${mode}.keys`)){
 const list=run(`(()=>{const s=currentSection(),k=s.key,m=s.mode;s.key=${JSON.stringify(key)};s.mode='${mode}';const out=sequencesFor(s).map(r=>r.chords);s.key=k;s.mode=m;return out})()`);
 assert.ok(list.length>=7,`${key} ${mode} has ${list.length} sequences`);
 for(const chords of list){assert.equal(chords.length,4);for(const c of chords)assert.ok(c&&typeof c==='string',`${key} ${mode}: every chord is named`)}
}
assert.equal(new Set(run("feelRecipes.map(r=>r.id)")).size,run("feelRecipes.length"),'sequence ids are unique');
assert.equal(new Set(run("feelRecipes.map(r=>r.mode+r.chords.join())")).size,run("feelRecipes.length"),'no sequence is repeated');

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

// Key wheel: all twelve keys round the circle of fifths, each minor beside its relative major.
assert.deepEqual(run("wheelKeys('major')"),['C','G','D','A','E','B','F♯','D♭','A♭','E♭','B♭','F']);
assert.deepEqual(run("wheelKeys('minor')"),['A','E','B','F♯','C♯','G♯','E♭','B♭','F','C','G','D']);
for(const mode of ['major','minor','power'])assert.deepEqual(run(`wheelKeys('${mode}').slice().sort()`),run(`keyGroups.${mode}.keys.slice().sort()`),`${mode} wheel holds every key`);
assert.deepEqual(run("padChords({key:'G',mode:'major'})"),['G','D','Em','C']);
assert.deepEqual(run("padChords({key:'E',mode:'minor'})"),['Em','C','G','D']);
assert.deepEqual(run("padChords({key:'E',mode:'power'})"),['E5','G5','A5','D5']);
act('feel-go','key');assert.equal(run("feelUI.screen"),'key');assert.match(html(),/Find where your song lives/);
assert.equal((html().match(/data-action="key-pick:/g)||[]).length,12,'twelve keys on the wheel');
assert.match(html(),/What's a key\?/);assert.match(html(),/The 7 notes/,'the key lesson is kept');
vm.runInContext("var keyStarts=0;const rp=previewPlayback.play;previewPlayback.play=o=>{keyStarts++;return rp(o)}",ctx);act('key-pick','D');assert.equal(run('keyStarts'),0,'tapping a key does not play');assert.equal(run("currentSection().key"),'D');assert.match(html(),/D feels like home/);
vm.runInContext("Math.random=()=>0.99",ctx);act('key-dice');
assert.ok(run("rankedKeys('major').slice(0,5)").includes(run("currentSection().key")),'dice picks a friendly key');assert.notEqual(run("currentSection().key"),'D');

// Brighter / Moodier moves to the relative key.
act('key-pick','G');act('feel-group','minor');assert.deepEqual(run("[currentSection().mode,currentSection().key,feelUI.seq]"),['minor','E','S1']);
assert.equal(run("feelUI.screen"),'key','stays on the key step');
act('feel-group','major');assert.equal(run("currentSection().key"),'G');
act('feel-group','minor');act('key-pick','A');assert.deepEqual(run("[currentSection().mode,currentSection().key]"),['minor','A']);

// Chords: pick a sequence. The first four use the easiest shapes; the rest wait behind one button.
act('feel-go','chords');assert.match(html(),/Pick a sequence/);
assert.equal((html().match(/data-action="loop-seq:/g)||[]).length,4);
assert.deepEqual(run("sequencesFor(currentSection()).slice(0,4).map(r=>r.chords.join(' '))"),['Am Dm E7 Am','Am F C G','Am Dm G C','Am F Dm Am'],'popular first, then easiest shapes');
act('loop-more');assert.equal((html().match(/data-action="loop-seq:/g)||[]).length,run("visibleRecipes('minor').length"));
assert.doesNotMatch(html(),/Spice|Learn more|substitution/);
// Nothing starts playing on its own.
vm.runInContext("var started=0;const realPlay=previewPlayback.play;previewPlayback.play=o=>{started++;return realPlay(o)}",ctx);
act('loop-seq','nope');assert.equal(run("feelUI.screen"),'chords','an unknown sequence is ignored');
act('loop-seq','S2');
assert.equal(run("feelUI.screen"),'build');assert.equal(run("bandReady()"),true);assert.equal(run("currentSection().recipe"),'S2');
assert.deepEqual(run("currentSection().chords"),['Am','Dm','E7','Am'],'sequences are transposed');
assert.match(html(),/Make it yours/);assert.equal(run('started'),0,'picking a sequence does not play');

// Song: the book's suggestions for the whole sequence, Roman numerals on every chord, and the full table grouped below.
const sugs=()=>run("bookSuggestions(currentSection()).map(o=>`${o.bar+1}:${labelsFor(currentSection())[o.from]}>${labelsFor(currentSection())[o.to]}`)");
assert.deepEqual(sugs(),['2:iv>IV','3:V7>v']);
assert.match(html(),/Suggestions from the book/);assert.match(html(),/Brighter \(Dorian\)/);
assert.match(html(),/Dm<\/b><small class="mono">iv</,'bars show numerals');
assert.match(html(),/Natural minor/);assert.match(html(),/Colour/);
assert.doesNotMatch(html(),/Hear original/);
act('feel-sughear','2,3');act('feel-sughear','9,9');
act('feel-sug','2,3');assert.deepEqual(run("currentSection().chords"),['Am','Dm','Em','Am']);
assert.match(html(),/aria-pressed="true">Undo/);assert.match(html(),/Hear original/);
assert.deepEqual(sugs(),['2:iv>IV','3:V7>v'],'suggestions stay put after one is used');
act('feel-sug','2,3');assert.deepEqual(run("currentSection().chords"),['Am','Dm','E7','Am'],'tapping again puts it back');
act('feel-sug','0,5');assert.deepEqual(run("currentSection().chords"),['Am','Dm','E7','Am'],'an unknown suggestion is ignored');
act('feel-bar','2');act('feel-swap','3');assert.deepEqual(run("currentSection().chords"),['Am','Dm','Em','Am']);
assert.equal(run('started'),1,'only the hear button played; using a suggestion or swap does not');
act('feel-swap','99');assert.deepEqual(run("currentSection().chords"),['Am','Dm','Em','Am'],'an unknown chord is ignored');
act('feel-undo');assert.deepEqual(run("currentSection().chords"),['Am','Dm','E7','Am']);
// Going back and tapping the same sequence keeps your changes; another one replaces them.
act('feel-sug','1,7');act('feel-go','chords');assert.match(html(),/class="seq on/);
act('loop-seq','S2');assert.deepEqual(run("currentSection().chords"),['Am','D','E7','Am']);
vm.runInContext("Math.random=()=>0",ctx);act('feel-go','chords');act('loop-dice');assert.notEqual(run("currentSection().recipe"),'S2','dice picks a different sequence');
act('feel-go','chords');act('loop-seq','S2');vm.runInContext("currentSection().barDegrees[1]=0;syncGuide(currentSection())",ctx);
// Book rules in major and power, including the ones tied to a place.
const book=(mode,key,degrees)=>run(`bookSuggestions({mode:'${mode}',key:'${key}',bars:4,barDegrees:${JSON.stringify(degrees)},recipe:null}).map(o=>palette({mode:'${mode}',key:'${key}'})[o.to]+'@'+(o.bar+1)+' '+o.label)`);
assert.deepEqual(book('major','G',[0,3,4,0]),['Cm@2 Tender, romantic','F@3 Bluesier way home']);
assert.ok(book('major','G',[0,3,4,0]).includes('F@3 Bluesier way home'));
assert.ok(book('major','G',[0,1,4,0]).includes('A@2 Brief lift before IV or V'));
assert.ok(!book('major','G',[0,1,5,0]).some(x=>x.startsWith('A@2')),'major II only before IV or V');
assert.ok(book('major','G',[0,2,3,0]).includes('B♭@2 Bluesy hard-rock step'),'♭III between I and IV');
assert.ok(book('power','E',[0,2,5,0]).includes('D5@3 Rock way home'),'power chords get suggestions');
assert.ok(book('major','G',[0,5,3,4]).every(x=>!x.endsWith('@1')),'home on bar 1 is never replaced');
// Sequence cards show numerals; popular ones are marked and listed first.
act('feel-go','chords');assert.match(html(),/<i class="badge">Popular<\/i>/);assert.match(html(),/<small class="mono">iv<\/small>/);
assert.deepEqual(run("sequencesFor(currentSection()).slice(0,2).map(r=>r.id)"),['S2','S3']);
act('loop-seq','S2');
assert.equal((html().match(/<details/g)||[]).length,1,'Song keeps one menu: Tempo and sound');

// Tracks: Rhythm and Bass lanes play together, with mute and solo.
vm.runInContext("bassAction('member','tracks')",ctx);assert.equal(run("bassState.tab"),'tracks');
assert.match(html(),/class="lane/);assert.equal((html().match(/Coming later/g)||[]).length,3,'Singer, Drums and Lead');
const instruments=()=>[...new Set(run("bandNotes().map(n=>n.instrument)"))].sort();
assert.deepEqual(instruments(),['bass','guitar']);
vm.runInContext("bassAction('tracks-mute','rhythm')",ctx);assert.deepEqual(instruments(),['bass']);
vm.runInContext("bassAction('tracks-mute','rhythm')",ctx);vm.runInContext("bassAction('tracks-solo','rhythm')",ctx);assert.deepEqual(instruments(),['guitar']);
vm.runInContext("bassAction('tracks-solo','rhythm')",ctx);assert.deepEqual(instruments(),['bass','guitar']);
vm.runInContext("bassAction('tracks-select','bass')",ctx);assert.match(html(),/Open Bass/);
vm.runInContext("bassAction('member','rhythm')",ctx);

// Bass follows the song; choosing a new feel starts over and locks it again.
vm.runInContext("bassAction('member','bass')",ctx);assert.match(html(),/Pick a bass line/);assert.match(html(),/Bass follows your chords: Am i · Am i · E7 V7 · Am i/);
for(const p of run("bassPatterns.map(p=>p.name)"))assert.ok(html().includes(p),p);
vm.runInContext("bassAction('bass-select','fifths')",ctx);assert.match(html(),/tab-staff/);
vm.runInContext("bassAction('member','rhythm')",ctx);
act('feel-go','feel');act('feel-pick','heavy');assert.equal(run("bandReady()"),false);
vm.runInContext("bassAction('member','bass')",ctx);assert.equal(run("bassState.tab"),'rhythm','Bass stays locked without chords');
vm.runInContext("bassAction('member','tracks')",ctx);assert.equal(run("bassState.tab"),'rhythm','Tracks stays locked without chords');
act('feel-undo');assert.equal(run("bandReady()"),true,'undo brings the song back');
console.log('Bandmaker flow: key ranking, scale notes, key wheel, sequence picker, bar swaps, Tracks lanes, guided steps and band unlock pass');
