import json,re,hashlib,wave,zipfile
from pathlib import Path
root=Path('/private/tmp/music-os-plan-20261010');src=root/'experiments/generated/guitarset-pilot';out=root/'experiments/generated/guitarset-rhythm-cached-v1'
if out.exists():raise ValueError('Choose fresh output')
out.mkdir();manifest=json.loads((src/'manifest.json').read_text());cases=[];refs=[];settings={}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for row in manifest['cases']:
 source=row['source'];folder=src/Path(row['audio']).parent;audio=src/row['audio'];recording=json.loads((folder/'intended.json').read_text())['recording'];assert sha(audio)==recording['audio_sha256']==source['prepared_audio_sha256']
 jams_path=root/source['source_jams'];assert sha(jams_path)==source['source_jams_sha256'];jams=json.loads(jams_path.read_text());ann=next(a for a in jams['annotations'] if a['namespace']=='beat_position');obs=[x for x in ann['data'] if 0<=x['time']<recording['duration_seconds']];assert all(x['value']['num_beats']==4 and x['value']['beat_units']==4 for x in obs)
 times=[x['time'] for x in obs];windows=[]
 for i in range(len(obs)):
  if obs[i]['value']['position'] in (1,3) and i+2<len(obs):windows.append({'start_seconds':obs[i]['time'],'end_seconds':obs[i+2]['time'],'expected_beats':2,'expected_bars':0.5,'type':'half_bar'})
  if obs[i]['value']['position']==1:
   for n,kind in [(4,'one_bar'),(8,'two_bars')]:
    if i+n<len(obs):windows.append({'start_seconds':obs[i]['time'],'end_seconds':obs[i+n]['time'],'expected_beats':n,'expected_bars':n/4,'type':kind})
 refs.append({'recording':recording,'split':'development','beat_times_seconds':times,'barlines_seconds':[x['time'] for x in obs if x['value']['position']==1],'count_windows':sorted(windows,key=lambda x:(x['start_seconds'],x['end_seconds'])),'beat_reference_semantics':'Nominal GuitarSet metronome/lead-sheet grid; retrospective prior six, not physical played attacks or fresh holdout','source':source})
 cases.append({'id':recording['id'],'recording':recording,'audio_url':'/cases/'+recording['id']+'/audio.wav'})
 bpm=float(re.search(r'-(\d+)-',row['original_id']).group(1));settings[recording['id']]=bpm
(out/'references.json').write_text(json.dumps({'schema_version':'rhythm-references-1.0','scope':'Retrospective nominal-grid check on saved six acoustic performances; no new holdout result','cases':refs},indent=2)+'\n')
# Prediction inputs remain at their original pilot location; rhythm_grid reads exact fixed-case WAVs there.
input_manifest=src/'rhythm-inputs.json'
if input_manifest.exists():raise ValueError('Existing rhythm input manifest')
input_manifest.write_text(json.dumps({'schema_version':'automatic-drafts-1.0','pack_id':'guitarset-pilot-rhythm-validation','cases':cases},indent=2)+'\n')
for condition in ('default-120','nominal-tempo-guided'):
 config={'schema_version':'playalong-rhythm-config-1.0','recordings':{}}
 for id,bpm in settings.items():
  guide=condition=='nominal-tempo-guided';cfg={'start_bpm':bpm if guide else 120,'beats_per_bar':4,'meter_label':'4/4 source hypothesis','meter_status':'Nominal metronome grid; physical timing not verified','pulse_prior_status':'Filename nominal tempo only' if guide else 'No reference tempo/time/positions supplied'}
  if guide:cfg.update(tempo_min_bpm=bpm*0.85,tempo_max_bpm=bpm*1.15)
  config['recordings'][id]=cfg
 (out/(condition+'-config.json')).write_text(json.dumps(config,indent=2)+'\n')
(out/'selection.json').write_text(json.dumps({'scope':'Retrospective development', 'conditions':['default-120','nominal-tempo-guided'],'nominal_hint_range_ratio':[0.85,1.15],'timestamps_withheld_from_inference':True,'source_pilot_manifest_sha256':sha(src/'manifest.json'),'recording_ids':[c['id'] for c in cases]},indent=2)+'\n')
print('Prepared six paired references with',sum(len(r['count_windows']) for r in refs),'count windows; no existing chart or media bytes changed.')
