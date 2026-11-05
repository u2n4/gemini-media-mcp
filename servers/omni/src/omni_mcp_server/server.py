"""
Gemini Omni MCP Server — Gemini Omni Video Generation
Professional-grade MCP server with async job pattern.

Architecture:
  - omni_generate_video() starts generation in background, returns job_id instantly
  - omni_check_job() reads job progress; workers poll file status and download
  - Background threads handle the long-running Google API calls
  - No more timeout issues — each MCP call returns in < 5 seconds
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
import time
import logging
import threading
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, TypedDict

from google import genai
from google.genai import interactions
from mcp.server.fastmcp import FastMCP

from .core.validation import (
    validate_file_path,
    validate_output_path,
    validate_video_uri,
)

# ── Logging ──────────────────────────────────────────────────────────────────
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[OMNI] %(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S"))
handler.setLevel(logging.INFO)
log = logging.getLogger("omni")
log.setLevel(logging.INFO)
log.addHandler(handler)
log.propagate = False

# ── Configuration ────────────────────────────────────────────────────────────
_RAW_KEYS = [
    os.environ.get("GEMINI_API_KEY", ""),
    os.environ.get("GEMINI_API_KEY_BACKUP", ""),
]
API_KEYS: list[str] = [k for k in _RAW_KEYS if k.strip()]

VIDEO_OUTPUT_DIR: str = os.environ.get(
    "VIDEO_OUTPUT_DIR",
    str(Path.home() / "omni-videos"),
)

# ── API Key Rotation Manager ────────────────────────────────────────────────

class OmniClientManager:
    """Manages multiple Gemini API keys with automatic rotation on 429."""

    def __init__(self, api_keys: list[str]):
        self.api_keys = api_keys
        self.clients = [genai.Client(api_key=k) for k in api_keys]
        self.current_index = 0
        self._lock = threading.Lock()
        log.info("Initialized with %d API key(s)", len(api_keys))

    @property
    def client(self) -> genai.Client:
        return self.clients[self.current_index]

    @property
    def api_key(self) -> str:
        return self.api_keys[self.current_index]

    def rotate(self) -> bool:
        """Switch to the next API key. Returns False if all keys exhausted."""
        with self._lock:
            next_idx = self.current_index + 1
            if next_idx < len(self.clients):
                self.current_index = next_idx
                log.info("Rotated to API key #%d of %d", next_idx + 1, len(self.clients))
                return True
            return False

    def reset(self):
        """Reset back to the first API key (e.g. after quota window resets)."""
        with self._lock:
            self.current_index = 0
            log.info("Reset to API key #1")

    @property
    def status(self) -> str:
        return (
            f"API Keys: {len(self.clients)} configured\n"
            f"Active: Key #{self.current_index + 1}\n"
            f"Keys remaining: {len(self.clients) - self.current_index}"
        )


_manager: Optional[OmniClientManager] = None
_manager_lock = threading.Lock()

_output_path: Optional[Path] = None
_output_path_lock = threading.Lock()


def _get_manager() -> OmniClientManager:
    """Lazy accessor for the Omni client manager (thread-safe double-checked locking)."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                if not API_KEYS:
                    raise RuntimeError("GEMINI_API_KEY is required to generate videos or access the API.")
                _manager = OmniClientManager(API_KEYS)
    return _manager


def _get_output_path() -> Path:
    """Lazy accessor for the video output directory (thread-safe double-checked locking)."""
    global _output_path
    if _output_path is None:
        with _output_path_lock:
            if _output_path is None:
                p = Path(VIDEO_OUTPUT_DIR).resolve()
                p.mkdir(parents=True, exist_ok=True)
                log.info("Video output directory: %s", p)
                _output_path = p
    return _output_path


# ── MCP Server ───────────────────────────────────────────────────────────────
mcp = FastMCP("omni_mcp")

# ── Constants ────────────────────────────────────────────────────────────────
MODELS = {
    "standard": "gemini-omni-1.2-flash",
    "fast": "gemini-omni-1.2-flash",
}

