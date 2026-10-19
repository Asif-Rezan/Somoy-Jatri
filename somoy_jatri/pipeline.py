import os
from pathlib import Path
from somoy_jatri.utils import save,load,duration
from somoy_jatri.narration.text import normalize,validate_segment
from somoy_jatri.narration.providers import provider
from somoy_jatri.audio import concatenate,read_wav
from somoy_jatri.storyboard.timeline import build,evaluate_semantics,reviewed_story


def mock_story():
    segments=[]
    for text,subject,visual,scene,mood,motion in [
        ('বন্ধুরা, আমি এখন কোথায় এসে পড়লাম!','ancient market','A wide ancient marketplace with pottery stalls','market','amazed','slow_forward'),
        ('সামনে একজন মানুষ মাটির পাত্র সাজিয়ে রাখছেন।','pottery merchant','Close view of a merchant arranging clay pottery','market','curious','stable'),
        ('নদীর দিকে তাকিয়ে ভাবছি, সময় কত কিছু বদলে দেয়।','river boats','Wooden boats on a calm river at sunset','river','reflective','pan_right')]:
        segments.append(dict(text=text,subject=subject,visual=visual,scene=scene,mood=mood,motion=motion,
            chapter=scene,emotion=mood,intensity=.5,pause_after_ms=300,anchors=subject.split(),ambient='river' if scene=='river' else 'wind',fact_ids=[]))
    return {'title':'সময়ের পথে একটি পরীক্ষা | Somoy Jatri','tags':['Bangla history','Time travel vlog'],'segments':segments}


def prepare(config,topic='',period=''):
    import json
    from dataclasses import asdict
    root=config.root;root.mkdir(parents=True,exist_ok=True)
    config.preflight()
    if (root/'config.json').exists():
        if load(root/'config.json')!=asdict(config):raise ValueError('Run configuration changed; use a new run ID')
    save(root/'config.json',asdict(config))
    if config.mode=='mock':
        dossier={k:'MOCK FIXTURE ONLY' for k in ['politics','culture','tools','transportation','food','trades','social_life','events']}
        dossier.update(location='unverified test environment',period='fictional fixture',buildings='mudbrick stalls along a river',
            clothing='linen clothing',facts=[],uncertain=['All visuals are test fixtures'],sources=[])
    else:
        from somoy_jatri.research.dossier import validate
        source_name=os.environ['RESEARCH_DOSSIER']
        source=Path(source_name)
        if (root/'research.json').exists():
            dossier=load(root/'research.json')
            dossier=validate(dossier,live=True,require_review=dossier.get('research_method')!='automatic source extraction')
        elif source_name=='auto':
            from somoy_jatri.research.automatic import build as build_research
            history=root.parent/'topic-history.json'
            dossier=build_research(load(history) if history.exists() else [])
        elif source.is_dir():
            history=root.parent/'topic-history.json'
            used={item['topic'] for item in load(history)} if history.exists() else set()
            candidates=[load(p) for p in sorted(source.glob('*.json'))]
            candidates=[d for d in candidates if d.get('reviewed_by') and
                        d.get('location','')+' '+d.get('period','') not in used]
            if not candidates:raise ValueError('No unused reviewed research dossier available')
            dossier=validate(candidates[0],live=True)
        else:
            dossier=validate(load(source),live=True)
        if period and period!=dossier['period']:raise ValueError('Period input differs from reviewed dossier')
    if config.mode=='production' and dossier.get('research_method')=='automatic source extraction' and len(dossier['facts'])<8 and not (root/'story.json').exists():
        from somoy_jatri.research.automatic import enrich
        dossier=enrich(dossier)
    save(root/'research.json',dossier)
    from somoy_jatri.topics.history import reserve
    history_path=root.parent/'topic-history.json'
    previous=load(history_path) if history_path.exists() else []
    title=topic or dossier['location']+' '+dossier['period']
    if config.mode=='production':
        reserve(history_path,title,config.run_id,dossier.get('topic_id'))
        print(json.dumps({'prepare_stage':'topic_reserved','topic_id':dossier.get('topic_id')}),flush=True)
    from somoy_jatri.scripts.groq import generate
    story=load(root/'story.json') if (root/'story.json').exists() else (
        mock_story() if config.mode=='mock' else generate(dossier,config.target,previous))
    if config.mode=='production':
        print(json.dumps({'prepare_stage':'story_received','segments':len(story.get('segments',[]))}),flush=True)
    tts=None;aligner=None
    for revision in range(3):
        if not story.get('title') or not story.get('segments'):raise ValueError('Empty story')
        for i,s in enumerate(story['segments']):
            s['text']=normalize(s['text'])
            try:
                validate_segment(s)
            except ValueError:
                print(json.dumps({'prepare_stage':'segment_invalid','index':i}),flush=True)
                raise
            if any(not isinstance(i,int) or not 0<=i<len(dossier['facts']) for i in s.get('fact_ids',[])):
                raise ValueError('Invalid fact reference')
        if config.mode=='production':
            print(json.dumps({'prepare_stage':'segments_validated','revision':revision}),flush=True)
        save(root/'story.json',story)
        if config.mode=='production':
            reviewed_story(story,dossier,root/'semantic-review.json')
        utterances=root/'utterances';utterances.mkdir(exist_ok=True)
        parts=[];records=[]
        for i,s in enumerate(story['segments']):
            path=utterances/f'{i:04}.wav'
            # Manifest fingerprint prevents using stale speech after script revisions.
            from somoy_jatri.narration.providers import (take_fingerprint,measured_take,
                save_measured_take,synthesize_measured)
            fingerprint=take_fingerprint(s,config.mode)
            stamp=path.with_suffix('.json')
            cached=path.exists() and stamp.exists() and load(stamp).get('fingerprint')==fingerprint
            audio={}
            if config.mode=='production':
                print(json.dumps({'prepare_stage':'voice_start','index':i}),flush=True)
                audio=measured_take(path,fingerprint)
                if audio is None:
                    tts=tts or provider(config.mode)
                    audio=synthesize_measured(tts,s,path,reuse=cached)
                    save_measured_take(path,fingerprint,audio)
                print(json.dumps({'prepare_stage':'audio_checked','index':i}),flush=True)
            elif not cached:
                tts=tts or provider(config.mode)
                tts.synthesize(s['text'],s['emotion'],s['intensity'],path)
            if config.mode=='mock':save(stamp,{'fingerprint':fingerprint})
            parts.append((path,s['pause_after_ms']));records.append({'text':s['text'],'audio':audio})
        bounds=concatenate(parts,root/'narration.wav')
        if config.mode=='production':
            from somoy_jatri.audio import fit_narration
            bounds=fit_narration(root/'narration.wav',bounds)
        total=bounds[-1]['end']
        if config.mode=='mock' or 600<=total<=900:break
        if revision==2:raise ValueError('Narration duration outside 600–900s after duration correction and script revisions')
        story=generate(dossier,config.target,previous,
            f'Measured previous voice duration {total:.1f}s. Adjust total words by ratio {config.target/total:.3f}.')
    for record,b in zip(records,bounds):record.update(b)
    save(root/'narration.json',records)
    shots=build(story,bounds,dossier)
    review={'passed':True,'method':'mock-only, no semantic quality claim'} if config.mode=='mock' else reviewed_story(story,dossier,root/'semantic-review.json')
    save(root/'semantic-review.json',review);save(root/'timeline.json',shots)
    return shots


