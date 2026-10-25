# Models — 2026-10-25

| Stage | Production default | Reference relationship |
|---|---|---|
| Text, research, storyboard, packaging | Qwen/Qwen3.5-9B via pinned Q4_K_M GGUF and local llama.cpp | Same model/runtime pins |
| Illustration | segmind/SSD-1B, CPU float32, 1024×576, 16 steps, guidance 9 | Same model/settings |
| Music | Magenta MusicRNN basic_rnn, @magenta/music 1.23.1, CPU | Same model/instrument renderer |
| Bangla voice | Tanmoyshome/bn-parler-tts via pinned Parler library | Bengali replacement for English Kokoro |
| Caption transcription | faster-whisper 1.2.1, multilingual small, CPU int8, language bn | Bengali replacement for base.en |

`TEXT_BACKEND=qwen-local` is the default. Qwen errors stop generation without
cloud fallback. To deliberately exercise old cloud integrations set
`TEXT_BACKEND=groq`, optionally `STORY_PROVIDER=gemini`. Local alignment is the
default even if a Groq key exists; `ALIGNMENT_BACKEND=groq` is an explicit opt-in.

The Bengali voice default is the existing public model, not the gated Indic
Parler model described in older documentation. `TTS_MODEL=ai4bharat/indic-parler-tts`
remains optional and needs authorized Hugging Face access. Voice quality, accent
and historical reconstruction accuracy still require listening/viewing review.

Sources: [Qwen weights](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF),
[SSD-1B](https://huggingface.co/segmind/SSD-1B),
[Bangla Parler](https://huggingface.co/Tanmoyshome/bn-parler-tts),
[Kokoro](https://huggingface.co/hexgrad/Kokoro-82M),
[Indic Parler](https://huggingface.co/ai4bharat/indic-parler-tts),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper).
