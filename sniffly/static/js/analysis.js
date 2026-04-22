/**
 * AI Usage Analysis Page JavaScript
 */

var currentSource = 'claude';
var currentAnalysis = null;
var multiAnalysisResults = null;

// Password protection: stored in JS variable only (cleared on refresh)
var analysisPassword = '';

// Intercept fetch to attach password header
var _originalFetch = window.fetch;
window.fetch = function(url, options) {
    options = options || {};
    if (analysisPassword && (!url.startsWith('http') || url.startsWith(window.location.origin))) {
        options.headers = options.headers || {};
        if (options.headers instanceof Headers) {
            options.headers.set('X-Analysis-Password', analysisPassword);
        } else {
            options.headers['X-Analysis-Password'] = analysisPassword;
        }
    }
    return _originalFetch.call(this, url, options);
};

// Password overlay logic
function initPasswordCheck() {
    fetch('/api/analysis/auth', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({password: ''})
    }).then(r => r.json()).then(data => {
        if (data.required === false) return; // No password configured
        // Password required - show overlay
        var overlay = document.getElementById('password-overlay');
        if (!overlay) return;
        overlay.style.display = 'flex';
        document.getElementById('analysis-pw').focus();
        document.getElementById('analysis-pw-btn').onclick = submitAnalysisPassword;
        document.getElementById('analysis-pw').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') submitAnalysisPassword();
        });
    }).catch(function() {});
}

function submitAnalysisPassword() {
    var pw = document.getElementById('analysis-pw').value;
    if (!pw) return;
    fetch('/api/analysis/auth', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({password: pw})
    }).then(function(r) {
        if (r.ok) {
            analysisPassword = pw;
            document.getElementById('password-overlay').style.display = 'none';
        } else {
            document.getElementById('analysis-pw-err').style.display = 'block';
            document.getElementById('analysis-pw').value = '';
            document.getElementById('analysis-pw').focus();
        }
    }).catch(function() {});
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initPasswordCheck();

    // Set default date range (last 30 days)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    document.getElementById('end-date').value = endDate.toISOString().split('T')[0];
    document.getElementById('start-date').value = startDate.toISOString().split('T')[0];

    // Show header buttons
    document.querySelectorAll('.btn-header').forEach(btn => {
        btn.style.display = 'block';
    });

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

    const exportControls = document.querySelector('.export-controls');

    if (source === 'multi') {
        if (exportControls) exportControls.style.display = 'none';
        renderMultiImportUI();
        return;
    }

    if (exportControls) exportControls.style.display = '';

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
    renderAnalysisViewInto(document.getElementById('analysis-content'), data);
}

