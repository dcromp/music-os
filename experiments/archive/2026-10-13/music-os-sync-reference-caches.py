from pathlib import Path
import hashlib, shutil, subprocess
source=Path('/private/tmp/music-os-plan-20261010')
target=Path('/Users/davidcrompton/Documents/music-os')
relative_dirs=[
'experiments/generated/bar-chart-alignment-v1',
'experiments/generated/bar-chart-alignment-v1-preparation-failed',
'experiments/generated/bar-chart-alignment-v1-preparation-failed-2',
'experiments/generated/guitarset-rhythm-reference-v1',
'experiments/generated/guitarset-chord-validation-v1',
'experiments/generated/mixed-rhythm-reference-v1',
'experiments/generated/jazzsamba-reference-v1',
'experiments/generated/beat-candidate-fresh-v1',
'experiments/generated/jazzsamba-alignment-v1',
'experiments/candidate-assets/guitarset-rhythm-20261012',
'experiments/candidate-assets/mixed-rhythm-20261012',
'experiments/candidate-assets/jazzsamba-20261012',
'experiments/candidate-assets/beat-this-1.1.0']
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(1<<20): h.update(chunk)
 return h.hexdigest()
count=0
size=0
for rel in relative_dirs:
 check=subprocess.run(['git','check-ignore','-q',rel+'/sync-check.json'],cwd=target)
 if check.returncode!=0: raise RuntimeError('Destination not ignored: '+rel)
 for src in sorted((source/rel).rglob('*')):
  if src.is_symlink(): raise RuntimeError('Unexpected symlink: '+str(src))
  if not src.is_file(): continue
  dst=target/src.relative_to(source)
  if dst.exists():
   if not dst.is_file() or digest(src)!=digest(dst): raise RuntimeError('Refuse different existing cache: '+str(dst))
  else:
   dst.parent.mkdir(parents=True,exist_ok=True)
   with src.open('rb') as f, dst.open('xb') as o: shutil.copyfileobj(f,o)
   if digest(src)!=digest(dst): raise RuntimeError('Copied cache hash mismatch: '+str(dst))
  count+=1
  size+=src.stat().st_size
print(f'Verified {count} cache files ({size/1e6:.1f} MB) in the Mac checkout.')
