# Somoy Jatri — বাংলা সময়ভ্রমণ

Updated against the reference on 2026-10-25. Production uses local Qwen3.5-9B,
SSD-1B illustrations, twenty CPU image jobs and Magenta MusicRNN. Narration,
packaging, captions and descriptions are Bangla. Bengali Parler and multilingual
Whisper replace the reference English-only speech components.

See [reference alignment](docs/reference-analysis.md) and [model settings](docs/models.md).
Run **Verify Google connections**, then **Model component test** in production mode
for voice, image and music. **Offline tests and short preview** exercises rendering
without cloud credentials. **Generate episode and optional private upload** runs
the complete pipeline; start with `preview_only=true` for review. The existing
daily schedule continues requesting private videos at 06:00 Asia/Dhaka.

Text generation no longer requires Groq or Gemini API keys. Keep this repository's
own Drive and YouTube credentials and account variables. Never use the reference
channel's credentials or folder.

---

# Somoy Jatri — Time Travel Vlogs

**ইতিহাস শুধু শুনব না, নিজের চোখে দেখব!**

A modular Python pipeline for Bangla first-person historical reconstruction videos. This repository is independent of `Asif-Rezan/youtube-dark-psychology-automation`; that repository was inspected but not modified.

## Current verification status

**Development implementation; not verified as production-ready.** Offline tests and a real short FFmpeg render pass. Mock narration is an audible tone, and mock images are labelled geometric fixtures. They demonstrate timing, captions, mixing, rendering and safety checks, not speech quality or photorealism. Mock outputs cannot upload.

Real Indic Parler synthesis, measured audio quality, SSD-1B CPU resource consumption, Groq story quality, Google Drive operations and YouTube uploads require integration tests. No live video has been uploaded by this implementation. Human historical and voice-quality review remains necessary.

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
| Audio checks and optional transcription utilities | `narration/providers.py`, `alignment/timing.py` |
| Dynamic shots and continuity | `storyboard/timeline.py` |
| Configurable CPU images | `images/providers.py` |
| Motion rendering | `animation/motion.py`, `renderer/ffmpeg.py` |
| Distinct music cues | `music/scoring.py` |
| Independent ambience | `ambient_audio/profiles.py` |
| Captions and thumbnail | `subtitles/`, `thumbnail/` |
| QC, storage and upload | `validation/`, `storage/`, `youtube/` |

All stage boundaries use UTF-8 JSON manifests. Assets live under run IDs. The pipeline logs durations and peak resident memory without credential values. Commands are argv lists, never generated shell strings. Copy `.env.example` to `.env` if helpful, but export variables explicitly: the CLI deliberately does not automatically load files containing secrets.

## Narration and seven-second images

The default CPU voice is the public Bengali Parler model (`Tanmoyshome/bn-parler-tts`). It has a fixed Bengali female-speaker description and does not provide verified emotion or named-speaker control. The optional gated `ai4bharat/indic-parler-tts` backend supports the documented Bengali speaker descriptions. Accent, naturalness and emotion still require listening review. See [model evaluation](docs/models.md).

Each short utterance is synthesized separately and checked for decoded duration, finite samples, audible level and clipping. Unusable audio is regenerated up to three times. Production no longer requires a transcription similarity score. A checksum and text fingerprint bind each reusable voice file to its script. Pronunciation still needs listening review; passing these checks does not certify exact spoken words.

Images change every **7 seconds**, independently of utterance boundaries, with a shorter final image when necessary. The visual sequence progresses through the reviewed storyboard; it is not word-synchronized. Captions use the original Bangla text and measured utterance start/end times, so image changes do not split or repeat captions. Existing word timestamps can refine captions for older saved episodes.

For a modest overrun, FFmpeg applies a pitch-preserving tempo adjustment capped at 1.10× and measures the result again. Caption boundaries scale to the measured output. Larger overruns or narration below 600 seconds require script revision (maximum three versions). Speech is never truncated.

## Visuals

SSD-1B starts at 1024×576, 16 steps, float32 CPU, attention/VAE slicing. Prompts contain historical period, setting, action, clothing, architecture, first-person framing and negative constraints. The initial revision is pinned to the reference's inspected checkpoint. Set both `CPU_IMAGE_MODEL` **and** `CPU_MODEL_REVISION` when switching models; implement another `ImageProvider` for a different architecture.

