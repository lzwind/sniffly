# Sniffly - AI Code Analytics Dashboard

分析 Claude Code 和 OpenCode 的使用日志，帮助你更好地使用 AI 编程助手。

[功能特性](#-功能特性) | [快速开始](#-快速开始) | [导出数据](#-导出数据) | [分析报告](#-分析报告)

## 📊 功能特性

### 双数据源支持
- **Claude Code**: 分析 `~/.claude/projects/` 下的 JSONL 日志
- **OpenCode**: 分析 `~/.local/share/opencode/opencode.db` SQLite 数据库

### 数据统计
<center>
<img src="assets/features/stats.png" width="800" />
</center>

- 项目级统计：会话数、Token 使用量、成本估算
- 每日统计：请求、会话、Token 趋势
- 模型分布：各模型使用占比

### 数据导出
支持导出 AI 使用数据，方便团队分析和绩效评估：
- **汇总报告 (Markdown)**: 总请求、会话、Token、每日统计
- **详细报告 (Markdown)**: 包含完整提示词记录
- **原始数据 (JSON)**: 完整数据结构

### 分析报告
AI 使用效率评分系统，包含六个维度：
- 📈 **活跃度分析**: 活跃天数、日均使用量
- ⚡ **任务效率**: 会话时长、成功率、错误率
- 💰 **Token 效率**: 缓存命中率、输入输出比
- 🛠️ **工具使用**: 工具多样性、使用频率
- 📝 **提示词质量**: 长度分布、清晰度评分
- 📊 **提示词数量**: 频率趋势、日均数量

效率等级：A (卓越) / B (优秀) / C (合格) / D (待改进) / E (需优化)

## 🚀 快速开始

### 环境要求
- Python 3.10+

### 使用 UV 安装（推荐）

确保已安装 `uv`: https://github.com/astral-sh/uv

```bash
# 一次性运行（无需安装）
uvx sniffly-lzwind@latest init

# 或安装后使用
uv tool install sniffly-lzwind@latest
sniffly init
```

### 使用 pip 安装

```bash
pip install sniffly-lzwind
sniffly init
```

### 从源码安装

```bash
git clone https://github.com/lzwind/sniffly.git
cd sniffly
pip install -e .
sniffly init
```

启动后访问 http://localhost:8081 查看仪表盘。

## 📥 导出数据

### Web 界面导出
1. 点击页面顶部 "📥 导出数据" 按钮
2. 选择数据源（Claude Code / OpenCode / 两者）
3. 选择项目（可选）
4. 选择导出类型：
   - 汇总报告 (Markdown)
   - 详细报告 (Markdown，含提示词)
   - 原始数据 (JSON)
5. 设置日期范围（可选）
6. 点击"导出"

### 导出示例

**Markdown 汇总报告**:
```markdown
# AI 使用数据报告

**项目**: All Projects
**数据源**: claude
**开发者**: Zhang San (zhangsan@example.com)

## 汇总统计

| 指标 | 数值 |
|------|------|
| 总请求 | 3883 |
| 总会话 | 44 |
| 总提示词 | 378 |
| 输入 Token | 113,413,750 |
| 输出 Token | 832,028 |

## 每日统计

| 日期 | 请求 | 会话 | 提示词 | 输入Token | 输出Token |
|------|------|------|--------|-----------|----------|
| 2026-03-14 | 13 | 1 | 13 | 133,505 | 51,138 |
...
```

## 📈 分析报告

访问 http://localhost:8081/analysis 查看分析报告。

### 评分维度权重

| 维度 | 权重 | 说明 |
|------|------|------|
| 提示词质量 | 25% | 清晰度、合理性 |
| 任务效率 | 20% | 成功率、会话效率 |
| Token 效率 | 15% | 缓存利用、输入输出比 |
| 工具使用 | 15% | 工具多样性 |
| 提示词数量 | 15% | 使用频率 |
| 活跃度 | 10% | 使用连贯性 |

## 🔧 配置

### 常用设置

```bash
# 更改端口（默认 8081）
sniffly config set port 8090

# 禁用自动打开浏览器
sniffly config set auto_browser false

# 查看当前配置
sniffly config show
```

### 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `port` | 8081 | 服务端口 |
| `host` | 127.0.0.1 | 服务主机 |
| `auto_browser` | true | 启动时自动打开浏览器 |
| `cache_max_projects` | 5 | 内存缓存最大项目数 |
| `cache_max_mb_per_project` | 500 | 每个项目最大缓存 MB |
| `messages_initial_load` | 500 | 初始加载消息数 |
| `max_date_range_days` | 30 | 日期范围选择最大天数 |

## 💡 分享仪表盘

可以创建链接与同事分享项目统计：

1. 点击仪表盘中的 "📤 Share" 按钮
2. 选择隐私选项：
   - **Private**: 只有链接的人可以查看
   - **Public**: 列在公共画廊
   - **Include Commands**: 分享实际命令内容
3. 复制并分享生成的链接

## 🚨 故障排除

```bash
sniffly help
```

**端口被占用？**
```bash
sniffly init --port 8090
```

**浏览器没有打开？**
```bash
sniffly config set auto_browser true
# 或手动访问 http://localhost:8081
```

**配置问题？**
```bash
# 查看所有设置
sniffly config show

# 重置配置
rm ~/.sniffly/config.json
```

## 🔐 隐私

Sniffly 完全在本地运行：
- ✅ 所有数据处理都在本地进行
- ✅ 无遥测数据
- ✅ 你的对话不会离开你的电脑
- ✅ 共享仪表盘仅在你选择时启用

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

## 🔗 链接

- **GitHub**: [github.com/lzwind/sniffly](https://github.com/lzwind/sniffly)
- **原项目**: [github.com/chiphuyen/sniffly](https://github.com/chiphuyen/sniffly)
- **问题反馈**: [GitHub Issues](https://github.com/lzwind/sniffly/issues)

## 🙏 致谢

本项目基于 [Sniffly](https://github.com/chiphuyen/sniffly) 开发，增加了以下功能：
- OpenCode 数据源支持
- AI 使用效率分析报告
- 数据导出功能（Markdown/JSON）
- 双数据源对比分析
