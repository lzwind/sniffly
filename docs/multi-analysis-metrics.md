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

## Trellis 工作流统计

Trellis 是 AI 辅助开发工作流管理工具，通过 `/trellis:*` 形式的 slash command 调用。Sniffly 从 Claude Code 对话日志中扫描这些命令调用，统计 Trellis 的使用情况。

### 数据来源

| 来源 | 说明 |
|------|------|
| Claude JSONL 日志 | 从 `~/.claude/projects/` 下的用户消息（`type=user`）中匹配 `/trellis:xxx` 模式 |
| 导出 JSON 文件 | 新版导出的 JSON 包含 `trellis` 字段；旧版导出数据在分析时自动补全 |

### 扫描算法

```
正则: /trellis:([a-z][-a-z]*)

输入: 每条用户消息的 prompt 内容字符串
过程: 正则 findall 匹配所有 /trellis: 开头的命令
输出: {total_invocations, command_counts, top_commands, unique_commands, projects_with_trellis}
```

### 执行位置

Trellis 扫描在两个阶段执行（双保险）：

1. **导出阶段**（`ClaudeExportService.export()`）：从原始日志导出 JSON 时实时扫描
2. **分析阶段**（`AIUsageAnalyzer.generate_report()`）：分析旧版导出 JSON 时自动补全

```
新导出数据流程:
  JSONL 日志 → ClaudeLogProcessor → ClaudeExportService.export()
                                            ↓
                                    _scan_trellis_commands()
                                            ↓
                                    export_data.trellis ✓

旧导出数据流程:
  旧 JSON (无 trellis) → AIUsageAnalyzer.generate_report()
                              ↓
                     _scan_trellis_commands() ← 从 prompts 补全
                              ↓
                     data["trellis"] ✓ → 传递到前端
```

### 统计指标

| 指标 | 含义 | 计算方式 |
|------|------|----------|
| **total_invocations** | Trellis 命令总调用次数 | 所有匹配到的 `/trellis:*` 命令数之和（同一条消息中多次调用分别计数） |
| **command_counts** | 各命令调用次数 | `defaultdict(int)` 累计每种命令名出现次数 |
| **top_commands** | Top 5 常用命令 | 按 `command_counts` 降序取前 5 |
| **unique_commands** | 使用了不同命令种类数 | `len(command_counts)` |
| **projects_with_trellis** | 涉及的项目数 | 去重统计包含 trellis 命令的 `project` 字段 |

### 匹配的命令示例

| 命令 | 用途 |
|------|------|
| `/trellis:start` | 启动开发任务 |
| `/trellis:brainstorm` | 头脑风暴讨论 |
| `/trellis:workflow` | 工作流管理 |
| `/trellis:finish-work` | 完成当前工作 |
| `/trellis:cowork` | 多人协作开发 |
| `/trellis:record-session` | 记录开发会话 |
| `/trellis:commit` | 提交代码 |
| `/trellis:archive` | 归档完成的任务 |
| `/trellis:check-cross-layer` | 跨层检查 |
| `/trellis:parallel` | 并行任务分发 |

### 展示位置

| 页面 | 位置 |
|------|------|
| **个人分析页** | 各分析维度下方，独立 "Trellis 工作流使用" 卡片 |
| **多人排名表** | 新增 "Trellis" 列，显示每人调用次数 |
| **Markdown 报告** | 个人报告新增 "## Trellis 工作流使用" 小节；批量报告排名表新增 Trellis 列 |

### 注意事项

- 仅支持 Claude Code 数据源（OpenCode 日志中无此格式）
- 统计的是 slash command 调用次数，而非 Trellis 任务完成数
- 用户消息中的 `/trellis:` 必须出现在消息文本开头部分（正则非全行匹配），嵌套在长文本中间的不会被误匹配
- 旧版导出的 JSON 导入后自动补全，无需重新导出
