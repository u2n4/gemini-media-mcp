# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and each sub-package (`servers/veo`, `servers/nanobanana`) follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-04-17

### Added
- `.editorconfig` for consistent cross-editor formatting
- `.gitattributes` enforcing LF line endings
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1)
- `SECURITY.md` disclosure policy
- GitHub Actions CI workflow (ruff + pyright + uv build against both sub-packages)
- PyPI Trusted Publisher publish workflow (OIDC, native `uv publish`)
- Dependabot weekly updates for both `servers/veo` + `servers/nanobanana` + GitHub Actions
- `<!-- mcp-name: io.github.u2n4/gemini-media-mcp -->` marker in README

### Changed
- GitHub username migrated from `alihsh0` to `u2n4` across all URLs, author metadata, plugin manifests, and clone commands
- Sub-package versions synchronized for this launch (VEO `1.0.0` → `1.1.0`, NanoBanana `0.3.4` → `1.1.0`)
- Removed dead reference to `setup.py` in README — replaced with uvx-first install instructions
- Incorporated upstream rebrand from `71986a6`: Gemini Imagen 3 → NanoBanana Pro 2 marketing name across description strings, README, llms.txt, marketplace.json, plugin.json
- NanoBanana PyPI distribution renamed `nanobanana-mcp-server` → `nanobanana-imagen-mcp` (the original slot was occupied by an unrelated package on PyPI); module name `nanobanana_mcp_server` is unchanged
- Removed broken upstream attribution to `https://github.com/nano-banana/mcp-server` (404); replaced with neutral "inspired by the nano-banana naming convention" note

### Fixed
- README "Auto-Setup" instructions referenced a `setup.py` file that did not exist in the repository

## [1.0.0] - 2026-03-07

### Added
- VEO 3.1 MCP Server with 9 tools for AI video generation
- NanoBanana MCP Server with 4 tools for AI image generation
- VEO Prompting Skill — 7-layer professional video prompt engineering
- NanoBanana Prompting Skill — 7-layer professional image prompt engineering
- Claude Code Plugin Marketplace support
- Comprehensive documentation and installation guides