Only verified images with matching prompt fingerprints/checksums are reused. Failed generation retains the run. No unrelated environmental image is substituted for a missing merchant or other narrated subject. Camera motion uses efficient FFmpeg zoom/pan/tilt/drift; it is not full image-to-video inference. Depth-based parallax/reference conditioning are extension points, not implemented capabilities. Shot cuts follow the fixed seven-second schedule with cumulative frame rounding; crossfades between images are not currently implemented.

Default four image jobs, with GitHub `max-parallel: 4`. Each runner loads one model. Increasing the matrix count does not enlarge one runner's RAM/CPU and may increase queue time or billable use. SSD-1B may exceed a standard runner's practical memory/time budget; validate one image before a full episode. Use a larger appropriately configured runner if necessary. No CPU speed claims have been measured here.

## Scene-aware sound

The default `ProceduralMusic` provider generates different original pentatonic/ambient cues with mood-dependent roots, timing and reproducible variation. Cues follow chapters/moods rather than images, overlap with fades at boundaries, and never repeat one full-video recording. This is local procedural synthesis, **not Magenta or a trained AI music model**. The reference's MusicRNN generates useful notes but its single-loop design was not carried over.

A `MusicProvider` protocol and `LicensedMusic` adapter allow future trained models or a curated catalog. Licensed audio must declare `license` and `source`; short music files are rejected rather than looped. The CLI currently uses the procedural provider. Wire an alternative into `score(..., provider=...)` to replace it.

Narration receives conservative peak normalization and click-free concatenation. Music and ambience have separate gain envelopes with rapid speech attack and gradual release. The mix peak is bounded; this is gain automation, not a certified intelligibility/LUFS result. Real voices and scoring need listening review.

Synthetic wind/water textures are supplied without third-party samples. Crowds, horses, boats and workshops need your licensed field recordings; unavailable profiles remain silent instead of using modern or mismatched recordings. Set `AMBIENT_CATALOG` to JSON mapping profile names to `{ "path": "...", "license": "...", "source": "..." }`. Attribution for externally supplied sounds must be added to your description. Do not assume a downloaded clip is royalty-free.

## Research and topic selection

Automatic private runs select the next unused topic from `docs/research/topics.json`, fetch its curated UNESCO page, and ask Groq to build a cautious research packet from that page. Exact source excerpts and source IDs are checked against the fetched page before generation. The episode stays private: automated extraction does not establish historical accuracy, and a person should review the research, narration, imagery, and voice before any wider release. Add new curated topics before the list is exhausted. The daily workflow runs at 06:00 Asia/Dhaka and dispatches generation with private visibility.

For editorially reviewed runs, create a dossier using `docs/research/example.json` and supply exact source URLs, titles, excerpts, fact-to-source IDs, uncertainties, and a human `reviewed_by` field. Use its path or a directory of reviewed dossiers with `RESEARCH_DOSSIER`. The example is incomplete and cannot pass production validation. Source checks establish page reachability and matching excerpts, not the truth of every claim. JS-only pages and PDFs need a separate adapter. Set `RESEARCH_DOSSIER=auto` for the curated automatic path; production stops when all curated topics have been used.

Topic history prevents close title/location-period repeats. GitHub production preparation restores/saves it in the dedicated Drive folder. Enable Drive for persistent history across hosted runs. No previous channel ID or Drive folder is hardcoded.

## First real voice and image tests

The default Bengali voice model is the public `Tanmoyshome/bn-parler-tts`, which does not need a Hugging Face token. It supports a female voice description but not named speakers or fine-grained emotion. To use the original named-voice model, set `TTS_MODEL=ai4bharat/indic-parler-tts`, accept its Hugging Face access conditions, and configure `HF_TOKEN`. Install voice dependencies in a separate environment from image dependencies to avoid Transformers version conflicts.

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

Open the helper's printed authorization URL in your chosen browser. Set `EXPECTED_DRIVE_EMAIL`
to verify the Drive account before its token is saved. Use the verified YouTube channel even
when Google's brand-account picker shows an older brand name; the helper checks the channel ID.
After configuring repository secrets, set the `EXPECTED_DRIVE_EMAIL` repository variable and run
**Verify Google and Groq connections**. It checks Groq model availability, the Drive account and
private checkpoint read/write, and the exact YouTube channel without uploading a video.

The YouTube helper requires `EXPECTED_CHANNEL_ID` and confirms the selected channel. It requests upload and read-only YouTube scopes for uploads, thumbnails and channel/processing verification. Drive uses `drive.file`, restricted to app-created or explicitly app-authorized files. Tokens are saved with owner-only access and never printed. Copy their JSON contents into GitHub Actions secrets yourself. Run `python -m somoy_jatri.cli drive-init` with `DRIVE_TOKEN_JSON` exported to create a new Somoy Jatri folder, then configure its printed ID. A folder created manually in Drive is not sufficient: the application must be authorized to access it and its dedicated-root marker must be present. Do not relabel or reuse the reference project's folder.

