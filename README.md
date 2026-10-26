# Somoy Jatri — বাংলা ঐতিহাসিক তথ্যচিত্র

Bangla historical documentaries following the chapter-based CPU generation process in
`Asif-Rezan/youtube-dark-psychology-automation`, adapted to sourced history and Bangla.
Twenty chapters, four narration batches, duration correction, timed images, captions,
and continuous ducked MusicRNN music follow the reference structure.

Narration uses an objective third-person documentary register with no vlog host,
fictional time travel, or scene-dependent voice/emotion changes. New chapter stories use
`reference-chapters-documentary-v2`; start a fresh episode to replace older vlog scripts.
Voice receipts include the delivery version so previous narration is regenerated.

The production voice is Microsoft Edge's online **bn-BD-NabanitaNeural** narrator,
a fixed Bangladesh Bangla female voice at a slightly slower rate (-8%), neutral pitch,
and fixed volume. Install `requirements-voice.txt`. Narration text is sent to the
online service; no API key is required. Service failures retry three times and
stop clearly, with no automatic switch to a different voice. Audio is converted
to 24 kHz mono WAV and cached per chapter. Switching from local narration invalidates
old voice receipts. Listen to the production sample before judging pronunciation.

The earlier local Parler adapter remains an explicit opt-in via
`TTS_BACKEND=indic-parler` plus `requirements-tts.txt`; it is no longer the production
default. Its public Bangla fine-tune has no named-speaker control. All adapters
ignore legacy scene emotion fields.

MusicRNN retries sparse/invalid continuations up to five times with increasing
sampling variety before failing clearly. It writes notes atomically and never fills
missing music with silence or a repeated loop.

## Production pipeline

1. Install the reference's pinned local **Qwen3-4B-Instruct-2507 Q4_K_M** CPU
   Python wheel and verify real grammar-constrained Bengali generation. No
   llama.cpp server build or hosted text API is needed.
2. Verify the Bengali production voice before full generation.
3. **Stage story:** select curated sourced historical anchors, generate one
   concise twenty-chapter outline, then four batches of five Bangla narrations,
   followed by publishing metadata. Chapter word counts have bounded grammar
   constraints and at most three retries. No repeated semantic-repair loop runs.
4. **Prepare:** cache one audio asset per chapter. Bounded text chunks
   keep narration requests short. Measure actual duration and rewrite
   only selected chapters if needed; resynthesize only changed chapters. Tempo
   correction is capped at 4%, and there are at most three duration corrections.
5. Cache multilingual Bengali Whisper word timestamps by audio/text hashes.
   Derive the seven-second visual windows from the measured narration.
6. **Storyboard:** request eight exact timed image prompts per batch, checkpoint
   each batch and reuse completed work. **Refine plan:** verify coverage and bind
   story, audio, captions and timeline with checksums.
7. Twenty CPU workers generate SSD-1B images at 1024×576, 16 steps/guidance 9.
   The final H.264/AAC video includes Bengali captions, packaging and a continuous
   MusicRNN soundtrack with fades and speech ducking. Music does not switch at
   chapter boundaries.
8. QC, private Drive checkpoints, guarded private YouTube uploads and verified
   cleanup retain their account identity and duplicate-upload protections.

The duration stays 600–900 seconds and images change every seven seconds.
The preparation job allows **240 minutes** for the Bengali speech adapter; the
English reference allows 150. This is a failure deadline, not a generation target
or speed control. The same bounded preparation sequence runs; Bengali CPU speech
can still be slow.

[Model details](docs/models.md). Structural/schema validation is not a claim of
historical accuracy or semantic agreement. The reference process does not run
an independent model review for every utterance. Review private output before
wider release; curated automatically selected research remains private-only.

## Local preview

Use Python 3.11+, FFmpeg/ffprobe with libx264 and libass, fontconfig and Pillow
with RAQM/HarfBuzz. Noto Sans Bengali is bundled under SIL OFL.

```bash
pip install -e '.[test]'
python -m pytest -q
python -m somoy_jatri.cli preview --run-id preview
```

The short preview uses labelled mock images and tone fixtures, and cannot upload.
Review `output/preview/video.mp4`, `thumbnail.jpg`, `captions.srt` and `qc.json`.

## Setup and Actions

Keep these repository-specific secrets: `DRIVE_TOKEN_JSON`, `DRIVE_FOLDER_ID`
and `YOUTUBE_TOKEN_JSON`. Configure `EXPECTED_CHANNEL_ID` and
`EXPECTED_DRIVE_EMAIL` as repository variables. The private Drive root must carry
the `somoy_jatri_root=v1` marker. Do not copy reference-project credentials or
channel/folder IDs. Optional Hugging Face authentication uses `HF_TOKEN`.

1. Run **Verify Google connections** to verify account identity, private storage
   and a checkpoint write/read round trip.
2. Run **Verify local Qwen Bangla generation** and production **Model component
   test** for voice, image and music.
3. Run **Generate episode and optional private upload**, using production mode,
   `dossier=auto`, target 720, workers 20 and `preview_only=true` to review output.
4. Set `preview_only=false` for a private upload. The existing daily schedule
   requests private generation at **06:00 Asia/Dhaka**.

Automatic research selects curated factual anchors and source links from eleven
topics, avoiding the last ten reserved topics. Source IDs and schemas are checked;
these anchors are not represented as a new live source extraction or human review. Automatically sourced
episodes cannot upload publicly or unlisted. Human-reviewed research and explicit
public opt-in are required for public upload.

Local production preparation also needs `pip install -r requirements-tts.txt`,
`pip install -r requirements-story.txt`. The same local Python model is reused
within each process; downloaded weights are reused by the runner's cache.
Image workers need `pip install -e '.[images]'`; final rendering needs
`npm install --ignore-scripts --no-audit --no-fund @magenta/music@1.23.1`.
Export settings explicitly: `.env` is not loaded automatically.

Groq and Gemini are optional legacy diagnostic backends. They are not required
for daily text generation or Google readiness. Deliberately select a legacy
backend with `TEXT_BACKEND=groq`; use `STORY_PROVIDER=gemini` for Gemini.
Multilingual local alignment is the default when alignment is requested.

## Recovery

Use **Resume prepared episode and upload privately** for completed narration,
**Recover, verify upload or clean a saved episode → prepare** for interrupted
chapter preparation, or
**Recover, verify upload or clean a saved episode** for saved checkpoints. Always
keep the original episode run ID. For older utterance-format runs, use **Resume voice in parallel and upload privately**.
Preparation and per-shard checkpoints have
separate names; restore them into that same run. Actions artifacts last 14 days.

An ambiguous YouTube insertion must be reconciled with the real video ID before
retrying; it cannot silently insert another video. **Resume verified private
Drive cleanup** only verifies an existing private HD upload and removes tagged
run media. It never generates or inserts a video. Scripts, research, timing,
captions, metadata and upload journals are retained.

Large CPU models can exhaust runner memory or time. Use retained checkpoints
rather than discarding successful work. Source websites can change and must
remain verifiable. No automated check proves historical image accuracy or voice
quality; full private upload verification is distinct from offline tests.
