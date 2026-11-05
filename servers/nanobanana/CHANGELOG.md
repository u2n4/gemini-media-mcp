# Changelog

## [Unreleased] — 2026-11-06

- Allow absolute upload paths on POSIX and Windows. Resolve tilde and symlink
  targets; reject traversal, device paths, system directories and credential paths.
- Validate local image content and the 20 MiB input limit before encoding/upload;
  validate resolved output destinations without rejecting innocent prefix matches.
- Honor explicit Flash resolution using the SDK image configuration.
- Preserve generation errors, align preview/metadata results, return full edited
  images in the legacy storage service, reserve file names atomically and validate extensions.
- Preserve corrupt registries, save registry replacements atomically, confine registry
  reads/deletes to storage, and flatten transparent previews onto white.
- Fix edited-image output-directory creation, Windows replacement writes, FIPS-safe
  hashing and repeated output indices when response image counts vary.
- Serialize database upserts, close file connections, explicitly serialize timestamps,
  normalize aware expiry times, and report actual database-hygiene dry-run counts.
- Handle absent file sizes/MIME metadata, PROCESSING files, failed tracking updates
  and actual Files API MIME types. Retain progress percentages on failure/cancel.
- Mark generation/maintenance tools as mutating, sanitize upload errors and log
  identifiers, honor CLI transport flags, validate configuration enums, and expand output tilde.
- Correct prompting examples, reference/output-path guidance and advisory-control descriptions.
- Upgrade all dependencies and the lockfile; synchronize requirements with bounded
  direct dependencies. Use google-genai 2.34.0/Pillow 13 on Python 3.11+, retaining
  the latest Python 3.10-compatible releases (2.33.0/12.3.0).
- Add Python 3.14 CI, current released Actions, registry API-key metadata and cold
  uvx initialize/tools-list checks. Fix isolated cold-install smoke diagnostics/cleanup.
- Add offline regression coverage; tests use fake clients with credentials absent.


## [1.2.0] — 2026-11-05

- Replace `gemini-3-pro-image-preview` with `gemini-3-pro-image`.
- Replace `gemini-3.1-flash-image-preview` with `gemini-nano-banana-2.1` in defaults and model metadata.
- `gemini-3.1-flash-image` is listed as Stable; Flash uses the preview replacement above.
- Cap dependencies to `fastmcp>=4,<5` and `google-genai>=2.5.0,<3`; sync requirements and lockfile.
- Fix FastMCP 4 `ToolResult` import paths; four tools register with FastMCP 4.1.6.
- Missing API-key authentication errors explicitly name GEMINI_API_KEY.
- Start and list tools without an API key; defer credential checks to Gemini use.
- Propagate authentication failures from image generation instead of returning an
  empty successful result; test both app factories and Flash/Pro/upload tool calls.
- Add fake image-client, missing-key and in-process MCP tool-list tests; remove dummy environment keys from smoke tests.
- Update package and MCP Registry metadata to 1.2.0.
- Gemini paths were tested only with a fake client and never live. No API key was available.
- Pyright remains nonblocking: 62 existing errors require a separate typing cleanup.
