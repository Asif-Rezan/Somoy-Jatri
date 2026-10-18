# Somoy Jatri — Time Travel Vlogs

**ইতিহাস শুধু শুনব না, নিজের চোখে দেখব!**

A modular Python pipeline for Bangla first-person historical reconstruction videos. This repository is independent of `Asif-Rezan/youtube-dark-psychology-automation`; that repository was inspected but not modified.

## Current verification status

**Development implementation; not verified as production-ready.** Offline tests and a real short FFmpeg render pass. Mock narration is an audible tone, and mock images are labelled geometric fixtures. They demonstrate timing, captions, mixing, rendering and safety checks, not speech quality or photorealism. Mock outputs cannot upload.

Real Indic Parler synthesis, Bengali ASR quality, SSD-1B CPU resource consumption, Groq story quality, Google Drive operations and YouTube uploads require integration tests. No live video has been uploaded by this implementation. Human historical and voice-quality review remains necessary.

## Quick start (no secrets)

Python 3.11, FFmpeg/ffprobe with libx264/libass, and fontconfig are required. A Noto Sans Bengali font is bundled under SIL OFL. Pillow must have RAQM/HarfBuzz for thumbnails.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python -m pytest -q
python -m somoy_jatri.cli preview --run-id preview
```

Inspect `output/preview/video.mp4`, `captions.srt`, `captions.ass`, `thumbnail.jpg`, `timeline.json`, and `qc.json`. The preview is approximately eight seconds, at 640×360. Production renders at 1920×1080/30fps, H.264/AAC, and requires 600–900 seconds of measured narration.

## Architecture

| Stage | Implementation |
|---|---|
| Configuration and CLI | `config.py`, `cli.py`, `pipeline.py` |
| Source evidence | `research/dossier.py` |
| Original Bangla scripts | `scripts/groq.py`, `topics/history.py` |
| Voice and normalization | `narration/` |
| Bengali speech verification | `alignment/timing.py` |
| Dynamic shots and continuity | `storyboard/timeline.py` |
| Configurable CPU images | `images/providers.py` |
| Motion rendering | `animation/motion.py`, `renderer/ffmpeg.py` |
| Distinct music cues | `music/scoring.py` |
| Independent ambience | `ambient_audio/profiles.py` |
| Captions and thumbnail | `subtitles/`, `thumbnail/` |
| QC, storage and upload | `validation/`, `storage/`, `youtube/` |

All stage boundaries use UTF-8 JSON manifests. Assets live under run IDs. The pipeline logs durations and peak resident memory without credential values. Commands are argv lists, never generated shell strings. Copy `.env.example` to `.env` if helpful, but export variables explicitly: the CLI deliberately does not automatically load files containing secrets.

## Narration and dynamic timing

Indic Parler-TTS (`ai4bharat/indic-parler-tts`) is the initial local CPU backend with Aditi, a documented Bengali voice, and female-speaker descriptions. Rashmi and Riya are configurable alternatives. The upstream model card documents Bengali and emotion prompting. Emotion tags map to descriptive prompts; intensity is retained as direction metadata, not an unverified numeric model control. There is no pitch shifting or synthetic emotion guarantee. Bangladeshi accent and perceived emotion require listening tests. See [model evaluation](docs/models.md).

Every short semantic utterance is synthesized separately. Its decoded audio sample count establishes exact boundaries, including intentional pauses. The final narration is concatenated before creating shot manifests. Multilingual faster-whisper (`small`, `language=bn`, CPU int8) checks speech against the original Bangla. English-only Whisper models are rejected. This is transcription-based alignment, not a Bengali forced-aligner accuracy claim. Low script similarity stops preparation. Word times refine captions when usable; measured utterance boundaries remain the sentence fallback.

Each distinct narrated subject receives a shot with its own duration. There is **no fixed image interval** and no proportional text-length timing in production. Complex sentences must be split into separate visual utterances during script generation. A deterministic validator checks coverage, overlaps, gaps and prompt anchors; a separate Groq review compares Bangla narration with English visuals and dossier facts. This model review is not factual proof. Continuity is prompt-based scene memory, not guaranteed pixel-level identity.

If voice duration falls outside 600–900 seconds, Groq revises the script and narration is regenerated (maximum three versions). Speech is never forcibly truncated or sped up to meet duration.

## Visuals

SSD-1B starts at 1024×576, 16 steps, float32 CPU, attention/VAE slicing. Prompts contain historical period, setting, action, clothing, architecture, first-person framing and negative constraints. The initial revision is pinned to the reference's inspected checkpoint. Set both `CPU_IMAGE_MODEL` **and** `CPU_MODEL_REVISION` when switching models; implement another `ImageProvider` for a different architecture.

Only verified images with matching prompt fingerprints/checksums are reused. Failed generation retains the run. No unrelated environmental image is substituted for a missing merchant or other narrated subject. Camera motion uses efficient FFmpeg zoom/pan/tilt/drift; it is not full image-to-video inference. Depth-based parallax/reference conditioning are extension points, not implemented capabilities. Shot cuts are synchronized to cumulative frame-rounded audio boundaries; crossfades between images are not currently implemented.

Default four image jobs, with GitHub `max-parallel: 4`. Each runner loads one model. Increasing the matrix count does not enlarge one runner's RAM/CPU and may increase queue time or billable use. SSD-1B may exceed a standard runner's practical memory/time budget; validate one image before a full episode. Use a larger appropriately configured runner if necessary. No CPU speed claims have been measured here.

## Scene-aware sound

The default `ProceduralMusic` provider generates different original pentatonic/ambient cues with mood-dependent roots, timing and reproducible variation. Cues follow chapters/moods rather than images, overlap with fades at boundaries, and never repeat one full-video recording. This is local procedural synthesis, **not Magenta or a trained AI music model**. The reference's MusicRNN generates useful notes but its single-loop design was not carried over.

A `MusicProvider` protocol and `LicensedMusic` adapter allow future trained models or a curated catalog. Licensed audio must declare `license` and `source`; short music files are rejected rather than looped. The CLI currently uses the procedural provider. Wire an alternative into `score(..., provider=...)` to replace it.

Narration receives conservative peak normalization and click-free concatenation. Music and ambience have separate gain envelopes with rapid speech attack and gradual release. The mix peak is bounded; this is gain automation, not a certified intelligibility/LUFS result. Real voices and scoring need listening review.

Synthetic wind/water textures are supplied without third-party samples. Crowds, horses, boats and workshops need your licensed field recordings; unavailable profiles remain silent instead of using modern or mismatched recordings. Set `AMBIENT_CATALOG` to JSON mapping profile names to `{ "path": "...", "license": "...", "source": "..." }`. Attribution for externally supplied sounds must be added to your description. Do not assume a downloaded clip is royalty-free.

## Research and topic selection

Create dossiers using `docs/research/example.json`. Supply exact source URLs, page titles, short evidence excerpts, fact-to-source IDs, uncertainties and a human `reviewed_by` field. The example is deliberately incomplete and cannot pass production validation. `requests` verifies source reachability and that excerpts occur on the current HTML page. JS-only pages and PDFs need an adapter or another accessible source. This check does not establish publisher credibility or whether every claim follows from evidence; the reviewer does that.

Use a single dossier path or a directory of reviewed dossiers with `RESEARCH_DOSSIER`. Directory mode chooses the next location/period not already reserved in topic history. Dossiers are not generated from unsupported model claims. New history source gathering/review is currently a required editorial input, not a fully autonomous research agent. When all reviewed topics are exhausted, production stops safely.

Topic history prevents close title/location-period repeats. GitHub production preparation restores/saves it in the dedicated Drive folder. Enable Drive for persistent history across hosted runs. No previous channel ID or Drive folder is hardcoded.

## First real voice and image tests

Accept the model's current access conditions on Hugging Face and configure `HF_TOKEN` if required. Install voice dependencies in a separate environment from image dependencies to avoid Transformers version conflicts.

```bash
pip install -e .
pip install -r requirements-tts.txt
python -m somoy_jatri.cli tts-test --mode production --run-id voice-check
```

Listen to `output/voice-check/voice-test.wav` for gender, pronunciation, dates, pauses and emotion. The test is short and does not prove ten-minute voice consistency. Then in an image environment:

```bash
pip install -e '.[images]'
python -m somoy_jatri.cli image-test --mode production --run-id image-check
python -m somoy_jatri.cli music-test --run-id music-check
```

## Google OAuth and required settings

Enable YouTube Data API v3 and Google Drive API in a Google Cloud project. Create Desktop OAuth credentials and download `client_secrets.json` locally. Never commit credentials.

```bash
pip install -e '.[google]'
python scripts/authorize_google.py drive
python scripts/authorize_google.py youtube
```

The YouTube helper requires `EXPECTED_CHANNEL_ID` and confirms the selected channel. It requests upload and read-only YouTube scopes for uploads, thumbnails and channel/processing verification. Drive uses `drive.file`, restricted to app-created or explicitly app-authorized files. Tokens are saved with owner-only access and never printed. Copy their JSON contents into GitHub Actions secrets yourself. Run `python -m somoy_jatri.cli drive-init` with `DRIVE_TOKEN_JSON` exported to create a new Somoy Jatri folder, then configure its printed ID. A folder created manually in Drive is not sufficient: the application must be authorized to access it and its dedicated-root marker must be present. Do not relabel or reuse the reference project's folder.

| GitHub Actions secret | Purpose |
|---|---|
| `GROQ_API_KEY` | Natural Bangla script generation and semantic review |
| `HF_TOKEN` | Gated model downloads if required by upstream |
| `YOUTUBE_TOKEN_JSON` | Separate OAuth authorized-user JSON for this channel |
| `DRIVE_TOKEN_JSON` | OAuth authorized-user JSON with `drive.file` scope |
| `DRIVE_FOLDER_ID` | Newly created private Somoy Jatri folder |
| `WORKFLOW_DISPATCH_TOKEN` | Optional fine-grained token with Actions write for daily dispatcher |

Repository variables: `EXPECTED_CHANNEL_ID` (mandatory for upload); `ALLOW_PUBLIC_UPLOAD` (default false); `DAILY_ENABLED` (default false); `RESEARCH_DOSSIER` (reviewed path or directory for scheduled dispatch).

Tokens must include refresh credentials and appropriate scopes. Google OAuth testing-mode expiry, YouTube API quota/audit restrictions, model access, and runner limits still apply. Public repositories are not a promise of unlimited/free compute. No paid inference API is added; Groq availability/quota is your configured account's responsibility.

## Exact first private-upload test

1. Run **Offline tests and short preview** in Actions and inspect the resulting MP4 and Bangla captions.
2. Run **Model component test → tts-test → production**. Listen to the uploaded voice test. Run `image-test` and `music-test` and review them.
3. Add the secrets and `EXPECTED_CHANNEL_ID` above. Commit a complete reviewed dossier in `docs/research/`.
4. Run **Generate episode and optional private upload** with `mode=production`, your reviewed `dossier`, `target=720`, `workers=4`, `visibility=private`, captions/music enabled, and `preview_only=true`. Inspect the complete final artifact before enabling upload.
5. Run generation with the reviewed settings and `preview_only=false`, `visibility=private`. Full test duration is 600–900 seconds. Mock or failed-QC outputs cannot upload.
6. Wait for YouTube processing. Run **Recover, verify upload or clean a saved episode → upload** for the original run to verify the existing video ID. It will not insert a second video. Confirm privacy and thumbnail in YouTube Studio. Only then use cleanup.

For a local prepared production run, use `prepare`, each `images --shard N`, `finish`, then `upload --privacy private`. A voice environment is needed only for prepare; images and finish can run in different environments.

## Workflows, recovery and scheduling

- `checks.yml`: secret-free tests and real short preview.
- `components.yml`: female Bangla voice, historical image, or music test.
- `generate.yml`: dynamic prepare → parallel image shards → finish/QC → optional upload.
- `recovery.yml`: restore, regenerate a shard, finish, verify an upload or clean.
- `daily.yml`: explicit daily gate. No active cron trigger by default.

Run-scoped manifests, checksum-verified uploads/downloads and reserved Drive IDs support recovery. Preparation and each shard use separate checkpoint names (`prepared`, `shard-0`, …); the full rendered episode uses `checkpoint`. Restore `prepared`, then the available `shard-N` snapshots into the same local run before finishing a partial episode. Actions artifacts retain preparation and individual shards for 14 days as a second recovery path. They contain media/manifests, not OAuth secrets. Upload state stays in the private Drive folder; restrict access to it.

YouTube cannot provide an idempotency key for video insertion. The upload journal is saved before requests and after chunk progress. If the video ID is unknown after interruption, **no reinsertion is allowed**. Inspect Studio and reconcile using:

```bash
python -m somoy_jatri.cli reconcile --run-id episode-ORIGINAL_ID --video-id ACTUAL_ID
python -m somoy_jatri.cli upload --run-id episode-ORIGINAL_ID --privacy private
```

Automatic cross-process resumable YouTube session continuation is not implemented; ambiguous cases require reconciliation. If no remote video exists, an operator must resolve the journal after investigation. Checkpoint this decision before retrying.

Cleanup requires successful final QC and, when an upload was attempted, a verified processed video. It retains scripts, research, timings, prompts, final video/thumbnail, captions and upload state. Only allowlisted temporary media is removed. Remote media is moved to trash after folder/key verification, not permanently deleted. Production credentials and arbitrary source files are never cleanup targets.

To schedule, first complete private testing, configure a directory of reviewed dossiers and Drive history, add the commented `schedule` trigger to `daily.yml`, set `DAILY_ENABLED=true`, and configure `WORKFLOW_DISPATCH_TOKEN`. The example cron is 03:00 UTC / 09:00 Dhaka; change the cron for cadence. Public visibility additionally requires explicit `ALLOW_PUBLIC_UPLOAD=true`; the daily dispatcher remains private.

## Troubleshooting and remaining integration work

- Missing model access: accept current upstream access conditions and check `HF_TOKEN`; no paid fallback is automatic.
- TTS/ASR mismatch: inspect the individual utterance, normalization and voice test. Do not bypass the similarity gate to publish.
- Duration failure: preparation rewrites and resynthesizes within bounded attempts. Review script lengths after failure.
- Source excerpt mismatch: websites change; review and update evidence instead of fabricating citations.
- OOM/timeouts: lower resolution/steps, reduce concurrent jobs, or provision a suitable runner. Recover verified images from checkpoints.
- Font error: install fontconfig/libass or set `BANGLA_FONT`. The bundled font is explicitly passed to libass; inspect conjuncts visually.
- No music: inspect `music-plan.json`, `mix.wav`, and `--no-music`; the CLI provides no hidden single-loop fallback.
- Upload interruption: preserve `upload.json`, verify the channel, reconcile the ID; never restart blind insertion.

Known limits: live models/API integrations untested; no objective pronunciation or emotion score; no automated historical-image proof; no human-level cross-language semantic guarantee; no depth parallax or image crossfades; procedural rather than learned music; no bundled realistic field recordings; peak rather than EBU R128 loudness normalization. These are documented limits, not production-readiness claims.
