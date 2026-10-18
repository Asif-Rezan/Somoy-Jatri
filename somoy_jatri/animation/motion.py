def filter_for(motion, frames, width, height, fps):
    x="iw/2-(iw/zoom/2)";y="ih/2-(ih/zoom/2)";z='1.04'
    if motion in {'slow_forward','zoom'}: z=f'1.02+0.06*on/{frames}'
    elif motion=='slow_backward': z=f'1.08-0.06*on/{frames}'
    elif motion=='pan_right': x=f'(iw-iw/zoom)*on/{frames}'
    elif motion=='pan_left': x=f'(iw-iw/zoom)*(1-on/{frames})'
    elif motion=='tilt_up': y=f'(ih-ih/zoom)*(1-on/{frames})'
    elif motion=='handheld': x+=' + 2*sin(on/18)';y+=' + sin(on/23)'
    return f"scale={width*2}:{height*2},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps},setsar=1,format=yuv420p"
