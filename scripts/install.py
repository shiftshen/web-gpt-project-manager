#!/usr/bin/env python3
"""Install this standalone skill; explicit replacement keeps the previous installation."""
import argparse,datetime,shutil,sys
from pathlib import Path

def install(dest,replace=False):
    source=Path(__file__).resolve().parent.parent
    dest=Path(dest).expanduser().absolute()
    if dest.resolve()==source: raise ValueError('Source and installation are identical')
    if source in dest.resolve().parents: raise ValueError('Do not install inside source')
    backup=None
    if dest.exists() or dest.is_symlink():
        if not replace:raise ValueError('Destination exists; use --replace to preserve it as a backup')
        backup=dest.with_name(dest.name+'.backup-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f'))
        dest.rename(backup)
    try:
        shutil.copytree(source,dest,ignore=shutil.ignore_patterns('.git','.github','__pycache__','*.pyc','.gpt-pm','.DS_Store','dist'))
    except Exception:
        if dest.exists():shutil.rmtree(dest)
        if backup:backup.rename(dest)
        raise
    return dest,backup
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dest',default=str(Path.home()/'.codex/skills/web-gpt-project-manager'));p.add_argument('--replace',action='store_true');a=p.parse_args()
    try:
        dest,backup=install(a.dest,a.replace);print('Installed:',dest);print('Backup:',backup or 'none')
    except (ValueError,OSError) as e:print(str(e),file=sys.stderr);sys.exit(2)
