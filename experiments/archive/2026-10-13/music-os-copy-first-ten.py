from pathlib import Path
import hashlib,shutil
src=Path('/private/tmp/music-os-plan-20261010/experiments/generated')
dst=Path('/Users/davidcrompton/Documents/music-os/experiments/generated')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
count=size=0
for name in ['first-ten-version-inspection-v1','repertoire-first-ten-v1','repertoire-first-ten-v2','automatic-first-ten-v1']:
 source=src/name; target=dst/name
 for p in [source,*source.rglob('*')]:
  if p.is_symlink(): raise ValueError('Source symlink is unsupported')
  if p.is_dir(): continue
  q=target/p.relative_to(source)
  for ancestor in [q,*q.parents]:
   if ancestor.is_symlink(): raise ValueError('Target symlink is unsupported')
   if ancestor==dst: break
  if q.exists():
   if not q.is_file() or sha(p)!=sha(q): raise ValueError('Refusing to replace different target data')
  else:
   q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
  assert sha(p)==sha(q)
  count+=1;size+=q.stat().st_size
 print(name,'verified')
print('Files:',count,'bytes:',size)
