"""
Export service for Claude Code and OpenCode usage data
"""

import csv
import io
import logging
import subprocess
from datetime import datetime
from typing import Optional

from sniffly.core.constants import USER_INTERRUPTION_PATTERNS
from sniffly.utils.pricing import calculate_cost

logger = logging.getLogger(__name__)


def get_git_user_info() -> dict:
    """Get user info from git config"""
    try:
        name = subprocess.check_output(
            ["git", "config", "--global", "user.name"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except subprocess.CalledProcessError:
        name = "Unknown"

    try:
        email = subprocess.check_output(
            ["git", "config", "--global", "user.email"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except subprocess.CalledProcessError:
        email = "unknown@example.com"

    return {"name": name, "email": email}


class ClaudeExportService:
    """Export service for Claude Code data"""

    def export(self,
               project_path: Optional[str] = None,
               start_date: Optional[str] = None,
               end_date: Optional[str] = None) -> dict:
        """
        Export Claude Code usage data.

        Args:
            project_path: Filter by project path
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)

        Returns:
            Exported data dictionary
        """
        from sniffly.core.processor import ClaudeLogProcessor
        from sniffly.utils.log_finder import get_all_projects_with_metadata

        # Get all projects
        all_projects = get_all_projects_with_metadata()

        # Filter projects
        if project_path:
            projects = [p for p in all_projects if project_path in p.get("log_path", "")]
            if not projects:
                # Try to find by name
                projects = [p for p in all_projects if project_path.lower() in p.get("display_name", "").lower()]
        else:
            projects = all_projects

        # Initialize result
        result = {
            "source": "claude",
            "developer": get_git_user_info(),
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "date_range": {
                    "start": start_date,
                    "end": end_date,
                },
                "filters_applied": [f"project:{project_path}"] if project_path else [],
            },
            "summary": {
                "total_requests": 0,
                "total_sessions": 0,
                "total_tokens": {
                    "input": 0,
                    "output": 0,
                    "cache_creation": 0,
                    "cache_read": 0,
                    "total": 0,
                },
                "total_cost": 0,
                "total_prompts": 0,
            },
            "daily_stats": [],
            "prompts": [],
            "projects": [],
            "sessions": [],
        }

        # Aggregate daily stats while processing projects (avoid double processing)
        daily_combined = {}

        for project in projects:
            log_path = project.get("log_path")
            if not log_path:
                continue

            try:
                # Process logs - returns (messages, statistics)
                processor = ClaudeLogProcessor(log_path)
                messages, _ = processor.process_logs()
                if not messages:
                    continue

                # Filter by date if needed
                if start_date or end_date:
                    messages = self._filter_messages_by_date(messages, start_date, end_date)

                # Extract project data for prompts and sessions only
                project_data = self._extract_project_data(project, messages)

                result["projects"].append(project_data["project_info"])
                result["prompts"].extend(project_data["prompts"])
                result["sessions"].extend(project_data["sessions"])

                # Aggregate daily stats from filtered messages (single pass)
                for msg in messages:
                    ts = msg.get("timestamp")
                    if not ts:
                        continue

                    date = ts[:10] if isinstance(ts, str) else ts[:10]

                    if date not in daily_combined:
                        daily_combined[date] = {
                            "date": date,
                            "requests": 0,
                            "sessions": set(),
                            "prompts": 0,
                            "tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0},
                            "models_used": {},
                        }

                    daily_combined[date]["requests"] += 1

                    sid = msg.get("session_id")
                    if sid:
                        daily_combined[date]["sessions"].add(sid)

                    # Count prompts (exclude tool result messages)
                    if msg.get("type") == "user" and not msg.get("has_tool_result", False):
                        daily_combined[date]["prompts"] += 1

                    # Token usage
                    tokens = msg.get("tokens", {})
                    if tokens:
                        daily_combined[date]["tokens"]["input"] += tokens.get("input", 0) or 0
                        daily_combined[date]["tokens"]["output"] += tokens.get("output", 0) or 0
                        daily_combined[date]["tokens"]["cache_creation"] += tokens.get("cache_creation", 0) or 0
                        daily_combined[date]["tokens"]["cache_read"] += tokens.get("cache_read", 0) or 0

                    # Model tracking for daily cost calculation
                    model = msg.get("model") or "unknown"
                    if msg.get("type") == "assistant" and model != "unknown" and model != "N/A":
                        if model not in daily_combined[date]["models_used"]:
                            daily_combined[date]["models_used"][model] = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0, "count": 0}
                        daily_combined[date]["models_used"][model]["input"] += tokens.get("input", 0) or 0
                        daily_combined[date]["models_used"][model]["output"] += tokens.get("output", 0) or 0
                        daily_combined[date]["models_used"][model]["cache_creation"] += tokens.get("cache_creation", 0) or 0
                        daily_combined[date]["models_used"][model]["cache_read"] += tokens.get("cache_read", 0) or 0
                        daily_combined[date]["models_used"][model]["count"] += 1

            except Exception as e:
                logger.error(f"Error processing project {project.get('display_name')}: {e}")
                continue

        # Calculate summary from daily_combined (single source of truth)
        all_sessions = set()
        for date, data in daily_combined.items():
            result["summary"]["total_requests"] += data["requests"]
            result["summary"]["total_prompts"] += data["prompts"]
            result["summary"]["total_tokens"]["input"] += data["tokens"]["input"]
            result["summary"]["total_tokens"]["output"] += data["tokens"]["output"]
            result["summary"]["total_tokens"]["cache_creation"] += data["tokens"]["cache_creation"]
            result["summary"]["total_tokens"]["cache_read"] += data["tokens"]["cache_read"]
            all_sessions.update(data["sessions"])

            # Calculate cost from model tokens for this day
            daily_cost = 0.0
            for model, model_data in data["models_used"].items():
                if model != "unknown" and model != "N/A":
                    cost_breakdown = calculate_cost({
                        "input": model_data.get("input", 0),
                        "output": model_data.get("output", 0),
                        "cache_creation": model_data.get("cache_creation", 0),
                        "cache_read": model_data.get("cache_read", 0),
                    }, model)
                    daily_cost += cost_breakdown.get("total_cost", 0)

            result["daily_stats"].append({
                "date": date,
                "requests": data["requests"],
                "sessions": len(data["sessions"]),
                "prompts": data["prompts"],
                "tokens": data["tokens"],
                "cost": daily_cost,
                "models_used": {k: v.get("count", 0) for k, v in data["models_used"].items()},
            })

        result["summary"]["total_sessions"] = len(all_sessions)

        # Calculate totals
        result["summary"]["total_tokens"]["total"] = (
            result["summary"]["total_tokens"]["input"] +
            result["summary"]["total_tokens"]["output"]
        )

        # Calculate total cost from daily stats
        result["summary"]["total_cost"] = sum(d.get("cost", 0) for d in result["daily_stats"])

        # Sort daily stats by date
        result["daily_stats"].sort(key=lambda x: x["date"])

        return result

    def _filter_messages_by_date(self, messages: list, start_date: Optional[str], end_date: Optional[str]) -> list:
        """Filter messages by date range"""
        filtered = []
        for msg in messages:
            ts = msg.get("timestamp")
            if not ts:
                continue

            msg_date = ts[:10] if isinstance(ts, str) else datetime.fromisoformat(ts).strftime("%Y-%m-%d")

            if start_date and msg_date < start_date:
                continue
            if end_date and msg_date > end_date:
                continue

            filtered.append(msg)

        return filtered

    def _is_interruption_message(self, content: str) -> bool:
        """Check if a message content indicates a user interruption."""
        if not content:
            return False
        return any(content.startswith(pattern) for pattern in USER_INTERRUPTION_PATTERNS)

    def _extract_project_data(self, project: dict, messages: list) -> dict:
        """Extract data for a single project. Returns prompts, sessions, and project info."""

        # Get date range from filtered messages
        timestamps = []
        for msg in messages:
            ts = msg.get("timestamp")
            if ts:
                timestamps.append(ts[:10] if isinstance(ts, str) else ts)

        if timestamps:
            first_used = min(timestamps)
            last_used = max(timestamps)
        else:
            first_used = None
            last_used = None

        # Extract prompts from filtered messages directly
        # Sort messages by timestamp for proper sequence
        sorted_messages = sorted(messages, key=lambda x: x.get("timestamp", "") or "")
        prompts = []

        for i, msg in enumerate(sorted_messages):
            # Only real user messages (not tool results)
            if msg.get("type") != "user" or msg.get("has_tool_result", False):
                continue

            # Get prompt content
            prompt_content = msg.get("content", "")

            # Get model and tools from interaction data or find from assistant responses
            model = msg.get("interaction_model", "N/A")
            tool_count = msg.get("interaction_tool_count", 0)
            tool_names = []

            # Find assistant responses to get tool names
            j = i + 1
            tools_found = []
            while j < len(sorted_messages):
                next_msg = sorted_messages[j]
                if next_msg.get("type") == "user" and not next_msg.get("has_tool_result", False):
                    break
                if next_msg.get("type") == "assistant":
                    if model == "N/A" and next_msg.get("model") and next_msg["model"] != "N/A":
                        model = next_msg["model"]
                    if next_msg.get("tools"):
                        tools_found.extend(next_msg.get("tools", []))
                j += 1

            # Extract tool names
            if tools_found:
                # Use interaction_tool_count to limit if available
                if tool_count and tool_count > 0:
                    tool_names = [t.get("name", "Unknown") for t in tools_found[:tool_count]]
                else:
                    tool_names = list(set(t.get("name", "Unknown") for t in tools_found))

            # Check if this is an interruption message
            is_interruption = self._is_interruption_message(prompt_content)

            prompts.append({
                "timestamp": msg.get("timestamp", ""),
                "session_id": msg.get("session_id", ""),
                "project": project.get("display_name"),
                "prompt": prompt_content,
                "model": model if model != "N/A" else None,
                "tools_used": tool_names,
                "tokens_used": {
                    "input": len(prompt_content) // 4,  # Rough estimate
                    "output": 0,
                },
                "has_error": False,
                "is_interruption": is_interruption,
            })

        # Get sessions
        sessions = []
        session_data = {}  # Group by session_id

        for msg in messages:
            sid = msg.get("session_id")
            if not sid:
                continue

            if sid not in session_data:
                session_data[sid] = {
                    "id": sid,
                    "project": project.get("display_name"),
                    "messages": [],
                    "timestamps": [],
                }

            session_data[sid]["messages"].append(msg)
            if msg.get("timestamp"):
                session_data[sid]["timestamps"].append(msg["timestamp"])

        for sid, data in session_data.items():
            timestamps = sorted(data["timestamps"])
            sessions.append({
                "id": sid,
                "project": data["project"],
                "started_at": timestamps[0] if timestamps else None,
                "ended_at": timestamps[-1] if timestamps else None,
                "total_prompts": len([m for m in data["messages"] if m.get("type") == "user" and not m.get("has_tool_result", False)]),
            })

        return {
            "project_info": {
                "name": project.get("display_name"),
                "path": project.get("log_path"),
                "first_used": first_used,
                "last_used": last_used,
            },
            "prompts": prompts,
            "sessions": sessions,
        }


class OpenCodeExportService:
    """Export service for OpenCode data"""

    def __init__(self):
        from sniffly.core.opencode_processor import OpenCodeLogProcessor
        self.processor = OpenCodeLogProcessor()

    def export(self,
               project_path: Optional[str] = None,
               start_date: Optional[str] = None,
               end_date: Optional[str] = None,
               output_format: str = "json") -> dict:
        """
        Export OpenCode usage data.

        Args:
            project_path: Filter by project path
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            output_format: "json" or "csv"

        Returns:
            Exported data dictionary
        """
        # Get statistics
        stats = self.processor.calculate_statistics(project_path, start_date, end_date)

        # Get prompts
        prompts = self.processor.get_user_prompts(project_path, start_date, end_date)

        # Get sessions
        sessions = self.processor.get_sessions(project_path, start_date, end_date)

        # Get projects
        projects = self.processor.get_project_statistics()

        # Format result
        result = {
            "source": "opencode",
            "developer": get_git_user_info(),
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "date_range": {
                    "start": start_date,
                    "end": end_date,
                },
                "filters_applied": [f"project:{project_path}"] if project_path else [],
            },
            "summary": {
                "total_requests": stats.get("summary", {}).get("total_messages", 0),
                "total_sessions": stats.get("summary", {}).get("total_sessions", 0),
                "total_tokens": stats.get("summary", {}).get("total_tokens", {}),
                "total_cost": 0,  # Not tracked in OpenCode
                "total_prompts": stats.get("summary", {}).get("total_prompts", 0),
            },
            "daily_stats": stats.get("daily_stats", []),
            "prompts": self._format_prompts(prompts),
            "projects": projects,
            "sessions": self._format_sessions(sessions),
        }

        return result

    def _format_prompts(self, prompts: list) -> list:
        """Format prompts for export"""
        return [
            {
                "timestamp": p.get("timestamp"),
                "session_id": p.get("session_id"),
                "project": p.get("project_path"),
                "prompt": p.get("prompt", ""),
                "model": p.get("model"),
                "tools_used": [],  # OpenCode doesn't track tools the same way
                "tokens_used": {
                    "input": p.get("tokens", {}).get("input", 0),
                    "output": p.get("tokens", {}).get("output", 0),
                },
                "has_error": False,
                "is_interruption": False,
            }
            for p in prompts
        ]

    def _format_sessions(self, sessions: list) -> list:
        """Format sessions for export"""
        return [
            {
                "id": s.get("id"),
                "project": s.get("project_path"),
                "title": s.get("title"),
                "started_at": s.get("time_created"),
                "ended_at": s.get("time_updated"),
                "total_prompts": 0,  # Would need to count from messages
            }
            for s in sessions
        ]

    def __del__(self):
        """Clean up resources"""
        if hasattr(self, 'processor'):
            self.processor.close()


def format_as_csv(data: dict) -> str:
    """Convert export data to CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write prompts as CSV
    writer.writerow([
        "timestamp", "session_id", "project", "prompt", "model",
        "tools_used", "input_tokens", "output_tokens", "has_error", "is_interruption"
    ])

    for prompt in data.get("prompts", []):
        writer.writerow([
            prompt.get("timestamp", ""),
            prompt.get("session_id", ""),
            prompt.get("project", ""),
            prompt.get("prompt", "")[:500],  # Truncate long prompts
            prompt.get("model", ""),
            ",".join(prompt.get("tools_used", [])),
            prompt.get("tokens_used", {}).get("input", 0),
            prompt.get("tokens_used", {}).get("output", 0),
            prompt.get("has_error", False),
            prompt.get("is_interruption", False),
        ])

    return output.getvalue()
