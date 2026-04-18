# NanoBanana MCP Server

MCP server for AI image generation using NanoBanana Pro 2. Supports Pro (maximum quality) and Flash (fast generation) models with default 4K resolution.

Inspired by the nano-banana naming convention used across the MCP community. This is an independent implementation.

## What It Does

Generates AI images using NanoBanana Pro 2 models. Supports text-to-image generation, image editing with reference images, file uploads, and server maintenance. Produces high-quality images at up to 4K resolution.

## Tools (4)

| Tool | Description |
|------|-------------|
| `generate_image` | Generate images using NanoBanana Pro 2. Supports model selection (Pro/Flash), aspect ratio, resolution (up to 4K), negative prompts, thinking level, grounding, reference images, and batch generation. |
| `upload_file` | Upload a reference image for use in image editing or conditioning. |
| `show_output_stats` | Display statistics about generated images — count, total size, file details. |
| `maintenance` | Server maintenance and cleanup — clear caches, remove temporary files, optimize storage. |

## Models

| Model | Engine | Best For |
|-------|--------|----------|
| Pro | Gemini 3 Pro Image | Maximum quality, complex scenes, photorealism |
| Flash | Gemini 3.1 Flash Image | Fast generation, simple scenes, quick iterations |

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Gemini API key (required) | -- |

## Claude Desktop Configuration

### From pip (recommended)

```bash
pip install nanobanana-imagen-mcp
```

```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "python",
      "args": ["-m", "nanobanana_mcp_server.server"],
      "env": {
        "GEMINI_API_KEY": "your_key_here"
      }
    }
  }
}
```

### From this repository

```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "python",
      "args": ["-m", "servers.nanobanana.nanobanana_mcp_server.server"],
      "env": {
        "GEMINI_API_KEY": "your_key_here"
      },
      "cwd": "path/to/gemini-media-mcp"
    }
  }
}
```

## Features

- Default 4K resolution for maximum detail
- Pro model for complex, photorealistic scenes
- Flash model for fast iterations and simple subjects
- Reference image support for consistent multi-angle shots
- Negative prompt support for quality control
- Thinking level control for complex multi-element scenes
- Google Search grounding for real-world subjects

## License

MIT

## Credits

Inspired by the nano-banana naming convention used across the MCP community. This is an independent implementation.