function renderAnalysisViewInto(container, data) {
    const analysis = data.analysis;
    const overall = analysis.overall_assessment;

    const scoreClass = overall.overall_score >= 75 ? 'excellent' :
                       overall.overall_score >= 50 ? 'good' :
                       overall.overall_score >= 30 ? 'average' : 'poor';

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

    // Data Overview Card (from export summary)
    if (data.summary || data.export_data?.summary) {
        var sum = data.summary || data.export_data.summary;
        var totalTokens = 0;
        if (typeof sum.total_tokens === 'object' && sum.total_tokens !== null) {
            totalTokens = sum.total_tokens.total || (sum.total_tokens.input || 0) + (sum.total_tokens.output || 0);
        } else {
            totalTokens = sum.total_tokens || 0;
        }
        var summarySection = document.createElement('div');
        summarySection.className = 'metric-section';
        summarySection.innerHTML = '<h3>数据概览</h3>' +
            '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-top: 0.5rem;">' +
                '<div class="summary-stat"><div class="value" style="font-size: 1.3rem; font-weight: 600; color: #667eea;">' + formatNumber(sum.total_requests || 0) + '</div><div class="label" style="color: #6b7280; font-size: 0.85rem; margin-top: 0.25rem;">总消息数</div></div>' +
                '<div class="summary-stat"><div class="value" style="font-size: 1.3rem; font-weight: 600; color: #667eea;">' + formatNumber(sum.total_prompts || 0) + '</div><div class="label" style="color: #6b7280; font-size: 0.85rem; margin-top: 0.25rem;">用户消息数</div></div>' +
                '<div class="summary-stat"><div class="value" style="font-size: 1.3rem; font-weight: 600; color: #667eea;">' + formatNumber(totalTokens) + '</div><div class="label" style="color: #6b7280; font-size: 0.85rem; margin-top: 0.25rem;">Token 总量</div></div>' +
                '<div class="summary-stat"><div class="value" style="font-size: 1.3rem; font-weight: 600; color: #667eea;">' + (sum.total_cost ? '$' + sum.total_cost.toFixed(2) : '$0.00') + '</div><div class="label" style="color: #6b7280; font-size: 0.85rem; margin-top: 0.25rem;">总费用</div></div>' +
            '</div>';
        container.appendChild(summarySection);
    }

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
    var exportSummary = data.summary || (data.export_data && data.export_data.summary) || null;
    container.appendChild(createSection(renderActivitySection(analysis.activity_analysis, exportSummary)));
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

function renderActivitySection(data, summary) {
    var totalRequests = summary ? (summary.total_requests || 0) : 0;
    var totalPrompts = summary ? (summary.total_prompts || 0) : 0;
    return `
        <div class="metric-section">
            <h3>活跃度分析</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">总消息数</div>
                    <div class="metric-value">${formatNumber(totalRequests)}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">用户消息数</div>
                    <div class="metric-value">${formatNumber(totalPrompts)}</div>
                </div>
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
        alert('请先选择日期范围并点击"生成分析"');
        return;
    }

    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const dateStr = new Date().toISOString().split('T')[0];

    if (format === 'markdown') {
        try {
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
            downloadFile(markdown, `ai_analysis_${currentSource}_${dateStr}.md`, 'text/markdown');
        } catch (e) {
            console.error('Export markdown failed:', e);
            alert('导出 Markdown 失败: ' + e.message);
        }
    } else {
        const json = JSON.stringify(currentAnalysis, null, 2);
        downloadFile(json, `ai_analysis_${currentSource}_${dateStr}.json`, 'application/json');
    }
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// Import JSON export file and analyze it
async function importAndAnalyze(input) {
    const file = input.files[0];
    if (!file) return;

    showLoading(true);
    try {
        const text = await file.text();
        const exportData = JSON.parse(text);

        // Validate it's an export file
        if (!exportData.source || !exportData.summary) {
            throw new Error('无效的导出数据文件，缺少 source 或 summary 字段');
        }

        // Update source based on import data
        currentSource = exportData.source;
        document.querySelectorAll('.source-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.source === currentSource);
        });

        // Update date range display from import data
        const dateRange = exportData.export_info?.date_range || {};
        if (dateRange.start) document.getElementById('start-date').value = dateRange.start;
        if (dateRange.end) document.getElementById('end-date').value = dateRange.end;

        // Send to analyze API
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(exportData)
        });

        if (!response.ok) throw new Error(`分析失败: HTTP ${response.status}`);

        const analysis = await response.json();
        // Wrap in same structure as loadSourceAnalysis
        currentAnalysis = { analysis: analysis, export_data: exportData };
        renderAnalysisView(currentAnalysis);

    } catch (e) {
        console.error('Import analyze failed:', e);
        document.getElementById('analysis-content').innerHTML = `
            <div class="metric-section">
                <p style="text-align: center; color: #ef4444; padding: 2rem;">
                    导入分析失败: ${e.message}
                </p>
            </div>
        `;
    } finally {
        showLoading(false);
        input.value = '';
    }
}

// ============================================
// Multi-person analysis functions
// ============================================

function renderMultiImportUI() {
    const content = document.getElementById('analysis-content');
    content.innerHTML = `
        <div class="metric-section multi-import-section">
            <h3>离线多人数据分析</h3>
            <p style="color: #6b7280; margin-bottom: 0.5rem;">
                选择包含多人 JSON 数据文件的文件夹，或选择单个文件进行分析。
            </p>
            <p style="color: #9ca3af; font-size: 0.85rem;">
                文件名即为人名（去除 .json 后缀），子目录名称作为分组名。
            </p>
            <div class="import-buttons">
                <button class="btn-export" onclick="document.getElementById('multi-folder-input').click()"
                        style="background: #667eea; padding: 0.7rem 1.5rem; font-size: 1rem;">
                    选择文件夹
                </button>
                <button class="btn-export" onclick="document.getElementById('multi-single-input').click()"
                        style="background: #10b981; padding: 0.7rem 1.5rem; font-size: 1rem;">
                    选择单个文件
                </button>
            </div>
            <input type="file" id="multi-folder-input" webkitdirectory style="display:none"
                   onchange="handleFolderImport(this)">
            <input type="file" id="multi-single-input" accept=".json" style="display:none"
                   onchange="handleSingleFileImport(this)">
            <div id="import-progress" style="display:none; margin-top: 1rem;"></div>
        </div>
    `;
}

async function handleFolderImport(input) {
    const files = Array.from(input.files);
    const jsonFiles = files.filter(f => f.name.endsWith('.json'));

    if (jsonFiles.length === 0) {
        alert('所选文件夹中没有找到 JSON 文件');
        return;
    }

    showLoading(true);
    const progressEl = document.getElementById('import-progress');
    if (progressEl) {
        progressEl.style.display = 'block';
        progressEl.innerHTML = `<p style="color: #667eea;">正在读取 ${jsonFiles.length} 个文件...</p>`;
    }

    try {
        const people = [];
        let rootName = '';

        for (let i = 0; i < jsonFiles.length; i++) {
            const file = jsonFiles[i];
            const parts = file.webkitRelativePath.split('/');

            if (!rootName) rootName = parts[0];

            const fileName = parts[parts.length - 1];
            const personName = fileName.replace(/\.json$/i, '');

            let group;
            if (parts.length <= 2) {
                group = rootName;
            } else {
                group = parts[1];
            }

            try {
                const text = await file.text();
                const exportData = JSON.parse(text);
                if (!exportData.source || !exportData.summary) {
                    console.warn(`Skipping ${fileName}: invalid export format`);
                    continue;
                }
                people.push({
                    name: personName,
                    group: group,
                    export_data: exportData
                });
            } catch (e) {
                console.warn(`Skipping ${fileName}: parse error`, e);
            }

            if (progressEl) {
                progressEl.innerHTML = `<p style="color: #667eea;">正在读取 ${i + 1}/${jsonFiles.length} 个文件...</p>`;
            }
        }

        if (people.length === 0) {
            alert('没有找到有效的数据文件');
            return;
        }

        await performBatchAnalysis(people);
    } catch (e) {
        console.error('Folder import failed:', e);
        alert('文件夹导入失败: ' + e.message);
    } finally {
        showLoading(false);
        if (progressEl) progressEl.style.display = 'none';
        input.value = '';
    }
}

async function handleSingleFileImport(input) {
    const file = input.files[0];
    if (!file) return;

    showLoading(true);
    try {
        const text = await file.text();
        const exportData = JSON.parse(text);

        if (!exportData.source || !exportData.summary) {
            throw new Error('无效的导出数据文件，缺少 source 或 summary 字段');
        }

        const personName = file.name.replace(/\.json$/i, '');

        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(exportData)
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const analysis = await response.json();

        multiAnalysisResults = {
            results: [{
                name: personName,
                group: personName,
                summary: {
                    total_requests: exportData.summary.total_requests || 0,
                    total_prompts: exportData.summary.total_prompts || 0,
                    total_tokens: exportData.summary.total_tokens?.total || 0,
                    total_cost: exportData.summary.total_cost || 0,
                },
                analysis: analysis,
                export_data: exportData
            }],
            groups: {}
        };
        multiAnalysisResults.groups[personName] = {
            member_count: 1,
            total_requests: exportData.summary.total_requests || 0,
            avg_score: analysis.overall_assessment?.overall_score || 0,
            top_user: personName,
            top_user_score: analysis.overall_assessment?.overall_score || 0
        };

        renderMultiResults(multiAnalysisResults);
        showIndividualDetail(personName);
    } catch (e) {
        console.error('Single file import failed:', e);
        alert('导入分析失败: ' + e.message);
    } finally {
        showLoading(false);
        input.value = '';
    }
}

async function performBatchAnalysis(people) {
    const progressEl = document.getElementById('import-progress');
    if (progressEl) {
        progressEl.style.display = 'block';
        progressEl.innerHTML = `<p style="color: #667eea;">正在分析 ${people.length} 个人的数据...</p>`;
    }

    try {
        const response = await fetch('/api/analyze/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ people: people })
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }

        const result = await response.json();
        multiAnalysisResults = result;
        renderMultiResults(result);
    } catch (e) {
        document.getElementById('analysis-content').innerHTML = `
            <div class="metric-section">
                <p style="text-align: center; color: #ef4444; padding: 2rem;">
                    批量分析失败: ${e.message}
                </p>
            </div>
        `;
    } finally {
        if (progressEl) progressEl.style.display = 'none';
    }
}

function renderMultiResults(result) {
    const content = document.getElementById('analysis-content');
    const totalPeople = result.results.length;
    const groupNames = Object.keys(result.groups);
    const totalGroups = groupNames.length;
    const totalRequests = result.results.reduce((sum, r) => sum + (r.summary.total_requests || 0), 0);
    const avgScore = totalPeople > 0
        ? (result.results.reduce((sum, r) => sum + (r.analysis.overall_assessment?.overall_score || 0), 0) / totalPeople).toFixed(1)
        : '0';

    content.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
            <div class="multi-summary-cards" style="flex: 1;">
                <div class="multi-summary-card">
                    <div class="value">${totalPeople}</div>
                    <div class="label">总人数</div>
                </div>
                <div class="multi-summary-card">
                    <div class="value">${totalGroups}</div>
                    <div class="label">分组数</div>
                </div>
                <div class="multi-summary-card">
                    <div class="value">${formatNumber(totalRequests)}</div>
                    <div class="label">总请求数</div>
                </div>
                <div class="multi-summary-card">
                    <div class="value">${avgScore}</div>
                    <div class="label">平均评分</div>
                </div>
            </div>
            <button class="btn-export" onclick="exportMultiMarkdown()"
                    style="background: #10b981; white-space: nowrap; margin-left: 1rem;">📄 导出 Markdown 报告</button>
        </div>

        <div id="multi-insights-section" class="metric-section"></div>
        <div id="multi-scenario-section" class="metric-section"></div>
        <div class="chart-row">
            <div class="metric-section"><canvas id="chart-score"></canvas></div>
            <div class="metric-section"><canvas id="chart-tokens"></canvas></div>
        </div>
        <div class="chart-row" style="margin-top: 1.5rem;">
            <div class="metric-section"><canvas id="chart-prompts"></canvas></div>
            <div class="metric-section"><canvas id="chart-scenario"></canvas></div>
        </div>

        <div class="multi-sub-tabs" style="margin-top: 1.5rem;">
            <button class="multi-sub-tab active" onclick="switchMultiTab('ranking')">综合排名</button>
            <button class="multi-sub-tab" onclick="switchMultiTab('groups')">分组汇总</button>
        </div>

        <div id="multi-ranking-section">
            <div class="metric-section">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h3 style="margin: 0; border: none; padding: 0;">综合排名</h3>
                    <label style="font-size: 0.9rem; color: #6b7280;">
                        显示:
                        <select id="ranking-top-n" onchange="renderRankingTable()" style="padding: 0.3rem 0.5rem; border: 1px solid #d1d5db; border-radius: 4px;">
                            <option value="10">TOP 10</option>
                            <option value="20">TOP 20</option>
                            <option value="50">TOP 50</option>
                            <option value="0">全部</option>
                        </select>
                    </label>
                </div>
                <table class="ranking-table">
                    <thead>
                        <tr>
                            <th style="width: 60px;">排名</th>
                            <th>姓名</th>
                            <th>所属组</th>
                            <th>总消息数</th>
                            <th>用户消息数</th>
                            <th>Token</th>
                            <th>提示词</th>
                            <th>活跃等级</th>
                        </tr>
                    </thead>
                    <tbody id="ranking-tbody"></tbody>
                </table>
            </div>
        </div>

        <div id="multi-groups-section" style="display:none;">
            <div class="metric-section">
                <h3>分组汇总对比</h3>
                <table class="ranking-table">
                    <thead>
                        <tr>
                            <th>分组</th>
                            <th>人数</th>
                            <th>总消息数</th>
                            <th>平均消息数</th>
                            <th>Token</th>
                            <th>提示词</th>
                            <th>最高使用者</th>
                            <th>占比</th>
                        </tr>
                    </thead>
                    <tbody id="groups-tbody"></tbody>
                </table>
            </div>
        </div>

        <div id="multi-individual-section" style="display:none;">
            <button class="back-btn" onclick="backToRanking()">&#8592; 返回排名</button>
            <div id="multi-individual-content"></div>
        </div>
    `;

    renderInsights(result);
    renderScenarioAnalysis(result);
    renderCharts(result);
    renderRankingTable();
    renderGroupsTable();
}

function renderRankingTable() {
    if (!multiAnalysisResults) return;

    const topNSelect = document.getElementById('ranking-top-n');
    const topN = topNSelect ? parseInt(topNSelect.value) : 10;

    const sorted = [...multiAnalysisResults.results].sort((a, b) =>
        (b.analysis.overall_assessment?.overall_score || 0) -
        (a.analysis.overall_assessment?.overall_score || 0)
    );

    const display = topN > 0 ? sorted.slice(0, topN) : sorted;

    const tbody = document.getElementById('ranking-tbody');
    if (!tbody) return;

    tbody.innerHTML = display.map((person, index) => {
        const totalReqs = person.summary.total_requests || 0;
        var totalTokens = 0;
        if (typeof person.summary.total_tokens === 'object' && person.summary.total_tokens !== null) {
            totalTokens = person.summary.total_tokens.total || (person.summary.total_tokens.input || 0) + (person.summary.total_tokens.output || 0);
        } else {
            totalTokens = person.summary.total_tokens || 0;
        }
        var promptCount = person.analysis.prompt_quantity_analysis?.total_prompts || person.summary.total_prompts || 0;
        const rank = index + 1;

        const medals = ['🥇','🥈','🥉'];
        const rankDisplay = rank <= 3
            ? '<span class="rank-medal">' + medals[rank - 1] + '</span>'
            : String(rank);

        var activityText = '中';
        if (totalReqs >= 5000) activityText = '极高';
        else if (totalReqs >= 1000) activityText = '高';

        const safeName = escapeHtml(person.name).replace(/'/g, "\\'");
        return '<tr onclick="showIndividualDetail(\'' + safeName + '\')" title="点击查看详细分析">' +
            '<td style="text-align: center;">' + rankDisplay + '</td>' +
            '<td style="font-weight: 500; color: #667eea;">' + escapeHtml(person.name) + '</td>' +
            '<td>' + escapeHtml(person.group) + '</td>' +
            '<td>' + formatNumber(totalReqs) + '</td>' +
            '<td>' + formatNumber(person.summary.total_prompts || 0) + '</td>' +
            '<td>' + formatNumber(totalTokens) + '</td>' +
            '<td>' + promptCount + '</td>' +
            '<td><span class="level-badge">' + activityText + '</span></td>' +
            '</tr>';
    }).join('');
}

function renderGroupsTable() {
    if (!multiAnalysisResults) return;

    const groups = multiAnalysisResults.groups;
    const totalRequests = Object.values(groups).reduce((sum, g) => sum + g.total_requests, 0);

    const sortedGroups = Object.entries(groups).sort((a, b) => b[1].avg_score - a[1].avg_score);

    const tbody = document.getElementById('groups-tbody');
    if (!tbody) return;

    tbody.innerHTML = sortedGroups.map(([name, data]) => {
        const share = totalRequests > 0 ? (data.total_requests / totalRequests * 100).toFixed(1) : '0.0';
        var avgMsgs = data.member_count > 0 ? (data.total_requests / data.member_count).toFixed(0) : '0';
        return '<tr>' +
            '<td style="font-weight: 500;">' + escapeHtml(name) + '</td>' +
            '<td>' + data.member_count + '</td>' +
            '<td>' + formatNumber(data.total_requests) + '</td>' +
            '<td style="font-weight: 600; color: #667eea;">' + avgMsgs + '</td>' +
            '<td>' + formatNumber(data.total_tokens || 0) + '</td>' +
            '<td>' + formatNumber(data.total_prompts || 0) + '</td>' +
            '<td>' + escapeHtml(data.top_user) + '</td>' +
            '<td>' + share + '%</td>' +
            '</tr>';
    }).join('');

    // Add totals row
    var totalMembers = Object.values(groups).reduce((sum, g) => sum + g.member_count, 0);
    var overallAvg = totalMembers > 0 ? (totalRequests / totalMembers).toFixed(0) : '0';
    var totalTokens = Object.values(groups).reduce((sum, g) => sum + (g.total_tokens || 0), 0);
    var totalPrompts = Object.values(groups).reduce((sum, g) => sum + (g.total_prompts || 0), 0);
    tbody.innerHTML += '<tr style="font-weight: 600; background: #f0f4ff; border-top: 2px solid #667eea;">' +
        '<td>合计</td>' +
        '<td>' + totalMembers + '</td>' +
        '<td>' + formatNumber(totalRequests) + '</td>' +
        '<td style="color: #667eea;">' + overallAvg + '</td>' +
        '<td>' + formatNumber(totalTokens) + '</td>' +
        '<td>' + formatNumber(totalPrompts) + '</td>' +
        '<td>-</td>' +
        '<td>100%</td>' +
        '</tr>';
}

function switchMultiTab(tab) {
    document.querySelectorAll('.multi-sub-tab').forEach(t => {
        t.classList.toggle('active', t.textContent.includes(tab === 'ranking' ? '综合排名' : '分组汇总'));
    });

    const rankingSection = document.getElementById('multi-ranking-section');
    const groupsSection = document.getElementById('multi-groups-section');
    const individualSection = document.getElementById('multi-individual-section');

    if (rankingSection) rankingSection.style.display = tab === 'ranking' ? '' : 'none';
    if (groupsSection) groupsSection.style.display = tab === 'groups' ? '' : 'none';
    if (individualSection) individualSection.style.display = 'none';
}

function showIndividualDetail(personName) {
    if (!multiAnalysisResults) return;

    const person = multiAnalysisResults.results.find(r => r.name === personName);
    if (!person) return;

    const rankingSection = document.getElementById('multi-ranking-section');
    const groupsSection = document.getElementById('multi-groups-section');
    const individualSection = document.getElementById('multi-individual-section');
    const subTabs = document.querySelectorAll('.multi-sub-tab');

    if (rankingSection) rankingSection.style.display = 'none';
    if (groupsSection) groupsSection.style.display = 'none';
    if (individualSection) individualSection.style.display = '';
    subTabs.forEach(t => t.style.display = 'none');

    const container = document.getElementById('multi-individual-content');
    if (!container) return;
    container.innerHTML = '';

    renderAnalysisViewInto(container, {
        analysis: person.analysis,
        export_data: person.export_data,
        summary: person.summary
    });
}

function backToRanking() {
    const rankingSection = document.getElementById('multi-ranking-section');
    const groupsSection = document.getElementById('multi-groups-section');
    const individualSection = document.getElementById('multi-individual-section');
    const subTabs = document.querySelectorAll('.multi-sub-tab');

    if (rankingSection) rankingSection.style.display = '';
    if (individualSection) individualSection.style.display = 'none';
    subTabs.forEach(t => t.style.display = '');

    const activeTab = document.querySelector('.multi-sub-tab.active');
    if (activeTab) {
        const isRanking = activeTab.textContent.includes('综合排名');
        if (groupsSection) groupsSection.style.display = isRanking ? 'none' : '';
        if (rankingSection) rankingSection.style.display = isRanking ? '' : 'none';
    }

    const container = document.getElementById('multi-individual-content');
    if (container) container.innerHTML = '';
}

// ============================================
// Insights, Scenario Analysis, Charts
// ============================================

var SCENARIO_TOOL_MAP = {
    '代码分析与调试': ['Read', 'Write', 'Edit', 'MultiEdit', 'Grep', 'Glob', 'Agent'],
    '问题排查': ['Bash', 'TaskOutput', 'TaskStop'],
    'Git操作辅助': [],
    '文档撰写': ['NotebookEdit'],
    '开发环境搭建': ['EnterPlanMode', 'ExitPlanMode', 'EnterWorktree', 'ExitWorktree', 'Skill', 'CronCreate', 'CronDelete', 'CronList']
};

function renderInsights(result) {
    var el = document.getElementById('multi-insights-section');
    if (!el || !result.results || result.results.length === 0) return;

    var totalReqs = result.results.reduce(function(s, r) { return s + (r.summary.total_requests || 0); }, 0);
    var totalPrompts = result.results.reduce(function(s, r) { return s + (r.summary.total_prompts || 0); }, 0);

    var topUser = result.results.reduce(function(max, r) {
        return (r.summary.total_requests || 0) > (max.summary.total_requests || 0) ? r : max;
    }, result.results[0]);
    var topPercent = totalReqs > 0 ? ((topUser.summary.total_requests / totalReqs) * 100).toFixed(1) : '0';

    var avgScore = (result.results.reduce(function(s, r) {
        return s + (r.analysis.overall_assessment?.overall_score || 0);
    }, 0) / result.results.length).toFixed(1);

    var avgPrompts = (totalPrompts / result.results.length).toFixed(0);

    var topTokenUser = result.results.reduce(function(max, r) {
        return (r.summary.total_tokens || 0) > (max.summary.total_tokens || 0) ? r : max;
    }, result.results[0]);

    var levelDesc = avgScore >= 75 ? '优秀' : avgScore >= 60 ? '良好' : avgScore >= 40 ? '合格' : '待改进';

    el.innerHTML = '<h3>分析结论</h3>' +
        '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-top: 0.5rem;">' +
            '<div style="background: #f0f9ff; padding: 1rem; border-radius: 8px; border-left: 4px solid #3b82f6;">' +
                '<div style="font-size: 0.85rem; color: #6b7280;">最活跃用户</div>' +
                '<div style="font-size: 1.1rem; font-weight: 600; color: #1e40af; margin-top: 0.3rem;">' + escapeHtml(topUser.name) + '</div>' +
                '<div style="font-size: 0.8rem; color: #6b7280; margin-top: 0.2rem;">贡献了 ' + topPercent + '% 的请求</div>' +
            '</div>' +
            '<div style="background: #f0fdf4; padding: 1rem; border-radius: 8px; border-left: 4px solid #10b981;">' +
                '<div style="font-size: 0.85rem; color: #6b7280;">整体使用水平</div>' +
                '<div style="font-size: 1.1rem; font-weight: 600; color: #166534; margin-top: 0.3rem;">平均评分 ' + avgScore + ' 分</div>' +
                '<div style="font-size: 0.8rem; color: #6b7280; margin-top: 0.2rem;">等级: ' + levelDesc + '</div>' +
            '</div>' +
            '<div style="background: #fefce8; padding: 1rem; border-radius: 8px; border-left: 4px solid #f59e0b;">' +
                '<div style="font-size: 0.85rem; color: #6b7280;">人均提示词</div>' +
                '<div style="font-size: 1.1rem; font-weight: 600; color: #92400e; margin-top: 0.3rem;">' + formatNumber(parseInt(avgPrompts)) + ' 条</div>' +
                '<div style="font-size: 0.8rem; color: #6b7280; margin-top: 0.2rem;">总计 ' + formatNumber(totalPrompts) + ' 条</div>' +
            '</div>' +
            '<div style="background: #fdf2f8; padding: 1rem; border-radius: 8px; border-left: 4px solid #ec4899;">' +
                '<div style="font-size: 0.85rem; color: #6b7280;">Token 消耗大户</div>' +
                '<div style="font-size: 1.1rem; font-weight: 600; color: #9d174d; margin-top: 0.3rem;">' + escapeHtml(topTokenUser.name) + '</div>' +
                '<div style="font-size: 0.8rem; color: #6b7280; margin-top: 0.2rem;">共 ' + formatNumber(topTokenUser.summary.total_tokens || 0) + ' Token</div>' +
            '</div>' +
        '</div>';
}

function renderScenarioAnalysis(result) {
    var el = document.getElementById('multi-scenario-section');
    if (!el || !result.results || result.results.length === 0) return;

    var scenarios = {};
    for (var sn in SCENARIO_TOOL_MAP) {
        scenarios[sn] = { count: 0, people: {} };
    }

    result.results.forEach(function(person) {
        var dist = person.analysis.tool_usage_analysis?.tool_distribution || {};
        for (var tool in dist) {
            var count = dist[tool];
            var matched = false;
            for (var scenario in SCENARIO_TOOL_MAP) {
                if (SCENARIO_TOOL_MAP[scenario].indexOf(tool) >= 0) {
                    scenarios[scenario].count += count;
                    scenarios[scenario].people[person.name] = true;
                    matched = true;
                    break;
                }
            }
            if (!matched && tool.toLowerCase().indexOf('git') >= 0) {
                scenarios['Git操作辅助'].count += count;
                scenarios['Git操作辅助'].people[person.name] = true;
            }
        }
    });

    var totalScenarioCount = 0;
    for (var s in scenarios) totalScenarioCount += scenarios[s].count;

    var scenarioIcons = {
        '代码分析与调试': '💻',
        '问题排查': '🔍',
        'Git操作辅助': '🔀',
        '文档撰写': '📝',
        '开发环境搭建': '🛠️'
    };

    var rows = '';
    for (var name in scenarios) {
        var data = scenarios[name];
        var pct = totalScenarioCount > 0 ? (data.count / totalScenarioCount * 100).toFixed(1) : '0';
        var people = Object.keys(data.people);
        var peopleStr = people.length > 3 ? people.slice(0, 3).join(', ') + ' 等' + people.length + '人' : people.join(', ') || '-';
        rows += '<tr>' +
            '<td>' + (scenarioIcons[name] || '') + ' ' + name + '</td>' +
            '<td>' + peopleStr + '</td>' +
            '<td style="font-weight: 600;">' + formatNumber(data.count) + '</td>' +
            '<td>' +
                '<div style="display: flex; align-items: center; gap: 0.5rem;">' +
                    '<div style="flex: 1; height: 8px; background: #e5e7eb; border-radius: 4px;">' +
                        '<div style="width: ' + pct + '%; height: 100%; background: #667eea; border-radius: 4px;"></div>' +
                    '</div>' +
                    '<span style="font-size: 0.85rem;">' + pct + '%</span>' +
                '</div>' +
            '</td>' +
        '</tr>';
    }

    el.innerHTML = '<h3>使用场景分布</h3>' +
        '<table class="ranking-table" style="margin-top: 0.5rem;">' +
            '<thead><tr><th>场景</th><th>涉及人员</th><th>工具使用次数</th><th>占比</th></tr></thead>' +
            '<tbody>' + rows + '</tbody>' +
        '</table>';
}

var _chartInstances = [];

function renderCharts(result) {
    _chartInstances.forEach(function(c) { c.destroy(); });
    _chartInstances = [];

    if (!result.results || result.results.length === 0) return;

    var names = result.results.map(function(r) { return r.name; });
    var scores = result.results.map(function(r) { return r.analysis.overall_assessment?.overall_score || 0; });
    var tokens = result.results.map(function(r) { return r.summary.total_tokens || 0; });
    var prompts = result.results.map(function(r) { return r.summary.total_prompts || 0; });

    var barColors = ['#667eea', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

    function makeChart(canvasId, label, data, options) {
        var ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        var chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: names,
                datasets: [{
                    label: label,
                    data: data,
                    backgroundColor: data.map(function(v, i) {
                        if (options.colorByValue) {
                            return v >= 75 ? '#10b981' : v >= 60 ? '#3b82f6' : v >= 40 ? '#f59e0b' : '#ef4444';
                        }
                        return barColors[i % barColors.length];
                    })
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: options.title || label, font: { size: 14 } }
                },
                scales: {
                    y: { beginAtZero: true, max: options.max || undefined }
                }
            }
        });
        _chartInstances.push(chart);
        return chart;
    }

    makeChart('chart-score', '综合评分', scores, { title: '综合评分对比', colorByValue: true, max: 100 });
    makeChart('chart-tokens', 'Token', tokens, { title: 'Token 消耗对比' });
    makeChart('chart-prompts', '提示词', prompts, { title: '提示词数量对比' });

    // Scenario chart (horizontal bar)
    var scenarios = {};
    for (var sn in SCENARIO_TOOL_MAP) scenarios[sn] = 0;
    result.results.forEach(function(person) {
        var dist = person.analysis.tool_usage_analysis?.tool_distribution || {};
        for (var tool in dist) {
            var matched = false;
            for (var scenario in SCENARIO_TOOL_MAP) {
                if (SCENARIO_TOOL_MAP[scenario].indexOf(tool) >= 0) {
                    scenarios[scenario] += dist[tool];
                    matched = true;
                    break;
                }
            }
            if (!matched && tool.toLowerCase().indexOf('git') >= 0) {
                scenarios['Git操作辅助'] += dist[tool];
            }
        }
    });

    var scenarioCtx = document.getElementById('chart-scenario');
    if (scenarioCtx) {
        var sLabels = Object.keys(scenarios);
        var sData = sLabels.map(function(k) { return scenarios[k]; });
        var sChart = new Chart(scenarioCtx, {
            type: 'bar',
            data: {
                labels: sLabels,
                datasets: [{
                    label: '工具使用次数',
                    data: sData,
                    backgroundColor: barColors.slice(0, sLabels.length)
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: '使用场景分布', font: { size: 14 } }
                },
                scales: { x: { beginAtZero: true } }
            }
        });
        _chartInstances.push(sChart);
    }
}

