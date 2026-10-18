import math
from somoy_jatri.utils import run, probe
from somoy_jatri.animation.motion import filter_for


def clip_command(image,output,seconds,motion,width,height,fps):
    frames=math.ceil(seconds*fps)
    return ['ffmpeg','-v','error','-y','-i',image,'-vf',filter_for(motion,frames,width,height,fps),
        '-frames:v',frames,'-an','-c:v','libx264','-preset','fast','-crf','21','-threads','2',output]


def render(root,shots,captions=True,mock=False):
    width,height=(640,360) if mock else (1920,1080);fps=30
    clips=root/'clips';clips.mkdir(exist_ok=True)
    # Round cumulative boundaries, not each duration: limits accumulated A/V error to one frame.
    names=[]
    for s in shots:
        path=clips/(s['id']+'.mp4')
        frames=round(s['end']*fps)-round(s['start']*fps)
        run(clip_command(root/'images'/(s['id']+'.png'),path,frames/fps,s['motion'],width,height,fps))
        names.append("file '"+path.resolve().as_posix()+"'")
    listing=root/'clips.txt';listing.write_text('\n'.join(names)+'\n')
    command=['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',listing,'-i',root/'mix.wav']
    if captions:
        # Fixed safe filename and cwd avoid filter escaping user-provided paths.
        ass=root/'captions.ass'
        escaped=str(ass.resolve()).replace('\\','/').replace(':','\\:').replace("'","\\'")
        command+=['-vf',f"ass=filename='{escaped}':fontsdir='{str(__import__('pathlib').Path(__file__).resolve().parents[2]/'assets/fonts')}'",'-c:v','libx264','-preset','fast','-threads','2']
    else: command+=['-c:v','copy']
    command+=['-c:a','aac','-b:a','192k','-t',str(shots[-1]['end']),'-movflags','+faststart',root/'video.mp4']
    run(command)
    return root/'video.mp4'
