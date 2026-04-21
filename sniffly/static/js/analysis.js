/**
 * AI Usage Analysis Page JavaScript
 */

let currentSource = 'claude';
let currentAnalysis = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Set default date range (last 30 days)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    document.getElementById('end-date').value = endDate.toISOString().split('T')[0];
    document.getElementById('start-date').value = startDate.toISOString().split('T')[0];

    // Load projects for filter
    loadProjects();
});

async function loadProjects() {
    try {
        // Load Claude projects
        const claudeResponse = await fetch('/api/projects');
        const claudeData = await claudeResponse.json();

        // Load OpenCode projects
        const opencodeResponse = await fetch('/api/opencode/projects');
        const opencodeData = await opencodeResponse.json();

        const select = document.getElementById('project-filter');

        // Add Claude projects
        if (claudeData.projects) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = 'Claude Code 项目';
            claudeData.projects.forEach(p => {
                const option = document.createElement('option');
                option.value = `claude:${p.display_name}`;
                option.textContent = p.display_name;
                optgroup.appendChild(option);
            });
            select.appendChild(optgroup);
        }

        // Add OpenCode projects
        if (opencodeData.projects) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = 'OpenCode 项目';
            opencodeData.projects.forEach(p => {
                const option = document.createElement('option');
                option.value = `opencode:${p.path}`;
                option.textContent = p.name;
                optgroup.appendChild(option);
            });
            select.appendChild(optgroup);
        }
    } catch (e) {
        console.error('Failed to load projects:', e);
    }
}

function switchSource(source) {
    currentSource = source;
    document.querySelectorAll('.source-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.source === source);
    });

    // Clear current analysis when switching
    document.getElementById('analysis-content').innerHTML = `
        <div class="metric-section">
            <p style="text-align: center; color: #6b7280; padding: 3rem;">
                选择数据源和日期范围，点击"生成分析"查看报告
            </p>
        </div>
    `;
}

function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}

async function loadAnalysis() {
    showLoading(true);

    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const projectFilter = document.getElementById('project-filter').value;

    try {
        if (currentSource === 'compare') {
            // Compare mode - load both sources
            const [claudeAnalysis, opencodeAnalysis] = await Promise.all([
                loadSourceAnalysis('claude', startDate, endDate, projectFilter),
                loadSourceAnalysis('opencode', startDate, endDate, projectFilter)
            ]);

            currentAnalysis = {
                claude: claudeAnalysis,
                opencode: opencodeAnalysis
            };
            renderCompareView(claudeAnalysis, opencodeAnalysis);
        } else {
            const analysis = await loadSourceAnalysis(currentSource, startDate, endDate, projectFilter);
            currentAnalysis = analysis;
            renderAnalysisView(analysis);
        }
    } catch (e) {
        console.error('Analysis failed:', e);
        document.getElementById('analysis-content').innerHTML = `
            <div class="metric-section">
                <p style="text-align: center; color: #ef4444; padding: 2rem;">
                    分析失败: ${e.message}
                </p>
            </div>
        `;
    } finally {
        showLoading(false);
    }
}

