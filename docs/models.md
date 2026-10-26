# Models — 2026-10-26

| Stage | New production default |
|---|---|
| Outline, narration, packaging and timed storyboards | Qwen/Qwen3-4B-Instruct-2507, local CPU via llama-cpp-python 0.3.36 |
| Quantized weights | unsloth/Qwen3-4B-Instruct-2507-GGUF, Q4_K_M, revision a06e946bb6b655725eafa393f4a9745d460374c9 |
| Weight SHA-256 | 3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597 |
| Runtime | 16,384-token context, at most four CPU threads, reused per process; no external text API |
| Illustration | segmind/SSD-1B, CPU float32, 1024×576, 16 steps, guidance 9 |
| Music | Magenta MusicRNN basic_rnn, @magenta/music 1.23.1, CPU |
| Bangla voice | Tanmoyshome/bn-parler-tts via pinned Parler library, bounded internal text chunks assembled/cached per chapter |
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
Bangla speech uses one fixed male/moderate/clear description and greedy decoding;
scene emotion fields are ignored. The ungated fine-tune cannot guarantee speaker
identity across different texts. For named-speaker conditioning the optional
`ai4bharat/indic-parler-tts` adapter defaults to recommended Bengali speaker Arjun;
it requires accepted model access terms and a runner token. See the
[Bangla model card](https://huggingface.co/Tanmoyshome/bn-parler-tts) and
[Indic speaker list](https://huggingface.co/ai4bharat/indic-parler-tts).

Voice cache receipts include `bangla-documentary-v2` and new chapter scripts use
`reference-chapters-documentary-v2`. Start a new episode rather than resuming an
old vlog story. MusicRNN rejects sparse/invalid continuations with at most five
independent sampling attempts; it never substitutes silence or repeated loops.
