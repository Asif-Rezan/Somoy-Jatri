"""Editorial sequences based on the fixed, source-checked history catalog."""
from functools import lru_cache
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageOps

from thumbnail_design import _font


ROOT = Path(__file__).resolve().parent / 'assets'
ARTIFACTS = {
    'Ancient Rome': ('augustus.jpg', 'Gold aureus of Augustus', '20–19 BCE', '246866', r'\bAugustus\b', 2),
    'the Ottoman Empire': ('suleiman.jpg', 'Tughra of Sultan Süleiman', 'c. 1555–60', '449533', r'\bS[uü]leiman\b', 2),
    'Feudal Japan': ('edo-mask.jpg', 'Half mask with gorget', 'c. 1615–1868', '31976', r'\bEdo\b', 3),
}
STORIES = {
    'Ancient Rome': {
        'eras': ('Early Rome', 'Late Republic', 'Empire', 'New capital', 'East and West'),
        'decision': ('Imperial Rome', 'A capital at Constantinople', 'Imperial rule continues in the East'),
        'trigger': r'\b(?:new capital|Constantinople)\b',
        'uncertainty': ('Roman tradition', '753 BCE is the traditional founding date.'),
        'uncertainty_pattern': r'\b(?:traditional|tradition|753)\b',
        'recap': ((0,'Rome expands across Italy'), (3,'Constantinople becomes a capital'),
                  (4,'Imperial rule continues in the East')),
        'compare': ('Rome', 'Early Rome', 'Imperial Rome', range(0,4), range(8,12)),
    },
    'the Ottoman Empire': {
        'eras': ('Anatolia', 'Expansion', 'Süleiman', 'Court culture', 'End of the Sultanate'),
        'decision': ('Bursa and Edirne', 'Constantinople conquered', 'Constantinople becomes the capital'),
        'trigger': r'\b(?:Constantinople|1453)\b',
        'uncertainty': ('Approximate date', 'The principality emerged around 1299.'),
        'uncertainty_pattern': r'\b(?:around|approximately)\b.*\b1299\b',
        'recap': ((0,'A principality in Anatolia'), (1,'Constantinople conquered'), (4,'The sultanate is abolished')),
        'compare': ('Constantinople', 'The Conquest Era', 'Later Ottoman Capital', range(4,8), range(12,16)),
    },
    'Feudal Japan': {
        'eras': ('Kamakura', 'Ashikaga', 'Unification', 'Tokugawa', 'Meiji'),
        'decision': ('Government in Edo', 'Authority returned', 'A new political order'),
        'trigger': r'\b(?:1867|restoration|Yoshinobu)\b',
        'uncertainty': ('Limits of the record', 'The assigned sources describe changes in government.'),
        'uncertainty_pattern': r'\b(?:evidence|records|sources)\b',
        'recap': ((0,'Warrior government in Kamakura'), (3,'Tokugawa rule centered on Edo'), (4,'The Meiji Restoration')),
        'compare': ('Edo', 'Tokugawa Rule', 'Imperial Transition', range(12,16), range(16,20)),
    },
}


def artifact_sources(subject):
    obj = ARTIFACTS.get(subject)
    return f'The Met · {obj[1]} — https://www.metmuseum.org/art/collection/search/{obj[3]}' if obj else ''


