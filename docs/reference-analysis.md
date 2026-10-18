# Reference inspection

Reference: `Asif-Rezan/youtube-dark-psychology-automation`, commit `5b9a124075b7017cd51844bc2014f3409b87e4aa`.

Inspected `workflow.py`, `long_video.py`, `daily_publish.py`, CPU image/voice/music providers, duration control, OAuth helpers, shard backup, requirements and workflow definitions. No reference files were edited.

Reused as independent, adapted code: Drive retry/class logic, reserved file IDs, checksum verification and quota guards from `workflow.py`. Folder marker changed to `somoy_jatri_root=v1`; all reference channel identifiers were excluded. The reference has no top-level license declaration in the inspected checkout; confirm your rights before redistribution beyond your own repositories.

Retained design ideas: run-scoped stages, per-shard workers, restore-before-regenerate, duration checking, private upload, identity guards and post-verification cleanup. Rebuilt: natural Bangla scripts, named Bengali female TTS, multilingual alignment, measured semantic shot boundaries, original multi-cue scoring, caption rendering and project structure. Did not copy English Kokoro, base.en, seven-second slots, hardcoded channel IDs or the single music loop.
