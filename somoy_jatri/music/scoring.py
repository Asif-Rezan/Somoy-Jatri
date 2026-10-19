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
        # Restrained historical documentary bed: modal strings, drone,
        # sparse plucked notes and soft frame-drum pulses beneath narration.
        root=110.
        t=np.arange(n)/RATE
        for semitone,level in [(0,.022),(7,.012),(12,.008)]:
            freq=root*2**(semitone/12)
            swell=.7+.3*np.sin(2*np.pi*t/12+semitone)
            audio+=level*swell*(np.sin(2*np.pi*freq*t)+.18*np.sin(4*np.pi*freq*t))
        audio+=.018*np.sin(2*np.pi*(root/2)*t)
        for start in np.arange(0,seconds,3.2):
            length=min(4.,seconds-start);note_t=np.arange(round(length*RATE))/RATE
            freq=root*2**(int(rng.choice([0,2,3,7,10]))/12)
            attack=np.minimum(note_t/.035,1)
            signal=.035*(np.sin(2*np.pi*freq*note_t)+.15*np.sin(4*np.pi*freq*note_t))*attack*np.exp(-note_t/1.1)
            a=round(start*RATE);b=min(n,a+len(signal));audio[a:b]+=signal[:b-a]
        for start in np.arange(0,seconds,2.4):
            drum_t=np.arange(round(min(.45,seconds-start)*RATE))/RATE
            phase=2*np.pi*(65*drum_t+30*.05*(1-np.exp(-drum_t/.05)))
            drum=.022*np.sin(phase)*np.minimum(drum_t/.008,1)*np.exp(-drum_t/.09)
            a=round(start*RATE);b=min(n,a+len(drum));audio[a:b]+=drum[:b-a]
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
        key=s['chapter']
        if cues and cues[-1]['chapter']==key:
            cues[-1]['end']=s['end'];continue
        cues.append({'start':s['start'],'end':s['end'],'chapter':s['chapter'],
            'mood':'reflective','style':'historical_documentary','intensity':.35,'fade':1.5,'ducking':True})
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