def plan_sequence(shots, subject):
    info = STORIES.get(subject)
    if not info or len(shots) < 3:
        return
    last_era, shown = None, set()
    for shot in shots:
        era = min(4,shot.get('chapter',0)//4)
        edit = shot.setdefault('edit',{})
        if era != last_era:
            edit['era'] = (info['eras'],era)
            last_era = era
        if 'decision' not in shown and era >= 2 and re.search(info['trigger'],shot['narration'],re.I):
            edit['decision'] = info['decision']
            edit['reveal'] = 5.2
            shown.add('decision')
        artifact = ARTIFACTS.get(subject)
        if artifact and 'artifact' not in shown and era == artifact[-1] and re.search(artifact[-2],shot['narration'],re.I):
            edit['artifact'] = artifact[:4]
            shown.add('artifact')
        if 'uncertainty' not in shown and re.search(info['uncertainty_pattern'],shot['narration'],re.I):
            edit['uncertainty'] = info['uncertainty']
            shown.add('uncertainty')
    for offset,(shot,(era,label)) in enumerate(zip(shots[-4:-1],info['recap']),1):
        shot['edit']['recap'] = (offset,label)
        earlier = [item for item in shots if item.get('chapter',0)//4 == era
                   and item.get('index',-1) < shot.get('index',0)]
        if earlier:
            source = max(earlier,key=lambda item: len(item.get('narration','')))
            shot['edit']['recap_image'] = source['index']


def comparison(shots, subject):
    info = STORIES.get(subject)
    if not info:
        return None
    place, old, new, early_eras, late_eras = info['compare']
    pattern = re.compile(r'\b'+re.escape(place)+r'\b',re.I)
    matching = [shot for shot in shots if pattern.search(shot.get('visual_action',''))]
    first = next((shot for shot in matching if shot['chapter'] in early_eras),None)
    last = next((shot for shot in matching if shot['chapter'] in late_eras and shot['duration'] >= 5),None)
    if first is None or last is None:
        return None
    return {'shots': [first['index'],last['index']], 'titles': [old,new],
            'place': place, 'start': last['start']+.7, 'end': last['start']+min(5.7,last['duration']-.2)}


@lru_cache(maxsize=10)
def font(size):
    return _font(size)


def badge(draw, box, text, *, size=24):
    draw.rounded_rectangle(box,radius=15,fill=(21,36,40,242),outline='#dfba78',width=2)
    x0,y0,x1,y1 = box
    while size > 14 and draw.textlength(text,font=font(size)) > x1-x0-20:
        size -= 2
    draw.text(((x0+x1)//2,(y0+y1)//2),text,anchor='mm',font=font(size),fill='#fff0cb')


@lru_cache(maxsize=3)
def artifact_image(filename):
    with Image.open(ROOT/'history-evidence'/filename) as source:
        return ImageOps.contain(source.convert('RGB'),(510,350),Image.Resampling.LANCZOS)


def draw_sequence(frame, spec, t, seconds):
    draw = ImageDraw.Draw(frame,'RGBA')
    if spec.get('era') and .4 <= t < min(3.6,seconds):
        eras, active = spec['era']
        for i,label in enumerate(eras):
            x = 45+i*240
            badge(draw,(x,475,x+226,534),('• ' if i == active else '')+label,size=21)
            if i == active:
                draw.line((x+22,527,x+204,527),fill='#f3c97b',width=4)
    if spec.get('decision') and 1.1 <= t < min(8.5,seconds):
        for i,label in enumerate(spec['decision'][:min(3,int((t-1.1)/2.05)+1)]):
            x = 48+i*398
            badge(draw,(x,372,x+386,455),('BEFORE · ','DECISION · ','AFTER · ')[i]+label,size=23)
    if spec.get('artifact') and 2.2 <= t < min(7.2,seconds):
        filename,title,period,object_id = spec['artifact']
        photo = artifact_image(filename)
        draw.rounded_rectangle((677,32,1247,459),radius=22,fill=(22,31,36,252),outline='#e6bd79',width=3)
        frame.paste(photo,(962-photo.width//2,54+(350-photo.height)//2))
        badge(draw,(694,393,1230,447),f'{title} · {period} · The Met #{object_id}',size=19)
    if spec.get('uncertainty') and 1.3 <= t < min(5.4,seconds):
        header,line = spec['uncertainty']
        badge(draw,(42,124,618,196),f'{header.upper()} · {line}',size=22)
    if spec.get('recap') and .45 <= t < min(8.7,seconds):
        index,label = spec['recap']
        badge(draw,(46,565,788,625),f'RECAP {index}/3  ·  {label}',size=27)
    return frame


def comparison_card(paths, spec, target):
    image = Image.new('RGB',(1280,720),'#17272c')
    draw = ImageDraw.Draw(image)
    badge(draw,(50,30,1230,106),spec['place'].upper()+' THROUGH TIME',size=42)
    for i,(path,title) in enumerate(zip(paths,spec['titles'])):
        with Image.open(path) as source:
            image.paste(ImageOps.fit(source.convert('RGB'),(580,442),Image.Resampling.LANCZOS),
                        (50+i*600,120))
        badge(draw,(50+i*600,565,630+i*600,619),title,size=30)
    draw.text((640,657),'ILLUSTRATIVE RECONSTRUCTIONS',anchor='mm',font=font(20),fill='#f0d29d')
    image.save(target)
