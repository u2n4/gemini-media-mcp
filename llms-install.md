# Gemini Media MCP -- Installation Guide

## Prerequisites

- Python 3.10 or higher
- A Google Gemini API key (get one at https://aistudio.google.com/apikey)

## VEO 3.1 Server

### Install dependencies

```bash
pip install google-genai mcp httpx
```

### Configure for Claude Desktop

Add to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "veo": {
      "command": "python",
      "args": ["/absolute/path/to/gemini-media-mcp/servers/veo/server.py"],
      "env": {
        "GEMINI_API_KEY": "your_gemini_api_key",
        "VIDEO_OUTPUT_DIR": "./videos"
      }
    }
  }
}
```

### Configure for Claude Code

```bash
claude mcp add veo -- python /absolute/path/to/gemini-media-mcp/servers/veo/server.py
```

Set environment variables:
```bash
export GEMINI_API_KEY=your_gemini_api_key
export VIDEO_OUTPUT_DIR=./videos
```

## NanoBanana Server

### Option A: Install from pip (recommended)

```bash
pip install nanobanana-imagen-mcp
```

Configure for Claude Desktop:
```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "python",
      "args": ["-m", "nanobanana_mcp_server.server"],
      "env": {
        "GEMINI_API_KEY": "your_gemini_api_key"
      }
    }
  }
}
```

### Option B: Use bundled version from this repo

```bash
cd gemini-media-mcp/servers/nanobanana
pip install -r requirements.txt
```

Configure for Claude Desktop:
```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "python",
      "args": ["-m", "servers.nanobanana.nanobanana_mcp_server.server"],
      "env": {
        "GEMINI_API_KEY": "your_gemini_api_key"
      },
      "cwd": "/absolute/path/to/gemini-media-mcp"
    }
  }
}
```

## Prompting Skills (Claude Code Plugin)

### Install via Plugin Marketplace

```
/plugin marketplace add u2n4/gemini-media-mcp
```

This installs both the VEO Prompting and NanoBanana Prompting skills.

### Manual Installation

Copy the skill files to your Claude Code skills directory:

```bash
# VEO Prompting
cp skills/veo-prompting/SKILL.md ~/.claude/skills/veo-prompting/SKILL.md

# NanoBanana Prompting
cp skills/nanobanana-prompting/SKILL.md ~/.claude/skills/nanobanana-prompting/SKILL.md
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Your Google Gemini API key |
| `GEMINI_API_KEY_BACKUP` | No | Backup API key for automatic rotation |
| `VIDEO_OUTPUT_DIR` | No | Directory for VEO video output (default: ~/veo-videos) |

## Verification

After setup, verify the servers are working:

1. **VEO**: Ask Claude to run `veo_api_status` -- it should show your key configuration.
2. **NanoBanana**: Ask Claude to run `show_output_stats` -- it should show the output directory.
