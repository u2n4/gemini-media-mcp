"""
VEO 3.1 MCP Server — Google Veo Video Generation
Professional-grade MCP server with async job pattern.

Architecture:
  - veo_generate_video() starts generation in background, returns job_id instantly
  - veo_check_job() polls job status and downloads when ready
  - Background threads handle the long-running Google API calls
  - No more timeout issues — each MCP call returns in < 5 seconds
"""

from __future__ import annotations

import os
import sys
import time
import logging
import threading
import uuid
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional

from google import genai
from google.genai import types
from mcp.server.fastmcp import FastMCP

# ── Logging ──────────────────────────────────────────────────────────────────
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[VEO] %(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S"))
handler.setLevel(logging.INFO)
log = logging.getLogger("veo")
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
    str(Path.home() / "veo-videos"),
)

if not API_KEYS:
    log.error("No GEMINI_API_KEY environment variables set!")
    sys.exit(1)

OUTPUT_PATH = Path(VIDEO_OUTPUT_DIR).resolve()
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
log.info("Video output directory: %s", OUTPUT_PATH)


# ── API Key Rotation Manager ────────────────────────────────────────────────

class VEOClientManager:
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


manager = VEOClientManager(API_KEYS)

# ── MCP Server ───────────────────────────────────────────────────────────────
mcp = FastMCP("veo_mcp")

# ── Constants ────────────────────────────────────────────────────────────────
MODELS = {
    "standard": "veo-3.1-generate-preview",
    "fast": "veo-3.1-fast-generate-preview",
}

VALID_RESOLUTIONS = ("720p", "1080p", "4k")
VALID_ASPECTS = ("16:9", "9:16")
VALID_DURATIONS = (4, 6, 8)

POLL_INTERVAL = 10
DOWNLOAD_MAX_RETRIES = 3
DOWNLOAD_RETRY_DELAY = 15

# ── Job Store ────────────────────────────────────────────────────────────────
# In-memory store for background generation jobs
jobs: dict[str, dict] = {}

# NEW: Video object store for extension support
# Stores actual Video objects from completed generations for reliable extension
video_objects: dict[str, object] = {}  # job_id -> types.Video object


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _resolve_output(output_path: str | None, prefix: str = "veo") -> Path:
    if output_path:
        p = Path(output_path)
        if p.suffix.lower() != ".mp4":
            p = p.with_suffix(".mp4")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return OUTPUT_PATH / f"{prefix}_{_ts()}.mp4"


def _get_model(model_tier: str) -> str:
    tier = model_tier.lower().strip()
    if tier not in MODELS:
        raise ValueError(f"Invalid model_tier '{model_tier}'. Use 'standard' or 'fast'.")
    return MODELS[tier]


def _load_image(image_path: str):
    """Load a local image file as a types.Image for VEO generation.

    Uses keyword argument 'location=' as required by SDK v1.63.0+.
    """
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    return types.Image.from_file(location=str(p))


# NEW: Reference images support
def _load_reference_images(reference_image_paths: str) -> list:
    """Load reference images from comma-separated paths for video style guidance.

    Each image is loaded as a VideoGenerationReferenceImage with ASSET type.
    NOTE: Reference images only work with Vertex AI, not Gemini Developer API.

    Args:
        reference_image_paths: Comma-separated file paths to reference images.

    Returns:
        List of VideoGenerationReferenceImage objects, or empty list.

    Raises:
        ValueError: If more than 3 images provided.
        FileNotFoundError: If any image file doesn't exist.
    """
    if not reference_image_paths or not reference_image_paths.strip():
        return []

    paths = [p.strip() for p in reference_image_paths.split(",") if p.strip()]
    if len(paths) > 3:
        raise ValueError(f"Maximum 3 reference images allowed, got {len(paths)}")

    ref_images = []
    for p in paths:
        img = _load_image(p)  # reuse existing helper
        ref_images.append(types.VideoGenerationReferenceImage(
            image=img,
            reference_type="ASSET",
        ))
    log.info("Loaded %d reference image(s)", len(ref_images))
    return ref_images


# NEW: Detect Gemini Developer API vs Vertex AI
# Seed and reference_images only work on Vertex AI, not Gemini Developer API
_IS_VERTEX_AI = not bool(API_KEYS)  # API keys = Gemini Developer API; no keys = Vertex AI


