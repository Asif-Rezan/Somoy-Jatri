"""Original procedural instrumental cues. This is synthesis, not a trained AI model."""
from typing import Protocol
import numpy as np
from somoy_jatri.audio import RATE, write_wav, read_wav, duck_gain

class MusicProvider(Protocol):
    def generate(self, cue: dict, seconds: float, seed: int) -> np.ndarray: ...

class ProceduralMusic:
    def generate(self, cue, seconds, seed):
        rng=np.random.default_rng(seed)
        n=round(seconds*RATE); audio=np.zeros(n,dtype=np.float32)
        roots={'curious':146.83,'amazed':130.81,'reflective':110.,'happy':164.81,'neutral':123.47}
        root=roots.get(cue['mood'],138.59)
        step={'reflective':1.7,'curious':.85,'amazed':1.2}.get(cue['mood'],1.)
        scale=[0,2,5,7,9] if cue['mood']!='reflective' else [0,3,5,7,10]
        for j,start in enumerate(np.arange(0,seconds,step)):
            length=min(step*1.8,seconds-start); t=np.arange(round(length*RATE))/RATE
            freq=root*2**(int(rng.choice(scale))/12)
            signal=(np.sin(2*np.pi*freq*t)+.22*np.sin(4*np.pi*freq*t))*np.minimum(t/.08,1)*np.exp(-t/1.2)
            a=round(start*RATE); b=min(n,a+len(signal)); audio[a:b]+=.17*signal[:b-a]
        t=np.arange(n)/RATE
        audio+=.035*np.sin(2*np.pi*root*.5*t)
        f=min(round(cue['fade']*RATE),n//2)
        audio[:f]*=np.linspace(0,1,f);audio[-f:]*=np.linspace(1,0,f)
        return audio

class LicensedMusic:
    def __init__(self, catalog): self.catalog=catalog
    def generate(self,cue,seconds,seed):
        entry=self.catalog[cue['style']]
        if not entry.get('license') or not entry.get('source'): raise ValueError('Unlicensed cue')
        audio=read_wav(entry['path'])
        if len(audio)<round(seconds*RATE): raise ValueError('Licensed cue too short; looping forbidden')
        return audio[:round(seconds*RATE)]


def plan(shots):
    cues=[]
    for s in shots:
        key=(s['chapter'],s['mood'])
        if cues and (cues[-1]['chapter'],cues[-1]['mood'])==key:
            cues[-1]['end']=s['end'];continue
        cues.append({'start':s['start'],'end':s['end'],'chapter':s['chapter'],
            'mood':s['mood'],'style':s['scene']+'_ambient','intensity':.35,'fade':1.5,'ducking':True})
    return cues


def score(cues,total,provider=None):
    provider=provider or ProceduralMusic()
    mix=np.zeros(round(total*RATE),dtype=np.float32)
    for i,cue in enumerate(cues):
        # Overlap tails around the larger chapter boundaries; cues never restart per shot.
        start=max(0.,cue['start']-(cue['fade']/2 if i else 0))
        end=min(total,cue['end']+(cue['fade']/2 if i<len(cues)-1 else 0))
        audio=provider.generate(cue,end-start,seed=2026+i*47)
        a=round(start*RATE);b=min(len(mix),a+len(audio));mix[a:b]+=audio[:b-a]
    return mix


def mix(voice_path, music, ambient, output):
    voice=read_wav(voice_path);n=len(voice)
    if len(music)!=n or len(ambient)!=n: raise ValueError('Audio timeline mismatch')
    result=voice+music*duck_gain(voice)+ambient*duck_gain(voice,.07)
    if not np.isfinite(result).all(): raise ValueError('Invalid mix')
    peak=float(np.max(np.abs(result)))
    if peak>.94: result*=.94/peak
    write_wav(output,result)
