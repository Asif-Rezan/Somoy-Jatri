from PIL import Image
import numpy as np
from somoy_jatri.utils import load,save,probe,duration,run,digest
from somoy_jatri.audio import read_wav
from somoy_jatri.storyboard.timeline import validate
from somoy_jatri.images.providers import verify


def validate_final(root,production=False):
    timeline=load(root/'timeline.json');audio=read_wav(root/'narration.wav')
    total=len(audio)/24000
    validate(timeline,total)
    voice_peak=float(np.max(np.abs(audio)))
    if voice_peak<.001 or voice_peak>.999:raise ValueError('Voice silent or clipping')
    mixed=read_wav(root/'mix.wav')
    if float(np.max(np.abs(mixed)))>.999:raise ValueError('Mix clipping')
    p=probe(root/'video.mp4');streams=p['streams']
    v=next(s for s in streams if s['codec_type']=='video')
    a=next(s for s in streams if s['codec_type']=='audio')
    if v['codec_name']!='h264' or a['codec_name']!='aac':raise ValueError('Wrong output codec')
    if abs(float(p['format']['duration'])-total)>.15:raise ValueError('Final video duration mismatch')
    if abs(float(v.get('duration',total))-float(a.get('duration',total)))>.15:
        raise ValueError('Audio/video duration mismatch')
    if production and (not 600<=total<=900 or (v['width'],v['height'])!=(1920,1080)):
        raise ValueError('Production output must be 600–900s at 1080p')
    for shot in timeline:
        path=root/'images'/(shot['id']+'.png');verify(path)
        receipt=load(path.with_suffix('.json'))
        if receipt['sha256']!=digest(path):raise ValueError('Image checkpoint checksum mismatch')
    cues=load(root/'music-plan.json')
    if len({s['mood'] for s in timeline})>1 and len(cues)<2:
        raise ValueError('Missing musical variety')
    if Image.open(root/'thumbnail.jpg').size!=(1280,720):raise ValueError('Thumbnail dimensions')
    # Decode all frames; blackdetect and silencedetect return measurements for review.
    import subprocess
    result=subprocess.run(['ffmpeg','-hide_banner','-i',str(root/'video.mp4'),
        '-vf','blackdetect=d=0.3:pix_th=0.05','-af','silencedetect=n=-50dB:d=3',
        '-f','null','-'],capture_output=True,text=True)
    if result.returncode or 'black_start:' in result.stderr or 'silence_start:' in result.stderr:
        raise ValueError('Blank frames, decoding failure or extended silence detected')
    if production:
        narration=load(root/'narration.json')
        from somoy_jatri.narration.providers import audio_record_passed
        if not narration or any(not audio_record_passed(s) for s in narration):
            raise ValueError('Narration audio checks missing')
        if load(root/'semantic-review.json').get('passed') is not True:
            raise ValueError('Semantic review missing')
        require_research_review(load(root/'research.json'))
    qc={'passed':True,'production_ready':production,'duration':total,'width':v['width'],
        'height':v['height'],'voice_peak':voice_peak,'sha256':digest(root/'video.mp4'),
        'limitations':['No automated proof of historical visual accuracy or perceived voice quality',
                        'Captions use measured utterance timing; pronunciation is not verified by ASR']}
    save(root/'qc.json',qc)
    return qc


def require_research_review(dossier):
    # Automatically sourced episodes are permitted for private review. Upload independently
    # refuses public/unlisted visibility for this method; never fabricate a human reviewer.
    if not dossier.get('reviewed_by') and dossier.get('research_method')!='automatic source extraction':
        raise ValueError('Research review missing')