# NEW: Seed validation
def _validate_seed(seed: int) -> Optional[int]:
    """Validate and return seed value, or None if random.

    NOTE: Seed is only supported on Vertex AI. On Gemini Developer API,
    the seed is stored for reference but not sent to the API.
    """
    if seed < 0:
        return None
    if seed > 4294967295:
        raise ValueError(f"seed must be 0-4294967295, got {seed}")
    return seed


def _seed_for_config(validated_seed: Optional[int]) -> Optional[int]:
    """Return seed for GenerateVideosConfig, or None if not supported."""
    if validated_seed is None:
        return None
    if not _IS_VERTEX_AI:
        log.info("Seed %d requested but not supported on Gemini Developer API (Vertex AI only). Ignoring.", validated_seed)
        return None
    return validated_seed


def _call_with_rotation(fn):
    """Call fn(). On 429 / RESOURCE_EXHAUSTED, rotate API key and retry once."""
    try:
        return fn()
    except Exception as exc:
        err = str(exc)
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "rate limit" in err.lower():
            log.warning("Key #%d quota exhausted, attempting rotation...", manager.current_index + 1)
            if manager.rotate():
                log.info("Retrying with key #%d...", manager.current_index + 1)
                return fn()
            raise RuntimeError(
                f"All {len(manager.clients)} API key(s) exhausted! "
                "VEO quota resets at midnight Pacific time (08:00 UTC)."
            ) from exc
        raise


# ── Background Worker Functions ──────────────────────────────────────────────

def _poll_operation(operation):
    """Poll until generation completes."""
    elapsed = 0
    while not operation.done:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        operation = manager.client.operations.get(operation)
        log.info("  Still generating... (%ds elapsed)", elapsed)
    log.info("Generation complete after ~%ds", elapsed)
    return operation


def _cleanup_old_files():
    """Delete stuck PROCESSING files to prevent quota exhaustion.

    Google's Files API can return 500 errors when too many files accumulate
    in PROCESSING state. This preventive cleanup runs before each generation.
    """
    try:
        with httpx.Client(timeout=15.0) as http:
            base = "https://generativelanguage.googleapis.com/v1beta"
            deleted = 0
            for _ in range(10):  # Max 10 files per cleanup
                resp = http.get(f"{base}/files", params={"key": manager.api_key, "pageSize": 1})
                if resp.status_code != 200:
                    break
                files = resp.json().get("files", [])
                if not files:
                    break
                for f in files:
                    name = f.get("name", "")
                    state = f.get("state", "")
                    if state == "PROCESSING":
                        dr = http.delete(f"{base}/{name}", params={"key": manager.api_key})
                        if dr.status_code == 200:
                            deleted += 1
                            log.info("Cleaned up stuck file: %s", name)
            if deleted:
                log.info("Cleaned up %d stuck file(s)", deleted)
    except Exception as exc:
        log.debug("File cleanup skipped: %s", exc)


def _download_via_uri(video_file, output_file: Path) -> bool:
    """Fallback: download video directly from its URI using httpx."""
    uri = getattr(video_file, 'uri', None)
    if not uri:
        log.warning("No URI found on video file object.")
        return False

    log.info("Fallback download from URI: %s", uri[:80])
    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as http:
            # Try with API key in query param (confirmed workaround for project mismatch)
            download_url = f"{uri}&key={manager.api_key}" if "?" in uri else f"{uri}?key={manager.api_key}"
            resp = http.get(download_url)
            if resp.status_code == 200 and len(resp.content) > 10000:
                output_file.write_bytes(resp.content)
                log.info("URI+key download succeeded: %d bytes", len(resp.content))
                return True

            # Try with API key in header
            resp = http.get(uri, headers={"x-goog-api-key": manager.api_key})
            if resp.status_code == 200 and len(resp.content) > 10000:
                output_file.write_bytes(resp.content)
                log.info("URI+header download succeeded: %d bytes", len(resp.content))
                return True

            log.warning("URI download returned: %d (%d bytes)", resp.status_code, len(resp.content))
            return False
    except Exception as exc:
        log.warning("Fallback URI download failed: %s", exc)
        return False


