# Somoy Jatri — English Islamic history and hadith documentaries

Rebuilt from `Asif-Rezan/Rezan-After-Dark` at commit
`cfc864f8265a4cdde2c34e6343c4c8ef800e295e`. The previous Bangla package, voice
experiments and workflows are replaced. The reference repository is unchanged.

The reference's CPU production structure is retained: one twenty-chapter outline,
four batches of five English narrations, measured 15–20 minute duration with bounded
corrections, word-timed English captions, a new image every ten seconds, twenty
image workers, 1080p rendering, thumbnails, public YouTube upload verification,
and private Drive checkpoints with upload-only recovery and verified cleanup.

## Content

`islamic_topics.json` starts with six source packets: Abbasid Samarra, Historic
Cairo, Abbasid Baghdad, intentions, good speech and neighbors, and concern for
others. History packets cite UNESCO or The Metropolitan Museum of Art. Hadith
packets use specific Sahih al-Bukhari report references on Sunnah.com. Each chapter
must retain valid claim identifiers; sources and report references appear in the
description. Expand the catalog by adding sourced claims and the same source schema.

Scripts use objective English educational narration. They must distinguish
reported teachings from explicitly labelled reflection or modern examples. They
must not invent religious quotations, hadith, narrator chains, authenticity grades,
miracles, dates or personal religious rulings. Hadith meanings are paraphrased,
not presented as exact translations. A model-based evidence review rejects
unsupported drafts before narration and runs again after duration revisions.
This is a same-model consistency check, not independent scholarly verification.

Visuals use objects, landscapes and empty architecture. They do not depict people,
prophets, companions, angels or divine figures. Reconstructions are illustrative,
not documentary evidence of a specific scene. Metadata uses Education category 27.

## Models and pacing

- Text: `Qwen/Qwen3-4B-Instruct-2507`, pinned Q4_K_M conversion, local CPU,
  SHA-256 verified by `story_cpu.py`; no text API key.
- English voice: the reference's Kokoro `am_michael`, speed `0.82`, pitch `-2`
  semitones with duration-preserving processing. No voice or emotion switching.
- Images: `segmind/SSD-1B`, CPU, 1024×576, 16 steps, safety checker retained.
- Alignment: Faster-Whisper `base.en`, measured English word timestamps.
- Background score: the reference's free Magenta MusicRNN engine, restrained
  synthesized documentary bed with narration ducking. Sparse outputs retry up to
  five times; no silence or loop is substituted for failed generation.

These models run without paid inference APIs. GitHub Actions runtime/storage and
Google service quotas still apply. No paid service is configured.

## Somoy Jatri account setup

Use only this repository's existing Somoy Jatri credentials:
`YOUTUBE_TOKEN_JSON`, `DRIVE_TOKEN_JSON`, and `DRIVE_FOLDER_ID`.
The expected YouTube channel is `UCoqbUdZG8anRCCW9eK4snZA`; upload checks reject
another channel. Drive must be owner-only and carry the existing
`somoy_jatri_root=v1` folder marker. Never copy Rezan-After-Dark's channel identity,
OAuth tokens or storage folder. `setup_drive_folder.py` can create a correctly
marked dedicated folder if needed. No credentials are stored in source control.

Run **Google OAuth check** to verify the existing credentials. The daily workflow
is `.github/workflows/daily-upload.yml`, with public uploads and the reference's
00:00 Asia/Dhaka daily start. A manual dispatch can start a fresh episode; the
`cleanup_run` input only verifies/cleans an already completed run. Old Bangla or
fictional-story checkpoints are incompatible: start a fresh English Islamic run.
Do not rerun an old workflow revision expecting this implementation.

## Checks

Use Python 3.12 and FFmpeg with libx264/libass, plus espeak-ng for Kokoro:

```sh
pip install -r requirements.txt
python -m unittest -v
node --test test_music_retry.cjs
```

`requirements-story.txt` supplies the reference's pinned Linux CPU Qwen wheel.
`requirements-cpu.txt` supplies its pinned Kokoro/tokenizer/image stack.
The **Qwen CPU script generation check** and **Kokoro CPU narration check**
exercise real model downloads and generation without publishing or Google
credentials. **Cloud component checks** runs the offline suite on pull requests.
`sample-story.json` is an explicitly labelled technical fixture; daily generation
creates fresh sourced scripts instead of publishing that fixture.

See `docs/error-recovery.md` for the retained Drive/shard recovery process.

New uploads publish publicly and must pass visibility, HD, channel, thumbnail and metadata checks before media cleanup. Existing private runs retain their recorded visibility.

The background score uses warm modal plucked strings, airy flute-like phrases and soft frame-drum pulses, without vocals. Packaging uses distinct title/thumbnail candidates, prominent subject keywords, readable gold/emerald hooks and source-linked descriptions without production-tool details.
