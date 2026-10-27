# Handling failures in video jobs

Incident: daily run 40456465352 on 2026-10-27. Preparation and 17 image shards succeeded. Shards 2, 3 and 6 failed because the runner Ubuntu mirror downloaded required FFmpeg libraries too slowly. Their backup steps then failed importing cryptography because setup had stopped before Python dependencies were installed. Final assembly correctly stayed blocked rather than assembling an incomplete video.

## Setup

Working tools are reused. If required downloads stall or fail, setup switches from runner-configured repositories to signed official Ubuntu archive/security repositories, using isolated source configuration. It does not edit the runner configuration or disable signature verification. Required archives are downloaded before installation, so a stalled network download cannot leave half-installed packages. Cached archives are retained for failover. Both sources have network and process time limits; if both fail, setup stops with a specific error instead of generating media with missing tools.

CI exercises both the primary path and a deliberately failed primary path on real Ubuntu runners. It installs FFmpeg, fonts and the speech dependency, then actually encodes a captioned H.264 clip and produces WAV audio. This supplements mock tests; a passing normal runner alone does not establish that failover works.

## Recovery

Encrypted backup runs only after the private plan has restored successfully. The backup CLI uses only the standard library to determine whether any generated work exists, and skips empty workspaces without importing encryption or video dependencies. Real work still requires encryption; plaintext unpublished work is never uploaded as a fallback. Tests cover the empty workspace with third-party packages unavailable, partial-work preservation and the authenticated encryption round trip.

Each render is published atomically. If a quality retry discards an image, its old clip and review are discarded too, so a new review cannot be paired with a stale clip. Existing source checks, image safety checks, incomplete-shard gates and duplicate-upload protections remain in force.

## Reading logs

Tests deliberately simulate rejection, outages and invalid media. On success, production validation shows the test summary instead of those synthetic error messages; failed tests show the detailed output. Optional CLIP similarity retries and library deprecation/device warnings are distinct from failed jobs. VAE slicing now uses the supported VAE API.

External network outages, unavailable runners and new upstream changes cannot be ruled out. Failures should remain bounded, visible, and recoverable without bypassing validation or inserting duplicate YouTube videos.
