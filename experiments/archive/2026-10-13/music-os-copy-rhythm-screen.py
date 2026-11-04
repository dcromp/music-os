from pathlib import Path
import hashlib,shutil
source=Path('/private/tmp/music-os-plan-20261010/experiments/generated/rhythm-screen-v1')
target=Path('/Users/davidcrompton/Documents/music-os/experiments/generated/rhythm-screen-v1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
count=0
for p in source.rglob('*'):
 if p.is_symlink():raise ValueError('Source symlinks unsupported')
 if p.is_dir():continue
 q=target/p.relative_to(source)
 if any(a.is_symlink() for a in [q,*q.parents]):raise ValueError('Target symlinks unsupported')
 if q.exists() and (not q.is_file() or sha(q)!=sha(p)):raise ValueError('Existing cache differs')
 q.parent.mkdir(parents=True,exist_ok=True)
 if not q.exists():shutil.copyfile(p,q)
 assert sha(q)==sha(p)
 count+=1
print('Verified procedural rhythm cache files:',count)
