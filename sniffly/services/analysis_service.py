"""
AI Usage Analysis Service for generating efficiency reports
"""

import logging
from collections import Counter
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# Efficiency level thresholds
EFFICIENCY_LEVELS = {
    "A": {"min_score": 90, "description": "卓越 - 高效使用 AI，提效显著"},
    "B": {"min_score": 75, "description": "优秀 - 良好的 AI 使用习惯"},
    "C": {"min_score": 60, "description": "合格 - 基本有效使用 AI"},
    "D": {"min_score": 40, "description": "待改进 - AI 使用效率较低"},
    "E": {"min_score": 0, "description": "需优化 - AI 使用方式需重新审视"}
}


def get_efficiency_level(score: float) -> str:
    """Get efficiency level from score"""
    for level, config in EFFICIENCY_LEVELS.items():
        if score >= config["min_score"]:
            return level
    return "E"


class AIUsageAnalyzer:
    """AI Usage Data Analysis Service"""

    def _get_date_range(self, data: dict) -> dict:
        """Extract date range from data"""
        date_range = data.get("export_info", {}).get("date_range", {})
        if date_range.get("start") or date_range.get("end"):
            return date_range

        # Infer from daily_stats
        daily_stats = data.get("daily_stats", [])
        if daily_stats:
            dates = [d.get("date") for d in daily_stats if d.get("date")]
            if dates:
                return {"start": min(dates), "end": max(dates)}

        return {"start": None, "end": None}

    def analyze_activity(self, data: dict) -> dict:
        """Analyze activity level"""
        daily_stats = data.get("daily_stats", [])
        prompts = data.get("prompts", [])
        sessions = data.get("sessions", [])
        summary = data.get("summary", {})

        # Calculate metrics
        total_active_days = len(daily_stats)
        total_prompts = summary.get("total_prompts", len(prompts))
        total_sessions = summary.get("total_sessions", len(sessions))

        # Date range
        date_range = data.get("export_info", {}).get("date_range", {})
        start_date = date_range.get("start")
        end_date = date_range.get("end")

        # Calculate total days in range
        total_days = total_active_days
        if start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date.replace("Z", "+00:00").split("T")[0])
                end = datetime.fromisoformat(end_date.replace("Z", "+00:00").split("T")[0])
                total_days = max(1, (end - start).days + 1)
            except (ValueError, TypeError):
                pass
        elif daily_stats:
            # Infer from daily_stats if no explicit date range
            try:
                dates = [d.get("date") for d in daily_stats if d.get("date")]
                if dates:
                    first = datetime.strptime(min(dates), '%Y-%m-%d')
                    last = datetime.strptime(max(dates), '%Y-%m-%d')
                    total_days = max(1, (last - first).days + 1)
            except (ValueError, TypeError):
                pass

        # Averages
        daily_average_prompts = total_prompts / total_active_days if total_active_days > 0 else 0
        daily_average_sessions = total_sessions / total_active_days if total_active_days > 0 else 0
        active_days_percentage = (total_active_days / total_days * 100) if total_days > 0 else 0

        # Peak usage hours (from prompts timestamps)
        hour_counts = Counter()
        for prompt in prompts:
            ts = prompt.get("timestamp")
            if ts:
                try:
                    hour = datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
                    hour_counts[hour] += 1
                except (ValueError, TypeError):
                    pass

        peak_hours = [h for h, _ in hour_counts.most_common(3)]

        # Activity score (based on consistency and volume)
        score = 0
        if active_days_percentage >= 80:
            score += 30
        elif active_days_percentage >= 50:
            score += 20
        elif active_days_percentage >= 20:
            score += 10

        if daily_average_prompts >= 20:
            score += 30
        elif daily_average_prompts >= 10:
            score += 20
        elif daily_average_prompts >= 5:
            score += 10

        if daily_average_sessions >= 3:
            score += 20
        elif daily_average_sessions >= 1:
            score += 10

        if len(peak_hours) >= 2:
            score += 20

        return {
            "total_active_days": total_active_days,
            "total_days_in_range": total_days,
            "daily_average_prompts": round(daily_average_prompts, 1),
            "daily_average_sessions": round(daily_average_sessions, 1),
            "active_days_percentage": round(active_days_percentage, 1),
            "session_frequency": round(total_sessions / total_active_days, 1) if total_active_days > 0 else 0,
            "peak_usage_hours": peak_hours,
            "activity_score": min(100, score),
            "activity_level": "high" if score >= 70 else "medium" if score >= 40 else "low"
        }

    def analyze_task_efficiency(self, data: dict) -> dict:
        """Analyze task completion efficiency"""
        prompts = data.get("prompts", [])
        sessions = data.get("sessions", [])
        summary = data.get("summary", {})

        total_sessions = len(sessions)
        total_prompts = len(prompts)

        # Calculate session durations
        durations = []
        for session in sessions:
            start = session.get("started_at")
            end = session.get("ended_at")
            if start and end:
                try:
                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                    durations.append((end_dt - start_dt).total_seconds())
                except (ValueError, TypeError):
                    pass

        avg_duration = sum(durations) / len(durations) if durations else 0
        avg_prompts_per_session = total_prompts / total_sessions if total_sessions > 0 else 0

        # Calculate error and interruption rates
        errors = sum(1 for p in prompts if p.get("has_error"))
        interruptions = sum(1 for p in prompts if p.get("is_interruption"))

        error_rate = errors / total_prompts if total_prompts > 0 else 0
        interruption_rate = interruptions / total_prompts if total_prompts > 0 else 0

        # Success rate (prompts without errors or interruptions)
        successful = total_prompts - errors - interruptions
        success_rate = successful / total_prompts if total_prompts > 0 else 1

        # Efficiency score
        score = 0
        if success_rate >= 0.95:
            score += 40
        elif success_rate >= 0.90:
            score += 30
        elif success_rate >= 0.80:
            score += 20
        elif success_rate >= 0.70:
            score += 10

        if avg_prompts_per_session >= 5 and avg_prompts_per_session <= 30:
            score += 30  # Good balance
        elif avg_prompts_per_session >= 3 and avg_prompts_per_session <= 50:
            score += 20
        else:
            score += 10

        if avg_duration > 0 and avg_duration <= 3600:  # Under 1 hour
            score += 30
        elif avg_duration > 0 and avg_duration <= 7200:  # Under 2 hours
            score += 20
        elif avg_duration > 0:
            score += 10

        return {
            "total_sessions": total_sessions,
            "avg_session_duration_seconds": round(avg_duration, 0),
            "avg_session_duration_minutes": round(avg_duration / 60, 1),
            "avg_prompts_per_session": round(avg_prompts_per_session, 1),
            "interruption_rate": round(interruption_rate * 100, 1),
            "error_rate": round(error_rate * 100, 1),
            "successful_completion_rate": round(success_rate * 100, 1),
            "task_efficiency_score": min(100, score),
            "task_efficiency_level": get_efficiency_level(score)
        }

    def analyze_token_efficiency(self, data: dict) -> dict:
        """Analyze token utilization"""
        summary = data.get("summary", {})
        prompts = data.get("prompts", [])

        tokens = summary.get("total_tokens", {})
        total_input = tokens.get("input", 0)
        total_output = tokens.get("output", 0)
        total_cache_read = tokens.get("cache_read", 0)
        total_cache_creation = tokens.get("cache_creation", 0)
        total = total_input + total_output

        total_prompts = len(prompts)

        # Averages
        avg_tokens_per_prompt = total / total_prompts if total_prompts > 0 else 0

        # Cache efficiency
        total_cache = total_cache_read + total_cache_creation
        cache_hit_rate = total_cache_read / (total_input + total_cache_read) if (total_input + total_cache_read) > 0 else 0

        # Input/output ratio
        io_ratio = total_input / total_output if total_output > 0 else 0

        # Efficiency score
        score = 0
        if cache_hit_rate >= 0.5:
            score += 30
        elif cache_hit_rate >= 0.3:
            score += 20
        elif cache_hit_rate >= 0.1:
            score += 10

        if io_ratio >= 2 and io_ratio <= 10:  # Good balance
            score += 30
        elif io_ratio >= 1 and io_ratio <= 20:
            score += 20
        else:
            score += 10

        if avg_tokens_per_prompt > 0 and avg_tokens_per_prompt <= 5000:
            score += 20
        elif avg_tokens_per_prompt <= 10000:
            score += 15
        elif avg_tokens_per_prompt <= 20000:
            score += 10

        if total > 0:
            score += 20  # Has activity

        return {
            "total_tokens": {
                "input": total_input,
                "output": total_output,
                "cache_read": total_cache_read,
                "cache_creation": total_cache_creation,
                "total": total
            },
            "avg_tokens_per_prompt": round(avg_tokens_per_prompt, 0),
            "avg_tokens_per_session": round(total / data.get("summary", {}).get("total_sessions", 1), 0) if data.get("summary", {}).get("total_sessions", 0) > 0 else 0,
            "cache_hit_rate": round(cache_hit_rate * 100, 1),
            "cache_efficiency": round(total_cache / total * 100, 1) if total > 0 else 0,
            "input_output_ratio": round(io_ratio, 2),
            "token_efficiency_score": min(100, score),
            "token_efficiency_level": get_efficiency_level(score)
        }

    def analyze_tool_usage(self, data: dict) -> dict:
        """Analyze tool usage diversity"""
        prompts = data.get("prompts", [])

        # Count tools
        all_tools = []
        tool_counts = Counter()

        for prompt in prompts:
            tools = prompt.get("tools_used", [])
            all_tools.extend(tools)
            for tool in tools:
                tool_counts[tool] += 1

        total_tools_used = len(all_tools)
        unique_tools = len(tool_counts)
        total_prompts = len(prompts)

        avg_tools_per_prompt = total_tools_used / total_prompts if total_prompts > 0 else 0

        # Tool diversity (Shannon entropy based)
        import math
        diversity_score = 0
        if total_tools_used > 0:
            for count in tool_counts.values():
                p = count / total_tools_used
                diversity_score -= p * math.log2(p) if p > 0 else 0
            diversity_score = (diversity_score / math.log2(max(unique_tools, 2))) * 100 if unique_tools > 1 else 0

        most_used_tools = [t for t, _ in tool_counts.most_common(5)]

        # Efficiency score
        score = 0
        if unique_tools >= 5:
            score += 25
        elif unique_tools >= 3:
            score += 15
        elif unique_tools >= 1:
            score += 5

        if avg_tools_per_prompt >= 2 and avg_tools_per_prompt <= 5:
            score += 25
        elif avg_tools_per_prompt >= 1 and avg_tools_per_prompt <= 10:
            score += 15
        elif avg_tools_per_prompt > 0:
            score += 5

        if diversity_score >= 50:
            score += 25
        elif diversity_score >= 25:
            score += 15
        elif diversity_score > 0:
            score += 5

        if total_tools_used > 0:
            score += 25

        return {
            "total_tools_used": total_tools_used,
            "unique_tools_count": unique_tools,
            "tool_distribution": dict(tool_counts),
            "avg_tools_per_prompt": round(avg_tools_per_prompt, 2),
            "tool_diversity_score": round(diversity_score, 1),
            "most_used_tools": most_used_tools,
            "tool_usage_efficiency": round(min(100, avg_tools_per_prompt * 20), 1),
            "tool_usage_score": min(100, score),
            "tool_usage_level": "diverse" if unique_tools >= 5 else "moderate" if unique_tools >= 2 else "focused"
        }

    def analyze_code_changes(self, data: dict) -> dict:
        """Analyze code change correlation"""
        sessions = data.get("sessions", [])
        prompts = data.get("prompts", [])

        # Basic metrics (OpenCode may have diff info in session)
        sessions_with_activity = len([s for s in sessions if s.get("total_prompts", 0) > 0])

        # Productivity score
        total_prompts = len(prompts)
        productivity = total_prompts / sessions_with_activity if sessions_with_activity > 0 else 0

        score = 0
        if productivity >= 10:
            score += 50
        elif productivity >= 5:
            score += 30
        elif productivity >= 1:
            score += 10

        if sessions_with_activity >= 5:
            score += 30
        elif sessions_with_activity >= 2:
            score += 20
        elif sessions_with_activity >= 1:
            score += 10

        score += 20  # Base score for having activity

        return {
            "total_sessions": len(sessions),
            "sessions_with_activity": sessions_with_activity,
            "productivity_score": round(min(100, score), 1),
            "avg_prompts_per_active_session": round(productivity, 1),
            "code_change_correlation": "N/A",  # Would need git integration
            "note": "Code change analysis requires additional git integration for detailed metrics"
        }

    def analyze_prompt_quality(self, data: dict) -> dict:
        """Analyze prompt reasonability"""
        prompts = data.get("prompts", [])

        if not prompts:
            return {
                "total_prompts": 0,
                "avg_prompt_length": 0,
                "prompt_length_distribution": {"short": 0, "medium": 0, "long": 0},
                "prompts_with_code_percentage": 0,
                "prompt_clarity_score": 0,
                "prompt_reasonability_score": 0,
                "prompt_quality_level": "unknown"
            }

        total_prompts = len(prompts)

        # Length analysis
        lengths = [len(p.get("prompt", "")) for p in prompts]
        avg_length = sum(lengths) / len(lengths)

        short = sum(1 for l in lengths if l < 100)
        medium = sum(1 for l in lengths if 100 <= l < 500)
        long = sum(1 for l in lengths if l >= 500)

        # Code detection (simple heuristic)
        code_keywords = ["def ", "class ", "import ", "function ", "const ", "let ", "var ", "```", "return "]
        prompts_with_code = sum(
            1 for p in prompts
            if any(kw in p.get("prompt", "") for kw in code_keywords)
        )

        # Clarity heuristics
        clear_prompts = 0
        for p in prompts:
            text = p.get("prompt", "")
            # Heuristics for clear prompts
            if len(text) >= 20:  # Not too short
                clear_prompts += 1
                if any(kw in text.lower() for kw in ["please", "help", "fix", "create", "implement", "分析", "修复", "实现"]):
                    clear_prompts += 0.5

        clarity_score = min(100, (clear_prompts / total_prompts) * 50)

        # Quality score
        score = 0
        if avg_length >= 50 and avg_length <= 500:
            score += 25
        elif avg_length >= 20 and avg_length <= 1000:
            score += 15

        code_percentage = prompts_with_code / total_prompts * 100
        if code_percentage >= 20 and code_percentage <= 80:
            score += 25
        elif code_percentage > 0:
            score += 15

        score += clarity_score * 0.5

        return {
            "total_prompts": total_prompts,
            "avg_prompt_length": round(avg_length, 0),
            "prompt_length_distribution": {
                "short": short,
                "medium": medium,
                "long": long
            },
            "prompts_with_code_percentage": round(code_percentage, 1),
            "prompts_with_code_count": prompts_with_code,
            "prompt_clarity_score": round(clarity_score, 1),
            "prompt_reasonability_score": round(min(100, score), 1),
            "prompt_quality_level": "excellent" if score >= 75 else "good" if score >= 50 else "needs_improvement"
        }

    def analyze_prompt_quantity(self, data: dict) -> dict:
        """Analyze prompt quantity"""
        prompts = data.get("prompts", [])
        daily_stats = data.get("daily_stats", [])
        sessions = data.get("sessions", [])
        projects = data.get("projects", [])

        total_prompts = len(prompts)
        total_days = len(daily_stats)
        total_sessions = len(sessions)
        total_projects = len(projects)

        prompts_per_day = total_prompts / total_days if total_days > 0 else 0
        prompts_per_session = total_prompts / total_sessions if total_sessions > 0 else 0
        prompts_per_project = total_prompts / total_projects if total_projects > 0 else 0

        # Trend analysis (compare first half vs second half)
        trend = "stable"
        if len(daily_stats) >= 4:
            half = len(daily_stats) // 2
            first_half = sum(d.get("prompts", 0) for d in daily_stats[:half])
            second_half = sum(d.get("prompts", 0) for d in daily_stats[half:])
            if second_half > first_half * 1.2:
                trend = "increasing"
            elif second_half < first_half * 0.8:
                trend = "decreasing"

        # Quantity score
        score = 0
        if prompts_per_day >= 10 and prompts_per_day <= 50:
            score += 30
        elif prompts_per_day >= 5:
            score += 20
        elif prompts_per_day >= 1:
            score += 10

        if prompts_per_session >= 5 and prompts_per_session <= 30:
            score += 30
        elif prompts_per_session >= 2:
            score += 20
        elif prompts_per_session >= 1:
            score += 10

        if trend == "stable":
            score += 20
        elif trend == "increasing":
            score += 15
        else:
            score += 5

        if total_prompts >= 50:
            score += 20
        elif total_prompts >= 10:
            score += 10

        return {
            "total_prompts": total_prompts,
            "prompts_per_day_average": round(prompts_per_day, 1),
            "prompts_per_session_average": round(prompts_per_session, 1),
            "prompts_per_project_average": round(prompts_per_project, 1),
            "prompt_frequency_trend": trend,
            "prompt_quantity_score": min(100, score)
        }

    def generate_report(self, data: dict) -> dict:
        """Generate comprehensive analysis report"""
        activity = self.analyze_activity(data)
        task_efficiency = self.analyze_task_efficiency(data)
        token_efficiency = self.analyze_token_efficiency(data)
        tool_usage = self.analyze_tool_usage(data)
        code_changes = self.analyze_code_changes(data)
        prompt_quality = self.analyze_prompt_quality(data)
        prompt_quantity = self.analyze_prompt_quantity(data)

        # Calculate overall score
        scores = [
            activity.get("activity_score", 0) * 0.1,
            task_efficiency.get("task_efficiency_score", 0) * 0.2,
            token_efficiency.get("token_efficiency_score", 0) * 0.15,
            tool_usage.get("tool_usage_score", 0) * 0.15,
            prompt_quality.get("prompt_reasonability_score", 0) * 0.25,
            prompt_quantity.get("prompt_quantity_score", 0) * 0.15,
        ]
        overall_score = sum(scores)

        # Identify strengths and areas for improvement
        all_metrics = {
            "activity": activity.get("activity_score", 0),
            "task_efficiency": task_efficiency.get("task_efficiency_score", 0),
            "token_efficiency": token_efficiency.get("token_efficiency_score", 0),
            "tool_usage": tool_usage.get("tool_usage_score", 0),
            "prompt_quality": prompt_quality.get("prompt_reasonability_score", 0),
            "prompt_quantity": prompt_quantity.get("prompt_quantity_score", 0),
        }

        sorted_metrics = sorted(all_metrics.items(), key=lambda x: x[1], reverse=True)
        strengths = [m[0] for m in sorted_metrics[:2]]
        improvements = [m[0] for m in sorted_metrics[-2:] if m[1] < 60]

        # Generate recommendations
        recommendations = []
        if task_efficiency.get("error_rate", 0) > 10:
            recommendations.append("建议优化提示词以降低错误率，确保指令清晰明确")
        if task_efficiency.get("interruption_rate", 0) > 15:
            recommendations.append("中断率较高，建议提前规划任务，减少中途修改")
        if token_efficiency.get("cache_hit_rate", 0) < 30:
            recommendations.append("缓存利用率较低，可考虑在会话中复用上下文以节省 token")
        if tool_usage.get("unique_tools_count", 0) < 3:
            recommendations.append("工具使用种类较少，可尝试使用更多 AI 工具提高效率")
        if prompt_quality.get("avg_prompt_length", 0) < 50:
            recommendations.append("提示词平均长度较短，建议提供更多上下文信息")
        if activity.get("active_days_percentage", 0) < 50:
            recommendations.append("活跃天数占比较低，建议保持更规律的 AI 使用习惯")
        if not recommendations:
            recommendations.append("AI 使用习惯良好，继续保持！")

        return {
            "source": data.get("source"),
            "analysis_timestamp": datetime.now().isoformat(),
            "developer": data.get("developer"),
            "date_range": self._get_date_range(data),

            # Individual analysis
            "activity_analysis": activity,
            "task_efficiency_analysis": task_efficiency,
            "token_efficiency_analysis": token_efficiency,
            "tool_usage_analysis": tool_usage,
            "code_change_analysis": code_changes,
            "prompt_quality_analysis": prompt_quality,
            "prompt_quantity_analysis": prompt_quantity,

            # Overall assessment
            "overall_assessment": {
                "overall_score": round(overall_score, 1),
                "efficiency_level": get_efficiency_level(overall_score),
                "strengths": strengths,
                "areas_for_improvement": improvements,
                "recommendations": recommendations,
                "level_description": EFFICIENCY_LEVELS.get(get_efficiency_level(overall_score), {}).get("description", "")
            }
        }

    def generate_markdown_report(self, data: dict) -> str:
        """Generate Markdown format analysis report"""
        self._data = data
        report = self.generate_report(data)
        return self._format_as_markdown(report)

    def _format_as_markdown(self, report: dict) -> str:
        """Format analysis report as Markdown"""
        overall = report["overall_assessment"]
        lines = []

        # Title
        source_name = "Claude Code" if report["source"] == "claude" else "OpenCode"
        lines.append(f"# {source_name} AI 使用分析报告\n")

        # Meta info
        lines.append(f"**开发者**: {report.get('developer', {}).get('name', 'Unknown')}")
        date_range = report.get("date_range", {})
        if date_range.get("start") and date_range.get("end"):
            lines.append(f"**分析周期**: {date_range['start']} 至 {date_range['end']}")
        lines.append(f"**生成时间**: {report.get('analysis_timestamp', 'N/A')}\n")

        # Overall Score
        lines.append("## 综合评估\n")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 综合评分 | **{overall['overall_score']}** 分 |")
        lines.append(f"| 效率等级 | **{overall['efficiency_level']}** 级 |")
        lines.append(f"| 评价 | {overall['level_description']} |\n")

        # Strengths and Improvements
        lines.append("### 优势领域\n")
        for s in overall["strengths"]:
            lines.append(f"- {self._translate_metric(s)}")
        lines.append("")

        lines.append("### 待改进领域\n")
        if overall["areas_for_improvement"]:
            for s in overall["areas_for_improvement"]:
                lines.append(f"- {self._translate_metric(s)}")
        else:
            lines.append("- 暂无明显短板")
        lines.append("")

        # Recommendations
        lines.append("### 改进建议\n")
        for r in overall["recommendations"]:
            lines.append(f"- {r}")
        lines.append("")

        # Activity Analysis
        activity = report["activity_analysis"]
        lines.append("## 活跃度分析\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|------|")
        lines.append(f"| 活跃天数 | {activity['total_active_days']} 天 / {activity['total_days_in_range']} 天 |")
        lines.append(f"| 活跃率 | {activity['active_days_percentage']}% |")
        lines.append(f"| 日均提示词 | {activity['daily_average_prompts']} |")
        lines.append(f"| 日均会话 | {activity['daily_average_sessions']} |")
        lines.append(f"| 高峰时段 | {', '.join([f'{h}:00' for h in activity['peak_usage_hours']]) or 'N/A'} |")
        lines.append(f"| 活跃度评分 | {activity['activity_score']} 分 ({activity['activity_level']}) |\n")

        # Task Efficiency
        task = report["task_efficiency_analysis"]
        lines.append("## 任务效率分析\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|------|")
        lines.append(f"| 总会话数 | {task['total_sessions']} |")
        lines.append(f"| 平均会话时长 | {task['avg_session_duration_minutes']} 分钟 |")
        lines.append(f"| 会话平均提示词 | {task['avg_prompts_per_session']} |")
        lines.append(f"| 中断率 | {task['interruption_rate']}% |")
        lines.append(f"| 错误率 | {task['error_rate']}% |")
        lines.append(f"| 成功率 | {task['successful_completion_rate']}% |")
        lines.append(f"| 效率评分 | {task['task_efficiency_score']} 分 ({task['task_efficiency_level']}级) |\n")

        # Token Efficiency
        token = report["token_efficiency_analysis"]
        tokens = token["total_tokens"]
        lines.append("## Token 效率分析\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|------|")
        lines.append(f"| 输入 Token | {self._format_number(tokens['input'])} |")
        lines.append(f"| 输出 Token | {self._format_number(tokens['output'])} |")
        lines.append(f"| 缓存读取 | {self._format_number(tokens['cache_read'])} |")
        lines.append(f"| 缓存写入 | {self._format_number(tokens['cache_creation'])} |")
        lines.append(f"| 缓存命中率 | {token['cache_hit_rate']}% |")
        lines.append(f"| 平均每提示词 Token | {self._format_number(token['avg_tokens_per_prompt'])} |")
        lines.append(f"| 输入输出比 | {token['input_output_ratio']} |")
        lines.append(f"| 效率评分 | {token['token_efficiency_score']} 分 ({token['token_efficiency_level']}级) |\n")

        # Tool Usage
        tool = report["tool_usage_analysis"]
        lines.append("## 工具使用分析\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|------|")
        lines.append(f"| 工具使用总次数 | {tool['total_tools_used']} |")
        lines.append(f"| 工具种类 | {tool['unique_tools_count']} 种 |")
        lines.append(f"| 平均每提示词工具数 | {tool['avg_tools_per_prompt']} |")
        lines.append(f"| 多样性评分 | {tool['tool_diversity_score']} |")
        level_map = {"diverse": "多样化", "moderate": "适中", "focused": "专注"}
        lines.append(f"| 使用水平 | {level_map.get(tool['tool_usage_level'], tool['tool_usage_level'])} |\n")

        # Tool distribution
        if tool["tool_distribution"]:
            lines.append("### 工具使用分布\n")
            lines.append("| 工具 | 使用次数 |")
            lines.append("|------|----------|")
            for tool_name, count in sorted(tool["tool_distribution"].items(), key=lambda x: -x[1])[:10]:
                lines.append(f"| {tool_name} | {count} |")
            lines.append("")

        # Prompt Quality
        quality = report["prompt_quality_analysis"]
        lines.append("## 提示词质量分析\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|------|")
        lines.append(f"| 提示词总数 | {quality['total_prompts']} |")
        lines.append(f"| 平均长度 | {self._format_number(quality['avg_prompt_length'])} 字符 |")
        dist = quality["prompt_length_distribution"]
        lines.append(f"| 长度分布 | 短:{dist['short']} / 中:{dist['medium']} / 长:{dist['long']} |")
        lines.append(f"| 含代码提示词占比 | {quality['prompts_with_code_percentage']}% |")
        lines.append(f"| 清晰度评分 | {quality['prompt_clarity_score']} 分 |")
        quality_map = {"excellent": "优秀", "good": "良好", "needs_improvement": "待改进"}
        lines.append(f"| 质量等级 | {quality_map.get(quality['prompt_quality_level'], quality['prompt_quality_level'])} |\n")

        # Prompt Quantity
        quantity = report["prompt_quantity_analysis"]
        lines.append("## 提示词数量分析\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|------|")
        lines.append(f"| 提示词总数 | {quantity['total_prompts']} |")
        lines.append(f"| 日均提示词 | {quantity['prompts_per_day_average']} |")
        lines.append(f"| 每会话提示词 | {quantity['prompts_per_session_average']} |")
        lines.append(f"| 每项目提示词 | {quantity['prompts_per_project_average']} |")
        trend_map = {"increasing": "📈 上升", "decreasing": "📉 下降", "stable": "➡️ 稳定"}
        lines.append(f"| 频率趋势 | {trend_map.get(quantity['prompt_frequency_trend'], quantity['prompt_frequency_trend'])} |")
        lines.append(f"| 数量评分 | {quantity['prompt_quantity_score']} 分 |\n")

        # Daily Stats (from original data)
        daily_stats = self._data.get("daily_stats", [])
        if daily_stats:
            lines.append("## 每日统计\n")
            lines.append("| 日期 | 请求 | 会话 | 提示词 | 输入Token | 输出Token |")
            lines.append("|------|------|------|--------|-----------|----------|")
            for d in daily_stats:
                tokens = d.get("tokens", {})
                lines.append(
                    f"| {d.get('date', 'N/A')} "
                    f"| {d.get('requests', d.get('messages', 0))} "
                    f"| {d.get('sessions', 0)} "
                    f"| {d.get('prompts', 0)} "
                    f"| {self._format_number(tokens.get('input', 0))} "
                    f"| {self._format_number(tokens.get('output', 0))} |"
                )
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*本报告由 Sniffly AI 使用分析工具自动生成*")

        return "\n".join(lines)

    def _translate_metric(self, metric: str) -> str:
        """Translate metric name to Chinese"""
        translations = {
            'activity': '活跃度',
            'task_efficiency': '任务效率',
            'token_efficiency': 'Token 效率',
            'tool_usage': '工具使用',
            'prompt_quality': '提示词质量',
            'prompt_quantity': '提示词数量',
            'code_changes': '代码改动'
        }
        return translations.get(metric, metric)

    def _format_number(self, num: int) -> str:
        """Format number with K/M suffix"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        if num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)
