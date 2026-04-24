"""
Local mode caching service for persistent result storage.

This service provides the L2 (disk) cache layer that persists data across
server restarts. It uses file metadata for fast change detection to support
the smart refresh functionality.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LocalCacheService:
    """Manages persistent cache for local mode.

    Features:
    - Persistent JSON storage for statistics and messages
    - Fast change detection using file metadata (size + mtime)
    - Automatic cache invalidation when source files change
    - Metadata tracking for cache validity

    Cache Structure:
    ~/.sniffly/cache/
    └── [md5_hash]/              # Hash of log directory path
        ├── metadata.json        # File checksums and cache timestamp
        ├── stats.json          # Cached statistics
        └── messages.json       # Cached messages
    """

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            # Default to ~/.sniffly/cache/
            self.cache_dir = Path.home() / ".sniffly" / "cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, log_path: str) -> str:
        """Generate a cache key from the log path"""
        # Use hash of the path to avoid filesystem issues
        return hashlib.md5(log_path.encode()).hexdigest()

    def _get_cache_path(self, log_path: str, filename: str) -> Path:
        """Get the cache file path for a given log path and filename"""
        cache_key = self._get_cache_key(log_path)
        cache_subdir = self.cache_dir / cache_key
        cache_subdir.mkdir(exist_ok=True)
        return cache_subdir / filename

    def _get_metadata_path(self, log_path: str) -> Path:
        """Get the metadata file path for a log path"""
        return self._get_cache_path(log_path, "metadata.json")

    def _update_metadata(self, log_path: str):
        """Update cache metadata with current file info"""
        metadata = {
            "log_path": log_path,
            "cached_at": datetime.now().isoformat(),
            "file_checksums": self._calculate_checksums(log_path),
        }

        with open(self._get_metadata_path(log_path), "w") as f:
            json.dump(metadata, f, indent=2)

    def _calculate_checksums(self, log_path: str) -> dict[str, str]:
        """Calculate checksums for all JSONL files in the log directory.

        Uses file metadata (size + modification time) as a fast "checksum"
        to detect changes without reading file contents. This enables
        sub-millisecond change detection for the refresh functionality.

        Args:
            log_path: Directory containing JSONL files

        Returns:
            Dict mapping filename to "size_mtime" string
        """
        checksums = {}
        log_dir = Path(log_path)

        if log_dir.exists() and log_dir.is_dir():
            for jsonl_file in log_dir.glob("*.jsonl"):
                # Use file size and modification time as a simple "checksum"
                # This is faster than reading entire files
                stat = jsonl_file.stat()
                # Round mtime to avoid precision issues across different systems
                checksums[jsonl_file.name] = f"{stat.st_size}_{int(stat.st_mtime)}"

        return checksums

    def has_changes(self, log_path: str) -> bool:
        """Check if the log files have changed since last cache.

        This is the core method for smart refresh functionality. It compares
        current file metadata with cached metadata to detect changes without
        reading file contents.

        Args:
            log_path: Directory to check for changes

        Returns:
            True if any files were added, removed, or modified since last cache

        Performance:
            - Typically completes in <5ms for projects with 10-50 files
            - O(n) where n is number of JSONL files
        """
        metadata_path = self._get_metadata_path(log_path)

        if not metadata_path.exists():
            return True  # No cache exists

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)

            # Compare current checksums with cached ones
            current_checksums = self._calculate_checksums(log_path)
            cached_checksums = metadata.get("file_checksums", {})

            # Check if any files were added, removed, or modified
            return current_checksums != cached_checksums

        except Exception as e:
            logger.debug(f"Error checking changes: {e}")
            return True  # Assume changes on any error

    def get_cached_stats(self, log_path: str) -> dict[str, Any] | None:
        """Get cached statistics if available and valid"""
        if self.has_changes(log_path):
            return None

        stats_path = self._get_cache_path(log_path, "stats.json")
        if stats_path.exists():
            try:
                with open(stats_path) as f:
                    return json.load(f)
            except Exception:
                return None

        return None

    def get_cached_stats_fast(self, log_path: str) -> dict[str, Any] | None:
        """Get cached statistics WITHOUT checking for changes.

        Use this for fast loading when you don't need to verify freshness.
        This is much faster than get_cached_stats() for overview pages.

        Args:
            log_path: Log directory path

        Returns:
            Cached stats or None if not cached
        """
        stats_path = self._get_cache_path(log_path, "stats.json")
        if stats_path.exists():
            try:
                with open(stats_path) as f:
                    return json.load(f)
            except Exception:
                return None

        return None

    def get_cached_messages(self, log_path: str) -> list[dict[str, Any]] | None:
        """Get cached messages if available and valid"""
        if self.has_changes(log_path):
            return None

        messages_path = self._get_cache_path(log_path, "messages.json")
        if messages_path.exists():
            try:
                with open(messages_path) as f:
                    return json.load(f)
            except Exception:
                return None

        return None

    def save_cached_stats(self, log_path: str, stats: dict[str, Any]):
        """Save statistics to cache"""
        stats_path = self._get_cache_path(log_path, "stats.json")
        logger.debug(f"Saving stats to: {stats_path}")
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)

        # Update metadata after saving
        self._update_metadata(log_path)

    def save_cached_messages(self, log_path: str, messages: list[dict[str, Any]]):
        """Save messages to cache"""
        messages_path = self._get_cache_path(log_path, "messages.json")
        logger.debug(f"Saving messages to: {messages_path}")
        with open(messages_path, "w") as f:
            json.dump(messages, f, indent=2)

        # Update metadata after saving
        self._update_metadata(log_path)

    def invalidate_cache(self, log_path: str):
        """Invalidate cache for a specific log path.

        Called by the refresh endpoint when changes are detected.
        Removes all cached files for the project, forcing reprocessing.

        Args:
            log_path: Directory whose cache should be invalidated
        """
        cache_key = self._get_cache_key(log_path)
        cache_subdir = self.cache_dir / cache_key

        if cache_subdir.exists():
            import shutil

            shutil.rmtree(cache_subdir)

    def get_cache_info(self, log_path: str) -> dict[str, Any] | None:
        """Get information about cached data"""
        metadata_path = self._get_metadata_path(log_path)

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)

            stats_path = self._get_cache_path(log_path, "stats.json")
            messages_path = self._get_cache_path(log_path, "messages.json")

            return {
                "cached_at": metadata.get("cached_at"),
                "has_stats": stats_path.exists(),
                "has_messages": messages_path.exists(),
                "is_valid": not self.has_changes(log_path),
            }

        except Exception:
            return None

    def clear_all_cache(self):
        """Clear all cached data"""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
