from __future__ import annotations
import json, hashlib, pathlib, urllib.request, subprocess, wave, datetime, math
ROOT=pathlib.Path('/private/tmp/music-os-plan-20261010')
ASSETS=ROOT/'experiments/candidate-assets/jazzsamba-20261012'
OUT=ROOT/'experiments/generated/jazzsamba-reference-v1'
COMMIT='3715097238b33593d865d05b772e094642843612'
BASE=f'https://raw.githubusercontent.com/pnlong/jazzsamba-demo/{COMMIT}/'
PICKS=[(7,'development'),(51,'holdout'),(75,'holdout')]
CLIP=60.0
MAX_METADATA=2_000_000
MAX_AUDIO=9_000_000

def sha(b): return hashlib.sha256(b).hexdigest()
def gitsha(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def put(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists(): raise FileExistsError(path)
 path.write_text(json.dumps(obj,indent=2)+'\n')
def fetch(path,budget):
 u=BASE+path
 with urllib.request.urlopen(u,timeout=30) as response:
  if response.status!=200: raise ValueError('Expected HTTP 200')
  b=response.read(budget+1)
 if len(b)>budget: raise ValueError('Byte limit exceeded')
 ent=TREE[path]
 if len(b)!=ent['size'] or gitsha(b)!=ent['sha']: raise ValueError('Git blob identity mismatch '+path)
 return b,{'url':u,'path':path,'bytes':len(b),'sha256':sha(b),'git_blob_sha1':ent['sha']}

def boolean(v):
 if v not in ['True','False']: raise ValueError('Invalid boolean')
 return v=='True'

def labels(row):
 if boolean(row['is_no_chord']): return 'N','N'
 root=row['root']; triad=row['triad']; seventh=row['seventh']
 if root in ['', 'NA'] or triad not in ['maj','min','dim','aug']: raise ValueError('Unknown triad '+str(row))
 full={('maj','none'):'maj',('min','none'):'min',('dim','none'):'dim',('aug','none'):'aug',('maj','dom'):'7',('maj','maj'):'maj7',('min','min'):'min7',('min','maj'):'minmaj7',('dim','min'):'hdim7',('dim','dim'):'dim7'}.get((triad,seventh))
 if not full: raise ValueError('Unknown quality '+str(row))
 if any(boolean(row.get(k,'False')) for k in ['has_6','has_9','has_11','has_13','has_add9','alt_b5','alt_sharp5','alt_b9','alt_sharp9','alt_sharp11','alt_b11','is_sus2','is_sus4','is_slash']):
  # Retain original field decomposition for later reviewed conversion; do not guess extensions.
  full='X'
 else: full=root+':'+full
 core=root+':'+triad if triad in ['maj','min'] else 'X'
 return full,core

ASSETS.mkdir(parents=True,exist_ok=True)
if OUT.exists() and any(OUT.iterdir()): raise FileExistsError(OUT)
OUT.mkdir(parents=True,exist_ok=True)
with urllib.request.urlopen('https://api.github.com/repos/pnlong/jazzsamba-demo/git/trees/'+COMMIT+'?recursive=1',timeout=20) as r: tree=json.load(r)
if tree.get('truncated'): raise ValueError('Tree truncated')
TREE={e['path']:e for e in tree['tree'] if e['type']=='blob'}
catb,catmeta=fetch('data/catalog.json',MAX_METADATA)
(ASSETS/'catalog.json').write_bytes(catb)
cat=json.loads(catb)
selected=[]
for song_id,split in PICKS:
 song=next(s for s in cat['songs'] if s['song_id']==song_id)
 selected.append({'id':'jazzsamba-'+song['song_subdir_basename'].replace('_','-')+'-preferred-first60','song_id':song_id,'split':split,'song':song,'clip_start_seconds':0.0,'clip_end_seconds':CLIP,'expected_audio_git_blob_sha1':TREE[song['audio_url']]['sha'],'expected_audio_bytes':TREE[song['audio_url']]['size'],'expected_annotation_git_blob_sha1':TREE[song['annotations_url']]['sha']})
selection={'schema_version':'jazzsamba-reference-selection-1.0','project_date':'2026-10-12','frozen_before':'Audio acquisition, detector inference and comparison scores','rationale':'One fixed-tempo asynchronous bossa nova development input; two live synchronous swing holdouts with different recorded tempi. Source titles/mixes chosen before detector outputs. This is jazz mixture method validation, not rock repertoire proof.','dataset_doi':'10.5281/zenodo.22943963','dataset_version':'1.0.0','publisher_demo_commit':COMMIT,'catalog':catmeta,'clip_policy':'First 60.000 seconds; no onset selection, silence trimming, estimated offset or endpoint scaling','asset_scope':'Official publisher preferred full-mixture web encoding and paired publisher expanded annotations; no third-party mirror','licence_status':'Publisher consented/public-release research source; exact dataset LICENCE in Zenodo catalogue ZIP unavailable in bounded request; do not infer audio licence from MIT Python package','cases':selected}
put(ASSETS/'selection.json',selection)
put(OUT/'selection.json',selection)
manifest={'pilot_version':'1.0','selection':'Pre-inference frozen first 60s publisher-paired jazz mixes: one development/two holdout','cases':[]}
audio_only={'pilot_version':'1.0','status':'audio-only-inference-ready','cases':[]}
barrefs={'schema_version':'jazzsamba-bar-references-1.0','scope':'Actual supplied bar times only; no quarter-note timestamps synthesized; written chart aligned to musician-authored bar grid','cases':[]}
for picked in selected:
 case_id=picked['id']; song=picked['song']; casedir=OUT/'cases'/case_id; casedir.mkdir(parents=True)
 annb,annmeta=fetch(song['annotations_url'],MAX_METADATA); ann=json.loads(annb)
 (ASSETS/(str(song['song_id'])+'-annotations.json')).write_bytes(annb)
 mp3b,mp3meta=fetch(song['audio_url'],MAX_AUDIO); mp3path=ASSETS/(str(song['song_id'])+'-preferred-mixture.mp3');mp3path.write_bytes(mp3b)
 audio=casedir/'audio.wav'
 subprocess.run(['/opt/homebrew/bin/ffmpeg','-nostdin','-v','error','-i',str(mp3path),'-t','60.000','-ac','1','-ar','22050','-c:a','pcm_s16le',str(audio)],check=True)
 with wave.open(str(audio)) as w:
  frames=w.getnframes();sr=w.getframerate();duration=frames/sr
  if w.getnchannels()!=1 or w.getsampwidth()!=2 or sr!=22050 or frames!=1_323_000: raise ValueError('Unexpected prepared format/length')
 audio_sha=sha(audio.read_bytes())
 rec={'id':case_id,'title':song['title']+' / JazzSAMBA '+song['protocol']+' preferred first60','duration_seconds':duration,'sample_rate_hz':sr,'audio_sha256':audio_sha}
 full=[];core=[]
 for row in ann['chords']:
  start=float(row['start_time']);end=float(row['end_time'])
  if not all(map(math.isfinite,[start,end])) or end<=start: raise ValueError('Invalid chord interval')
  if start>=CLIP or end<=0: continue
  label,corelabel=labels(row)
  base={'start_seconds':max(start,0.0),'end_seconds':min(end,CLIP),'native_label':row['chord'],'source_start_seconds':start,'source_end_seconds':end,'source_fields':row}
  full.append(dict(base,label=label));core.append(dict(base,label=corelabel))
 # Unannotated leading/tail spans stay uncovered, not fabricated N.
 for filename,chords,kind in [('intended.json',full,'supported-rich-Harte'),('core-reference.json',core,'declared-major-minor-triad-projection')]:
  reference={'schema_version':'1.0','recording':rec,'analysis':{'id':'jazzsamba-written-chart-reference','algorithm':'dataset-reference','version':'1.0.0','runtime_seconds':0,'parameters':{'reference_kind':'Written chart time-aligned by musicians; not note-level performed chord truth','boundaries':'Bar/fraction derived chart boundaries; not separately marked physical harmonic attacks','label_mapping':kind,'unknown_conversion':'Unsupported richer/slash/suspended/altered fields use X, original fields retained'}},'chords':chords}
  put(casedir/filename,reference)
 # Only supplied bar boundaries. Do not invent physical quarter-note timestamps.
 bars=[]
 for row in ann['bars']:
  start=float(row['start_time']);end=float(row['end_time'])
  if not all(map(math.isfinite,[start,end])) or end<=start: raise ValueError('Invalid bar interval')
  if start>=CLIP or end<=0:continue
  bars.append({'bar':row['bar'],'measure':row['measure'],'start_seconds':start,'end_seconds':end,'clipped_start_seconds':max(start,0),'clipped_end_seconds':min(end,CLIP)})
 source={'dataset_doi':'10.5281/zenodo.22943963','dataset_version':'1.0.0','publisher_demo_commit':COMMIT,'official_demo_mp3':mp3meta,'official_annotation':annmeta,'prepared_audio_sha256':audio_sha,'prepared_duration_seconds':duration,'preparation':'FFmpeg MP3 decoder honors codec delay/padding metadata; mono 22050Hz PCM16 first 60.000s from zero; no arbitrary offset, trim, gain or endpoint scaling','mp3_scope':'Publisher 24kHz stereo/192kbps web export, not original 48kHz FLAC archive','source_metadata':song,'split':picked['split'],'selection_sha256':sha((OUT/'selection.json').read_bytes()),'source_annotation_sha256':sha(annb)}
 put(casedir/'source.json',source)
 case={'id':case_id,'original_id':song['song_subdir_basename'],'audio':'cases/'+case_id+'/audio.wav','reference':'cases/'+case_id+'/intended.json','core_reference':'cases/'+case_id+'/core-reference.json','intended_reference_sha256':sha((casedir/'intended.json').read_bytes()),'split':picked['split'],'source':source}
 manifest['cases'].append(case)
 audio_only['cases'].append({'id':case_id,'audio':case['audio'],'name':rec['title'],'source':{'prepared_audio_sha256':audio_sha,'prepared_duration_seconds':duration,'sample_rate_hz':sr}})
 barrefs['cases'].append({'id':case_id,'split':picked['split'],'recording':rec,'bars':bars,'sections':[r for r in ann['sections'] if float(r['start_time'])<CLIP and float(r['end_time'])>0],'source':source})
 print('Prepared',case_id,'chords',len(full),'bars',len(bars),'frames',frames,flush=True)
put(OUT/'manifest.json',manifest)
put(OUT/'audio-only-inference-manifest.json',audio_only)
put(OUT/'bar-references.json',barrefs)
print('Complete',len(manifest['cases']),'cases',flush=True)