| GitHub Actions secret | Purpose |
|---|---|
| `GROQ_API_KEY` | Natural Bangla script generation and semantic review |
| `HF_TOKEN` | Optional for the public default voice; required if selecting a gated model |
| `YOUTUBE_TOKEN_JSON` | Separate OAuth authorized-user JSON for this channel |
| `DRIVE_TOKEN_JSON` | OAuth authorized-user JSON with `drive.file` scope |
| `DRIVE_FOLDER_ID` | Newly created private Somoy Jatri folder |

Repository variables: `EXPECTED_CHANNEL_ID` (mandatory for upload); `ALLOW_PUBLIC_UPLOAD` (default false). The daily workflow uses its scoped GitHub token and always requests private upload. An automatically researched episode is blocked from unlisted or public upload even if `ALLOW_PUBLIC_UPLOAD` is enabled.

Tokens must include refresh credentials and appropriate scopes. Google OAuth testing-mode expiry, YouTube API quota/audit restrictions, model access, and runner limits still apply. Public repositories are not a promise of unlimited/free compute. No paid inference API is added; Groq availability/quota is your configured account's responsibility.

## Exact first private-upload test

1. Run **Offline tests and short preview** in Actions and inspect the resulting MP4 and Bangla captions.
2. Run **Model component test → tts-test → production**. Listen to the uploaded voice test. Run `image-test` and `music-test` and review them.
3. Add the secrets and `EXPECTED_CHANNEL_ID` above. The automatic run uses the curated topic catalog, or you can supply a reviewed dossier.
4. Run **Generate episode and optional private upload** with `mode=production`, `dossier=auto`, `target=720`, `workers=4`, `visibility=private`, captions/music enabled, and `preview_only=true` for the first full render. Inspect its artifact.
5. Run the same workflow with `preview_only=false` for a private upload. The workflow's one-click defaults also choose this path. Full test duration is 600–900 seconds. Mock or failed-QC outputs cannot upload.
6. Wait for the **publish-cleanup** job to verify private HD processing and remove tagged temporary Drive media. Confirm privacy and thumbnail in YouTube Studio. If that job is interrupted, run **Resume verified private Drive cleanup** with the original run ID; it cannot insert another video.

For a local prepared production run, use `prepare`, each `images --shard N`, `finish`, then `upload --privacy private`. A voice environment is needed only for prepare; images and finish can run in different environments.

## Workflows, recovery and scheduling

- `checks.yml`: secret-free tests and real short preview.
- `components.yml`: female Bangla voice, historical image, or music test.
- `generate.yml`: measured narration and seven-second image prepare → parallel image shards → finish/QC → optional upload.
- `recovery.yml`: restore, regenerate a shard, finish, verify an upload or clean.
- `daily.yml`: explicit daily gate. No active cron trigger by default.

Run-scoped manifests, checksum-verified uploads/downloads and reserved Drive IDs support recovery. Failed preparation saves `preparation-failed` plus an Actions artifact, including successful utterance fingerprints. Preparation and each shard use separate checkpoint names (`prepared`, `shard-0`, …); the full rendered episode uses `checkpoint`. Restore `prepared`, then the available `shard-N` snapshots into the same local run before finishing a partial episode. Actions artifacts retain preparation and individual shards for 14 days as a second recovery path. They contain media/manifests, not OAuth secrets. Upload state stays in the private Drive folder; restrict access to it.

YouTube cannot provide an idempotency key for video insertion. The upload journal is saved before requests and after chunk progress. If the video ID is unknown after interruption, **no reinsertion is allowed**. Inspect Studio and reconcile using:

```bash
python -m somoy_jatri.cli reconcile --run-id episode-ORIGINAL_ID --video-id ACTUAL_ID
python -m somoy_jatri.cli upload --run-id episode-ORIGINAL_ID --privacy private
```

Automatic cross-process resumable YouTube session continuation is not implemented; ambiguous cases require reconciliation. If no remote video exists, an operator must resolve the journal after investigation. Checkpoint this decision before retrying.

Cleanup requires successful final QC and a verified private HD upload. The automatic Drive cleanup retains scripts, research, timings, prompts, captions, metadata, upload state, and topic history. It permanently deletes only tagged, allowlisted run media, including the final video and thumbnail after their YouTube versions are verified. Production credentials and arbitrary source files are never cleanup targets. The older local recovery cleanup command still moves its remote targets to Drive trash; use the dedicated **Resume verified private Drive cleanup** workflow for the resumable production path.

