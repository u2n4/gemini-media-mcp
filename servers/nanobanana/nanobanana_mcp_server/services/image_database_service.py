"""
Image Database Service for tracking generated images with Files API integration.

Implements the DB/Index layer shown in workflows.md for tracking:
- Local file paths and thumbnails
- Files API metadata (file_id, file_uri, expires_at)
- Parent/child relationships for edits
- Generation and editing metadata

AC4(b): DB path is configurable via NANOBANANA_DB_PATH env var.
  Default: ~/nanobanana-images/images.db
  Opt-out:  NANOBANANA_DB_PATH=:memory:  (no filesystem writes)
"""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, NamedTuple
import logging


DEFAULT_DB_PATH: Path = Path.home() / "nanobanana-images" / "images.db"


def _resolve_db_path(explicit_path: Optional[str] = None) -> str:
    """Resolve the SQLite DB path with NANOBANANA_DB_PATH override.

    Resolution order:
      1. explicit_path argument (e.g. passed by tests or services/__init__.py)
      2. NANOBANANA_DB_PATH env var (honors ":memory:" for in-memory mode)
      3. ~/nanobanana-images/images.db  (DEFAULT_DB_PATH)
    """
    if explicit_path:
        return explicit_path
    env_override = os.environ.get("NANOBANANA_DB_PATH", "").strip()
    if env_override:
        return env_override
    return str(DEFAULT_DB_PATH)


