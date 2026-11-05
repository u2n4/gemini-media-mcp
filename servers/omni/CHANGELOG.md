# Changelog

## [Unreleased] — 2026-11-06

- Upgrade MCP to 2.3.0 and use its documented MCPServer API; preserve all nine
  omni_* tool names and update the SDK tool-schema test accessor.
- Upgrade all dependencies and the lockfile; synchronize bounded requirements.
  Use google-genai 2.34.0 on Python 3.11+, retaining 2.33.0 on Python 3.10.
- Reject Windows device paths, normalize doubled POSIX roots, protect credential
  paths after resolution, and match allowed video URI hosts as well as prefixes.
- Revalidate the actual video destination at save time and try every remaining
  API key on quota failures; propagate non-quota errors without rotation.
- Reject unknown CLI flags instead of silently discarding them; strengthen CLI
  smoke tests to check import completion and absent-key/default-output behavior.
- Add optional secret API-key metadata to the MCP Registry manifest.
- Add Python 3.14 CI, current released Actions and clean uvx initialize/tools-list
  checks. Test both Python 3.10 and 3.14 without credentials or live Gemini calls.


All notable changes to `omni-mcp-server` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.0] — 2026-11-05

- `omni-mcp-server` replaces `veo-mcp-server`; this is a breaking naming change.
- Rename the server folder to `servers/omni`, package to `omni_mcp_server`,
  console script to `omni-mcp-server`, and prompting plugin/skill to `omni-prompting`.
- Update client configurations to the new distribution, command and tool names;
  old names are no longer registered. Gemini Omni request behavior is unchanged.
- Default output directory is now `~/omni-videos`; the generic file prefix is `omni`.
  Set `VIDEO_OUTPUT_DIR` to keep an existing output location.
- Release tags use `omni-v*.*.*`. Python 3.10 remains supported.

| Old tool name | New tool name |
|---------------|---------------|
| `veo_generate_video` | `omni_generate_video` |
| `veo_image_to_video` | `omni_image_to_video` |
| `veo_extend_video` | `omni_extend_video` |
| `veo_interpolate_video` | `omni_interpolate_video` |
| `veo_check_job` | `omni_check_job` |
| `veo_list_jobs` | `omni_list_jobs` |
| `veo_api_status` | `omni_api_status` |
| `veo_pricing_info` | `omni_pricing_info` |
| `veo_show_output_stats` | `omni_show_output_stats` |

## [1.2.0] — 2026-11-05

- Migrate text and image video tools to `gemini-omni-1.2-flash` using Interactions.
- Keep background jobs; decode inline video or poll URI files until ACTIVE and download via SDK.
- Support 3–15 seconds (default 10), 360p/720p/1080p/4k, and 16:9/9:16.
- `standard` and `fast` remain compatibility aliases for the same Omni model.
- Restore `veo_extend_video` on Omni with the `extend` task: accept a completed
  source job or validated video URI; retain interaction IDs for multi-turn continuation.
- Restore `veo_interpolate_video` with ordered first/last image parts and the
  `image_to_video` task. Both restored tools enforce integer durations of 3–10 seconds.
- Restore comma-separated `reference_image_paths` on `veo_generate_video`, using
  up to 6 image parts and the `reference_to_video` task.
- Leave legacy seed, batch and negative-prompt parameters unavailable: their
  Omni video-specific behavior/request shape is not confirmed by the Omni docs.
- Replace the legacy video-object cache/expiry handling with Omni interaction IDs,
  video URIs and a local-result upload fallback for older completed jobs.
- Remove old operations polling, destructive file cleanup and HTTP download fallbacks.
- Missing credentials now raise an error naming GEMINI_API_KEY instead of exiting.
- Cap MCP to `>=1.0.0,<2` and google-genai to `>=2.5.0,<3`; sync requirements.
- Gemini paths tested only with a fake client, never live; no API key available.
- Request shape: https://aistudio.google.com/docs/omni and installed google-genai 2.34.0.

## [1.1.3] — 2026-04-19

### Security

- **Add `validate_output_path` to all video-generation tools** (addresses Codex
  Security threat-model 3.4 — arbitrary filesystem write). `veo_generate_video`,
  `veo_image_to_video`, `veo_extend_video`, `veo_interpolate_video` now reject
  `output_path` values that resolve into blocked system directories
  (`C:\Windows`, `C:\Program Files`, `/etc`, `/usr`, `/bin`, ...) or sensitive
  user subdirectories (`~/.ssh`, `~/.aws`, `~/.gnupg`, `~/.docker`, `~/.kube`,
  `~/.config/gh`, ...). Also rejects path traversal (`..`), NUL bytes, over-long
  paths, and non-video file extensions.
- **Add `validate_file_path` to all tools that accept image paths**
  (`image_path`, `first_frame_path`, `last_frame_path`, `reference_image_paths`).
  Prevents arbitrary file read / exfiltration of local secrets through
  prompt-injected paths. Enforces image-only extensions (`.png`, `.jpg`,
  `.jpeg`, `.webp`) and a 50 MB size cap.
- **Add `validate_video_uri` to `veo_extend_video`**. User-supplied `video_uri`
  is now allowlisted to Gemini Files API and Vertex AI hosts, rejecting
  `file://`, `ftp://`, plain `http://`, credential-bearing URIs, and cloud
  metadata endpoints (addresses threat-model 3.1 SSRF surface).
- **Move API key from URL query string to `x-goog-api-key` header** across all
  four internal httpx call sites (addresses threat-model 3.5 — leakage via
  proxy logs, TLS-inspection middleboxes, crash dumps, browser history). This
  is the long-standing HIGH-severity residual risk; a single authorization
  path now runs through the header transport.

### Added

- `src/veo_mcp_server/core/validation.py` — new security module with
  `validate_output_path`, `validate_file_path`, `validate_video_uri`,
  and `ValidationError`.
- `tests/test_validation.py` — 28 tests covering every validator plus one
  tool-level rejection test per tool (4 tool tests).

### Changed

- `_resolve_output` now validates `output_path` before creating directories
  (dual-validation pattern: tool entry → utility function).
- `_load_image` now calls `validate_file_path` before touching the filesystem.
- `_download_via_uri` simplified — removed the URL-query-param fallback path
  (security regression). Header-based auth is now the only path.

### Security notes for operators

- `output_path` that targeted `~/.ssh/authorized_keys.mp4` or
  `C:\Windows\System32\evil.mp4` previously SUCCEEDED (no validation shipped
  in 1.1.2's wheel). They now raise `ValidationError` before any FS operation.
- The `x-goog-api-key` header switch is transparent to end users; no
  configuration changes are required.

## [1.1.2] — prior releases

See git history.
