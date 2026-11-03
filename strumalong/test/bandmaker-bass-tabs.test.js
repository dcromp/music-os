'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root={dataset:{},querySelectorAll:()=>[]};const ctx={setTimeout,clearTimeout,document:{querySelector:()=>root,querySelectorAll:()=>[],addEventListener(){}},window:{addEventListener(){}}};vm.createContext(ctx);
for(const file of ['bandmaker-samples.js','bandmaker-bass.js','bandmaker.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',file),'utf8'),ctx);
vm.runInContext(`
for(const mode of ['major','minor','power'])for(const key of keyGroups[mode].keys){const chords=palette({mode,key});for(const pattern of bassPatterns){const bars=bassTabBars(chords,pattern.id);bars.forEach((bar,i)=>{const scheduled=bassNotes(chords[i],pattern.id);if(bar.events.length!==scheduled.length)throw Error('Missing tab event');bar.events.forEach((e,j)=>{if(bassStrings[e.string].midi+e.fret!==e.midi)throw Error('Wrong pitch');if(e.midi!==scheduled[j].midi||e.beat!==scheduled[j].beat||e.length!==scheduled[j].length)throw Error('Tab/audio disagreement');if(e.fret<0||e.fret>12||rootPc(e.note)!==e.midi%12)throw Error('Invalid range/spelling')});for(let beat=0;beat<4;beat++){const active=bar.events.filter(e=>e.beat<=beat&&e.beat+e.length>beat);if(active.length>1)throw Error('Overlapping bass notes');const sounding=bassStrings.filter((_,string)=>bassTabCell(bar.events,beat,string)!=='–');if(sounding.length!==active.length)throw Error('Tab sustain/rest mismatch')}})}}
const restBar=bassTabBars(['G'],'space')[0];if(restBar.events.map(e=>e.beat).join(',')!=='0,2'||restBar.events.some(e=>e.length!==1))throw Error('Rest timing');
const held=bassTabBars(['Em'],'roots')[0];if(bassTabCell(held.events,1,0)!=='~'||bassTabCell(held.events,0,0)!=='0')throw Error('Open string hold');
if(bassNotes('B7','tones').map(n=>n.note).join(',')!=='B,D♯,F♯,B')throw Error('Minor-key dominant');
if(bassNotes('F♯dim','fifths')[1].note!=='C')throw Error('Diminished fifth');
if(bassNotes('E5','tones').map(n=>n.note).join(',')!=='E,B,E,B')throw Error('Power chord');
for(const pattern of bassPatterns.filter(p=>p.id!=='octaves'))for(const chords of [['G','C','D','G'],['Em','Am','B7','Em']])if(bassTabBars(chords,pattern.id).some(b=>b.events.some(e=>e.fret>4)))throw Error('Starter position');
`,ctx);
console.log('Bass tabs: all offered keys/chords/patterns match pitch and timing; holds, rests, quality and starter positions pass');
