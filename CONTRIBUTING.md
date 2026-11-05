# Contributing to Gemini Media MCP

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/gemini-media-mcp.git
   cd gemini-media-mcp
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Omni Server

```bash
cd servers/omni
pip install -r requirements.txt
```

### NanoBanana Server

```bash
cd servers/nanobanana
pip install -r requirements.txt
```

Both servers require a `GEMINI_API_KEY` environment variable. Copy `.env.example` to `.env` and fill in your key.

## Making Changes

### Code Style

- Follow PEP 8 for Python code.
- Use type hints where possible.
- Keep functions small and focused (under 50 lines).
- Handle errors explicitly with clear messages.
- Never hardcode secrets, API keys, or user-specific paths.

### Commit Messages

Use conventional commit format:

```
feat: add new video resolution option
fix: handle API timeout gracefully
docs: update Omni tool parameter descriptions
refactor: extract download logic into helper
test: add unit tests for key rotation
```

### Pull Requests

1. Ensure your code follows the style guidelines above.
2. Update documentation if you changed any tool parameters or behavior.
3. Run offline tests with GEMINI_API_KEY, GOOGLE_API_KEY and GEMINI_API_KEY_BACKUP unset; tests use fake clients and block network calls.
4. Write a clear PR description explaining what changed and why.
5. Reference any related issues.

## Project Structure

```
gemini-media-mcp/
├── servers/
│   ├── omni/               # Gemini Omni MCP Server
│   │   ├── src/omni_mcp_server/server.py  # Main server code
│   │   └── requirements.txt
│   └── nanobanana/         # NanoBanana MCP Server
│       ├── nanobanana_mcp_server/  # Package
│       └── requirements.txt
├── skills/                 # Prompting skills (source of truth)
│   ├── omni-prompting/
│   └── nanobanana-prompting/
├── plugins/                # Claude Code Plugin Marketplace packages
│   ├── omni-prompting/
│   └── nanobanana-prompting/
└── .claude-plugin/         # Marketplace manifest
```

## Reporting Issues

- Use GitHub Issues to report bugs or request features.
- Include steps to reproduce for bugs.
- Include error messages and log output when applicable.
- Specify which server (Omni or NanoBanana) is affected.

## Security

- Never commit API keys, tokens, or secrets.
- Never commit user-specific file paths.
- If you discover a security issue, please report it privately via GitHub Security Advisories.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