def _wait_for_active_and_download(video_file, output_file: Path, max_wait: int = 120) -> bool:
    """Wait for file to become ACTIVE, then download."""
    uri = getattr(video_file, 'uri', None)
    if not uri or '/files/' not in uri:
        return False

    file_id = uri.split('/files/')[1].split(':')[0].split('?')[0]
    file_name = f"files/{file_id}"
    base = "https://generativelanguage.googleapis.com/v1beta"

    log.info("Waiting for %s to become ACTIVE (max %ds)...", file_name, max_wait)
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as http:
            start = time.time()
            while time.time() - start < max_wait:
                resp = http.get(f"{base}/{file_name}", params={"key": manager.api_key})
                if resp.status_code == 200:
                    info = resp.json()
                    state = info.get("state", "?")
                    elapsed = int(time.time() - start)
                    log.info("  [%ds] state=%s", elapsed, state)

                    if state == "ACTIVE":
                        dl_uri = info.get("downloadUri", "")
                        if dl_uri:
                            r = http.get(dl_uri, headers={"x-goog-api-key": manager.api_key})
                            if r.status_code == 200 and len(r.content) > 10000:
                                output_file.write_bytes(r.content)
                                log.info("Downloaded via ACTIVE downloadUri: %d bytes", len(r.content))
                                return True
                        # Constructed URL
                        url = f"{base}/{file_name}:download?alt=media"
                        r = http.get(url, headers={"x-goog-api-key": manager.api_key})
                        if r.status_code == 200 and len(r.content) > 10000:
                            output_file.write_bytes(r.content)
                            log.info("Downloaded via ACTIVE constructed URL: %d bytes", len(r.content))
                            return True
                        return False
                    elif state == "FAILED":
                        log.error("File processing FAILED: %s", info.get("error", {}))
                        return False
                time.sleep(15)
    except Exception as exc:
        log.warning("Wait-for-ACTIVE failed: %s", exc)
    return False


def _save_video(operation, output_file: Path) -> list[str]:
    """Download and save video(s). Tries SDK method first, then multiple fallbacks.

    Returns list of saved file paths (one per generated video).
    """
    generated_videos = operation.response.generated_videos
    saved_paths = []

    for idx, generated_video in enumerate(generated_videos):
        video_file = generated_video.video

        # NEW: Determine target filename for batch generation
        if len(generated_videos) > 1:
            target = output_file.parent / f"{output_file.stem}_{idx + 1}.mp4"
        else:
            target = output_file

        log.info("Video %d/%d file object: uri=%s", idx + 1, len(generated_videos), getattr(video_file, 'uri', 'N/A'))

        saved = False
        # Method 1: Official SDK download
        for attempt in range(1, DOWNLOAD_MAX_RETRIES + 1):
            try:
                log.info("SDK download attempt %d/%d for video %d...", attempt, DOWNLOAD_MAX_RETRIES, idx + 1)
                manager.client.files.download(file=video_file)
                video_file.save(str(target))
                if target.exists() and target.stat().st_size > 0:
                    size_mb = target.stat().st_size / (1024 * 1024)
                    log.info("SDK download succeeded: %s (%.1f MB)", target, size_mb)
                    saved_paths.append(str(target))
                    saved = True
                    break
                else:
                    raise RuntimeError("SDK download produced empty file.")
            except Exception as exc:
                log.warning("SDK download attempt %d/%d failed for video %d: %s", attempt, DOWNLOAD_MAX_RETRIES, idx + 1, exc)
                if attempt < DOWNLOAD_MAX_RETRIES:
                    time.sleep(DOWNLOAD_RETRY_DELAY)

        if saved:
            continue

        # Method 2: Direct HTTP download from URI
        log.info("SDK download failed for video %d. Trying URI fallback...", idx + 1)
        for attempt in range(1, DOWNLOAD_MAX_RETRIES + 1):
            if _download_via_uri(video_file, target):
                size_mb = target.stat().st_size / (1024 * 1024)
                log.info("Saved via URI fallback: %s (%.1f MB)", target, size_mb)
                saved_paths.append(str(target))
                saved = True
                break
            log.warning("URI fallback attempt %d/%d failed for video %d.", attempt, DOWNLOAD_MAX_RETRIES, idx + 1)
            if attempt < DOWNLOAD_MAX_RETRIES:
                time.sleep(DOWNLOAD_RETRY_DELAY)

        if saved:
            continue

        # Method 3: Wait for ACTIVE state
        log.info("URI fallback failed for video %d. Waiting for ACTIVE state...", idx + 1)
        if _wait_for_active_and_download(video_file, target):
            size_mb = target.stat().st_size / (1024 * 1024)
            log.info("Saved via ACTIVE wait: %s (%.1f MB)", target, size_mb)
            saved_paths.append(str(target))
        else:
            log.error("All download methods failed for video %d", idx + 1)

    if not saved_paths:
        raise RuntimeError("All download methods failed for all videos.")

    return saved_paths


