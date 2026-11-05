# Gemini Omni Video MCP Server

<!-- mcp-name: io.github.u2n4/omni-mcp-server -->

MCP server for Gemini Omni video generation with background jobs, API key rotation, and SDK downloads.

## Quick Install

```bash
pip install omni-mcp-server
# or
uvx omni-mcp-server --help
```

**Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "omni": {
      "command": "uvx",
      "args": ["omni-mcp-server"],
      "env": {
        "GEMINI_API_KEY": "your_key_here"
      }
    }
  }
}
```

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Gemini API key — required for all generation | -- |
| `GEMINI_API_KEY_BACKUP` | Backup key for automatic rotation on 429 | -- |
| `VIDEO_OUTPUT_DIR` | Directory where generated videos are saved | `~/omni-videos` |

## What It Does

Generates videos using `gemini-omni-1.2-flash` through the Interactions API. Supports text-to-video, image-to-video, extension, first/last-frame interpolation and subject reference images. Generation runs in the background and returns a job ID for polling.

## Tools (9)

| Tool | Description |
|------|-------------|
| `omni_generate_video` | Generate from text: 3–15 seconds (default 10), 360p/720p/1080p/4k, 16:9 or 9:16. Optional comma-separated `reference_image_paths` accepts 1–6 subject images. Returns a background job ID. |
| `omni_image_to_video` | Animate a JPEG, PNG or WebP with a text prompt; same duration, resolution and aspect options. |
| `omni_extend_video` | Continue a completed `source_job_id` or Gemini Files API `video_uri`; 3–10 seconds per turn (default 10), 720p, up to 30 seconds total. Returns a job ID. |
| `omni_interpolate_video` | Transition from `first_frame_path` to `last_frame_path` (JPEG/PNG/WebP); 3–10 seconds (default 10), 360p/720p/1080p/4k. Returns a job ID. |
| `omni_check_job` | Check the status of an async video generation job. Call repeatedly until status is 'completed' or 'failed'. |
| `omni_list_jobs` | List all video generation jobs and their current status. |
| `omni_api_status` | Show current API key rotation status — keys configured, active key, keys remaining. |
| `omni_pricing_info` | Link to current Gemini Omni pricing documentation. |
| `omni_show_output_stats` | Display statistics about generated videos and active/recent jobs. |

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Primary Gemini API key (required) | -- |
| `GEMINI_API_KEY_BACKUP` | Backup key for automatic rotation on 429 | -- |
| `VIDEO_OUTPUT_DIR` | Directory where generated videos are saved | `~/omni-videos` |

## Architecture

- **Async Job Pattern**: All generation tools return a job ID instantly. Background threads handle the long-running Google API calls, so each MCP call returns in under 5 seconds.
- **API Key Rotation**: On 429/RESOURCE_EXHAUSTED, automatically switches to the backup key and retries.
- **SDK delivery**: request URI delivery, poll the file until ACTIVE, then use `client.files.download`. Inline base64 responses are also supported.

## Models

| Tier | Model ID | Use Case |
|------|----------|----------|
| Standard | `gemini-omni-1.2-flash` | Default model |
| Fast | `gemini-omni-1.2-flash` | Compatibility alias; same model as Standard |

## Migration and verification (2.0.0)

The distribution, command and all nine tools have new names in 2.0.0;
see the [migration table](CHANGELOG.md#200--2026-11-05). Background jobs,
extension and first/last-frame interpolation retain their Omni behavior. `reference_image_paths` is available on `omni_generate_video`.
Legacy seed, batch and negative-prompt parameters remain unavailable because the
Omni docs do not confirm their video-specific behavior/request shape. Duration
defaults to 10 seconds and is validated without silently changing it: 3–15 for
text/single-image generation, 3–10 for extension/interpolation.

Extension reuses the source job's Omni interaction ID, or its video URI; older
completed jobs with only a local result are uploaded through the Files API.
Google enforces the 30-second total length limit. Uploaded-video extension has
regional restrictions and cannot add dialogue to an uploaded clip with speech;
see [Google's extension constraints](https://aistudio.google.com/docs/omni#extension-constraints).

Use a separate environment from NanoBanana: this server requires `mcp>=1.0.0,<2`
and `google-genai>=2.5.0,<3`. Clean startup checked with MCP 1.27.0 and SDK 2.34.0.

Request/response shapes verified against [Google's Omni docs](https://aistudio.google.com/docs/omni),
[full docs](https://aistudio.google.com/llms-full.txt), and installed SDK source.
Gemini paths were tested only with a fake client and never live. No API key was available.

```bash
env -u GEMINI_API_KEY -u GOOGLE_API_KEY -u GEMINI_API_KEY_BACKUP uv run --locked pytest tests -q
```

## License

MIT