class ImageRecord(NamedTuple):
    """Represents a stored image record from the database."""

    id: int
    path: str
    thumb_path: str
    mime_type: str
    width: int
    height: int
    size_bytes: int
    file_id: Optional[str]
    file_uri: Optional[str]
    expires_at: Optional[datetime]
    parent_file_id: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ImageDatabaseService:
    """Database service for tracking image metadata and Files API integration.

    Initialization is deferred: no filesystem access or DB connection is made
    until the first actual operation.  This ensures that importing the package
    or constructing the service object at startup does not create directories
    or files.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize database service.

        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory
                     mode.  When None the value of NANOBANANA_DB_PATH env var
                     is used, falling back to ~/nanobanana-images/images.db.
        """
        self.db_path: str = _resolve_db_path(db_path)
        self._is_memory: bool = self.db_path == ":memory:"
        self._memory_conn: Optional[sqlite3.Connection] = None
        self._memory_lock = threading.Lock()
        self._initialized: bool = False
        self._init_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Lazy initialisation
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        """Initialize the database schema on first use (double-checked locking)."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            if self._is_memory:
                self._memory_conn = sqlite3.connect(
                    ":memory:", check_same_thread=False, isolation_level=None
                )
            else:
                parent = os.path.dirname(self.db_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
            self._init_db()
            self._initialized = True

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a live SQLite connection, initializing on first call."""
        self._ensure_initialized()
        if self._is_memory:
            with self._memory_lock:
                yield self._memory_conn  # type: ignore[misc]
        else:
            with sqlite3.connect(self.db_path) as conn:
                yield conn

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Initialize database schema.

        Called once by _ensure_initialized(); must NOT call _conn() (would
        recurse before _initialized is True).
        """
        if self._is_memory:
            conn = self._memory_conn
            assert conn is not None
            conn.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    thumb_path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    file_id TEXT,
                    file_uri TEXT,
                    expires_at TIMESTAMP,
                    parent_file_id TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_id ON images(file_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_parent_file_id ON images(parent_file_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON images(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON images(path)")
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT NOT NULL,
                        thumb_path TEXT NOT NULL,
                        mime_type TEXT NOT NULL,
                        width INTEGER NOT NULL,
                        height INTEGER NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        file_id TEXT,
                        file_uri TEXT,
                        expires_at TIMESTAMP,
                        parent_file_id TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_file_id ON images(file_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_parent_file_id ON images(parent_file_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON images(expires_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON images(path)")
                conn.commit()
        self.logger.info("Database initialized at %s", self.db_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert_image(
        self,
        path: str,
        thumb_path: str,
        mime_type: str,
        width: int,
        height: int,
        size_bytes: int,
        file_id: Optional[str] = None,
        file_uri: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        parent_file_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Insert or update image record.

        Args:
            path: Local file path to full-resolution image
            thumb_path: Local file path to thumbnail
            mime_type: MIME type of the image
            width: Image width in pixels
            height: Image height in pixels
            size_bytes: File size in bytes
            file_id: Gemini Files API file ID (e.g., 'files/abc123')
            file_uri: Gemini Files API file URI
            expires_at: When the Files API entry expires (~48h from upload)
            parent_file_id: For edits, the file_id of the original image
            metadata: Additional metadata as JSON

        Returns:
            Database ID of the inserted/updated record
        """
        metadata_json = json.dumps(metadata or {})
        now = datetime.now()

        # Default expires_at to 48 hours from now if file_id is provided
        if file_id and expires_at is None:
            expires_at = now + timedelta(hours=48)

        with self._conn() as conn:
            # Check if record already exists by path
            existing = conn.execute("SELECT id FROM images WHERE path = ?", (path,)).fetchone()

            if existing:
                # Update existing record
                conn.execute(
                    """
                    UPDATE images
                    SET thumb_path = ?, mime_type = ?, width = ?, height = ?,
                        size_bytes = ?, file_id = ?, file_uri = ?, expires_at = ?,
                        parent_file_id = ?, metadata = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (
                        thumb_path,
                        mime_type,
                        width,
                        height,
                        size_bytes,
                        file_id,
                        file_uri,
                        expires_at,
                        parent_file_id,
                        metadata_json,
                        now,
                        existing[0],
                    ),
                )
                record_id = existing[0]
                self.logger.debug("Updated image record %s for %s", record_id, path)
            else:
                # Insert new record
                cursor = conn.execute(
                    """
                    INSERT INTO images
                    (path, thumb_path, mime_type, width, height, size_bytes,
                     file_id, file_uri, expires_at, parent_file_id, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        path,
                        thumb_path,
                        mime_type,
                        width,
                        height,
                        size_bytes,
                        file_id,
                        file_uri,
                        expires_at,
                        parent_file_id,
                        metadata_json,
                        now,
                        now,
                    ),
                )
                record_id = cursor.lastrowid
                self.logger.info("Inserted new image record %s for %s", record_id, path)

            if not self._is_memory:
                conn.commit()
            return record_id

    def get_by_file_id(self, file_id: str) -> Optional[ImageRecord]:
        """Get image record by Files API file_id."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM images WHERE file_id = ?", (file_id,)).fetchone()
            if row:
                return self._row_to_record(row)
            return None

    def get_by_path(self, path: str) -> Optional[ImageRecord]:
        """Get image record by local file path."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM images WHERE path = ?", (path,)).fetchone()
            if row:
                return self._row_to_record(row)
            return None

    def get_by_id(self, record_id: int) -> Optional[ImageRecord]:
        """Get image record by database ID."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM images WHERE id = ?", (record_id,)).fetchone()
            if row:
                return self._row_to_record(row)
            return None

    def list_expired_files(self, buffer_minutes: int = 30) -> List[ImageRecord]:
        """
        List Files API entries that are expired or will expire soon.

        Args:
            buffer_minutes: Consider files expiring within this many minutes

        Returns:
            List of image records with expired or soon-to-expire Files API entries
        """
        cutoff_time = datetime.now() + timedelta(minutes=buffer_minutes)

        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM images
                WHERE file_id IS NOT NULL
                  AND expires_at IS NOT NULL
                  AND expires_at <= ?
                ORDER BY expires_at ASC
            """,
                (cutoff_time,),
            ).fetchall()

            return [self._row_to_record(row) for row in rows]

    def update_files_api_info(
        self, record_id: int, file_id: str, file_uri: str, expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Update Files API information for an existing record.

        Args:
            record_id: Database record ID
            file_id: New Files API file ID
            file_uri: New Files API file URI
            expires_at: New expiration time (defaults to 48h from now)

        Returns:
            True if update was successful
        """
        if expires_at is None:
            expires_at = datetime.now() + timedelta(hours=48)

        with self._conn() as conn:
            result = conn.execute(
                """
                UPDATE images
                SET file_id = ?, file_uri = ?, expires_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (file_id, file_uri, expires_at, datetime.now(), record_id),
            )

            if not self._is_memory:
                conn.commit()
            success = result.rowcount > 0

            if success:
                self.logger.debug("Updated Files API info for record %s", record_id)
            else:
                self.logger.warning("No record found with ID %s", record_id)

            return success

    def clear_files_api_info(self, record_id: int) -> bool:
        """
        Clear Files API information when file expires or is deleted.

        Args:
            record_id: Database record ID

        Returns:
            True if update was successful
        """
        with self._conn() as conn:
            result = conn.execute(
                """
                UPDATE images
                SET file_id = NULL, file_uri = NULL, expires_at = NULL, updated_at = ?
                WHERE id = ?
            """,
                (datetime.now(), record_id),
            )

            if not self._is_memory:
                conn.commit()
            success = result.rowcount > 0

            if success:
                self.logger.debug("Cleared Files API info for record %s", record_id)

            return success

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get database usage statistics."""
        with self._conn() as conn:
            # Total records and sizes
            stats_row = conn.execute("""
                SELECT
                    COUNT(*) as total_images,
                    SUM(size_bytes) as total_size_bytes,
                    COUNT(CASE WHEN file_id IS NOT NULL THEN 1 END) as uploaded_to_files_api,
                    COUNT(CASE WHEN parent_file_id IS NOT NULL THEN 1 END) as edited_images
                FROM images
            """).fetchone()

            # Files API expiration status
            now = datetime.now()
            expiration_row = conn.execute(
                """
                SELECT
                    COUNT(CASE WHEN expires_at IS NOT NULL AND expires_at <= ? THEN 1 END) as expired,
                    COUNT(CASE WHEN expires_at IS NOT NULL AND expires_at > ? THEN 1 END) as active
                FROM images
            """,
                (now, now),
            ).fetchone()

            return {
                "total_images": stats_row[0],
                "total_size_bytes": stats_row[1] or 0,
                "total_size_mb": round((stats_row[1] or 0) / (1024 * 1024), 2),
                "uploaded_to_files_api": stats_row[2],
                "edited_images": stats_row[3],
                "files_api_expired": expiration_row[0],
                "files_api_active": expiration_row[1],
            }

    def cleanup_missing_files(self) -> int:
        """
        Remove database records for files that no longer exist on disk.

        Returns:
            Number of records removed
        """
        removed_count = 0

        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            all_records = conn.execute("SELECT * FROM images").fetchall()

            for row in all_records:
                record = self._row_to_record(row)

                # Check if both main file and thumbnail exist
                main_exists = os.path.exists(record.path)
                thumb_exists = os.path.exists(record.thumb_path)

                if not main_exists or not thumb_exists:
                    conn.execute("DELETE FROM images WHERE id = ?", (record.id,))
                    removed_count += 1
                    self.logger.info(
                        "Removed record %s: main=%s, thumb=%s",
                        record.id,
                        main_exists,
                        thumb_exists,
                    )

            if not self._is_memory:
                conn.commit()

        if removed_count > 0:
            self.logger.info("Cleaned up %s missing file records", removed_count)

        return removed_count

    def _row_to_record(self, row: sqlite3.Row) -> ImageRecord:
        """Convert database row to ImageRecord."""
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        # Parse timestamps
        created_at = datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
        updated_at = datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
        expires_at = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None

        return ImageRecord(
            id=row["id"],
            path=row["path"],
            thumb_path=row["thumb_path"],
            mime_type=row["mime_type"],
            width=row["width"],
            height=row["height"],
            size_bytes=row["size_bytes"],
            file_id=row["file_id"],
            file_uri=row["file_uri"],
            expires_at=expires_at,
            parent_file_id=row["parent_file_id"],
            metadata=metadata,
            created_at=created_at,
            updated_at=updated_at,
        )
