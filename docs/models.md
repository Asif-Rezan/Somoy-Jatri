# Models — 2026-10-26

| Stage | New production default |
|---|---|
| Outline, narration, packaging and timed storyboards | Qwen/Qwen3-4B-Instruct-2507, local CPU via llama-cpp-python 0.3.36 |
| Quantized weights | unsloth/Qwen3-4B-Instruct-2507-GGUF, Q4_K_M, revision a06e946bb6b655725eafa393f4a9745d460374c9 |
| Weight SHA-256 | 3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597 |
| Runtime | 16,384-token context, at most four CPU threads, reused per process; no external text API |
| Illustration | segmind/SSD-1B, CPU float32, 1024×576, 16 steps, guidance 9 |
| Music | Magenta MusicRNN basic_rnn, @magenta/music 1.23.1, CPU |
| Bangla voice | Microsoft Edge online bn-BD-PradeepNeural, fixed rate -8%, neutral pitch, cached per chapter |
| Word alignment | faster-whisper 1.2.1, multilingual base, CPU int8, language bn, two threads, beam size 3 |

The first four rows follow the chapter preparation process from
`Asif-Rezan/youtube-dark-psychology-automation`. Explicit
JSON schemas constrain local generation and are validated again in Python.
Incomplete output has at most three attempts. Model identity, checksum or context
errors stop without cloud fallback. English-only word regexes, Kokoro narration
and base.en are replaced with Bengali-compatible adapters.

`PREPARATION_PROCESS=after-dark` selects fresh chapter preparation. Old saved
utterance-format artifacts retain their legacy Qwen3.5-9B/Groq/Gemini recovery
utilities; these are not used by fresh production preparation.

Production music is continuous through the episode, with opening/closing fades
and narration ducking. It does not switch at chapter boundaries. Bengali voice
quality, pronunciation and historical reconstruction accuracy need private
listening/viewing review; a schema/audio check cannot establish those qualities.

New narration is objective third-person history, with no first-person vlog host.
Bangla speech uses Microsoft Edge's online `bn-BD-PradeepNeural` male narrator,
with fixed rate (-8%), pitch (+0 Hz), and volume (+0%). Install
`requirements-voice.txt`. This sends narration text to the online service and
requires network access, but no API key. Three failed service attempts stop
without switching speakers. The local Parler adapter remains opt-in using
`TTS_BACKEND=indic-parler` and `requirements-tts.txt`.

See [Microsoft's voice list](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
and the [Edge TTS client](https://github.com/rany2/edge-tts).

Voice cache receipts include the backend, voice, rate and `online-documentary-v1` and new chapter scripts use
`reference-chapters-documentary-v2`. Start a new episode rather than resuming an
old vlog story. MusicRNN rejects sparse/invalid continuations with at most five
independent sampling attempts; it never substitutes silence or repeated loops.
