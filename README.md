<!-- mcp-name: io.github.u2n4/gemini-media-mcp -->
<div align="center">
  <img src="assets/banner.png" alt="Gemini Media MCP" width="100%">

  <h1>Gemini Media MCP</h1>
  <p><strong>All-in-one MCP toolkit for AI media generation -- Gemini Omni video + NanoBanana Pro 2 images + prompting skills</strong></p>

  <p>
    <a href="https://pypi.org/project/omni-mcp-server/"><img src="https://img.shields.io/pypi/v/omni-mcp-server?style=for-the-badge&logo=pypi&logoColor=white&label=omni" alt="PyPI omni-mcp-server"></a>
    <a href="https://pypi.org/project/nanobanana-imagen-mcp/"><img src="https://img.shields.io/pypi/v/nanobanana-imagen-mcp?style=for-the-badge&logo=pypi&logoColor=white&label=nanobanana" alt="PyPI nanobanana-imagen-mcp"></a>
    <a href="#"><img src="https://img.shields.io/badge/MCP-Compatible-blue?style=for-the-badge" alt="MCP"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT"></a>
    <a href="#"><img src="https://img.shields.io/badge/Claude_Code-Plugin-purple?style=for-the-badge" alt="Claude Code"></a>
    <a href="#"><img src="https://img.shields.io/badge/Gemini-Powered-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini"></a>
  </p>

  <p>
    <a href="#whats-included">What's Included</a> &bull;
    <a href="#quick-start">Quick Start</a> &bull;
    <a href="#omni-server">Omni Server</a> &bull;
    <a href="#nanobanana-server">NanoBanana Server</a> &bull;
    <a href="#prompting-skills">Skills</a> &bull;
    <a href="#contributing">Contributing</a>
  </p>
</div>

---

| CLI | Install check | Version check |
|-----|---------------|---------------|
| `omni-mcp-server` | `omni-mcp-server --help` | `omni-mcp-server --version` |
| `nanobanana-imagen-mcp` | `nanobanana-imagen-mcp --help` | `nanobanana-imagen-mcp --version` |

---

`veo-mcp-server` is replaced by `omni-mcp-server` 2.0.0; update client commands and tool names (see [migration notes](servers/omni/CHANGELOG.md)).

## What is This?

Gemini Media MCP is a comprehensive toolkit that brings Google's most powerful AI media generation models into any MCP-compatible AI assistant. Generate videos with Gemini Omni, create stunning images with NanoBanana Pro 2, and craft professional prompts with built-in skills -- all from a single repository.

## What's Included

### MCP Servers

| Server | Description | Tools |
|--------|-------------|-------|
| **Gemini Omni** | AI video generation, reference images, extension and first/last-frame interpolation | 9 tools |
| **NanoBanana** | AI image generation with NanoBanana Pro 2 (Pro + Flash models) | 4 tools |

### Claude Code Skills (Plugin Marketplace)

| Skill | Description |
|-------|-------------|
| **Omni Prompting** | 7-layer prompt engineering for Gemini Omni video prompts |
| **NanoBanana Prompting** | 7-layer prompt engineering for photorealistic NanoBanana Pro 2 images |

Install skills via Claude Code:
```
/plugin marketplace add u2n4/gemini-media-mcp
```

## Quick Start

This repo hosts **two independent MCP servers**. Install whichever you need — or both. Each server publishes to PyPI separately.

### Option A — `uvx` (zero-install, recommended)

Add a block to your MCP client config (Claude Desktop, Claude Code, Cursor, VS Code, Windsurf) using the appropriate server block below (see Omni Server / NanoBanana Server sections).

### Option B — clone + editable install

```bash
git clone https://github.com/u2n4/gemini-media-mcp.git
cd gemini-media-mcp

# Each server needs its own environment (different MCP major versions).
uv sync --project servers/omni
uv sync --project servers/nanobanana

uv run --project servers/omni omni-mcp-server --help
uv run --project servers/nanobanana nanobanana-imagen-mcp --help
```

### Omni Server

**uvx (zero-install):**
```json
{
  "mcpServers": {
    "omni": {
      "command": "uvx",
      "args": ["omni-mcp-server"],
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
claude mcp add omni -s user -e GEMINI_API_KEY=your_key -- uvx omni-mcp-server
```

