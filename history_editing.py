"""Evidence-aligned graphics and restrained sound cues for history documentaries."""
from functools import lru_cache
import math
import re
import wave

from PIL import ImageDraw

from thumbnail_design import _font


ATLAS = {
    'Ancient Rome': {'Rome': (12.50, 41.90), 'Carthage': (10.33, 36.85),
                     'Constantinople': (28.98, 41.01)},
    'the Ottoman Empire': {'Bursa': (29.06, 40.19), 'Edirne': (26.56, 41.68),
                           'Constantinople': (28.98, 41.01), 'Cairo': (31.24, 30.04)},
    'Feudal Japan': {'Kamakura': (139.55, 35.32), 'Kyoto': (135.77, 35.02),
                     'Edo': (139.76, 35.68)},
}
CAPITAL_SHIFTS = {
    'Ancient Rome': ('Rome', 'Constantinople'),
    'the Ottoman Empire': ('Edirne', 'Constantinople'),
}
EVENTS = (
    (r'\b(?:new capital|capital moved)\b', 'A NEW CAPITAL'),
    (r'\b(?:separate emperors|divided rule)\b', 'EAST AND WEST'),
    (r'\b(?:deposition|deposed|abdicated|abdication)\b', 'A RULER FALLS'),
    (r'\b(?:abolished|abolition)\b', 'THE OLD ORDER ENDS'),
    (r'\b(?:continu(?:ed|ation)|survived)\b', 'WHAT SURVIVED'),
    (r'\b(?:unified|unification)\b', 'POWER CONSOLIDATES'),
)
DATE = re.compile(r'\b(?:AD|CE)\s+\d{1,4}\b|\b\d{1,4}\s+(?:BC|BCE|AD|CE)\b|\b[1-2]\d{3}\b', re.I)


def supported_date(label, claims):
    year = re.search(r'\d+',label).group()
    bc = bool(re.search(r'\bBCE?\b',label,re.I))
    pattern = (rf'\b{year}\s+BCE?\b' if bc else
               rf'\b{year}\b(?!\s+BCE?\b)')
    return bool(re.search(pattern,claims,re.I))


def plan_edits(shots, evidence):
    subject = evidence.get('history_subject')
    if not subject or not shots:
        return
    claims = ' '.join(claim['text'] for claim in evidence.get('claims', []))
    atlas = ATLAS.get(subject, {})
    places = [name for name in atlas if re.search(r'\b'+re.escape(name)+r'\b', claims, re.I)]
    last_popup = -30
    previous_places = None
    for i, shot in enumerate(shots):
        narrated = shot['narration']
        edit = {}
        mentioned = [name for name in places if re.search(r'\b'+re.escape(name)+r'\b', narrated, re.I)]
        if i in (0, len(shots)-1) and places:
            edit.update(map=places, focus=places[:1] if i == 0 else mentioned,
                        closing=i == len(shots)-1)
        elif mentioned and mentioned != previous_places:
            when = min((offset for word,offset in shot.get('word_offsets', [])
                        if word.strip('.,?!:;').casefold() in {name.casefold() for name in mentioned}),
                       default=.4)
            if when > shot.get('duration',10)-2:
                mentioned = []
            else:
                edit.update(map=places, focus=mentioned, map_start=max(.4,when))
            shift = CAPITAL_SHIFTS.get(subject)
            if 'map' in edit and shift and all(name in places for name in shift) and shift[-1] in mentioned and re.search(
                    r'\b(?:capital|conquered)\b', narrated, re.I):
                edit['shift'] = shift
        if 'map' in edit:
            edit['subject'] = subject
            previous_places = mentioned
        if shot['start'] - last_popup >= 28:
            date = next((m.group().upper() for m in DATE.finditer(narrated)
                         if supported_date(m.group(),claims)), None)
            event = next((label for pattern,label in EVENTS if re.search(pattern,narrated,re.I)), None)
            if date or event:
                edit['label'] = date or event
                last_popup = shot['start']
        if re.search(r'\b(?:harbou?r|quay|boats?|wooden ships?)\b', narrated, re.I):
            edit['ambience'] = 'water'
        elif re.search(r'\b(?:roads?|march(?:ed|ing)?|footsteps)\b', narrated, re.I):
            edit['ambience'] = 'steps'
        shot['edit'] = edit


@lru_cache(maxsize=12)
def font(size):
    return _font(size)


