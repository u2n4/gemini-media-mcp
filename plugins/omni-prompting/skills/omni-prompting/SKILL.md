---
name: omni-prompting
description: Use when preparing Gemini Omni video requests with omni_generate_video, omni_image_to_video, omni_extend_video or omni_interpolate_video.
---

# Gemini Omni Video Prompting

## Tool selection and controls

Read the current tool schema before calling a tool. These are the controls exposed
by this server; they are not a promise of output quality or exact prompt adherence.

| Tool | Input and constraints |
|------|-----------------------|
| `omni_generate_video` | Text prompt; optional comma-separated `reference_image_paths` for 1–6 local subject images. Duration 3–15 seconds, default 10. |
| `omni_image_to_video` | Text prompt and one local JPEG, PNG or WebP. Duration 3–15 seconds, default 10. |
| `omni_extend_video` | Completed `source_job_id` or validated Gemini Files API `video_uri`. Duration 3–10 seconds per turn, default 10; 720p; API enforces 30 seconds total. |
| `omni_interpolate_video` | Text prompt plus ordered `first_frame_path` and `last_frame_path` images. Duration 3–10 seconds, default 10. |

Text, single-image and interpolation tools accept `360p`, `720p`, `1080p` or `4k`.
Text and single-image tools accept `16:9` or `9:16`; interpolation has no aspect-ratio
parameter. `standard` and `fast` both select `gemini-omni-1.2-flash`.
All generation tools return a job ID. Poll `omni_check_job` until completed or failed;
use `omni_list_jobs` to inspect jobs. Save to `output_path` when supplied by the user;
otherwise the server uses `VIDEO_OUTPUT_DIR` (default `~/omni-videos`).

Do not pass seed, batch, negative-prompt or audio configuration parameters: these
are not exposed by this wrapper. Do not promise native dialogue, synchronized audio,
precise timing, deterministic output or character consistency without confirming
that behavior in the current official documentation. Uploaded-video extension has
regional and speech-related constraints; consult the official extension section.

## Prompt planning: seven layers

Use these as creative suggestions, not model-specific guarantees:

1. **Cinematography:** choose framing and one camera movement, such as a wide
   establishing shot with a slow dolly-in. Describe camera and subject motion separately.
2. **Subject:** describe the person, object or scene clearly. Repeat key visual
   attributes across related clips when continuity matters.
3. **Action:** describe observable motion using concrete verbs. Keep the action
   manageable within the selected duration; avoid competing instructions.
4. **Environment:** specify place, time of day, background activity and depth.
5. **Lighting and mood:** name physical light sources and a coherent visual style.
6. **Continuity:** use a source image, subject references, first/last frames or a
   completed job when the selected tool supports them. Describe what should change.
7. **Tool controls:** choose duration, resolution, supported aspect ratio and output
   path as tool arguments. Do not invent parameters or rely on prose to override them.

## Examples

### Text to video

Prompt: "Wide shot, slow dolly-in. A hiker wearing a red jacket stands at a canyon
rim at sunrise. Wind moves the jacket as the hiker turns toward the horizon.
Mist drifts through the valley; warm sunlight catches the rock faces."

Use `omni_generate_video` with `duration_seconds=10`, `resolution="1080p"`,
`aspect_ratio="16:9"`. Add reference paths only when local images are available.

### Animate an image

Prompt: "The camera moves slowly closer. The subject turns toward the window;
curtains move gently in the breeze. Maintain the source composition and lighting."

Use `omni_image_to_video` with `image_path` pointing to a local JPEG, PNG or WebP.
Focus on motion instead of repeating every visible detail in the image.

### Continue a completed clip

Prompt: "Continue the camera movement as the subject walks toward the doorway.
Keep the same lighting and visual style."

Use `omni_extend_video` with the completed `source_job_id` and a duration from
3 to 10 seconds. The server reuses the interaction ID or video URI, or uploads an
older job's local result. Do not assume an unlimited number of extensions.

### First/last-frame transition

Describe a plausible motion connecting the two compositions. Call
`omni_interpolate_video` with `first_frame_path`, `last_frame_path` and a duration
from 3 to 10 seconds. Both frames must be local JPEG, PNG or WebP files.

## NanoBanana and multi-clip workflow

When requested, generate reference frames with NanoBanana, animate them with the
appropriate Omni tool, and wait for each job to complete before using its result.
For a finished montage, inspect the saved clips before trimming or joining them
with FFmpeg. Add separately sourced audio during editing if the user requests it;
do not promise generated audio based on prompt wording alone.

## Sources and verification boundary

- [Google's Omni documentation](https://aistudio.google.com/docs/omni)
- [Extension constraints](https://aistudio.google.com/docs/omni#extension-constraints)
- [Server controls and migration notes](https://github.com/u2n4/gemini-media-mcp/tree/main/servers/omni)

The repository verifies request shapes with fake clients and the installed SDK.
Offline tests do not establish live availability or visual/audio quality.
