"""
Export service for Claude Code and OpenCode usage data
"""

import csv
import io
import json
import logging
import subprocess
from datetime import datetime
from typing import Optional

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

        for project in projects:
            log_path = project.get("log_path")
            if not log_path:
                continue

            try:
                # Process logs - returns (messages, statistics)
                processor = ClaudeLogProcessor(log_path)
                messages, stats = processor.process_logs()
                if not messages:
                    continue

                # Filter by date if needed
                if start_date or end_date:
                    messages = self._filter_messages_by_date(messages, start_date, end_date)
                    # Note: For proper date filtering, we'd need to reprocess
                    # For now, just filter the messages

                # Extract project data
                project_data = self._extract_project_data(project, messages, stats, start_date, end_date)

                # Merge into result
                result["summary"]["total_requests"] += project_data["summary"]["total_requests"]
                result["summary"]["total_sessions"] += project_data["summary"]["total_sessions"]
                result["summary"]["total_tokens"]["input"] += project_data["summary"]["total_tokens"]["input"]
                result["summary"]["total_tokens"]["output"] += project_data["summary"]["total_tokens"]["output"]
                result["summary"]["total_tokens"]["cache_creation"] += project_data["summary"]["total_tokens"].get("cache_creation", 0)
                result["summary"]["total_tokens"]["cache_read"] += project_data["summary"]["total_tokens"].get("cache_read", 0)
                result["summary"]["total_cost"] += project_data["summary"].get("total_cost", 0)
                result["summary"]["total_prompts"] += project_data["summary"]["total_prompts"]

                result["projects"].append(project_data["project_info"])
                result["prompts"].extend(project_data["prompts"])
                result["sessions"].extend(project_data["sessions"])

            except Exception as e:
                logger.error(f"Error processing project {project.get('display_name')}: {e}")
                continue

        # Calculate totals
        result["summary"]["total_tokens"]["total"] = (
            result["summary"]["total_tokens"]["input"] +
            result["summary"]["total_tokens"]["output"]
        )

        # Aggregate daily stats from stats data with date filter
        result["daily_stats"] = self._aggregate_daily_stats_from_stats(projects, start_date, end_date)

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

    def _extract_project_data(self, project: dict, messages: list, stats: dict,
                              start_date: Optional[str], end_date: Optional[str]) -> dict:
        """Extract data for a single project"""
        overview = stats.get("overview", {})
        sessions_stats = stats.get("sessions", {})
        user_interactions = stats.get("user_interactions", {})
        daily_stats = stats.get("daily_stats", {})

        # Get prompts from command details
        prompts = []
        for cmd in user_interactions.get("command_details", []):
            ts = cmd.get("timestamp", "")
            date = ts[:10] if ts else None

            if start_date and date and date < start_date:
                continue
            if end_date and date and date > end_date:
                continue

            prompts.append({
                "timestamp": ts,
                "session_id": cmd.get("session_id"),
                "project": project.get("display_name"),
                "prompt": cmd.get("user_message", ""),
                "model": cmd.get("model"),
                "tools_used": cmd.get("tool_names", []),
                "tokens_used": {
                    "input": cmd.get("estimated_tokens", 0),
                    "output": 0,  # Not available per prompt in current structure
                },
                "has_error": False,
                "is_interruption": cmd.get("is_interruption", False),
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
                "total_prompts": len([m for m in data["messages"] if m.get("type") == "user"]),
            })

        return {
            "summary": {
                "total_requests": overview.get("total_messages", 0),
                "total_sessions": sessions_stats.get("count", 0),
                "total_tokens": {
                    "input": overview.get("total_tokens", {}).get("input", 0),
                    "output": overview.get("total_tokens", {}).get("output", 0),
                    "cache_creation": overview.get("total_tokens", {}).get("cache_creation", 0),
                    "cache_read": overview.get("total_tokens", {}).get("cache_read", 0),
                },
                "total_cost": overview.get("total_cost", 0),
                "total_prompts": user_interactions.get("real_user_messages", 0),
            },
            "project_info": {
                "name": project.get("display_name"),
                "path": project.get("log_path"),
                "total_requests": overview.get("total_messages", 0),
                "total_sessions": sessions_stats.get("count", 0),
                "total_tokens": overview.get("total_tokens", {}),
                "first_used": overview.get("date_range", {}).get("start"),
                "last_used": overview.get("date_range", {}).get("end"),
            },
            "prompts": prompts,
            "sessions": sessions,
        }

    def _aggregate_daily_stats(self, prompts: list) -> list:
        """Aggregate prompts into daily statistics"""
        daily = {}

        for prompt in prompts:
            ts = prompt.get("timestamp")
            if not ts:
                continue

            date = ts[:10] if isinstance(ts, str) else ts.strftime("%Y-%m-%d")

            if date not in daily:
                daily[date] = {
                    "date": date,
                    "requests": 0,
                    "sessions": set(),
                    "prompts": 0,
                    "tokens": {"input": 0, "output": 0},
                    "models_used": {},
                }

            daily[date]["requests"] += 1
            daily[date]["prompts"] += 1
            if prompt.get("session_id"):
                daily[date]["sessions"].add(prompt["session_id"])

            model = prompt.get("model", "unknown")
            daily[date]["models_used"][model] = daily[date]["models_used"].get(model, 0) + 1

            tokens = prompt.get("tokens_used", {})
            daily[date]["tokens"]["input"] += tokens.get("input", 0)
            daily[date]["tokens"]["output"] += tokens.get("output", 0)

        result = []
        for date in sorted(daily.keys()):
            data = daily[date]
            result.append({
                "date": date,
                "requests": data["requests"],
                "sessions": len(data["sessions"]),
                "prompts": data["prompts"],
                "tokens": data["tokens"],
                "models_used": data["models_used"],
            })

        return result

    def _aggregate_daily_stats_from_stats(self, projects: list,
                                          start_date: Optional[str] = None,
                                          end_date: Optional[str] = None) -> list:
        """Aggregate daily stats from processed stats data"""
        from sniffly.core.processor import ClaudeLogProcessor

        daily_combined = {}

        for project in projects:
            log_path = project.get("log_path")
            if not log_path:
                continue

            try:
                processor = ClaudeLogProcessor(log_path)
                messages, stats = processor.process_logs()
                daily_stats = stats.get("daily_stats", {})

                for date, data in daily_stats.items():
                    # Apply date filter
                    if start_date and date < start_date:
                        continue
                    if end_date and date > end_date:
                        continue

                    if date not in daily_combined:
                        daily_combined[date] = {
                            "date": date,
                            "requests": 0,
                            "sessions": 0,
                            "prompts": 0,
                            "tokens": {"input": 0, "output": 0},
                            "models_used": {},
                        }

                    daily_combined[date]["requests"] += data.get("messages", 0)
                    daily_combined[date]["sessions"] += data.get("sessions", 0)
                    daily_combined[date]["prompts"] += data.get("user_commands", 0)

                    tokens = data.get("tokens", {})
                    daily_combined[date]["tokens"]["input"] += tokens.get("input", 0)
                    daily_combined[date]["tokens"]["output"] += tokens.get("output", 0)

                    # Merge models
                    cost_data = data.get("cost", {}).get("by_model", {})
                    for model in cost_data.keys():
                        daily_combined[date]["models_used"][model] = \
                            daily_combined[date]["models_used"].get(model, 0) + 1

            except Exception as e:
                logger.error(f"Error getting daily stats for {project.get('display_name')}: {e}")
                continue

        # Sort by date
        result = [daily_combined[date] for date in sorted(daily_combined.keys())]
        return result


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