VALID_RESOLUTIONS = ("360p", "720p", "1080p", "4k")
VALID_ASPECTS = ("16:9", "9:16")
VALID_DURATIONS = tuple(range(3, 16))

POLL_INTERVAL = 10
FILE_POLL_TIMEOUT = 600

# ── Job Store ────────────────────────────────────────────────────────────────
# In-memory store for background generation jobs
jobs: dict[str, dict] = {}

# ── Helpers ──────────────────────────────────────────────────────────────────

class _GenerationOptions(TypedDict, total=False):
    generation_config: interactions.GenerationConfigParam


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _resolve_output(output_path: str | None, prefix: str = "omni") -> Path:
    if output_path:
        # Security: force .mp4 extension BEFORE validation so we validate the
        # actual path we intend to write.
        candidate = output_path
        if Path(candidate).suffix.lower() not in (".mp4", ".mov"):
            candidate = str(Path(candidate).with_suffix(".mp4"))
        # Defence-in-depth: validate even though the tool entry already did.
        p = validate_output_path(candidate)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return _get_output_path() / f"{prefix}_{_ts()}.mp4"


def _get_model(model_tier: str) -> str:
    tier = model_tier.lower().strip()
    if tier not in MODELS:
        raise ValueError(f"Invalid model_tier '{model_tier}'. Use 'standard' or 'fast'.")
    return MODELS[tier]


def _load_image(image_path: str) -> dict:
    """Validate a local image and encode it for the Interactions API."""
    p = validate_file_path(image_path)
    mime_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                  ".png": "image/png", ".webp": "image/webp"}
    return {"type": "image", "data": base64.b64encode(p.read_bytes()).decode("ascii"),
            "mime_type": mime_types[p.suffix.lower()]}


def _load_reference_images(reference_image_paths: str) -> list[dict]:
    """Load the legacy comma-separated reference paths as Omni image parts."""
    if not reference_image_paths.strip():
        return []
    paths = [p.strip() for p in reference_image_paths.split(",")]
    if not 1 <= len(paths) <= 6 or not all(paths):
        raise ValueError("reference_image_paths must contain 1 to 6 image paths")
    return [_load_image(p) for p in paths]


def _validate_duration(duration_seconds: int, maximum: int = 15) -> None:
    if type(duration_seconds) is not int or not 3 <= duration_seconds <= maximum:
        raise ValueError(f"duration_seconds must be an integer from 3 to {maximum}")


def _start_job(prompt, model, resolution, output_path, prefix, job_type, generate_fn) -> str:
    """Start a generation with the same job store, worker and download handling."""
    if output_path:
        validate_output_path(output_path)
    _get_manager()
    output_file = _resolve_output(output_path or None, prefix)
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "type": job_type, "status": "starting", "message": "Initializing...",
        "prompt": prompt[:100], "model": model, "resolution": resolution,
        "output_file": str(output_file), "started_at": datetime.now().isoformat(),
    }
    threading.Thread(target=_run_generation_job,
                     args=(job_id, generate_fn, output_file), daemon=True).start()
    return (f"Video generation started!\n  Job ID: {job_id}\n  Model: {model}\n"
            f'Use omni_check_job(job_id="{job_id}") to check progress.')


def _call_with_rotation(fn):
    """Call fn(). On 429 / RESOURCE_EXHAUSTED, rotate API key and retry once."""
    try:
        return fn()
    except Exception as exc:
        err = str(exc)
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "rate limit" in err.lower():
            log.warning("Key #%d quota exhausted, attempting rotation...", _get_manager().current_index + 1)
            if _get_manager().rotate():
                log.info("Retrying with key #%d...", _get_manager().current_index + 1)
                return fn()
            raise RuntimeError(
                f"All {len(_get_manager().clients)} API key(s) exhausted! "
                "Retry after your Gemini quota is available."
            ) from exc
        raise


# ── Background Worker Functions ──────────────────────────────────────────────


