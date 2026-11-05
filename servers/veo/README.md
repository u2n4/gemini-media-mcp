# Gemini Omni Video MCP Server

<!-- mcp-name: io.github.u2n4/veo-mcp-server -->

MCP server for Gemini Omni video generation with background jobs, API key rotation, and SDK downloads.

## Quick Install

```bash
pip install veo-mcp-server
# or
uvx veo-mcp-server --help
```

**Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "veo": {
      "command": "uvx",
      "args": ["veo-mcp-server"],
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
| `VIDEO_OUTPUT_DIR` | Directory where generated videos are saved | `~/veo-videos` |

## What It Does

Generates videos using `gemini-omni-1.2-flash` through the Interactions API. Supports text-to-video and image-to-video. Uses an async job pattern where generation starts immediately in the background and returns a job ID for polling.

## Tools (7)

| Tool | Description |
|------|-------------|
| `veo_generate_video` | Generate from text: 3–15 seconds (default 10), 360p/720p/1080p/4k, 16:9 or 9:16. Returns a background job ID. |
| `veo_image_to_video` | Animate a JPEG, PNG or WebP with a text prompt; same duration, resolution and aspect options. |
| `veo_check_job` | Check the status of an async video generation job. Call repeatedly until status is 'completed' or 'failed'. |
| `veo_list_jobs` | List all video generation jobs and their current status. |
| `veo_api_status` | Show current API key rotation status — keys configured, active key, keys remaining. |
| `veo_pricing_info` | Link to current Gemini Omni pricing documentation. |
| `veo_show_output_stats` | Display statistics about generated videos and active/recent jobs. |

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Primary Gemini API key (required) | -- |
| `GEMINI_API_KEY_BACKUP` | Backup key for automatic rotation on 429 | -- |
| `VIDEO_OUTPUT_DIR` | Directory where generated videos are saved | `~/veo-videos` |

## Architecture

- **Async Job Pattern**: All generation tools return a job ID instantly. Background threads handle the long-running Google API calls, so each MCP call returns in under 5 seconds.
- **API Key Rotation**: On 429/RESOURCE_EXHAUSTED, automatically switches to the backup key and retries.
- **SDK delivery**: request URI delivery, poll the file until ACTIVE, then use `client.files.download`. Inline base64 responses are also supported.

## Models

| Tier | Model ID | Use Case |
|------|----------|----------|
| Standard | `gemini-omni-1.2-flash` | Default model |
| Fast | `gemini-omni-1.2-flash` | Compatibility alias; same model as Standard |

## Migration and verification (1.2.0)

The VEO 3.1 preview models shut down on 2026-10-22. Existing tool names and
background jobs remain, but `veo_extend_video` and `veo_interpolate_video` were
removed. Seed, batch, negative-prompt and reference-image arguments were removed
from the retained generation tools. Duration now defaults to 10 seconds and is
validated without silently changing it.

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
