"""Original synthetic wind/water textures; licensed field recordings are optional."""
import numpy as np
from somoy_jatri.audio import RATE, read_wav


def render(shots,total,catalog=None):
    output=np.zeros(round(total*RATE),dtype=np.float32)
    rng=np.random.default_rng(107)
    for s in shots:
        a=round(s['start']*RATE);b=round(s['end']*RATE);n=b-a
        profile=s.get('ambient','wind')
        if catalog and profile in catalog:
            item=catalog[profile]
            if not item.get('license') or not item.get('source'): raise ValueError('Unlicensed ambient asset')
            sound=read_wav(item['path'])
            if len(sound)<n: raise ValueError('Ambient asset shorter than scene')
            sound=sound[:n]
        elif profile in {'wind','river','outdoor'}:
            noise=rng.normal(0,.15,n)
            sound=np.convolve(noise,np.ones(80)/80,mode='same')
            if profile=='river': sound*=2
        else:
            # Never fake realistic crowds/animals with unrelated or unlicensed recordings.
            sound=np.zeros(n)
        f=min(RATE//3,n//2)
        sound[:f]*=np.linspace(0,1,f);sound[-f:]*=np.linspace(1,0,f)
        output[a:b]+=sound
    return output
