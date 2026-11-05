# Changelog

## [1.2.0] — 2026-11-05

- Replace `gemini-3-pro-image-preview` with `gemini-3-pro-image`.
- Replace `gemini-3.1-flash-image-preview` with `gemini-nano-banana-2.1` in defaults and model metadata.
- `gemini-3.1-flash-image` is listed as Stable; Flash uses the preview replacement above.
- Cap dependencies to `fastmcp>=4,<5` and `google-genai>=2.5.0,<3`; sync requirements and lockfile.
- Fix FastMCP 4 `ToolResult` import paths; four tools register with FastMCP 4.1.6.
- Missing API-key authentication errors explicitly name GEMINI_API_KEY.
- Add fake image-client, missing-key and in-process MCP tool-list tests; remove dummy environment keys from smoke tests.
- Update package and MCP Registry metadata to 1.2.0.
- Gemini paths were tested only with a fake client and never live. No API key was available.
- Pyright remains nonblocking: 62 existing errors require a separate typing cleanup.