def _save_video(interaction, output_file: Path, client) -> list[str]:
    """Save inline output or poll a URI-delivered file before SDK download.

    Shape verified against https://aistudio.google.com/docs/omni and SDK 2.34.0.
    """
    video = interaction.output_video
    if video is None:
        raise RuntimeError("Omni returned no output_video.")
    if video.data:
        data = base64.b64decode(video.data, validate=True)
        if not data:
            raise RuntimeError("Omni returned an empty video.")
        output_file.write_bytes(data)
    elif video.uri:
        uri = validate_video_uri(video.uri)
        file_name = "files/" + uri.rstrip("/").split("/")[-1]
        deadline = time.monotonic() + FILE_POLL_TIMEOUT
        while True:
            info = client.files.get(name=file_name)
            state = getattr(info.state, "name", info.state)
            if state == "ACTIVE":
                break
            if state == "FAILED":
                raise RuntimeError("Omni video file processing FAILED.")
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for Omni video file to become ACTIVE.")
            time.sleep(POLL_INTERVAL)
        client.files.download(file=uri, destination=str(output_file))
        if not output_file.exists() or output_file.stat().st_size == 0:
            raise RuntimeError("Omni video download produced an empty file.")
    else:
        raise RuntimeError("Omni output_video has neither data nor uri.")
    return [str(output_file)]


def _run_generation_job(job_id: str, generate_fn, output_file: Path):
    """
    Background worker that runs the full generation pipeline.
    Updates the job store with progress and final result.
    """
    job = jobs[job_id]
    try:
        job["status"] = "generating"
        job["message"] = "Sending request to Gemini Omni Interactions API..."
        client, interaction = _call_with_rotation(generate_fn)
        # Preserve Omni provenance for extension of inline and URI-delivered jobs.
        if getattr(interaction, "id", None):
            job["interaction_id"] = interaction.id
        if interaction.output_video is not None and interaction.output_video.uri:
            job["video_uri"] = interaction.output_video.uri
        job["status"] = "downloading"
        job["message"] = "Waiting for video processing and download..."
        saved_paths = _save_video(interaction, output_file, client)

        # Step 5: Done!
        total_size = sum(Path(p).stat().st_size for p in saved_paths)
        size_mb = total_size / (1024 * 1024)
        job["status"] = "completed"
        job["result_paths"] = saved_paths  # NEW: All paths
        job["result_path"] = saved_paths[0]  # Backward compat
        job["size_mb"] = round(size_mb, 1)
        if len(saved_paths) == 1:
            job["message"] = f"Done! {Path(saved_paths[0]).name} ({size_mb:.1f} MB)"
        else:
            job["message"] = f"Done! {len(saved_paths)} videos ({size_mb:.1f} MB total)"
        log.info("[Job %s] COMPLETED: %s", job_id[:8], saved_paths)

    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        job["message"] = f"Failed: {exc}"
        log.error("[Job %s] FAILED: %s", job_id[:8], exc, exc_info=True)
        sys.stderr.flush()


# ── MCP Tools ────────────────────────────────────────────────────────────────