def draw_edit(frame, spec, t, seconds):
    draw = ImageDraw.Draw(frame, 'RGBA')
    map_start = spec.get('map_start',.4)
    if spec.get('map') and map_start <= t <= min(seconds-.2,map_start+6.6):
        x, y, w, h = 690, 32, 558, 305
        draw.rounded_rectangle((x,y,x+w,y+h),radius=23,fill=(19,37,41,235),outline='#d9af69',width=3)
        draw.text((x+24,y+19),'PLACES IN THE STORY',font=font(25),fill='#ffdc93')
        draw.text((x+24,y+h-37),'SCHEMATIC LOCATION MAP',font=font(14),fill='#cee2d9')
        atlas = ATLAS[spec['subject']]
        coordinates = [atlas[name] for name in spec['map']]
        west, east = min(p[0] for p in coordinates), max(p[0] for p in coordinates)
        south, north = min(p[1] for p in coordinates), max(p[1] for p in coordinates)
        scale = min(410/max(1.2,east-west), 138/max(.6,north-south))
        positions = {name: (x+w/2+(atlas[name][0]-(west+east)/2)*scale,
                            y+152-(atlas[name][1]-(south+north)/2)*scale) for name in spec['map']}
        for i in range(1,6):
            draw.line((x+w*i/6,y+63,x+w*i/6,y+248),fill=(128,183,169,72),width=1)
        for i in range(4):
            draw.line((x+25,y+72+i*55,x+w-25,y+72+i*55),fill=(128,183,169,72),width=1)
        if spec.get('shift'):
            a,b = (positions[name] for name in spec['shift'])
            progress = min(1,max(0,(t-map_start-.55)/1.5))
            end = tuple(p+(q-p)*progress for p,q in zip(a,b))
            draw.line((a,end),fill='#ffd081',width=4)
            if progress > .15:
                angle = math.atan2(b[1]-a[1],b[0]-a[0])
                wings = [(end[0]-14*math.cos(angle+s),end[1]-14*math.sin(angle+s)) for s in (-.55,.55)]
                draw.polygon((end,*wings),fill='#ffd081')
        for i,(name,(px,py)) in enumerate(positions.items()):
            active = name in spec['focus']
            r = 7 + (round(2*math.sin(t*5)) if active else 0)
            draw.ellipse((px-r,py-r,px+r,py+r),fill='#ffcd72' if active else '#afc9bc')
            draw.text((px,py+(-21 if i%2 else 21)),name,anchor='mm',font=font(17),
                      fill='#fff6dc',stroke_width=2,stroke_fill='#142629')
    if spec.get('label') and 1.1 <= t < min(seconds,4):
        text = spec['label']
        width = round(draw.textlength(text,font=font(34)))+44
        draw.rounded_rectangle((38,36,38+width,97),radius=14,fill=(19,37,41,240),outline='#edbd69',width=3)
        draw.text((60,66),text,font=font(34),anchor='lm',fill='#fff2ca')
    if spec.get('label') or spec.get('map'):
        if .4 < t < min(4,seconds):
            draw.text((1240,567),'ILLUSTRATIVE RECONSTRUCTION',anchor='ra',font=font(16),fill='#fff2ca',
                      stroke_width=2,stroke_fill='#192a28')
    return frame


def audio_cues(shots, target, seconds):
    """Write short, low-level procedural cues and return a timed music gain filter."""
    import numpy as np

    rate = 12000
    signal = np.zeros(round(seconds*rate), dtype=np.int16)
    rng = np.random.default_rng(465)
    dips = []
    for shot in shots:
        spec = shot.get('edit') or {}
        if not spec:
            continue
        reveal = spec.get('reveal')
        start = round((shot['start']+(reveal-.85 if reveal else 1.15))*rate)
        count = min(rate*2, len(signal)-start)
        if count <= 0:
            continue
        t = np.arange(count)/rate
        envelope = np.sin(np.pi*t/2)**2
        sound = np.zeros(count)
        if spec.get('ambience') == 'water':
            noise = rng.uniform(-1, 1, count)
            sound += np.convolve(noise,np.ones(30)/30,mode='same') * .10
        elif spec.get('ambience') == 'steps':
            sound += .023*np.sin(2*np.pi*63*t)*np.exp(-15*(t%0.47))
        if spec.get('label') or spec.get('shift') or reveal:
            sound += .017*np.sin(2*np.pi*(210*t-35*t*t))
            dips.append(f'between(t,{start/rate:.3f},{(start+count)/rate:.3f})')
        signal[start:start+count] = np.rint(sound*envelope*32767).astype(np.int16)
    with wave.open(str(target),'wb') as file:
        file.setparams((1,2,rate,0,'NONE',''))
        file.writeframes(signal.astype('<i2',copy=False).tobytes())
    return "volume='if("+'+'.join(dips)+",0.65,1)':eval=frame," if dips else ''
