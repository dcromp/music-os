import json,hashlib,re,struct,time,urllib.request,urllib.error,wave,zlib,zipfile,subprocess
from pathlib import Path
root=Path('/private/tmp/music-os-plan-20261010');selection_path=root/'experiments/fixtures/rhythm-reference-selection.json';selection=json.loads(selection_path.read_text());selection_sha=hashlib.sha256(selection_path.read_bytes()).hexdigest()
assets=root/'experiments/candidate-assets/guitarset-rhythm-20261012';output=root/'experiments/generated/guitarset-rhythm-reference-v1';output.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((root/'experiments/candidate-assets/guitarset/record-3371780.json').read_text());file=next(f for f in record['files'] if f['key']=='audio_mono-mic.zip');url=file['links']['self']
assert url.startswith('https://zenodo.org/')
annotation_zip=root/'experiments/candidate-assets/guitarset/annotation.zip';assert sha(annotation_zip)=='8daa02e6417ccca1685feb44b135e95928ad7037e5032ecb326b5791856fda99'
def get_range(start,end):
 for attempt in range(3):
  req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}','User-Agent':'music-os-reference-validation/0.1'})
  try:
   with urllib.request.urlopen(req,timeout=45) as resp:
    if resp.status!=206 or not resp.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):raise ValueError('Expected exact ZIP byte range')
    data=resp.read(end-start+2)
    if len(data)!=end-start+1:raise ValueError('Wrong byte-range size')
    return data
  except urllib.error.HTTPError as e:
   if e.code!=429 or attempt==2:raise
   pause=min(45,20*(attempt+1));print('Rate limit; bounded retry in',pause,'seconds',flush=True);time.sleep(pause)
with zipfile.ZipFile(annotation_zip) as z:
 cases=[];refs=[];provenance=[]
 for i,row in enumerate(selection['cases']):
  name=row['original_id'];entry=row['zip_entry'];target=assets/'audio'/(name+'_mic.wav');target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():
   start=entry['local_offset'];end=min(file['size']-1,start+30+4096+entry['compressed_size']-1);blob=get_range(start,end);h=struct.unpack_from('<4s5H3I2H',blob)
   if h[0]!=b'PK\x03\x04':raise ValueError('Invalid local ZIP header')
   n,ex=h[-2:];assert blob[30:30+n].decode()==entry['name'];comp=blob[30+n+ex:30+n+ex+entry['compressed_size']];raw=zlib.decompress(comp,-15) if entry['method']==8 else comp
   if len(raw)!=entry['size'] or zlib.crc32(raw)!=entry['crc']:raise ValueError('Entry CRC/size mismatch')
   with target.open('xb') as f:f.write(raw)
   time.sleep(2)
  if target.is_symlink() or len(target.read_bytes())!=entry['size'] or zlib.crc32(target.read_bytes())!=entry['crc']:raise ValueError('Cached ZIP entry mismatch')
  jams_raw=z.read(name+'.jams');assert hashlib.sha256(jams_raw).hexdigest()==row['source_jams_sha256'];jams=json.loads(jams_raw)
  folder=output/'cases'/row['id'];folder.mkdir(parents=True,exist_ok=True);audio=folder/'audio.wav'
  if not audio.exists():subprocess.run(['/opt/homebrew/bin/ffmpeg','-nostdin','-v','error','-n','-i',str(target),'-ac','1','-ar','22050','-c:a','pcm_s16le',str(audio)],check=True)
  with wave.open(str(audio)) as w:
   assert (w.getnchannels(),w.getframerate(),w.getsampwidth())==(1,22050,2);duration=w.getnframes()/22050
  if abs(duration-jams['file_metadata']['duration'])>1/22050:raise ValueError('Source/audio time origins differ')
  recording={'id':row['id'],'title':name+' / microphone performance','audio_sha256':sha(audio),'duration_seconds':duration,'sample_rate_hz':22050}
  beat_ann=next(a for a in jams['annotations'] if a['namespace']=='beat_position');obs=[x for x in beat_ann['data'] if 0<=x['time']<duration];assert all(x['value']['beat_units']==4 and x['value']['num_beats']==4 for x in obs)
  beat_times=[x['time'] for x in obs];bars=[x['time'] for x in obs if x['value']['position']==1];windows=[]
  for k in range(len(obs)):
   if obs[k]['value']['position'] in (1,3) and k+2<len(obs):windows.append({'start_seconds':obs[k]['time'],'end_seconds':obs[k+2]['time'],'expected_beats':2,'expected_bars':0.5,'type':'half_bar'})
   if obs[k]['value']['position']==1:
    for step,kind in [(4,'one_bar'),(8,'two_bars')]:
     if k+step<len(obs):windows.append({'start_seconds':obs[k]['time'],'end_seconds':obs[k+step]['time'],'expected_beats':step,'expected_bars':step/4,'type':kind})
  source={'original_id':name,'source_url':url,'source_archive_declared_md5':file['checksum'],'full_audio_archive_verified':False,'entry_crc32':entry['crc'],'entry_size_bytes':entry['size'],'source_audio_sha256':sha(target),'source_jams_sha256':row['source_jams_sha256'],'annotation_archive_sha256':sha(annotation_zip),'prepared_audio_sha256':sha(audio),'time_origin_seconds':0,'preparation':'FFmpeg mono22050Hz PCM16, notrim/padding/offset','dataset_doi':'10.5281/zenodo.3371780','dataset_version':'1.1.0','selection_sha256':selection_sha}
  (folder/'source.json').write_text(json.dumps(source,indent=2)+'\n')
  ref={'recording':recording,'split':row['split'],'beat_reference_semantics':'GuitarSet nominal metronome/lead-sheet beat-position grid; not manually marked physical played attacks or predicted downbeats','beat_times_seconds':beat_times,'barlines_seconds':bars,'count_windows':sorted(windows,key=lambda x:(x['start_seconds'],x['end_seconds'])),'source':source}
  refs.append(ref);cases.append({'id':row['id'],'name':recording['title'],'recording':recording,'audio_url':'/cases/'+row['id']+'/audio.wav'})
  provenance.append(source);print(i+1,len(selection['cases']),name,round(duration,2),'seconds',flush=True)
manifest={'schema_version':'automatic-drafts-1.0','pack_id':output.name,'status':'Isolated reference-validation inputs, not aplaybackpack','cases':cases,'selection_sha256':selection_sha}
reference={'schema_version':'rhythm-references-1.0','selection_sha256':selection_sha,'scope':'New isolated-guitar recordings with nominal beat/bar grid; projectsplit frozenbeforepulse inference; notfull-mixfirst-ten validation','cases':refs}
(output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(output/'references.json').write_text(json.dumps(reference,indent=2)+'\n');(assets/'provenance.json').write_text(json.dumps({'selection_sha256':selection_sha,'files':provenance},indent=2)+'\n')
for condition in selection['conditions']:
 config={'schema_version':'playalong-rhythm-config-1.0','recordings':{}}
 for row in selection['cases']:
  hint=condition['id']=='nominal-tempo-guided';bpm=row['nominal_bpm'] if hint else 120
  cfg={'start_bpm':bpm,'beats_per_bar':4,'meter_label':'4/4 reference hypothesis','meter_status':'Nominal source-meter hypothesis; performed beats not verified','pulse_prior_status':condition['input_guidance']}
  if hint:cfg.update(tempo_min_bpm=bpm*0.85,tempo_max_bpm=bpm*1.15)
  config['recordings'][row['id']]=cfg
 (output/(condition['id']+'-config.json')).write_text(json.dumps(config,indent=2)+'\n')
print('Complete reference packet:',output,flush=True)
