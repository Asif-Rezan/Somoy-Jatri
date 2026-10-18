# Implementation report

Implemented in `Asif-Rezan/Somoy-Jatri`; the reference repository was read only.

- Created modular Python stages for research validation, topic history, Groq scripts, Bangla normalization and emotional directions, named female Indic Parler voice, Bengali ASR, semantic storyboard, SSD-1B CPU shards, continuity prompts, FFmpeg motion/composition, Bangla captions/thumbnail, music/ambience, QC, Drive recovery, safe cleanup and guarded YouTube uploads.
- Added `pyproject.toml`, `.env.example`, optional voice dependencies, bundled OFL Bengali font, five workflow files, OAuth helper, README and model/reference documentation.
- Selected Indic Parler/Aditi for documented Bengali and descriptive emotion support; live gender, Bangladesh accent, pronunciation, emotion and CPU performance are unverified. Conceptual intensity is not passed as an invented model control.
- Timings come from actual synthesized utterance audio and pauses; Bengali ASR validates agreement and refines word times. No seven-second image interval exists.
- Original procedural music varies by chapter/mood, with fades and voice gain automation; it is not trained music generation. Synthetic wind/water provided. Realistic market/horse/workshop recordings require a licensed catalog.
- Local validation: 26 tests pass; short real FFmpeg MP4 rendered; representative frame inspected with correctly shaped Bengali captions. YAML parses and all workflow shell snippets pass `bash -n`. These are local checks, not live Actions/model/API results.
- Remaining: real TTS and multilingual ASR integration; SSD-1B CPU image/runtime/memory test; Groq script/semantic output; evidence-reviewed dossiers; perceptual audio/history review; authenticated Drive and private YouTube test; actual hosted Actions execution.
- Limits: manually reviewed source dossiers; prompt-based visual continuity; no depth motion or image crossfades; peak normalization rather than LUFS certification; no automatic ambiguous-upload session continuation. Production readiness is not claimed.

Required secrets: `GROQ_API_KEY`, `HF_TOKEN` when gated access requires it, `YOUTUBE_TOKEN_JSON`, `DRIVE_TOKEN_JSON`, `DRIVE_FOLDER_ID`; optional daily dispatcher `WORKFLOW_DISPATCH_TOKEN`. Variable `EXPECTED_CHANNEL_ID` is required before upload. Scheduling and public visibility remain disabled by default.

First private test: run offline preview; run production TTS/image component checks and listen/review; add separate OAuth/Drive configuration and reviewed research; run Generate episode with production mode and preview_only=true; inspect final artifact; then run with private visibility and preview_only=false. Re-run recovery/upload after processing to verify the existing ID, then clean. See README for exact commands and settings.
