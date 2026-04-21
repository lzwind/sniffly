"""
Utility to find OpenCode data from SQLite database
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OPENCODE_DB_PATH = Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def find_opencode_db() -> Optional[str]:
    """
    Find OpenCode database path.

    Returns:
        Path to OpenCode database if found, None otherwise
    """
    if OPENCODE_DB_PATH.exists():
        return str(OPENCODE_DB_PATH)

    # Try alternative locations
    alt_paths = [
        Path.home() / ".config" / "opencode" / "opencode.db",
        Path.home() / ".opencode" / "opencode.db",
    ]

    for path in alt_paths:
        if path.exists():
            return str(path)

    return None


def list_opencode_projects(db_path: Optional[str] = None) -> list[dict]:
    """
    List all OpenCode projects with metadata.

    Args:
        db_path: Optional database path, will auto-detect if not provided

    Returns:
        List of dictionaries containing project information
    """
    if db_path is None:
        db_path = find_opencode_db()

    if db_path is None:
        return []

    projects = []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query sessions grouped by directory (project)
        query = """
        SELECT
            s.directory as project_path,
            COUNT(DISTINCT s.id) as session_count,
            COUNT(DISTINCT m.id) as message_count,
            MIN(s.time_created) as first_session,
            MAX(s.time_updated) as last_session
        FROM session s
        LEFT JOIN message m ON s.id = m.session_id
        GROUP BY s.directory
        ORDER BY last_session DESC
        """
        cursor.execute(query)

        for row in cursor.fetchall():
            project_path = row["project_path"] or "unknown"
            project_name = Path(project_path).name if project_path != "unknown" else "global"

            # Convert timestamps from milliseconds to datetime
            first_session = None
            last_session = None
            if row["first_session"]:
                first_session = datetime.fromtimestamp(row["first_session"] / 1000).isoformat()
            if row["last_session"]:
                last_session = datetime.fromtimestamp(row["last_session"] / 1000).isoformat()

            projects.append({
                "name": project_name,
                "path": project_path,
                "session_count": row["session_count"],
                "message_count": row["message_count"],
                "first_session": first_session,
                "last_session": last_session,
            })

        conn.close()

    except sqlite3.Error as e:
        logger.error(f"Error reading OpenCode database: {e}")

    return projects


def get_opencode_db_info(db_path: Optional[str] = None) -> dict:
    """
    Get general information about the OpenCode database.

    Returns:
        Dictionary with database information
    """
    if db_path is None:
        db_path = find_opencode_db()

    if db_path is None:
        return {"exists": False}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get table counts
        tables = ["session", "message", "part", "project"]
        counts = {}

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = 0

        # Get database file size
        db_file = Path(db_path)
        size_mb = db_file.stat().st_size / (1024 * 1024) if db_file.exists() else 0

        conn.close()

        return {
            "exists": True,
            "path": db_path,
            "size_mb": round(size_mb, 2),
            "counts": counts,
        }

    except sqlite3.Error as e:
        logger.error(f"Error getting OpenCode database info: {e}")
        return {"exists": False, "error": str(e)}


def validate_opencode_db(db_path: Optional[str] = None) -> tuple[bool, str]:
    """
    Validate OpenCode database.

    Returns:
        (is_valid, message)
    """
    if db_path is None:
        db_path = find_opencode_db()

    if db_path is None:
        return False, "OpenCode database not found"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        required = {"session", "message"}
        missing = required - tables

        if missing:
            return False, f"Missing required tables: {missing}"

        # Check if there's any data
        cursor.execute("SELECT COUNT(*) FROM session")
        session_count = cursor.fetchone()[0]

        conn.close()

        if session_count == 0:
            return False, "No sessions found in database"

        return True, f"Valid OpenCode database with {session_count} sessions"

    except sqlite3.Error as e:
        return False, f"Database error: {e}"