@mcp.tool(name="omni_generate_video")
def omni_generate_video(
    prompt: str,
    model_tier: str = "standard",
    resolution: str = "1080p",
    aspect_ratio: str = "16:9",
    duration_seconds: int = 10,
    output_path: str = "",
    reference_image_paths: str = "",
) -> str:
    """Generate an Omni video; returns a job ID for omni_check_job.

    standard and fast are compatibility aliases for gemini-omni-1.2-flash.
    Duration is 3-15 seconds; resolution is 360p, 720p, 1080p or 4k.
    reference_image_paths: Comma-separated paths to 1-6 subject reference images.
    """
    model = _get_model(model_tier)
    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {VALID_RESOLUTIONS}")
    if aspect_ratio not in VALID_ASPECTS:
        raise ValueError(f"aspect_ratio must be one of {VALID_ASPECTS}")
    _validate_duration(duration_seconds)
    references = _load_reference_images(reference_image_paths)
    if output_path:
        validate_output_path(output_path)
    _get_manager()  # Fail synchronously with a useful missing-key error.
    output_file = _resolve_output(output_path or None, "t2v")
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "type": "text-to-video", "status": "starting", "message": "Initializing...",
        "prompt": prompt[:100], "model": model, "resolution": resolution,
        "output_file": str(output_file), "started_at": datetime.now().isoformat(),
    }

    def generate_fn():
        client = _get_manager().client
        options: _GenerationOptions = {}
        if references:
            options["generation_config"] = {"video_config": {"task": "reference_to_video"}}
        interaction = client.interactions.create(
            model=model,
            input=references + [{"type": "text", "text": prompt}] if references else prompt,
            response_format={"type": "video", "duration": f"{duration_seconds}s",
                             "aspect_ratio": aspect_ratio, "resolution": resolution,
                             "delivery": "uri"},
            **options,
        )
        return client, interaction

    threading.Thread(target=_run_generation_job,
                     args=(job_id, generate_fn, output_file), daemon=True).start()
    return (f"Video generation started!\n  Job ID: {job_id}\n  Model: {model}\n"
            f"  Duration: {duration_seconds}s\n"
            f'Use omni_check_job(job_id="{job_id}") to check progress.')


@mcp.tool(name="omni_check_job")
def omni_check_job(job_id: str) -> str:
    """Check the status of a Omni video generation job.

    Call this repeatedly (every 15-20 seconds) until status is 'completed' or 'failed'.

    Args:
        job_id: The job ID returned by omni_generate_video or other generation tools.

    Returns:
        Current job status with details.
    """
    if job_id not in jobs:
        return f"Job not found: {job_id}\nAvailable jobs: {list(jobs.keys())}"

    job = jobs[job_id]
    status = job["status"]

    lines = [
        f"Job: {job_id[:8]}...",
        f"  Type: {job.get('type', 'unknown')}",
        f"  Status: {status}",
        f"  Message: {job.get('message', '')}",
    ]

    if status == "completed":
        # NEW: Show batch results if multiple videos
        result_paths = job.get("result_paths", [])
        if len(result_paths) > 1:
            lines.append(f"  Files ({len(result_paths)} videos):")
            for rp in result_paths:
                lines.append(f"    - {rp}")
        else:
            lines.append(f"  File: {job.get('result_path', '')}")
        lines.append(f"  Size: {job.get('size_mb', 0)} MB")
        # NEW: Show seed if used
        if job.get("seed") is not None:
            lines.append(f"  Seed: {job['seed']}")
        lines.append("Video is ready!")
    elif status == "failed":
        lines.extend([
            f"  Error: {job.get('error', 'Unknown error')}",
        ])

    return "\n".join(lines)


@mcp.tool(name="omni_list_jobs")
def omni_list_jobs() -> str:
    """List all video generation jobs and their current status.

    Returns:
        Summary of all jobs.
    """
    if not jobs:
        return "No jobs yet. Use omni_generate_video to start one."

    lines = ["Active Jobs:", "-" * 50]
    for jid, job in sorted(jobs.items(), key=lambda x: x[1].get("started_at", ""), reverse=True):
        status_icon = {
            "starting": "...",
            "generating": "...",
            "downloading": "...",
            "completed": "OK",
            "failed": "ERR",
        }.get(job["status"], "?")
        lines.append(
            f"  [{status_icon}] {jid[:8]}  {job['status']:<12}  {job.get('type', ''):<16}  {job.get('message', '')[:40]}"
        )
    return "\n".join(lines)


