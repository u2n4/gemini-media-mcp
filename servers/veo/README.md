# VEO 3.1 MCP Server

Professional-grade MCP server for Google VEO 3.1 video generation with async job pattern, API key rotation, and multi-fallback download.

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

Generates AI videos using Google's VEO 3.1 model. Supports text-to-video, image-to-video, video extension, and frame interpolation. Uses an async job pattern where generation starts immediately in the background and returns a job ID for polling.

## Tools (9)

| Tool | Description |
|------|-------------|
| `veo_generate_video` | Generate video from a text prompt. Supports resolution (720p/1080p/4K), aspect ratio (16:9/9:16), duration (4/6/8s), negative prompts, reference images, seed control, and batch generation (1-4 videos). |
| `veo_image_to_video` | Animate a reference image with a text prompt. Supports resolution, aspect ratio, reference images, and seed control. |
| `veo_interpolate_video` | Create a smooth video transition between a first frame and a last frame image. |
| `veo_extend_video` | Extend an existing VEO-generated video by ~7 seconds. 720p only, max 148 seconds total. Source must be from a previous VEO generation (tracks provenance server-side). |
| `veo_check_job` | Check the status of an async video generation job. Call repeatedly until status is 'completed' or 'failed'. |
| `veo_list_jobs` | List all video generation jobs and their current status. |
| `veo_api_status` | Show current API key rotation status — keys configured, active key, keys remaining. |
| `veo_pricing_info` | Show VEO 3.1 pricing per second of generated video for both standard and fast models at all resolutions. |
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
- **3-Layer Download Fallback**: SDK download -> URI fallback -> Wait-for-ACTIVE state. Handles Google's Files API edge cases.
- **Preventive Cleanup**: Deletes stuck PROCESSING files before each generation to prevent cascading 500 errors.

## Models

| Tier | Model ID | Use Case |
|------|----------|----------|
| Standard | `veo-3.1-generate-preview` | Higher quality output |
| Fast | `veo-3.1-fast-generate-preview` | Quicker generation |

## License

MIT
