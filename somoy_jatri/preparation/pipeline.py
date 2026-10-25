"""Chapter preparation follows Rezan-After-Dark d6dcde3, with Bengali adapters."""
import hashlib
import json
import math
import os
import re
from dataclasses import asdict
from pathlib import Path
import numpy as np
from somoy_jatri.utils import save, load, digest, duration, run
from somoy_jatri.audio import RATE, read_wav, write_wav, concatenate
from somoy_jatri.narration.text import normalize
from somoy_jatri.preparation import duration_control as dc
from somoy_jatri.preparation import story as scripts


def event(stage, **fields):
    print(json.dumps({'prepare_stage':stage,**fields}),flush=True)


def catalog_dossier(previous):
    from somoy_jatri.research.automatic import choose
    topic=choose(previous)
    if not topic.get('facts'):raise ValueError('Curated historical facts required')
    sources=[{'id':f's{i+1}','url':url,'title':topic['location'],
              'excerpt':topic['facts'][0], 'excerpt_kind':'curated factual paraphrase'}
             for i,url in enumerate(topic['sources'])]
    if any(not s['url'].startswith('https://') for s in sources):raise ValueError('HTTPS historical sources required')
    packet={key:'Unknown; reconstruct cautiously' for key in ['politics','culture','clothing','buildings',
        'tools','transportation','food','trades','social_life','events']}
    packet.update(location=topic['location'],period=topic['period'],topic_id=topic['id'],
        facts=[{'claim':fact,'source_id':'s1'} for fact in topic['facts']],sources=sources,
        uncertain=['Unstated details are artistic reconstruction, not documented history.'],
        research_method='curated source catalog')
    from somoy_jatri.research.dossier import validate
    return validate(packet,live=False,require_review=False)


def stage_story(config, topic='', period=''):
    config.preflight()
    root=config.root;root.mkdir(parents=True,exist_ok=True)
    if (root/'config.json').exists() and load(root/'config.json')!=asdict(config):
        raise ValueError('Saved configuration changed; use a new run')
    save(root/'config.json',asdict(config))
    previous=load(root.parent/'topic-history.json') if (root.parent/'topic-history.json').exists() else []
    if (root/'research.json').exists():dossier=load(root/'research.json')
    elif os.environ['RESEARCH_DOSSIER']=='auto':dossier=catalog_dossier(previous)
    else:
        from somoy_jatri.research.dossier import validate
        dossier=validate(load(Path(os.environ['RESEARCH_DOSSIER'])),live=True)
    if period and period!=dossier['period']:raise ValueError('Period differs from research')
    save(root/'research.json',dossier)
    if (root/'story.json').exists():
        scripts.validate(load(root/'story.json'),dossier)
        event('story_restored');return
    from somoy_jatri.topics.history import reserve
    reserve(root.parent/'topic-history.json',topic or dossier['location']+' '+dossier['period'],config.run_id,dossier.get('topic_id'))
    event('outline_start',model='Qwen/Qwen3-4B-Instruct-2507',chapters=20)
    story=scripts.generate(dossier,previous)
    save(root/'story.json',story)
    event('story_ready',chapters=20,words=sum(len(s['narration'].split()) for s in story['scenes']))


def chapter_chunks(text, limit=240):
    """Bengali Parler's bounded input replaces Kokoro's internal sentence splitter."""
    chunks=[];current=''
    for sentence in re.split(r'(?<=[।.!?])\s+',text):
        for word in sentence.split():
            if len(word)>limit:raise ValueError('Narration contains an oversized token')
            candidate=(current+' '+word).strip()
            if len(candidate)>limit:
                chunks.append(current);current=word
            else:current=candidate
        if current and len(current)>limit*.65:
            chunks.append(current);current=''
    if current:chunks.append(current)
    return chunks


def fingerprint(text):
    return hashlib.sha256(json.dumps({'text':text,'model':os.getenv('TTS_MODEL','Tanmoyshome/bn-parler-tts'),
        'voice':os.getenv('TTS_VOICE','Aditi'),'emotion':os.getenv('TTS_EMOTION_ENABLED','true'),
        'adapter':'chapter-bengali-v1'},sort_keys=True).encode()).hexdigest()