@mcp.tool(name="omni_image_to_video")
def omni_image_to_video(
    prompt: str,
    image_path: str,
    model_tier: str = "standard",
    resolution: str = "1080p",
    aspect_ratio: str = "16:9",
    output_path: str = "",
    duration_seconds: int = 10,
) -> str:
    """Animate a local JPEG, PNG or WebP with Omni; poll using omni_check_job.

    standard and fast both select gemini-omni-1.2-flash. Duration: 3-15 seconds.
    """
    model = _get_model(model_tier)
    image = _load_image(image_path)
    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {VALID_RESOLUTIONS}")
    if aspect_ratio not in VALID_ASPECTS:
        raise ValueError(f"aspect_ratio must be one of {VALID_ASPECTS}")
    _validate_duration(duration_seconds)
    if output_path:
        validate_output_path(output_path)
    _get_manager()
    output_file = _resolve_output(output_path or None, "i2v")
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "type": "image-to-video", "status": "starting", "message": "Initializing...",
        "prompt": prompt[:100], "model": model, "resolution": resolution,
        "output_file": str(output_file), "started_at": datetime.now().isoformat(),
    }

    def generate_fn():
        client = _get_manager().client
        interaction = client.interactions.create(
            model=model, input=[image, {"type": "text", "text": prompt}],
            response_format={"type": "video", "duration": f"{duration_seconds}s",
                             "aspect_ratio": aspect_ratio, "resolution": resolution,
                             "delivery": "uri"},
        )
        return client, interaction

    threading.Thread(target=_run_generation_job,
                     args=(job_id, generate_fn, output_file), daemon=True).start()
    return (f"Image-to-Video generation started!\n  Job ID: {job_id}\n  Model: {model}\n"
            f'Use omni_check_job(job_id="{job_id}") to check progress.')


@mcp.tool(name="omni_extend_video")
def omni_extend_video(
    prompt: str,
    source_job_id: str = "",
    video_uri: str = "",
    output_path: str = "",
    duration_seconds: int = 10,
) -> str:
    """Extend an Omni video by 3-10 seconds (default 10), up to 30 seconds total.

    Provide a completed source_job_id or a Gemini Files API video_uri.
    Returns a job ID; poll with omni_check_job. Output resolution is 720p.
    """
    _validate_duration(duration_seconds, 10)
    previous_id = ""
    source_file = ""
    if source_job_id:
        if source_job_id not in jobs:
            return f"Source job not found: {source_job_id}\nAvailable jobs: {list(jobs.keys())}"
        source = jobs[source_job_id]
        if source.get("status") != "completed":
            return f"Source job is not completed yet (status: {source.get('status')}). Wait for it to finish."
        previous_id = source.get("interaction_id", "")
        video_uri = source.get("video_uri", "")
        if not previous_id and not video_uri:
            source_file = source.get("result_path", "")
            if not source_file or not Path(source_file).is_file():
                return "Source job has no interaction ID, video URI or local video file."
    elif not video_uri:
        return "Error: Must provide either source_job_id or video_uri."
    if video_uri:
        video_uri = validate_video_uri(video_uri)

    def generate_fn():
        client = _get_manager().client
        parts = []
        if not previous_id:
            uri = video_uri
            if source_file:
                uploaded_uri = client.files.upload(file=source_file).uri
                if not uploaded_uri:
                    raise RuntimeError("Source video upload returned no URI.")
                uri = validate_video_uri(uploaded_uri)
            parts.append({"type": "video", "uri": uri})
        parts.append({"type": "text", "text": prompt})
        interaction = client.interactions.create(
            model=MODELS["standard"], input=parts,
            generation_config={"video_config": {"task": "extend"}},
            response_format={"type": "video", "duration": f"{duration_seconds}s",
                             "resolution": "720p", "delivery": "uri"},
            **({"previous_interaction_id": previous_id} if previous_id else {}),
        )
        return client, interaction

    return _start_job(prompt, MODELS["standard"], "720p", output_path,
                      "ext", "extend-video", generate_fn)


