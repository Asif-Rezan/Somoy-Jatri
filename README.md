# Somoy Jatri — বাংলা সময়ভ্রমণ

**ইতিহাস শুধু শুনব না, নিজের চোখে দেখব!**

A Bangla historical time-travel video pipeline aligned with
`Asif-Rezan/youtube-dark-psychology-automation` at commit `85b67a9`.
The reference repository is unchanged. See [reference comparison](docs/reference-analysis.md).

## Production pipeline

- Local **Qwen3.5-9B Q4_K_M** writes research packets, original Bangla scripts,
  storyboard reviews and packaging. The pinned loopback llama.cpp server has
  thinking disabled. Qwen failures stop generation without a cloud fallback.
- **Bengali Parler** narrates short utterances. Measured audio receipts and content
  hashes prevent stale or silent takes. Duration recovery targets 600–900 seconds.
  English Kokoro is not used for Bengali speech.
- **SSD-1B** creates 1024×576 historical illustrations at 16 steps/guidance 9,
  with the reference scheduler. A new image appears every seven seconds.
  Twenty independent CPU image workers are requested by default.
- **Magenta MusicRNN** generates one continuous historical instrumental soundtrack.
  It does not switch at chapter boundaries. Music fades and ducks under narration.
- Bengali captions, source-linked Bangla descriptions, Bangla titles and short
  thumbnail questions accompany 1080p H.264/AAC output.
- QC, private Drive checkpoints, guarded private YouTube uploads and verified
  cleanup preserve the existing recovery and duplicate-upload protections.

[Bengali voice and model details](docs/models.md). Passing automated checks does
not certify pronunciation, accent, historical imagery or editorial quality.
Review the output before wider release.

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

Automatic research selects from eleven curated topics, avoiding the last ten
reserved topics, and checks source excerpts and citations. Automatically sourced
episodes cannot upload publicly or unlisted. Human-reviewed research and explicit
public opt-in are required for public upload.

Local production preparation also needs `pip install -r requirements-tts.txt`,
`pip install 'huggingface-hub>=0.34,<1'` and `bash scripts/setup_qwen.sh`.
Image workers need `pip install -e '.[images]'`; final rendering needs
`npm install --ignore-scripts --no-audit --no-fund @magenta/music@1.23.1`.
Export settings explicitly: `.env` is not loaded automatically.

Groq and Gemini are optional legacy diagnostic backends. They are not required
for daily text generation or Google readiness. Deliberately select a legacy
backend with `TEXT_BACKEND=groq`; use `STORY_PROVIDER=gemini` for Gemini.
Multilingual local alignment is the default when alignment is requested.

## Recovery

Use **Resume prepared episode and upload privately** for completed narration,
**Resume voice in parallel and upload privately** for interrupted narration, or
**Recover, verify upload or clean a saved episode** for saved checkpoints. Always
keep the original episode run ID. Preparation and per-shard checkpoints have
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
