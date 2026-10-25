# Reference alignment — 2026-10-25

Compared against `Asif-Rezan/youtube-dark-psychology-automation` at
`85b67a9bd990cae4169c30807cf0b8662ec649ba`. The reference repository was read only.

Somoy Jatri now uses the same pinned Qwen3.5-9B Q4_K_M local text model,
llama.cpp revision, loopback-only inference and disabled thinking. Research,
scripts, semantic review, packaging and duration revisions use this backend by
default. There is no automatic cloud text fallback from Qwen. Explicit legacy
Groq/Gemini diagnostics remain available. Groq is no longer a Google readiness
requirement, and alignment defaults to local multilingual Whisper.

Images match SSD-1B, 1024×576, 16 steps, guidance 9, seven-second slots and twenty
CPU workers. Production music uses the reference Magenta basic_rnn and historical
instrument renderer, generating independent sections instead of repeating a loop.
Mock previews keep lightweight procedural audio. Packaging uses accurate Bangla
titles, complementary short questions and a left-text/right-art thumbnail layout.

Language-specific differences are deliberate: Kokoro's reference English voice
and Whisper base.en cannot provide Bengali narration and transcription. Somoy
Jatri retains `Tanmoyshome/bn-parler-tts` and multilingual Whisper small with
language `bn`. Existing emotion metadata, measured utterances, source citation
checks and first-person time-travel framing remain. No English model is silently
used for Bengali speech. Model defaults are documented in docs/models.md.

The topic catalog now covers the reference subjects and excludes the last ten
reserved topics when choosing the next episode.

Existing private uploads, channel/folder identity guards, per-run checksums,
Drive retries, independent image jobs, resumable preparation, recovery and
verified cleanup are retained. Credentials and channel/folder IDs are not copied
from the reference repository. Recovery paths install MusicRNN when assembling
production output; voice recovery starts Qwen when revalidating the storyboard.

Failures observed: repeated preparation connection checks stopped at Groq HTTP
errors; an earlier run exhausted rate limits during generation; offline checks
failed because the music variety gate disagreed with the chapter-level score.
The Google check now reports the failing service and HTTP status without dumping
credential-bearing exceptions. The music gate checks chapter boundaries.

A passing offline preview does not establish live model quality or a completed
private YouTube upload. Large CPU models can hit runner memory or time limits;
production uploads must still pass all existing validation and identity guards.