async function loadSourceAnalysis(source, startDate, endDate, projectFilter) {
    let projectPath = null;
    if (projectFilter && projectFilter.startsWith(source + ':')) {
        projectPath = projectFilter.substring(source.length + 1);
    }

    const response = await fetch(`/api/export-and-analyze/${source}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            start_date: startDate || null,
            end_date: endDate || null,
            project_path: projectPath
        })
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderAnalysisView(data) {
    const analysis = data.analysis;
    const overall = analysis.overall_assessment;

    const scoreClass = overall.overall_score >= 75 ? 'excellent' :
                       overall.overall_score >= 50 ? 'good' :
                       overall.overall_score >= 30 ? 'average' : 'poor';

    const container = document.getElementById('analysis-content');
    container.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'analysis-header';
    header.innerHTML = `
        <h1>${analysis.source === 'claude' ? 'Claude Code' : 'OpenCode'} 使用分析报告</h1>
        <div class="subtitle">
            ${escapeHtml(analysis.developer?.name || '开发者')} •
            ${analysis.date_range?.start || 'N/A'} 至 ${analysis.date_range?.end || 'N/A'}
        </div>
    `;
    container.appendChild(header);

    // Overall Score Card
    const scoreSection = document.createElement('div');
    scoreSection.className = 'metric-section';
    scoreSection.innerHTML = `
        <div class="score-card">
            <div class="score-circle ${scoreClass}">
                ${Math.round(overall.overall_score)}
            </div>
            <h2>综合评分</h2>
            <span class="level-badge ${overall.efficiency_level}">${overall.efficiency_level} 级</span>
            <p style="margin-top: 0.5rem; color: #6b7280;">${escapeHtml(overall.level_description || '')}</p>
        </div>
    `;
    container.appendChild(scoreSection);

    // Strengths and Improvements
    const strengthImprovement = document.createElement('div');
    strengthImprovement.className = 'strengths-improvements';
    const strengthsList = (overall.strengths || []).map(s => `<li>${escapeHtml(translateMetric(s))}</li>`).join('') || '<li>暂无</li>';
    const improvementsList = (overall.areas_for_improvement || []).map(s => `<li>${escapeHtml(translateMetric(s))}</li>`).join('') || '<li>暂无明显短板</li>';
    strengthImprovement.innerHTML = `
        <div class="metric-section strengths">
            <h3>优势领域</h3>
            <ul>${strengthsList}</ul>
        </div>
        <div class="metric-section improvements">
            <h3>待改进领域</h3>
            <ul>${improvementsList}</ul>
        </div>
    `;
    container.appendChild(strengthImprovement);

    // Recommendations
    const recommendations = document.createElement('div');
    recommendations.className = 'metric-section recommendations';
    const recommendationsList = (overall.recommendations || []).map(r => `<li>${escapeHtml(r)}</li>`).join('') || '<li>暂无建议</li>';
    recommendations.innerHTML = `
        <h3>改进建议</h3>
        <ul>${recommendationsList}</ul>
    `;
    container.appendChild(recommendations);

    // Detailed sections
    container.appendChild(createSection(renderActivitySection(analysis.activity_analysis)));
    container.appendChild(createSection(renderTaskEfficiencySection(analysis.task_efficiency_analysis)));
    container.appendChild(createSection(renderTokenEfficiencySection(analysis.token_efficiency_analysis)));
    container.appendChild(createSection(renderToolUsageSection(analysis.tool_usage_analysis)));
    container.appendChild(createSection(renderPromptQualitySection(analysis.prompt_quality_analysis)));
    container.appendChild(createSection(renderPromptQuantitySection(analysis.prompt_quantity_analysis)));
}

function createSection(html) {
    const section = document.createElement('div');
    section.innerHTML = html;
    return section.firstElementChild;
}

function translateMetric(metric) {
    const translations = {
        'activity': '活跃度',
        'task_efficiency': '任务效率',
        'token_efficiency': 'Token 效率',
        'tool_usage': '工具使用',
        'prompt_quality': '提示词质量',
        'prompt_quantity': '提示词数量',
        'code_changes': '代码改动'
    };
    return translations[metric] || metric;
}

function renderActivitySection(data) {
    return `
        <div class="metric-section">
            <h3>活跃度分析</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">活跃天数</div>
                    <div class="metric-value">${data.total_active_days} 天</div>
                    <div class="metric-subvalue">共 ${data.total_days_in_range} 天</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">活跃率</div>
                    <div class="metric-value">${data.active_days_percentage}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">日均提示词</div>
                    <div class="metric-value">${data.daily_average_prompts}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">日均会话</div>
                    <div class="metric-value">${data.daily_average_sessions}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">高峰时段</div>
                    <div class="metric-value">${data.peak_usage_hours.map(h => `${h}:00`).join(', ') || 'N/A'}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">活跃度评分</div>
                    <div class="metric-value">${data.activity_score} 分</div>
                    <div class="metric-subvalue">${data.activity_level === 'high' ? '高' : data.activity_level === 'medium' ? '中' : '低'}</div>
                </div>
            </div>
        </div>
    `;
}

function renderTaskEfficiencySection(data) {
    return `
        <div class="metric-section">
            <h3>任务效率分析</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">总会话数</div>
                    <div class="metric-value">${data.total_sessions}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">平均会话时长</div>
                    <div class="metric-value">${data.avg_session_duration_minutes} 分钟</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">会话平均提示词</div>
                    <div class="metric-value">${data.avg_prompts_per_session}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">中断率</div>
                    <div class="metric-value">${data.interruption_rate}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">错误率</div>
                    <div class="metric-value">${data.error_rate}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">成功率</div>
                    <div class="metric-value">${data.successful_completion_rate}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">效率评分</div>
                    <div class="metric-value">${data.task_efficiency_score} 分</div>
                    <span class="level-badge ${data.task_efficiency_level}">${data.task_efficiency_level} 级</span>
                </div>
            </div>
        </div>
    `;
}

function renderTokenEfficiencySection(data) {
    const tokens = data.total_tokens;
    return `
        <div class="metric-section">
            <h3>Token 效率分析</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">输入 Token</div>
                    <div class="metric-value">${formatNumber(tokens.input)}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">输出 Token</div>
                    <div class="metric-value">${formatNumber(tokens.output)}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">缓存读取</div>
                    <div class="metric-value">${formatNumber(tokens.cache_read)}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">缓存命中率</div>
                    <div class="metric-value">${data.cache_hit_rate}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">平均每提示词 Token</div>
                    <div class="metric-value">${formatNumber(data.avg_tokens_per_prompt)}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">输入输出比</div>
                    <div class="metric-value">${data.input_output_ratio}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">效率评分</div>
                    <div class="metric-value">${data.token_efficiency_score} 分</div>
                    <span class="level-badge ${data.token_efficiency_level}">${data.token_efficiency_level} 级</span>
                </div>
            </div>
        </div>
    `;
}

function renderToolUsageSection(data) {
    const toolList = Object.entries(data.tool_distribution || {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([tool, count]) => `${tool} (${count})`)
        .join(', ');

    return `
        <div class="metric-section">
            <h3>工具使用分析</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">工具使用总次数</div>
                    <div class="metric-value">${data.total_tools_used}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">工具种类</div>
                    <div class="metric-value">${data.unique_tools_count} 种</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">平均每提示词工具数</div>
                    <div class="metric-value">${data.avg_tools_per_prompt}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">最常用工具</div>
                    <div class="metric-value" style="font-size: 0.9rem;">${toolList || 'N/A'}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">多样性评分</div>
                    <div class="metric-value">${data.tool_diversity_score}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">使用水平</div>
                    <div class="metric-value">${data.tool_usage_level === 'diverse' ? '多样化' : data.tool_usage_level === 'moderate' ? '适中' : '专注'}</div>
                </div>
            </div>
        </div>
    `;
}

function renderPromptQualitySection(data) {
    return `
        <div class="metric-section">
            <h3>提示词质量分析</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">提示词总数</div>
                    <div class="metric-value">${data.total_prompts}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">平均长度</div>
                    <div class="metric-value">${formatNumber(data.avg_prompt_length)} 字符</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">长度分布</div>
                    <div class="metric-value" style="font-size: 0.9rem;">
                        短: ${data.prompt_length_distribution.short} |
                        中: ${data.prompt_length_distribution.medium} |
                        长: ${data.prompt_length_distribution.long}
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">含代码提示词</div>
                    <div class="metric-value">${data.prompts_with_code_percentage}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">清晰度评分</div>
                    <div class="metric-value">${data.prompt_clarity_score} 分</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">质量等级</div>
                    <div class="metric-value">${data.prompt_quality_level === 'excellent' ? '优秀' : data.prompt_quality_level === 'good' ? '良好' : '待改进'}</div>
                </div>
            </div>
        </div>
    `;
}

function renderPromptQuantitySection(data) {
    return `
        <div class="metric-section">
            <h3>提示词数量分析</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">提示词总数</div>
                    <div class="metric-value">${data.total_prompts}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">日均提示词</div>
                    <div class="metric-value">${data.prompts_per_day_average}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">每会话提示词</div>
                    <div class="metric-value">${data.prompts_per_session_average}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">每项目提示词</div>
                    <div class="metric-value">${data.prompts_per_project_average}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">频率趋势</div>
                    <div class="metric-value">${data.prompt_frequency_trend === 'increasing' ? '上升' : data.prompt_frequency_trend === 'decreasing' ? '下降' : '稳定'}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">数量评分</div>
                    <div class="metric-value">${data.prompt_quantity_score} 分</div>
                </div>
            </div>
        </div>
    `;
}

function renderCompareView(claudeData, opencodeData) {
    const claude = claudeData?.analysis;
    const opencode = opencodeData?.analysis;

    const container = document.getElementById('analysis-content');
    container.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'analysis-header';
    header.innerHTML = `
        <h1>双数据源对比分析</h1>
        <div class="subtitle">Claude Code vs OpenCode</div>
    `;
    container.appendChild(header);

    // Comparison cards
    const cardsRow = document.createElement('div');
    cardsRow.className = 'chart-row';
    cardsRow.innerHTML = `
        <div class="metric-section">
            <h3>Claude Code</h3>
            ${claude ? renderCompareCard(claude) : '<p style="color: #6b7280;">暂无数据</p>'}
        </div>
        <div class="metric-section">
            <h3>OpenCode</h3>
            ${opencode ? renderCompareCard(opencode) : '<p style="color: #6b7280;">暂无数据</p>'}
        </div>
    `;
    container.appendChild(cardsRow);

    // Comparison table
    if (claude && opencode) {
        const table = document.createElement('div');
        table.innerHTML = renderComparisonTable(claude, opencode);
        container.appendChild(table.firstElementChild);
    }
}

function renderCompareCard(analysis) {
    if (!analysis || !analysis.overall_assessment) {
        return '<p style="color: #6b7280; text-align: center;">暂无数据</p>';
    }

    const overall = analysis.overall_assessment;
    const scoreClass = overall.overall_score >= 75 ? 'excellent' :
                       overall.overall_score >= 50 ? 'good' :
                       overall.overall_score >= 30 ? 'average' : 'poor';

    return `
        <div class="score-card">
            <div class="score-circle ${scoreClass}">
                ${Math.round(overall.overall_score)}
            </div>
            <span class="level-badge ${overall.efficiency_level}">${overall.efficiency_level} 级</span>
            <p style="margin-top: 0.5rem; color: #6b7280; font-size: 0.9rem;">${escapeHtml(overall.level_description || '')}</p>
        </div>
        <div class="metric-grid" style="margin-top: 1rem;">
            <div class="metric-item">
                <div class="metric-label">活跃度</div>
                <div class="metric-value">${analysis.activity_analysis?.activity_score || 0} 分</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">任务效率</div>
                <div class="metric-value">${analysis.task_efficiency_analysis?.task_efficiency_score || 0} 分</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Token 效率</div>
                <div class="metric-value">${analysis.token_efficiency_analysis?.token_efficiency_score || 0} 分</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">提示词质量</div>
                <div class="metric-value">${analysis.prompt_quality_analysis?.prompt_reasonability_score || 0} 分</div>
            </div>
        </div>
    `;
}

function renderComparisonTable(claude, opencode) {
    // Handle null cases
    if (!claude || !opencode) {
        return `
            <div class="metric-section">
                <h3>关键指标对比</h3>
                <p style="color: #6b7280; text-align: center;">需要两个数据源都有数据才能对比</p>
            </div>
        `;
    }

    const metrics = [
        { name: '活跃天数', claude: claude.activity_analysis?.total_active_days || 0, opencode: opencode.activity_analysis?.total_active_days || 0 },
        { name: '总会话数', claude: claude.task_efficiency_analysis?.total_sessions || 0, opencode: opencode.task_efficiency_analysis?.total_sessions || 0 },
        { name: '提示词数', claude: claude.prompt_quantity_analysis?.total_prompts || 0, opencode: opencode.prompt_quantity_analysis?.total_prompts || 0 },
        { name: 'Token 总量', claude: claude.token_efficiency_analysis?.total_tokens?.total || 0, opencode: opencode.token_efficiency_analysis?.total_tokens?.total || 0 },
        { name: '平均会话时长(分)', claude: claude.task_efficiency_analysis?.avg_session_duration_minutes || 0, opencode: opencode.task_efficiency_analysis?.avg_session_duration_minutes || 0 },
        { name: '成功率(%)', claude: claude.task_efficiency_analysis?.successful_completion_rate || 0, opencode: opencode.task_efficiency_analysis?.successful_completion_rate || 0 },
    ];

    return `
        <div class="metric-section">
            <h3>关键指标对比</h3>
            <table class="data-table" style="width: 100%;">
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>Claude Code</th>
                        <th>OpenCode</th>
                        <th>差异</th>
                    </tr>
                </thead>
                <tbody>
                    ${metrics.map(m => `
                        <tr>
                            <td>${m.name}</td>
                            <td>${formatNumber(m.claude)}</td>
                            <td>${formatNumber(m.opencode)}</td>
                            <td style="color: ${m.claude > m.opencode ? '#10b981' : m.claude < m.opencode ? '#ef4444' : '#6b7280'};">
                                ${m.claude > m.opencode ? '+' : ''}${formatNumber(m.claude - m.opencode)}
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function formatNumber(num) {
    if (typeof num !== 'number') return num || '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toLocaleString();
}

async function exportAnalysis(format = 'json') {
    if (!currentAnalysis) {
        alert('请先生成分析报告');
        return;
    }

    const dateStr = new Date().toISOString().split('T')[0];

    if (format === 'markdown') {
        // Call the markdown API
        try {
            // currentAnalysis is the full export_and_analyze response
            // For markdown, we need to send the export_data to the analyze/markdown endpoint
            const exportData = currentAnalysis.export_data || currentAnalysis;

            const response = await fetch('/api/analyze/markdown', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(exportData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const markdown = await response.text();
            const blob = new Blob([markdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ai_analysis_${currentSource}_${dateStr}.md`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Export markdown failed:', e);
            alert('导出 Markdown 失败: ' + e.message);
        }
    } else {
        // JSON format
        const blob = new Blob([JSON.stringify(currentAnalysis, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ai_analysis_${currentSource}_${dateStr}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
}
