# Video pipeline reliability and timing

Compared on 2026-10-27:

- Somoy Jatri failed run: https://github.com/Asif-Rezan/Somoy-Jatri/actions/runs/40412815393
- Reference successful run: https://github.com/Asif-Rezan/Rezan-After-Dark/actions/runs/40412148950

## What the logs establish

Somoy Jatri failed during stage-story, before narration preparation, images, rendering, or upload. The outline, four narration batches, and ten-token source review completed. The next stage is YouTube packaging; its three JSON attempts failed. Existing logs do not retain the validation reason, so the exact rejected field cannot be recovered from this run.

The reference run took 5 hours 2 minutes, from 22:24 UTC to 03:26 UTC. Preparation took 63 minutes. Image generation generally took roughly 7–8 minutes per image, and several shards waited for runners. Both repositories used Qwen3-4B Q4_K_M and SSD-1B at 1024x576 with 16 steps and twenty image shards. The reference is therefore not evidence of a fast full-video CPU run.

## Changes

- The pinned llama-cpp-python 0.3.36 schema converter handles string pattern before maxLength. The old thumbnail pattern allowed questions longer than 30 characters, which the independent validator rejected without corrective feedback. The revised pattern bounds its own output to 30 characters. Length limits also bound packaging fields and tag counts.
- JSON retries now receive corrective constraint feedback. Logs show only schema paths, constraint names, completion state, token counts, and timing, rather than unpublished content.
- Each schema-valid story response is saved under the private run in Drive. A retry of the same run validates and reuses matching responses, preserving the outline and narration when packaging fails. The cache key includes the full prompt, schema, model, temperature, and token budget. Source review and all downstream validations remain required.
- Local packaging retries wait one second instead of using a hosted-provider sixty-second rate-limit delay.
- Daily jobs cache dependency downloads across runners.
- Image generation retains the default PyTorch SDPA processor instead of unconditionally replacing it with sliced attention. Hugging Face warns that combining these approaches can cause serious slowdowns: https://huggingface.co/docs/diffusers/main/api/diffusion_pipeline . For constrained-memory environments, set CPU_IMAGE_ATTENTION_SLICING=true to restore sliced attention. Model, resolution, steps, VAE slicing, and image safety checks remain unchanged.
- The real Qwen readiness check now generates a thumbnail question using the corrected schema as well as word-constrained narration. The image smoke test uses production Torch and compares against the actual Islamic documentary subject, replacing a leftover horror-story target.

## Recovery and limits

Rerun failed jobs in the same workflow run to reuse private story responses produced by this version. Changing a prompt, schema, or run uses a different response key. The old failed run predates these response checkpoints and cannot recover its lost in-memory chapters.

Dependency caches speed setup after a warm run; they do not cache unpublished content. CPU diffusion and runner queues still dominate total completion time. No fixed speedup or complete successful upload is implied by passing component checks; report a measured production run separately.
