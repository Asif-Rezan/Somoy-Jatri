import os
from pathlib import Path
from somoy_jatri.utils import save,load,duration
from somoy_jatri.narration.text import normalize,validate_segment
from somoy_jatri.narration.providers import provider
from somoy_jatri.audio import concatenate,read_wav
from somoy_jatri.alignment.timing import BengaliASR
from somoy_jatri.storyboard.timeline import build,evaluate_semantics


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
    save(root/'research.json',dossier)
    from somoy_jatri.topics.history import reserve
    history_path=root.parent/'topic-history.json'
    previous=load(history_path) if history_path.exists() else []
    title=topic or dossier['location']+' '+dossier['period']
    if config.mode=='production':reserve(history_path,title,config.run_id,dossier.get('topic_id'))
    from somoy_jatri.scripts.groq import generate
    story=load(root/'story.json') if (root/'story.json').exists() else (
        mock_story() if config.mode=='mock' else generate(dossier,config.target,previous))
    tts=None;aligner=None
    for revision in range(3):
        if not story.get('title') or not story.get('segments'):raise ValueError('Empty story')
        for s in story['segments']:
            s['text']=normalize(s['text']);validate_segment(s)
            if any(not isinstance(i,int) or not 0<=i<len(dossier['facts']) for i in s.get('fact_ids',[])):
                raise ValueError('Invalid fact reference')
        save(root/'story.json',story)
        utterances=root/'utterances';utterances.mkdir(exist_ok=True)
        parts=[];records=[]
        for i,s in enumerate(story['segments']):
            path=utterances/f'{i:04}.wav'
            # Manifest fingerprint prevents using stale speech after script revisions.
            from hashlib import sha256
            fingerprint=sha256((s['text']+s['emotion']+str(s['intensity'])+os.getenv('TTS_MODEL','indic-parler')+os.getenv('TTS_VOICE','Aditi')+config.mode).encode()).hexdigest()
            stamp=path.with_suffix('.json')
            if not (path.exists() and stamp.exists() and load(stamp).get('fingerprint')==fingerprint):
                tts=tts or provider(config.mode)
                tts.synthesize(s['text'],s['emotion'],s['intensity'],path)
                save(stamp,{'fingerprint':fingerprint})
            asr={}
            if config.mode=='production':
                aligner=aligner or BengaliASR();asr=aligner.align(path,s['text'])
            parts.append((path,s['pause_after_ms']));records.append({'text':s['text'],'asr':asr})
        bounds=concatenate(parts,root/'narration.wav')
        total=bounds[-1]['end']
        if config.mode=='mock' or 600<=total<=900:break
        if revision==2:raise ValueError('Narration duration outside 600–900s after revisions; never speed up or truncate')
        story=generate(dossier,config.target,previous,
            f'Measured previous voice duration {total:.1f}s. Adjust total words by ratio {config.target/total:.3f}.')
    for record,b in zip(records,bounds):record.update(b)
    save(root/'narration.json',records)
    shots=build(story,bounds,dossier)
    for shot,record in zip(shots,records):
        shot['words']=[dict(w,start=w['start']+shot['start'],end=w['end']+shot['start'])
                       for w in record.get('asr',{}).get('words',[])]
    review={'passed':True,'method':'mock-only, no semantic quality claim'} if config.mode=='mock' else evaluate_semantics(story,dossier)
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
