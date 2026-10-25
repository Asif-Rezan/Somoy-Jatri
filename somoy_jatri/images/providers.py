import hashlib
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageStat
from typing import Protocol
from somoy_jatri.utils import digest, save, load

class ImageProvider(Protocol):
    def generate(self, shot: dict, path: Path) -> None: ...

class MockImages:
    def generate(self, shot, path):
        image = Image.new('RGB', (640,360), (32,47,65))
        d = ImageDraw.Draw(image)
        seed = int(hashlib.sha256(shot['id'].encode()).hexdigest()[:6],16)
        for x in range(0,640,80):
            h = 70+(seed+x)%160
            d.rectangle((x,360-h,x+60,360), fill=(130+x//8,105,60))
        d.text((25,25), 'MOCK FIXTURE - NOT HISTORICAL FOOTAGE', fill='white')
        d.text((25,55), shot['subject'], fill='white')
        image.save(path)

class SSDImages:
    def __init__(self):
        import torch
        from diffusers import DiffusionPipeline, DPMSolverMultistepScheduler
        self.torch = torch
        torch.set_num_threads(int(os.getenv('CPU_THREADS','2')))
        self.pipeline = DiffusionPipeline.from_pretrained(os.getenv('CPU_IMAGE_MODEL','segmind/SSD-1B'),
            revision=os.getenv('CPU_MODEL_REVISION','60987f37e94cd59c36b1cba832b9f97b57395a10'),
            torch_dtype=torch.float32, use_safetensors=True, trust_remote_code=False).to('cpu')
        self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(self.pipeline.scheduler.config, algorithm_type='dpmsolver++', use_karras_sigmas=True)
        self.pipeline.enable_attention_slicing(); self.pipeline.enable_vae_slicing()

    def generate(self, shot, path):
        w,h = int(os.getenv('CPU_IMAGE_WIDTH','1024')),int(os.getenv('CPU_IMAGE_HEIGHT','576'))
        if w%8 or h%8 or w<256 or h<256 or w>1536 or h>1536: raise ValueError('Image dimensions')
        seed = int(hashlib.sha256(shot['id'].encode()).hexdigest()[:8],16)
        # Preserve the assigned subject on retries; never silently substitute an unrelated empty scene.
        result = self.pipeline(prompt=shot['prompt'], negative_prompt=shot['negative_prompt'],
            width=w, height=h, guidance_scale=float(os.getenv('CPU_IMAGE_GUIDANCE', '9')), num_inference_steps=int(os.getenv('CPU_IMAGE_STEPS','16')),
            generator=self.torch.Generator('cpu').manual_seed(seed))
        if any(getattr(result,'nsfw_content_detected',None) or []):
            raise RuntimeError('Image rejected; preserve run for review')
        result.images[0].save(path)


def verify(path):
    with Image.open(path) as im:
        im.load()
        if abs(im.width/im.height-16/9) > .03: raise ValueError('Image aspect ratio')
        if max(ImageStat.Stat(im.convert('RGB')).stddev) < 1: raise ValueError('Blank image')


def generate_shard(root, shots, index, count, mode):
    from somoy_jatri.storyboard.timeline import shard
    provider = None
    for shot in shard(shots,index,count):
        path = root/'images'/(shot['id']+'.png'); path.parent.mkdir(exist_ok=True)
        stamp = path.with_suffix('.json')
        prompt_hash = hashlib.sha256(shot['prompt'].encode()).hexdigest()
        if path.exists() and stamp.exists():
            record=load(stamp)
            if record.get('prompt_hash')==prompt_hash and record.get('sha256')==digest(path):
                verify(path); continue
        provider = provider or (MockImages() if mode=='mock' else SSDImages())
        for attempt in range(3):
            try:
                provider.generate(shot,path); verify(path); break
            except Exception:
                path.unlink(missing_ok=True)
                if attempt==2: raise
        save(stamp, {'sha256':digest(path), 'prompt_hash':prompt_hash})
