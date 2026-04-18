<!-- mcp-name: io.github.u2n4/gemini-media-mcp -->
<div align="center">
  <img src="assets/banner.png" alt="Gemini Media MCP" width="100%">

  <h1>Gemini Media MCP</h1>
  <p><strong>All-in-one MCP toolkit for AI media generation -- VEO 3.1 video + NanoBanana Pro 2 images + prompting skills</strong></p>

  <p>
    <a href="#"><img src="https://img.shields.io/badge/MCP-Compatible-blue?style=for-the-badge" alt="MCP"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT"></a>
    <a href="#"><img src="https://img.shields.io/badge/Claude_Code-Plugin-purple?style=for-the-badge" alt="Claude Code"></a>
    <a href="#"><img src="https://img.shields.io/badge/Gemini-Powered-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini"></a>
  </p>

  <p>
    <a href="#whats-included">What's Included</a> &bull;
    <a href="#quick-start">Quick Start</a> &bull;
    <a href="#veo-server">VEO Server</a> &bull;
    <a href="#nanobanana-server">NanoBanana Server</a> &bull;
    <a href="#prompting-skills">Skills</a> &bull;
    <a href="#contributing">Contributing</a>
  </p>
</div>

---

## What is This?

Gemini Media MCP is a comprehensive toolkit that brings Google's most powerful AI media generation models into any MCP-compatible AI assistant. Generate 4K videos with VEO 3.1, create stunning images with NanoBanana Pro 2, and craft professional prompts with built-in skills -- all from a single repository.

## What's Included

### MCP Servers

| Server | Description | Tools |
|--------|-------------|-------|
| **VEO 3.1** | AI video generation (text-to-video, image-to-video, extend, interpolate) | 9 tools |
| **NanoBanana** | AI image generation with NanoBanana Pro 2 (Pro + Flash models) | 4 tools |

### Claude Code Skills (Plugin Marketplace)

| Skill | Description |
|-------|-------------|
| **VEO Prompting** | 7-layer prompt engineering for cinematic VEO 3.1 videos |
| **NanoBanana Prompting** | 7-layer prompt engineering for photorealistic NanoBanana Pro 2 images |

Install skills via Claude Code:
```
/plugin marketplace add u2n4/gemini-media-mcp
```

## Quick Start

This repo hosts **two independent MCP servers**. Install whichever you need — or both. Each server publishes to PyPI separately.

### Option A — `uvx` (zero-install, recommended)

Add a block to your MCP client config (Claude Desktop, Claude Code, Cursor, VS Code, Windsurf) using the appropriate server block below (see VEO Server / NanoBanana Server sections).

### Option B — clone + editable install

```bash
git clone https://github.com/u2n4/gemini-media-mcp.git
cd gemini-media-mcp

# Install one or both sub-packages
uv pip install -e servers/veo
uv pip install -e servers/nanobanana
```

### VEO Server

**uvx (zero-install):**
```json
{
  "mcpServers": {
    "veo": {
      "command": "uvx",
      "args": ["veo-mcp-server"],
      "env": {
        "GEMINI_API_KEY": "your_key",
        "VIDEO_OUTPUT_DIR": "./videos"
      }
    }
  }
}
```

**Claude Code:**
```bash
claude mcp add veo -s user -e GEMINI_API_KEY=your_key -- uvx veo-mcp-server
```

**pip install:**
```bash
pip install veo-mcp-server
```

### NanoBanana Server

**uvx (zero-install):**
```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "uvx",
      "args": ["nanobanana-imagen-mcp"],
      "env": {
        "GEMINI_API_KEY": "your_key"
      }
    }
  }
}
```

**Claude Code:**
```bash
claude mcp add nanobanana -s user -e GEMINI_API_KEY=your_key -- uvx nanobanana-imagen-mcp
```

**pip install:**
```bash
pip install nanobanana-imagen-mcp
```

## VEO Server

AI video generation powered by Google VEO 3.1. Uses an async job pattern where generation starts in the background and returns a job ID for polling -- no timeouts.

### Tools

