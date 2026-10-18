import re
from pathlib import Path
from somoy_jatri.utils import load, save, digest


def disposable(name):
    return name in {'mix.wav','music.wav','ambient.wav','narration.wav','video.mp4','thumbnail.jpg'} or bool(
        re.fullmatch(r'(?:images/shot_\d+\.png|clips/shot_\d+\.mp4|utterances/\d+\.wav)', name))


def checkpoint(root):
    # Never archive .env, OAuth files, session URLs, or arbitrary files.
    names={'research.json','story.json','narration.json','timeline.json','music-plan.json',
           'semantic-review.json','config.json','qc.json','metadata.json','captions.srt',
           'captions.ass','thumbnail.jpg','narration.wav','mix.wav','video.mp4','upload.json'}
    files=[]
    for p in root.rglob('*'):
        name=p.relative_to(root).as_posix()
        if p.is_file() and (name in names or disposable(name) or
              re.fullmatch(r'(?:images/shot_\d+|utterances/\d+)\.json',name)):
            if p.is_symlink(): raise ValueError('Checkpoint symlink forbidden')
            files.append({'name':name,'sha256':digest(p)})
    save(root/'checkpoint.json',{'project':'somoy-jatri','run':root.name,'files':files})
    return files


def backup(root,store,snapshot="checkpoint"):
    if not re.fullmatch(r"[a-z0-9-]+",snapshot):raise ValueError("Unsafe snapshot")
    entries=checkpoint(root)
    for entry in entries: store.upload(root/entry['name'],f"runs/{root.name}/{entry['name']}")
    store.upload(root/'checkpoint.json',f'runs/{root.name}/{snapshot}.json')


def restore(root,store,snapshot="checkpoint"):
    if not re.fullmatch(r"[a-z0-9-]+",snapshot):raise ValueError("Unsafe snapshot")
    manifest=store.load(f'runs/{root.name}/{snapshot}.json',None)
    if not manifest or manifest.get('project')!='somoy-jatri' or manifest.get('run')!=root.name:
        raise ValueError('Missing or foreign checkpoint')
    root.mkdir(parents=True,exist_ok=True)
    for entry in manifest['files']:
        name=entry['name'];target=(root/name).resolve()
        if not target.is_relative_to(root.resolve()) or Path(name).is_absolute():
            raise ValueError('Unsafe checkpoint path')
        if target.exists() and digest(target)==entry['sha256']:continue
        target.parent.mkdir(parents=True,exist_ok=True)
        fid=store.find(f'runs/{root.name}/{name}')
        if not fid:raise ValueError('Missing remote asset')
        store.download(fid,target)
        if digest(target)!=entry['sha256']:raise ValueError('Recovery checksum mismatch')
    save(root/'checkpoint.json',manifest)


def cleanup(root,store=None):
    qc=load(root/'qc.json')
    if qc.get('passed') is not True:raise ValueError('Validated video required')
    if (root/'upload.json').exists():
        state=load(root/'upload.json')
        if state.get('phase')!='verified':raise ValueError('Verify upload processing before cleanup')
    manifest=load(root/'checkpoint.json')
    if manifest.get('project')!='somoy-jatri' or manifest.get('run')!=root.name:
        raise ValueError('Foreign cleanup manifest')
    deleted=[]
    for entry in manifest['files']:
        name=entry['name'];target=root/name
        if not disposable(name):continue
        if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
            raise ValueError('Unsafe cleanup target')
        if store:
            key=f'runs/{root.name}/{name}'
            fid=store.find(key)
            if fid:
                meta=store.client.files().get(fileId=fid,fields='parents,appProperties').execute()
                import hashlib
                if store.folder not in meta.get('parents',[]) or meta.get('appProperties',{}).get('workflow_key')!=hashlib.sha256(key.encode()).hexdigest():
                    raise ValueError('Remote cleanup identity mismatch')
                # Reversible trash rather than permanent deletion.
                store.client.files().update(fileId=fid,body={'trashed':True}).execute()
        if target.exists():
            if digest(target)!=entry['sha256']:raise ValueError('Cleanup checksum mismatch')
            target.unlink()
        deleted.append(name)
    save(root/'cleanup.json',{'deleted':deleted,'project':'somoy-jatri'})
