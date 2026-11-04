from pathlib import Path
import hashlib,json,os,shutil,time
src=Path('/private/tmp/music-os-plan-20261010')
dst=Path('/Users/davidcrompton/Documents/music-os')
base=Path('/private/tmp/music-os-python/cpython-3.11.13-macos-aarch64-none')
newbase=dst/'.runtime/cpython-3.11.13-macos-aarch64-none'
roots=['experiments/candidate-assets','experiments/generated','experiments/local-audio','experiments/results','node_modules','.expo','.venv-beatthis','.venv-btc','.venv-chordmini','.venv-crema','.venv-demucs']
notes=dst/'experiments/local-research-notes/2026-10-13'
notes.mkdir(parents=True,exist_ok=True)
backup=dst/'.migration-backup/2026-10-13'
started=time.perf_counter();entries=[];conflicts=[];relocated=[]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(1048576):h.update(chunk)
 return h.hexdigest()
def copy_tree(source,target):
 for p in sorted(source.rglob('*')):
  rel=p.relative_to(source)
  if '__pycache__' in rel.parts or p.suffix=='.pyc':continue
  q=target/rel
  if p.is_symlink():
   link=os.readlink(p)
   mapped=link.replace(str(base),str(newbase)).replace(str(src),str(dst))
   q.parent.mkdir(parents=True,exist_ok=True)
   if q.is_symlink():
    if os.readlink(q)!=mapped:raise RuntimeError('Different existing symlink: '+str(q))
   elif q.exists():raise RuntimeError('Non-symlink destination: '+str(q))
   else:q.symlink_to(mapped)
   entries.append({'path':str(q.relative_to(dst)),'symlink':mapped})
  elif p.is_dir():q.mkdir(parents=True,exist_ok=True)
  elif p.is_file():
   expected=sha(p)
   if q.exists() and sha(q)!=expected:
    if str(q.relative_to(dst)) not in {'experiments/generated/metrics.json','experiments/generated/baseline.json','experiments/generated/guitarset-pilot/report.json'}:
     raise RuntimeError('Unexpected different destination: '+str(q))
    saved=backup/q.relative_to(dst);saved.parent.mkdir(parents=True,exist_ok=True)
    if saved.exists():raise RuntimeError('Preserve existing conflict backup')
    shutil.copy2(q,saved);conflicts.append({'path':str(q.relative_to(dst)),'preserved_destination':str(saved.relative_to(dst)),'previous_sha256':sha(saved)})
   q.parent.mkdir(parents=True,exist_ok=True)
   if not q.exists() or sha(q)!=expected:shutil.copy2(p,q)
   if sha(q)!=expected:raise RuntimeError('Copied file verification failed: '+str(q))
   entries.append({'path':str(q.relative_to(dst)),'sha256':expected,'bytes':p.stat().st_size})
copy_tree(base,newbase)
for relative in roots:
 if (src/relative).exists():copy_tree(src/relative,dst/relative)
for env in sorted(dst.glob('.venv-*')):
 for p in [env/'pyvenv.cfg',*sorted((env/'bin').glob('*'))]:
  if p.is_symlink() or not p.is_file():continue
  try:text=p.read_text()
  except (UnicodeError,OSError):continue
  changed=text.replace(str(base),str(newbase)).replace(str(src),str(dst))
  if changed!=text:
   before=sha(p);p.write_text(changed);relocated.append({'path':str(p.relative_to(dst)),'before_sha256':before,'after_sha256':sha(p)})
for p in sorted(Path('/private/tmp').glob('music-os-*')):
 if p.is_file() and p.suffix in ('.py','.json','.md','.sh'):
  q=notes/p.name
  if not q.exists():shutil.copy2(p,q)
  elif sha(q)!=sha(p):raise RuntimeError('Different archived helper/note: '+str(q))
report={'date':'2026-10-13','source':str(src),'canonical_workspace':str(dst),'verified_entries':len(entries),'verified_bytes':sum(e.get('bytes',0) for e in entries),'seconds':time.perf_counter()-started,'preserved_destination_variants':conflicts,'relocated_runtime_text':relocated,'entries':entries,'disposable_bytecode_caches_copied':False,'existing_durable_analysis_youtube_and_pilot_environments_preserved':True}
(notes/'migration-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('entries','relocated_runtime_text')},indent=2))
print('Repaired runtime text files:',len(relocated))