def audio_measure(path):
    samples=read_wav(path)
    seconds=len(samples)/RATE
    peak=float(np.max(np.abs(samples))) if len(samples) else 0
    rms=float(np.sqrt(np.mean(samples**2))) if len(samples) else 0
    if not np.isfinite(samples).all() or not .3<=seconds<=180 or peak<.001 or rms<.0005 or np.mean(np.abs(samples)>=.999)>.001:
        raise ValueError('Chapter audio is invalid, silent or clipped')
    return {'method':'measured-chapter-audio','passed':True,'seconds':seconds,'peak':peak,'rms':rms,
            'transcript_verified':False}


def chapter_audio(root,index,text,tts):
    path=root/f'narration-{index:02}.wav';stamp=path.with_suffix('.meta.json')
    meta=load(stamp) if stamp.exists() else {}
    if path.exists() and meta.get('fingerprint')==fingerprint(text) and meta.get('audio_sha256')==digest(path):
        audio_measure(path);event('chapter_audio_cached',chapter=index+1,seconds=round(duration(path),2));return duration(path)
    event('chapter_audio_start',chapter=index+1)
    # One cached audio asset per chapter; no independent 140-utterance preparation loop.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='somoy-chapter-') as work:
        for attempt in range(3):
            parts=[]
            for part,chunk in enumerate(chapter_chunks(text)):
                candidate=Path(work)/f'{part}.wav'
                tts.synthesize(chunk,'neutral',.5,candidate)
                audio_measure(candidate)
                parts.append((candidate,0))
            candidate=Path(work)/'chapter.wav'
            concatenate(parts,candidate)
            try:audio=audio_measure(candidate)
            except ValueError:
                if attempt==2:raise
                continue
            candidate.replace(path)
            save(stamp,{'fingerprint':fingerprint(text),'audio_sha256':digest(path),'seconds':audio['seconds']})
            (root/f'words-{index:02}.json').unlink(missing_ok=True)
            (root/f'words-{index:02}.meta.json').unlink(missing_ok=True)
            event('chapter_audio_ready',chapter=index+1,seconds=round(audio['seconds'],2))
            return audio['seconds']
    raise RuntimeError('Chapter audio did not complete')


def adjust_tempo(root,story,lengths,factor):
    if not 1<factor<=dc.MAX_TEMPO:raise ValueError('Unsafe chapter tempo')
    candidates=[]
    try:
        for index,length in enumerate(lengths):
            source=root/f'narration-{index:02}.wav';stamp=source.with_suffix('.meta.json')
            if load(stamp).get('tempo_factor',1)*factor>dc.MAX_TEMPO:raise ValueError('Cumulative chapter tempo exceeds 4%')
            candidate=source.with_suffix('.new.wav');candidates.append(candidate)
            run(['ffmpeg','-v','error','-y','-i',source,'-af',f'atempo={factor:.9f}','-c:a','pcm_s16le',candidate])
            if abs(duration(candidate)-length/factor)>max(.15,length*.01):raise ValueError('Chapter tempo duration mismatch')
        for index,candidate in enumerate(candidates):
            source=root/f'narration-{index:02}.wav';stamp=source.with_suffix('.meta.json');meta=load(stamp)
            candidate.replace(source)
            save(stamp,{**meta,'audio_sha256':digest(source),'seconds':duration(source),
                        'tempo_factor':meta.get('tempo_factor',1)*factor})
        return [duration(root/f'narration-{i:02}.wav') for i in range(20)]
    finally:
        for path in candidates:path.unlink(missing_ok=True)


def correct_duration(root,story,dossier,tts):
    lengths=[chapter_audio(root,i,s['narration'],tts) for i,s in enumerate(story['scenes'])]
    for attempt in range(dc.MAX_ATTEMPTS+1):
        total=sum(lengths);event('duration_check',seconds=round(total,2),passed=dc.valid(total),attempt=attempt)
        if dc.valid(total):return story,lengths
        if attempt==dc.MAX_ATTEMPTS:break
        factor=dc.tempo_factor(total)
        if factor and any(load((root/f'narration-{i:02}.wav').with_suffix('.meta.json')).get('tempo_factor',1)*factor>dc.MAX_TEMPO for i in range(20)):
            factor=None
        if factor:
            event('duration_tempo',factor=round(factor,6));lengths=adjust_tempo(root,story,lengths,factor)
        else:
            direction='shorten' if total>dc.MAX_SECONDS else 'expand'
            selected,ratio=dc.select_revisions(lengths,direction)
            event('duration_rewrite',chapters=[i+1 for i in selected],direction=direction)
            revised=scripts.revise(story,dossier,ratio,direction,selected)
            # Save corrected text first; fingerprints invalidate old chapter audio on recovery.
            save(root/'story.json',revised)
            for index in selected:
                if revised['scenes'][index]['narration']!=story['scenes'][index]['narration']:
                    lengths[index]=chapter_audio(root,index,revised['scenes'][index]['narration'],tts)
            story=revised
    raise RuntimeError('Chapter narration remains outside 600–900 seconds after three bounded corrections')