def _run_generation_job(job_id: str, generate_fn, output_file: Path):
    """
    Background worker that runs the full generation pipeline.
    Updates the job store with progress and final result.
    """
    job = jobs[job_id]
    try:
        # Step 0: Cleanup stuck files to prevent quota issues
        _cleanup_old_files()

        # Step 1: Call Google API (with automatic key rotation on 429)
        job["status"] = "generating"
        job["message"] = "Sending request to Google VEO API..."
        job["api_key_num"] = manager.current_index + 1
        log.info("[Job %s] Starting generation (key #%d)...", job_id[:8], manager.current_index + 1)

        operation = _call_with_rotation(generate_fn)
        job["api_key_num"] = manager.current_index + 1  # update if rotated
        sys.stderr.flush()

        # Step 2: Poll until done
        job["message"] = "Video is being generated by Google..."
        elapsed = 0
        while not operation.done:
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            operation = manager.client.operations.get(operation)
            job["message"] = f"Generating... ({elapsed}s elapsed)"
            log.info("[Job %s] Still generating... (%ds)", job_id[:8], elapsed)

        job["message"] = f"Generation complete after ~{elapsed}s. Downloading..."
        job["status"] = "downloading"
        log.info("[Job %s] Generation done, downloading...", job_id[:8])

        # Step 3: Download and save
        saved_paths = _save_video(operation, output_file)

        # Step 4: Store video URI(s) and object(s) for extension support
        try:
            for vidx, gen_video in enumerate(operation.response.generated_videos):
                uri = getattr(gen_video.video, 'uri', None)
                if vidx == 0:
                    job["video_uri"] = uri
                    video_objects[job_id] = gen_video.video
                    job["video_stored_at"] = datetime.now().isoformat()
        except Exception:
            job["video_uri"] = None

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

@mcp.tool(name="veo_generate_video")
def veo_generate_video(
    prompt: str,
    model_tier: str = "standard",
    resolution: str = "1080p",
    aspect_ratio: str = "16:9",
    duration_seconds: int = 8,
    negative_prompt: str = "",
    output_path: str = "",
    reference_image_paths: str = "",  # NEW: Reference images
    seed: int = -1,  # NEW: Seed control
    number_of_videos: int = 1,  # NEW: Batch generation
) -> str:
    """Generate a video from a text prompt using Google VEO 3.1.

    Returns a job_id immediately. Use veo_check_job(job_id) to poll status.
    Video generation typically takes 30-120 seconds.

    Args:
        prompt: Detailed description of the video to generate.
        model_tier: "standard" (higher quality) or "fast" (quicker generation).
        resolution: "720p", "1080p", or "4k". Note: 1080p and 4k only support 8-second videos.
        aspect_ratio: "16:9" (landscape) or "9:16" (portrait).
        duration_seconds: 4, 6, or 8. Must be 8 for 1080p/4k.
        negative_prompt: What to avoid in the video (e.g., "blur, low quality").
        output_path: Custom output file path. Auto-generated if empty.
        reference_image_paths: Comma-separated paths to 1-3 reference images for style guidance. NOTE: Requires Vertex AI.
        seed: Reproducibility seed (0-4294967295). Use -1 for random. Same seed = same output.
        number_of_videos: Number of videos to generate (1-4). Each gets a separate file.

    Returns:
        Job ID and instructions. Use veo_check_job to monitor progress.
    """
    model = _get_model(model_tier)

    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {VALID_RESOLUTIONS}")
    if aspect_ratio not in VALID_ASPECTS:
        raise ValueError(f"aspect_ratio must be one of {VALID_ASPECTS}")
    if resolution in ("1080p", "4k") and duration_seconds != 8:
        duration_seconds = 8
    if duration_seconds not in VALID_DURATIONS:
        raise ValueError(f"duration_seconds must be one of {VALID_DURATIONS}")

    # NEW: Seed and batch validation
    validated_seed = _validate_seed(seed)
    if number_of_videos < 1 or number_of_videos > 4:
        raise ValueError("number_of_videos must be 1-4")

    output_file = _resolve_output(output_path or None, "t2v")
    job_id = str(uuid.uuid4())

    # Register job
    jobs[job_id] = {
        "type": "text-to-video",
        "status": "starting",
        "message": "Initializing...",
        "prompt": prompt[:100],
        "model": model,
        "resolution": resolution,
        "output_file": str(output_file),
        "started_at": datetime.now().isoformat(),
        "seed": validated_seed,  # NEW
        "number_of_videos": number_of_videos,  # NEW
    }

    # Define the generation function
    def generate_fn():
        # NEW: Load reference images if provided
        ref_images = _load_reference_images(reference_image_paths)
        config = types.GenerateVideosConfig(
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt if negative_prompt else None,
            reference_images=ref_images if ref_images else None,  # NEW: Reference images
            duration_seconds=duration_seconds,  # NEW: Pass duration to config
            seed=_seed_for_config(validated_seed),  # NEW: Seed control (Vertex AI only)
            number_of_videos=number_of_videos,  # NEW: Batch generation
        )
        return manager.client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=config,
        )

    # Launch background thread
    thread = threading.Thread(
        target=_run_generation_job,
        args=(job_id, generate_fn, output_file),
        daemon=True,
    )
    thread.start()

    # NEW: Build return message with seed and batch info
    seed_info = f"  Seed: {validated_seed}\n" if validated_seed is not None else ""
    batch_info = f"  Videos: {number_of_videos}\n" if number_of_videos > 1 else ""
    return (
        f"Video generation started!\n"
        f"  Job ID: {job_id}\n"
        f"  Model: {model}\n"
        f"  Resolution: {resolution}\n"
        f"  Duration: {duration_seconds}s\n"
        f"{seed_info}{batch_info}\n"
        f"Use veo_check_job(job_id=\"{job_id}\") to check progress.\n"
        f"Generation typically takes 30-120 seconds."
    )


