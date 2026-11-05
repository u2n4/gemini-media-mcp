"""
Image storage and serving service for handling large generated images.
Provides file-based storage with TTL cleanup and thumbnail generation.
"""

import os
import uuid
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import base64
import logging
import tempfile
from PIL import Image as PILImage
import io

from ..config.settings import GeminiConfig


@dataclass
class StoredImageInfo:
    """Information about a stored image."""

    id: str
    filename: str
    full_path: str
    thumbnail_path: str
    size_bytes: int
    thumbnail_size_bytes: int
    mime_type: str
    created_at: float
    expires_at: float
    width: int
    height: int
    thumbnail_width: int
    thumbnail_height: int
    metadata: Dict[str, Any]


class ImageStorageService:
    """Service for storing, serving, and managing generated images."""

    def __init__(self, config: GeminiConfig, base_dir: Optional[str] = None):
        self.config = config
        self.base_dir = Path(base_dir or "temp_images")
        self.thumbnails_dir = self.base_dir / "thumbnails"
        self.metadata_file = self.base_dir / "image_registry.json"
        self.logger = logging.getLogger(__name__)

        # Default settings
        self.default_ttl_seconds = 3600  # 1 hour
        self.thumbnail_max_size = (256, 256)
        self.thumbnail_quality = 85
        self.max_thumbnail_bytes = 50 * 1024  # 50KB

        # Load existing metadata (deferred: dirs created on first use via _ensure_dirs)
        self.image_registry: Dict[str, StoredImageInfo] = self._load_registry()

        # Cleanup on init
        self._cleanup_expired()

    def _ensure_dirs(self) -> None:
        """Lazily create storage directories on first use."""
        self.base_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _setup_directories(self) -> None:
        """Create necessary directories (alias kept for compatibility)."""
        self._ensure_dirs()

    def _load_registry(self) -> Dict[str, StoredImageInfo]:
        """Load image registry from disk."""
        if not self.metadata_file.exists():
            return {}

        try:
            with open(self.metadata_file, "r") as f:
                data = json.load(f)

            registry = {}
            for image_id, info_dict in data.items():
                registry[image_id] = StoredImageInfo(**info_dict)

            self.logger.debug(f"Loaded {len(registry)} images from registry")
            return registry

        except Exception:
            self.logger.exception("Failed to load image registry; preserving original file")
            raise

    def _save_registry(self) -> None:
        """Save image registry to disk."""
        temp_path = None
        try:
            self._ensure_dirs()
            data = {}
            for image_id, info in self.image_registry.items():
                data[image_id] = asdict(info)

            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.base_dir,
                                             delete=False) as f:
                temp_path = f.name
                json.dump(data, f, indent=2)
            os.replace(temp_path, self.metadata_file)

        except Exception:
            self.logger.exception("Failed to save image registry")
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _validated_paths(self, info: StoredImageInfo) -> tuple[Path, Path]:
        """Never trust paths loaded from a mutable registry for read or delete."""
        root = self.base_dir.resolve()
        full = Path(info.full_path).resolve()
        thumb = Path(info.thumbnail_path).resolve()
        if not full.is_relative_to(root) or not thumb.is_relative_to(self.thumbnails_dir.resolve()):
            raise ValueError("Image registry path escapes storage directory")
        return full, thumb

    def _cleanup_expired(self) -> None:
        """Remove expired images and their metadata."""
        current_time = time.time()
        expired_ids = []

        for image_id, info in self.image_registry.items():
            if current_time > info.expires_at:
                # Remove files
                try:
                    for path in self._validated_paths(info):
                        path.unlink(missing_ok=True)
                    expired_ids.append(image_id)
                except Exception as e:
                    self.logger.error(f"Failed to remove expired image {image_id}: {e}")

        # Remove from registry
        for image_id in expired_ids:
            del self.image_registry[image_id]

        if expired_ids:
            self.logger.info(f"Cleaned up {len(expired_ids)} expired images")
            self._save_registry()

    def _generate_thumbnail(self, image_bytes: bytes, mime_type: str) -> Tuple[bytes, int, int]:
        """Generate thumbnail from image bytes."""
        try:
            # Open image
            image = PILImage.open(io.BytesIO(image_bytes))

            # Convert to RGB if needed (for JPEG compatibility)
            if image.mode in ("RGBA", "LA", "P"):
                rgba = image.convert("RGBA")
                image = PILImage.new("RGB", rgba.size, "white")
                image.paste(rgba, mask=rgba.getchannel("A"))

            # Calculate thumbnail size preserving aspect ratio
            image.thumbnail(self.thumbnail_max_size, PILImage.Resampling.LANCZOS)

            # Save thumbnail
            output = io.BytesIO()
            format_name = "JPEG"  # Always use JPEG for thumbnails (smaller)
            image.save(output, format=format_name, quality=self.thumbnail_quality, optimize=True)
            thumbnail_bytes = output.getvalue()

            # If still too large, reduce quality
            quality = self.thumbnail_quality
            while len(thumbnail_bytes) > self.max_thumbnail_bytes and quality > 20:
                quality -= 10
                output = io.BytesIO()
                image.save(output, format=format_name, quality=quality, optimize=True)
                thumbnail_bytes = output.getvalue()

            return thumbnail_bytes, image.width, image.height

        except Exception as e:
            self.logger.error(f"Failed to generate thumbnail: {e}")
            raise

    def store_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> StoredImageInfo:
        """
        Store image and generate thumbnail.

        Args:
            image_bytes: Raw image data
            mime_type: MIME type (e.g., 'image/png')
            metadata: Additional metadata to store
            ttl_seconds: Time to live, defaults to 1 hour

        Returns:
            StoredImageInfo with paths and metadata
        """
        self._ensure_dirs()

        # Generate unique ID
        image_id = str(uuid.uuid4())

        # Determine file extension
        ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        ext = ext_map.get(mime_type, ".png")

        # Create file paths
        filename = f"{image_id}{ext}"
        full_path = str(self.base_dir / filename)
        thumbnail_filename = f"{image_id}_thumb.jpg"
        thumbnail_path = str(self.thumbnails_dir / thumbnail_filename)

        try:
            # Get image dimensions
            image = PILImage.open(io.BytesIO(image_bytes))
            width, height = image.size

            # Store full image
            with open(full_path, "wb") as f:
                f.write(image_bytes)

            # Generate and store thumbnail
            thumbnail_bytes, thumb_w, thumb_h = self._generate_thumbnail(image_bytes, mime_type)
            with open(thumbnail_path, "wb") as f:
                f.write(thumbnail_bytes)

            # Calculate expiration
            ttl = ttl_seconds or self.default_ttl_seconds
            created_at = time.time()
            expires_at = created_at + ttl

            # Create info object
            info = StoredImageInfo(
                id=image_id,
                filename=filename,
                full_path=full_path,
                thumbnail_path=thumbnail_path,
                size_bytes=len(image_bytes),
                thumbnail_size_bytes=len(thumbnail_bytes),
                mime_type=mime_type,
                created_at=created_at,
                expires_at=expires_at,
                width=width,
                height=height,
                thumbnail_width=thumb_w,
                thumbnail_height=thumb_h,
                metadata=metadata or {},
            )

            # Store in registry
            self.image_registry[image_id] = info
            self._save_registry()

            self.logger.info(
                f"Stored image {image_id}: {len(image_bytes)} bytes, expires at {datetime.fromtimestamp(expires_at)}"
            )
            return info

        except Exception as e:
            # Cleanup on failure
            for path in [full_path, thumbnail_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            raise e

    def get_image_info(self, image_id: str) -> Optional[StoredImageInfo]:
        """Get information about a stored image."""
        self._cleanup_expired()
        return self.image_registry.get(image_id)

    def get_image_bytes(self, image_id: str, thumbnail: bool = False) -> Optional[bytes]:
        """Retrieve image bytes by ID."""
        info = self.get_image_info(image_id)
        if not info:
            return None

        try:
            full_path, thumb_path = self._validated_paths(info)
            path = thumb_path if thumbnail else full_path
            with open(path, "rb") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read image {image_id}: {e}")
            return None

    def get_thumbnail_base64(self, image_id: str) -> Optional[str]:
        """Get thumbnail as base64 string for inline embedding."""
        thumbnail_bytes = self.get_image_bytes(image_id, thumbnail=True)
        if thumbnail_bytes:
            return base64.b64encode(thumbnail_bytes).decode()
        return None

    def list_images(self, include_expired: bool = False) -> List[StoredImageInfo]:
        """List all stored images."""
        if not include_expired:
            self._cleanup_expired()

        return list(self.image_registry.values())

    def delete_image(self, image_id: str) -> bool:
        """Delete an image and its thumbnail."""
        info = self.image_registry.get(image_id)
        if not info:
            return False

        try:
            # Remove files
            for path in self._validated_paths(info):
                path.unlink(missing_ok=True)

            # Remove from registry
            del self.image_registry[image_id]
            self._save_registry()

            self.logger.info(f"Deleted image {image_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete image {image_id}: {e}")
            return False

    def cleanup_all(self) -> int:
        """Clean up all images (useful for shutdown)."""
        count = 0
        for image_id in list(self.image_registry.keys()):
            if self.delete_image(image_id):
                count += 1
        return count

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        self._cleanup_expired()

        total_size = sum(info.size_bytes for info in self.image_registry.values())
        total_thumbnail_size = sum(
            info.thumbnail_size_bytes for info in self.image_registry.values()
        )

        return {
            "total_images": len(self.image_registry),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_thumbnail_size_bytes": total_thumbnail_size,
            "total_thumbnail_size_kb": round(total_thumbnail_size / 1024, 2),
            "base_directory": str(self.base_dir),
            "default_ttl_seconds": self.default_ttl_seconds,
        }