def ensure_words(root,index,path,text,recognizer):
    words_path=root/f'words-{index:02}.json';meta_path=root/f'words-{index:02}.meta.json'
    stamp={'audio_sha256':digest(path),'text_fingerprint':fingerprint(text)}
    if words_path.exists() and meta_path.exists() and load(meta_path)==stamp:
        words=load(words_path)
        if isinstance(words,list) and words:return words
    words=recognizer.align(path,text,strict=False)['words']
    if not words:raise ValueError('Chapter has no measured Bengali word timestamps')
    save(words_path,words);save(meta_path,stamp)
    return words


def shot_plan(story,lengths,word_lists):
    if not len(story['scenes'])==len(lengths)==len(word_lists)==20:raise ValueError('Chapter timing mismatch')
    words=[];offset=0.
    for index,(length,part) in enumerate(zip(lengths,word_lists)):
        if not part:raise ValueError('Missing measured chapter words')
        for word in part:
            start,end=float(word['start']),float(word['end'])
            if not math.isfinite(start) or not math.isfinite(end) or not 0<=start<end<=length+.1:
                raise ValueError('Word timing outside measured chapter audio')
            words.append({**word,'start':offset+start,'end':offset+min(end,length),'chapter':index})
        offset+=length
    shots=[]
    for index in range(math.ceil(offset/7)):
        start,end=index*7.,min((index+1)*7.,offset)
        spoken=[w for w in words if w['end']>start and w['start']<end]
        anchors=spoken or [min(words,key=lambda w:abs(w['start']-start))]
        chapter=max({w['chapter'] for w in anchors},key=lambda c:sum(max(0,min(end,w['end'])-max(start,w['start'])) for w in anchors if w['chapter']==c))
        shots.append({'id':f'shot_{index:04}','start':start,'end':end,'speech_end':end,
            'chapter':f'chapter_{chapter+1:02}','scene':f'chapter_{chapter+1:02}',
            'chapter_index':chapter,'narration':' '.join(w['word'].strip() for w in anchors),
            'motion':'slow_forward','mood':'reflective','ambient':'wind','image_interval_seconds':7})
    return shots


def prepare_audio(config):
    from somoy_jatri.narration.providers import provider
    from somoy_jatri.alignment.timing import BengaliASR
    root=config.root;dossier=load(root/'research.json');story=scripts.validate(load(root/'story.json'),dossier)
    # Models load only after input validation, and are reused across all twenty chapters.
    event('narration_start',chapters=20)
    story,lengths=correct_duration(root,story,dossier,provider('production'))
    save(root/'story.json',story)
    recognizer=BengaliASR();word_lists=[];records=[];parts=[];offset=0.
    for index,(scene,length) in enumerate(zip(story['scenes'],lengths)):
        path=root/f'narration-{index:02}.wav'
        words=ensure_words(root,index,path,scene['narration'],recognizer)
        word_lists.append(words);parts.append((path,0))
        records.append({'text':' '.join(w['word'].strip() for w in words),'script_text':scene['narration'],
            'start':offset,'speech_end':offset+length,'end':offset+length,
            'asr':{'words':words,'method':'measured-bengali-transcription'},'audio':audio_measure(path)})
        offset+=length;event('chapter_aligned',chapter=index+1,seconds=round(length,2),words=len(words))
    concatenate(parts,root/'narration.wav')
    measured=duration(root/'narration.wav')
    if not dc.valid(measured) or abs(measured-sum(lengths))>.15:raise ValueError('Concatenated chapter audio duration mismatch')
    save(root/'narration.json',records)
    source_hash=hashlib.sha256(json.dumps({'story':story,'words':word_lists,'interval':7,
        'audio_hashes':[digest(root/f'narration-{i:02}.wav') for i in range(20)]},sort_keys=True).encode()).hexdigest()
    old=load(root/'plan.json') if (root/'plan.json').exists() else {}
    plan=old if old.get('source_hash')==source_hash and old.get('storyboard_verified') else {
        'source_hash':source_hash,'duration_seconds':measured,'shots':shot_plan(story,lengths,word_lists),'storyboard_verified':False}
    save(root/'plan.json',plan)
    from somoy_jatri.subtitles.captions import generate
    generate(root,plan['shots'])
    save(root/'duration.json',{'duration_seconds':measured,'story_sha256':digest(root/'story.json'),
        'narration_sha256':digest(root/'narration.wav'),'captions_sha256':digest(root/'captions.srt'),
        'plan_source_hash':source_hash,'chapters':lengths})
    event('audio_ready',seconds=round(measured,2),images=len(plan['shots']))
    return plan['shots']