def finish(config):
    import numpy as np
    from somoy_jatri.music.scoring import plan,score,mix
    from somoy_jatri.ambient_audio.profiles import render as ambient
    from somoy_jatri.subtitles.captions import generate
    from somoy_jatri.renderer.ffmpeg import render
    from somoy_jatri.thumbnail.design import create
    from somoy_jatri.validation.quality import validate_final
    root=config.root;shots=load(root/'timeline.json');total=shots[-1]['end']
    cues=plan(shots);save(root/'music-plan.json',cues)
    catalog=load(os.environ['AMBIENT_CATALOG']) if os.getenv('AMBIENT_CATALOG') else None
    music=score(cues,total) if config.music else np.zeros(round(total*24000))
    mix(root/'narration.wav',music,ambient(shots,total,catalog),root/'mix.wav')
    generate(root,shots)
    create(root,'সময়ের পথে!' if config.mode=='mock' else load(root/'research.json')['location'])
    render(root,shots,captions=config.captions,mock=config.mode=='mock')
    dossier=load(root/'research.json');story=load(root/'story.json')
    chapters=[];last=None
    from somoy_jatri.subtitles.captions import timestamp
    for s in shots:
        if s['chapter']!=last:
            seconds=round(s['start']);chapters.append(f'{seconds//60:02}:{seconds%60:02} {s["chapter"]}');last=s['chapter']
    disclosure='এটি AI দিয়ে তৈরি ঐতিহাসিক পুনর্নির্মাণ। সময়ভ্রমণ ও বর্ণনাকারীর অভিজ্ঞতা কাল্পনিক। কিছু দৃশ্য সম্ভাব্য পুনর্গঠন।'
    description=disclosure+'\n\n'+'\n'.join(chapters)+'\n\nSources:\n'+'\n'.join(s['url'] for s in dossier['sources'])
    description+='\nMusic: original procedural synthesis.\n#SomoyJatri #BanglaHistory #TimeTravel'
    if catalog:
        description+='\nSound credits:\n'+'\n'.join(str(c.get('source',''))+' — '+str(c.get('license','')) for c in catalog.values())
    save(root/'metadata.json',{'title':story['title'][:100],'description':description[:5000],
        'tags':story.get('tags',['Bangla history']),'categoryId':'27','defaultLanguage':'bn', 'defaultAudioLanguage':'bn'})
    qc=validate_final(root,production=config.mode=='production')
    from somoy_jatri.storage.safety import checkpoint
    checkpoint(root)
    return qc