function exportMultiMarkdown() {
    if (!multiAnalysisResults) {
        alert('请先导入数据并完成分析');
        return;
    }
    var result = multiAnalysisResults;
    var lines = [];

    lines.push('# 团队 AI 使用分析报告\n');

    var now = new Date();
    lines.push('**生成时间**: ' + now.getFullYear() + '-' + String(now.getMonth()+1).padStart(2,'0') + '-' + String(now.getDate()).padStart(2,'0') + '\n');

    // Overview
    var totalPeople = result.results.length;
    var totalReqs = result.results.reduce(function(s, r) { return s + (r.summary.total_requests || 0); }, 0);
    var totalPrompts = result.results.reduce(function(s, r) { return s + (r.summary.total_prompts || 0); }, 0);
    var totalTokens = result.results.reduce(function(s, r) { return s + (r.summary.total_tokens || 0); }, 0);
    var avgScore = totalPeople > 0
        ? (result.results.reduce(function(s, r) { return s + (r.analysis.overall_assessment?.overall_score || 0); }, 0) / totalPeople).toFixed(1)
        : '0';

    lines.push('## 概览\n');
    lines.push('| 指标 | 值 |');
    lines.push('|------|------|');
    lines.push('| 总人数 | ' + totalPeople + ' |');
    lines.push('| 分组数 | ' + Object.keys(result.groups).length + ' |');
    lines.push('| 总请求数 | ' + formatNumber(totalReqs) + ' |');
    lines.push('| 总提示词 | ' + formatNumber(totalPrompts) + ' |');
    lines.push('| 总 Token | ' + formatNumber(totalTokens) + ' |');
    lines.push('| 平均评分 | ' + avgScore + ' 分 |\n');

    // Insights
    lines.push('## 分析结论\n');
    var topUser = result.results.reduce(function(max, r) {
        return (r.summary.total_requests || 0) > (max.summary.total_requests || 0) ? r : max;
    }, result.results[0]);
    var topPercent = totalReqs > 0 ? ((topUser.summary.total_requests / totalReqs) * 100).toFixed(1) : '0';
    lines.push('- **最活跃用户**: ' + topUser.name + '，贡献了 ' + topPercent + '% 的请求');
    lines.push('- **整体使用水平**: 平均评分 ' + avgScore + ' 分');
    lines.push('- **人均提示词**: ' + (totalPeople > 0 ? Math.round(totalPrompts / totalPeople) : 0) + ' 条');

    var topTokenUser = result.results.reduce(function(max, r) {
        return (r.summary.total_tokens || 0) > (max.summary.total_tokens || 0) ? r : max;
    }, result.results[0]);
    lines.push('- **Token 消耗大户**: ' + topTokenUser.name + '，共 ' + formatNumber(topTokenUser.summary.total_tokens || 0) + ' Token\n');

    // Ranking table
    lines.push('## 综合排名\n');
    lines.push('| 排名 | 姓名 | 所属组 | 总消息数 | 用户消息数 | Token | 提示词 | 活跃等级 |');
    lines.push('|------|------|--------|----------|-----------|-------|--------|----------|');

    var sorted = result.results.slice().sort(function(a, b) {
        return (b.analysis.overall_assessment?.overall_score || 0) - (a.analysis.overall_assessment?.overall_score || 0);
    });
    sorted.forEach(function(person, i) {
        var reqs = person.summary.total_requests || 0;
        var prompts = person.summary.total_prompts || 0;
        var tokens = person.summary.total_tokens || 0;
        var pCount = person.analysis.prompt_quantity_analysis?.total_prompts || prompts;
        var level = reqs >= 5000 ? '极高' : reqs >= 1000 ? '高' : '中';
        lines.push('| ' + (i+1) + ' | ' + person.name + ' | ' + person.group + ' | ' + reqs + ' | ' + prompts + ' | ' + tokens + ' | ' + pCount + ' | ' + level + ' |');
    });
    lines.push('');

    // Groups
    lines.push('## 分组汇总\n');
    lines.push('| 分组 | 人数 | 总消息数 | 平均消息数 | Token | 提示词 | 最高使用者 | 占比 |');
    lines.push('|------|------|---------|-----------|-------|--------|-----------|------|');
    var gTotalReqs = Object.values(result.groups).reduce(function(s, g) { return s + g.total_requests; }, 0);
    Object.entries(result.groups).sort(function(a, b) { return b[1].avg_score - a[1].avg_score; }).forEach(function(entry) {
        var name = entry[0], g = entry[1];
        var share = gTotalReqs > 0 ? (g.total_requests / gTotalReqs * 100).toFixed(1) : '0.0';
        var avg = g.member_count > 0 ? Math.round(g.total_requests / g.member_count) : 0;
        lines.push('| ' + name + ' | ' + g.member_count + ' | ' + g.total_requests + ' | ' + avg + ' | ' + (g.total_tokens || 0) + ' | ' + (g.total_prompts || 0) + ' | ' + g.top_user + ' | ' + share + '% |');
    });
    lines.push('');

    // Scenario
    lines.push('## 使用场景分布\n');
    lines.push('| 场景 | 工具使用次数 | 占比 |');
    lines.push('|------|-------------|------|');

    var scenarios = {};
    for (var sn in SCENARIO_TOOL_MAP) scenarios[sn] = 0;
    result.results.forEach(function(person) {
        var dist = person.analysis.tool_usage_analysis?.tool_distribution || {};
        for (var tool in dist) {
            var matched = false;
            for (var scenario in SCENARIO_TOOL_MAP) {
                if (SCENARIO_TOOL_MAP[scenario].indexOf(tool) >= 0) {
                    scenarios[scenario] += dist[tool];
                    matched = true;
                    break;
                }
            }
            if (!matched && tool.toLowerCase().indexOf('git') >= 0) {
                scenarios['Git操作辅助'] += dist[tool];
            }
        }
    });
    var sTotal = 0;
    for (var k in scenarios) sTotal += scenarios[k];
    for (var sk in scenarios) {
        var pct = sTotal > 0 ? (scenarios[sk] / sTotal * 100).toFixed(1) : '0';
        lines.push('| ' + sk + ' | ' + scenarios[sk] + ' | ' + pct + '% |');
    }
    lines.push('');

    // Individual summaries
    lines.push('## 各成员评分概览\n');
    sorted.forEach(function(person) {
        var overall = person.analysis.overall_assessment || {};
        lines.push('### ' + person.name + ' (' + person.group + ')');
        lines.push('- 综合评分: ' + (overall.overall_score || 0) + ' 分 (' + (overall.efficiency_level || 'N/A') + ' 级)');
        lines.push('- 总消息数: ' + (person.summary.total_requests || 0));
        lines.push('- Token: ' + formatNumber(person.summary.total_tokens || 0));
        lines.push('- 提示词: ' + (person.summary.total_prompts || 0));
        if (overall.strengths && overall.strengths.length > 0) {
            lines.push('- 优势: ' + overall.strengths.map(translateMetric).join(', '));
        }
        lines.push('');
    });

    var md = lines.join('\n');
    var dateStr = new Date().toISOString().split('T')[0];
    downloadFile(md, 'team_analysis_' + dateStr + '.md', 'text/markdown');
}
