# Preparation reference alignment — 2026-10-25

Preparation reference: `Asif-Rezan/Rezan-After-Dark`, commit
`d6dcde36a636946279ec7bc20c05d2c56625b958`. The reference is read only.
This supersedes the earlier Qwen3.5-9B preparation integration.

| Stage | Reference process used by Somoy Jatri |
|---|---|
| CPU runtime | Same Qwen3-4B-Instruct-2507 identity, Q4_K_M artifact/revision/checksum, llama-cpp-python 0.3.36 wheel, 16,384 context, at most four threads |
| Readiness | Real grammar-constrained local text check, then real language-specific voice check before full story |
| Story | One concise twenty-chapter outline, four five-chapter narration batches, publishing metadata after narration |
| Output checks | Grammar word bounds plus measured word counts, at most three invalid-output/length attempts; no hosted fallback |
| Audio | One checksum/text/voice-bound chapter cache; reuse unchanged chapters |
| Duration | Actual measured audio, maximum 4% tempo adjustment, selected-chapter rewrites/resynthesis, three correction attempts |
| Alignment | Cached measured word timestamps bound to each chapter's audio and text |
| Storyboard | Generate prompts only after audio timing, eight exact windows per request, checkpoint each completed batch |
| Finalization | Verify story/audio/caption/plan hashes and complete timeline before image workers |

Language/content adaptations: Bengali Parler replaces English Kokoro, with
bounded internal text splitting and one chapter-level cache. Multilingual
Whisper base with language `bn` replaces base.en. Word-count grammar accepts
Bengali characters and punctuation. Historical factual anchors and fictional
time travel remain; horror prompts, channel identity and credentials are not
copied. Existing 600–900-second videos and seven-second images are retained.
The initial Bangla target is 75 words per chapter; actual audio determines acceptance.
The job deadline is 240 minutes instead of the English reference's 150 to allow
the slower Bengali voice adapter; this does not add any generation or review work.

Fresh runs use curated source anchors directly, like the reference's curated
input, rather than making extra live research/extraction/enrichment requests.
The dossier says `curated source catalog` and does not fabricate a reviewer or
claim that paraphrases are exact quotations. These runs are restricted to private
uploads. A structural/evidence receipt replaces the old repeated semantic-review
loop and explicitly states that it is not proof of historical visual accuracy.

Image generation, continuous historical MusicRNN, Drive identity checks,
private YouTube upload journals and verified cleanup remain in place. Chapter
media and timestamp caches are included in recovery checkpoints. Old saved
utterance-format artifacts retain their legacy resume path.

The cancelled older run repeatedly repaired/re-reviewed its first semantic batch
before any voice synthesis. That cycle is not part of the new preparation path.
No runtime or speed guarantee is inferred from the reference; real full-video
performance must be measured on the production runner.
