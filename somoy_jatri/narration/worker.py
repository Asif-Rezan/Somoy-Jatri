"""Independent CPU speech shards with checksum-bound verification receipts."""
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from somoy_jatri.config import Config
from somoy_jatri.utils import load, save
from somoy_jatri.narration.text import normalize, validate_segment
from somoy_jatri.narration.providers import (
    provider, synthesize_measured, take_fingerprint, measured_take, save_measured_take)


def partial_checkpoint(root, image_workers):
    config = Config(**load(root/'config.json'))
    if config.mode!='production' or config.run_id!=root.name:
        raise ValueError('Matching production checkpoint required')
    if not 1<=image_workers<=16: raise ValueError('Use 1–16 image workers')
    story = load(root/'story.json')
    dossier=load(root/'research.json')
    if dossier.get('research_method')=='automatic source extraction' and len(dossier['facts'])<8 and not (root/'story.json').exists():
        from somoy_jatri.research.automatic import enrich
        dossier=enrich(dossier);save(root/'research.json',dossier)
    facts=dossier['facts']
    if not story.get('segments'): raise ValueError('Saved story required')
    for segment in story['segments']:
        segment['text'] = normalize(segment['text'])
        validate_segment(segment)
        if any(not isinstance(i,int) or not 0<=i<len(facts) for i in segment.get('fact_ids',[])):
            raise ValueError('Invalid saved fact citation')
    save(root/'story.json',story)
    import wave
    cached_count=0;cached_seconds=0.0
    for i,segment in enumerate(story['segments']):
        path=root/'utterances'/f'{i:04}.wav';stamp=path.with_suffix('.json')
        if path.exists() and stamp.exists() and load(stamp).get('fingerprint')==take_fingerprint(segment,'production'):
            with wave.open(str(path),'rb') as wav:
                cached_seconds+=wav.getnframes()/wav.getframerate()
            cached_count+=1
    print(json.dumps({'voice_stage':'checkpoint_summary','planned_takes':len(story['segments']),
                      'saved_takes':cached_count,'saved_audio_seconds':round(cached_seconds,2)}),flush=True)
    from somoy_jatri.storyboard.timeline import reviewed_story
    reviewed_story(story,load(root/'research.json'),root/'semantic-review.json')
    config.workers=image_workers
    save(root/'config.json',asdict(config))


def generate_shard(root, shard, count, target):
    config = Config(**load(root/'config.json'))
    if config.mode!='production' or config.run_id!=root.name:
        raise ValueError('Matching production checkpoint required')
    if not 1<=count<=16 or not 0<=shard<count: raise ValueError('Invalid voice shard')
    tts=None;recognizer=None
    (root/'utterances').mkdir(exist_ok=True)
    (target/'utterances').mkdir(parents=True,exist_ok=True)
    for i,segment in enumerate(load(root/'story.json')['segments']):
        if i%count!=shard: continue
        path=root/'utterances'/f'{i:04}.wav'
        fingerprint=take_fingerprint(segment,config.mode)
        asr=measured_take(path,fingerprint)
        if asr is None:
            stamp=path.with_suffix('.json')
            reuse=path.exists() and stamp.exists() and load(stamp).get('fingerprint')==fingerprint
            tts=tts or provider(config.mode)
            asr=synthesize_measured(tts,segment,path,reuse=reuse)
            save_measured_take(path,fingerprint,asr)
        # Only this shard's files are published; merging cannot overwrite other workers' takes.
        shutil.copy2(path,target/'utterances'/path.name)
        shutil.copy2(path.with_suffix('.json'),target/'utterances'/path.with_suffix('.json').name)
        print(json.dumps({'voice_stage':'shard_verified','index':i,'shard':shard}),flush=True)


if __name__=='__main__':
    run=os.environ['RUN']
    Config(mode='production',run_id=run)
    root=Path('output')/run
    if os.getenv('VOICE_OPERATION')=='checkpoint':
        count=int(os.environ['VOICE_WORKERS'])
        if not 1<=count<=16: raise ValueError('Use 1–16 voice workers')
        partial_checkpoint(root,int(os.environ['IMAGE_WORKERS']))
        with open(os.environ['GITHUB_OUTPUT'],'a') as out:
            out.write('matrix='+json.dumps({'shard':list(range(count))})+'\n')
    else:
        shard=int(os.environ['SHARD'])
        generate_shard(root,shard,int(os.environ['VOICE_WORKERS']),Path('output')/f'voice-shard-{shard}')
