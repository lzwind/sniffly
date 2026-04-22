# 多人分析指标计算说明

## 数据来源

分析数据来自首页"导出数据"功能生成的 JSON 文件，每个文件包含一个人的 AI 使用记录。

## 排名表指标

| 指标 | 计算方式 |
|------|----------|
| **总消息数** | 导出 JSON 中 `summary.total_requests`，统计所有类型消息（用户消息 + 助手回复 + 工具结果）的总数 |
| **用户消息数** | 导出 JSON 中 `summary.total_prompts`，仅统计用户发送的消息（排除工具结果 `tool_result` 类型） |
| **Token** | 导出 JSON 中 `summary.total_tokens`，取 `input + output` 之和（不含缓存 Token） |
| **提示词** | 分析报告 `analysis.prompt_quantity_analysis.total_prompts`，从提示词列表重新计数 |
| **活跃等级** | 按 `总消息数` 分档：≥5000 极高，≥1000 高，<1000 中 |

## 分组汇总表指标

| 指标 | 计算方式 |
|------|----------|
| **人数** | 该分组内的人数 |
| **总消息数** | 分组内所有人 `总消息数` 之和 |
| **平均消息数** | `总消息数 / 人数` |
| **Token** | 分组内所有人 `Token` 之和 |
| **提示词** | 分组内所有人 `提示词` 之和 |
| **最高使用者** | 该分组中综合评分最高的人 |
| **占比** | 该分组 `总消息数 / 全部总消息数 × 100%` |

## 个人详情 - 数据概览

点击排名表中某一行进入个人详情页，顶部显示"数据概览"卡片：

| 指标 | 来源 |
|------|------|
| **总消息数** | `summary.total_requests` |
| **用户消息数** | `summary.total_prompts` |
| **Token 总量** | `summary.total_tokens`（input + output） |
| **总费用** | `summary.total_cost`（仅 Claude 数据有值，OpenCode 为 $0） |

## 综合评分计算

综合评分（0-100 分）由 6 个子维度加权得出：

| 维度 | 权重 | 来源 |
|------|------|------|
| 活跃度 | 10% | `activity_analysis.activity_score` |
| 任务效率 | 20% | `task_efficiency_analysis.task_efficiency_score` |
| Token 效率 | 15% | `token_efficiency_analysis.token_efficiency_score` |
| 工具使用 | 15% | `tool_usage_analysis.tool_usage_score` |
| 提示词质量 | 25% | `prompt_quality_analysis.prompt_reasonability_score` |
| 提示词数量 | 15% | `prompt_quantity_analysis.prompt_quantity_score` |

## 文件夹分组规则

通过"选择文件夹"导入时，按文件夹结构自动分组：

- `FolderName/file.json` → 分组为 `FolderName`（无子目录）
- `FolderName/subdir/file.json` → 分组为 `subdir`（子目录名作为分组）
- 文件名（去掉 `.json` 后缀）作为人名