def verify_preparation(root):
    manifest=load(root/'duration.json');plan=load(root/'plan.json')
    if not dc.valid(manifest['duration_seconds']):raise ValueError('Invalid measured chapter duration')
    if manifest['story_sha256']!=digest(root/'story.json') or manifest['narration_sha256']!=digest(root/'narration.wav') or manifest['captions_sha256']!=digest(root/'captions.srt') or manifest['plan_source_hash']!=plan['source_hash']:
        raise ValueError('Prepared story/audio/captions changed; rebuild chapter timing')
    return plan


def storyboard(root,request=scripts.ask):
    plan=verify_preparation(root)
    if plan.get('storyboard_verified'):return
    story=load(root/'story.json');dossier=load(root/'research.json')
    from somoy_jatri.storyboard.timeline import NEGATIVE
    for begin in range(0,len(plan['shots']),8):
        batch=plan['shots'][begin:begin+8]
        if all(s.get('prompt') for s in batch):continue
        schema=scripts.obj({s['id']:{'type':'string'} for s in batch})
        indices={s['chapter_index'] for s in batch}
        context={str(i):story['scenes'][i]['narration'] for i in indices}
        values=request('Return one concise 12–22 word English image prompt for EACH exact shot key. '
            'Illustrate the concrete action, object or documented setting in the measured Bangla narration window. '
            'Chapter narration only resolves context; do not illustrate earlier or later events. '
            'Subject and action first, then relevant objects and location. One simple composition, no typography. '
            'Historical first-person travel documentary, narrator behind camera; no horror or modern objects. '
            'Uncertain visual detail must be described as artistic reconstruction, never documented evidence. '
            f'Location: {dossier["location"]}. Period: {dossier["period"]}. Facts: '+json.dumps(dossier['facts'],ensure_ascii=False)
            +'. Chapter context: '+json.dumps(context,ensure_ascii=False)
            +'. Exact windows: '+json.dumps({s['id']:s['narration'] for s in batch},ensure_ascii=False),1800,schema,.2)
        if set(values)!=set(schema['properties']):raise ValueError('Storyboard did not cover every timed shot')
        for shot in batch:
            visual=values[shot['id']].strip()
            if not 5<=len(visual.split())<=30:raise ValueError('Storyboard visual must be concise')
            shot.update(subject=visual,visual=visual,anchors=[visual],
                prompt=visual+'. Photorealistic historical documentary reconstruction, first-person POV, no typography.',
                negative_prompt=NEGATIVE)
        save(root/'plan.json',plan)
        event('storyboard_progress',completed=min(begin+8,len(plan['shots'])),total=len(plan['shots']))
    plan['storyboard_verified']=True;save(root/'plan.json',plan)


def refine_plan(root):
    plan=verify_preparation(root)
    if plan.get('storyboard_verified') is not True:raise ValueError('Timed storyboard must finish first')
    from somoy_jatri.storyboard.timeline import validate
    validate(plan['shots'],plan['duration_seconds'])
    save(root/'timeline.json',plan['shots'])
    # A structural/evidence receipt, explicitly NOT a repeated model semantic review.
    save(root/'semantic-review.json',{'passed':True,'method':'reference-schema-and-evidence-validation',
        'plan_source_hash':plan['source_hash'],'story_sha256':digest(root/'story.json'),
        'timeline_sha256':digest(root/'timeline.json'),
        'limitations':['No automated historical or cross-language semantic proof; private editorial review required']})
    event('preparation_complete',chapters=20,images=len(plan['shots']),seconds=round(plan['duration_seconds'],2))