| Tool | Description |
|------|-------------|
| `veo_generate_video` | Generate video from text prompt. Supports 720p/1080p/4K, 16:9 or 9:16, 4/6/8 second duration, negative prompts, reference images, seed control, and batch generation (1-4 videos). |
| `veo_image_to_video` | Animate a reference image with a motion prompt. |
| `veo_interpolate_video` | Create smooth transition between two frames (first frame + last frame). |
| `veo_extend_video` | Extend an existing VEO video by ~7 seconds. 720p only, max 148 seconds total. |
| `veo_check_job` | Check async job status. Call every 15-20 seconds until completed or failed. |
| `veo_list_jobs` | List all generation jobs and their current status. |
| `veo_api_status` | Check API key status -- keys configured, active key, keys remaining. |
| `veo_pricing_info` | Show pricing per second for standard and fast models at all resolutions. |
| `veo_show_output_stats` | Display generation statistics -- video count, total size, file details, job statuses. |

### VEO Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Primary API key (required) | -- |
| `GEMINI_API_KEY_BACKUP` | Backup key for auto-rotation | -- |
| `VIDEO_OUTPUT_DIR` | Output directory for videos | `~/veo-videos` |

### VEO Models

| Tier | Model | Best For |
|------|-------|----------|
| Standard | `veo-3.1-generate-preview` | Higher quality output |
| Fast | `veo-3.1-fast-generate-preview` | Quicker generation |

## NanoBanana Server

AI image generation powered by NanoBanana Pro 2. Supports Pro (maximum quality) and Flash (fast) models with default 4K resolution.

### Tools

| Tool | Description |
|------|-------------|
| `generate_image` | Generate images using NanoBanana Pro 2 (Pro or Flash). Supports aspect ratio, resolution (up to 4K), negative prompts, thinking level, grounding, and reference images. |
| `upload_file` | Upload reference image for editing or conditioning. |
| `show_output_stats` | Display generation statistics -- image count, total size, file details. |
| `maintenance` | Server maintenance and cleanup -- clear caches, remove temporary files. |

### Models

| Model | Engine | Best For |
|-------|--------|----------|
| Pro | Gemini 3 Pro Image | Maximum quality, complex scenes |
| Flash | Gemini 3.1 Flash Image | Fast generation, simple scenes |

## Prompting Skills

### VEO Prompting Skill
7-layer prompt engineering system for VEO 3.1:
1. Cinematography (camera, shot type, lens, angles)
2. Subject (characters, objects, material cues)
3. Action (force-based verbs, timestamp beats)
4. Environment (time of day, weather, depth layers)
5. Lighting & Mood (physical light sources, color temperature)
6. Audio Design (dialogue, SFX, ambient, music)
7. Technical Controls (negative prompts, style anchors, film stocks)

### NanoBanana Prompting Skill
7-layer prompt engineering system for NanoBanana Pro 2:
1. Style & Art Direction (visual DNA)
2. Scene Description (environment, atmosphere)
3. Main Subject (hero element with extreme specificity)
4. Camera & Lens (real camera specs for realism)
5. Lighting (natural, studio, color temperature)
6. Texture, Material & Color (tactile detail)
7. Negative Prompts (quality guards)

## Architecture

```
gemini-media-mcp/
├── servers/
│   ├── veo/                       # VEO 3.1 MCP Server (PyPI: veo-mcp-server)
│   │   ├── pyproject.toml
│   │   ├── requirements.txt
│   │   └── src/
│   │       └── veo_mcp_server/
│   │           ├── __init__.py
│   │           ├── __main__.py
│   │           └── server.py
│   └── nanobanana/                # NanoBanana MCP Server (PyPI: nanobanana-imagen-mcp)
│       ├── pyproject.toml
│       ├── requirements.txt
│       └── nanobanana_mcp_server/ # Package
├── skills/
│   ├── veo-prompting/             # VEO prompting skill
│   │   └── SKILL.md
│   └── nanobanana-prompting/      # NanoBanana prompting skill
│       └── SKILL.md
├── plugins/                       # Claude Code Plugin Marketplace
│   ├── veo-prompting/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── veo-prompting/
│   │           └── SKILL.md
│   └── nanobanana-prompting/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/
│           └── nanobanana-prompting/
│               └── SKILL.md
├── .claude-plugin/
│   └── marketplace.json
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── llms.txt
└── llms-install.md
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT -- see [LICENSE](LICENSE).

## Credits

- NanoBanana MCP Server: inspired by the nano-banana naming convention used across the MCP community. This is an independent implementation.
- VEO 3.1 by Google DeepMind

## Support

If you find this useful, please star this repository!

---

Made with ❤️ in the Eastern Province of Saudi Arabia.