@mcp.tool(name="omni_interpolate_video")
def omni_interpolate_video(
    prompt: str,
    first_frame_path: str,
    last_frame_path: str,
    model_tier: str = "standard",
    resolution: str = "1080p",
    output_path: str = "",
    duration_seconds: int = 10,
) -> str:
    """Generate a 3-10 second transition between first and last frame images.

    Images must be local JPEG, PNG or WebP files. Returns a job ID for omni_check_job.
    standard and fast both select gemini-omni-1.2-flash.
    """
    _validate_duration(duration_seconds, 10)
    model = _get_model(model_tier)
    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {VALID_RESOLUTIONS}")
    first = _load_image(first_frame_path)
    last = _load_image(last_frame_path)

    def generate_fn():
        client = _get_manager().client
        interaction = client.interactions.create(
            model=model, input=[first, last, {"type": "text", "text": prompt}],
            generation_config={"video_config": {"task": "image_to_video"}},
            response_format={"type": "video", "duration": f"{duration_seconds}s",
                             "resolution": resolution, "delivery": "uri"},
        )
        return client, interaction

    return _start_job(prompt, model, resolution, output_path,
                      "interp", "interpolate", generate_fn)


@mcp.tool(name="omni_show_output_stats")
def omni_show_output_stats() -> str:
    """Show statistics about generated videos and active/recent jobs.

    Returns:
        Summary of video count, total size, file details, and job statuses.
    """
    lines = []

    # ── Job Status Section ──
    if jobs:
        lines.append("=== Active/Recent Jobs ===")
        for jid, job in sorted(jobs.items(), key=lambda x: x[1].get("started_at", ""), reverse=True):
            status = job.get("status", "unknown")
            msg = job.get("message", "")
            err = job.get("error", "")
            path = job.get("result_path", "")
            started = job.get("started_at", "?")
            lines.append(f"  [{jid[:8]}] status={status}  started={started}")
            if msg:
                lines.append(f"           message: {msg}")
            if err:
                lines.append(f"           ERROR: {err}")
            if path:
                lines.append(f"           path: {path}")
        lines.append("")

    # ── Video Files Section ──
    videos = list(_get_output_path().glob("*.mp4"))
    if not videos:
        lines.append(f"No videos found in {_get_output_path()}")
        return "\n".join(lines) if lines else f"No videos found in {_get_output_path()}"

    total_size = sum(v.stat().st_size for v in videos)
    total_mb = total_size / (1024 * 1024)

    lines.append(f"=== Video Output Stats - {_get_output_path()} ===")
    lines.append("-" * 60)
    lines.append(f"  Total videos: {len(videos)}")
    lines.append(f"  Total size:   {total_mb:.1f} MB")
    lines.append("-" * 60)

    videos.sort(key=lambda v: v.stat().st_mtime, reverse=True)
    for v in videos:
        stat = v.stat()
        size_mb = stat.st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"  {v.name:<40} {size_mb:>6.1f} MB   {mod_time}")

    return "\n".join(lines)


@mcp.tool(name="omni_pricing_info")
def omni_pricing_info() -> str:
    """Link to current Omni pricing; see the official documentation for rates."""
    return "Gemini Omni pricing: https://aistudio.google.com/docs/omni (check current pricing)."


@mcp.tool(name="omni_api_status")
def omni_api_status() -> str:
    """Show current API key rotation status.

    Displays how many keys are configured, which key is currently active,
    and how many remain before all keys are exhausted.

    Returns:
        API key status summary.
    """
    lines = [
        "=== Omni API Key Status ===",
        f"  Keys configured: {len(_get_manager().clients)}",
        f"  Currently using: Key #{_get_manager().current_index + 1}",
        f"  Keys remaining: {len(_get_manager().clients) - _get_manager().current_index}",
        "",
        "Rotation behavior:",
        "  - On 429 (quota exhausted), automatically switches to next key",
        "  - Quotas depend on the Gemini project and model",
    ]
    return "\n".join(lines)


# ── Entry Point ──────────────────────────────────────────────────────────────
def main():
    """Entry point for the MCP server."""
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="omni-mcp-server",
        description="Gemini Omni MCP Server — video generation via Gemini Omni",
        add_help=True,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    # parse_known_args so MCP framework args (if any) are forwarded unchanged
    _known, _remaining = parser.parse_known_args()

    log.info("Starting Gemini Omni MCP Server (async job pattern)...")
    mcp.run()


if __name__ == "__main__":
    main()
