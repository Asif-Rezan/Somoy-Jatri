import argparse
import json
import os
import time
from pathlib import Path
from somoy_jatri.config import Config
from somoy_jatri.utils import load,save


def main():
    p=argparse.ArgumentParser(description='Somoy Jatri — historical reconstruction pipeline')
    p.add_argument('command',choices=['prepare','images','finish','preview','tts-test','image-test',
        'music-test','upload','backup','restore','cleanup','drive-init','reconcile'])
    p.add_argument('--resume',action='store_true',help='Reuse saved configuration for preparation')
    p.add_argument('--mode',choices=['mock','production'],default='mock')
    p.add_argument('--run-id',default='preview');p.add_argument('--workers',type=int,default=4)
    p.add_argument('--shard',type=int,default=0);p.add_argument('--target',type=int,default=720)
    p.add_argument('--topic',default='');p.add_argument('--period',default='')
    p.add_argument('--no-captions',action='store_true');p.add_argument('--no-music',action='store_true')
    p.add_argument('--privacy',default='private');p.add_argument('--video-id');p.add_argument('--snapshot',default='checkpoint')
    args=p.parse_args();start=time.monotonic()
    config=Config(args.mode,args.run_id,args.workers,not args.no_captions,not args.no_music,args.target)
    root=config.root
    if (args.command not in {'prepare','preview','drive-init'} or (args.command=='prepare' and args.resume)) and (root/'config.json').exists():
        config=Config(**load(root/'config.json'))
        if config.run_id!=args.run_id:raise ValueError('Saved run identity mismatch')
    from somoy_jatri.pipeline import prepare,finish
    if args.command=='prepare': prepare(config,args.topic,args.period)
    elif args.command=='preview':
        if config.mode!='mock':raise ValueError('Use separate stages for production')
        shots=prepare(config)
        from somoy_jatri.images.providers import generate_shard
        for i in range(config.workers):generate_shard(root,shots,i,config.workers,'mock')
        finish(config)
    elif args.command=='images':
        from somoy_jatri.images.providers import generate_shard
        generate_shard(root,load(root/'timeline.json'),args.shard,config.workers,config.mode)
    elif args.command=='finish':finish(config)
    elif args.command=='tts-test':
        from somoy_jatri.narration.providers import provider
        from somoy_jatri.narration.providers import synthesize_measured
        from somoy_jatri.audio import concatenate
        from somoy_jatri.narration.text import normalize
        root.mkdir(parents=True,exist_ok=True);tts=provider(args.mode);parts=[]
        for i,(text,emotion) in enumerate([
            ('বন্ধুরা, আমরা কি সত্যিই প্রাচীন মিশরে এসে পড়েছি?', 'curious'),
            ('ওই দেখো! সামনে গিজার বিশাল পিরামিড!', 'amazed'),
            ('ভাবতেই অবাক লাগছে, খ্রিস্টপূর্ব ২৫০০ সালে জীবন কত আলাদা ছিল।','reflective')]):
            path=root/f'voice-{i}.wav'
            if args.mode=='production':
                result=synthesize_measured(tts,{'text':normalize(text),'emotion':emotion,'intensity':.6},path)
                print(json.dumps({'voice_stage':'audio_checked','index':i,'seconds':result['seconds']}),flush=True)
            else:tts.synthesize(normalize(text),emotion,.6,path)
            parts.append((path,500))
        concatenate(parts,root/'voice-test.wav')
    elif args.command=='image-test':
        from somoy_jatri.images.providers import SSDImages,MockImages
        from somoy_jatri.pipeline import mock_story
        from somoy_jatri.storyboard.timeline import build
        root.mkdir(parents=True,exist_ok=True)
        shot={'id':'test','subject':'pottery merchant','prompt':'Pottery merchant at Giza, c.2500 BCE, first-person POV photorealistic documentary, linen garments, mudbrick stalls, natural light','negative_prompt':'modern objects, anime, cartoon'}
        (MockImages() if args.mode=='mock' else SSDImages()).generate(shot,root/'image-test.png')
    elif args.command=='music-test':
        from somoy_jatri.music.scoring import score
        from somoy_jatri.audio import write_wav
        root.mkdir(parents=True,exist_ok=True)
        cues=[dict(start=i*8,end=(i+1)*8,mood=m,style='ambient',fade=1.5) for i,m in enumerate(['amazed','curious','reflective'])]
        if args.mode == 'production':
            from somoy_jatri.music.scoring import MusicRNN
            audio = MusicRNN(root).compose(24,cues)
        else:
            audio = score(cues,24)
        write_wav(root/'music-test.wav',audio)
    elif args.command=='drive-init':
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        client=build('drive','v3',credentials=Credentials.from_authorized_user_info(json.loads(os.environ['DRIVE_TOKEN_JSON'])))
        folder=client.files().create(body={'name':'Somoy Jatri — Private Checkpoints',
            'mimeType':'application/vnd.google-apps.folder','appProperties':{'somoy_jatri_root':'v1'}},fields='id').execute()
        print(json.dumps({'DRIVE_FOLDER_ID':folder['id']}))
    elif args.command in {'backup','restore','cleanup'}:
        from somoy_jatri.storage.drive import Store
        from somoy_jatri.storage import safety
        store=Store() if os.getenv('DRIVE_FOLDER_ID') else None
        if args.command!='cleanup' and not store:raise ValueError('Separate Drive configuration required')
        getattr(safety,args.command)(root,store,**({'snapshot':args.snapshot} if args.command!='cleanup' else {}))
    elif args.command=='upload':
        from somoy_jatri.youtube.publish import upload
        persist=None
        if os.getenv('DRIVE_FOLDER_ID'):
            from somoy_jatri.storage.drive import Store
            store=Store();persist=lambda path:store.upload(path,f'runs/{config.run_id}/upload.json')
            remote=store.load(f'runs/{config.run_id}/upload.json',None)
            if remote:save(root/'upload.json',remote)
        upload(root,args.privacy,persist=persist)
    elif args.command=='reconcile':
        from somoy_jatri.youtube.publish import service,identity
        if not args.video_id:raise ValueError('--video-id required after manual YouTube Studio inspection')
        state=load(root/'upload.json');client=service();channel=identity(client)
        video=client.videos().list(part='snippet,status',id=args.video_id).execute()['items']
        metadata=load(root/'metadata.json')
        if len(video)!=1 or video[0]['snippet']['channelId']!=channel or video[0]['snippet']['title']!=metadata['title']:
            raise ValueError('Reconciliation identity mismatch')
        state.update(video_id=args.video_id,phase='uploaded',privacy=video[0]['status']['privacyStatus']);save(root/'upload.json',state)
        if os.getenv('DRIVE_FOLDER_ID'):
            from somoy_jatri.storage.drive import Store
            Store().upload(root/'upload.json',f'runs/{config.run_id}/upload.json')
    import resource
    print(json.dumps({'stage':args.command,'mode':config.mode,'run':config.run_id,
        'seconds':round(time.monotonic()-start,2),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))

if __name__=='__main__':
    try:main()
    except Exception as error:
        # SDK errors can include bearer tokens or resumable URLs. Never dump them in CI.
        print(json.dumps({'passed':False,'error_type':type(error).__name__,
            'hint':'Check configuration and retained manifests; authentication details are suppressed.'}))
        raise SystemExit(1)