@mcp.tool(name="veo_check_job")
def veo_check_job(job_id: str) -> str:
    """Check the status of a VEO video generation job.

    Call this repeatedly (every 15-20 seconds) until status is 'completed' or 'failed'.

    Args:
        job_id: The job ID returned by veo_generate_video or other generation tools.

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
        if job.get("video_uri"):
            lines.append(f"  Video URI: {job['video_uri']}")
        # NEW: Show extension availability and expiry info
        if job.get("video_stored_at"):
            stored_time = datetime.fromisoformat(job["video_stored_at"])
            hours_elapsed = (datetime.now() - stored_time).total_seconds() / 3600
            remaining = max(0, 48 - hours_elapsed)
            if remaining > 0:
                lines.append(f"  Extension available: {remaining:.1f}h remaining")
            else:
                lines.append(f"  Extension EXPIRED ({hours_elapsed:.0f}h ago)")
        if job.get("video_uri") or job.get("video_stored_at"):
            lines.append("")
            lines.append("Video is ready! To extend this video, use:")
            lines.append(f'  veo_extend_video(source_job_id="{job_id}", prompt="...")')
        else:
            lines.append("")
            lines.append("Video is ready!")
    elif status == "failed":
        lines.extend([
            f"  Error: {job.get('error', 'Unknown error')}",
        ])

    return "\n".join(lines)


@mcp.tool(name="veo_list_jobs")
def veo_list_jobs() -> str:
    """List all video generation jobs and their current status.

    Returns:
        Summary of all jobs.
    """
    if not jobs:
        return "No jobs yet. Use veo_generate_video to start one."

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


@mcp.tool(name="veo_image_to_video")
def veo_image_to_video(
    prompt: str,
    image_path: str,
    model_tier: str = "standard",
    resolution: str = "1080p",
    aspect_ratio: str = "16:9",
    output_path: str = "",
    reference_image_paths: str = "",  # NEW: Reference images
    seed: int = -1,  # NEW: Seed control
) -> str:
    """Generate a video from an image + text prompt using VEO 3.1.

    Returns a job_id immediately. Use veo_check_job(job_id) to poll status.

    Args:
        prompt: Description of the motion/animation to apply to the image.
        image_path: Path to the source image file (.png, .jpg, .jpeg, .webp).
        model_tier: "standard" or "fast".
        resolution: "720p", "1080p", or "4k".
        aspect_ratio: "16:9" or "9:16".
        output_path: Custom output file path. Auto-generated if empty.
        reference_image_paths: Comma-separated paths to 1-3 reference images for style guidance. NOTE: Requires Vertex AI.
        seed: Reproducibility seed (0-4294967295). Use -1 for random. Same seed = same output.

    Returns:
        Job ID and instructions.
    """
    model = _get_model(model_tier)
    image = _load_image(image_path)
    output_file = _resolve_output(output_path or None, "i2v")

    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {VALID_RESOLUTIONS}")
    if aspect_ratio not in VALID_ASPECTS:
        raise ValueError(f"aspect_ratio must be one of {VALID_ASPECTS}")

    # NEW: Seed validation
    validated_seed = _validate_seed(seed)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "type": "image-to-video",
        "status": "starting",
        "message": "Initializing...",
        "prompt": prompt[:100],
        "model": model,
        "resolution": resolution,
        "output_file": str(output_file),
        "started_at": datetime.now().isoformat(),
        "seed": validated_seed,  # NEW
    }

    def generate_fn():
        # NEW: Load reference images if provided
        ref_images = _load_reference_images(reference_image_paths)
        return manager.client.models.generate_videos(
            model=model,
            prompt=prompt,
            image=image,
            config=types.GenerateVideosConfig(
                resolution=resolution,
                aspect_ratio=aspect_ratio,
                number_of_videos=1,
                reference_images=ref_images if ref_images else None,  # NEW: Reference images
                seed=_seed_for_config(validated_seed),  # NEW: Seed control (Vertex AI only)
            ),
        )

    thread = threading.Thread(target=_run_generation_job, args=(job_id, generate_fn, output_file), daemon=True)
    thread.start()

    # NEW: Build return message with seed info
    seed_info = f"  Seed: {validated_seed}\n" if validated_seed is not None else ""
    return (
        f"Image-to-Video generation started!\n"
        f"  Job ID: {job_id}\n"
        f"  Source: {image_path}\n"
        f"  Model: {model}\n"
        f"  Resolution: {resolution}\n"
        f"{seed_info}\n"
        f"Use veo_check_job(job_id=\"{job_id}\") to check progress."
    )


@mcp.tool(name="veo_extend_video")
def veo_extend_video(
    prompt: str,
    source_job_id: str = "",
    video_uri: str = "",
    output_path: str = "",
    seed: int = -1,  # NEW: Seed control
) -> str:
    """Extend an existing VEO-generated video by ~7 seconds (VEO 3.1 only).

    Returns a job_id immediately. Use veo_check_job(job_id) to poll status.

    IMPORTANT: The source video MUST be from a previous VEO generation — Google's
    API tracks provenance server-side. Provide either source_job_id or video_uri.

    Constraints:
    - 720p resolution ONLY
    - Input video must be 141 seconds or shorter
    - Each extension adds ~7 seconds
    - Maximum total length: 148 seconds (up to 20 extensions)
    - VEO files expire after 2 days on Google's servers

    Args:
        prompt: Description of what happens next in the video.
        source_job_id: Job ID from a previous veo_generate_video / veo_image_to_video call.
        video_uri: Direct VEO video URI (alternative to source_job_id).
        output_path: Custom output file path. Auto-generated if empty.
        seed: Reproducibility seed (0-4294967295). Use -1 for random. Same seed = same output.

    Returns:
        Job ID and instructions.
    """
    # NEW: Resolve video reference with multiple fallback strategies
    video_ref = None
    source_uri = ""
    source_info = ""

    if source_job_id:
        if source_job_id not in jobs:
            return f"Source job not found: {source_job_id}\nAvailable jobs: {list(jobs.keys())}"
        source_job = jobs[source_job_id]
        if source_job.get("status") != "completed":
            return f"Source job is not completed yet (status: {source_job.get('status')}). Wait for it to finish."

        # NEW: Check expiry (48 hours)
        stored_at = source_job.get("video_stored_at")
        if stored_at:
            stored_time = datetime.fromisoformat(stored_at)
            hours_elapsed = (datetime.now() - stored_time).total_seconds() / 3600
            if hours_elapsed > 48:
                return (
                    f"Source video has expired! It was stored {hours_elapsed:.0f} hours ago.\n"
                    f"VEO videos expire after 48 hours on Google's servers.\n"
                    f"Please generate a new video and extend it within 48 hours."
                )
            source_info = f" (stored {hours_elapsed:.1f}h ago, expires in {48 - hours_elapsed:.1f}h)"

        # NEW: Strategy 1 - Use stored Video object (most reliable)
        if source_job_id in video_objects:
            video_ref = video_objects[source_job_id]
            log.info("Using stored Video object for extension")
        else:
            # Strategy 2 - Reconstruct from URI
            source_uri = source_job.get("video_uri", "")
            if not source_uri:
                # Strategy 3 - Upload local file to get a URI reference
                # NOTE: Video.from_file() loads raw bytes which causes
                # "encoding isn't supported" error. Must upload first.
                local_path = source_job.get("result_path", "")
                if local_path and Path(local_path).exists():
                    log.info("Uploading local video to get URI reference: %s", local_path)
                    try:
                        uploaded = manager.client.files.upload(file=local_path)
                        source_uri = uploaded.uri
                        video_ref = types.Video(uri=source_uri)
                        log.info("Uploaded video, got URI: %s", source_uri[:80] if source_uri else "None")
                    except Exception as exc:
                        return (
                            f"Cannot extend: no video URI stored and upload failed: {exc}\n"
                            f"The video may have been generated before extension support was added.\n"
                            f"Try generating a new video first, then extend it."
                        )
                else:
                    return "Source job has no video_uri stored. The video may have been generated before this feature was added."
            else:
                video_ref = types.Video(uri=source_uri)
                log.info("Using reconstructed Video(uri=...) for extension")

    elif video_uri:
        source_uri = video_uri
        video_ref = types.Video(uri=video_uri)
        log.info("Using provided video_uri for extension")
    else:
        return (
            "Error: Must provide either source_job_id or video_uri.\n"
            "  - source_job_id: Job ID from a previous VEO generation\n"
            "  - video_uri: Direct URI of a VEO-generated video on Google's servers\n\n"
            "Note: Local video files cannot be used — Google's API requires the original VEO file reference."
        )

    output_file = _resolve_output(output_path or None, "ext")
    model = MODELS["standard"]
    new_job_id = str(uuid.uuid4())

    # NEW: Seed validation
    validated_seed = _validate_seed(seed)

    jobs[new_job_id] = {
        "type": "extend-video",
        "status": "starting",
        "message": "Initializing extension...",
        "prompt": prompt[:100],
        "model": model,
        "resolution": "720p",
        "source_uri": source_uri or getattr(video_ref, 'uri', 'stored-object'),
        "output_file": str(output_file),
        "started_at": datetime.now().isoformat(),
        "seed": validated_seed,  # NEW
    }

    # NEW: Capture video_ref in closure
    _video_ref = video_ref

    def generate_fn():
        return manager.client.models.generate_videos(
            model=model,
            prompt=prompt,
            video=_video_ref,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                resolution="720p",
                seed=_seed_for_config(validated_seed),  # NEW: Seed control (Vertex AI only)
            ),
        )

    thread = threading.Thread(target=_run_generation_job, args=(new_job_id, generate_fn, output_file), daemon=True)
    thread.start()

    return (
        f"Video extension started!{source_info}\n"
        f"  Job ID: {new_job_id}\n"
        f"  Source: {source_uri[:60] + '...' if len(source_uri) > 60 else source_uri or 'stored Video object'}\n"
        f"  Resolution: 720p\n\n"
        f"Use veo_check_job(job_id=\"{new_job_id}\") to check progress."
    )


@mcp.tool(name="veo_interpolate_video")
def veo_interpolate_video(
    prompt: str,
    first_frame_path: str,
    last_frame_path: str,
    model_tier: str = "standard",
    resolution: str = "1080p",
    output_path: str = "",
    seed: int = -1,  # NEW: Seed control
) -> str:
    """Generate a video that transitions from a first frame to a last frame (VEO 3.1 only).

    Returns a job_id immediately. Use veo_check_job(job_id) to poll status.

    Args:
        prompt: Description of the transition/motion between the two frames.
        first_frame_path: Path to the first frame image.
        last_frame_path: Path to the last frame image.
        model_tier: "standard" or "fast".
        resolution: "720p", "1080p", or "4k".
        output_path: Custom output file path. Auto-generated if empty.
        seed: Reproducibility seed (0-4294967295). Use -1 for random. Same seed = same output.

    Returns:
        Job ID and instructions.
    """
    model = _get_model(model_tier)
    first_frame = _load_image(first_frame_path)
    last_frame = _load_image(last_frame_path)
    output_file = _resolve_output(output_path or None, "interp")

    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {VALID_RESOLUTIONS}")

    # NEW: Seed validation
    validated_seed = _validate_seed(seed)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "type": "interpolate",
        "status": "starting",
        "message": "Initializing...",
        "prompt": prompt[:100],
        "model": model,
        "resolution": resolution,
        "output_file": str(output_file),
        "started_at": datetime.now().isoformat(),
        "seed": validated_seed,  # NEW
    }

    def generate_fn():
        return manager.client.models.generate_videos(
            model=model,
            prompt=prompt,
            image=first_frame,
            config=types.GenerateVideosConfig(
                last_frame=last_frame,
                resolution=resolution,
                number_of_videos=1,
                seed=_seed_for_config(validated_seed),  # NEW: Seed control (Vertex AI only)
            ),
        )

    thread = threading.Thread(target=_run_generation_job, args=(job_id, generate_fn, output_file), daemon=True)
    thread.start()

    # NEW: Build return message with seed info
    seed_info = f"  Seed: {validated_seed}\n" if validated_seed is not None else ""
    return (
        f"Frame interpolation started!\n"
        f"  Job ID: {job_id}\n"
        f"  First: {first_frame_path}\n"
        f"  Last: {last_frame_path}\n"
        f"  Model: {model}\n"
        f"{seed_info}\n"
        f"Use veo_check_job(job_id=\"{job_id}\") to check progress."
    )


@mcp.tool(name="veo_show_output_stats")
def veo_show_output_stats() -> str:
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
    videos = list(OUTPUT_PATH.glob("*.mp4"))
    if not videos:
        lines.append(f"No videos found in {OUTPUT_PATH}")
        return "\n".join(lines) if lines else f"No videos found in {OUTPUT_PATH}"

    total_size = sum(v.stat().st_size for v in videos)
    total_mb = total_size / (1024 * 1024)

    lines.append(f"=== Video Output Stats - {OUTPUT_PATH} ===")
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


@mcp.tool(name="veo_pricing_info")
def veo_pricing_info() -> str:
    """Show VEO 3.1 pricing information per second of generated video.

    Returns:
        Pricing table for both standard and fast models at all resolutions.
    """
    return "\n".join([
        "VEO 3.1 Pricing (per second of generated video)",
        "=" * 55,
        "",
        "Standard Model (veo-3.1-generate-preview):",
        "  720p:  $0.035/sec  |  8s video = $0.28",
        "  1080p: $0.060/sec  |  8s video = $0.48",
        "  4K:    $0.100/sec  |  8s video = $0.80",
        "",
        "Fast Model (veo-3.1-fast-generate-preview):",
        "  720p:  $0.025/sec  |  8s video = $0.20",
        "  1080p: $0.045/sec  |  8s video = $0.36",
        "  4K:    $0.075/sec  |  8s video = $0.60",
        "",
        "=" * 55,
        "Notes:",
        "  - 1080p and 4K only support 8-second videos",
        "  - 720p supports 4, 6, or 8 seconds",
        "  - Video extension: 720p only, adds ~7s per extension",
        "  - Max 20 extensions, up to 148 seconds total",
        "  - Videos deleted from Google servers after 2 days",
        "  - Frame rate: 24fps",
        "  - Latency: 11 seconds to 6 minutes",
    ])


@mcp.tool(name="veo_api_status")
def veo_api_status() -> str:
    """Show current API key rotation status.

    Displays how many keys are configured, which key is currently active,
    and how many remain before all keys are exhausted.

    Returns:
        API key status summary.
    """
    lines = [
        "=== VEO API Key Status ===",
        f"  Keys configured: {len(manager.clients)}",
        f"  Currently using: Key #{manager.current_index + 1}",
        f"  Keys remaining: {len(manager.clients) - manager.current_index}",
        "",
        "Rotation behavior:",
        "  - On 429 (quota exhausted), automatically switches to next key",
        "  - VEO quota resets at midnight Pacific time (08:00 UTC)",
    ]
    return "\n".join(lines)


# ── Entry Point ──────────────────────────────────────────────────────────────
def main():
    """Entry point for the MCP server."""
    log.info("Starting VEO 3.1 MCP Server (async job pattern)...")
    mcp.run()


if __name__ == "__main__":
    main()
