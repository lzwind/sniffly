"""
OpenCode data processor for extracting usage statistics from SQLite database
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class OpenCodeLogProcessor:
    """Process OpenCode logs from SQLite database"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize OpenCode log processor.

        Args:
            db_path: Path to OpenCode database. If None, will auto-detect.
        """
        from sniffly.utils.opencode_finder import find_opencode_db

        self.db_path = db_path or find_opencode_db()
        self._conn = None

    def _get_connection(self):
        """Get database connection"""
        if self._conn is None and self.db_path:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_sessions(self, project_path: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> list[dict]:
        """
        Get sessions with optional filters.

        Args:
            project_path: Filter by project path
            start_date: Filter sessions starting from this date (YYYY-MM-DD)
            end_date: Filter sessions until this date (YYYY-MM-DD)

        Returns:
            List of session dictionaries
        """
        conn = self._get_connection()
        if not conn:
            return []

        cursor = conn.cursor()

        query = """
        SELECT
            s.id,
            s.project_id,
            s.directory,
            s.title,
            s.time_created,
            s.time_updated
        FROM session s
        WHERE 1=1
        """
        params = []

        if project_path:
            query += " AND s.directory = ?"
            params.append(project_path)

        if start_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp() * 1000)
            query += " AND s.time_created >= ?"
            params.append(start_ts)

        if end_date:
            # Include the full end date
            end_ts = int(datetime.fromisoformat(end_date + "T23:59:59").timestamp() * 1000)
            query += " AND s.time_created <= ?"
            params.append(end_ts)

        query += " ORDER BY s.time_created DESC"

        cursor.execute(query, params)

        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "id": row["id"],
                "project_id": row["project_id"],
                "project_path": row["directory"],
                "title": row["title"],
                "time_created": datetime.fromtimestamp(row["time_created"] / 1000).isoformat() if row["time_created"] else None,
                "time_updated": datetime.fromtimestamp(row["time_updated"] / 1000).isoformat() if row["time_updated"] else None,
            })

        return sessions

    def get_messages(self, session_id: Optional[str] = None,
                     project_path: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> list[dict]:
        """
        Get messages with optional filters.

        Returns:
            List of message dictionaries
        """
        conn = self._get_connection()
        if not conn:
            return []

        cursor = conn.cursor()

        query = """
        SELECT
            m.id,
            m.session_id,
            m.time_created,
            m.data,
            s.directory as project_path
        FROM message m
        JOIN session s ON m.session_id = s.id
        WHERE 1=1
        """
        params = []

        if session_id:
            query += " AND m.session_id = ?"
            params.append(session_id)

        if project_path:
            query += " AND s.directory = ?"
            params.append(project_path)

        if start_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp() * 1000)
            query += " AND m.time_created >= ?"
            params.append(start_ts)

        if end_date:
            end_ts = int(datetime.fromisoformat(end_date + "T23:59:59").timestamp() * 1000)
            query += " AND m.time_created <= ?"
            params.append(end_ts)

        query += " ORDER BY m.time_created ASC"

        cursor.execute(query, params)

        messages = []
        for row in cursor.fetchall():
            data = json.loads(row["data"]) if row["data"] else {}

            messages.append({
                "id": row["id"],
                "session_id": row["session_id"],
                "project_path": row["project_path"],
                "time_created": datetime.fromtimestamp(row["time_created"] / 1000).isoformat() if row["time_created"] else None,
                "role": data.get("role"),
                "model": data.get("modelID"),
                "provider": data.get("providerID"),
                "tokens": data.get("tokens", {}),
                "cost": data.get("cost", 0),
                "error": data.get("error"),
            })

        return messages

    def get_message_parts(self, message_id: str) -> list[dict]:
        """Get parts for a specific message"""
        conn = self._get_connection()
        if not conn:
            return []

        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, data FROM part WHERE message_id = ? ORDER BY time_created",
            (message_id,)
        )

        parts = []
        for row in cursor.fetchall():
            data = json.loads(row["data"]) if row["data"] else {}
            parts.append({
                "id": row["id"],
                "type": data.get("type"),
                "text": data.get("text", ""),
                "tokens": data.get("tokens", {}),
                "reason": data.get("reason"),
            })

        return parts

    def get_user_prompts(self, project_path: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> list[dict]:
        """
        Get all user prompts with full content.

        Returns:
            List of prompt dictionaries
        """
        conn = self._get_connection()
        if not conn:
            return []

        cursor = conn.cursor()

        query = """
        SELECT
            m.id as message_id,
            m.session_id,
            m.time_created,
            m.data as message_data,
            s.directory as project_path,
            s.title as session_title
        FROM message m
        JOIN session s ON m.session_id = s.id
        WHERE json_extract(m.data, '$.role') = 'user'
        """
        params = []

        if project_path:
            query += " AND s.directory = ?"
            params.append(project_path)

        if start_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp() * 1000)
            query += " AND m.time_created >= ?"
            params.append(start_ts)

        if end_date:
            end_ts = int(datetime.fromisoformat(end_date + "T23:59:59").timestamp() * 1000)
            query += " AND m.time_created <= ?"
            params.append(end_ts)

        query += " ORDER BY m.time_created ASC"

        cursor.execute(query, params)

        prompts = []
        for row in cursor.fetchall():
            message_data = json.loads(row["message_data"]) if row["message_data"] else {}

            # Get parts to extract text content
            parts = self.get_message_parts(row["message_id"])
            text_parts = [p["text"] for p in parts if p["type"] == "text" and p["text"]]

            # Extract model from message or use default
            model = message_data.get("model", {}).get("modelID", "unknown")

            prompts.append({
                "message_id": row["message_id"],
                "session_id": row["session_id"],
                "project_path": row["project_path"],
                "session_title": row["session_title"],
                "timestamp": datetime.fromtimestamp(row["time_created"] / 1000).isoformat() if row["time_created"] else None,
                "prompt": "\n".join(text_parts) if text_parts else "",
                "model": model,
                "tokens": message_data.get("tokens", {}),
            })

        return prompts

    def calculate_statistics(self, project_path: Optional[str] = None,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> dict:
        """
        Calculate usage statistics.

        Returns:
            Dictionary with statistics
        """
        conn = self._get_connection()
        if not conn:
            return {}

        cursor = conn.cursor()

        # Build filter conditions for messages
        msg_conditions = ["1=1"]
        msg_params = []

        if project_path:
            msg_conditions.append("s.directory = ?")
            msg_params.append(project_path)

        if start_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp() * 1000)
            msg_conditions.append("m.time_created >= ?")
            msg_params.append(start_ts)

        if end_date:
            end_ts = int(datetime.fromisoformat(end_date + "T23:59:59").timestamp() * 1000)
            msg_conditions.append("m.time_created <= ?")
            msg_params.append(end_ts)

        msg_where = " AND ".join(msg_conditions)

        # Build filter conditions for sessions
        sess_conditions = ["1=1"]
        sess_params = []

        if project_path:
            sess_conditions.append("directory = ?")
            sess_params.append(project_path)

        if start_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp() * 1000)
            sess_conditions.append("time_created >= ?")
            sess_params.append(start_ts)

        if end_date:
            end_ts = int(datetime.fromisoformat(end_date + "T23:59:59").timestamp() * 1000)
            sess_conditions.append("time_created <= ?")
            sess_params.append(end_ts)

        sess_where = " AND ".join(sess_conditions)

        # Get session statistics
        session_query = f"""
        SELECT
            COUNT(DISTINCT id) as total_sessions,
            MIN(time_created) as first_session,
            MAX(time_updated) as last_session
        FROM session
        WHERE {sess_where}
        """
        cursor.execute(session_query, sess_params)
        session_row = cursor.fetchone()

        total_sessions = session_row["total_sessions"] if session_row else 0
        first_session = datetime.fromtimestamp(session_row["first_session"] / 1000).isoformat() if session_row and session_row["first_session"] else None
        last_session = datetime.fromtimestamp(session_row["last_session"] / 1000).isoformat() if session_row and session_row["last_session"] else None

        # Get message statistics
        message_query = f"""
        SELECT
            COUNT(*) as total_messages,
            SUM(CASE WHEN json_extract(m.data, '$.role') = 'user' THEN 1 ELSE 0 END) as user_messages,
            SUM(CASE WHEN json_extract(m.data, '$.role') = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
            SUM(CASE WHEN json_extract(m.data, '$.error') IS NOT NULL THEN 1 ELSE 0 END) as error_messages
        FROM message m
        JOIN session s ON m.session_id = s.id
        WHERE {msg_where}
        """
        cursor.execute(message_query, msg_params)
        message_row = cursor.fetchone()

        total_messages = message_row["total_messages"] if message_row else 0
        user_messages = message_row["user_messages"] if message_row else 0
        assistant_messages = message_row["assistant_messages"] if message_row else 0
        error_messages = message_row["error_messages"] if message_row else 0

        # Get token statistics from part table (step-finish contains token counts)
        token_query = f"""
        SELECT
            SUM(json_extract(p.data, '$.tokens.input')) as total_input,
            SUM(json_extract(p.data, '$.tokens.output')) as total_output,
            SUM(json_extract(p.data, '$.tokens.cache.read')) as total_cache_read,
            SUM(json_extract(p.data, '$.tokens.cache.write')) as total_cache_write
        FROM part p
        JOIN message m ON p.message_id = m.id
        JOIN session s ON m.session_id = s.id
        WHERE json_extract(p.data, '$.type') = 'step-finish'
        AND {msg_where}
        """
        cursor.execute(token_query, msg_params)
        token_row = cursor.fetchone()

        total_input = token_row["total_input"] if token_row and token_row["total_input"] else 0
        total_output = token_row["total_output"] if token_row and token_row["total_output"] else 0
        total_cache_read = token_row["total_cache_read"] if token_row and token_row["total_cache_read"] else 0
        total_cache_write = token_row["total_cache_write"] if token_row and token_row["total_cache_write"] else 0

        # Get model distribution
        model_query = f"""
        SELECT
            json_extract(m.data, '$.modelID') as model,
            COUNT(*) as count
        FROM message m
        JOIN session s ON m.session_id = s.id
        WHERE json_extract(m.data, '$.modelID') IS NOT NULL
        AND {msg_where}
        GROUP BY json_extract(m.data, '$.modelID')
        ORDER BY count DESC
        """
        cursor.execute(model_query, msg_params)
        model_distribution = {row["model"]: row["count"] for row in cursor.fetchall()}

        # Get daily statistics
        daily_query = f"""
        SELECT
            date(m.time_created / 1000, 'unixepoch') as date,
            COUNT(DISTINCT m.session_id) as sessions,
            COUNT(*) as messages,
            SUM(CASE WHEN json_extract(m.data, '$.role') = 'user' THEN 1 ELSE 0 END) as prompts
        FROM message m
        JOIN session s ON m.session_id = s.id
        WHERE {msg_where}
        GROUP BY date
        ORDER BY date
        """
        cursor.execute(daily_query, msg_params)
        daily_stats = []
        for row in cursor.fetchall():
            daily_stats.append({
                "date": row["date"],
                "sessions": row["sessions"],
                "messages": row["messages"],
                "prompts": row["prompts"],
            })

        # Get daily tokens
        daily_token_query = f"""
        SELECT
            date(m.time_created / 1000, 'unixepoch') as date,
            SUM(json_extract(p.data, '$.tokens.input')) as input_tokens,
            SUM(json_extract(p.data, '$.tokens.output')) as output_tokens
        FROM part p
        JOIN message m ON p.message_id = m.id
        JOIN session s ON m.session_id = s.id
        WHERE json_extract(p.data, '$.type') = 'step-finish'
        AND {msg_where}
        GROUP BY date
        ORDER BY date
        """
        cursor.execute(daily_token_query, msg_params)

        # Merge tokens into daily stats
        daily_tokens = {}
        for row in cursor.fetchall():
            daily_tokens[row["date"]] = {
                "input": row["input_tokens"] or 0,
                "output": row["output_tokens"] or 0,
            }

        for stat in daily_stats:
            if stat["date"] in daily_tokens:
                stat["tokens"] = daily_tokens[stat["date"]]
            else:
                stat["tokens"] = {"input": 0, "output": 0}

        return {
            "source": "opencode",
            "summary": {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "total_prompts": user_messages,
                "total_tokens": {
                    "input": total_input,
                    "output": total_output,
                    "cache_creation": total_cache_write,
                    "cache_read": total_cache_read,
                    "total": total_input + total_output,
                },
                "model_distribution": model_distribution,
                "date_range": {
                    "start": first_session,
                    "end": last_session,
                },
            },
            "daily_stats": daily_stats,
            "error_rate": error_messages / total_messages if total_messages > 0 else 0,
        }

    def get_project_statistics(self) -> list[dict]:
        """Get statistics per project"""
        conn = self._get_connection()
        if not conn:
            return []

        cursor = conn.cursor()

        query = """
        SELECT
            s.directory as project_path,
            COUNT(DISTINCT s.id) as total_sessions,
            COUNT(DISTINCT m.id) as total_messages,
            MIN(s.time_created) as first_used,
            MAX(s.time_updated) as last_used
        FROM session s
        LEFT JOIN message m ON s.id = m.session_id
        GROUP BY s.directory
        ORDER BY last_used DESC
        """

        cursor.execute(query)

        projects = []
        for row in cursor.fetchall():
            project_path = row["project_path"] or "unknown"
            projects.append({
                "name": Path(project_path).name if project_path != "unknown" else "global",
                "path": project_path,
                "total_sessions": row["total_sessions"],
                "total_messages": row["total_messages"],
                "first_used": datetime.fromtimestamp(row["first_used"] / 1000).isoformat() if row["first_used"] else None,
                "last_used": datetime.fromtimestamp(row["last_used"] / 1000).isoformat() if row["last_used"] else None,
            })

        return projects
