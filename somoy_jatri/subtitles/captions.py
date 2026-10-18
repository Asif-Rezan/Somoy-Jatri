from pathlib import Path
import os
from somoy_jatri.utils import run


def font():
    supplied=os.getenv('BANGLA_FONT')
    if supplied:
        if not Path(supplied).is_file(): raise ValueError('Missing Bangla font')
        return supplied
    bundled=Path(__file__).resolve().parents[2]/'assets/fonts/NotoSansBengali-Regular.ttf'
    if bundled.is_file(): return str(bundled)
    files=run(['fc-list',':lang=bn','file']).strip().splitlines()
    if not files: raise ValueError('Install fonts-noto-core or set BANGLA_FONT')
    return files[0].split(':')[0]


def timestamp(value,ass=False):
    units=100 if ass else 1000
    ticks=round(value*units);seconds,fraction=divmod(ticks,units)
    minutes,seconds=divmod(seconds,60);hours,minutes=divmod(minutes,60)
    return (f'{hours}:{minutes:02}:{seconds:02}.{fraction:02}' if ass else
            f'{hours:02}:{minutes:02}:{seconds:02},{fraction:03}')


def chunks(shot):
    # Word-level ASR times anchor short chunks of original text; no proportional timing estimates.
    words=shot.get('words',[])
    text=shot['narration'].split()
    if words and len(words)==len(text):
        return [(words[i]['start'],words[min(i+7,len(words)-1)]['end'],' '.join(text[i:i+8]))
                for i in range(0,len(words),8)]
    # Reliable sentence boundary fallback: independently synthesized single visual utterance.
    return [(shot['start'],shot['speech_end'],shot['narration'])]


def generate(root,shots):
    font()
    entries=[e for s in shots for e in chunks(s)]
    srt=[];ass=['[Script Info]','ScriptType: v4.00+','PlayResX: 1920','PlayResY: 1080',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: Default,Noto Sans Bengali,50,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,130,130,80,1',
        '[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    for i,(start,end,text) in enumerate(entries,1):
        words=text.split();lines=[];line=''
        for word in words:
            if len(line+' '+word)>38 and line: lines.append(line);line=''
            line=(line+' '+word).strip()
        lines.append(line)
        srt.append(f'{i}\n{timestamp(start)} --> {timestamp(end)}\n'+ '\n'.join(lines))
        # Escape ASS controls from generated text.
        clean='\\N'.join(lines).replace('{','').replace('}','')
        ass.append(f'Dialogue: 0,{timestamp(start,True)},{timestamp(end,True)},Default,,0,0,0,,{clean}')
    (root/'captions.srt').write_text('\n\n'.join(srt)+'\n',encoding='utf-8')
    (root/'captions.ass').write_text('\n'.join(ass)+'\n',encoding='utf-8')