**pip install:**
```bash
pip install omni-mcp-server
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

## Omni Server

AI video generation powered by `gemini-omni-1.2-flash` through the Interactions API. Uses an async job pattern where generation starts in the background and returns a job ID for polling -- no timeouts.

### Tools

| Tool | Description |
|------|-------------|
| `omni_generate_video` | Generate from text: 3–15 seconds (default 10), 360p/720p/1080p/4k, 16:9 or 9:16. Optional comma-separated `reference_image_paths` accepts 1–6 subject images. Returns a background job ID. |
| `omni_image_to_video` | Animate a JPEG, PNG or WebP with a text prompt; same duration, resolution and aspect options. |
| `omni_extend_video` | Extend a completed `source_job_id` or Gemini Files API `video_uri`; 3–10 seconds per turn (default 10), 720p, up to 30 seconds total (API enforced). Returns a job ID. |
| `omni_interpolate_video` | Transition between `first_frame_path` and `last_frame_path`; 3–10 seconds (default 10), 360p/720p/1080p/4k. Returns a job ID. |
| `omni_check_job` | Check async job status. Call every 15-20 seconds until completed or failed. |
| `omni_list_jobs` | List all generation jobs and their current status. |
| `omni_api_status` | Check API key status -- keys configured, active key, keys remaining. |
| `omni_pricing_info` | Link to current Gemini Omni pricing documentation. |
| `omni_show_output_stats` | Display generation statistics -- video count, total size, file details, job statuses. |

### Omni Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Primary API key (required) | -- |
| `GEMINI_API_KEY_BACKUP` | Backup key for auto-rotation | -- |
| `VIDEO_OUTPUT_DIR` | Output directory for videos | `~/omni-videos` |

### Omni Models

| Tier | Model | Best For |
|------|-------|----------|
| Standard | `gemini-omni-1.2-flash` | Default model |
| Fast | `gemini-omni-1.2-flash` | Compatibility alias; same model as Standard |

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
| Pro | `gemini-3-pro-image` | Maximum quality, complex scenes |
| Flash | `gemini-nano-banana-2.1` | Fast generation, simple scenes |

## Prompting Skills

### Omni Prompting Skill
Prompt planning guidance for Gemini Omni:
1. Cinematography (camera, shot type, lens, angles)
2. Subject (characters, objects, material cues)
3. Action (force-based verbs, timestamp beats)
4. Environment (time of day, weather, depth layers)
5. Lighting & Mood (physical light sources, color temperature)
6. Continuity (reference images, first/last frames and extension)
7. Tool Controls (duration, resolution, aspect ratio and output path)

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
│   ├── omni/                       # Gemini Omni Video MCP Server (PyPI: omni-mcp-server)
│   │   ├── pyproject.toml
│   │   ├── requirements.txt
│   │   └── src/
│   │       └── omni_mcp_server/
│   │           ├── __init__.py
│   │           ├── __main__.py
│   │           └── server.py
│   └── nanobanana/                # NanoBanana MCP Server (PyPI: nanobanana-imagen-mcp)
│       ├── pyproject.toml
│       ├── requirements.txt
│       └── nanobanana_mcp_server/ # Package
├── skills/
│   ├── omni-prompting/             # Omni prompting skill
│   │   └── SKILL.md
│   └── nanobanana-prompting/      # NanoBanana prompting skill
│       └── SKILL.md
├── plugins/                       # Claude Code Plugin Marketplace
│   ├── omni-prompting/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── omni-prompting/
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
- Gemini Omni by Google DeepMind

## Support

If you find this useful, please star this repository!

---

Made with ❤️ in the Eastern Province of Saudi Arabia.

## Refresh verification — 2026-11-05

Gemini paths were tested only with a fake client and never live. Both API keys
were unset for all test runs; tests block real SDK clients and HTTP requests.
Omni extension/interpolation and reference-image request shapes were checked
against [Google's Omni docs](https://aistudio.google.com/docs/omni),
[full docs](https://aistudio.google.com/llms-full.txt) and installed SDK source.
Legacy video seed, batch and negative-prompt shapes remain unconfirmed and unavailable.
NanoBanana starts and lists tools without credentials; Gemini-dependent tools
return a clear error naming `GEMINI_API_KEY` when no key is configured.
`gemini-3.1-flash-image` is also listed as Stable; this server's Flash route uses
the documented preview replacement `gemini-nano-banana-2.1`.

Omni uses `mcp>=1.0.0,<2`; NanoBanana uses `fastmcp>=4,<5`. Install them in
separate environments or use their independent `uvx` commands. Both cap
`google-genai>=2.5.0,<3`. See each server's CHANGELOG for migration details.
