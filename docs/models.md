# Model evaluation and integration status — 2026-10-18

Documentation checked before implementation; no live inference benchmarks were run.

| Candidate | Verified upstream facts | Decision |
|---|---|---|
| AI4Bharat Indic Parler-TTS | Bengali supported; Bengali named speakers; descriptive emotion/prosody controls; Apache-2.0 model card; gated access notice | Initial replaceable CPU provider, Aditi plus female description. CPU latency, accent, perceived gender and emotion need listening/benchmarking. |
| Meta MMS-TTS Bengali | Bengali VITS checkpoint; CC-BY-NC 4.0 | Not selected for monetized YouTube default; no verified female/emotion control. |
| XTTS v2 | Bengali support not established in evaluated material | Not integrated; no unsupported-language claims. |
| Tanmoyshome/bn-parler-tts | Model card describes Bengali female/male prompts; fine emotion and named voice not supported | Not selected over named upstream speaker; dataset/license and consistency need evaluation. |
| AI4Bharat Indic-Speak | Current Parler card points to this newer alternative | Future evaluation; not silently substituted for the documented provider API. |
| segmind/SSD-1B | SDXL-derived distilled image pipeline; upstream model license applies | Selected as requested; locally executed CPU float32; practical runner memory/time unmeasured. |
| faster-whisper multilingual small | Whisper Bengali language; word timestamp API and CPU int8 inference | Script agreement gate plus timestamp refinement; not forced-alignment proof. |

Sources:
- https://huggingface.co/ai4bharat/indic-parler-tts
- https://huggingface.co/facebook/mms-tts-ben
- https://huggingface.co/Tanmoyshome/bn-parler-tts
- https://huggingface.co/segmind/SSD-1B (review its current license before distribution/use)
- https://github.com/SYSTRAN/faster-whisper
- https://github.com/openai/whisper/blob/main/whisper/tokenizer.py

Emotion tags are conceptual directions. The numeric intensity is metadata, not an invented strength parameter. Descriptive prompts are only as reliable as the selected model. Bengali support does not establish a natural Bangladesh accent. Listen to the test fixtures before a full generation run.

To replace TTS, implement `BanglaTTSProvider.synthesize(text, emotion, intensity, path)` and select it explicitly in `provider()`. The pipeline decodes its WAV to 24 kHz mono, measures duration, and runs Bengali ASR. Add model license/source information and an integration test. Never silently fall back to English speech or mock audio in production.