The daily workflow is scheduled for 00:00 UTC / 06:00 Dhaka. It selects the next unused curated topic through the generation workflow and keeps upload private. Drive topic history prevents repeats across runs; when the catalog is exhausted, the run fails closed. After upload, a separate job checks channel, private visibility, metadata, thumbnail confirmation, completed HD processing, and the original run checkpoint. It then permanently deletes only tagged temporary Drive media for that run, saving a resumable cleanup journal after each deletion. Scripts, research, captions, metadata, upload state, and topic history remain. Use **Resume verified private Drive cleanup** with the original `episode-...` run ID if verification or cleanup is interrupted; it never generates or uploads a second video. Verify the first private video and runner capacity before relying on the schedule. Public visibility for manually reviewed dossiers additionally requires `ALLOW_PUBLIC_UPLOAD=true`.

## Troubleshooting and remaining integration work

- Missing model access: accept current upstream access conditions and check `HF_TOKEN`; no paid fallback is automatic.
- Voice failure: inspect the saved utterance for silence, clipping or invalid duration. Audio checks do not certify pronunciation.
- Duration failure: preparation rewrites and resynthesizes within bounded attempts. Review script lengths after failure.
- Source excerpt mismatch: websites change; review and update evidence instead of fabricating citations.
- OOM/timeouts: lower resolution/steps, reduce concurrent jobs, or provision a suitable runner. Recover verified images from checkpoints.
- Font error: install fontconfig/libass or set `BANGLA_FONT`. The bundled font is explicitly passed to libass; inspect conjuncts visually.
- No music: inspect `music-plan.json`, `mix.wav`, and `--no-music`; the CLI provides no hidden single-loop fallback.
- Upload interruption: preserve `upload.json`, verify the channel, reconcile the ID; never restart blind insertion.

Known limits: live models/API integrations untested; no objective pronunciation or emotion score; no automated historical-image proof; no human-level cross-language semantic guarantee; no depth parallax or image crossfades; procedural rather than learned music; no bundled realistic field recordings; peak rather than EBU R128 loudness normalization. These are documented limits, not production-readiness claims.

Story requests prefer GPT-OSS 120B. On a long quota reset, an available GPT-OSS 20B quota can be used without bypassing script, speech, or semantic checks. Configure `STORY_FALLBACK_MODELS` (empty disables fallback). Requests bound completion tokens and report token counts without exposing API keys or raw authentication errors. Longer reset waits are honored up to one hour per retry.

Completed narration can be reused with **Resume prepared episode and upload privately**. Enter the original Actions run number containing a successful `prepared` artifact. The workflow checks production mode, 600–900-second narration, Bengali speech verification, timeline coverage and semantic review before repartitioning only the image worker count. Audio and scene content are retained. Upload remains private and uses the original episode ID to preserve duplicate-upload protection. New generation and the daily dispatcher now request up to 16 parallel standard CPU image jobs, subject to account capacity, with four CPU threads per worker.

For an interrupted narration stage, use **Resume voice in parallel and upload privately** with the original run number. It reviews the saved story before more synthesis, reuses existing utterances, distributes remaining takes over eight CPU workers by default, and merges disjoint voice artifacts. Successful takes retain a fingerprint, audio checksum and measured-audio receipt, so assembly does not repeat synthesis or transcription. The resulting episode ID is unchanged, protecting against duplicate uploads. The recovery workflow defaults to `preview_only=true`; it generates the video without uploading unless that option is explicitly disabled. Automatically sourced research is eligible for private review uploads; it never receives a fabricated human reviewer and remains blocked from public/unlisted upload.


### Optional Gemini text fallback

Set the repository secret `GEMINI_API_KEY` to enable Gemini when Groq text-model quota is exhausted. The default model is `gemini-3.8-flash`, with `gemini-3.5-flash-lite` available when its quota is exhausted. `GEMINI_MODEL` and `GEMINI_FALLBACK_MODELS` can select compatible models. The same JSON schemas, citation validation, storyboard review, and audio checks remain required. `STORY_PROVIDER=gemini` exercises Gemini directly in the full verification workflow. Image timing does not require audio transcription. Keys are sent in request headers and never logged or committed.

Background music uses an original historical documentary instrumental bed: low drones, slow modal string tones, sparse plucked notes and soft frame-drum pulses. Cues continue across seven-second image cuts and duck beneath Bangla narration.
