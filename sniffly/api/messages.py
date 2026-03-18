"""
Messages API endpoint with pagination support.
"""

import re
from datetime import datetime, timedelta, timezone

_DATE_RE = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")


def _parse_local_datetime(date_str: str, tz: timezone, end_of_day: bool = False) -> datetime:
    """Validate and parse a YYYY-MM-DD string into a UTC-aware datetime.

    Args:
        date_str: Date string in YYYY-MM-DD format
        tz: Local timezone
        end_of_day: If True, return 23:59:59.999999; otherwise 00:00:00

    Raises:
        ValueError: If the format is invalid or the date is out of calendar range
    """
    if not _DATE_RE.match(date_str):
        raise ValueError(f"Invalid date format: {date_str!r}, expected YYYY-MM-DD")
    y, m, d = (int(x) for x in date_str.split("-"))
    time_args = (23, 59, 59, 999999) if end_of_day else (0, 0, 0)
    return datetime(y, m, d, *time_args, tzinfo=tz).astimezone(timezone.utc)


def filter_messages_by_time(
    messages: list[dict],
    start_date: str | None = None,
    end_date: str | None = None,
    timezone_offset_minutes: int = 0,
) -> list[dict]:
    """Filter messages by local date range.

    Args:
        messages: Full list of messages
        start_date: Start date in YYYY-MM-DD (local time), inclusive
        end_date: End date in YYYY-MM-DD (local time), inclusive
        timezone_offset_minutes: Local UTC offset in minutes (e.g. 480 for UTC+8)

    Returns:
        Filtered list of messages

    Raises:
        ValueError: If start_date or end_date is not a valid YYYY-MM-DD string
    """
    if not start_date and not end_date:
        return messages

    tz = timezone(timedelta(minutes=timezone_offset_minutes))

    start_dt: datetime | None = None
    end_dt: datetime | None = None

    if start_date:
        start_dt = _parse_local_datetime(start_date, tz, end_of_day=False)

    if end_date:
        end_dt = _parse_local_datetime(end_date, tz, end_of_day=True)

    result = []
    for msg in messages:
        ts = msg.get("timestamp", "")
        if not ts:
            continue
        try:
            if ts.endswith("Z"):
                msg_dt = datetime.fromisoformat(ts[:-1]).replace(tzinfo=timezone.utc)
            else:
                msg_dt = datetime.fromisoformat(ts)
                if msg_dt.tzinfo is None:
                    msg_dt = msg_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        if start_dt and msg_dt < start_dt:
            continue
        if end_dt and msg_dt > end_dt:
            continue
        result.append(msg)

    return result


def get_paginated_messages(messages: list[dict], page: int = 1, per_page: int = 100, include_all: bool = False) -> dict:
    """
    Return paginated messages or all messages based on flag.

    Args:
        messages: Full list of messages
        page: Page number (1-indexed)
        per_page: Items per page
        include_all: If True, return all messages (for backwards compatibility)

    Returns:
        Dictionary with messages and pagination info
    """
    if include_all:
        # Return all messages for charts and full analysis
        return {"messages": messages, "total": len(messages), "page": 1, "per_page": len(messages), "total_pages": 1}

    # Calculate pagination
    total = len(messages)
    total_pages = (total + per_page - 1) // per_page

    # Validate page number
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    # Get page slice
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_messages = messages[start_idx:end_idx]

    return {
        "messages": page_messages,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "start_index": start_idx,
        "end_index": min(end_idx, total),
    }


def get_messages_summary(messages: list[dict]) -> dict:
    """
    Get summary statistics about messages without returning all data.

    Args:
        messages: Full list of messages

    Returns:
        Summary statistics
    """
    if not messages:
        return {"total": 0, "by_type": {}, "by_model": {}, "total_tokens": 0}

    by_type = {}
    by_model = {}
    total_tokens = 0

    for msg in messages:
        # Count by type
        msg_type = msg.get("type", "unknown")
        by_type[msg_type] = by_type.get(msg_type, 0) + 1

        # Count by model
        model = msg.get("model", "unknown")
        by_model[model] = by_model.get(model, 0) + 1

        # Sum tokens
        tokens = msg.get("tokens", {})
        if isinstance(tokens, dict):
            total_tokens += tokens.get("input", 0) + tokens.get("output", 0)

    return {"total": len(messages), "by_type": by_type, "by_model": by_model, "total_tokens": total_tokens}
