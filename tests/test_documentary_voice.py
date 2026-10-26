from types import SimpleNamespace
from contextlib import nullcontext
from unittest.mock import Mock
import numpy as np
from somoy_jatri.narration.providers import IndicParlerTTS


def test_production_adapter_uses_same_delivery_for_all_scene_emotions(monkeypatch,tmp_path):
    voice=IndicParlerTTS.__new__(IndicParlerTTS)
    voice.named_voice=False
    inputs=SimpleNamespace(input_ids='ids',attention_mask='mask')
    voice.description=Mock(return_value=inputs)
    voice.tokenizer=Mock(return_value=inputs)
    audio=Mock(); audio.cpu.return_value.numpy.return_value=np.ones(20,dtype=np.float32)*.1
    voice.model=Mock();voice.model.generate.return_value=audio
    voice.model.config.sampling_rate=24000
    voice.torch=SimpleNamespace(random=SimpleNamespace(fork_rng=lambda **kw:nullcontext()),
        inference_mode=nullcontext,manual_seed=Mock())
    for emotion,intensity in [('amazed',1),('soft',.1)]:
        voice.synthesize('প্রাচীন ইতিহাস।',emotion,intensity,tmp_path/f'{emotion}.wav')
    assert voice.description.call_args_list[0]==voice.description.call_args_list[1]
    assert voice.model.generate.call_args_list[0]==voice.model.generate.call_args_list[1]
    assert voice.model.generate.call_args.kwargs['do_sample'] is False
    assert [call.args for call in voice.torch.manual_seed.call_args_list]==[(1729,),(1729,)]
